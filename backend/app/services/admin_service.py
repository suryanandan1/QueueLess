from datetime import datetime, timezone

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.exceptions import BadRequestError, NotFoundError
from app.models import AuditLog, Business, QueueSession, QueueToken, Service, User, UserRole
from app.schemas.admin import PlatformStats
from app.services.audit_service import record_audit
from app.services.auth_service import revoke_all_sessions


def _count(db: Session, query) -> int:
    return db.scalar(query) or 0


def get_platform_stats(db: Session) -> PlatformStats:
    role_counts = dict(db.execute(select(User.role, func.count(User.id)).group_by(User.role)).all())
    # Platform-wide view uses the UTC date; per-business stats use the business's timezone.
    today_utc = datetime.now(timezone.utc).date()
    return PlatformStats(
        total_users=_count(db, select(func.count(User.id))),
        active_users=_count(db, select(func.count(User.id)).where(User.is_active.is_(True))),
        users_by_role={role.value: role_counts.get(role, 0) for role in UserRole},
        total_businesses=_count(db, select(func.count(Business.id))),
        active_businesses=_count(
            db, select(func.count(Business.id)).where(Business.is_active.is_(True))
        ),
        total_services=_count(db, select(func.count(Service.id))),
        tokens_today=_count(
            db,
            select(func.count(QueueToken.id))
            .join(QueueSession)
            .where(QueueSession.session_date == today_utc),
        ),
    )


def _paginate(db: Session, query, order_by, limit: int, offset: int):
    total = _count(db, select(func.count()).select_from(query.subquery()))
    items = db.scalars(query.order_by(*order_by).limit(limit).offset(offset)).all()
    return list(items), total


def list_users(
    db: Session,
    search: str | None,
    role: UserRole | None,
    is_active: bool | None,
    limit: int,
    offset: int,
) -> tuple[list[User], int]:
    query = select(User)
    if search:
        pattern = f"%{search.strip()}%"
        query = query.where(or_(User.email.ilike(pattern), User.full_name.ilike(pattern)))
    if role:
        query = query.where(User.role == role)
    if is_active is not None:
        query = query.where(User.is_active.is_(is_active))
    return _paginate(db, query, (User.created_at.desc(), User.id.desc()), limit, offset)


def set_user_status(db: Session, actor: User, user_id: int, is_active: bool) -> User:
    if actor.id == user_id:
        raise BadRequestError("You cannot change the status of your own account.")
    user = db.get(User, user_id)
    if user is None:
        raise NotFoundError("User not found.")
    if user.is_active != is_active:
        user.is_active = is_active
        if not is_active:
            revoke_all_sessions(db, user.id)
        record_audit(db, action="user.activated" if is_active else "user.deactivated",
                     actor=actor, entity_type="user", entity_id=user.id)
        db.commit()
    return user


def list_businesses(
    db: Session, search: str | None, is_active: bool | None, limit: int, offset: int
) -> tuple[list[Business], int]:
    query = select(Business)
    if search:
        query = query.where(Business.name.ilike(f"%{search.strip()}%"))
    if is_active is not None:
        query = query.where(Business.is_active.is_(is_active))
    return _paginate(db, query, (Business.created_at.desc(), Business.id.desc()), limit, offset)


def list_audit_logs(
    db: Session, business_id: int | None, action: str | None, limit: int, offset: int
) -> tuple[list[AuditLog], int]:
    query = select(AuditLog)
    if business_id is not None:
        query = query.where(AuditLog.business_id == business_id)
    if action:
        query = query.where(AuditLog.action == action)
    return _paginate(db, query, (AuditLog.created_at.desc(), AuditLog.id.desc()), limit, offset)
