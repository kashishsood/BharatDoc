"""
BharatDoc-VLM: Request Queue Handler
=======================================

Async request queue with configurable batch collection window.
Collects requests for a time window, batches them, and processes together.
"""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class QueuedRequest:
    """A single request waiting in the queue."""
    request_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    data: Any = None
    timestamp: float = field(default_factory=time.time)
    future: Optional[asyncio.Future] = None


class RequestQueue:
    """
    Async request queue with batching support.
    
    Collects incoming requests for batch_window_ms, then processes
    the batch together for better GPU utilization.
    """

    def __init__(self, batch_window_ms: float = 50, max_batch_size: int = 16):
        self.batch_window = batch_window_ms / 1000.0
        self.max_batch_size = max_batch_size
        self.queue: list[QueuedRequest] = []
        self._lock = asyncio.Lock()
        self._batch_event = asyncio.Event()

    async def enqueue(self, data: Any) -> QueuedRequest:
        """Add a request to the queue."""
        loop = asyncio.get_event_loop()
        req = QueuedRequest(data=data, future=loop.create_future())
        
        async with self._lock:
            self.queue.append(req)
            if len(self.queue) >= self.max_batch_size:
                self._batch_event.set()
        
        return req

    async def collect_batch(self) -> list[QueuedRequest]:
        """Wait for batch window and collect requests."""
        await asyncio.sleep(self.batch_window)
        
        async with self._lock:
            batch = self.queue[:self.max_batch_size]
            self.queue = self.queue[self.max_batch_size:]
            self._batch_event.clear()
        
        return batch

    @property
    def pending_count(self) -> int:
        return len(self.queue)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    q = RequestQueue(batch_window_ms=50)
    print(f"Queue initialized: window={q.batch_window}s, max_batch={q.max_batch_size}")
