import logging
import time
import uuid
from contextvars import ContextVar

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger("queueless.requests")

_client_ip: ContextVar[str | None] = ContextVar("client_ip", default=None)
_request_id: ContextVar[str | None] = ContextVar("request_id", default=None)


def get_client_ip() -> str | None:
    return _client_ip.get()


def get_request_id() -> str | None:
    return _request_id.get()


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Assigns a request id, records the client IP for audit logs and logs timing."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex
        ip_token = _client_ip.set(request.client.host if request.client else None)
        id_token = _request_id.set(request_id)
        started = time.perf_counter()
        try:
            response = await call_next(request)
        finally:
            _client_ip.reset(ip_token)
            _request_id.reset(id_token)

        duration_ms = (time.perf_counter() - started) * 1000
        response.headers["X-Request-ID"] = request_id
        logger.info(
            "%s %s -> %s (%.1f ms) [%s]",
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
            request_id,
        )
        return response
