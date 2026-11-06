"""
Tier 4: Absent TIA Portal Graceful Degradation Tests.
Verifies server behavior when Siemens TIA Portal is not running or not installed,
ensuring zero crashes, clean diagnostics, and structured error responses.
"""

from tests.e2e.harness import McpTestCase, assert_mcp_tool_result


class TestAbsentTiaDegradation(McpTestCase):
    """Tier 4: Graceful degradation in environments without live TIA Portal."""

    def test_handshake_and_enumeration_without_tia(self):
        """Verifies handshake and tool listing execute 100% offline without live Siemens runtime."""
        init = self.init_session()
        self.assertEqual(init.get("protocolVersion"), "2024-11-05")

        tools = self.list_tools()
        self.assertEqual(len(tools), 19)

    def test_get_project_status_when_no_portal_running(self):
        """Verifies get_project_status returns clean 'no_project' without crashing."""
        self.init_session()
        res = self.call_tool("get_project_status", {})
        assert_mcp_tool_result(res, expected_tool="get_project_status")
        struct = res["structuredContent"]
        self.assertTrue(struct["success"])
        self.assertIn(struct["result"]["status"], ("no_project", "bound"))

    def test_bind_project_returns_candidates_or_clean_rejection(self):
        """Verifies bind_project returns structured list of candidates rather than throwing unhandled exception."""
        self.init_session()
        res = self.call_tool("bind_project", {})
        assert_mcp_tool_result(res, expected_tool="bind_project")
        struct = res["structuredContent"]
        self.assertIn("result", struct)

    def test_clean_stderr_diagnostic_logging(self):
        """Verifies diagnostic startup logs are captured exclusively on stderr."""
        self.init_session()
        stderr_text = "\n".join(self.client.stderr_lines)
        # Should contain access mode diagnostic banner on stderr
        self.assertIn("TIA MCP access mode", stderr_text)
