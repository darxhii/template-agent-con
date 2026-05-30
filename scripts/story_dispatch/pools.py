"""Per–agent-type concurrency caps (dynamic pooling → asyncio semaphores)."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

import asyncio

from .types import StoryMessage


class AgentPool:
    """Logical pool: at most `max_concurrent` concurrent Process(m) calls."""

    def __init__(self, max_concurrent: int) -> None:
        if max_concurrent < 1:
            raise ValueError("max_concurrent must be >= 1")
        self._sem = asyncio.Semaphore(max_concurrent)
        self.max_concurrent = max_concurrent

    @asynccontextmanager
    async def acquire(self) -> AsyncIterator[None]:
        await self._sem.acquire()
        try:
            yield
        finally:
            self._sem.release()


class PoolSet:
    """P from Algorithm 1: one pool per subagent role (+ monolith)."""

    def __init__(
        self,
        *,
        max_reporter: int,
        max_fact_checker: int,
        max_editor: int,
        max_publisher: int,
        max_pipeline_monolith: int,
    ) -> None:
        self.reporter = AgentPool(max_reporter)
        self.fact_checker = AgentPool(max_fact_checker)
        self.editor = AgentPool(max_editor)
        self.publisher = AgentPool(max_publisher)
        self.pipeline_monolith = AgentPool(max_pipeline_monolith)

    def pool_for(self, msg: StoryMessage) -> AgentPool:
        key = msg.pool_key()
        return {
            "reporter": self.reporter,
            "fact-checker": self.fact_checker,
            "editor": self.editor,
            "newsletter-publisher": self.publisher,
            "pipeline_monolith": self.pipeline_monolith,
        }[key]
