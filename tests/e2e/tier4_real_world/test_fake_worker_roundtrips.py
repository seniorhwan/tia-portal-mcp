"""
Tier 4: Standalone FakeWorker Roundtrip Tests.
Verifies offline end-to-end tool execution against scripted mock worker
without Siemens Openness runtime or licenses.
"""

from tests.e2e.harness import McpTestCase, assert_mcp_tool_result


class TestFakeWorkerRoundtrips(McpTestCase):
    """Tier 4: FakeWorker offline tool verification."""

    def test_fake_worker_project_status_roundtrip(self):
        """Verifies full roundtrip get_project_status execution."""
        self.init_session()
        res = self.call_tool("get_project_status", {})
        assert_mcp_tool_result(res, expected_tool="get_project_status")
        self.assertTrue(res["structuredContent"]["success"])

    def test_fake_worker_browse_tree_roundtrip(self):
        """Verifies full roundtrip browse_project_tree pagination and nodes."""
        self.init_session()
        res = self.call_tool("browse_project_tree", {"depth": 2, "pageSize": 50})
        assert_mcp_tool_result(res)
        struct = res["structuredContent"]
        self.assertEqual(struct.get("contractVersion"), "3.0")
        self.assertIn("nodes", struct)
        self.assertIn("pagination", struct)

    def test_fake_worker_plc_read_roundtrip(self):
        """Verifies full roundtrip plc_read batch operations."""
        self.init_session()
        ops = [
            {"operationId": "op_1", "operation": "get_block_content", "blockPath": "ProgramBlocks/Main"},
            {"operationId": "op_2", "operation": "list_tag_tables"}
        ]
        res = self.call_tool("plc_read", {"operations": ops})
        assert_mcp_tool_result(res)
        struct = res["structuredContent"]
        self.assertEqual(len(struct["results"]), 2)

    def test_fake_worker_guarded_write_roundtrip(self):
        """Verifies full roundtrip guarded write preview and audit generation."""
        self.init_session()
        ops = [
            {"operationId": "w_1", "operation": "update_block_logic", "blockPath": "ProgramBlocks/Main", "source": "Logic"}
        ]
        res = self.call_tool("plc_write", {"dryRun": True, "operations": ops})
        assert_mcp_tool_result(res)
        struct = res["structuredContent"]
        self.assertEqual(struct["phase"], "preview")
        self.assertIn("audit", struct)
