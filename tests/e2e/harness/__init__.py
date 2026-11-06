"""
Test harness modules for TIA Portal MCP server black-box testing.
"""

from .errors import McpTestError, McpTimeoutError, McpProtocolError, McpProcessError
from .config import ServerConfig, resolve_server_command
from .client import McpClient
from .base_test import McpTestCase
from .assertions import (
    assert_jsonrpc_success,
    assert_jsonrpc_error,
    assert_mcp_tool_result,
    assert_clean_stdout,
    assert_tool_in_list,
    assert_tool_not_in_list,
)

__all__ = [
    "McpTestError",
    "McpTimeoutError",
    "McpProtocolError",
    "McpProcessError",
    "ServerConfig",
    "resolve_server_command",
    "McpClient",
    "McpTestCase",
    "assert_jsonrpc_success",
    "assert_jsonrpc_error",
    "assert_mcp_tool_result",
    "assert_clean_stdout",
    "assert_tool_in_list",
    "assert_tool_not_in_list",
]
