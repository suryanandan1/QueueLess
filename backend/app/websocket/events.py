"""Publish change events to WebSocket rooms after a request has committed.

Events carry only ids, never customer data: clients react by re-fetching the
resource through the authenticated REST API. Broadcasting runs as a FastAPI
background task, i.e. after the response is sent and the transaction committed.
"""

from fastapi import BackgroundTasks

from app.websocket.manager import business_room, manager, queue_room

QUEUE_UPDATED = "queue_updated"
APPOINTMENTS_UPDATED = "appointments_updated"


def queue_changed(tasks: BackgroundTasks, queue_id: int, business_id: int) -> None:
    payload = {"queue_id": queue_id}
    tasks.add_task(manager.broadcast, queue_room(queue_id), QUEUE_UPDATED, payload)
    tasks.add_task(manager.broadcast, business_room(business_id), QUEUE_UPDATED, payload)


def appointments_changed(tasks: BackgroundTasks, business_id: int) -> None:
    tasks.add_task(
        manager.broadcast, business_room(business_id), APPOINTMENTS_UPDATED, {"business_id": business_id}
    )
