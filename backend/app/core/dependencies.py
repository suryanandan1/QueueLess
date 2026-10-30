from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, Query, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.exceptions import AuthenticationError, PermissionDeniedError
from app.core.security import ACCESS_TOKEN_TYPE, decode_token
from app.database import get_db
from app.models import User, UserRole
from app.services import auth_service

bearer_scheme = HTTPBearer(auto_error=False, description="JWT access token")

DbSession = Annotated[Session, Depends(get_db)]


def authenticate_access_token(db: Session, token: str) -> tuple[User, str]:
    """Validate an access token and return (user, session_id)."""
    payload = decode_token(token, ACCESS_TOKEN_TYPE)
    session_id = payload.get("sid")
    if not session_id or not auth_service.is_session_active(db, session_id):
        raise AuthenticationError("Session has ended. Please sign in again.")

    user = db.get(User, int(payload["sub"]))
    if user is None:
        raise AuthenticationError("User no longer exists.")
    if not user.is_active:
        raise PermissionDeniedError("Your account has been deactivated.")
    return user, session_id


def get_current_user(
    request: Request,
    db: DbSession,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> User:
    if credentials is None:
        raise AuthenticationError("Not authenticated.")
    user, session_id = authenticate_access_token(db, credentials.credentials)
    request.state.session_id = session_id
    return user


def get_optional_current_user(
    request: Request,
    db: DbSession,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> User | None:
    """Like get_current_user but returns None for anonymous requests.

    An invalid token still fails loudly rather than silently downgrading to anonymous.
    """
    if credentials is None:
        return None
    return get_current_user(request, db, credentials)


CurrentUser = Annotated[User, Depends(get_current_user)]
OptionalUser = Annotated[User | None, Depends(get_optional_current_user)]


def require_roles(*roles: UserRole) -> Callable[[User], User]:
    def _checker(user: CurrentUser) -> User:
        if user.role not in roles:
            raise PermissionDeniedError()
        return user

    return _checker


SuperAdmin = Annotated[User, Depends(require_roles(UserRole.SUPER_ADMIN))]


class Pagination:
    def __init__(
        self,
        limit: Annotated[int, Query(ge=1, le=100)] = 20,
        offset: Annotated[int, Query(ge=0)] = 0,
    ) -> None:
        self.limit = limit
        self.offset = offset


PaginationParams = Annotated[Pagination, Depends()]
