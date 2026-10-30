from sqlalchemy import select, update
from sqlalchemy.orm import Session, joinedload

from app.core.exceptions import BadRequestError, ConflictError, NotFoundError
from app.core.security import hash_password
from app.models import (
    BusinessMember,
    Counter,
    MemberRole,
    NotificationType,
    User,
    UserRole,
)
from app.schemas.member import MemberCreate, MemberUpdate
from app.services.access_control import require_business_role
from app.services.audit_service import record_audit
from app.services.auth_service import get_user_by_email
from app.services.db_utils import commit_or_conflict
from app.services.notification_service import create_notification

ALREADY_MEMBER_MESSAGE = "This user is already a member of the business."


def list_members(db: Session, actor: User, business_id: int) -> list[BusinessMember]:
    require_business_role(db, actor, business_id, MemberRole.STAFF)
    return list(
        db.scalars(
            select(BusinessMember)
            .options(joinedload(BusinessMember.user))
            .where(BusinessMember.business_id == business_id)
            .order_by(BusinessMember.created_at)
        ).all()
    )


def _get_member_in_business(db: Session, business_id: int, member_id: int) -> BusinessMember:
    # Filtering by business_id as well guarantees a member of another business is never touched.
    member = db.scalar(
        select(BusinessMember)
        .options(joinedload(BusinessMember.user))
        .where(BusinessMember.id == member_id, BusinessMember.business_id == business_id)
    )
    if member is None:
        raise NotFoundError("Member not found.")
    return member


def add_member(db: Session, actor: User, business_id: int, data: MemberCreate) -> BusinessMember:
    business = require_business_role(db, actor, business_id, MemberRole.OWNER)

    user = get_user_by_email(db, data.email)
    if user is None:
        if not (data.full_name and data.password):
            raise NotFoundError(
                "No account exists for this email. Provide full_name and password "
                "to create a staff account."
            )
        user = User(
            email=data.email,
            full_name=data.full_name.strip(),
            phone=data.phone,
            hashed_password=hash_password(data.password),
            role=UserRole.STAFF,
        )
        db.add(user)
        db.flush()
    else:
        if not user.is_active:
            raise BadRequestError("This account is deactivated and cannot be added.")
        existing = db.scalar(
            select(BusinessMember).where(
                BusinessMember.business_id == business_id, BusinessMember.user_id == user.id
            )
        )
        if existing is not None:
            raise ConflictError(ALREADY_MEMBER_MESSAGE)
        # A customer who joins a business's team gets access to the staff dashboard.
        if user.role == UserRole.CUSTOMER:
            user.role = UserRole.STAFF

    member = BusinessMember(business_id=business_id, user_id=user.id, role=data.role)
    db.add(member)
    db.flush()
    create_notification(
        db,
        user_id=user.id,
        business_id=business_id,
        notification_type=NotificationType.MEMBERSHIP,
        title="You joined a team",
        message=f"You were added to {business.name} as {data.role.value.lower()}.",
    )
    record_audit(db, action="member.added", actor=actor, business_id=business_id,
                 entity_type="business_member", entity_id=member.id,
                 details={"user_id": user.id, "role": data.role.value})
    commit_or_conflict(db, ALREADY_MEMBER_MESSAGE)
    db.refresh(member)
    return member


def update_member(
    db: Session, actor: User, business_id: int, member_id: int, data: MemberUpdate
) -> BusinessMember:
    require_business_role(db, actor, business_id, MemberRole.OWNER)
    member = _get_member_in_business(db, business_id, member_id)
    if member.role == MemberRole.OWNER:
        raise BadRequestError("The owner's membership cannot be changed.")

    changes = data.changes()
    for field_name, value in changes.items():
        setattr(member, field_name, value)
    if changes:
        record_audit(db, action="member.updated", actor=actor, business_id=business_id,
                     entity_type="business_member", entity_id=member.id,
                     details={key: getattr(value, "value", value) for key, value in changes.items()})
        db.commit()
    return member


def remove_member(db: Session, actor: User, business_id: int, member_id: int) -> None:
    require_business_role(db, actor, business_id, MemberRole.OWNER)
    member = _get_member_in_business(db, business_id, member_id)
    if member.role == MemberRole.OWNER:
        raise BadRequestError("The owner cannot be removed from the business.")

    db.execute(
        update(Counter).where(Counter.assigned_member_id == member.id).values(assigned_member_id=None)
    )
    record_audit(db, action="member.removed", actor=actor, business_id=business_id,
                 entity_type="business_member", entity_id=member.id,
                 details={"user_id": member.user_id})
    db.delete(member)
    db.commit()
