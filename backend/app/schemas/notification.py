from datetime import datetime

from pydantic import BaseModel

from app.models import NotificationType
from app.schemas.common import ORMModel


class NotificationRead(ORMModel):
    id: int
    business_id: int | None
    type: NotificationType
    title: str
    message: str
    is_read: bool
    read_at: datetime | None
    created_at: datetime


class UnreadCount(BaseModel):
    unread: int
