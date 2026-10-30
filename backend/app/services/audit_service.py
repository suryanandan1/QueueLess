from typing import Any

from sqlalchemy.orm import Session

from app.middleware.request_context import get_client_ip
from app.models import AuditLog, User


def record_audit(
    db: Session,
    *,
    action: str,
    actor: User | None,
    business_id: int | None = None,
    entity_type: str | None = None,
    entity_id: int | None = None,
    details: dict[str, Any] | None = None,
) -> None:
    """Stage an audit entry in the caller's transaction (committed together with the change)."""
    db.add(
        AuditLog(
            actor_user_id=actor.id if actor else None,
            business_id=business_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            details=details,
            ip_address=get_client_ip(),
        )
    )
