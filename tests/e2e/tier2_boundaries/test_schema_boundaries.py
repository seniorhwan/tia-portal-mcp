"""
Tier 2: Closed Schema & Argument Boundary Tests.
Verifies additionalProperties: false enforcement, type validation, and required fields.
"""

from tests.e2e.harness import McpTestCase, McpProtocolError


class TestSchemaBoundaries(McpTestCase):
    """Tier 2: Closed schema and type boundary enforcement."""

    def test_closed_schema_extra_parameters_rejected(self):
        """Verifies extraneous parameters on get_project_status trigger schema error."""
        self.init_session()
        with self.assertRaises(McpProtocolError) as ctx:
            self.call_tool("get_project_status", {"unexpectedExtraField": "illegal_value"})
        self.assertEqual(ctx.exception.code, -32602)
        self.assertIn("unexpectedExtraField", ctx.exception.message)

    def test_closed_schema_boolean_type_mismatch(self):
        """Verifies string passed where boolean expected is rejected."""
        self.init_session()
        with self.assertRaises(McpProtocolError) as ctx:
            self.call_tool("open_project", {
                "projectPath": "C:\\test.ap21",
                "dryRun": "yes_dry_run"  # Must be bool
            })
        self.assertEqual(ctx.exception.code, -32602)

    def test_closed_schema_integer_type_mismatch(self):
        """Verifies string passed where integer expected is rejected."""
        self.init_session()
        with self.assertRaises(McpProtocolError) as ctx:
            self.call_tool("browse_project_tree", {
                "depth": "two"  # Must be int
            })
        self.assertEqual(ctx.exception.code, -32602)

    def test_missing_required_property(self):
        """Verifies calling open_project without required projectPath is rejected."""
        self.init_session()
        with self.assertRaises(McpProtocolError) as ctx:
            self.call_tool("open_project", {"dryRun": True})
        self.assertEqual(ctx.exception.code, -32602)
        self.assertIn("projectPath", ctx.exception.message)

    def test_missing_required_batch_operations(self):
        """Verifies calling plc_read without required 'operations' array is rejected."""
        self.init_session()
        with self.assertRaises(McpProtocolError) as ctx:
            self.call_tool("plc_read", {})
        self.assertEqual(ctx.exception.code, -32602)
        self.assertIn("operations", ctx.exception.message)
