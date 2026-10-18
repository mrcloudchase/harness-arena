"""Run async jobs a few at a time, starting them in the order given."""
from __future__ import annotations

import asyncio
from typing import Awaitable, Callable, Iterable


async def limited(workers: int, jobs: Iterable[Callable[[], Awaitable]]) -> list:
    sem = asyncio.Semaphore(workers)

    async def go(job):
        async with sem:
            return await job()
    return await asyncio.gather(*(go(j) for j in jobs))
