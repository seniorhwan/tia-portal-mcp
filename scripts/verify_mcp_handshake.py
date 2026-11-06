#!/usr/bin/env python3
"""
Automated Protocol Handshake Verification Script for TIA Portal MCP Server.

Validates the full JSON-RPC 2.0 stdio lifecycle:
  1. `initialize` request (protocolVersion 2024-11-05, capabilities, serverInfo).
  2. `notifications/initialized` notification (process liveness, zero stdout noise).
  3. `tools/list` request (tool enumeration, count verification, schema validation).
  4. `tools/call` request (`get_project_status`, response format, error preservation).
  5. Graceful shutdown on stdin EOF (exit code 0 propagation).

Supports testing both:
  - Antigravity wrapper script (`scripts/run-tia-mcp.bat`)
  - Direct compiled server binary (`TiaMcpServer.exe` or `dotnet TiaMcpServer.dll`)

Usage:
  python scripts/verify_mcp_handshake.py [--mock] [--access-mode {read-write,read-only,full}] [--target PATH]
"""

import argparse
import json
import os
import queue
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

PROTOCOL_VERSION = "2024-11-05"
SERVER_NAME = "TiaMcpServer"

CANONICAL_READ_TOOLS = [
    "bind_project",
    "browse_project_tree",
    "get_project_status",
    "hmi_read",
    "network_read",
    "plc_read",
    "read_cross_references",
    "vci_read",
]

CANONICAL_WRITE_TOOLS = [
    "archive_project",
    "close_project",
    "compile_check",
    "create_project",
    "hmi_write",
    "network_write",
    "open_project",
    "plc_write",
    "save_project",
    "save_project_as",
    "vci_write",
]

ALL_19_TOOLS = sorted(CANONICAL_READ_TOOLS + CANONICAL_WRITE_TOOLS)


class Ansi:
    """Terminal styling helper with automatic Windows VT100 support."""

    def __init__(self, enable_color: bool = True):
        self.enabled = enable_color and sys.stdout.isatty()
        if self.enabled and sys.platform == "win32":
            try:
                import ctypes
                kernel32 = ctypes.windll.kernel32
                mode = ctypes.c_ulong()
                handle = kernel32.GetStdHandle(-11)  # STD_OUTPUT_HANDLE
                kernel32.GetConsoleMode(handle, ctypes.byref(mode))
                kernel32.SetConsoleMode(handle, mode.value | 0x0004)  # ENABLE_VIRTUAL_TERMINAL_PROCESSING
            except Exception:
                self.enabled = False

    def green(self, text: str) -> str:
        return f"\033[92m{text}\033[0m" if self.enabled else text

    def red(self, text: str) -> str:
        return f"\033[91m{text}\033[0m" if self.enabled else text

    def yellow(self, text: str) -> str:
        return f"\033[93m{text}\033[0m" if self.enabled else text

    def cyan(self, text: str) -> str:
        return f"\033[96m{text}\033[0m" if self.enabled else text

    def bold(self, text: str) -> str:
        return f"\033[1m{text}\033[0m" if self.enabled else text

    def dim(self, text: str) -> str:
        return f"\033[2m{text}\033[0m" if self.enabled else text

    def pass_badge(self) -> str:
        return self.green("[PASS]")

    def fail_badge(self) -> str:
        return self.red("[FAIL]")

    def warn_badge(self) -> str:
        return self.yellow("[WARN]")

    def info_badge(self) -> str:
        return self.cyan("[INFO]")


