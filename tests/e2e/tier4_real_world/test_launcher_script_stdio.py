"""
Tier 4: Launcher Script & Clean Stdio Transport Tests.
Verifies scripts/run-tia-mcp.bat wrapper behavior, argument and environment
propagation, and zero-stdout-noise guarantees.
"""

from pathlib import Path
from tests.e2e.harness import McpTestCase, McpClient, ServerConfig


class TestLauncherScriptStdio(McpTestCase):
    """Tier 4: Launcher script stdio integrity."""

    def test_launcher_clean_exit_code_on_eof(self):
        """Verifies server cleanly terminates with exit code 0 when stdin stream closes."""
        self.init_session()
        self.client.process.stdin.close()
        self.client.process.wait(timeout=3.0)
        self.assertEqual(self.client.exit_code, 0)

    def test_launcher_script_environment_mode_propagation(self):
        """Verifies TIA_MCP_ACCESS_MODE environment variable propagates cleanly."""
        cfg = ServerConfig(
            access_mode="read-only",
            extra_env={"TIA_MCP_ACCESS_MODE": "read-only"},
            use_mock_server=self.use_mock_server
        )
        with McpClient(cfg) as cl:
            cl.initialize()
            cl.initialized_notification()
            tools = cl.list_tools()
            self.assertEqual(len(tools), 8)

    def test_launcher_script_project_path_propagation(self):
        """Verifies startup project path assertion via config."""
        test_path = "C:\\Automated\\TestProject.ap21"
        cfg = ServerConfig(
            project_path=test_path,
            use_mock_server=self.use_mock_server
        )
        with McpClient(cfg) as cl:
            cl.initialize()
            cl.initialized_notification()
            st = cl.call_tool("get_project_status", {})
            self.assertEqual(st["structuredContent"]["result"]["status"], "bound")
            self.assertEqual(st["structuredContent"]["result"]["value"]["path"], test_path)

    def test_launcher_stdout_starts_with_valid_json(self):
        """Verifies stdout has no batch echo banners before the first JSON-RPC character."""
        # Ping check ensuring immediate valid JSON
        res = self.client.send_raw('{"jsonrpc": "2.0", "id": 1, "method": "ping", "params": {}}\n')
        self.assertEqual(res.get("id"), 1)
        self.assertIn("result", res)
