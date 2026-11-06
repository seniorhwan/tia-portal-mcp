"""
Tier 1: Project Lifecycle Feature Tests.
Verifies project status, binding, open, create, save, save-as, archive, and close tools.
"""

from tests.e2e.harness import McpTestCase, assert_mcp_tool_result


class TestMcpLifecycle(McpTestCase):
    """Tier 1: Lifecycle tools verification."""

    def test_lifecycle_get_project_status(self):
        """Verifies get_project_status returns structured status outcome."""
        self.init_session()
        res = self.call_tool("get_project_status", {})
        assert_mcp_tool_result(res, expected_tool="get_project_status")
        struct = res.get("structuredContent", {})
        self.assertEqual(struct.get("contractVersion"), "1.0")
        self.assertIn("result", struct)
        self.assertIn("status", struct["result"])

    def test_lifecycle_bind_project_listing(self):
        """Verifies bind_project without arguments lists candidate projects."""
        self.init_session()
        res = self.call_tool("bind_project", {})
        assert_mcp_tool_result(res, expected_tool="bind_project")
        struct = res.get("structuredContent", {})
        self.assertIn("result", struct)
        self.assertIn(struct["result"].get("status"), ("listed", "bound"))

    def test_lifecycle_bind_project_explicit_path(self):
        """Verifies bind_project with a specific path binds successfully."""
        self.init_session()
        test_path = "C:\\Projects\\Plant_A.ap21"
        res = self.call_tool("bind_project", {"projectPath": test_path, "forceRebind": True})
        assert_mcp_tool_result(res, expected_tool="bind_project")
        struct = res.get("structuredContent", {})
        self.assertEqual(struct["result"].get("status"), "bound")
        self.assertEqual(struct["result"].get("projectPath"), test_path)

    def test_lifecycle_open_project_dry_run(self):
        """Verifies open_project dryRun previews without modifying state."""
        self.init_session()
        test_path = "C:\\Projects\\Simulation.ap21"
        res = self.call_tool("open_project", {"projectPath": test_path, "dryRun": True})
        assert_mcp_tool_result(res)
        struct = res.get("structuredContent", {})
        self.assertEqual(struct.get("phase"), "preview")
        self.assertTrue(struct.get("audit", {}).get("dryRun", True))

    def test_lifecycle_create_project_dry_run(self):
        """Verifies create_project dryRun previews project creation safely."""
        self.init_session()
        res = self.call_tool("create_project", {
            "projectDirectory": "C:\\Automation",
            "projectName": "NewUnit",
            "dryRun": True
        })
        assert_mcp_tool_result(res)
        struct = res.get("structuredContent", {})
        self.assertEqual(struct.get("phase"), "preview")

    def test_lifecycle_archive_project_dry_run(self):
        """Verifies archive_project dryRun previews project archiving."""
        self.init_session()
        res = self.call_tool("archive_project", {
            "archiveDirectory": "C:\\Backup",
            "archiveName": "Unit1.zap21",
            "dryRun": True
        })
        assert_mcp_tool_result(res)
        struct = res.get("structuredContent", {})
        self.assertEqual(struct.get("phase"), "preview")
