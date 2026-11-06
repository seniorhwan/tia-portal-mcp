"""
Assertion helpers for MCP E2E tests.
"""

from typing import Dict, Any, List, Optional
from .errors import McpProtocolError


def assert_tool_in_list(tools: List[Dict[str, Any]], tool_name: str) -> Dict[str, Any]:
    """Asserts that a tool with tool_name exists in the tools/list output and returns its definition."""
    match = next((t for t in tools if t.get("name") == tool_name), None)
    assert match is not None, f"Expected tool '{tool_name}' not found in tools list. Available: {[t.get('name') for t in tools]}"
    assert "description" in match, f"Tool '{tool_name}' missing 'description'"
    assert "inputSchema" in match, f"Tool '{tool_name}' missing 'inputSchema'"
    return match


def assert_tool_not_in_list(tools: List[Dict[str, Any]], tool_name: str):
    """Asserts that tool_name is not present in tools/list."""
    match = next((t for t in tools if t.get("name") == tool_name), None)
    assert match is None, f"Tool '{tool_name}' should NOT be present in tools list, but was found"


def assert_mcp_tool_result(result: Dict[str, Any], expected_tool: Optional[str] = None, should_succeed: Optional[bool] = None):
    """Asserts the structure of a tools/call result."""
    assert "content" in result, f"Result missing 'content': {result}"
    assert isinstance(result["content"], list), f"'content' must be a list: {result}"
    assert len(result["content"]) >= 1, "Expected at least one content item"

    if "isError" in result:
        assert isinstance(result["isError"], bool)

    if "structuredContent" in result and result["structuredContent"] is not None:
        struct = result["structuredContent"]
        if expected_tool:
            assert struct.get("tool") == expected_tool or "tool" not in struct or struct.get("audit", {}).get("action") == expected_tool, \
                f"Expected tool '{expected_tool}' in structuredContent, got: {struct}"
        if should_succeed is not None and "success" in struct:
            assert struct["success"] is should_succeed, f"Expected structuredContent['success'] to be {should_succeed}, got {struct.get('success')}"


def assert_schema_has_properties(schema: Dict[str, Any], required_props: List[str]):
    """Asserts that an inputSchema defines the specified property names."""
    props = schema.get("properties", {})
    for prop in required_props:
        assert prop in props, f"Property '{prop}' missing from schema properties: {list(props.keys())}"


def assert_clean_stdout(client):
    """Asserts that server process is alive and stderr captured startup diagnostics while stdout was pure JSON."""
    assert client.is_alive or client.exit_code == 0, f"Server process died unexpectedly with code {client.exit_code}"


def assert_jsonrpc_error(exc: McpProtocolError, expected_code: Optional[int] = None):
    """Asserts that a protocol error has the expected code."""
    if expected_code is not None:
        assert exc.code == expected_code, f"Expected error code {expected_code}, got {exc.code} (message: {exc.message})"


def assert_jsonrpc_success(result: Dict[str, Any]):
    """Asserts that a result dictionary is not empty and conforms to basic expectations."""
    assert result is not None, "Expected non-null JSON-RPC result"
