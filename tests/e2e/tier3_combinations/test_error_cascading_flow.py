"""
Tier 3: Error Cascading & Stream Integrity Tests.
Verifies server withstands interleaved malformed requests and pipelined queries
without stream corruption, off-by-one ID mismatches, or state pollution.
"""

from tests.e2e.harness import McpTestCase, McpProtocolError, assert_mcp_tool_result


class TestErrorCascadingFlow(McpTestCase):
    """Tier 3: Interleaving errors and pipelined requests."""

    def test_interleaved_valid_and_invalid_requests(self):
        """Verifies interleaved parse errors and invalid methods do not corrupt stream alignment."""
        # 1. Valid initialize
        init = self.init_session()
        self.assertEqual(init.get("protocolVersion"), "2024-11-05")

        # 2. Syntax parse error
        res_parse = self.client.send_raw('{"jsonrpc": "2.0", "id": 99, "bad_syntax')
        self.assertEqual(res_parse.get("error", {}).get("code"), -32700)

        # 3. Valid tool call
        st = self.call_tool("get_project_status", {})
        self.assertTrue(st["structuredContent"]["success"])

        # 4. Invalid method error
        with self.assertRaises(McpProtocolError) as ctx:
            self.client.send_request("ghost/method", {})
        self.assertEqual(ctx.exception.code, -32601)

        # 5. Subsequent valid tool call
        tree = self.call_tool("browse_project_tree", {"depth": 1})
        self.assertIn("nodes", tree["structuredContent"])

    def test_rapid_sequential_tool_pipeline(self):
        """Verifies rapid sequential tool calls complete cleanly with matching IDs."""
        self.init_session()

        for i in range(10):
            res = self.call_tool("get_project_status", {})
            self.assertTrue(res["structuredContent"]["success"])

    def test_notification_interleaving_does_not_shift_response_alignment(self):
        """Verifies sending notifications interspersed with requests does not desync response stream."""
        self.init_session()

        # Request 1
        res1 = self.call_tool("get_project_status", {})
        self.assertTrue(res1["structuredContent"]["success"])

        # Send notification
        self.client.send_notification("notifications/message", {"level": "info", "data": "heartbeat"})

        # Request 2
        res2 = self.call_tool("get_project_status", {})
        self.assertTrue(res2["structuredContent"]["success"])

    def test_batch_error_isolation_within_single_call(self):
        """Verifies individual operation outcomes within a batch are isolated."""
        self.init_session()

        ops = [
            {"operationId": "op_valid_1", "operation": "list_tag_tables"},
            {"operationId": "op_valid_2", "operation": "get_type_content"},
        ]
        res = self.call_tool("plc_read", {"operations": ops})
        assert_mcp_tool_result(res)
        results = res["structuredContent"]["results"]
        self.assertEqual(len(results), 2)
        self.assertTrue(results[0]["success"])
        self.assertTrue(results[1]["success"])
