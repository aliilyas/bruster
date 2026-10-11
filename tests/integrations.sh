#!/bin/sh
# Integration checks against third-party MCP clients: the TypeScript SDK
# (Claude Desktop, Cursor, VS Code), the Python SDK and the Inspector CLI.
# Needs node, python3 and the network. Usage: tests/integrations.sh <bruster>
set -u
BIN=${1:?bruster binary}
BIN=$(cd "$(dirname "$BIN")" && pwd)/$(basename "$BIN")
cd "$(dirname "$0")/integrations" || exit 1
status=0
check() { if "$@"; then echo "PASS $1 $2"; else echo "FAIL $1 $2"; status=1; fi; }

if [ ! -d node_modules/@modelcontextprotocol/sdk ]; then
  npm init -y >/dev/null 2>&1
  npm i --silent @modelcontextprotocol/sdk @modelcontextprotocol/inspector >/dev/null 2>&1
fi
python3 -c 'import mcp' 2>/dev/null || python3 -m pip install -q --break-system-packages mcp >/dev/null 2>&1 || pip install -q mcp >/dev/null 2>&1

# The SDKs spawn the server with a scrubbed environment (no DISPLAY), like
# the desktop clients do. bruster must cope on its own.
check node ts_sdk.mjs "$BIN" --hidden --mcp --quiet
check python3 py_sdk.py "$BIN" --hidden --mcp --quiet

# Inspector CLI: the reference client, strict about protocol shape. It only
# takes servers from a config file.
cat > insp.json <<EOF
{"mcpServers":{"bruster":{"command":"$BIN","args":["--hidden","--mcp","--quiet"]}}}
EOF
insp() { npx --no-install @modelcontextprotocol/inspector --cli --config insp.json --server bruster "$@" 2>/dev/null; }
out=$(insp --method tools/list)
case "$out" in *'"name": "snapshot"'*) echo "PASS inspector tools/list" ;; *) echo "FAIL inspector tools/list"; echo "$out" | head -5; status=1 ;; esac
out=$(insp --method tools/call --tool-name navigate --tool-arg url=https://example.com/)
case "$out" in *example.com*) echo "PASS inspector tools/call" ;; *) echo "FAIL inspector tools/call"; echo "$out" | head -5; status=1 ;; esac
rm -f insp.json

exit $status
