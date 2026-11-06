"""
Tier 1: Handshake Feature Tests.
Verifies standard MCP 2024-11-05 initialization protocol, server metadata,
notifications/initialized lifecycle, capabilities advertisement, and ping.
"""

from tests.e2e.harness import McpTestCase, assert_jsonrpc_success


class TestMcpHandshake(McpTestCase):
    """Tier 1: Handshake verification."""

    def test_handshake_standard_initialize(self):
        """Verifies standard MCP initialize returns protocol version 2024-11-05."""
        res = self.client.initialize()
        assert_jsonrpc_success(res)
        self.assertIn("protocolVersion", res)
        self.assertEqual(res["protocolVersion"], "2024-11-05")

    def test_handshake_server_info(self):
        """Verifies serverInfo contains name 'TiaMcpServer' and non-empty version."""
        res = self.client.initialize()
        assert_jsonrpc_success(res)
        self.assertIn("serverInfo", res)
        info = res["serverInfo"]
        self.assertEqual(info.get("name"), "TiaMcpServer")
        self.assertTrue(bool(info.get("version")))

    def test_handshake_capabilities_tools_advertised(self):
        """Verifies server advertises tools capability."""
        res = self.client.initialize()
        assert_jsonrpc_success(res)
        self.assertIn("capabilities", res)
        caps = res["capabilities"]
        self.assertIn("tools", caps)
        self.assertIn("listChanged", caps["tools"])

    def test_handshake_notifications_initialized_lifecycle(self):
        """Verifies sending notifications/initialized after initialize maintains server health."""
        self.client.initialize()
        self.client.initialized_notification()
        # Verify server is responsive after notification
        tools = self.client.list_tools()
        self.assertIsInstance(tools, list)
        self.assertGreaterEqual(len(tools), 1)

    def test_handshake_ping_response(self):
        """Verifies MCP ping request receives empty success object."""
        self.client.initialize()
        self.client.initialized_notification()
        res = self.client.send_request("ping", {})
        self.assertIsInstance(res, dict)

    def test_handshake_client_info_preservation(self):
        """Verifies initialize accepts custom clientInfo cleanly."""
        custom_client = {"name": "AntigravityTestClient", "version": "3.5.0"}
        res = self.client.initialize(client_info=custom_client)
        assert_jsonrpc_success(res)
        self.assertEqual(res["protocolVersion"], "2024-11-05")
