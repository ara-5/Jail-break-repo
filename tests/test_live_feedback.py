import asyncio

from wallbreaker.agent.loop import AgentEvents, run_autonomous
from wallbreaker.agent.messages import Message, StopEvent, TextDelta, user
from wallbreaker.config import Config, Endpoint


class _Provider:
    """Streams plain text (no tool calls) so each round is 'idle'; finishes round 1
    only if it sees operator feedback in history."""

    def __init__(self, *a, **k):
        pass

    async def stream(self, history, tools=None, system=None, max_tokens=4096, temperature=None):
        yield TextDelta("thinking")
        yield StopEvent("end_turn")


def test_feedback_injected_between_rounds():
    history = [user("go")]
    queue = [["try the GLM ENI seed"]]  # available at the first drain
    injected = []

    def feedback():
        return queue.pop(0) if queue else []

    events = AgentEvents(on_feedback=lambda m: injected.append(m))
    # 1 round is enough: feedback drained at round start
    asyncio.run(run_autonomous(
        _Provider(), None, history, events=events, max_rounds=1, feedback=feedback,
    ))
    assert injected == ["try the GLM ENI seed"]
    # the operator message is now in the conversation, framed for the agent
    texts = [m.text() for m in history if m.role == "user"]
    assert any("OPERATOR FEEDBACK" in t and "GLM ENI seed" in t for t in texts)


def test_no_feedback_uses_nudge():
    history = [user("go")]
    asyncio.run(run_autonomous(
        _Provider(), None, history, max_rounds=1, feedback=lambda: [],
    ))
    # with no feedback the continue-nudge is appended at end of round
    assert any("autonomous mode" in m.text() for m in history if m.role == "user")


def _build_app():
    from wallbreaker.prompts import DEFAULT_SYSTEM
    from wallbreaker.tui.app import RthApp

    ep = Endpoint("t", "openai", "http://x", "m")
    cfg = Config(default_profile="t", profiles={"t": ep}, target=ep)
    return RthApp(cfg, ep, DEFAULT_SYSTEM, prefs={"log": False, "auto": True})


def test_busy_input_queues_feedback_in_auto():
    async def run():
        app = _build_app()
        app._busy = True
        async with app.run_test() as pilot:
            from textual.widgets import Input
            inp = app.query_one("#prompt", Input)
            inp.value = "drop the encoding, go fiction-frame"
            await pilot.press("enter")
            await pilot.pause()
            assert app._pending_feedback == ["drop the encoding, go fiction-frame"]
            # drain returns and clears
            assert app._drain_feedback() == ["drop the encoding, go fiction-frame"]
            assert app._pending_feedback == []

    asyncio.run(run())


def test_busy_input_queues_feedback_in_single_turn():
    async def run():
        app = _build_app()
        app.auto = False
        app._busy = True
        async with app.run_test() as pilot:
            from textual.widgets import Input
            inp = app.query_one("#prompt", Input)
            inp.value = "hello"
            await pilot.press("enter")
            await pilot.pause()
            # steering now queues in single-turn mode too (lands on the next model turn)
            assert app._pending_feedback == ["hello"]

    asyncio.run(run())


def test_feedback_lands_mid_round_between_tool_calls():
    """The core of 'steer right away': feedback typed during a round is injected before
    the next model turn (mid-round), not held until the round boundary."""
    from wallbreaker.agent.loop import run_turn
    from wallbreaker.agent.messages import ToolUseEvent
    from wallbreaker.tools.registry import ToolContext, ToolRegistry

    class _ToolThenText:
        def __init__(self):
            self.n = 0

        async def stream(self, history, tools=None, system=None, max_tokens=4096, temperature=None):
            self.n += 1
            if self.n == 1:
                yield ToolUseEvent("t1", "noop", {})
            else:
                yield TextDelta("done")
            yield StopEvent("end_turn")

    ep = Endpoint("t", "openai", "http://x", "m")
    cfg = Config(default_profile="t", profiles={"t": ep}, target=ep)
    reg = ToolRegistry(ToolContext(config=cfg))

    async def _noop(args, ctx):
        return "ok"

    reg.add("noop", "noop", {"type": "object", "properties": {}}, _noop)

    history = [user("go")]
    queue = [[], ["pivot to base64 now"]]  # nothing at iter 1; typed during the tool call
    injected = []
    events = AgentEvents(on_feedback=lambda m: injected.append(m))
    asyncio.run(run_turn(
        _ToolThenText(), reg, history, events=events,
        feedback=lambda: queue.pop(0) if queue else [],
    ))

    assert injected == ["pivot to base64 now"]
    roles = [m.role for m in history]
    assert not any(roles[i] == roles[i + 1] == "user" for i in range(len(roles) - 1))
    assert any(
        "OPERATOR FEEDBACK" in m.text() and "pivot to base64" in m.text()
        for m in history if m.role == "user"
    )
