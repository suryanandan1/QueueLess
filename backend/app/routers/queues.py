from fastapi import APIRouter, BackgroundTasks, status

from app.core.dependencies import CurrentUser, DbSession, OptionalUser, PaginationParams
from app.schemas.common import Page
from app.schemas.queue import (
    QueueOpenRequest,
    QueueSessionRead,
    QueueSummary,
    QueueUpdate,
    StaffTokenRead,
    TokenDetail,
    WalkInCreate,
)
from app.services import queue_service
from app.websocket.events import queue_changed

router = APIRouter(tags=["Queues"])


def _summary_and_publish(db, tasks: BackgroundTasks, queue) -> QueueSummary:
    queue_changed(tasks, queue.id, queue.business_id)
    return queue_service.build_summary(db, queue)


@router.get("/queues", response_model=list[QueueSummary], summary="Today's active queues (public)")
def list_active_queues(db: DbSession, business_id: int | None = None, service_id: int | None = None):
    return queue_service.list_active_queues(db, business_id, service_id)


@router.post("/queues", response_model=QueueSummary, status_code=status.HTTP_201_CREATED,
             summary="Open (or reopen) today's queue for a service")
def open_queue(payload: QueueOpenRequest, db: DbSession, current_user: CurrentUser,
               tasks: BackgroundTasks):
    queue = queue_service.open_queue(db, current_user, payload.service_id, payload.max_capacity)
    return _summary_and_publish(db, tasks, queue)


@router.get("/queues/{queue_id}", response_model=QueueSummary, summary="Public queue status")
def get_queue(queue_id: int, db: DbSession, viewer: OptionalUser):
    return queue_service.get_queue_summary(db, viewer, queue_id)


@router.patch("/queues/{queue_id}", response_model=QueueSummary)
def update_queue(queue_id: int, payload: QueueUpdate, db: DbSession, current_user: CurrentUser,
                 tasks: BackgroundTasks):
    queue = queue_service.update_queue(db, current_user, queue_id, payload.max_capacity)
    return _summary_and_publish(db, tasks, queue)


@router.post("/queues/{queue_id}/pause", response_model=QueueSummary)
def pause_queue(queue_id: int, db: DbSession, current_user: CurrentUser, tasks: BackgroundTasks):
    return _summary_and_publish(db, tasks, queue_service.pause_queue(db, current_user, queue_id))


@router.post("/queues/{queue_id}/resume", response_model=QueueSummary)
def resume_queue(queue_id: int, db: DbSession, current_user: CurrentUser, tasks: BackgroundTasks):
    return _summary_and_publish(db, tasks, queue_service.resume_queue(db, current_user, queue_id))


@router.post("/queues/{queue_id}/close", response_model=QueueSummary)
def close_queue(queue_id: int, db: DbSession, current_user: CurrentUser, tasks: BackgroundTasks):
    return _summary_and_publish(db, tasks, queue_service.close_queue(db, current_user, queue_id))


@router.post("/queues/{queue_id}/join", response_model=TokenDetail,
             status_code=status.HTTP_201_CREATED, summary="Join a queue and receive a token")
def join_queue(queue_id: int, db: DbSession, current_user: CurrentUser, tasks: BackgroundTasks):
    token = queue_service.join_queue(db, current_user, queue_id)
    queue_changed(tasks, token.queue_session_id, token.business_id)
    return token


@router.post("/queues/{queue_id}/walk-ins", response_model=TokenDetail,
             status_code=status.HTTP_201_CREATED, summary="Issue a token to a walk-in customer")
def add_walk_in(queue_id: int, payload: WalkInCreate, db: DbSession, current_user: CurrentUser,
                tasks: BackgroundTasks):
    token = queue_service.add_walk_in(db, current_user, queue_id, payload)
    queue_changed(tasks, token.queue_session_id, token.business_id)
    return token


@router.get("/queues/{queue_id}/tokens", response_model=list[StaffTokenRead],
            summary="All tokens in a queue (business staff)")
def list_queue_tokens(queue_id: int, db: DbSession, current_user: CurrentUser):
    return queue_service.list_session_tokens(db, current_user, queue_id)


@router.get("/businesses/{business_id}/queues", response_model=Page[QueueSessionRead],
            summary="Current and previous queue sessions of a business")
def list_business_queues(business_id: int, db: DbSession, current_user: CurrentUser,
                         pagination: PaginationParams, include_closed: bool = True):
    items, total = queue_service.list_business_sessions(
        db, current_user, business_id, include_closed, pagination.limit, pagination.offset
    )
    return Page(items=items, total=total, limit=pagination.limit, offset=pagination.offset)
