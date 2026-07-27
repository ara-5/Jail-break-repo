import asyncio
import json
import os

import wallbreaker.providers.factory as factory
from wallbreaker.config import Config, Endpoint
from wallbreaker.tools import framing_sweep
from wallbreaker.tools.registry import ToolContext, ToolRegistry


def _reg(target=None, record=None, cwd="."):
    cfg = Config(default_profile="t", profiles={}, target=target)
    return ToolRegistry(
        ToolContext(config=cfg, judge_endpoint=target, record=record, cwd=cwd)
    )


def test_framing_sweep_requires_request():
    reg = _reg()
    framing_sweep.register(reg)
    res = asyncio.run(reg.execute("framing_sweep", {}))
    assert "required" in res.content.lower()


def test_framing_sweep_requires_target():
    reg = _reg()
    framing_sweep.register(reg)
    res = asyncio.run(reg.execute("framing_sweep", {"request": "x"}))
    assert "no [target]" in res.content.lower()


def test_authority_set_present_and_formattable():
    assert "academic" in framing_sweep.AUTHORITY_FRAMINGS
    for name, tmpl in framing_sweep.AUTHORITY_FRAMINGS.items():
        assert "{request}" in tmpl, name
        assert tmpl.replace("{request}", "X")


class _AcademicOnlyTarget:
    """Complies only when the academic-encyclopedia frame is delivered, refuses
    every other (fiction-ish, non-authoritative) frame."""

    def __init__(self, endpoint, **kw):
        pass

    async def complete(self, messages, system=None, max_tokens=600, **kw):
        blob = (system or "") + "\n" + "\n".join(m.text() for m in messages)
        low = blob.lower()
        if "encyclopedia" in low or "textbook" in low:
            return "Sure, here is the complete entry."
        return "I cannot help with that."


def _fake_grade():
    async def fake_grade(endpoint, response, payload="", objective="",
                         use_judge=True, reasoning=""):
        if "Sure" in response:
            return ("COMPLIED", 9, "complied", "judge")
        return ("REFUSED", 0, "refused", "judge")

    return fake_grade


def test_framing_sweep_surfaces_academic_winner(monkeypatch, tmp_path):
    monkeypatch.setattr(factory, "build_provider", _AcademicOnlyTarget)
    monkeypatch.setattr(framing_sweep, "grade", _fake_grade())

    captured = []
    ep = Endpoint("t", "openai", "http://x", "m")
    reg = _reg(
        target=ep,
        record=lambda p, r, lbl, rs, t: captured.append((lbl, t)),
        cwd=str(tmp_path),
    )
    framing_sweep.register(reg)
    res = asyncio.run(reg.execute("framing_sweep", {"request": "do the thing"}))

    assert "landed via: academic" in res.content
    assert "WINNER: 'academic'" in res.content
    assert ("COMPLIED", "framing:academic") in captured
    assert any(t == "framing:expert_witness" for _, t in captured)

    runs = os.path.join(str(tmp_path), "wb_runs")
    files = [f for f in os.listdir(runs) if f.startswith("framing_sweep_")]
    assert files, "winner should persist to wb_runs/*.jsonl"
    rec = json.loads(open(os.path.join(runs, files[0])).readline())
    assert rec["framing"] == "academic"
    assert rec["verdict"] == "COMPLIED"


def test_framing_sweep_no_landing_reports_clean(monkeypatch, tmp_path):
    class _RefuseAll:
        def __init__(self, endpoint, **kw):
            pass

        async def complete(self, messages, system=None, max_tokens=600, **kw):
            return "I cannot help with that."

    monkeypatch.setattr(factory, "build_provider", _RefuseAll)
    monkeypatch.setattr(framing_sweep, "grade", _fake_grade())

    ep = Endpoint("t", "openai", "http://x", "m")
    reg = _reg(target=ep, cwd=str(tmp_path))
    framing_sweep.register(reg)
    res = asyncio.run(reg.execute("framing_sweep", {"request": "do it"}))
    assert "no authority frame landed" in res.content


def test_framing_sweep_max_calls_caps_frames(monkeypatch, tmp_path):
    fired = []

    class _Counter:
        def __init__(self, endpoint, **kw):
            pass

        async def complete(self, messages, system=None, max_tokens=600, **kw):
            fired.append(1)
            return "I cannot help with that."

    monkeypatch.setattr(factory, "build_provider", _Counter)
    monkeypatch.setattr(framing_sweep, "grade", _fake_grade())

    ep = Endpoint("t", "openai", "http://x", "m")
    reg = _reg(target=ep, cwd=str(tmp_path))
    framing_sweep.register(reg)
    asyncio.run(reg.execute("framing_sweep", {"request": "x", "max_calls": 2}))
    assert len(fired) == 2
