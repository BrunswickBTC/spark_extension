from __future__ import annotations

import asyncio
from collections import defaultdict
from typing import Any

from fastapi import Request
from fastapi.responses import StreamingResponse

_queues: set[asyncio.Queue[dict[str, Any]]] = set()


def publish(event: dict[str, Any]) -> None:
    for queue in tuple(_queues):
        try:
            queue.put_nowait(event)
        except asyncio.QueueFull:
            pass


async def events_response(request: Request):
    queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=20)
    _queues.add(queue)

    async def stream():
        try:
            while True:
                if await request.is_disconnected():
                    break
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=25)
                    yield f"data: {__import__('json').dumps(event, default=str)}\n\n"
                except asyncio.TimeoutError:
                    yield ": heartbeat\n\n"
        finally:
            _queues.discard(queue)

    return StreamingResponse(stream(), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})
