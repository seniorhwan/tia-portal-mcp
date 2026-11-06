"""
Tier 2: Buffer Bounds & Batch Limits Tests.
Verifies batch upper bounds (<=50 items), integer minimum/maximum limits,
and large string handling.
"""

from tests.e2e.harness import McpTestCase, McpProtocolError, assert_mcp_tool_result


class TestBufferAndBatchLimits(McpTestCase):
    """Tier 2: Batch operation and buffer boundary checks."""

    def test_batch_operations_upper_bound_50_items_exceeded(self):
        """Verifies submitting 51 operations to plc_read violates maxItems=50."""
        self.init_session()
        oversized_ops = [{"operationId": f"op_{i}", "operation": "list_tag_tables"} for i in range(51)]
        with self.assertRaises(McpProtocolError) as ctx:
            self.call_tool("plc_read", {"operations": oversized_ops})
        self.assertEqual(ctx.exception.code, -32602)
        self.assertIn("50", ctx.exception.message)

    def test_batch_operations_at_exact_50_limit(self):
        """Verifies submitting exactly 50 operations succeeds cleanly."""
        self.init_session()
        exact_ops = [{"operationId": f"op_{i}", "operation": "list_tag_tables"} for i in range(50)]
        res = self.call_tool("plc_read", {"operations": exact_ops})
        assert_mcp_tool_result(res)
        struct = res.get("structuredContent", {})
        self.assertEqual(len(struct.get("results", [])), 50)

    def test_browse_tree_zero_depth_rejected(self):
        """Verifies depth=0 is rejected (minimum: 1)."""
        self.init_session()
        with self.assertRaises(McpProtocolError) as ctx:
            self.call_tool("browse_project_tree", {"depth": 0})
        self.assertEqual(ctx.exception.code, -32602)

    def test_browse_tree_page_size_exceeded(self):
        """Verifies pageSize=201 is rejected (maximum: 200)."""
        self.init_session()
        with self.assertRaises(McpProtocolError) as ctx:
            self.call_tool("browse_project_tree", {"pageSize": 201})
        self.assertEqual(ctx.exception.code, -32602)

    def test_large_argument_string_handling(self):
        """Verifies large payload argument within document budget transmits cleanly."""
        self.init_session()
        # 10KB source string
        large_source = "// Comment\n" + ("X := Y + 1;\n" * 500)
        res = self.call_tool("plc_write", {
            "dryRun": True,
            "operations": [
                {
                    "operationId": "large_block_op",
                    "operation": "update_block_logic",
                    "source": large_source
                }
            ]
        })
        assert_mcp_tool_result(res)
        struct = res.get("structuredContent", {})
        self.assertEqual(struct.get("phase"), "preview")
