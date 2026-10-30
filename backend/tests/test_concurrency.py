"""Concurrency tests against a real file-backed SQLite database.

The in-memory test database shares one connection, so it cannot exercise lock
contention. Here every thread gets its own connection and session, exactly like
concurrent API requests.
"""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from threading import Barrier

import pytest
from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from app.core.exceptions import AppError
from app.core.security import hash_password
from app.database import Base, create_db_engine
from app.models import (
    Business,
    BusinessMember,
    Counter,
    MemberRole,
    QueueSession,
    QueueToken,
    Service,
    TokenStatus,
    User,
    UserRole,
)
from app.schemas.appointment import AppointmentCreate
from app.services import appointment_service, queue_service, token_service

ALL_DAYS_OPEN = [
    {"day_of_week": day, "is_closed": False, "open_time": "00:00:00", "close_time": "23:59:00"}
    for day in range(7)
]


@pytest.fixture
def file_db(tmp_path):
    engine = create_db_engine(f"sqlite:///{tmp_path / 'concurrency.db'}")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    yield factory
    engine.dispose()


def _seed(factory, customers: int, capacity: int | None = None) -> dict:
    password = hash_password("Passw0rd!")
    with factory() as db:
        owner = User(email="owner@example.com", full_name="Owner", hashed_password=password,
                     role=UserRole.BUSINESS_OWNER)
        users = [User(email=f"c{i}@example.com", full_name=f"C{i}", hashed_password=password)
                 for i in range(customers)]
        business = Business(name="Busy Bank", slug="busy-bank", timezone="UTC",
                            working_hours=ALL_DAYS_OPEN)
        db.add_all([owner, business, *users])
        db.flush()
        db.add(BusinessMember(business_id=business.id, user_id=owner.id, role=MemberRole.OWNER))
        service = Service(business_id=business.id, name="Deposit", estimated_duration_minutes=5,
                          appointments_enabled=True, appointment_duration_minutes=30)
        db.add(service)
        db.flush()
        counters = [Counter(service_id=service.id, name=f"Desk {i}") for i in range(4)]
        queue = QueueSession(business_id=business.id, service_id=service.id,
                             session_date=datetime.now(timezone.utc).date(), max_capacity=capacity)
        db.add_all([*counters, queue])
        db.commit()
        return {
            "owner_id": owner.id,
            "user_ids": [u.id for u in users],
            "queue_id": queue.id,
            "service_id": service.id,
            "counter_ids": [c.id for c in counters],
        }


def _run_concurrently(count: int, work) -> list:
    barrier = Barrier(count)

    def wrapped(index):
        barrier.wait()  # start everyone at the same moment
        try:
            return work(index)
        except AppError as exc:
            return exc

    with ThreadPoolExecutor(max_workers=count) as pool:
        return list(pool.map(wrapped, range(count)))


def test_concurrent_joins_get_unique_sequential_numbers(file_db):
    seed = _seed(file_db, customers=20)

    def join(index):
        with file_db() as db:
            user = db.get(User, seed["user_ids"][index])
            return queue_service.join_queue(db, user, seed["queue_id"]).token_number

    results = _run_concurrently(20, join)
    assert not [r for r in results if isinstance(r, Exception)]
    assert sorted(results) == list(range(1, 21))
    with file_db() as db:
        assert db.get(QueueSession, seed["queue_id"]).next_token_number == 21


def test_concurrent_joins_respect_capacity(file_db):
    seed = _seed(file_db, customers=15, capacity=5)

    def join(index):
        with file_db() as db:
            user = db.get(User, seed["user_ids"][index])
            return queue_service.join_queue(db, user, seed["queue_id"]).token_number

    results = _run_concurrently(15, join)
    successes = [r for r in results if isinstance(r, int)]
    assert len(successes) == 5
    assert all("full" in str(r) for r in results if isinstance(r, Exception))
    with file_db() as db:
        count = len(db.scalars(select(QueueToken).where(QueueToken.queue_session_id == seed["queue_id"])).all())
        assert count == 5


def test_same_customer_double_submit_creates_one_token(file_db):
    seed = _seed(file_db, customers=1)

    def join(_index):
        with file_db() as db:
            user = db.get(User, seed["user_ids"][0])
            return queue_service.join_queue(db, user, seed["queue_id"]).token_number

    results = _run_concurrently(6, join)
    assert len([r for r in results if isinstance(r, int)]) == 1
    with file_db() as db:
        tokens = db.scalars(select(QueueToken).where(QueueToken.queue_session_id == seed["queue_id"])).all()
        assert len(tokens) == 1


def test_counters_never_call_the_same_token(file_db):
    seed = _seed(file_db, customers=4)
    with file_db() as db:
        for user_id in seed["user_ids"]:
            queue_service.join_queue(db, db.get(User, user_id), seed["queue_id"])

    def call_next(index):
        with file_db() as db:
            owner = db.get(User, seed["owner_id"])
            return token_service.call_next(db, owner, seed["counter_ids"][index]).id

    results = _run_concurrently(4, call_next)
    called = [r for r in results if isinstance(r, int)]
    assert len(called) == len(set(called)) == 4
    with file_db() as db:
        statuses = db.scalars(select(QueueToken.status)).all()
        assert statuses.count(TokenStatus.CALLED) == 4


def test_two_staff_completing_same_token_only_one_wins(file_db):
    seed = _seed(file_db, customers=1)
    with file_db() as db:
        owner = db.get(User, seed["owner_id"])
        token = queue_service.join_queue(db, db.get(User, seed["user_ids"][0]), seed["queue_id"])
        token_service.call_token(db, owner, token.id, seed["counter_ids"][0])
        token_service.start_service(db, owner, token.id)

    def complete(_index):
        with file_db() as db:
            return token_service.complete_service(db, db.get(User, seed["owner_id"]), token.id).status

    results = _run_concurrently(4, complete)
    assert results.count(TokenStatus.COMPLETED) == 1
    assert sum(isinstance(r, AppError) for r in results) == 3


def test_concurrent_bookings_cannot_overbook_a_slot(file_db):
    seed = _seed(file_db, customers=8)
    start = (datetime.now(timezone.utc) + timedelta(days=1)).replace(hour=10, minute=0, second=0,
                                                                     microsecond=0)

    def book(index):
        with file_db() as db:
            user = db.get(User, seed["user_ids"][index])
            data = AppointmentCreate(service_id=seed["service_id"], scheduled_start=start)
            return appointment_service.book_appointment(db, user, data).id

    results = _run_concurrently(8, book)
    assert len([r for r in results if isinstance(r, int)]) == 1  # slot capacity is 1
