"""
Tier 2: Malformed JSON Boundary Tests.
Verifies server robustly responds with -32700 Parse error or handles
whitespace/non-object payloads without crashing.
"""

from tests.e2e.harness import McpTestCase


class TestMalformedJsonBoundaries(McpTestCase):
    """Tier 2: Malformed JSON handling."""

    def test_malformed_json_unclosed_brace(self):
        """Verifies unclosed JSON object returns Parse error (-32700)."""
        raw = '{"jsonrpc": "2.0", "id": 1, "method": "initialize"'
        res = self.client.send_raw(raw)
        self.assertIn("error", res)
        self.assertEqual(res["error"].get("code"), -32700)

    def test_malformed_json_trailing_comma(self):
        """Verifies trailing comma in JSON returns Parse error (-32700)."""
        raw = '{"jsonrpc": "2.0", "id": 2, "method": "ping",}'
        res = self.client.send_raw(raw)
        self.assertIn("error", res)
        self.assertEqual(res["error"].get("code"), -32700)

    def test_malformed_json_invalid_escapes(self):
        """Verifies unescaped control character / invalid escape returns Parse error."""
        raw = '{"jsonrpc": "2.0", "id": 3, "method": "initialize\\xZZ"}'
        res = self.client.send_raw(raw)
        self.assertIn("error", res)
        self.assertEqual(res["error"].get("code"), -32700)

    def test_empty_line_and_whitespace(self):
        """Verifies empty lines and pure whitespace do not crash server or emit responses."""
        self.client.process.stdin.write("\n\n   \t\n")
        self.client.process.stdin.flush()
        # Verify subsequent valid request succeeds normally
        res = self.client.initialize()
        self.assertEqual(res.get("protocolVersion"), "2024-11-05")

    def test_non_object_json_top_level(self):
        """Verifies top-level array or scalar returns Invalid Request (-32600)."""
        raw = '["invalid", "array"]'
        res = self.client.send_raw(raw)
        self.assertIn("error", res)
        self.assertEqual(res["error"].get("code"), -32600)
