@echo off
setlocal

:: -----------------------------------------------------------------------------
:: Resolve repository root directory and change to it
:: -----------------------------------------------------------------------------
set "REPO_ROOT=%~dp0.."
cd /d "%REPO_ROOT%"

:: -----------------------------------------------------------------------------
:: Ensure .NET runtime is available in PATH / DOTNET_ROOT
:: -----------------------------------------------------------------------------
if not defined DOTNET_ROOT (
    if exist "%LOCALAPPDATA%\Microsoft\dotnet\dotnet.exe" (
        set "DOTNET_ROOT=%LOCALAPPDATA%\Microsoft\dotnet"
    )
)
if defined DOTNET_ROOT (
    set "PATH=%DOTNET_ROOT%;%PATH%"
)
if exist "%LOCALAPPDATA%\Microsoft\dotnet\dotnet.exe" (
    set "PATH=%LOCALAPPDATA%\Microsoft\dotnet;%PATH%"
)

:: -----------------------------------------------------------------------------
:: Resolve Server Executable or Fallback
:: Search order:
:: 1. TiaMcpServer\bin\Release\net10.0\TiaMcpServer.exe
:: 2. TiaMcpServer\bin\Release\net10.0\TiaMcpServer.dll
:: 3. TiaMcpServer\bin\Debug\net10.0\TiaMcpServer.exe
:: 4. TiaMcpServer\bin\Debug\net10.0\TiaMcpServer.dll
:: 5. Fallback: dotnet run --project TiaMcpServer --no-build --
:: -----------------------------------------------------------------------------
set "EXEC_CMD="
if exist "%REPO_ROOT%\TiaMcpServer\bin\Release\net10.0\TiaMcpServer.exe" (
    set "EXEC_CMD="%REPO_ROOT%\TiaMcpServer\bin\Release\net10.0\TiaMcpServer.exe""
) else if exist "%REPO_ROOT%\TiaMcpServer\bin\Release\net10.0\TiaMcpServer.dll" (
    set "EXEC_CMD=dotnet "%REPO_ROOT%\TiaMcpServer\bin\Release\net10.0\TiaMcpServer.dll""
) else if exist "%REPO_ROOT%\TiaMcpServer\bin\Debug\net10.0\TiaMcpServer.exe" (
    set "EXEC_CMD="%REPO_ROOT%\TiaMcpServer\bin\Debug\net10.0\TiaMcpServer.exe""
) else if exist "%REPO_ROOT%\TiaMcpServer\bin\Debug\net10.0\TiaMcpServer.dll" (
    set "EXEC_CMD=dotnet "%REPO_ROOT%\TiaMcpServer\bin\Debug\net10.0\TiaMcpServer.dll""
) else (
    set "EXEC_CMD=dotnet run --project "%REPO_ROOT%\TiaMcpServer" --no-build --"
)

:: -----------------------------------------------------------------------------
:: Check if an access mode is already specified via CLI argument or environment
:: -----------------------------------------------------------------------------
set "HAS_ACCESS_MODE=0"
if defined TIA_MCP_ACCESS_MODE set "HAS_ACCESS_MODE=1"

for %%A in (%*) do (
    if /i "%%~A"=="--access-mode" set "HAS_ACCESS_MODE=1"
    if /i "%%~A"=="--read-only" set "HAS_ACCESS_MODE=1"
    if /i "%%~A"=="--read-write" set "HAS_ACCESS_MODE=1"
)

:: -----------------------------------------------------------------------------
:: Execute Server as Top-Level Command and Propagate Exit Code
:: -----------------------------------------------------------------------------
if "%HAS_ACCESS_MODE%"=="1" (
    goto :RUN_EXPLICIT
) else (
    goto :RUN_DEFAULT
)

:RUN_EXPLICIT
%EXEC_CMD% %*
exit /b %ERRORLEVEL%

:RUN_DEFAULT
%EXEC_CMD% %* --access-mode read-write
exit /b %ERRORLEVEL%
