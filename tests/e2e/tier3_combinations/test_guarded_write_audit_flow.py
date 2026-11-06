"""
Tier 3: Guarded Write & Audit Flow Tests.
Verifies the two-phase guarded write pattern (dryRun=True preview -> inspection -> dryRun=False apply)
and associated audit outcomes across engineering domains.
"""

from tests.e2e.harness import McpTestCase, assert_mcp_tool_result


class TestGuardedWriteAuditFlow(McpTestCase):
    """Tier 3: Guarded write preview and apply pipeline verification."""

    def test_plc_guarded_write_preview_then_apply(self):
        """Verifies plc_write preview phase followed by applied phase."""
        self.init_session()

        ops = [
            {
                "operationId": "mod_block_1",
                "operation": "update_block_logic",
                "blockPath": "ProgramBlocks/Main",
                "source": "Network 1:\n#Counter := #Counter + 1;"
            }
        ]

        # Phase 1: Preview
        preview = self.call_tool("plc_write", {"dryRun": True, "operations": ops})
        assert_mcp_tool_result(preview)
        p_struct = preview["structuredContent"]
        self.assertEqual(p_struct.get("phase"), "preview")
        self.assertTrue(p_struct.get("audit", {}).get("dryRun", True))

        # Phase 2: Apply
        applied = self.call_tool("plc_write", {"dryRun": False, "operations": ops})
        assert_mcp_tool_result(applied)
        a_struct = applied["structuredContent"]
        self.assertEqual(a_struct.get("phase"), "applied")
        self.assertFalse(a_struct.get("audit", {}).get("dryRun", False))

    def test_network_guarded_write_preview_then_apply(self):
        """Verifies network_write preview phase followed by applied phase."""
        self.init_session()

        ops = [
            {
                "operationId": "net_subnet_1",
                "operation": "create_subnet",
                "subnet": {"name": "IndustrialEthernet", "networkType": "Ethernet"}
            }
        ]

        # Preview
        preview = self.call_tool("network_write", {"dryRun": True, "operations": ops})
        self.assertEqual(preview["structuredContent"]["phase"], "preview")

        # Apply
        applied = self.call_tool("network_write", {"dryRun": False, "operations": ops})
        self.assertEqual(applied["structuredContent"]["phase"], "applied")

    def test_hmi_guarded_write_preview_then_apply(self):
        """Verifies hmi_write preview phase followed by applied phase."""
        self.init_session()

        ops = [
            {
                "operationId": "hmi_write_1",
                "operation": "create_hmi_tag",
                "deviceName": "HMI_1",
                "tagName": "LevelSensor",
                "dataType": "Real"
            }
        ]

        preview = self.call_tool("hmi_write", {"dryRun": True, "operations": ops})
        self.assertEqual(preview["structuredContent"]["phase"], "preview")

        applied = self.call_tool("hmi_write", {"dryRun": False, "operations": ops})
        self.assertEqual(applied["structuredContent"]["phase"], "applied")

    def test_vci_guarded_write_preview_then_apply(self):
        """Verifies vci_write preview phase followed by applied phase."""
        self.init_session()

        ops = [
            {
                "operationId": "vci_ws_create",
                "operation": "create_workspace",
                "workspaceName": "GitMaster",
                "targetPath": "C:\\GitMaster"
            }
        ]

        preview = self.call_tool("vci_write", {"dryRun": True, "operations": ops})
        self.assertEqual(preview["structuredContent"]["phase"], "preview")

        applied = self.call_tool("vci_write", {"dryRun": False, "operations": ops})
        self.assertEqual(applied["structuredContent"]["phase"], "applied")
