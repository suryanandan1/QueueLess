import hashlib
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
import jwt

from app.config import settings
from app.core.exceptions import AuthenticationError

ACCESS_TOKEN_TYPE = "access"
REFRESH_TOKEN_TYPE = "refresh"
PASSWORD_RESET_TOKEN_TYPE = "password_reset"


def hash_password(password: str) -> str:
    salt = bcrypt.gensalt(rounds=settings.bcrypt_rounds)
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def verify_password(password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), hashed_password.encode("utf-8"))
    except ValueError:
        # Malformed hash or password longer than bcrypt supports.
        return False


# Used to spend the same time on logins for unknown emails (prevents user enumeration).
DUMMY_PASSWORD_HASH = hash_password("queueless-timing-equalizer")


def password_fingerprint(hashed_password: str) -> str:
    """Short digest of the current hash; changes whenever the password changes."""
    return hashlib.sha256(hashed_password.encode("utf-8")).hexdigest()[:16]


def _encode(claims: dict[str, Any], expires_delta: timedelta) -> str:
    now = datetime.now(timezone.utc)
    payload = {**claims, "iat": now, "exp": now + expires_delta}
    return jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)


def create_access_token(user_id: int, role: str, session_id: str) -> tuple[str, int]:
    """Return (token, lifetime_seconds). `session_id` ties the token to a refresh session."""
    lifetime = timedelta(minutes=settings.access_token_expire_minutes)
    token = _encode(
        {"sub": str(user_id), "type": ACCESS_TOKEN_TYPE, "role": role, "sid": session_id},
        lifetime,
    )
    return token, int(lifetime.total_seconds())


def create_refresh_token(user_id: int) -> tuple[str, str, datetime]:
    """Return (token, jti, expires_at)."""
    jti = uuid.uuid4().hex
    lifetime = timedelta(days=settings.refresh_token_expire_days)
    token = _encode({"sub": str(user_id), "type": REFRESH_TOKEN_TYPE, "jti": jti}, lifetime)
    return token, jti, datetime.now(timezone.utc) + lifetime


def create_password_reset_token(user_id: int, hashed_password: str) -> str:
    # Embedding the password fingerprint makes the token single-use: once the
    # password changes, the fingerprint no longer matches.
    return _encode(
        {
            "sub": str(user_id),
            "type": PASSWORD_RESET_TOKEN_TYPE,
            "pwd": password_fingerprint(hashed_password),
        },
        timedelta(minutes=settings.password_reset_token_expire_minutes),
    )


def decode_token(token: str, expected_type: str) -> dict[str, Any]:
    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.jwt_algorithm],
            options={"require": ["exp", "iat", "sub"]},
        )
    except jwt.ExpiredSignatureError as exc:
        raise AuthenticationError("Token has expired.") from exc
    except jwt.InvalidTokenError as exc:
        raise AuthenticationError("Invalid token.") from exc

    if payload.get("type") != expected_type:
        raise AuthenticationError("Invalid token type.")
    if not str(payload.get("sub", "")).isdigit():
        raise AuthenticationError("Invalid token subject.")
    return payload
