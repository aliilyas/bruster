# r/mcp showcase

Submit: <https://www.reddit.com/r/mcp/submit>  
Suggested flair: Showcase, if available. Attach the demo MP4 from the release.

## Title

Bruster: native-webview browser automation over MCP, without Node.js

## Body

I maintain **Bruster**, an MIT-licensed browser automation tool written in Rust.
It exposes navigation, page snapshots, forms, tabs, screenshots, and page-level
network/console inspection over stdio MCP.

It uses WKWebView on macOS, WebKitGTK on Linux, and WebView2 on Windows. The Rust
controller is small, but the browser runtime and helper processes are separate
dependencies. WebView2 is Chromium-based. No Node.js runtime is required.

The 30-second demo shows actual WebKitGTK screenshots from a scripted MCP
client: navigate → inspect → fill a form → submit → verify → screenshot. Each
step is held for readability; it is not a speed test or an LLM recording.

On macOS/Linux:

```sh
curl -fsSL https://raw.githubusercontent.com/aliilyas/bruster/main/install.sh | sh
export PATH="$HOME/.local/bin:$PATH"
```

MCP configuration, with `bruster` on the client's PATH:

```json
{"mcpServers":{"bruster":{"command":"bruster","args":["--mcp","--quiet"]}}}
```

There is also a native MCP bundle in Releases and an official registry entry
named `io.github.aliilyas/bruster`.

The main limits: synthetic DOM events, no cross-origin iframe access, and
page-level rather than browser-wide network interception. Linux needs
WebKitGTK 4.1 and a display or Xvfb.

- Repo and platform downloads: https://github.com/aliilyas/bruster
- Reproduce the demo: https://github.com/aliilyas/bruster/tree/main/launch#try-the-demo
- Benchmarks and methodology: https://aliilyas.github.io/bruster/benchmarks/

I'd appreciate feedback on MCP client compatibility and which browser workflows
you would want to use it for.
