import os

# Must be set before the app (and its settings) are imported.
os.environ.setdefault("SECRET_KEY", "test-secret-key-that-is-long-enough-for-hs256")
os.environ["DATABASE_URL"] = "sqlite://"
os.environ["BCRYPT_ROUNDS"] = "4"

from collections.abc import Callable, Generator  # noqa: E402

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy.orm import Session, sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from app.core.security import hash_password  # noqa: E402
from app.database import Base, create_db_engine, get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.models import User, UserRole  # noqa: E402

API = "/api/v1"
DEFAULT_PASSWORD = "Passw0rd!"


@pytest.fixture
def db_session_factory() -> Generator[sessionmaker, None, None]:
    engine = create_db_engine("sqlite://", poolclass=StaticPool)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    yield factory
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
def db(db_session_factory: sessionmaker) -> Generator[Session, None, None]:
    session = db_session_factory()
    yield session
    session.close()


@pytest.fixture
def client(db_session_factory: sessionmaker) -> Generator[TestClient, None, None]:
    def override_get_db():
        session = db_session_factory()
        try:
            yield session
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def register(client: TestClient) -> Callable[..., dict]:
    def _register(email: str, role: str = "customer", full_name: str = "Test User") -> dict:
        response = client.post(
            f"{API}/auth/register/{role}",
            json={"email": email, "password": DEFAULT_PASSWORD, "full_name": full_name},
        )
        assert response.status_code == 201, response.text
        return response.json()

    return _register


@pytest.fixture
def login(client: TestClient) -> Callable[..., dict]:
    def _login(email: str, password: str = DEFAULT_PASSWORD) -> dict:
        response = client.post(f"{API}/auth/login", json={"email": email, "password": password})
        assert response.status_code == 200, response.text
        return response.json()

    return _login


@pytest.fixture
def make_user(register, login) -> Callable[..., dict[str, str]]:
    """Register + log in; returns auth headers."""

    def _make_user(email: str, role: str = "customer") -> dict[str, str]:
        register(email, role)
        return auth_header(login(email)["access_token"])

    return _make_user


@pytest.fixture
def owner_headers(make_user) -> dict[str, str]:
    return make_user("owner@example.com", "business-owner")


@pytest.fixture
def customer_headers(make_user) -> dict[str, str]:
    return make_user("customer@example.com")


@pytest.fixture
def admin_headers(db: Session, login) -> dict[str, str]:
    db.add(
        User(
            email="admin@example.com",
            full_name="Platform Admin",
            hashed_password=hash_password(DEFAULT_PASSWORD),
            role=UserRole.SUPER_ADMIN,
        )
    )
    db.commit()
    return auth_header(login("admin@example.com")["access_token"])


@pytest.fixture
def create_business(client: TestClient) -> Callable[..., dict]:
    def _create(headers: dict[str, str], name: str = "City Bank", **fields) -> dict:
        response = client.post(
            f"{API}/businesses", json={"name": name, "category": "BANK", **fields}, headers=headers
        )
        assert response.status_code == 201, response.text
        return response.json()

    return _create


@pytest.fixture
def create_service(client: TestClient) -> Callable[..., dict]:
    def _create(headers: dict[str, str], business_id: int, name: str = "Cash Deposit", **fields):
        payload = {"name": name, "estimated_duration_minutes": 10, **fields}
        response = client.post(
            f"{API}/businesses/{business_id}/services", json=payload, headers=headers
        )
        assert response.status_code == 201, response.text
        return response.json()

    return _create


@pytest.fixture
def queue_setup(client, owner_headers, make_user, create_business, create_service):
    """A business with one service, a counter assigned to a staff member, and an open queue."""
    business = create_business(owner_headers, "Sunrise Salon", timezone="UTC")
    service = create_service(owner_headers, business["id"], "Haircut", estimated_duration_minutes=20)
    staff_headers = make_user("staff@example.com")
    member = client.post(
        f"{API}/businesses/{business['id']}/members",
        json={"email": "staff@example.com", "role": "STAFF"},
        headers=owner_headers,
    ).json()
    counter = client.post(
        f"{API}/services/{service['id']}/counters",
        json={"name": "Chair 1", "assigned_member_id": member["id"]},
        headers=owner_headers,
    ).json()
    queue = client.post(
        f"{API}/queues", json={"service_id": service["id"]}, headers=owner_headers
    )
    assert queue.status_code == 201, queue.text
    return {
        "business": business,
        "service": service,
        "counter": counter,
        "queue": queue.json(),
        "owner": owner_headers,
        "staff": staff_headers,
    }
