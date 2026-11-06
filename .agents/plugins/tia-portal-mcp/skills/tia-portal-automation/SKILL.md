---
name: tia-portal-automation
description: >-
  Automate Siemens TIA Portal V21 engineering workflows via the TIA Portal MCP server.
  Use this skill whenever inspecting, creating, or modifying Siemens TIA Portal projects,
  including PLC programming (OB/FB/FC/DB code logic, tag tables, data types),
  hardware & network topology (subnets, PROFINET device names, IP addresses, IO systems),
  WinCC Unified HMI configuration (tags, discrete/analog alarms),
  Version Control Interface (VCI workspaces, XML export/import), and project compilation checks.
---

# Siemens TIA Portal Automation Guide

This skill provides step-by-step workflows for interacting with Siemens TIA Portal V21 using the 19 tools exposed by `TiaMcpServer`.

---

## Tool Overview by Domain

| Category | Read / Inspection Tools | Write / Execution Tools |
| :--- | :--- | :--- |
| **Project & Lifecycle** | `get_project_status`, `browse_project_tree`, `read_cross_references` | `bind_project`, `open_project`, `create_project`, `save_project`, `save_project_as`, `archive_project`, `close_project` |
| **PLC Programming** | `plc_read` | `plc_write` (14 operations, dryRun preview) |
| **Hardware & Network** | `network_read` | `network_write` (PN name, Subnet, IP, IO systems) |
| **Unified HMI** | `hmi_read` | `hmi_write` (Tag tables, tags, discrete & analog alarms) |
| **Version Control (VCI)**| `vci_read` | `vci_write` (Workspaces, XML import/export) |
| **Compilation** | — | `compile_check` |

---

## Phase 1: Environment Health & Doctor Check

Before initiating automation workflows, verify that the Siemens Openness environment is operational:

```powershell
& ".\scripts\run-tia-mcp.bat" doctor
```

Key checks evaluated:
- **Operating System**: Windows 10/11 x64
- **.NET Runtime**: .NET 10.0+
- **.NET Framework**: 4.8.1 installed
- **TIA Portal V21**: Verified in Siemens PublicAPI folder
- **Siemens TIA Openness Group**: Current user must be a member of the local `Siemens TIA Openness` group.

---

## Phase 2: Project Discovery & Binding

All content read and write tools require an active, pinned project binding.

### 1. Check Binding Status
Call `get_project_status` (takes no arguments):
- If `bound: true`, proceed with content inspection or mutations.
- If `bound: false`, you must bind before calling content tools.

### 2. Discover Open Portals and Sessions
Use `bind_project` with inspection verbs:
- `bind_project(action: "list_portals")`: Lists running TIA Portal instances and their process IDs.
- `bind_project(action: "list_local_sessions")`: Lists active Multiuser local sessions (`.als21`).

### 3. Bind to an Open Project
```json
// Example: Bind to a project by file path
{
  "action": "bind",
  "projectPath": "C:\\Projects\\PlantAutomation\\PlantAutomation.ap21"
}
```
Or bind by Portal process ID:
```json
{
  "action": "bind",
  "portalId": 12345
}
```

---

## Phase 3: Project Tree & Cross-Reference Inspection

Once bound, browse the project structure:

### 1. Browse Project Tree
Call `browse_project_tree` to discover devices, CPU stations, software containers, and HMI targets.
```json
{
  "path": "Station_1/PLC_1/Program blocks",
  "depth": 2
}
```

### 2. Inspect Cross-References
Call `read_cross_references` to trace tag usages and block calls across the PLC program:
```json
{
  "target": "Tag_Motor_Speed",
  "scope": "PLC_1"
}
```

---

## Phase 4: PLC Programming & Logic Updates

### 1. Read-Before-Write Pattern (MANDATORY)
To modify block logic or type content, you **must first read the existing content** to acquire the current `expectedContentHash`:

```json
// 1. Read the block
// Tool: plc_read
{
  "operation": "read_block_logic",
  "target": "Main [OB1]",
  "format": "scl"
}
```
Take note of `content` and `contentHash` from the response.

