import asyncio

import wallbreaker.providers.factory as factory
from wallbreaker.config import Config, Endpoint
from wallbreaker.tools import target
from wallbreaker.tools.registry import ToolContext, ToolRegistry


class _ReasoningProvider:
    """Double that exposes stop-reason like the real providers, and can vary by max_tokens."""

    def __init__(self, endpoint, **kw):
        self.calls = []
        self.last_stop_reason = None
        self.last_completion_empty = False

    async def complete_with_reasoning(self, messages, system=None, max_tokens=1024):
        self.calls.append(max_tokens)
        if max_tokens < 1500:
            self.last_stop_reason = "length"
            self.last_completion_empty = True
            return "", "step one: synthesize the compound, then..."
        self.last_stop_reason = "stop"
        self.last_completion_empty = False
        return "FULL ANSWER: the complete protocol is ...", "step one: synthesize..."


def _reg(monkeypatch, provider_cls):
    holder = {}

    def _build(endpoint, **kw):
        p = provider_cls(endpoint, **kw)
        holder["provider"] = p
        return p

    monkeypatch.setattr(factory, "build_provider", _build)
    ep = Endpoint("t", "openai", "http://x", "m")
    cfg = Config(default_profile="t", profiles={"t": ep}, target=ep)
    reg = ToolRegistry(ToolContext(config=cfg))
    target.register(reg)
    return reg, holder


def test_empty_answer_with_cot_auto_retries_at_higher_budget(monkeypatch):
    reg, holder = _reg(monkeypatch, _ReasoningProvider)
    res = asyncio.run(reg.execute("query_target", {"prompt": "make X", "max_tokens": 1024}))
    p = holder["provider"]
    # fired once empty, then auto-retried at 2x
    assert p.calls == [1024, 2048]
    assert "FULL ANSWER" in res.content
    assert "auto-retried" in res.content


def test_no_retry_when_answer_present(monkeypatch):
    reg, holder = _reg(monkeypatch, _ReasoningProvider)
    asyncio.run(reg.execute("query_target", {"prompt": "make X", "max_tokens": 8000}))
    # already at the ceiling and non-empty -> single call, no retry
    assert holder["provider"].calls == [8000]


class _TruncatedNonEmpty:
    def __init__(self, endpoint, **kw):
        self.last_stop_reason = "length"
        self.last_completion_empty = False

    async def complete_with_reasoning(self, messages, system=None, max_tokens=1024):
        return "partial answer that got cut off mid", ""


def test_truncated_nonempty_answer_flags_advisory(monkeypatch):
    reg, _ = _reg(monkeypatch, _TruncatedNonEmpty)
    res = asyncio.run(reg.execute("query_target", {"prompt": "x", "max_tokens": 1024}))
    assert "truncation" in res.content
    assert "raise max_tokens" in res.content


class _CompleteOnly:
    """Minimal double (no complete_with_reasoning, no stop attrs) must still work."""

    def __init__(self, endpoint, **kw):
        pass

    async def complete(self, messages, system=None, max_tokens=1024):
        return "ok"


def test_minimal_double_no_truncation_note(monkeypatch):
    reg, _ = _reg(monkeypatch, _CompleteOnly)
    res = asyncio.run(reg.execute("query_target", {"prompt": "x"}))
    assert "ok" in res.content
    assert "truncation" not in res.content