class McpSession:
    """Manages the stdio process lifecycle and JSON-RPC framing."""

    def __init__(self, cmd: List[str], env: Dict[str, str], cwd: str, timeout: float = 10.0, verbose: bool = False):
        self.cmd = cmd
        self.env = env
        self.cwd = cwd
        self.timeout = timeout
        self.verbose = verbose
        self.process: Optional[subprocess.Popen] = None
        self._stdout_queue: queue.Queue = queue.Queue()
        self._stderr_lines: List[str] = []
        self._stdout_raw_lines: List[str] = []
        self._req_id = 0
        self._clean_stdout = True
        self._dirty_stdout_reasons: List[str] = []

    def start(self):
        try:
            self.process = subprocess.Popen(
                self.cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                env=self.env,
                cwd=self.cwd
            )
        except Exception as e:
            raise RuntimeError(f"Failed to spawn server process '{' '.join(self.cmd)}': {e}") from e

        def _read_stdout():
            try:
                for line in iter(self.process.stdout.readline, ''):
                    if line:
                        self._stdout_raw_lines.append(line)
                        self._stdout_queue.put(line)
            except Exception:
                pass
            finally:
                self._stdout_queue.put(None)

        def _read_stderr():
            try:
                for line in iter(self.process.stderr.readline, ''):
                    if line:
                        stripped = line.rstrip('\r\n')
                        self._stderr_lines.append(stripped)
                        if self.verbose:
                            print(f"       [stderr] {stripped}", file=sys.stderr)
            except Exception:
                pass

        threading.Thread(target=_read_stdout, daemon=True).start()
        threading.Thread(target=_read_stderr, daemon=True).start()

    def send_request(self, method: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        self._req_id += 1
        req_id = self._req_id
        req = {
            "jsonrpc": "2.0",
            "id": req_id,
            "method": method,
            "params": params or {}
        }
        line = json.dumps(req, separators=(',', ':')) + '\n'

        if self.process.poll() is not None:
            raise RuntimeError(f"Server process terminated prematurely with exit code {self.process.poll()}")

        self.process.stdin.write(line)
        self.process.stdin.flush()

        resp_line = self._read_next_stdout_line()
        try:
            resp_obj = json.loads(resp_line)
        except json.JSONDecodeError as jde:
            self._clean_stdout = False
            self._dirty_stdout_reasons.append(f"Non-JSON stdout line: {resp_line.strip()[:150]}")
            raise RuntimeError(f"Server stdout contained non-JSON line: '{resp_line.strip()[:200]}'") from jde

        return resp_obj

    def send_notification(self, method: str, params: Optional[Dict[str, Any]] = None):
        msg = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params or {}
        }
        line = json.dumps(msg, separators=(',', ':')) + '\n'

        if self.process.poll() is not None:
            raise RuntimeError(f"Server process terminated prematurely with exit code {self.process.poll()}")

        self.process.stdin.write(line)
        self.process.stdin.flush()

    def _read_next_stdout_line(self) -> str:
        deadline = time.time() + self.timeout
        while time.time() < deadline:
            remaining = max(0.05, deadline - time.time())
            try:
                line = self._stdout_queue.get(timeout=remaining)
            except queue.Empty:
                break

            if line is None:
                recent_stderr = "\n".join(self._stderr_lines[-10:])
                raise RuntimeError(
                    f"Server closed stdout unexpectedly (exit code: {self.process.poll()}). Stderr:\n{recent_stderr}"
                )

            stripped = line.strip()
            if not stripped:
                continue

            return stripped

        recent_stderr = "\n".join(self._stderr_lines[-5:])
        raise TimeoutError(f"Timed out after {self.timeout}s waiting for response. Recent stderr:\n{recent_stderr}")

    def close_and_wait(self, timeout: float = 3.0) -> int:
        if self.process is None:
            return 0
        try:
            if self.process.stdin and not self.process.stdin.closed:
                self.process.stdin.close()
        except Exception:
            pass

        try:
            return self.process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            self.process.terminate()
            try:
                return self.process.wait(timeout=2.0)
            except subprocess.TimeoutExpired:
                self.process.kill()
                return self.process.wait()

    @property
    def stderr_lines(self) -> List[str]:
        return list(self._stderr_lines)

    @property
    def is_stdout_clean(self) -> bool:
        return self._clean_stdout


