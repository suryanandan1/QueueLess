from fastapi import APIRouter, status

from app.core.dependencies import CurrentUser, DbSession, PaginationParams
from app.schemas.common import Page
from app.schemas.notification import NotificationRead, UnreadCount
from app.services import notification_service

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get("", response_model=Page[NotificationRead])
def list_notifications(db: DbSession, current_user: CurrentUser, pagination: PaginationParams,
                       unread_only: bool = False):
    items, total = notification_service.list_notifications(
        db, current_user, unread_only, pagination.limit, pagination.offset
    )
    return Page(items=items, total=total, limit=pagination.limit, offset=pagination.offset)


@router.get("/unread-count", response_model=UnreadCount)
def unread_count(db: DbSession, current_user: CurrentUser):
    return UnreadCount(unread=notification_service.count_unread(db, current_user))


@router.patch("/{notification_id}/read", response_model=NotificationRead)
def mark_notification_read(notification_id: int, db: DbSession, current_user: CurrentUser):
    return notification_service.mark_read(db, current_user, notification_id)


@router.post("/read-all", status_code=status.HTTP_204_NO_CONTENT)
def mark_all_notifications_read(db: DbSession, current_user: CurrentUser) -> None:
    notification_service.mark_all_read(db, current_user)
