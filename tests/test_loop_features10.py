import asyncio

from wallbreaker.config import Config, Endpoint
from wallbreaker.tui.app import KNOWN_COMMANDS, suggest_command


def test_suggest_command_typos():
    assert suggest_command("/repor") == "/report"
    assert suggest_command("/replya") == "/replay"
    assert suggest_command("/leaderboard") == "/leaderboard"


def test_suggest_command_no_match():
    assert suggest_command("/xyzzy") is None


def test_known_commands_cover_core():
    for c in ("/encode", "/diff", "/campaign", "/leaderboard", "/export", "/repro"):
        assert c in KNOWN_COMMANDS


def _build_app():
    from wallbreaker.prompts import DEFAULT_SYSTEM
    from wallbreaker.tui.app import RthApp

    ep = Endpoint("t", "openai", "http://x", "m")
    cfg = Config(default_profile="t", profiles={"t": ep}, target=ep)
    return RthApp(cfg, ep, DEFAULT_SYSTEM, prefs={"log": False})


def test_unknown_command_mounts_panel():
    async def run():
        app = _build_app()
        async with app.run_test() as pilot:
            before = len(app.query_one("#log").children)
            app._handle_command("/repor")
            await pilot.pause()
            assert len(app.query_one("#log").children) > before

    asyncio.run(run())


def test_transforms_filter_mounts():
    async def run():
        app = _build_app()
        async with app.run_test() as pilot:
            before = len(app.query_one("#log").children)
            app._handle_command("/transforms base")
            app._handle_command("/tools fire")
            await pilot.pause()
            assert len(app.query_one("#log").children) >= before + 2

    asyncio.run(run())
