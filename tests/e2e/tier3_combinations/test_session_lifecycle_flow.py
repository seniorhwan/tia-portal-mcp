"""
Tier 3: Session Lifecycle Flow Tests.
Verifies multi-tool stateful progressions across MCP connection, binding,
browsing, mutating, and disconnecting.
"""

from tests.e2e.harness import McpTestCase, assert_mcp_tool_result


class TestSessionLifecycleFlow(McpTestCase):
    """Tier 3: Multi-step session lifecycle flows."""

    def test_complete_client_session_lifecycle(self):
        """Verifies full standard lifecycle: initialize -> list -> status -> bind -> browse -> close."""
        # 1. Initialize
        init = self.init_session()
        self.assertEqual(init.get("protocolVersion"), "2024-11-05")

        # 2. List tools
        tools = self.list_tools()
        self.assertEqual(len(tools), 19)

        # 3. Initial status
        st1 = self.call_tool("get_project_status", {})
        self.assertEqual(st1["structuredContent"]["result"]["status"], "no_project")

        # 4. Bind project
        bound = self.call_tool("bind_project", {"projectPath": "C:\\Plant\\Main.ap21"})
        self.assertEqual(bound["structuredContent"]["result"]["status"], "bound")

        # 5. Status updated
        st2 = self.call_tool("get_project_status", {})
        self.assertEqual(st2["structuredContent"]["result"]["status"], "bound")

        # 6. Browse project tree
        tree = self.call_tool("browse_project_tree", {"depth": 2, "pageSize": 10})
        self.assertGreaterEqual(len(tree["structuredContent"]["nodes"]), 1)

        # 7. Close project
        close_res = self.call_tool("close_project", {"dryRun": False})
        self.assertEqual(close_res["structuredContent"]["phase"], "applied")

        # 8. Post-close status
        st3 = self.call_tool("get_project_status", {})
        self.assertEqual(st3["structuredContent"]["result"]["status"], "no_project")

    def test_rebind_without_force_fails_then_force_succeeds(self):
        """Verifies rebinding to a different project without forceRebind fails, then succeeds with forceRebind=True."""
        self.init_session()
        # Bind Project 1
        res1 = self.call_tool("bind_project", {"projectPath": "C:\\Proj1.ap21"})
        self.assertTrue(res1["structuredContent"]["success"])

        # Attempt to bind Project 2 without forceRebind
        res2 = self.call_tool("bind_project", {"projectPath": "C:\\Proj2.ap21", "forceRebind": False})
        self.assertFalse(res2["structuredContent"]["success"])
        self.assertEqual(res2["structuredContent"]["error"]["category"], "binding_conflict")

        # Bind Project 2 with forceRebind=True
        res3 = self.call_tool("bind_project", {"projectPath": "C:\\Proj2.ap21", "forceRebind": True})
        self.assertTrue(res3["structuredContent"]["success"])
        self.assertEqual(res3["structuredContent"]["result"]["projectPath"], "C:\\Proj2.ap21")

    def test_open_then_browse_then_compile(self):
        """Verifies opening a project, browsing its blocks, and running compile check."""
        self.init_session()
        open_res = self.call_tool("open_project", {"projectPath": "C:\\Demo.ap21", "dryRun": False})
        self.assertEqual(open_res["structuredContent"]["phase"], "applied")

        tree = self.call_tool("browse_project_tree", {"depth": 1})
        self.assertTrue(len(tree["structuredContent"]["nodes"]) > 0)

        compile_res = self.call_tool("compile_check", {"plcName": "PLC_1"})
        assert_mcp_tool_result(compile_res, expected_tool="compile_check")
        self.assertTrue(compile_res["structuredContent"]["success"])

    def test_save_project_as_rebinds_active_session(self):
        """Verifies save_project_as seamlessly rebinds the session to the new project path."""
        self.init_session()
        self.call_tool("bind_project", {"projectPath": "C:\\Original.ap21"})

        save_as_res = self.call_tool("save_project_as", {
            "targetDirectory": "C:\\Copies",
            "targetName": "Copy1",
            "rebind": True,
            "dryRun": False
        })
        self.assertEqual(save_as_res["structuredContent"]["phase"], "applied")

        status = self.call_tool("get_project_status", {})
        self.assertIn("Copy1.ap21", status["structuredContent"]["result"]["value"]["path"])
