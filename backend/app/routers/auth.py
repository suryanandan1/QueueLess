from typing import Annotated

from fastapi import APIRouter, Header, status

from app.core.dependencies import CurrentUser, DbSession
from app.models import UserRole
from app.schemas.auth import (
    ForgotPasswordRequest,
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    ResetPasswordRequest,
    TokenPair,
)
from app.schemas.common import Message
from app.schemas.user import UserRead
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["Authentication"])

UserAgent = Annotated[str | None, Header()]


@router.post("/register/customer", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def register_customer(payload: RegisterRequest, db: DbSession):
    return auth_service.register_user(db, payload, UserRole.CUSTOMER)


@router.post(
    "/register/business-owner", response_model=UserRead, status_code=status.HTTP_201_CREATED
)
def register_business_owner(payload: RegisterRequest, db: DbSession):
    return auth_service.register_user(db, payload, UserRole.BUSINESS_OWNER)


@router.post("/login", response_model=TokenPair)
def login(payload: LoginRequest, db: DbSession, user_agent: UserAgent = None):
    return auth_service.login(db, payload.email, payload.password, user_agent)


@router.post("/refresh", response_model=TokenPair)
def refresh(payload: RefreshRequest, db: DbSession, user_agent: UserAgent = None):
    return auth_service.refresh_session(db, payload.refresh_token, user_agent)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(payload: RefreshRequest, db: DbSession) -> None:
    auth_service.logout(db, payload.refresh_token)


@router.get("/me", response_model=UserRead)
def read_current_user(current_user: CurrentUser):
    return current_user


@router.post("/forgot-password", response_model=Message, status_code=status.HTTP_202_ACCEPTED)
def forgot_password(payload: ForgotPasswordRequest, db: DbSession):
    auth_service.request_password_reset(db, payload.email)
    return Message(message="If an account exists for this email, a reset link has been sent.")


@router.post("/reset-password", response_model=Message)
def reset_password(payload: ResetPasswordRequest, db: DbSession):
    auth_service.reset_password(db, payload.token, payload.new_password)
    return Message(message="Your password has been reset. Please sign in.")
