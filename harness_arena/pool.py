"""Run async jobs a few at a time, starting them in the order given. If one fails, the rest are cancelled before the
error is raised, so nothing keeps writing records after the caller has stopped."""
from __future__ import annotations

import asyncio
from typing import Awaitable, Callable, Iterable


async def limited(workers: int, jobs: Iterable[Callable[[], Awaitable]]) -> list:
    sem = asyncio.Semaphore(workers)

    async def go(job):
        async with sem:
            return await job()
    tasks = [asyncio.ensure_future(go(j)) for j in jobs]
    try:
        return await asyncio.gather(*tasks)
    except BaseException:
        for t in tasks:
            t.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        raise
