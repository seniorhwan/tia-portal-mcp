<#
.SYNOPSIS
    Installs the Siemens TIA Portal MCP Plugin into Google Antigravity.
.DESCRIPTION
    Copies the plugin bundle into the Antigravity global plugins directory (~/.gemini/config/plugins/tia-portal-mcp),
    verifies release binaries, and validates the configuration.
#>

[CmdletBinding()]
param(
    [string]$TargetDir = "$env:USERPROFILE\.gemini\config\plugins\tia-portal-mcp"
)

$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $PSScriptRoot
$SourcePluginDir = Join-Path $RepoRoot ".agents\plugins\tia-portal-mcp"
$BinaryPath = Join-Path $RepoRoot "TiaMcpServer\bin\Release\net10.0\TiaMcpServer.exe"

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host " Installing Siemens TIA Portal MCP Plugin for Antigravity" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

# 1. Verify source plugin directory exists
if (-not (Test-Path $SourcePluginDir)) {
    throw "Source plugin directory not found at $SourcePluginDir"
}

# Resolve .NET 10 SDK
$DotnetExe = "dotnet"
$LocalDotnet = "$env:LOCALAPPDATA\Microsoft\dotnet\dotnet.exe"
if (Test-Path $LocalDotnet) {
    $DotnetExe = $LocalDotnet
    $env:DOTNET_ROOT = "$env:LOCALAPPDATA\Microsoft\dotnet"
    $env:PATH = "$env:DOTNET_ROOT;$env:PATH"
}

# 2. Check binary
if (-not (Test-Path $BinaryPath)) {
    Write-Host "[-] Pre-built Release binary not found. Building TiaMcpServer..." -ForegroundColor Yellow
    & $DotnetExe build "$RepoRoot\TiaMcpServer.slnx" -c Release -m:1 /p:UseTiaPortalReferenceStubs=true
    if ($LASTEXITCODE -ne 0) {
        throw "Build failed. Could not compile TiaMcpServer."
    }
} else {
    Write-Host "[+] Found compiled TiaMcpServer binary at $BinaryPath" -ForegroundColor Green
}

# 3. Create target directory
if (-not (Test-Path $TargetDir)) {
    New-Item -ItemType Directory -Path $TargetDir -Force | Out-Null
}

# 4. Copy plugin files to global Antigravity config
Write-Host "[*] Copying plugin files to $TargetDir..." -ForegroundColor Cyan
Copy-Item -Path "$SourcePluginDir\*" -Destination $TargetDir -Recurse -Force

# 5. Stamp resolved absolute executable path in global mcp_config.json
$ResolvedBinaryPath = (Resolve-Path $BinaryPath).Path
$GlobalMcpConfigPath = Join-Path $TargetDir "mcp_config.json"
$McpConfigObj = Get-Content $GlobalMcpConfigPath -Raw | ConvertFrom-Json
$McpConfigObj.mcpServers.'tia-portal'.command = $ResolvedBinaryPath
$McpConfigObj | ConvertTo-Json -Depth 5 | Set-Content -Path $GlobalMcpConfigPath -Encoding UTF8

Write-Host "[+] Antigravity Plugin installed successfully!" -ForegroundColor Green
Write-Host "    Location: $TargetDir" -ForegroundColor Gray
Write-Host "    Manifest: $(Join-Path $TargetDir 'plugin.json')" -ForegroundColor Gray
Write-Host "    MCP Config: $(Join-Path $TargetDir 'mcp_config.json')" -ForegroundColor Gray
Write-Host "    Skill: $(Join-Path $TargetDir 'skills\tia-portal-automation\SKILL.md')" -ForegroundColor Gray
