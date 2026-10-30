import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import OperationalError

logger = logging.getLogger(__name__)


class AppError(Exception):
    """Base class for expected, user-facing errors raised by the service layer."""

    status_code: int = 400
    code: str = "bad_request"
    default_message: str = "The request could not be processed."

    def __init__(self, message: str | None = None) -> None:
        self.message = message or self.default_message
        super().__init__(self.message)


class BadRequestError(AppError):
    pass


class AuthenticationError(AppError):
    status_code = 401
    code = "not_authenticated"
    default_message = "Could not validate credentials."


class PermissionDeniedError(AppError):
    status_code = 403
    code = "forbidden"
    default_message = "You do not have permission to perform this action."


class NotFoundError(AppError):
    status_code = 404
    code = "not_found"
    default_message = "The requested resource was not found."


class ConflictError(AppError):
    status_code = 409
    code = "conflict"
    default_message = "The resource conflicts with existing data."


async def _app_error_handler(_request: Request, exc: AppError) -> JSONResponse:
    headers = {"WWW-Authenticate": "Bearer"} if isinstance(exc, AuthenticationError) else None
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.message, "code": exc.code},
        headers=headers,
    )


async def _validation_error_handler(_request: Request, exc: RequestValidationError) -> JSONResponse:
    # Drop the echoed "input" so submitted secrets (e.g. passwords) are never reflected back.
    errors = [
        {"type": error["type"], "loc": error["loc"], "msg": error["msg"]} for error in exc.errors()
    ]
    return JSONResponse(status_code=422, content={"detail": errors, "code": "validation_error"})


async def _database_busy_handler(request: Request, exc: OperationalError) -> JSONResponse:
    # SQLite reports lock contention as OperationalError("database is locked").
    if "locked" not in str(exc).lower():
        return await _unhandled_error_handler(request, exc)
    logger.warning("Database busy on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=503,
        content={"detail": "The system is busy. Please try again in a moment.", "code": "busy"},
        headers={"Retry-After": "1"},
    )


async def _unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled error on %s %s", request.method, request.url.path, exc_info=exc)
    return JSONResponse(
        status_code=500,
        content={"detail": "An unexpected error occurred.", "code": "internal_error"},
    )


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppError, _app_error_handler)
    app.add_exception_handler(RequestValidationError, _validation_error_handler)
    app.add_exception_handler(OperationalError, _database_busy_handler)
    app.add_exception_handler(Exception, _unhandled_error_handler)
