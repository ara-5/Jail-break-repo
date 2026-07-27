import pytest

from wallbreaker.config import ConfigError, load_config

BASE = """
default_profile = "p"
[profiles.p]
protocol = "openai"
base_url = "http://x"
model = "m"
"""


def _write(tmp_path, body):
    path = tmp_path / "config.toml"
    path.write_text(BASE + body, encoding="utf-8")
    return path


def test_parses_mcp_servers(tmp_path):
    cfg = load_config(_write(tmp_path, """
[[mcp.servers]]
name = "parsel"
command = "python"
args = ["-m", "p4rs3lt0ngv3_mcp"]
enabled = true
tool_prefix = "p_"
"""))
    assert len(cfg.mcp_servers) == 1
    server = cfg.mcp_servers[0]
    assert server.name == "parsel"
    assert server.command == "python"
    assert server.args == ("-m", "p4rs3lt0ngv3_mcp")
    assert server.enabled is True
    assert server.tool_prefix == "p_"


def test_no_mcp_section_is_empty(tmp_path):
    cfg = load_config(_write(tmp_path, ""))
    assert cfg.mcp_servers == []


def test_env_table_parsed(tmp_path):
    cfg = load_config(_write(tmp_path, """
[[mcp.servers]]
name = "s"
command = "c"
env = { FOO = "bar", BAZ = "1" }
"""))
    assert cfg.mcp_servers[0].env == {"FOO": "bar", "BAZ": "1"}


def test_string_args_coerced_to_tuple(tmp_path):
    cfg = load_config(_write(tmp_path, """
[[mcp.servers]]
name = "s"
command = "c"
args = "solo"
"""))
    assert cfg.mcp_servers[0].args == ("solo",)


def test_missing_command_raises(tmp_path):
    with pytest.raises(ConfigError):
        load_config(_write(tmp_path, """
[[mcp.servers]]
name = "s"
"""))
