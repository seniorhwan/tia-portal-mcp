"""
Server configuration and command resolution for MCP E2E tests.
"""

import os
import sys
from pathlib import Path
from typing import List, Optional, Dict


class ServerConfig:
    """Configuration settings for launching an MCP server instance."""

    def __init__(
        self,
        command: Optional[List[str]] = None,
        access_mode: str = "read-write",
        project_path: Optional[str] = None,
        worker_path: Optional[str] = None,
        max_item_chars: Optional[int] = None,
        max_document_chars: Optional[int] = None,
        worker_timeout_minutes: Optional[int] = None,
        extra_env: Optional[Dict[str, str]] = None,
        use_mock_server: bool = False,
    ):
        self.command = command
        self.access_mode = access_mode
        self.project_path = project_path
        self.worker_path = worker_path
        self.max_item_chars = max_item_chars
        self.max_document_chars = max_document_chars
        self.worker_timeout_minutes = worker_timeout_minutes
        self.extra_env = extra_env or {}
        self.use_mock_server = use_mock_server

    def build_command(self) -> List[str]:
        """Build the full command line arguments list."""
        if self.use_mock_server:
            cmd = [sys.executable, "-m", "tests.e2e.harness.mock_server"]
        elif self.command:
            cmd = list(self.command)
        else:
            cmd = resolve_server_command()

        # Append access mode if supported and not already present
        if "--access-mode" not in cmd and "--read-only" not in cmd and "--read-write" not in cmd:
            cmd.extend(["--access-mode", self.access_mode])

        if self.project_path and "--project" not in cmd:
            cmd.extend(["--project", self.project_path])

        if self.max_item_chars is not None and "--max-item-chars" not in cmd:
            cmd.extend(["--max-item-chars", str(self.max_item_chars)])

        if self.max_document_chars is not None and "--max-document-chars" not in cmd:
            cmd.extend(["--max-document-chars", str(self.max_document_chars)])

        if self.worker_timeout_minutes is not None and "--worker-timeout-minutes" not in cmd:
            cmd.extend(["--worker-timeout-minutes", str(self.worker_timeout_minutes)])

        return cmd

    def build_env(self) -> Dict[str, str]:
        """Build environment variables dictionary."""
        env = os.environ.copy()
        if self.worker_path:
            env["TIA_MCP_WORKER_PATH"] = self.worker_path
        if self.project_path:
            env["TIA_MCP_PROJECT_PATH"] = self.project_path
        if self.access_mode:
            env["TIA_MCP_ACCESS_MODE"] = self.access_mode
        env.update(self.extra_env)
        return env


def resolve_server_command() -> List[str]:
    """
    Auto-detect the appropriate MCP server command.
    Checks environment, project scripts, prebuilt artifacts, or falls back to
    the embedded mock server oracle.
    """
    # 1. Explicit env var
    env_cmd = os.environ.get("TIA_MCP_SERVER_COMMAND")
    if env_cmd:
        import shlex
        return shlex.split(env_cmd)

    # 2. Check run-tia-mcp.bat in scripts/
    workspace_root = Path(__file__).resolve().parents[3]
    bat_path = workspace_root / "scripts" / "run-tia-mcp.bat"
    if bat_path.is_file():
        return ["cmd.exe", "/c", str(bat_path)]

    # 3. Check artifacts/tia-mcp.exe
    exe_path = workspace_root / "artifacts" / "tia-mcp.exe"
    if exe_path.is_file():
        return [str(exe_path)]

    # 4. Check TiaMcpServer.exe in bin/Release/net10.0 or TiaMcpServer.dll in bin/Debug/net10.0
    release_exe = workspace_root / "TiaMcpServer" / "bin" / "Release" / "net10.0" / "TiaMcpServer.exe"
    if release_exe.is_file():
        return [str(release_exe)]

    dll_path = workspace_root / "TiaMcpServer" / "bin" / "Debug" / "net10.0" / "TiaMcpServer.dll"
    if dll_path.is_file():
        return ["dotnet", str(dll_path)]

    # 5. Fallback: Embedded Python Mock Server Oracle
    return [sys.executable, "-m", "tests.e2e.harness.mock_server"]
