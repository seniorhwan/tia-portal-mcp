"""
Tier 1: WinCC Unified HMI Feature Tests.
Verifies hmi_read tags, alarms, screens, and hmi_write preview phase.
"""

from tests.e2e.harness import McpTestCase, assert_mcp_tool_result


class TestMcpHmi(McpTestCase):
    """Tier 1: WinCC Unified HMI tool verification."""

    def test_hmi_read_empty_operations(self):
        """Verifies hmi_read with empty operations returns valid empty batch response."""
        self.init_session()
        res = self.call_tool("hmi_read", {"operations": []})
        assert_mcp_tool_result(res)
        struct = res.get("structuredContent", {})
        self.assertEqual(struct.get("contractVersion"), "1.0")
        self.assertEqual(struct.get("results"), [])

    def test_hmi_read_tags(self):
        """Verifies hmi_read list_hmi_tags operation."""
        self.init_session()
        res = self.call_tool("hmi_read", {
            "operations": [
                {
                    "operationId": "hmi_tags_1",
                    "operation": "list_hmi_tags",
                    "deviceName": "HMI_Unified_1"
                }
            ]
        })
        assert_mcp_tool_result(res)
        struct = res.get("structuredContent", {})
        self.assertEqual(len(struct.get("results", [])), 1)

    def test_hmi_read_alarms(self):
        """Verifies hmi_read list_alarms operation."""
        self.init_session()
        res = self.call_tool("hmi_read", {
            "operations": [
                {
                    "operationId": "hmi_alarms_1",
                    "operation": "list_alarms",
                    "deviceName": "HMI_Unified_1"
                }
            ]
        })
        assert_mcp_tool_result(res)
        struct = res.get("structuredContent", {})
        self.assertEqual(len(struct.get("results", [])), 1)

    def test_hmi_read_screens(self):
        """Verifies hmi_read list_screens operation."""
        self.init_session()
        res = self.call_tool("hmi_read", {
            "operations": [
                {
                    "operationId": "hmi_screens_1",
                    "operation": "list_screens",
                    "deviceName": "HMI_Unified_1"
                }
            ]
        })
        assert_mcp_tool_result(res)
        struct = res.get("structuredContent", {})
        self.assertEqual(len(struct.get("results", [])), 1)

    def test_hmi_write_create_tag_dry_run(self):
        """Verifies hmi_write create_hmi_tag with dryRun=True returns preview phase."""
        self.init_session()
        res = self.call_tool("hmi_write", {
            "dryRun": True,
            "operations": [
                {
                    "operationId": "new_tag_1",
                    "operation": "create_hmi_tag",
                    "deviceName": "HMI_Unified_1",
                    "tagName": "Speed_RPM",
                    "dataType": "Int"
                }
            ]
        })
        assert_mcp_tool_result(res)
        struct = res.get("structuredContent", {})
        self.assertEqual(struct.get("phase"), "preview")

    def test_hmi_write_create_alarm_dry_run(self):
        """Verifies hmi_write create_discrete_alarm with dryRun=True returns preview phase."""
        self.init_session()
        res = self.call_tool("hmi_write", {
            "dryRun": True,
            "operations": [
                {
                    "operationId": "new_alarm_1",
                    "operation": "create_discrete_alarm",
                    "deviceName": "HMI_Unified_1",
                    "alarmName": "EStop_Triggered"
                }
            ]
        })
        assert_mcp_tool_result(res)
        struct = res.get("structuredContent", {})
        self.assertEqual(struct.get("phase"), "preview")
