"""
Base TestCase for MCP E2E tests using standard library unittest.
"""

import unittest
from typing import Optional, Dict, Any, List
from .client import McpClient
from .config import ServerConfig


class McpTestCase(unittest.TestCase):
    """Base class for all MCP test cases across Tiers 1-4."""

    access_mode: str = "read-write"
    project_path: Optional[str] = None
    worker_path: Optional[str] = None
    use_mock_server: bool = False
    max_item_chars: Optional[int] = None
    max_document_chars: Optional[int] = None
    extra_env: Optional[Dict[str, str]] = None

    def setUp(self):
        super().setUp()
        config = self.get_server_config()
        self.client = McpClient(config)
        self.client.start()

    def tearDown(self):
        if hasattr(self, "client") and self.client:
            self.client.close()
        super().tearDown()

    def get_server_config(self) -> ServerConfig:
        return ServerConfig(
            access_mode=self.access_mode,
            project_path=self.project_path,
            worker_path=self.worker_path,
            max_item_chars=self.max_item_chars,
            max_document_chars=self.max_document_chars,
            extra_env=self.extra_env,
            use_mock_server=self.use_mock_server,
        )

    def init_session(
        self,
        protocol_version: str = "2024-11-05",
        capabilities: Optional[Dict[str, Any]] = None,
        client_info: Optional[Dict[str, Any]] = None,
        timeout: float = 5.0
    ) -> Dict[str, Any]:
        """Convenience helper to complete the initialize handshake and send initialized notification."""
        init_res = self.client.initialize(
            protocol_version=protocol_version,
            capabilities=capabilities,
            client_info=client_info,
            timeout=timeout
        )
        self.client.initialized_notification()
        return init_res

    def list_tools(self, timeout: float = 5.0) -> List[Dict[str, Any]]:
        return self.client.list_tools(timeout=timeout)

    def call_tool(self, name: str, arguments: Optional[Dict[str, Any]] = None, timeout: float = 10.0) -> Dict[str, Any]:
        return self.client.call_tool(name=name, arguments=arguments, timeout=timeout)
