# Claude Code community workflow

Destination: <https://www.reddit.com/r/ClaudeCode/>. Use its current project-sharing
thread or flair if required by the community rules.

## Title

Bruster: give Claude Code native-webview browser tools through MCP

## Body

I maintain Bruster, an open-source Rust browser controller with a stdio MCP
interface. Here's a small reproducible workflow: have Claude inspect a local
form, fill it, verify the confirmation, and return a screenshot.

Install on macOS/Linux and register the MCP server:

```sh
curl -fsSL https://raw.githubusercontent.com/aliilyas/bruster/main/install.sh | sh
claude mcp add bruster -- "$HOME/.local/bin/bruster" --mcp --quiet
```

Serve the included fixture in another terminal:

```sh
git clone https://github.com/aliilyas/bruster.git
python3 -m http.server 8765 --bind 127.0.0.1 --directory bruster/examples/launch-demo
```

Then ask Claude:

> Use Bruster to open http://127.0.0.1:8765. Inspect the page. Enter Ada Lovelace
> as the name and Bruster as the project. Select Form submission, enable Include
> screenshots, and submit. Verify that the confirmation names Bruster and says
> Screenshots: on. Return a screenshot.

Bruster uses native webviews: WKWebView, WebKitGTK, or WebView2. No Node.js is
needed for the server. Linux requires WebKitGTK 4.1 and a display or Xvfb;
Windows downloads and WebView2 requirements are in the README. Add `--visible`
to the server arguments to watch the browser.

Inputs are synthetic DOM events, and cross-origin iframes are not supported.
The included video demonstrates the same tool sequence with a scripted MCP
client; it is not a recording of Claude.

Repo, demo, and setup: https://github.com/aliilyas/bruster

I'd be interested in compatibility reports from people trying the workflow in
their own Claude Code setup.
