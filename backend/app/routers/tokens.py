from fastapi import APIRouter, BackgroundTasks

from app.core.dependencies import CurrentUser, DbSession, PaginationParams
from app.schemas.common import Page
from app.schemas.queue import (
    CallTokenRequest,
    RecallTokenRequest,
    StaffTokenRead,
    TokenCancelRequest,
    TokenDetail,
    TokenRead,
)
from app.services import token_service
from app.websocket.events import queue_changed

router = APIRouter(prefix="/tokens", tags=["Tokens"])


def _published(tasks: BackgroundTasks, token):
    queue_changed(tasks, token.queue_session_id, token.business_id)
    return token


@router.get("", response_model=Page[TokenDetail], summary="My tokens (history)")
def list_my_tokens(db: DbSession, current_user: CurrentUser, pagination: PaginationParams,
                   active_only: bool = False):
    items, total = token_service.list_my_tokens(
        db, current_user, active_only, pagination.limit, pagination.offset
    )
    return Page(items=items, total=total, limit=pagination.limit, offset=pagination.offset)


@router.get("/{token_id}", response_model=TokenDetail, summary="Track a token")
def get_token(token_id: int, db: DbSession, current_user: CurrentUser):
    return token_service.get_token_for_viewer(db, current_user, token_id)


@router.post("/{token_id}/cancel", response_model=TokenRead)
def cancel_token(token_id: int, db: DbSession, current_user: CurrentUser, tasks: BackgroundTasks,
                 payload: TokenCancelRequest | None = None):
    reason = payload.reason if payload else None
    return _published(tasks, token_service.cancel_token(db, current_user, token_id, reason))


@router.post("/{token_id}/call", response_model=StaffTokenRead)
def call_token(token_id: int, payload: CallTokenRequest, db: DbSession, current_user: CurrentUser,
               tasks: BackgroundTasks):
    return _published(tasks, token_service.call_token(db, current_user, token_id, payload.counter_id))


@router.post("/{token_id}/recall", response_model=StaffTokenRead)
def recall_token(token_id: int, db: DbSession, current_user: CurrentUser, tasks: BackgroundTasks,
                 payload: RecallTokenRequest | None = None):
    counter_id = payload.counter_id if payload else None
    return _published(tasks, token_service.recall_token(db, current_user, token_id, counter_id))


@router.post("/{token_id}/start", response_model=StaffTokenRead)
def start_service(token_id: int, db: DbSession, current_user: CurrentUser, tasks: BackgroundTasks):
    return _published(tasks, token_service.start_service(db, current_user, token_id))


@router.post("/{token_id}/complete", response_model=StaffTokenRead)
def complete_service(token_id: int, db: DbSession, current_user: CurrentUser,
                     tasks: BackgroundTasks):
    return _published(tasks, token_service.complete_service(db, current_user, token_id))


@router.post("/{token_id}/skip", response_model=StaffTokenRead)
def skip_token(token_id: int, db: DbSession, current_user: CurrentUser, tasks: BackgroundTasks):
    return _published(tasks, token_service.skip_token(db, current_user, token_id))


@router.post("/{token_id}/no-show", response_model=StaffTokenRead)
def mark_no_show(token_id: int, db: DbSession, current_user: CurrentUser, tasks: BackgroundTasks):
    return _published(tasks, token_service.mark_no_show(db, current_user, token_id))
