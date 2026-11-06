"""
Opaque-box Black-box JSON-RPC 2.0 stdio client for TIA Portal MCP server.
Works on Windows and POSIX using standard library subprocess and threading queues.
"""

import subprocess
import threading
import queue
import json
import time
from typing import Dict, Any, List, Optional
from .errors import McpTimeoutError, McpProtocolError, McpProcessError
from .config import ServerConfig


class McpClient:
    """Manages the lifecycle of an MCP server process over standard I/O."""

    def __init__(self, config: Optional[ServerConfig] = None):
        self.config = config or ServerConfig()
        self.process: Optional[subprocess.Popen] = None
        self._stdout_queue: queue.Queue = queue.Queue()
        self._stderr_lines: List[str] = []
        self._stdout_thread: Optional[threading.Thread] = None
        self._stderr_thread: Optional[threading.Thread] = None
        self._request_counter = 0
        self._is_closed = False

    @property
    def stderr_lines(self) -> List[str]:
        return list(self._stderr_lines)

    @property
    def is_alive(self) -> bool:
        return self.process is not None and self.process.poll() is None

    @property
    def exit_code(self) -> Optional[int]:
        if self.process is None:
            return None
        return self.process.poll()

    def start(self):
        """Starts the MCP server process and launches stream reader threads."""
        cmd = self.config.build_command()
        env = self.config.build_env()

        try:
            self.process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                env=env,
            )
        except Exception as e:
            raise McpProcessError(f"Failed to start MCP server command {cmd}: {e}") from e

        # Background thread to read stdout line by line into thread-safe queue
        def _read_stdout():
            try:
                for line in iter(self.process.stdout.readline, ''):
                    if line:
                        self._stdout_queue.put(line)
            except Exception:
                pass
            finally:
                self._stdout_queue.put(None)  # Sentinel for EOF

        # Background thread to capture stderr lines for diagnostics
        def _read_stderr():
            try:
                for line in iter(self.process.stderr.readline, ''):
                    if line:
                        self._stderr_lines.append(line.rstrip('\r\n'))
            except Exception:
                pass

        self._stdout_thread = threading.Thread(target=_read_stdout, daemon=True)
        self._stderr_thread = threading.Thread(target=_read_stderr, daemon=True)
        self._stdout_thread.start()
        self._stderr_thread.start()

    def send_raw(self, raw_string: str, timeout: float = 5.0) -> Dict[str, Any]:
        """
        Sends raw string over stdin and waits for a single JSON line on stdout.
        Used for boundary tests (malformed JSON, unclosed quotes, etc.).
        """
        if not self.is_alive:
            raise McpProcessError("Server process is not running")

        if not raw_string.endswith('\n'):
            raw_string += '\n'

        try:
            self.process.stdin.write(raw_string)
            self.process.stdin.flush()
        except (BrokenPipeError, OSError) as e:
            raise McpProcessError(f"Failed to write to server stdin: {e}") from e

        return self._read_next_json(timeout=timeout)

    def send_notification(self, method: str, params: Optional[Dict[str, Any]] = None):
        """Sends a JSON-RPC 2.0 notification (no 'id' field, expects no response)."""
        if not self.is_alive:
            raise McpProcessError("Server process is not running")

        msg = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params or {}
        }
        line = json.dumps(msg, separators=(',', ':')) + '\n'
        try:
            self.process.stdin.write(line)
            self.process.stdin.flush()
        except (BrokenPipeError, OSError) as e:
            raise McpProcessError(f"Failed to write notification to stdin: {e}") from e

    def send_request(self, method: str, params: Optional[Dict[str, Any]] = None, timeout: float = 5.0) -> Dict[str, Any]:
        """
        Sends a standard JSON-RPC 2.0 request and returns the 'result' object.
        Raises McpProtocolError if the server returns an 'error' object.
        """
        self._request_counter += 1
        req_id = self._request_counter

        msg = {
            "jsonrpc": "2.0",
            "id": req_id,
            "method": method,
            "params": params or {}
        }
        line = json.dumps(msg, separators=(',', ':')) + '\n'

        if not self.is_alive:
            raise McpProcessError(f"Server exited before sending request '{method}'")

        try:
            self.process.stdin.write(line)
            self.process.stdin.flush()
        except (BrokenPipeError, OSError) as e:
            raise McpProcessError(f"Failed to write request '{method}' to stdin: {e}") from e

        resp = self._read_next_json(timeout=timeout)

        if "error" in resp:
            err = resp["error"]
            raise McpProtocolError(
                code=err.get("code", -1),
                message=err.get("message", "Unknown error"),
                data=err.get("data"),
                response_id=resp.get("id")
            )

        if "result" not in resp:
            raise McpProtocolError(
                code=-32603,
                message="Response missing both 'result' and 'error' keys",
                data=resp,
                response_id=resp.get("id")
            )

        return resp["result"]

    def _read_next_json(self, timeout: float = 5.0) -> Dict[str, Any]:
        """Reads the next available JSON response line from stdout queue."""
        deadline = time.time() + timeout
        while time.time() < deadline:
            remaining = max(0.05, deadline - time.time())
            try:
                line = self._stdout_queue.get(timeout=remaining)
            except queue.Empty:
                break

            if line is None:
                # EOF reached
                stderr_summary = "\n".join(self._stderr_lines[-10:])
                raise McpProcessError(f"Server closed stdout (process exited with code {self.process.poll()}). Stderr:\n{stderr_summary}")

            line_str = line.strip()
            if not line_str:
                continue

            try:
                return json.loads(line_str)
            except json.JSONDecodeError as jde:
                raise McpProtocolError(
                    code=-32700,
                    message=f"Received non-JSON line from server stdout: {line_str[:200]}",
                    data=str(jde)
                )

        stderr_summary = "\n".join(self._stderr_lines[-5:])
        raise McpTimeoutError(f"Timed out after {timeout}s waiting for response. Recent stderr:\n{stderr_summary}")

    def initialize(
        self,
        protocol_version: str = "2024-11-05",
        capabilities: Optional[Dict[str, Any]] = None,
        client_info: Optional[Dict[str, Any]] = None,
        timeout: float = 5.0
    ) -> Dict[str, Any]:
        """Convenience method to perform the standard MCP initialize handshake."""
        params = {
            "protocolVersion": protocol_version,
            "capabilities": capabilities or {},
            "clientInfo": client_info or {"name": "tia-mcp-e2e-tester", "version": "1.0.0"}
        }
        return self.send_request("initialize", params, timeout=timeout)

    def initialized_notification(self):
        """Sends notifications/initialized."""
        self.send_notification("notifications/initialized")

    def list_tools(self, timeout: float = 5.0) -> List[Dict[str, Any]]:
        """Convenience method to list tools."""
        res = self.send_request("tools/list", {}, timeout=timeout)
        return res.get("tools", [])

    def call_tool(self, name: str, arguments: Optional[Dict[str, Any]] = None, timeout: float = 10.0) -> Dict[str, Any]:
        """Convenience method to invoke a tool via tools/call."""
        params = {
            "name": name,
            "arguments": arguments or {}
        }
        return self.send_request("tools/call", params, timeout=timeout)

    def close(self):
        """Cleanly closes the client and terminates the server process."""
        if self._is_closed:
            return
        self._is_closed = True

        if self.process is not None:
            try:
                if self.process.stdin and not self.process.stdin.closed:
                    self.process.stdin.close()
            except Exception:
                pass

            try:
                self.process.wait(timeout=2.0)
            except subprocess.TimeoutExpired:
                self.process.terminate()
                try:
                    self.process.wait(timeout=1.0)
                except subprocess.TimeoutExpired:
                    self.process.kill()

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
