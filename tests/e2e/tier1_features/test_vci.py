"""
Tier 1: Version Control Interface (VCI) Feature Tests.
Verifies vci_read workspaces, mappings, status, and vci_write dry-run preview.
"""

from tests.e2e.harness import McpTestCase, assert_mcp_tool_result


class TestMcpVci(McpTestCase):
    """Tier 1: VCI tool verification."""

    def test_vci_read_empty_operations(self):
        """Verifies vci_read with empty operations returns valid empty batch response."""
        self.init_session()
        res = self.call_tool("vci_read", {"operations": []})
        assert_mcp_tool_result(res)
        struct = res.get("structuredContent", {})
        self.assertEqual(struct.get("contractVersion"), "1.0")
        self.assertEqual(struct.get("results"), [])

    def test_vci_read_workspaces(self):
        """Verifies vci_read list_workspaces operation."""
        self.init_session()
        res = self.call_tool("vci_read", {
            "operations": [
                {
                    "operationId": "list_ws_1",
                    "operation": "list_workspaces"
                }
            ]
        })
        assert_mcp_tool_result(res)
        struct = res.get("structuredContent", {})
        self.assertEqual(len(struct.get("results", [])), 1)

    def test_vci_read_mappings(self):
        """Verifies vci_read list_mappings operation."""
        self.init_session()
        res = self.call_tool("vci_read", {
            "operations": [
                {
                    "operationId": "list_map_1",
                    "operation": "list_mappings",
                    "workspaceName": "MainWorkspace"
                }
            ]
        })
        assert_mcp_tool_result(res)
        struct = res.get("structuredContent", {})
        self.assertEqual(len(struct.get("results", [])), 1)

    def test_vci_read_workspace_status(self):
        """Verifies vci_read workspace_status operation."""
        self.init_session()
        res = self.call_tool("vci_read", {
            "operations": [
                {
                    "operationId": "stat_ws_1",
                    "operation": "workspace_status",
                    "workspaceName": "MainWorkspace"
                }
            ]
        })
        assert_mcp_tool_result(res)
        struct = res.get("structuredContent", {})
        self.assertEqual(len(struct.get("results", [])), 1)

    def test_vci_write_create_workspace_dry_run(self):
        """Verifies vci_write create_workspace with dryRun=True returns preview phase."""
        self.init_session()
        res = self.call_tool("vci_write", {
            "dryRun": True,
            "operations": [
                {
                    "operationId": "new_ws_1",
                    "operation": "create_workspace",
                    "workspaceName": "GitWorkspace",
                    "targetPath": "C:\\Repo\\VCI"
                }
            ]
        })
        assert_mcp_tool_result(res)
        struct = res.get("structuredContent", {})
        self.assertEqual(struct.get("phase"), "preview")

    def test_vci_write_sync_to_workspace_dry_run(self):
        """Verifies vci_write sync_to_workspace with dryRun=True returns preview phase."""
        self.init_session()
        res = self.call_tool("vci_write", {
            "dryRun": True,
            "operations": [
                {
                    "operationId": "sync_ws_1",
                    "operation": "sync_to_workspace",
                    "workspaceName": "GitWorkspace"
                }
            ]
        })
        assert_mcp_tool_result(res)
        struct = res.get("structuredContent", {})
        self.assertEqual(struct.get("phase"), "preview")
