@echo off
REM Engram installer for Windows CMD
REM Usage: curl -fsSL https://engram-us.com/install.cmd -o install.cmd && install.cmd && del install.cmd

setlocal enabledelayedexpansion

if defined ENGRAM_MCP_URL (
    set "MCP_URL=%ENGRAM_MCP_URL%"
) else (
    set "MCP_URL=https://mcp.engram.app/mcp"
)
set "INVITE_KEY="

REM ── Require Python 3 ─────────────────────────────────────────────
where python3 >nul 2>&1
if %errorlevel% equ 0 (
    set "PY=python3"
) else (
    where python >nul 2>&1
    if %errorlevel% equ 0 (
        set "PY=python"
    ) else (
        echo Python 3 is required but not found. Please install it first.
        exit /b 1
    )
)

REM ── Ask for invite key ───────────────────────────────────────────
echo.
set /p "HAS_KEY=Do you have an invite key from a teammate? (y/n): "
if /i "%HAS_KEY%"=="y" (
    set /p "INVITE_KEY=Paste your invite key: "
)

REM ── Detect and patch MCP clients ────────────────────────────────
echo.
echo Detecting MCP clients...
set "PATCHED=0"

REM Claude Desktop — npx mcp-remote bridge
if exist "%APPDATA%\Claude" (
    call :patch_claude_desktop "%APPDATA%\Claude\claude_desktop_config.json"
    set /a PATCHED+=1
)

REM Claude Code — ~/.claude.json
if exist "%USERPROFILE%\.claude" (
    call :patch_claude_code "%USERPROFILE%\.claude.json"
    set /a PATCHED+=1
)
if exist "%USERPROFILE%\.claude.json" if not exist "%USERPROFILE%\.claude" (
    call :patch_claude_code "%USERPROFILE%\.claude.json"
    set /a PATCHED+=1
)

REM Cursor
if exist "%USERPROFILE%\.cursor" (
    call :patch_mcpservers_url "%USERPROFILE%\.cursor\mcp.json"
    set /a PATCHED+=1
)

REM VS Code — {servers: {type, url}} in mcp.json
if exist "%APPDATA%\Code" (
    call :patch_vscode "%APPDATA%\Code\User\mcp.json"
    set /a PATCHED+=1
)

REM Windsurf — serverUrl
if exist "%USERPROFILE%\.codeium\windsurf" (
    call :patch_windsurf "%USERPROFILE%\.codeium\windsurf\mcp_config.json"
    set /a PATCHED+=1
)

REM Kiro
if exist "%USERPROFILE%\.kiro" (
    call :patch_mcpservers_url "%USERPROFILE%\.kiro\settings\mcp.json"
    set /a PATCHED+=1
)

REM Amazon Q Developer
if exist "%USERPROFILE%\.aws\amazonq" (
    call :patch_mcpservers_url "%USERPROFILE%\.aws\amazonq\mcp.json"
    set /a PATCHED+=1
)

REM Trae (ByteDance)
if exist "%APPDATA%\Trae" (
    call :patch_mcpservers_url "%APPDATA%\Trae\User\mcp.json"
    set /a PATCHED+=1
)

REM JetBrains / Junie
if exist "%USERPROFILE%\.junie" (
    call :patch_mcpservers_url "%USERPROFILE%\.junie\mcp\mcp.json"
    set /a PATCHED+=1
)

REM Cline (VS Code extension)
if exist "%USERPROFILE%\Documents\Cline" (
    call :patch_mcpservers_url "%USERPROFILE%\Documents\Cline\MCP\cline_mcp_settings.json"
    set /a PATCHED+=1
)

REM Roo Code (VS Code extension)
if exist "%APPDATA%\Code\User\globalStorage\rooveterinaryinc.roo-cline" (
    call :patch_mcpservers_url "%APPDATA%\Code\User\globalStorage\rooveterinaryinc.roo-cline\settings\cline_mcp_settings.json"
    set /a PATCHED+=1
)

REM OpenCode
if exist "%USERPROFILE%\.config\opencode" (
    call :patch_opencode "%USERPROFILE%\.config\opencode\config.json"
    set /a PATCHED+=1
)

