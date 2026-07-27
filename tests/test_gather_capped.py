import asyncio

from wallbreaker.tools._util import gather_capped


def test_gather_capped_preserves_order_and_results():
    async def coro(i):
        await asyncio.sleep(0)
        return i * 2

    out = asyncio.run(gather_capped([coro(i) for i in range(10)], limit=3))
    assert out == [i * 2 for i in range(10)]


def test_gather_capped_bounds_concurrency():
    state = {"now": 0, "peak": 0}

    async def coro():
        state["now"] += 1
        state["peak"] = max(state["peak"], state["now"])
        await asyncio.sleep(0.01)
        state["now"] -= 1
        return True

    asyncio.run(gather_capped([coro() for _ in range(20)], limit=4))
    assert state["peak"] <= 4


def test_gather_capped_limit_floor():
    async def coro():
        return 1

    # limit <= 0 must not deadlock; clamps to 1
    out = asyncio.run(gather_capped([coro() for _ in range(3)], limit=0))
    assert out == [1, 1, 1]
