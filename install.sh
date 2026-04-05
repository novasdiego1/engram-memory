#!/bin/sh
# Engram installer — adds Engram to your MCP config
# Usage: curl -fsSL https://engram.app/install | sh
#   or:  curl -fsSL https://engram.app/install | sh -s -- --join ek_live_...

set -e

MCP_URL="https://mcp.engram.app/mcp"
INVITE_KEY=""

# Parse --join flag
while [ $# -gt 0 ]; do
  case "$1" in
    --join) INVITE_KEY="$2"; shift 2 ;;
    *) shift ;;
  esac
done

# ── Detect OS ──────────────────────────────────────────────────────
OS="$(uname -s)"
if [ "$OS" != "Darwin" ] && [ "$OS" != "Linux" ]; then
  echo "Unsupported OS: $OS"
  echo "Manually add Engram to your MCP config:"
  echo "  url: $MCP_URL"
  exit 1
fi

# ── Require Python 3 ───────────────────────────────────────────────
if ! command -v python3 >/dev/null 2>&1; then
  echo "Python 3 is required but not found. Please install it first."
  exit 1
fi

# ── Ask for invite key if not provided ─────────────────────────────
if [ -z "$INVITE_KEY" ]; then
  printf "\nDo you have an invite key from a teammate? (y/n): "
  read HAS_KEY
  if [ "$HAS_KEY" = "y" ] || [ "$HAS_KEY" = "Y" ]; then
    printf "Paste your invite key: "
    read INVITE_KEY
  fi
fi

# ── Build the MCP server config block ──────────────────────────────
if [ -n "$INVITE_KEY" ]; then
  SERVER_BLOCK="\"engram\": {\"url\": \"$MCP_URL\", \"headers\": {\"Authorization\": \"Bearer $INVITE_KEY\"}}"
else
  SERVER_BLOCK="\"engram\": {\"url\": \"$MCP_URL\"}"
fi

# ── JSON patcher (Python) ──────────────────────────────────────────
patch_json() {
  CONFIG_FILE="$1"
  python3 - "$CONFIG_FILE" "$MCP_URL" "$INVITE_KEY" << 'PYEOF'
import json, sys, os

config_file = sys.argv[1]
mcp_url     = sys.argv[2]
invite_key  = sys.argv[3]

if os.path.exists(config_file):
  try:
    with open(config_file) as f:
      config = json.load(f)
  except Exception:
    config = {}
else:
  os.makedirs(os.path.dirname(config_file), exist_ok=True)
  config = {}

if "mcpServers" not in config:
  config["mcpServers"] = {}

entry = {"url": mcp_url}
if invite_key:
  entry["headers"] = {"Authorization": f"Bearer {invite_key}"}

config["mcpServers"]["engram"] = entry

with open(config_file, "w") as f:
  json.dump(config, f, indent=2)

print(f"  Patched: {config_file}")
PYEOF
}

# ── Detect and patch MCP clients ──────────────────────────────────
echo ""
echo "Detecting MCP clients..."
PATCHED=0

# Claude Desktop (Mac)
CLAUDE_DESKTOP="$HOME/Library/Application Support/Claude/claude_desktop_config.json"
if [ "$OS" = "Darwin" ] && [ -d "$HOME/Library/Application Support/Claude" ]; then
  patch_json "$CLAUDE_DESKTOP"
  PATCHED=$((PATCHED + 1))
fi

# Claude Desktop (Linux)
CLAUDE_DESKTOP_LINUX="$HOME/.config/Claude/claude_desktop_config.json"
if [ "$OS" = "Linux" ] && [ -d "$HOME/.config/Claude" ]; then
  patch_json "$CLAUDE_DESKTOP_LINUX"
  PATCHED=$((PATCHED + 1))
fi

# Claude Code (~/.claude/settings.json)
CLAUDE_CODE="$HOME/.claude/settings.json"
if [ -f "$CLAUDE_CODE" ] || [ -d "$HOME/.claude" ]; then
  patch_json "$CLAUDE_CODE"
  PATCHED=$((PATCHED + 1))
fi

# Cursor (~/.cursor/mcp.json)
CURSOR="$HOME/.cursor/mcp.json"
if [ -f "$CURSOR" ] || [ -d "$HOME/.cursor" ]; then
  patch_json "$CURSOR"
  PATCHED=$((PATCHED + 1))
fi

# VS Code (Mac)
VSCODE_MAC="$HOME/Library/Application Support/Code/User/settings.json"
if [ "$OS" = "Darwin" ] && [ -f "$VSCODE_MAC" ]; then
  patch_json "$VSCODE_MAC"
  PATCHED=$((PATCHED + 1))
fi

# Windsurf
WINDSURF="$HOME/.codeium/windsurf/mcp_config.json"
if [ -f "$WINDSURF" ] || [ -d "$HOME/.codeium/windsurf" ]; then
  patch_json "$WINDSURF"
  PATCHED=$((PATCHED + 1))
fi

# ── Result ─────────────────────────────────────────────────────────
echo ""
if [ "$PATCHED" -eq 0 ]; then
  echo "No MCP clients detected. Manually add to your config:"
  echo ""
  echo "  \"mcpServers\": {"
  echo "    $SERVER_BLOCK"
  echo "  }"
  echo ""
  echo "Then restart your IDE."
else
  echo "Done. Restart your IDE, then ask your agent:"
  if [ -z "$INVITE_KEY" ]; then
    echo ""
    echo "  \"Set up Engram for my team\"    — to create a new workspace"
    echo "  \"Join Engram with key ek_live_...\"  — to join a teammate's workspace"
  else
    echo ""
    echo "  \"Set up Engram\"  — your agent will connect to your workspace"
  fi
fi
echo ""
