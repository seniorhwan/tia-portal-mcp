<#
.SYNOPSIS
    Verifies the Siemens TIA Portal Antigravity Plugin and performs an end-to-end MCP protocol handshake.
#>

[CmdletBinding()]
param(
    [string]$PluginDir = "$PSScriptRoot\..\.agents\plugins\tia-portal-mcp"
)

$ErrorActionPreference = "Stop"

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host " Verifying Siemens TIA Portal MCP Plugin for Antigravity" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

$PluginJsonPath = Join-Path $PluginDir "plugin.json"
$McpConfigPath = Join-Path $PluginDir "mcp_config.json"
$SkillPath = Join-Path $PluginDir "skills\tia-portal-automation\SKILL.md"

# 1. Validate plugin.json
Write-Host "[1/4] Checking plugin.json..." -ForegroundColor Cyan
if (-not (Test-Path $PluginJsonPath)) {
    throw "plugin.json not found at $PluginJsonPath"
}
$pluginData = Get-Content $PluginJsonPath -Raw | ConvertFrom-Json
if (-not $pluginData.name -or -not $pluginData.displayName) {
    throw "plugin.json is missing required metadata"
}
Write-Host "      Name: $($pluginData.name) ($($pluginData.displayName)) v$($pluginData.version)" -ForegroundColor Green

# 2. Validate mcp_config.json
Write-Host "[2/4] Checking mcp_config.json..." -ForegroundColor Cyan
if (-not (Test-Path $McpConfigPath)) {
    throw "mcp_config.json not found at $McpConfigPath"
}
$mcpData = Get-Content $McpConfigPath -Raw | ConvertFrom-Json
$serverConfig = $mcpData.mcpServers.'tia-portal'
if (-not $serverConfig) {
    throw "mcpServers.tia-portal not defined in mcp_config.json"
}
$exePath = $serverConfig.command
if (-not [System.IO.Path]::IsPathRooted($exePath)) {
    $RepoRoot = Split-Path -Parent $PSScriptRoot
    $exePath = Join-Path $RepoRoot $exePath
}
if (-not (Test-Path $exePath)) {
    throw "Target executable not found at $exePath"
}
Write-Host "      Target Executable: $exePath" -ForegroundColor Green

# 3. Validate SKILL.md
Write-Host "[3/4] Checking SKILL.md..." -ForegroundColor Cyan
if (-not (Test-Path $SkillPath)) {
    throw "SKILL.md not found at $SkillPath"
}
$skillContent = Get-Content $SkillPath -Raw
if ($skillContent -notmatch "name:\s*tia-portal-automation" -or $skillContent -notmatch "description:") {
    throw "SKILL.md is missing valid frontmatter"
}
Write-Host "      Skill Name: tia-portal-automation" -ForegroundColor Green

# 4. Perform live MCP Protocol Handshake
Write-Host "[4/4] Testing MCP protocol handshake over stdio..." -ForegroundColor Cyan

$psi = New-Object System.Diagnostics.ProcessStartInfo
$psi.FileName = $exePath
$psi.Arguments = "--access-mode read-write"
$psi.RedirectStandardInput = $true
$psi.RedirectStandardOutput = $true
$psi.RedirectStandardError = $true
$psi.UseShellExecute = $false
$psi.CreateNoWindow = $true

$proc = [System.Diagnostics.Process]::Start($psi)

try {
    # Send initialize request
    $initRequest = '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"antigravity-verifier","version":"1.0"}}}'
    $proc.StandardInput.WriteLine($initRequest)
    $proc.StandardInput.Flush()

    # Read response
    $initResponse = $proc.StandardOutput.ReadLine()
    $initObj = $initResponse | ConvertFrom-Json
    if (-not $initObj.result.serverInfo) {
        throw "Failed to receive valid MCP initialize response: $initResponse"
    }
    Write-Host "      Server Name: $($initObj.result.serverInfo.name) v$($initObj.result.serverInfo.version)" -ForegroundColor Green

    # Send initialized notification
    $notif = '{"jsonrpc":"2.0","method":"notifications/initialized","params":{}}'
    $proc.StandardInput.WriteLine($notif)
    $proc.StandardInput.Flush()

    # Query tools/list
    $toolsRequest = '{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}'
    $proc.StandardInput.WriteLine($toolsRequest)
    $proc.StandardInput.Flush()

    $toolsResponse = $proc.StandardOutput.ReadLine()
    $toolsObj = $toolsResponse | ConvertFrom-Json
    $tools = $toolsObj.result.tools
    Write-Host "      Exposed Tools Count: $($tools.Count)" -ForegroundColor Green

    if ($tools.Count -ne 19) {
        throw "Expected 19 tools in read-write mode, but found $($tools.Count)"
    }

    $toolNames = ($tools | ForEach-Object { $_.name }) -join ", "
    Write-Host "      Tools: $toolNames" -ForegroundColor Gray

    Write-Host "`n[+] ALL MCP PLUGIN CHECKS PASSED SUCCESSFULLY!" -ForegroundColor Green
}
finally {
    if (-not $proc.HasExited) {
        $proc.Kill()
        $proc.WaitForExit()
    }
}
