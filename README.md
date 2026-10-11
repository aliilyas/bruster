<div align="center">
  <img src="assets/logo.svg" width="96" alt="bruster">
  <h1>bruster</h1>
  <p>
    <strong>Native webview browser driven by an agent over JSON lines on stdio.</strong>
  </p>
  <p>
    WKWebView · WebKitGTK · WebView2 &mdash; no Chromium download, no Node, one process under 1&nbsp;MB.
  </p>
  <p>
    <a href="https://github.com/aliilyas/bruster/actions/workflows/ci.yml"><img src="https://github.com/aliilyas/bruster/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
    <a href="https://github.com/aliilyas/bruster/releases/latest"><img src="https://img.shields.io/github/v/release/aliilyas/bruster?label=release&color=6ee7f7" alt="Release"></a>
    <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="MIT License"></a>
    <img src="https://img.shields.io/badge/macOS-arm64%20%7C%20x86__64-lightgrey.svg" alt="macOS">
    <img src="https://img.shields.io/badge/Linux-x86__64%20%7C%20arm64-FCC624.svg" alt="Linux">
    <img src="https://img.shields.io/badge/Windows-x86__64-0078D4.svg" alt="Windows">
    <a href="https://aliilyas.github.io/bruster/"><img src="https://img.shields.io/badge/docs-%E2%9C%93-6ee7f7.svg" alt="Website"></a>
  </p>
  <p>
    <a href="#install">Install</a> ·
    <a href="#quickstart">Quickstart</a> ·
    <a href="#mcp">MCP</a> ·
    <a href="#protocol">Protocol</a> ·
    <a href="#api">API</a> ·
    <a href="https://aliilyas.github.io/bruster/">Performance</a>
  </p>
</div>

<br>

bruster wraps the browser engines your operating system already ships. It runs
as a single, lightweight process and speaks JSON lines on stdin/stdout —
perfect for agents, scripts and test harnesses. With `--mcp` it exposes
every method as a tool.

## Why bruster?

