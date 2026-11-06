"""
Tier 1: Capabilities & Access Mode Feature Tests.
Verifies tool exposure, schema structure, and mode partitioning
(read-only: 8 tools; read-write / full: 19 tools).
"""

from tests.e2e.harness import (
    McpTestCase,
    McpProtocolError,
    assert_tool_in_list,
    assert_tool_not_in_list,
)


class TestMcpCapabilitiesDefaultMode(McpTestCase):
    """Verifies default read-write capability surface (19 tools)."""

    access_mode = "read-write"

    def test_capabilities_read_write_count(self):
        """Verifies exactly 19 tools are listed in read-write mode."""
        self.init_session()
        tools = self.list_tools()
        self.assertEqual(len(tools), 19)

    def test_capabilities_schema_completeness(self):
        """Verifies every tool has a non-empty name, description, and valid inputSchema."""
        self.init_session()
        tools = self.list_tools()
        for tool in tools:
            name = tool.get("name")
            self.assertTrue(name, "Tool name must not be empty")
            self.assertTrue(tool.get("description"), f"Tool {name} missing description")
            schema = tool.get("inputSchema", {})
            self.assertEqual(schema.get("type"), "object", f"Tool {name} inputSchema must be object")
            self.assertIn("properties", schema, f"Tool {name} inputSchema missing properties")

    def test_capabilities_all_nineteen_tools_present(self):
        """Verifies all 19 canonical tools are present."""
        expected_tools = [
            "bind_project", "browse_project_tree", "get_project_status", "hmi_read",
            "network_read", "plc_read", "read_cross_references", "vci_read",
            "compile_check", "open_project", "create_project", "save_project",
            "save_project_as", "archive_project", "close_project", "plc_write",
            "network_write", "hmi_write", "vci_write"
        ]
        self.init_session()
        tools = self.list_tools()
        for t in expected_tools:
            assert_tool_in_list(tools, t)


class TestMcpCapabilitiesReadOnlyMode(McpTestCase):
    """Verifies restricted read-only capability surface (8 tools)."""

    access_mode = "read-only"

    def test_capabilities_read_only_count(self):
        """Verifies exactly 8 tools are listed in read-only mode."""
        self.init_session()
        tools = self.list_tools()
        self.assertEqual(len(tools), 8)

    def test_capabilities_read_only_surface_enforcement(self):
        """Verifies only read tools are listed; write tools are strictly absent."""
        self.init_session()
        tools = self.list_tools()
        read_tools = [
            "bind_project", "browse_project_tree", "get_project_status",
            "hmi_read", "network_read", "plc_read", "read_cross_references", "vci_read"
        ]
        write_tools = [
            "compile_check", "open_project", "create_project", "save_project",
            "save_project_as", "archive_project", "close_project", "plc_write",
            "network_write", "hmi_write", "vci_write"
        ]
        for rt in read_tools:
            assert_tool_in_list(tools, rt)
        for wt in write_tools:
            assert_tool_not_in_list(tools, wt)

    def test_capabilities_write_tool_invocation_rejected_in_read_only(self):
        """Verifies calling a write tool in read-only mode results in protocol error."""
        self.init_session()
        with self.assertRaises(McpProtocolError) as ctx:
            self.call_tool("create_project", {
                "projectDirectory": "C:\\temp",
                "projectName": "TestProject"
            })
        self.assertEqual(ctx.exception.code, -32602)
