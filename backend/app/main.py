import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.config import settings
from app.core.dependencies import DbSession
from app.core.exceptions import register_exception_handlers
from app.database import init_db
from app.middleware.request_context import RequestContextMiddleware
from app.routers import (
    admin,
    appointments,
    auth,
    businesses,
    counters,
    members,
    notifications,
    queues,
    services,
    tokens,
    users,
)
from app.websocket import routes as websocket_routes

logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    init_db()
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title=f"{settings.app_name} API",
        description="Virtual queue and appointment management for multi-business use.",
        version="1.0.0",
        lifespan=lifespan,
        openapi_url=f"{settings.api_v1_prefix}/openapi.json",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    app.add_middleware(RequestContextMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID"],
    )
    register_exception_handlers(app)

    for router in (
        auth.router,
        users.router,
        businesses.router,
        members.router,
        services.router,
        counters.router,
        queues.router,
        tokens.router,
        appointments.router,
        notifications.router,
        admin.router,
        websocket_routes.router,
    ):
        app.include_router(router, prefix=settings.api_v1_prefix)

    @app.get(f"{settings.api_v1_prefix}/health", tags=["Health"])
    def health_check(db: DbSession) -> dict[str, str]:
        db.execute(text("SELECT 1"))
        return {"status": "ok", "database": "ok"}

    return app


app = create_app()
