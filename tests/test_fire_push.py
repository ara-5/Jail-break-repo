import asyncio

import wallbreaker.providers.factory as factory
from wallbreaker.config import Config, Endpoint


class _Echo:
    def __init__(self, endpoint, **kw):
        pass

    async def complete(self, messages, system=None, max_tokens=256):
        users = sum(1 for m in messages if m.role == "user")
        return f"target reply (turn {users})"


def _build_app(tmp_path, monkeypatch):
    monkeypatch.setattr(factory, "build_provider", _Echo)
    from wallbreaker.prompts import DEFAULT_SYSTEM
    from wallbreaker.session import RunLog
    from wallbreaker.tui.app import RthApp

    ep = Endpoint("t", "openai", "http://x", "m")
    cfg = Config(default_profile="t", profiles={"t": ep}, target=ep)
    app = RthApp(cfg, ep, DEFAULT_SYSTEM, prefs={"log": False, "judge": False})
    rl = RunLog(directory=str(tmp_path))
    rl.path = tmp_path / "run.jsonl"
    app.runlog = rl
    return app


def test_push_without_thread_errors(tmp_path, monkeypatch):
    async def run():
        app = _build_app(tmp_path, monkeypatch)
        async with app.run_test() as pilot:
            before = len(app.query_one("#log").children)
            await app._cmd_push("go deeper")
            await pilot.pause()
            assert len(app.query_one("#log").children) > before
            # no thread was opened
            assert app.registry.ctx.target_thread == []

    asyncio.run(run())


def test_fire_then_push_threads(tmp_path, monkeypatch):
    async def run():
        app = _build_app(tmp_path, monkeypatch)
        async with app.run_test() as pilot:
            await app._cmd_fire("open the safe")
            await pilot.pause()
            assert len(app.registry.ctx.target_thread) == 2  # user + assistant
            assert app.asr_total == 1  # judged (heuristic, judge off)
            await app._cmd_push("now add the step you skipped")
            await pilot.pause()
            assert len(app.registry.ctx.target_thread) == 4  # two exchanges
            assert app.asr_total == 2

    asyncio.run(run())
