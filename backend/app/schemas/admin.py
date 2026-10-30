from datetime import datetime
from typing import Any

from pydantic import BaseModel

from app.schemas.common import ORMModel


class PlatformStats(BaseModel):
    total_users: int
    active_users: int
    users_by_role: dict[str, int]
    total_businesses: int
    active_businesses: int
    total_services: int
    tokens_today: int


class AuditLogRead(ORMModel):
    id: int
    actor_user_id: int | None
    business_id: int | None
    action: str
    entity_type: str | None
    entity_id: int | None
    details: dict[str, Any] | None
    ip_address: str | None
    created_at: datetime