def resolve_server_target(target: Optional[str], access_mode: str, mock: bool, root_dir: Path) -> Tuple[List[str], Dict[str, str], str]:
    """Resolves target executable or launch script and constructs execution arguments."""
    env = os.environ.copy()
    env["TIA_MCP_ACCESS_MODE"] = access_mode
    if mock:
        env["TIA_MCP_USE_FAKE_WORKER"] = "1"

    cmd: List[str] = []

    if target:
        target_path = Path(target)
        if not target_path.is_absolute():
            target_path = (root_dir / target_path).resolve()
        if not target_path.exists():
            raise FileNotFoundError(f"Specified target path does not exist: {target_path}")

        ext = target_path.suffix.lower()
        if ext in (".bat", ".cmd"):
            cmd = ["cmd.exe", "/c", str(target_path)]
        elif ext == ".dll":
            cmd = ["dotnet", str(target_path)]
        elif ext == ".exe":
            cmd = [str(target_path)]
        else:
            cmd = [str(target_path)]
    else:
        # Auto-detect target candidates in priority order
        bat_candidate = root_dir / "scripts" / "run-tia-mcp.bat"
        exe_release = root_dir / "TiaMcpServer" / "bin" / "Release" / "net10.0" / "TiaMcpServer.exe"
        exe_debug = root_dir / "TiaMcpServer" / "bin" / "Debug" / "net10.0" / "TiaMcpServer.exe"
        dll_release = root_dir / "TiaMcpServer" / "bin" / "Release" / "net10.0" / "TiaMcpServer.dll"
        dll_debug = root_dir / "TiaMcpServer" / "bin" / "Debug" / "net10.0" / "TiaMcpServer.dll"

        if bat_candidate.is_file():
            cmd = ["cmd.exe", "/c", str(bat_candidate)]
        elif exe_release.is_file():
            cmd = [str(exe_release)]
        elif exe_debug.is_file():
            cmd = [str(exe_debug)]
        elif dll_release.is_file():
            cmd = ["dotnet", str(dll_release)]
        elif dll_debug.is_file():
            cmd = ["dotnet", str(dll_debug)]
        else:
            raise FileNotFoundError(
                "Could not auto-detect TiaMcpServer binary or launcher script. "
                "Build the solution ('dotnet build TiaMcpServer.slnx') or specify --target explicitly."
            )

    # Append flags if not already present
    if "--access-mode" not in cmd and "--read-only" not in cmd and "--read-write" not in cmd:
        cmd.extend(["--access-mode", access_mode])
    if mock and "--mock" not in cmd:
        cmd.append("--mock")

    return cmd, env, str(root_dir)


