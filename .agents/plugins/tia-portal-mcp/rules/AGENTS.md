# Siemens TIA Portal MCP - Agent Operating Rules

You are integrating with Siemens TIA Portal V21 via the Model Context Protocol (MCP) server. Adhere strictly to the following rules:

## 1. Two-Process Architecture
- The MCP server operates as two separate processes:
  - **Host** (`TiaMcpServer`, .NET 10): Exposes the MCP stdio interface, request budgeting, validation, and pipeline orchestration.
  - **Worker** (`TiaMcpServer.OpennessWorker`, .NET Framework 4.8): Manages the Siemens Openness remoting runtime (`Siemens.Engineering.*`).
- Never attempt to load or execute Siemens Openness assemblies directly in .NET Core/.NET 10 environments.

## 2. Pinned Project Binding
- Content tools (`plc_read`, `plc_write`, `network_read`, `network_write`, `hmi_read`, `hmi_write`, `vci_read`, `vci_write`, `compile_check`, `save_project`) require a verified bound project.
- With no verified binding, operations return `binding_conflict`.
- Before modifying or reading project contents:
  1. Call `get_project_status` to inspect current binding.
  2. If unbound, call `bind_project` with the target `.ap21` (or local session `.als21`) path or Portal PID.
- Ordinary read tools never implicitly bind or switch projects.

## 3. Single-Call Guarded Write Pipeline
- Writes are executed through single-call guarded pipelines (`plc_write`, `network_write`, `hmi_write`, `vci_write`).
- No safety tokens or batch replay are used.
- For previewing effects and verifying guard conditions before mutating project state, always set `dryRun: true`.
- Up to 50 operations are executed in caller-defined order, stopping immediately at the first failure without automatic batch rollback.

## 4. Read-Before-Write Integrity
- When updating PLC block logic (`update_block_logic`) or user-defined types (`update_type_content`):
  1. Always perform a prior `plc_read` in the same format to retrieve the current content and `expectedContentHash`.
  2. Pass `expectedContentHash` to `plc_write`. Stale content fails safely with `state_changed`.
  3. Content exceeding 60,000 characters has no hash and cannot be written unless `--max-item-chars` is explicitly configured.

## 5. Strict Live Openness Environment Diagnostics
- If a tool reports that TIA Portal V21 is not reachable, do not retry blindly.
- Check environment readiness using `doctor` or `get_project_status`.
- Common prerequisites:
  - Siemens TIA Portal V21 installed with Openness enabled.
  - User added to the local Windows security group `"Siemens TIA Openness"`.
  - TIA Portal running with the target project open (for attachment/binding).
