"""The loop core: it stops on a named state, and an error or a spent budget is never success."""
import asyncio

from harness_arena.loop import Check, Loop


async def run(checks, rounds=3, seconds=None):
    told = []
    results = iter(checks)

    async def step(n, feedback):
        told.append((n, feedback))
    loop = Loop(step, lambda: asyncio.sleep(0, next(results)), rounds, seconds)
    return await loop.run(), told


async def test_success_stops_at_once():
    result, told = await run([Check(False, "a"), Check(True)])
    assert (result.state, result.rounds) == ("success", 2) and told == [(1, ""), (2, "a")]      # the failure is fed back


async def test_the_same_failure_twice_is_stalled():
    result, _ = await run([Check(False, "a"), Check(False, "b"), Check(False, "a")], rounds=5)
    assert result.state == "stalled" and result.rounds == 3


async def test_blocked_means_iterating_cannot_help():
    result, told = await run([Check(False, "needs a human", blocked=True)])
    assert result.state == "blocked" and result.why == "needs a human" and len(told) == 1


async def test_running_out_of_rounds_is_exhausted_not_success():
    result, _ = await run([Check(False, "a"), Check(False, "b"), Check(False, "c")], rounds=3)
    assert result.state == "exhausted"


async def test_running_out_of_time_is_exhausted():
    result, _ = await run([Check(False, "a"), Check(False, "b")], rounds=5, seconds=-1)
    assert result.state == "exhausted" and "time" in result.why
