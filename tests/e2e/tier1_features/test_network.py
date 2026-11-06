"""
Tier 1: Network & Topology Feature Tests.
Verifies network_read hardware configuration, object listing, inspection,
and network_write subnet/device previews.
"""

from tests.e2e.harness import McpTestCase, assert_mcp_tool_result


class TestMcpNetwork(McpTestCase):
    """Tier 1: Network and topology tool verification."""

    def test_network_read_empty_operations(self):
        """Verifies network_read with empty operations returns valid empty batch response."""
        self.init_session()
        res = self.call_tool("network_read", {"operations": []})
        assert_mcp_tool_result(res)
        struct = res.get("structuredContent", {})
        self.assertEqual(struct.get("contractVersion"), "1.0")
        self.assertEqual(struct.get("results"), [])

    def test_network_read_hardware_config(self):
        """Verifies network_read read_hardware_config operation."""
        self.init_session()
        res = self.call_tool("network_read", {
            "operations": [
                {
                    "operationId": "hw_read_1",
                    "operation": "read_hardware_config",
                    "deviceName": "PLC_1"
                }
            ]
        })
        assert_mcp_tool_result(res)
        struct = res.get("structuredContent", {})
        self.assertEqual(len(struct.get("results", [])), 1)

    def test_network_read_list_network_objects(self):
        """Verifies network_read list_network_objects operation."""
        self.init_session()
        res = self.call_tool("network_read", {
            "operations": [
                {
                    "operationId": "list_objs",
                    "operation": "list_network_objects",
                    "pageSize": 50
                }
            ]
        })
        assert_mcp_tool_result(res)
        struct = res.get("structuredContent", {})
        self.assertEqual(len(struct.get("results", [])), 1)

    def test_network_read_inspect_network_object(self):
        """Verifies network_read inspect_network_object operation."""
        self.init_session()
        res = self.call_tool("network_read", {
            "operations": [
                {
                    "operationId": "inspect_iface",
                    "operation": "inspect_network_object",
                    "target": {"kind": "networkInterface", "itemPath": "Devices/PLC_1/PROFINET"}
                }
            ]
        })
        assert_mcp_tool_result(res)
        struct = res.get("structuredContent", {})
        self.assertEqual(len(struct.get("results", [])), 1)

    def test_network_write_create_subnet_dry_run(self):
        """Verifies network_write create_subnet with dryRun=True returns preview phase."""
        self.init_session()
        res = self.call_tool("network_write", {
            "dryRun": True,
            "operations": [
                {
                    "operationId": "create_subnet_1",
                    "operation": "create_subnet",
                    "subnet": {
                        "name": "PN/IE_Subnet_1",
                        "networkType": "Profibus"
                    }
                }
            ]
        })
        assert_mcp_tool_result(res)
        struct = res.get("structuredContent", {})
        self.assertEqual(struct.get("phase"), "preview")

    def test_network_write_configure_device_dry_run(self):
        """Verifies network_write configure_network_device dryRun preview."""
        self.init_session()
        res = self.call_tool("network_write", {
            "dryRun": True,
            "operations": [
                {
                    "operationId": "cfg_dev_1",
                    "operation": "configure_network_device",
                    "deviceName": "PLC_1"
                }
            ]
        })
        assert_mcp_tool_result(res)
        struct = res.get("structuredContent", {})
        self.assertEqual(struct.get("phase"), "preview")
