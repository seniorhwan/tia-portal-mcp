"""
Tier 3: Access Mode Boundary Flow Tests.
Verifies mode isolation and enforcement across sequential read/write tool requests.
"""

from tests.e2e.harness import McpTestCase, McpClient, ServerConfig, McpProtocolError


class TestAccessModeBoundaryFlow(McpTestCase):
    """Tier 3: Access mode behavior across chained operations."""

    access_mode = "read-only"

    def test_read_only_sequential_read_pipeline(self):
        """Verifies read-only mode smoothly allows chaining multiple read tools."""
        self.init_session()

        # 1. Status
        res1 = self.call_tool("get_project_status", {})
        self.assertTrue(res1["structuredContent"]["success"])

        # 2. Project tree
        res2 = self.call_tool("browse_project_tree", {"depth": 1})
        self.assertIn("nodes", res2["structuredContent"])

        # 3. PLC read
        res3 = self.call_tool("plc_read", {"operations": []})
        self.assertEqual(res3["structuredContent"]["results"], [])

        # 4. Network read
        res4 = self.call_tool("network_read", {"operations": []})
        self.assertEqual(res4["structuredContent"]["results"], [])

        # 5. HMI read
        res5 = self.call_tool("hmi_read", {"operations": []})
        self.assertEqual(res5["structuredContent"]["results"], [])

        # 6. VCI read
        res6 = self.call_tool("vci_read", {"operations": []})
        self.assertEqual(res6["structuredContent"]["results"], [])

    def test_read_only_sequential_write_rejections(self):
        """Verifies write tools are consistently rejected in read-only mode without crashing the connection."""
        self.init_session()

        write_calls = [
            ("compile_check", {}),
            ("open_project", {"projectPath": "C:\\a.ap21"}),
            ("create_project", {"projectDirectory": "C:\\", "projectName": "A"}),
            ("plc_write", {"operations": []}),
            ("network_write", {"operations": []}),
            ("hmi_write", {"operations": []}),
            ("vci_write", {"operations": []}),
        ]

        for tool_name, args in write_calls:
            with self.assertRaises(McpProtocolError) as ctx:
                self.call_tool(tool_name, args)
            self.assertEqual(ctx.exception.code, -32602, f"Expected -32602 for {tool_name}")

        # Ensure session remains completely healthy for read operations after repeated rejections
        res = self.call_tool("get_project_status", {})
        self.assertTrue(res["structuredContent"]["success"])

    def test_mode_isolation_between_concurrent_clients(self):
        """Verifies two clients with different access modes maintain strict isolation."""
        cfg_ro = ServerConfig(access_mode="read-only", use_mock_server=self.use_mock_server)
        cfg_rw = ServerConfig(access_mode="read-write", use_mock_server=self.use_mock_server)

        with McpClient(cfg_ro) as client_ro, McpClient(cfg_rw) as client_rw:
            client_ro.initialize()
            client_rw.initialize()

            tools_ro = client_ro.list_tools()
            tools_rw = client_rw.list_tools()

            self.assertEqual(len(tools_ro), 8)
            self.assertEqual(len(tools_rw), 19)

    def test_read_only_mode_blocks_dry_run_writes(self):
        """Verifies that even dryRun=True write calls are prohibited in read-only mode."""
        self.init_session()
        with self.assertRaises(McpProtocolError) as ctx:
            self.call_tool("plc_write", {"dryRun": True, "operations": []})
        self.assertEqual(ctx.exception.code, -32602)
