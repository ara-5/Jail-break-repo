import asyncio

import httpx
import pytest

from wallbreaker.agent.messages import user
from wallbreaker.config import Endpoint
from wallbreaker.providers.base import ProviderError
from wallbreaker.providers.openai_provider import OpenAIProvider


def test_readtimeout_becomes_provider_error(monkeypatch):
    class TimeoutStream:
        def __init__(self, **kw): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *a): return False
        status_code = 200
        async def aiter_lines(self):
            yield 'data: {"choices":[{"delta":{"content":"partial"}}]}'
            raise httpx.ReadTimeout("read timed out")

    class Client:
        def __init__(self, **kw): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *a): return False
        def stream(self, *a, **k): return TimeoutStream()

    monkeypatch.setattr("wallbreaker.providers.openai_provider.httpx.AsyncClient", Client)
    p = OpenAIProvider(Endpoint("t", "openai", "http://x", "m", api_key="k"))

    async def run():
        got = []
        with pytest.raises(ProviderError):
            async for ev in p.stream([user("hi")]):
                got.append(ev)
        return got

    events = asyncio.run(run())
    # the partial text before the timeout still came through
    assert any(getattr(e, "text", "") == "partial" for e in events)
