"""A minimal stdio MCP server used by tests/test_mcp_bridge.py.

Not a test module (underscore prefix keeps pytest from collecting it). Run as a script:
    python tests/_stub_mcp_server.py
"""

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("stub", log_level="WARNING")


@mcp.tool()
def echo(text: str) -> str:
    """Echo the input text back, prefixed with 'echo:'."""
    return f"echo:{text}"


@mcp.tool()
def add(a: int, b: int) -> str:
    """Add two integers and return the sum as a string."""
    return str(a + b)


if __name__ == "__main__":
    mcp.run(transport="stdio")