def run_verification(args) -> int:
    """Executes the full 5-step MCP protocol handshake verification."""
    ansi = Ansi(enable_color=not args.no_color)
    root_dir = Path(__file__).resolve().parents[1]

    print(ansi.bold(ansi.cyan("======================================================================")))
    print(ansi.bold(ansi.cyan(" TIA Portal MCP Server - Automated Protocol Handshake Verification    ")))
    print(ansi.bold(ansi.cyan("======================================================================")))

    try:
        cmd, env, cwd = resolve_server_target(args.target, args.access_mode, args.mock, root_dir)
    except Exception as e:
        print(f"{ansi.fail_badge()} Target resolution error: {e}")
        return 1

    print(f"{ansi.info_badge()} Target Command : {' '.join(cmd)}")
    print(f"{ansi.info_badge()} Access Mode    : {args.access_mode}")
    print(f"{ansi.info_badge()} Mock Mode       : {'ENABLED' if args.mock else 'DISABLED (Live/Absent-TIA)'}")
    print(f"{ansi.info_badge()} Working Dir    : {cwd}")
    print("----------------------------------------------------------------------")

    session = McpSession(cmd, env, cwd, timeout=args.timeout, verbose=args.verbose)
    steps_passed = 0
    total_steps = 5
    start_time = time.time()

    # Step 1: Initialize
    t0 = time.time()
    step1_name = "1. MCP Protocol Handshake (`initialize`)"
    try:
        session.start()
        init_resp = session.send_request("initialize", {
            "protocolVersion": PROTOCOL_VERSION,
            "capabilities": {"tools": {"listChanged": False}},
            "clientInfo": {"name": "verify-mcp-handshake", "version": "1.0.0"}
        })
        d1 = (time.time() - t0) * 1000

        if "error" in init_resp:
            raise RuntimeError(f"Server returned error on initialize: {init_resp['error']}")
        res = init_resp.get("result", {})
        if res.get("protocolVersion") != PROTOCOL_VERSION:
            raise ValueError(f"Expected protocolVersion '{PROTOCOL_VERSION}', got '{res.get('protocolVersion')}'")
        sinfo = res.get("serverInfo", {})
        if sinfo.get("name") != SERVER_NAME:
            raise ValueError(f"Expected serverInfo.name '{SERVER_NAME}', got '{sinfo.get('name')}'")
        if not sinfo.get("version"):
            raise ValueError("serverInfo.version is missing or empty")
        if "tools" not in res.get("capabilities", {}):
            raise ValueError("capabilities missing 'tools' key")

        print(f"{ansi.pass_badge()} {step1_name} ({d1:.1f}ms)")
        print(f"       Server: {sinfo.get('name')} v{sinfo.get('version')}, Protocol: {res.get('protocolVersion')}")
        steps_passed += 1
    except Exception as e:
        d1 = (time.time() - t0) * 1000
        print(f"{ansi.fail_badge()} {step1_name} ({d1:.1f}ms): {e}")
        session.close_and_wait()
        return 1

    # Step 2: Initialized notification
    t0 = time.time()
    step2_name = "2. Lifecycle Acknowledgment (`notifications/initialized`)"
    try:
        session.send_notification("notifications/initialized")
        d2 = (time.time() - t0) * 1000
        print(f"{ansi.pass_badge()} {step2_name} ({d2:.1f}ms)")
        print("       Notification sent successfully; process remains receptive")
        steps_passed += 1
    except Exception as e:
        d2 = (time.time() - t0) * 1000
        print(f"{ansi.fail_badge()} {step2_name} ({d2:.1f}ms): {e}")
        session.close_and_wait()
        return 1

    # Step 3: Tools list
    t0 = time.time()
    step3_name = "3. Tool Enumeration & Schema Audit (`tools/list`)"
    try:
        list_resp = session.send_request("tools/list", {})
        d3 = (time.time() - t0) * 1000
        if "error" in list_resp:
            raise RuntimeError(f"tools/list error: {list_resp['error']}")
        tools = list_resp.get("result", {}).get("tools", [])
        tool_names = [t.get("name") for t in tools]

        expected_count = 8 if args.access_mode == "read-only" else 19
        if len(tools) != expected_count:
            raise ValueError(f"Expected {expected_count} tools in {args.access_mode} mode, but found {len(tools)}: {tool_names}")

        # Verify schema validity for all returned tools
        for tool in tools:
            t_name = tool.get("name")
            if not t_name:
                raise ValueError("Tool definition missing 'name'")
            if not tool.get("description"):
                raise ValueError(f"Tool '{t_name}' missing 'description'")
            schema = tool.get("inputSchema", {})
            if schema.get("type") != "object":
                raise ValueError(f"Tool '{t_name}' inputSchema.type must be 'object', got '{schema.get('type')}'")
            if "properties" not in schema:
                raise ValueError(f"Tool '{t_name}' inputSchema missing 'properties' dictionary")

        # Verify access mode partitioning
        if args.access_mode == "read-only":
            for wt in CANONICAL_WRITE_TOOLS:
                if wt in tool_names:
                    raise ValueError(f"Write tool '{wt}' leaked into read-only tools list!")
            for rt in CANONICAL_READ_TOOLS:
                if rt not in tool_names:
                    raise ValueError(f"Expected read tool '{rt}' missing from read-only tools list")
        else:
            for t in ALL_19_TOOLS:
                if t not in tool_names:
                    raise ValueError(f"Expected tool '{t}' missing from tool list")

        print(f"{ansi.pass_badge()} {step3_name} ({d3:.1f}ms)")
        print(f"       Enumerated {len(tools)} tools conforming to MCP schemas in '{args.access_mode}' mode")
        steps_passed += 1
    except Exception as e:
        d3 = (time.time() - t0) * 1000
        print(f"{ansi.fail_badge()} {step3_name} ({d3:.1f}ms): {e}")
        session.close_and_wait()
        return 1

    # Step 4: Tool call (get_project_status)
    t0 = time.time()
    step4_name = "4. Tool Invocation & Diagnostics (`tools/call get_project_status`)"
    try:
        call_resp = session.send_request("tools/call", {"name": "get_project_status", "arguments": {}})
        d4 = (time.time() - t0) * 1000
        if "error" in call_resp:
            raise RuntimeError(f"tools/call returned JSON-RPC error: {call_resp['error']}")
        result = call_resp.get("result", {})
        if "content" not in result or not isinstance(result["content"], list):
            raise ValueError(f"Expected 'content' list in tool result: {result}")
        if len(result["content"]) == 0:
            raise ValueError("Tool result 'content' list is empty")

        struct = result.get("structuredContent")
        status_desc = "unknown"
        if struct and isinstance(struct, dict):
            if struct.get("contractVersion") != "1.0":
                raise ValueError(f"Expected contractVersion '1.0', got '{struct.get('contractVersion')}'")
            if struct.get("tool") != "get_project_status":
                raise ValueError(f"Expected tool 'get_project_status', got '{struct.get('tool')}'")
            res_sub = struct.get("result", {})
            if res_sub and isinstance(res_sub, dict):
                status_desc = res_sub.get("status", "unknown")
            elif struct.get("failure"):
                status_desc = f"failure ({struct.get('failure', {}).get('category')})"

        print(f"{ansi.pass_badge()} {step4_name} ({d4:.1f}ms)")
        print(f"       Outcome: status='{status_desc}', isError={result.get('isError')}, structured={bool(struct)}")
        steps_passed += 1
    except Exception as e:
        d4 = (time.time() - t0) * 1000
        print(f"{ansi.fail_badge()} {step4_name} ({d4:.1f}ms): {e}")
        session.close_and_wait()
        return 1

    # Step 5: Graceful shutdown
    t0 = time.time()
    step5_name = "5. Graceful Shutdown & Exit Code Propagation"
    try:
        exit_code = session.close_and_wait(timeout=3.0)
        d5 = (time.time() - t0) * 1000
        if exit_code != 0:
            raise RuntimeError(f"Server exited with non-zero exit code: {exit_code}")
        print(f"{ansi.pass_badge()} {step5_name} ({d5:.1f}ms)")
        print("       Process terminated cleanly on stdin EOF with exit code 0")
        steps_passed += 1
    except Exception as e:
        d5 = (time.time() - t0) * 1000
        print(f"{ansi.fail_badge()} {step5_name} ({d5:.1f}ms): {e}")
        return 1

    # Stdio cleanliness check
    if not session.is_stdout_clean:
        print(f"{ansi.fail_badge()} Stdio Framing Contamination detected on stdout:")
        for reason in session._dirty_stdout_reasons:
            print(f"       - {reason}")
        return 1

    total_duration = time.time() - start_time
    print("----------------------------------------------------------------------")
    print(f"{ansi.bold(ansi.green('ALL MCP PROTOCOL VERIFICATION CHECKS PASSED'))} ({steps_passed}/{total_steps} in {total_duration:.2f}s)")
    print(ansi.bold(ansi.cyan("======================================================================")))
    return 0


def main():
    parser = argparse.ArgumentParser(description="Automated MCP Protocol Handshake Verification Script")
    parser.add_argument("--target", help="Path to server executable, batch script (.bat), or dll (.dll)")
    parser.add_argument("--access-mode", choices=["read-write", "read-only", "full"], default="read-write", help="Access mode to test (default: read-write)")
    parser.add_argument("--mock", action="store_true", help="Run with mock worker or offline simulator")
    parser.add_argument("--timeout", type=float, default=10.0, help="Per-operation response timeout in seconds (default: 10.0)")
    parser.add_argument("--no-color", action="store_true", help="Disable ANSI color output")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose diagnostic logs")

    args = parser.parse_args()
    return run_verification(args)


if __name__ == "__main__":
    sys.exit(main())
