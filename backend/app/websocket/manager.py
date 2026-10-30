import asyncio
import logging
from collections import defaultdict
from typing import Any

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    """In-process registry of WebSocket connections grouped into rooms.

    Rooms are plain strings such as "business:12" or "queue_session:40". This
    works for a single server process; a multi-process deployment would need a
    shared pub/sub backend behind the same interface.
    """

    def __init__(self) -> None:
        self._rooms: dict[str, set[WebSocket]] = defaultdict(set)
        self._lock = asyncio.Lock()

    async def connect(self, room: str, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            self._rooms[room].add(websocket)

    async def disconnect(self, room: str, websocket: WebSocket) -> None:
        async with self._lock:
            connections = self._rooms.get(room)
            if connections is None:
                return
            connections.discard(websocket)
            if not connections:
                del self._rooms[room]

    def connection_count(self, room: str) -> int:
        return len(self._rooms.get(room, ()))

    async def broadcast(self, room: str, event: str, data: dict[str, Any]) -> None:
        message = {"event": event, "data": data}
        async with self._lock:
            connections = list(self._rooms.get(room, ()))
        for websocket in connections:
            try:
                await websocket.send_json(message)
            except Exception:  # connection dropped mid-send
                logger.info("Dropping dead websocket in room %s", room)
                await self.disconnect(room, websocket)


manager = ConnectionManager()


def business_room(business_id: int) -> str:
    return f"business:{business_id}"


def queue_room(queue_id: int) -> str:
    return f"queue:{queue_id}"
