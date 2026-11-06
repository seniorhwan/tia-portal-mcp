"""
Tier 2: JSON-RPC Protocol Errors Tests.
Verifies version checks, missing fields, unknown methods, and invalid tool names.
"""

from tests.e2e.harness import McpTestCase, McpProtocolError


class TestRpcProtocolErrors(McpTestCase):
    """Tier 2: Protocol error handling."""

    def test_invalid_jsonrpc_version(self):
        """Verifies jsonrpc version other than '2.0' returns Invalid Request (-32600)."""
        raw = '{"jsonrpc": "1.0", "id": 1, "method": "initialize", "params": {}}'
        res = self.client.send_raw(raw)
        self.assertIn("error", res)
        self.assertEqual(res["error"].get("code"), -32600)

    def test_missing_method_field(self):
        """Verifies request missing 'method' returns Invalid Request (-32600)."""
        raw = '{"jsonrpc": "2.0", "id": 2, "params": {}}'
        res = self.client.send_raw(raw)
        self.assertIn("error", res)
        self.assertEqual(res["error"].get("code"), -32600)

    def test_unknown_method_name(self):
        """Verifies unrecognized method returns Method Not Found (-32601)."""
        with self.assertRaises(McpProtocolError) as ctx:
            self.client.send_request("non_existent_method_xyz", {})
        self.assertEqual(ctx.exception.code, -32601)

    def test_invalid_tool_call_name(self):
        """Verifies tools/call with unknown tool name returns error code (-32602)."""
        self.init_session()
        with self.assertRaises(McpProtocolError) as ctx:
            self.client.call_tool("invalid_unknown_tool_999", {})
        self.assertEqual(ctx.exception.code, -32602)

    def test_request_continuity_after_protocol_error(self):
        """Verifies server remains fully operational after a protocol error."""
        # 1. Trigger protocol error
        with self.assertRaises(McpProtocolError):
            self.client.send_request("broken_method", {})

        # 2. Subsequent valid request succeeds
        res = self.client.initialize()
        self.assertEqual(res.get("protocolVersion"), "2024-11-05")
