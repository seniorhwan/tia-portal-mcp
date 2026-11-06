"""
Tier 1: PLC Feature Tests.
Verifies plc_read batch operations, read_cross_references, compile_check, and plc_write preview.
"""

from tests.e2e.harness import McpTestCase, assert_mcp_tool_result


class TestMcpPlc(McpTestCase):
    """Tier 1: PLC software tool verification."""

    def test_plc_read_empty_operations(self):
        """Verifies plc_read with empty operations array returns valid empty batch response."""
        self.init_session()
        res = self.call_tool("plc_read", {"operations": []})
        assert_mcp_tool_result(res)
        struct = res.get("structuredContent", {})
        self.assertEqual(struct.get("contractVersion"), "1.0")
        self.assertEqual(struct.get("results"), [])

    def test_plc_read_get_block_content(self):
        """Verifies plc_read get_block_content operation."""
        self.init_session()
        res = self.call_tool("plc_read", {
            "operations": [
                {
                    "operationId": "read_main",
                    "operation": "get_block_content",
                    "blockPath": "ProgramBlocks/Main",
                    "plcName": "PLC_1"
                }
            ]
        })
        assert_mcp_tool_result(res)
        struct = res.get("structuredContent", {})
        results = struct.get("results", [])
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].get("operationId"), "read_main")

    def test_plc_read_get_type_content(self):
        """Verifies plc_read get_type_content operation."""
        self.init_session()
        res = self.call_tool("plc_read", {
            "operations": [
                {
                    "operationId": "read_udt",
                    "operation": "get_type_content",
                    "typePath": "DataTypes/MotorData",
                    "plcName": "PLC_1"
                }
            ]
        })
        assert_mcp_tool_result(res)
        struct = res.get("structuredContent", {})
        self.assertEqual(len(struct.get("results", [])), 1)

    def test_plc_read_list_tag_tables(self):
        """Verifies plc_read list_tag_tables operation."""
        self.init_session()
        res = self.call_tool("plc_read", {
            "operations": [
                {
                    "operationId": "list_tags",
                    "operation": "list_tag_tables",
                    "plcName": "PLC_1"
                }
            ]
        })
        assert_mcp_tool_result(res)
        struct = res.get("structuredContent", {})
        self.assertEqual(len(struct.get("results", [])), 1)

    def test_plc_read_cross_references(self):
        """Verifies read_cross_references target inspection."""
        self.init_session()
        res = self.call_tool("read_cross_references", {
            "target": {"targetType": "block", "name": "Main", "plcName": "PLC_1"},
            "maxResults": 50
        })
        assert_mcp_tool_result(res)
        struct = res.get("structuredContent", {})
        self.assertIn("value", struct)

    def test_plc_write_dry_run_preview(self):
        """Verifies plc_write with dryRun=True returns preview phase with audit."""
        self.init_session()
        res = self.call_tool("plc_write", {
            "dryRun": True,
            "operations": [
                {
                    "operationId": "update_logic",
                    "operation": "update_block_logic",
                    "blockPath": "ProgramBlocks/Main",
                    "source": "Network 1:\n// Logic here"
                }
            ]
        })
        assert_mcp_tool_result(res)
        struct = res.get("structuredContent", {})
        self.assertEqual(struct.get("phase"), "preview")
        self.assertIn("audit", struct)