- **No Chromium.** Uses WKWebView (macOS), WebKitGTK (Linux) and WebView2 (Windows) via [wry](https://github.com/tauri-apps/wry).
- **Tiny footprint.** One release binary, usually **< 1&nbsp;MB**; no bundled runtime or download on first run.
- **Agent-ready.** First-class [MCP](#mcp) support (`--mcp`) with screenshots as image content and page events as notifications.
- **Cross-platform.** Prebuilt for macOS (arm64, x86_64), Linux (x86_64, arm64) and Windows (x86_64).
- **Practical API.** Navigate, snapshot, click, fill forms, drag, upload, take screenshots, inspect network/console, manage tabs, persist sessions with `--profile`.
- **Deterministic and safe.** Every call is a line-based JSON request/response. `beforeunload` is disarmed and dialogs never block.
- **Fast.** Persistent HTTP cache and profiles help repeat visits. The first tab warms `about:blank` while the agent sets up.

> [!TIP]
> Live performance numbers (cold start, page load, snapshot and idle memory) are published at [aliilyas.github.io/bruster/](https://aliilyas.github.io/bruster/).

## Install

### One-liner (recommended)

```sh
curl -fsSL https://raw.githubusercontent.com/aliilyas/bruster/main/install.sh | sh
```

The script installs the correct build for your OS and CPU into `~/.local/bin`.

### Prebuilt releases

Download archives for all platforms from the [Releases page](https://github.com/aliilyas/bruster/releases).

### From source

```sh
cargo build --release
```

> [!NOTE]
> **Linux requirements.** WebKitGTK 4.1 is needed at runtime: `apt install libwebkit2gtk-4.1-0`, `apk add webkit2gtk-4.1`, or `dnf install webkit2gtk4.1`. Without a desktop session, bruster automatically re-runs under `xvfb-run -a` when no `DISPLAY` is set.

## Quickstart

Run bruster in its native protocol mode:

```sh
bruster
```

Then send JSON objects, one per line:

```json
{"id":1,"method":"navigate","params":{"url":"https://example.com"}}
{"id":2,"method":"snapshot"}
{"id":3,"method":"click","params":{"ref":"e2"}}
{"id":4,"method":"close"}
```

You'll receive results and events back on stdout:

```json
{"event":"load","tab":1,"url":"https://example.com/"}
{"id":1,"result":{"url":"https://example.com/"}}
{"id":2,"result":{"url":"https://example.com/","title":"Example Domain","elements":[...]}}
{"id":3,"result":null}
```

## MCP

With `--mcp`, bruster speaks the Model Context Protocol over stdio. Every
native method becomes a tool; screenshots return as image content and page
events come through as notifications.

### Common MCP client configs

```jsonc
// opencode (opencode.json), Claude Desktop (claude_desktop_config.json),
// Cursor (.cursor/mcp.json), Windsurf, Zed
{ "mcpServers": { "bruster": { "command": "bruster", "args": ["--mcp", "--quiet"] } } }
```

```sh
claude mcp add bruster -- bruster --mcp --quiet          # Claude Code
codex mcp add bruster -- bruster --mcp --quiet           # Codex CLI
```

```jsonc
// VS Code (.vscode/mcp.json)
{ "servers": { "bruster": { "type": "stdio", "command": "bruster", "args": ["--mcp", "--quiet"] } } }
```

`--mcp` keeps windows hidden; add `--visible` to watch the browser.

## Run

```sh
bruster [--mcp] [--hidden|--visible] [--quiet] [options]
```

| flag | effect |
|---|---|
| `--mcp` | speak Model Context Protocol on stdio instead of the native protocol; implies `--hidden` |
| `--hidden` / `--visible` | park windows off-screen / show them |
| `--quiet` | stderr to `/dev/null`; mutes GL, ALSA and GTK noise |
| `--viewport WxH` | initial window size, default 1280x800 |
| `--user-agent UA` | override the user agent |
| `--profile DIR` | persistent cookies and storage |
| `--proxy URL` | `http://host:port` or `socks5://host:port` |
| `--init-script FILE` | JavaScript run in every page before its own scripts |
| `--insecure` | ignore TLS errors (Linux only) |
| `--no-images` | do not load images (Linux only); pages load ~30% faster |

Linux rendering is software only under Xvfb (halves memory). Set `BRUSTER_NO_XVFB=1` to stop automatic `xvfb-run -a`.

## Tests

`tests/run_all.sh [--rounds N] [--no-e2e]` runs the full suite: build, unit tests, smoke, edge, leftover-process check, MCP launch, and e2e tests. On Linux, run it under `xvfb-run -a`. CI runs builds, tests and publishes release archives on `v*` tags.

## Protocol

One JSON object per line in both directions. Elements are addressed by `{"selector": "css"}` or `{"ref": "eN"}` from the last `snapshot`/`find`. With `format: "text"`, a snapshot returns one line per element:

```text
https://example.com/
Example Domain
e1 heading "Example Domain"
e2 text "This domain is for use in..."
e3 link "Learn more" href=https://iana.org/help/example-domains
e4 checkbox "Remember me" checked=false
```

> [!NOTE]
> Same-origin hrefs lose the origin in the text format. Alerts/prompts never block — they're answered according to the current `dialog` setting and reported as `dialog` events. `beforeunload` handlers are disarmed.

## API

| method | params | result |
|---|---|---|
| `navigate` | `url`, `until?` (`load` default, `dom`, `idle`), `timeout?` ms (default 30000) | `{tab, url}` on load/DOM/idle, or fails on timeout, DNS/error, download (Linux) |
| `reload` `back` `forward` | — | `{url}` or `null` if nowhere to go |
| `url` `title` | — | string |
| `eval` | `expression` | JSON value; promises awaited; compiled as script |
| `snapshot` | `selector?`, `max?` (1000), `boxes?`, `format?` (`json` default, `text`) | `{url,title,elements[],truncated?}` or text lines |
| `find` | `text?` or `regex?` + snapshot params | filtered snapshot |
| `screenshot` | `path?`, `full?`, `clip?` `{x,y,width,height}` | `{path,bytes}` or `{png_base64}`; full pages capped at 16000 px |
| `rect` | target | `{x,y,width,height}` viewport-relative |
| `click` | target or `x,y`; `force?`, `timeout?` | `null` |
| `hover` | target | `null` |
| `fill` | target, `value` | `null` |
| `fill_form` | `fields: [{selector\|ref, value}]` | `null` (checkboxes bool, selects string/array) |
| `type` | target, `text`, `delay?`, `submit?` | `null` |
| `press` | target?, `key` (`Enter`, `Control+a`) | `null` |
| `select` | target, `value` | selected values |
| `check` | target, `checked?` | bool |
| `drag` | `from` target, `to` target | `null` |
| `upload` | target, `paths[]` | file names set on input |
| `scroll` | target or `x,y` | `{x,y}` |
| `resize` | `width`, `height` (1–16000) | `{width,height}` |
| `text` `html` | target | string |
| `attr` | target, `name` | string or null |
| `count` | `selector` | number |
| `wait_for` | `selector`/`ref` + `state?` (visible, attached, hidden), `text`, `textGone`, `url`, `idle`, `time` ms; `timeout?` ms | `null` |
| `network` | `clear?` | `[{index,type,method,url,status,ms}]` |
| `network_request` | `index` | one entry with `req_headers`, `res_headers`, `body` (first 16 KB) |
| `console` | `clear?` | `[{level,text,ms}]` console output and uncaught errors |
| `dialog` | `accept?`, `text?`, `clear?` | dialogs seen; sets answer for next ones |
| `cookies` | — | list |
| `set_cookie` | `name`, `value`, `domain?`, `path?` (`/`) | `null` |
| `new_tab` | `url?` | `{tab}` or `{tab,url}` after load if URL given |
| `tabs` | — | `[{tab,url,current}]` |
| `switch_tab` | `tab` | `null` |
| `close_tab` | (uses `tab`) | `null` |
| `close` | — | exits |

## Events

`ready`, `navigating`, `load`, `tab_opened`, `tab_closed`, `dialog` (`type`, `message`, `accept`), `tls_error` (Linux), `load_failed` and `download` (Linux).

## Limits

- Input is synthetic DOM events (`isTrusted` is false): no `:hover` styles, no native `<select>` popups, no OS-level shortcuts.
- Network/console logs are patched in-page; no request bodies, reset on navigation. Use `--proxy` for real interception.
- Cross-origin iframes are out of reach; same-origin iframes and open shadow roots work.
- `data:` and `file:` pages load but in-page calls get no reply; serve over localhost instead.
- Native file choosers are not intercepted; use `upload` instead of clicking a file input.
- Without `--profile`, cookies and storage live for one session.
- Full-page screenshots capped at 16000 px; on macOS very tall pages may be cut if exceeding screen height.
- Windows (WebView2): `screenshot` has no `clip`, `--quiet` is a no-op, Linux-only flags have no effect.
- Under `--hidden`, WebKit timer throttling can slow `setTimeout`-driven pages.

## Development

- `bin/bruster` runs the development build from this checkout.
- `tests/run_all.sh` runs build, unit, smoke, edge, MCP launch and e2e.
- CI (`.github/workflows/ci.yml`) builds all platforms, runs tests, and publishes release archives on `v*` tags.
- Benchmarks: `scripts/bench.py` measures binary size, cold start, page load, snapshot and idle RSS under Xvfb.

## License

[MIT License](LICENSE)
