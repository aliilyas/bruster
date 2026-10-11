#!/bin/sh
# Spawns the MCP server the way opencode does (stdio, one initialize line)
# and expects a reply. A launch that dies first is what opencode reports as
# "MCP error -32000: Connection closed".
# Usage: mcp_launch.sh [command...]   default: the opencode launcher.
LAUNCHER="$HOME/.config/opencode/bruster-mcp.sh"
REPLY_TIMEOUT_SECS=60
INIT='{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"mcp_launch","version":"0"}}}'

[ $# -eq 0 ] && set -- "$LAUNCHER"

# Bound the wait where a timeout tool exists (stock macOS has none).
guard=$(command -v timeout || command -v gtimeout)
out=$(printf '%s\n' "$INIT" | ${guard:+"$guard" "$REPLY_TIMEOUT_SECS"} "$@" 2>&1)
status=$?

case "$out" in
  *'"name":"bruster"'*)
    echo "PASS: initialize answered"
    ;;
  *)
    echo "FAIL: no initialize reply (exit $status)"
    echo "$out" | head -5
    exit 1
    ;;
esac
