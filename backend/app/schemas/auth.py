from pydantic import BaseModel, EmailStr, Field

from app.schemas.common import Password, PhoneNumber
from app.schemas.user import NormalizedEmailModel, UserRead


class RegisterRequest(NormalizedEmailModel):
    email: EmailStr
    password: Password
    full_name: str = Field(min_length=2, max_length=120)
    phone: PhoneNumber = None


class LoginRequest(NormalizedEmailModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=1)


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = Field(description="Access token lifetime in seconds")
    user: UserRead


class ForgotPasswordRequest(NormalizedEmailModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str = Field(min_length=1)
    new_password: Password


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: Password
