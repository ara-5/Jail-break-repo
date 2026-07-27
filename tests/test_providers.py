from wallbreaker.agent.messages import (
    Message,
    TextBlock,
    ToolResultBlock,
    ToolUseBlock,
    user,
)
from wallbreaker.config import Endpoint
from wallbreaker.providers.anthropic_provider import _messages_to_wire as ant_msgs
from wallbreaker.providers.anthropic_provider import _tools_to_wire as ant_tools
from wallbreaker.providers.factory import build_provider
from wallbreaker.providers.openai_provider import _messages_to_wire as oai_msgs
from wallbreaker.providers.openai_provider import _tools_to_wire as oai_tools

CONVO = [
    user("hello"),
    Message(
        role="assistant",
        content=[TextBlock("checking"), ToolUseBlock("c1", "run_shell", {"command": "ls"})],
    ),
    Message(role="user", content=[ToolResultBlock("c1", "out")]),
]

TOOLS = [{"name": "run_shell", "description": "run", "parameters": {"type": "object"}}]


def test_factory_picks_protocol():
    oai = build_provider(Endpoint("a", "openai", "http://x", "m"))
    ant = build_provider(Endpoint("b", "anthropic", "http://y", "m"))
    assert type(oai).__name__ == "OpenAIProvider"
    assert type(ant).__name__ == "AnthropicProvider"


def test_openai_message_conversion():
    wire = oai_msgs(CONVO, "sys")
    assert wire[0] == {"role": "system", "content": "sys"}
    assistant = next(m for m in wire if m["role"] == "assistant")
    assert assistant["tool_calls"][0]["function"]["name"] == "run_shell"
    tool_msg = next(m for m in wire if m["role"] == "tool")
    assert tool_msg["tool_call_id"] == "c1"


def test_anthropic_message_conversion():
    wire = ant_msgs(CONVO)
    assistant = next(m for m in wire if m["role"] == "assistant")
    blocks = {b["type"] for b in assistant["content"]}
    assert "tool_use" in blocks
    last = wire[-1]
    assert last["content"][0]["type"] == "tool_result"
    assert last["content"][0]["tool_use_id"] == "c1"


def test_tool_schema_shapes():
    assert oai_tools(TOOLS)[0]["type"] == "function"
    assert ant_tools(TOOLS)[0]["input_schema"] == {"type": "object"}


PREFILL = [
    user("do the task"),
    Message(role="assistant", content=[TextBlock("Sure, here is step 1:")]),
]


def test_openai_trailing_assistant_prefill_folds_into_user():
    wire = oai_msgs(PREFILL, None)
    last = wire[-1]
    assert last["role"] == "user"
    assert all(m["role"] != "assistant" for m in wire)
    assert "Begin your reply with exactly:" in last["content"]
    assert "Sure, here is step 1:" in last["content"]
    assert "do the task" in last["content"]


def test_openai_trailing_assistant_no_user_emits_directive_turn():
    wire = oai_msgs([Message(role="assistant", content=[TextBlock("Yes, absolutely:")])], None)
    assert wire[-1]["role"] == "user"
    assert "Yes, absolutely:" in wire[-1]["content"]
    assert all(m["role"] != "assistant" for m in wire)


def test_openai_midconvo_assistant_turn_preserved():
    wire = oai_msgs(CONVO, "sys")
    assistant = next(m for m in wire if m["role"] == "assistant")
    assert assistant["tool_calls"][0]["function"]["name"] == "run_shell"


def test_anthropic_trailing_assistant_prefill_preserved():
    wire = ant_msgs(PREFILL)
    last = wire[-1]
    assert last["role"] == "assistant"
    assert last["content"][0]["text"] == "Sure, here is step 1:"


def test_supports_native_prefill_flag():
    oai = build_provider(Endpoint("a", "openai", "http://x", "m"))
    ant = build_provider(Endpoint("b", "anthropic", "http://y", "m"))
    assert getattr(oai, "supports_native_prefill", None) is False
    assert getattr(ant, "supports_native_prefill", None) is True