### 2. Guarded Write with Preview (`dryRun: true`)
Always preview changes before executing:

```json
// Tool: plc_write
{
  "dryRun": true,
  "operations": [
    {
      "operationId": "op_update_main",
      "type": "update_block_logic",
      "target": "Main [OB1]",
      "format": "scl",
      "expectedContentHash": "<hash-from-plc_read>",
      "content": "REGION Motor Control\n  #Motor_Speed := 1500;\nEND_REGION"
    }
  ]
}
```

### 3. Commit the Changes
If `dryRun: true` passes with no blocking guards, execute with `dryRun: false` (or default):
```json
// Tool: plc_write
{
  "dryRun": false,
  "operations": [ ... ]
}
```

### Available `plc_write` Operations
- Blocks: `create_block`, `update_block_logic`, `delete_block`, `rename_block`
- Tags: `create_tag`, `update_tag`, `delete_tag`
- Tag Tables: `create_tag_table`, `delete_tag_table`
- Groups/Folders: `create_group`, `delete_group`, `rename_group`
- Types: `update_type_content`

---

## Phase 5: Hardware & Network Topology

Use `network_read` and `network_write` to configure PROFINET interfaces, IP addresses, subnets, and IO systems.

### 1. Inspect Network Topology
```json
// Tool: network_read
{
  "operation": "get_topology"
}
```

### 2. Configure PROFINET Device & Subnet
```json
// Tool: network_write
{
  "dryRun": false,
  "operations": [
    {
      "operationId": "op_cfg_pn_io",
      "type": "configure_interface",
      "deviceName": "PLC_1",
      "interfaceName": "PROFINET interface_1",
      "settings": {
        "Address": "192.168.0.10",
        "SubnetMask": "255.255.255.0",
        "PnDeviceName": "plc1-cpu",
        "Subnet": "PROFINET_Subnet_1"
      }
    }
  ]
}
```

---

## Phase 6: WinCC Unified HMI Configuration

Manage HMI tags, tag tables, discrete alarms, and analog alarms via `hmi_read` and `hmi_write`.

### 1. Read HMI Tags & Alarms
```json
// Tool: hmi_read
{
  "operation": "list_alarms",
  "hmiTarget": "HMI_RT_1"
}
```

### 2. Create Alarms and Tags
```json
// Tool: hmi_write
{
  "dryRun": false,
  "operations": [
    {
      "operationId": "op_hmi_alarm_1",
      "type": "create_discrete_alarm",
      "hmiTarget": "HMI_RT_1",
      "name": "Alarm_EmergencyStop",
      "triggerTag": "HMI_Tags.EStop_Active",
      "bit": 0,
      "text": "Emergency Stop Triggered!"
    }
  ]
}
```

---

## Phase 7: Version Control Interface (VCI)

Use `vci_read` and `vci_write` to synchronize software blocks and types with external source repositories or local folders.

### 1. Synchronize Workspace
```json
// Tool: vci_write
{
  "dryRun": false,
  "operations": [
    {
      "operationId": "op_sync_vci",
      "type": "synchronize_workspace",
      "workspaceName": "GitWorkspace"
    }
  ]
}
```

---

## Phase 8: Compilation & Diagnostics

Always compile and verify software blocks after modifications:

### 1. Run Compile Check
```json
// Tool: compile_check
{
  "target": "PLC_1",
  "type": "software"
}
```
Examine compiler warnings and errors in the returned report.

### 2. Error Diagnostics Guide
- `binding_conflict`: No active project is bound. Call `get_project_status` then `bind_project`.
- `state_changed`: The block content on the PLC changed since your `plc_read`. Re-read to obtain the latest hash.
- `engineering_rejected`: Siemens Openness rejected the operation (e.g. invalid syntax, duplicate identifier). Review `engineeringError` details.
- `portal_lost`: TIA Portal process crashed or disconnected. Re-launch TIA Portal and call `bind_project`.
- `target_not_found`: The specified block, tag, or device path does not exist in the project tree.
