"""
Exception types for MCP E2E test harness.
"""


class McpTestError(Exception):
    """Base exception for all MCP testing errors."""
    pass


class McpTimeoutError(McpTestError):
    """Raised when an MCP operation or response read times out."""
    pass


class McpProcessError(McpTestError):
    """Raised when the server process terminates unexpectedly or fails to launch."""
    pass


class McpProtocolError(McpTestError):
    """Raised when a JSON-RPC 2.0 error object is returned by the server."""

    def __init__(self, code: int, message: str, data=None, response_id=None):
        self.code = code
        self.message = message
        self.data = data
        self.response_id = response_id
        super().__init__(f"JSON-RPC Error {code}: {message} (id={response_id}, data={data})")
