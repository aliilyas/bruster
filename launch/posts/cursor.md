# Cursor community post

Destination: <https://forum.cursor.com/c/showcase/9>, **Built for Cursor**
subcategory (category ID 19).

## Title

Bruster: native-webview browser automation for Cursor through MCP

## Body

I maintain Bruster, an MIT-licensed browser automation tool written in Rust.
It provides navigation, snapshots, form interaction, tabs, and screenshots
through stdio MCP, using WKWebView on macOS, WebKitGTK on Linux, and WebView2 on
Windows. No Node.js runtime is needed for the server.

### Setup

On macOS/Linux:

```sh
curl -fsSL https://raw.githubusercontent.com/aliilyas/bruster/main/install.sh | sh
```

Add `~/.local/bin` to the PATH used to start Cursor, or use the executable's
absolute path as `command`. Merge this entry into the project's `.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "bruster": {
      "command": "bruster",
      "args": ["--mcp", "--quiet"]
    }
  }
}
```

Enable Bruster in Cursor's MCP settings. Add `--visible` to the arguments to
watch the native browser window.

### Try it on a local form

```sh
git clone https://github.com/aliilyas/bruster.git
python3 -m http.server 8765 --bind 127.0.0.1 --directory bruster/examples/launch-demo
```

Ask Agent:

> Use Bruster to open http://127.0.0.1:8765. Inspect the page. Enter Ada Lovelace
> as the name and Bruster as the project. Select Form submission, enable Include
> screenshots, and submit. Verify the confirmation and return a screenshot.

The included 30-second video shows this tool sequence with a scripted MCP
client and actual WebKitGTK captures; it is not a recording of Cursor.

Linux requires WebKitGTK 4.1 and a display or Xvfb. Windows requires WebView2,
which is Chromium-based. Inputs use synthetic DOM events, and cross-origin
iframes are not accessible.

- Source, releases, and full API: https://github.com/aliilyas/bruster
- Demo and reproduction steps: https://github.com/aliilyas/bruster/tree/main/launch
- Benchmark methodology and raw data: https://aliilyas.github.io/bruster/benchmarks/

Feedback on setup and useful Cursor workflows would be welcome.
