"""
Reference Python Mock Server Oracle for TIA Portal MCP Server.
Implements the exact JSON-RPC 2.0 stdio specification, access modes,
19 tool schemas, boundary validations, and FakeWorker-compatible responses.
"""

import sys
import json
import os
import argparse
from typing import Dict, Any, List, Optional

PROTOCOL_VERSION = "2024-11-05"
SERVER_NAME = "TiaMcpServer"
SERVER_VERSION = "4.3.0"

READ_ONLY_TOOLS = [
    "bind_project",
    "browse_project_tree",
    "get_project_status",
    "hmi_read",
    "network_read",
    "plc_read",
    "read_cross_references",
    "vci_read",
]

WRITE_TOOLS = [
    "compile_check",
    "open_project",
    "create_project",
    "save_project",
    "save_project_as",
    "archive_project",
    "close_project",
    "plc_write",
    "network_write",
    "hmi_write",
    "vci_write",
]

ALL_TOOLS = sorted(READ_ONLY_TOOLS + WRITE_TOOLS)

TOOL_DEFINITIONS = {
    "bind_project": {
        "description": "Binds MCP session to an already-open TIA project or lists open candidate projects.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "projectPath": {"type": "string", "description": "Path to project"},
                "portalProcessId": {"type": "integer", "description": "Process ID of TIA Portal"},
                "forceRebind": {"type": "boolean", "default": False}
            },
            "additionalProperties": False
        }
    },
    "get_project_status": {
        "description": "Returns active project metadata, save status, and attached process ID.",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "additionalProperties": False
        }
    },
    "browse_project_tree": {
        "description": "Browses a point-in-time tree of the bound TIA project.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "startSelector": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "nodeType": {"type": "string"},
                            "name": {"type": "string"}
                        },
                        "required": ["name", "nodeType"],
                        "additionalProperties": False
                    }
                },
                "depth": {"type": "integer", "minimum": 1, "default": 1},
                "pageSize": {"type": "integer", "minimum": 1, "maximum": 200, "default": 100},
                "cursor": {"type": "string"}
            },
            "additionalProperties": False
        }
    },
    "open_project": {
        "description": "Opens an existing project file (.ap21/.als21) and binds the session to it.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "projectPath": {"type": "string"},
                "dryRun": {"type": "boolean", "default": False},
                "forceRebind": {"type": "boolean", "default": False}
            },
            "required": ["projectPath"],
            "additionalProperties": False
        }
    },
    "create_project": {
        "description": "Creates a new TIA Portal project at target directory and binds the session.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "projectDirectory": {"type": "string"},
                "projectName": {"type": "string"},
                "author": {"type": "string"},
                "comment": {"type": "string"},
                "dryRun": {"type": "boolean", "default": False}
            },
            "required": ["projectDirectory", "projectName"],
            "additionalProperties": False
        }
    },
    "save_project": {
        "description": "Saves the currently active verified project or local session.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "dryRun": {"type": "boolean", "default": False}
            },
            "additionalProperties": False
        }
    },
    "save_project_as": {
        "description": "Saves active project to a new copy directory and rebinds session.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "targetDirectory": {"type": "string"},
                "targetName": {"type": "string"},
                "rebind": {"type": "boolean"},
                "dryRun": {"type": "boolean", "default": False}
            },
            "required": ["targetDirectory", "targetName", "rebind"],
            "additionalProperties": False
        }
    },
    "archive_project": {
        "description": "Archives the active verified project to a compressed file.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "archiveDirectory": {"type": "string"},
                "archiveName": {"type": "string"},
                "mode": {"type": "string"},
                "saveBeforeArchive": {"type": "boolean", "default": True},
                "dryRun": {"type": "boolean", "default": False}
            },
            "required": ["archiveDirectory", "archiveName"],
            "additionalProperties": False
        }
    },
    "close_project": {
        "description": "Closes active project and clears the MCP session binding.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "saveBeforeClose": {"type": "boolean", "default": True},
                "dryRun": {"type": "boolean", "default": False}
            },
            "additionalProperties": False
        }
    },
    "compile_check": {
        "description": "Compiles a PLC, software unit, or specific block scope and returns messages.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "plcName": {"type": "string"},
                "blockPath": {"type": "string"}
            },
            "additionalProperties": False
        }
    },
    "plc_read": {
        "description": "Executes up to 50 independent PLC read operations.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "operations": {
                    "type": "array",
                    "maxItems": 50,
                    "items": {"type": "object"}
                }
            },
            "required": ["operations"],
            "additionalProperties": False
        }
    },
    "plc_write": {
        "description": "Executes up to 50 ordered guarded PLC software writes against bound project.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "operations": {
                    "type": "array",
                    "maxItems": 50,
                    "items": {"type": "object"}
                },
                "dryRun": {"type": "boolean", "default": False}
            },
            "required": ["operations"],
            "additionalProperties": False
        }
    },
    "read_cross_references": {
        "description": "Inspects cross-references for a project target.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "target": {"type": "object"},
                "filter": {"type": "object"},
                "maxResults": {"type": "integer", "default": 100}
            },
            "required": ["target"],
            "additionalProperties": False
        }
    },
    "network_read": {
        "description": "Executes up to 50 dedicated network reads.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "operations": {
                    "type": "array",
                    "maxItems": 50,
                    "items": {"type": "object"}
                }
            },
            "required": ["operations"],
            "additionalProperties": False
        }
    },
    "network_write": {
        "description": "Previews or applies up to 50 ordered network writes.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "operations": {
                    "type": "array",
                    "maxItems": 50,
                    "items": {"type": "object"}
                },
                "dryRun": {"type": "boolean", "default": False}
            },
            "required": ["operations"],
            "additionalProperties": False
        }
    },
    "hmi_read": {
        "description": "Executes up to 50 read-only WinCC Unified HMI operations.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "operations": {
                    "type": "array",
                    "maxItems": 50,
                    "items": {"type": "object"}
                }
            },
            "required": ["operations"],
            "additionalProperties": False
        }
    },
    "hmi_write": {
        "description": "Previews or applies up to 50 ordered WinCC Unified HMI writes.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "operations": {
                    "type": "array",
                    "maxItems": 50,
                    "items": {"type": "object"}
                },
                "dryRun": {"type": "boolean", "default": False}
            },
            "required": ["operations"],
            "additionalProperties": False
        }
    },
    "vci_read": {
        "description": "Inspects standalone-project VCI workspaces and leaf mappings.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "operations": {
                    "type": "array",
                    "maxItems": 50,
                    "items": {"type": "object"}
                }
            },
            "required": ["operations"],
            "additionalProperties": False
        }
    },
    "vci_write": {
        "description": "Previews or applies up to 50 ordered VCI operations.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "operations": {
                    "type": "array",
                    "maxItems": 50,
                    "items": {"type": "object"}
                },
                "dryRun": {"type": "boolean", "default": False}
            },
            "required": ["operations"],
            "additionalProperties": False
        }
    }
}


