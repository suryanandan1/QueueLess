"""Business-scoped authorization.

Every endpoint that touches a business's private data goes through
`require_business_role`, which resolves the caller's membership from the
database. The business id in the URL is never trusted on its own.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError, PermissionDeniedError
from app.models import Business, BusinessMember, MemberRole, User, UserRole

ROLE_RANK = {MemberRole.STAFF: 1, MemberRole.MANAGER: 2, MemberRole.OWNER: 3}


def get_business_or_404(db: Session, business_id: int) -> Business:
    business = db.get(Business, business_id)
    if business is None:
        raise NotFoundError("Business not found.")
    return business


def get_active_membership(db: Session, business_id: int, user_id: int) -> BusinessMember | None:
    return db.scalar(
        select(BusinessMember).where(
            BusinessMember.business_id == business_id,
            BusinessMember.user_id == user_id,
            BusinessMember.is_active.is_(True),
        )
    )


def has_business_role(
    db: Session, user: User | None, business_id: int, min_role: MemberRole = MemberRole.STAFF
) -> bool:
    if user is None:
        return False
    if user.role == UserRole.SUPER_ADMIN:
        return True
    membership = get_active_membership(db, business_id, user.id)
    return membership is not None and ROLE_RANK[membership.role] >= ROLE_RANK[min_role]


def require_business_role(
    db: Session, user: User, business_id: int, min_role: MemberRole = MemberRole.STAFF
) -> Business:
    """Return the business if `user` holds at least `min_role` in it (super admins always pass)."""
    business = get_business_or_404(db, business_id)
    if not has_business_role(db, user, business_id, min_role):
        raise PermissionDeniedError("You do not have permission to access this business.")
    return business
