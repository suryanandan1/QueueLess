import logging
from datetime import datetime, timezone

from sqlalchemy import delete, select, update
from sqlalchemy.orm import Session

from app.config import settings
from app.core.exceptions import AuthenticationError, ConflictError, PermissionDeniedError
from app.core.security import (
    DUMMY_PASSWORD_HASH,
    PASSWORD_RESET_TOKEN_TYPE,
    REFRESH_TOKEN_TYPE,
    create_access_token,
    create_password_reset_token,
    create_refresh_token,
    decode_token,
    hash_password,
    password_fingerprint,
    verify_password,
)
from app.models import RefreshToken, User, UserRole
from app.schemas.auth import RegisterRequest, TokenPair
from app.schemas.user import UserRead
from app.services.audit_service import record_audit
from app.services.db_utils import commit_or_conflict

logger = logging.getLogger(__name__)

SELF_REGISTRATION_ROLES = {UserRole.CUSTOMER, UserRole.BUSINESS_OWNER}
EMAIL_TAKEN_MESSAGE = "An account with this email already exists."


def get_user_by_email(db: Session, email: str) -> User | None:
    return db.scalar(select(User).where(User.email == email.lower()))


def register_user(db: Session, data: RegisterRequest, role: UserRole) -> User:
    if role not in SELF_REGISTRATION_ROLES:
        raise PermissionDeniedError("This role cannot be self-registered.")
    if get_user_by_email(db, data.email):
        raise ConflictError(EMAIL_TAKEN_MESSAGE)

    user = User(
        email=data.email,
        full_name=data.full_name.strip(),
        phone=data.phone,
        hashed_password=hash_password(data.password),
        role=role,
    )
    db.add(user)
    db.flush()
    record_audit(db, action="user.registered", actor=user, entity_type="user", entity_id=user.id,
                 details={"role": role.value})
    commit_or_conflict(db, EMAIL_TAKEN_MESSAGE)
    return user


def authenticate(db: Session, email: str, password: str) -> User:
    user = get_user_by_email(db, email)
    if user is None:
        verify_password(password, DUMMY_PASSWORD_HASH)
        raise AuthenticationError("Invalid email or password.")
    if not verify_password(password, user.hashed_password):
        raise AuthenticationError("Invalid email or password.")
    if not user.is_active:
        raise PermissionDeniedError("Your account has been deactivated.")
    return user


def _issue_token_pair(db: Session, user: User, user_agent: str | None) -> TokenPair:
    """Create a new refresh session row and the matching access token (caller commits)."""
    now = datetime.now(timezone.utc)
    # Housekeeping: drop this user's expired sessions.
    db.execute(
        delete(RefreshToken).where(RefreshToken.user_id == user.id, RefreshToken.expires_at < now)
    )

    refresh_token, jti, expires_at = create_refresh_token(user.id)
    db.add(
        RefreshToken(
            user_id=user.id,
            jti=jti,
            expires_at=expires_at,
            user_agent=(user_agent or "")[:255] or None,
        )
    )
    access_token, expires_in = create_access_token(user.id, user.role.value, jti)
    return TokenPair(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=expires_in,
        user=UserRead.model_validate(user),
    )


def login(db: Session, email: str, password: str, user_agent: str | None) -> TokenPair:
    user = authenticate(db, email, password)
    user.last_login_at = datetime.now(timezone.utc)
    pair = _issue_token_pair(db, user, user_agent)
    record_audit(db, action="auth.login", actor=user, entity_type="user", entity_id=user.id)
    db.commit()
    return pair


def refresh_session(db: Session, refresh_token: str, user_agent: str | None) -> TokenPair:
    """Rotate a refresh token: the presented token is revoked and a new pair issued."""
    payload = decode_token(refresh_token, REFRESH_TOKEN_TYPE)
    session = db.scalar(select(RefreshToken).where(RefreshToken.jti == payload.get("jti")))
    if session is None or session.user_id != int(payload["sub"]):
        raise AuthenticationError("Invalid refresh token.")

    if session.revoked_at is not None:
        # A revoked token being replayed suggests theft: end every session for this user.
        revoke_all_sessions(db, session.user_id)
        record_audit(db, action="auth.refresh_reuse_detected", actor=session.user,
                     entity_type="user", entity_id=session.user_id)
        db.commit()
        raise AuthenticationError("Refresh token has been revoked.")

    user = session.user
    if not user.is_active:
        raise PermissionDeniedError("Your account has been deactivated.")

    session.revoked_at = datetime.now(timezone.utc)
    pair = _issue_token_pair(db, user, user_agent)
    db.commit()
    return pair


def logout(db: Session, refresh_token: str) -> None:
    payload = decode_token(refresh_token, REFRESH_TOKEN_TYPE)
    session = db.scalar(select(RefreshToken).where(RefreshToken.jti == payload.get("jti")))
    if session is None:
        raise AuthenticationError("Invalid refresh token.")
    if session.revoked_at is None:
        session.revoked_at = datetime.now(timezone.utc)
        record_audit(db, action="auth.logout", actor=session.user, entity_type="user",
                     entity_id=session.user_id)
        db.commit()


def is_session_active(db: Session, jti: str) -> bool:
    session = db.scalar(select(RefreshToken).where(RefreshToken.jti == jti))
    return (
        session is not None
        and session.revoked_at is None
        and session.expires_at > datetime.now(timezone.utc)
    )


def revoke_all_sessions(db: Session, user_id: int, except_jti: str | None = None) -> None:
    statement = update(RefreshToken).where(
        RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None)
    )
    if except_jti:
        statement = statement.where(RefreshToken.jti != except_jti)
    db.execute(statement.values(revoked_at=datetime.now(timezone.utc)))


def request_password_reset(db: Session, email: str) -> None:
    """Generate a reset link for an active account.

    No email provider is configured yet, so the link is written to the server log.
    The API response is identical whether or not the email exists.
    """
    user = get_user_by_email(db, email)
    if user is None or not user.is_active:
        return
    token = create_password_reset_token(user.id, user.hashed_password)
    reset_link = f"{settings.frontend_url}/reset-password?token={token}"
    logger.warning("Password reset requested for %s. Reset link: %s", user.email, reset_link)
    record_audit(db, action="auth.password_reset_requested", actor=user, entity_type="user",
                 entity_id=user.id)
    db.commit()


def reset_password(db: Session, token: str, new_password: str) -> None:
    payload = decode_token(token, PASSWORD_RESET_TOKEN_TYPE)
    user = db.get(User, int(payload["sub"]))
    if user is None or not user.is_active:
        raise AuthenticationError("Invalid reset token.")
    if payload.get("pwd") != password_fingerprint(user.hashed_password):
        raise AuthenticationError("This reset link has already been used.")

    user.hashed_password = hash_password(new_password)
    revoke_all_sessions(db, user.id)
    record_audit(db, action="auth.password_reset", actor=user, entity_type="user", entity_id=user.id)
    db.commit()


def change_password(
    db: Session, user: User, current_password: str, new_password: str, current_session: str | None
) -> None:
    if not verify_password(current_password, user.hashed_password):
        raise AuthenticationError("Current password is incorrect.")
    user.hashed_password = hash_password(new_password)
    # Keep the session making this request; sign out everywhere else.
    revoke_all_sessions(db, user.id, except_jti=current_session)
    record_audit(db, action="user.password_changed", actor=user, entity_type="user",
                 entity_id=user.id)
    db.commit()