class MockServerState:
    def __init__(self, access_mode: str = "read-write", startup_project: Optional[str] = None):
        self.access_mode = access_mode
        self.bound_project_path = startup_project
        self.initialized = False
        self.audit_records: List[Dict[str, Any]] = []

    def get_exposed_tool_names(self) -> List[str]:
        if self.access_mode == "read-only":
            return list(READ_ONLY_TOOLS)
        return list(ALL_TOOLS)


def write_response(response: Dict[str, Any]):
    line = json.dumps(response, separators=(',', ':')) + '\n'
    sys.stdout.write(line)
    sys.stdout.flush()


def write_error(code: int, message: str, req_id: Any = None, data: Any = None):
    err: Dict[str, Any] = {"code": code, "message": message}
    if data is not None:
        err["data"] = data
    write_response({"jsonrpc": "2.0", "id": req_id, "error": err})


def validate_schema(schema: Dict[str, Any], args: Dict[str, Any]) -> Optional[str]:
    """Lightweight closed schema validator."""
    if not isinstance(args, dict):
        return f"Arguments must be an object, got {type(args).__name__}"

    props = schema.get("properties", {})
    required = schema.get("required", [])

    for req in required:
        if req not in args:
            return f"Missing required property: '{req}'"

    if schema.get("additionalProperties") is False:
        for key in args:
            if key not in props:
                return f"Unexpected property '{key}' violates closed schema"

    # Validate types and bounds
    for key, val in args.items():
        if key not in props:
            continue
        p_def = props[key]
        expected_type = p_def.get("type")
        if expected_type == "integer" and (not isinstance(val, int) or isinstance(val, bool)):
            return f"Property '{key}' must be an integer"
        if expected_type == "string" and not isinstance(val, str):
            return f"Property '{key}' must be a string"
        if expected_type == "boolean" and not isinstance(val, bool):
            return f"Property '{key}' must be a boolean"
        if expected_type == "array":
            if not isinstance(val, list):
                return f"Property '{key}' must be an array"
            max_items = p_def.get("maxItems")
            if max_items is not None and len(val) > max_items:
                return f"Property '{key}' exceeds maximum allowed items ({max_items})"
            if "items" in p_def and isinstance(p_def["items"], dict):
                item_def = p_def["items"]
                for item in val:
                    if isinstance(item, dict):
                        item_err = validate_schema(item_def, item)
                        if item_err:
                            return f"Item in '{key}' invalid: {item_err}"

        if "minimum" in p_def and isinstance(val, (int, float)) and val < p_def["minimum"]:
            return f"Property '{key}' is less than minimum {p_def['minimum']}"
        if "maximum" in p_def and isinstance(val, (int, float)) and val > p_def["maximum"]:
            return f"Property '{key}' exceeds maximum {p_def['maximum']}"

    return None


