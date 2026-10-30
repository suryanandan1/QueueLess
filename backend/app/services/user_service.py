from sqlalchemy.orm import Session

from app.models import User
from app.schemas.user import UserUpdate
from app.services.audit_service import record_audit


def update_profile(db: Session, user: User, data: UserUpdate) -> User:
    changes = data.changes()
    if "full_name" in changes:
        changes["full_name"] = changes["full_name"].strip()
    for field_name, value in changes.items():
        setattr(user, field_name, value)
    if changes:
        record_audit(db, action="user.profile_updated", actor=user, entity_type="user",
                     entity_id=user.id, details={"fields": sorted(changes)})
        db.commit()
    return user