REM ── Result ───────────────────────────────────────────────────────
echo.
if %PATCHED% equ 0 (
    echo No MCP clients detected. Manually add to your IDE's MCP config:
    echo.
    echo   Remote MCP URL: %MCP_URL%
    if not "%INVITE_KEY%"=="" echo   Header: Authorization: Bearer %INVITE_KEY%
    echo.
    echo Then restart your IDE.
) else (
    echo Done! Restart your IDE, then ask your agent:
    echo.
    if "%INVITE_KEY%"=="" (
        echo   "Set up Engram for my team"    - to create a new workspace
        echo   "Join Engram with key ek_live_..."  - to join a teammate's workspace
    ) else (
        echo   "Set up Engram"  - your agent will connect to your workspace
    )
)
echo.
goto :eof

:patch_mcpservers_url
set "CF=%~1"
%PY% -c "import json,os;f=r'%CF%';u='%MCP_URL%';k='%INVITE_KEY%';c=json.load(open(f)) if os.path.exists(f) else {};os.makedirs(os.path.dirname(f),exist_ok=True);c.setdefault('mcpServers',{});e={'url':u};k and e.update({'headers':{'Authorization':'Bearer '+k}});c['mcpServers']['engram']=e;json.dump(c,open(f,'w'),indent=2);print('  + '+f)"
goto :eof

:patch_windsurf
set "CF=%~1"
%PY% -c "import json,os;f=r'%CF%';u='%MCP_URL%';k='%INVITE_KEY%';c=json.load(open(f)) if os.path.exists(f) else {};os.makedirs(os.path.dirname(f),exist_ok=True);c.setdefault('mcpServers',{});e={'serverUrl':u};k and e.update({'headers':{'Authorization':'Bearer '+k}});c['mcpServers']['engram']=e;json.dump(c,open(f,'w'),indent=2);print('  + '+f)"
goto :eof

:patch_vscode
set "CF=%~1"
%PY% -c "import json,os;f=r'%CF%';u='%MCP_URL%';k='%INVITE_KEY%';c=json.load(open(f)) if os.path.exists(f) else {};os.makedirs(os.path.dirname(f),exist_ok=True);c.setdefault('servers',{});e={'type':'http','url':u};k and e.update({'headers':{'Authorization':'Bearer '+k}});c['servers']['engram']=e;json.dump(c,open(f,'w'),indent=2);print('  + '+f)"
goto :eof

:patch_claude_code
set "CF=%~1"
%PY% -c "import json,os;f=r'%CF%';u='%MCP_URL%';k='%INVITE_KEY%';c=json.load(open(f)) if os.path.exists(f) else {};c.setdefault('mcpServers',{});e={'type':'http','url':u};k and e.update({'headers':{'Authorization':'Bearer '+k}});c['mcpServers']['engram']=e;json.dump(c,open(f,'w'),indent=2);print('  + '+f)"
goto :eof

:patch_claude_desktop
set "CF=%~1"
%PY% -c "import json,os;f=r'%CF%';u='%MCP_URL%';k='%INVITE_KEY%';c=json.load(open(f)) if os.path.exists(f) else {};os.makedirs(os.path.dirname(f),exist_ok=True);c.setdefault('mcpServers',{});a=['-y','mcp-remote@latest',u];k and a.extend(['--header','Authorization: Bearer '+k]);c['mcpServers']['engram']={'command':'npx','args':a};json.dump(c,open(f,'w'),indent=2);print('  + '+f)"
goto :eof

:patch_opencode
set "CF=%~1"
%PY% -c "import json,os;f=r'%CF%';u='%MCP_URL%';k='%INVITE_KEY%';c=json.load(open(f)) if os.path.exists(f) else {};os.makedirs(os.path.dirname(f),exist_ok=True);c.setdefault('mcp',{});e={'type':'remote','url':u,'enabled':True};k and e.update({'headers':{'Authorization':'Bearer '+k}});c['mcp']['engram']=e;json.dump(c,open(f,'w'),indent=2);print('  + '+f)"
goto :eof
