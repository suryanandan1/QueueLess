from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect, status
from sqlalchemy.orm import Session

from app.core.dependencies import authenticate_access_token
from app.core.exceptions import AppError
from app.database import get_db
from app.models import QueueSession
from app.services.access_control import has_business_role
from app.websocket.manager import business_room, manager, queue_room

router = APIRouter(tags=["WebSocket"])


@router.websocket("/ws/businesses/{business_id}")
async def business_events(
    websocket: WebSocket,
    business_id: int,
    token: str = Query(..., description="JWT access token"),
    db: Session = Depends(get_db),
) -> None:
    """Live event channel for members of a business.

    Browsers cannot set headers on WebSocket requests, so the access token is
    passed as a query parameter. Clients may send "ping" and receive "pong".
    """
    try:
        user, _session_id = authenticate_access_token(db, token)
        allowed = has_business_role(db, user, business_id)
    except AppError:
        allowed = False
    finally:
        # Release the DB connection; it is not needed while the socket stays open.
        db.close()

    if not allowed:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    room = business_room(business_id)
    await manager.connect(room, websocket)
    try:
        while True:
            message = await websocket.receive_text()
            if message == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        pass
    finally:
        await manager.disconnect(room, websocket)


@router.websocket("/ws/queues/{queue_id}")
async def queue_events(
    websocket: WebSocket, queue_id: int, db: Session = Depends(get_db)
) -> None:
    """Public channel announcing that a queue changed. It carries only the queue id,
    so subscribers learn nothing about other customers; they re-fetch via REST."""
    try:
        queue = db.get(QueueSession, queue_id)
        allowed = queue is not None and queue.business.is_active
    finally:
        db.close()
    if not allowed:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    room = queue_room(queue_id)
    await manager.connect(room, websocket)
    try:
        while True:
            if await websocket.receive_text() == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        pass
    finally:
        await manager.disconnect(room, websocket)