def execute_tool(state: MockServerState, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Simulates tool execution and produces structuredContent conforming to contract."""
    # 1. Project lifecycle & binding
    if name == "get_project_status":
        if state.bound_project_path:
            return {
                "contractVersion": "1.0",
                "tool": "get_project_status",
                "success": True,
                "result": {
                    "status": "bound",
                    "value": {
                        "name": os.path.basename(state.bound_project_path),
                        "path": state.bound_project_path,
                        "isSaved": True,
                        "portalProcessId": 1234
                    }
                },
                "warnings": [],
                "error": None
            }
        return {
            "contractVersion": "1.0",
            "tool": "get_project_status",
            "success": True,
            "result": {
                "status": "no_project",
                "value": None
            },
            "warnings": [],
            "error": None
        }

    if name == "bind_project":
        path = arguments.get("projectPath")
        force = arguments.get("forceRebind", False)
        if state.bound_project_path and not force and path != state.bound_project_path:
            return {
                "contractVersion": "1.0",
                "tool": "bind_project",
                "success": False,
                "error": {"category": "binding_conflict", "message": "Project already bound; use forceRebind=true"},
                "result": None,
                "warnings": []
            }
        if path:
            state.bound_project_path = path
            return {
                "contractVersion": "1.0",
                "tool": "bind_project",
                "success": True,
                "result": {
                    "status": "bound",
                    "projectPath": path,
                    "portalProcessId": arguments.get("portalProcessId", 4321),
                    "candidates": []
                },
                "warnings": [],
                "error": None
            }
        return {
            "contractVersion": "1.0",
            "tool": "bind_project",
            "success": True,
            "result": {
                "status": "listed",
                "projectPath": None,
                "candidates": ["Project_Offline_1.ap21", "Project_Offline_2.ap21"]
            },
            "warnings": [],
            "error": None
        }

    if name == "open_project":
        path = arguments["projectPath"]
        dry_run = arguments.get("dryRun", False)
        if dry_run:
            return {
                "phase": "preview",
                "verification": {"projectPath": path, "canOpen": True},
                "audit": {"action": "open_project", "dryRun": True}
            }
        state.bound_project_path = path
        return {
            "phase": "applied",
            "verification": {"projectPath": path, "opened": True},
            "audit": {"action": "open_project", "dryRun": False}
        }

    if name == "create_project":
        dry_run = arguments.get("dryRun", False)
        dir_path = arguments["projectDirectory"]
        p_name = arguments["projectName"]
        full_path = os.path.join(dir_path, p_name + ".ap21")
        if dry_run:
            return {"phase": "preview", "audit": {"action": "create_project", "target": full_path}}
        state.bound_project_path = full_path
        return {"phase": "applied", "audit": {"action": "create_project", "target": full_path}}

    if name in ("save_project", "close_project"):
        dry_run = arguments.get("dryRun", False)
        if not state.bound_project_path:
            return {
                "phase": "blocked",
                "failure": {"category": "binding_conflict", "message": "No active project bound"}
            }
        if name == "close_project" and not dry_run:
            state.bound_project_path = None
        return {"phase": "preview" if dry_run else "applied", "audit": {"action": name}}

    if name == "save_project_as":
        if not arguments.get("rebind"):
            return {
                "phase": "error",
                "failure": {"category": "validation_error", "message": "'rebind' must be true"}
            }
        dry_run = arguments.get("dryRun", False)
        new_path = os.path.join(arguments["targetDirectory"], arguments["targetName"] + ".ap21")
        if not dry_run:
            state.bound_project_path = new_path
        return {"phase": "preview" if dry_run else "applied", "audit": {"action": "save_project_as", "path": new_path}}

    if name == "archive_project":
        dry_run = arguments.get("dryRun", False)
        target = os.path.join(arguments["archiveDirectory"], arguments["archiveName"])
        return {"phase": "preview" if dry_run else "applied", "audit": {"action": "archive_project", "target": target}}

    if name == "browse_project_tree":
        depth = arguments.get("depth", 1)
        page_size = arguments.get("pageSize", 100)
        return {
            "contractVersion": "3.0",
            "nodes": [
                {"name": "PLC_1", "nodeType": "PlcDevice", "path": "Devices/PLC_1", "hasChildren": True},
                {"name": "ProgramBlocks", "nodeType": "Folder", "path": "Devices/PLC_1/ProgramBlocks", "hasChildren": True},
                {"name": "Main", "nodeType": "Block", "path": "Devices/PLC_1/ProgramBlocks/Main", "hasChildren": False}
            ],
            "pagination": {"nextCursor": None, "totalNodes": 3, "returnedNodes": 3, "hasMore": False},
            "warnings": [],
            "failure": None
        }

    if name == "compile_check":
        return {
            "contractVersion": "1.0",
            "tool": "compile_check",
            "success": True,
            "result": {
                "status": "succeeded",
                "value": {
                    "totalErrorCount": 0,
                    "totalWarningCount": 0,
                    "messages": []
                }
            },
            "warnings": [],
            "error": None
        }

    # Batch read / write tools
    if name in ("plc_read", "network_read", "hmi_read", "vci_read"):
        ops = arguments.get("operations", [])
        results = []
        for i, op in enumerate(ops):
            op_id = op.get("operationId", f"op_{i}")
            results.append({
                "operationId": op_id,
                "success": True,
                "result": {"status": "ok", "data": {"type": name, "item": i}},
                "warnings": [],
                "error": None
            })
        return {
            "contractVersion": "1.0",
            "results": results,
            "success": True,
            "error": None
        }

    if name in ("plc_write", "network_write", "hmi_write", "vci_write"):
        dry_run = arguments.get("dryRun", False)
        ops = arguments.get("operations", [])
        results = []
        for i, op in enumerate(ops):
            op_id = op.get("operationId", f"op_{i}")
            results.append({
                "operationId": op_id,
                "phase": "preview" if dry_run else "applied",
                "applied": not dry_run
            })
        return {
            "phase": "preview" if dry_run else "applied",
            "results": results,
            "audit": {"action": name, "operationsCount": len(ops), "dryRun": dry_run}
        }

    if name == "read_cross_references":
        return {
            "contractVersion": "1.0",
            "value": {
                "target": arguments["target"],
                "totalReferences": 0,
                "references": []
            },
            "warnings": [],
            "failure": None
        }

    return {"status": "unhandled", "tool": name}


def main():
    parser = argparse.ArgumentParser(description="TIA MCP Server (Mock Oracle)")
    parser.add_argument("--access-mode", choices=["read-only", "read-write", "full"], default="read-write")
    parser.add_argument("--read-only", action="store_const", const="read-only", dest="access_mode")
    parser.add_argument("--read-write", action="store_const", const="read-write", dest="access_mode")
    parser.add_argument("--project", dest="project_path", default=None)
    parser.add_argument("--max-item-chars", type=int, default=60000)
    parser.add_argument("--max-document-chars", type=int, default=180000)
    parser.add_argument("--worker-timeout-minutes", type=int, default=5)
    parser.add_argument("-v", "--version", action="store_true")
    parser.add_argument("subcommand", nargs="?", default=None)

    # Allow unknown args gracefully
    args, unknown = parser.parse_known_args()

    if args.version:
        sys.stdout.write(f"{SERVER_NAME} {SERVER_VERSION}\n")
        return 0

    if args.subcommand == "doctor":
        sys.stderr.write("Checking system configuration...\n")
        sys.stdout.write("TIA Portal MCP Diagnostic: All systems operational (mock oracle).\n")
        return 0

    if args.subcommand == "install":
        sys.stdout.write("Mock registration succeeded.\n")
        return 0

    # Environment variable fallback
    access_mode = os.environ.get("TIA_MCP_ACCESS_MODE", args.access_mode)
    project_path = os.environ.get("TIA_MCP_PROJECT_PATH", args.project_path)

    # Diagnostic logs strictly to stderr
    sys.stderr.write(f"TIA MCP access mode: {access_mode.upper()}\n")
    sys.stderr.write(f"TIA MCP response budget: {args.max_item_chars} characters per value, {args.max_document_chars} per response\n")
    sys.stderr.write(f"TIA MCP worker timeout: {args.worker_timeout_minutes} minutes\n")
    if access_mode == "read-only":
        sys.stderr.write("Project opening, compilation, writes and lifecycle operations are disabled.\n")
    sys.stderr.flush()

    state = MockServerState(access_mode=access_mode, startup_project=project_path)

    # Main Stdio Loop
    while True:
        try:
            line = sys.stdin.readline()
            if not line:
                break  # EOF
            line = line.strip()
            if not line:
                continue

            try:
                request = json.loads(line)
            except json.JSONDecodeError:
                write_error(-32700, "Parse error")
                continue

            if not isinstance(request, dict) or request.get("jsonrpc") != "2.0" or "method" not in request or not isinstance(request.get("method"), str):
                write_error(-32600, "Invalid Request", req_id=request.get("id") if isinstance(request, dict) else None)
                continue

            method = request.get("method")
            req_id = request.get("id")
            params = request.get("params", {})

            # Notification handling (no id)
            if req_id is None:
                if method == "notifications/initialized":
                    state.initialized = True
                continue

            # Standard methods
            if method == "initialize":
                write_response({
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "protocolVersion": PROTOCOL_VERSION,
                        "capabilities": {
                            "tools": {
                                "listChanged": False
                            }
                        },
                        "serverInfo": {
                            "name": SERVER_NAME,
                            "version": SERVER_VERSION
                        }
                    }
                })
            elif method == "ping":
                write_response({"jsonrpc": "2.0", "id": req_id, "result": {}})
            elif method == "tools/list":
                exposed_names = state.get_exposed_tool_names()
                tool_list = []
                for t_name in exposed_names:
                    t_def = TOOL_DEFINITIONS.get(t_name, {})
                    tool_list.append({
                        "name": t_name,
                        "description": t_def.get("description", ""),
                        "inputSchema": t_def.get("inputSchema", {"type": "object"}),
                    })
                write_response({
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {"tools": tool_list}
                })
            elif method == "tools/call":
                tool_name = params.get("name") if isinstance(params, dict) else None
                arguments = params.get("arguments", {}) if isinstance(params, dict) else {}

                exposed = state.get_exposed_tool_names()
                if not tool_name or tool_name not in exposed:
                    write_error(-32602, f"Tool '{tool_name}' not found or access denied in {state.access_mode} mode", req_id=req_id)
                    continue

                tool_def = TOOL_DEFINITIONS[tool_name]
                schema_err = validate_schema(tool_def["inputSchema"], arguments)
                if schema_err:
                    write_error(-32602, f"Invalid arguments for tool '{tool_name}': {schema_err}", req_id=req_id)
                    continue

                structured = execute_tool(state, tool_name, arguments)
                content_text = json.dumps(structured, indent=2)
                write_response({
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "content": [
                            {"type": "text", "text": content_text}
                        ],
                        "structuredContent": structured,
                        "isError": False
                    }
                })
            else:
                write_error(-32601, f"Method not found: '{method}'", req_id=req_id)

        except Exception as e:
            sys.stderr.write(f"Unhandled exception in mock server: {e}\n")
            sys.stderr.flush()

    return 0


if __name__ == "__main__":
    sys.exit(main())
