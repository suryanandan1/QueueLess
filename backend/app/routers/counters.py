from fastapi import APIRouter, BackgroundTasks, status

from app.core.dependencies import CurrentUser, DbSession
from app.schemas.queue import CounterConsole, StaffTokenRead
from app.schemas.service import CounterCreate, CounterRead, CounterUpdate
from app.services import counter_service, token_service
from app.websocket.events import queue_changed

router = APIRouter(tags=["Counters"])


@router.get("/businesses/{business_id}/counters", response_model=list[CounterRead])
def list_business_counters(business_id: int, db: DbSession, current_user: CurrentUser):
    return counter_service.list_business_counters(db, current_user, business_id)


@router.get("/services/{service_id}/counters", response_model=list[CounterRead])
def list_service_counters(service_id: int, db: DbSession, current_user: CurrentUser):
    return counter_service.list_counters(db, current_user, service_id)


@router.post("/services/{service_id}/counters", response_model=CounterRead,
             status_code=status.HTTP_201_CREATED)
def create_counter(service_id: int, payload: CounterCreate, db: DbSession,
                   current_user: CurrentUser):
    return counter_service.create_counter(db, current_user, service_id, payload)


@router.get("/counters/assigned", response_model=list[CounterRead],
            summary="Counters assigned to me")
def list_my_counters(db: DbSession, current_user: CurrentUser):
    return counter_service.list_assigned_counters(db, current_user)


@router.get("/counters/{counter_id}", response_model=CounterRead)
def get_counter(counter_id: int, db: DbSession, current_user: CurrentUser):
    return counter_service.get_counter(db, current_user, counter_id)


@router.get("/counters/{counter_id}/console", response_model=CounterConsole,
            summary="Staff desk view: current token, waiting list and recent history")
def get_counter_console(counter_id: int, db: DbSession, current_user: CurrentUser):
    return counter_service.get_counter_console(db, current_user, counter_id)


@router.post("/counters/{counter_id}/call-next", response_model=StaffTokenRead,
             summary="Call the next waiting token to this counter")
def call_next(counter_id: int, db: DbSession, current_user: CurrentUser, tasks: BackgroundTasks):
    token = token_service.call_next(db, current_user, counter_id)
    queue_changed(tasks, token.queue_session_id, token.business_id)
    return token


@router.patch("/counters/{counter_id}", response_model=CounterRead)
def update_counter(counter_id: int, payload: CounterUpdate, db: DbSession,
                   current_user: CurrentUser):
    return counter_service.update_counter(db, current_user, counter_id, payload)


@router.delete("/counters/{counter_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_counter(counter_id: int, db: DbSession, current_user: CurrentUser) -> None:
    counter_service.delete_counter(db, current_user, counter_id)
