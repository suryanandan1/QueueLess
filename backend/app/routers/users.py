from fastapi import APIRouter, Request, status

from app.core.dependencies import CurrentUser, DbSession
from app.schemas.auth import ChangePasswordRequest
from app.schemas.user import UserRead, UserUpdate
from app.services import auth_service, user_service

router = APIRouter(prefix="/users", tags=["Users"])


@router.patch("/me", response_model=UserRead)
def update_my_profile(payload: UserUpdate, db: DbSession, current_user: CurrentUser):
    return user_service.update_profile(db, current_user, payload)


@router.post("/me/change-password", status_code=status.HTTP_204_NO_CONTENT)
def change_my_password(
    payload: ChangePasswordRequest, request: Request, db: DbSession, current_user: CurrentUser
) -> None:
    auth_service.change_password(
        db,
        current_user,
        payload.current_password,
        payload.new_password,
        getattr(request.state, "session_id", None),
    )
