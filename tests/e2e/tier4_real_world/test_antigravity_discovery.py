"""
Tier 4: Antigravity Host Discovery Workflow Tests.
Simulates Antigravity Go backend (mcp_manager.go) discovering and cataloging
the TIA Portal MCP server tools over stdio transport.
"""

from tests.e2e.harness import McpTestCase, assert_clean_stdout


class TestAntigravityDiscovery(McpTestCase):
    """Tier 4: Antigravity integration workflow."""

    def test_antigravity_mcp_handshake_flow(self):
        """Simulates Antigravity discovery: initialize -> initialized notification -> tools/list."""
        init = self.client.initialize(
            protocol_version="2024-11-05",
            client_info={"name": "Antigravity", "version": "1.0.0"}
        )
        self.assertEqual(init.get("protocolVersion"), "2024-11-05")
        self.assertEqual(init.get("serverInfo", {}).get("name"), "TiaMcpServer")

        self.client.initialized_notification()

        tools = self.client.list_tools()
        self.assertEqual(len(tools), 19)

    def test_antigravity_tool_schema_conformance(self):
        """Verifies every tool's schema conforms to Antigravity tool schema format."""
        self.init_session()
        tools = self.list_tools()

        for tool in tools:
            # Antigravity tool registry requires name, description, and inputSchema
            self.assertIn("name", tool)
            self.assertIn("description", tool)
            self.assertIn("inputSchema", tool)

            schema = tool["inputSchema"]
            self.assertEqual(schema.get("type"), "object")
            self.assertIn("properties", schema)
            self.assertIsInstance(schema["properties"], dict)

    def test_antigravity_jsonrpc_stdio_framing(self):
        """Verifies stdio stream emits pure newline-delimited JSON with no batch script echoes."""
        self.init_session()
        assert_clean_stdout(self.client)

        # Raw check of stdout queue items
        res = self.client.send_request("ping", {})
        self.assertIsInstance(res, dict)

    def test_antigravity_custom_environment_launch(self):
        """Verifies server initializes properly when launched with Antigravity-style env config."""
        self.client.initialize()
        self.client.initialized_notification()
        status = self.call_tool("get_project_status", {})
        self.assertTrue(status["structuredContent"]["success"])
