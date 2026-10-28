<div align="center">
  <img src="assets/logo.svg" width="96" alt="bruster">
  <h1>bruster</h1>
  <p>
    <strong>Native webview browser driven by an agent over JSON lines on stdio.</strong>
  </p>
  <p>
    WKWebView · WebKitGTK · WebView2. A small Rust executable using native browser runtimes. No Node required.
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
    <a href="https://aliilyas.github.io/bruster/benchmarks/">Performance</a> ·
    <a href="https://aliilyas.github.io/bruster/test-lab/">Test Lab</a>
  </p>
</div>

<br>

bruster uses native browser engines, installed separately where required.
Its Rust controller reads and writes JSON lines on stdin and stdout; rendering
also uses browser helper processes. This design is good for agents, scripts, and test harnesses. The
`--mcp` option exposes every method as a tool.

## Why bruster?

- **No Chromium.** bruster uses WKWebView on macOS, WebKitGTK on Linux, and WebView2 on Windows. It uses [wry](https://github.com/tauri-apps/wry) to control them.
- **Small controller.** One small release executable, with a separately installed native browser runtime. The complete runtime footprint includes its libraries and helper processes.
- **Agent support.** [MCP](#mcp) support with `--mcp`. Screenshots return as image content, and page events return as notifications.
- **Cross-platform.** Prebuilt for macOS (arm64, x86_64), Linux (x86_64, arm64), and Windows (x86_64).
- **Practical API.** Navigate, snapshot, click, fill forms, drag, upload, take screenshots, inspect the network and console, manage tabs, and keep a session with `--profile`.
- **Deterministic and safe.** Each call is one line-based JSON request and response. `beforeunload` is disarmed, and dialogs never block.
- **Fast.** A persistent HTTP cache and profiles make repeat visits faster. The first tab loads `about:blank` while the agent starts.

> [!TIP]
> [Live benchmarks](https://aliilyas.github.io/bruster/benchmarks/) compare Bruster with the latest stable Playwright, Puppeteer, and agent-browser after every merge to `main`: startup, navigation, extraction, screenshots, total process memory, and installed runtime files. See [benchmark setup and methodology](benchmarks/README.md).

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
> **Linux requirements.** WebKitGTK 4.1 is necessary at run time. Install it with one of these commands: `apt install libwebkit2gtk-4.1-0`, `apk add webkit2gtk-4.1`, or `dnf install webkit2gtk4.1`. If the system has no desktop session, bruster starts again under `xvfb-run -a` when `DISPLAY` is not set.

### Docker / Glama

The [Dockerfile](Dockerfile) builds the locked Rust source and includes WebKitGTK,
Xvfb, fonts, and HTTPS certificates. The runtime image runs as a non-root user;
the compiler and development packages stay in the build stage. Linux amd64 and
arm64 images are built and exercised in [Docker CI](.github/workflows/docker.yml).

```sh
docker build -t bruster:local .
docker run --rm -i bruster:local
```

The default command serves MCP on stdin/stdout. Keep `-i` and omit `-t` for MCP
clients; no port mapping or host display is needed. For example:

```json
{ "mcpServers": { "bruster": { "command": "docker", "args": ["run", "--rm", "-i", "bruster:local"] } } }
```

To pass additional options, include `--mcp` again, for example
`docker run --rm -i bruster:local --mcp --viewport 1920x1080`.
The image uses software rendering and disables WebKit's nested sandbox because
Docker's default seccomp profile blocks its user namespaces. It needs no
`--privileged` or extra capabilities. Tini forwards shutdown signals and reaps
browser helper processes. Diagnostics remain on stderr.

For Glama, submit the Dockerfile in the listing's **Admin → Docker builds**
configuration, using this repository as the build context, then run its evaluation.
The default command answers `initialize` and `tools/list` without credentials.

To test the image on a Linux Docker host (Python standard library only):

```sh
python3 tests/docker.py --image bruster:local --https
```

This checks MCP discovery, navigation, form interactions, JavaScript, screenshots,
tabs, HTTPS certificates, and shutdown via MCP, stdin EOF, and SIGTERM. Containers
run with a 512 MiB memory limit, all capabilities dropped, and no new privileges;
the report includes image size, initialization time, and memory use.

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

You receive the results and events on stdout:

```json
{"event":"load","tab":1,"url":"https://example.com/"}
{"id":1,"result":{"url":"https://example.com/"}}
{"id":2,"result":{"url":"https://example.com/","title":"Example Domain","elements":[...]}}
{"id":3,"result":null}
```

## MCP

With `--mcp`, bruster uses the Model Context Protocol on stdio. Every native
method becomes a tool. Screenshots return as image content, and page events
return as notifications.

### Common MCP client configs

```jsonc
// Claude Desktop (claude_desktop_config.json), Cursor (.cursor/mcp.json)
{ "mcpServers": { "bruster": { "command": "bruster", "args": ["--mcp", "--quiet"] } } }
```

```sh
claude mcp add bruster -- bruster --mcp --quiet          # Claude Code
codex mcp add bruster -- bruster --mcp --quiet           # Codex CLI
opencode mcp add bruster -- bruster --mcp --quiet        # OpenCode
```

OpenCode V2 uses `mcp.servers` in `opencode.jsonc`. See the
[client-specific MCP setup guide](https://aliilyas.github.io/bruster/mcp/)
for complete configurations.

```jsonc
// VS Code (.vscode/mcp.json)
{ "servers": { "bruster": { "type": "stdio", "command": "bruster", "args": ["--mcp", "--quiet"] } } }
```

`--mcp` keeps the windows off-screen. Add `--visible` to see the browser.
`--hidden` is not true headless mode: on Linux, WebKitGTK still requires an
X11/Wayland display or Xvfb. When no display is set, Bruster automatically tries
`xvfb-run`; install Xvfb if it is unavailable.

On Linux, hidden/MCP mode skips the desktop session bus to avoid waiting for
unavailable desktop portals. Set `BRUSTER_USE_SESSION_BUS=1` if you need desktop
session integration in hidden mode. `--visible` uses the normal session bus.

## Run

```sh
bruster [--mcp] [--hidden|--visible] [--quiet] [options]
```

| flag | effect |
|---|---|
| `--mcp` | use the Model Context Protocol on stdio instead of the native protocol. This option also sets `--hidden` |
| `--hidden` / `--visible` | move the windows off-screen / show the windows |
| `--quiet` | send stderr to `/dev/null`. This mutes GL, ALSA, and GTK noise |
| `--viewport WxH` | initial window size, default 1280x800 |
| `--user-agent UA` | replace the user agent |
| `--profile DIR` | keep cookies and storage between runs |
| `--proxy URL` | `http://host:port` or `socks5://host:port` |
| `--init-script FILE` | JavaScript that runs in every page before its own scripts |
| `--dark` | persist dark color-scheme for this profile (or the default state); use `light` to reset |
| `--insecure` | ignore TLS errors (Linux only) |
| `--no-images` | do not load images. Pages load about 30% faster (Linux only) |

### Window and color controls

Native commands and MCP tools `minimize` and `maximize` target the specified `tab`
(or the current tab), return `"minimized"` or `"maximized"`, and persist the requested
window mode. Each mode replaces the previous one. `minimize` hides the native
window (rather than iconifying it); `maximize` restores visibility and maximizes.
In hidden/MCP mode both commands are accepted and saved, but windows stay
off-screen for rendering.

`dark` and `light` persist a color preference independently of window mode and
apply it to all existing tabs, new tabs, and subsequent navigations. The portable
page-level fallback sets the root CSS `color-scheme` (including native controls
and default page colors); it does not emulate `prefers-color-scheme` media queries
or recolor a site's explicit colors. Custom `--init-script` scripts still run.

Preferences are stored outside WebView data. With `--profile PATH`, metadata is
a sibling of the canonical profile directory, named `PATH.bruster-window.json`.
Without a profile, the file is:

- Linux: `$XDG_STATE_HOME/bruster/window.json`, falling back to
  `$HOME/.local/state/bruster/window.json`.
- macOS: `$HOME/Library/Application Support/bruster/window.json`.
- Windows: `%LOCALAPPDATA%/bruster/window.json`.

Settings are profile-wide; the last successful command wins. Missing or malformed
metadata uses defaults, and legacy window-only state files are still accepted.
Persistence failures return protocol errors. OS window-manager changes are not
saved. `close` shuts down the server and all tabs; `close_tab` or closing a window
through the OS closes only that tab. Closing stdin also shuts down the server.

Linux uses software rendering. Hidden views skip off-screen GTK painting while
remaining mapped for layout, animation, and native screenshots. Set
`BRUSTER_PAINT_HIDDEN=1` to enable those window paints. Hidden mode also defaults
`WEBKIT_DISABLE_DMABUF_RENDERER=1` to avoid an unnecessary graphics transport
probe; an explicitly supplied value (including `0`) takes precedence.

Automatic Xvfb launches disable GLX. `BRUSTER_XVFB_ARGS` overrides the server
arguments (default: `-screen 0 1280x1024x24 -nolisten tcp -extension GLX`). Set
`BRUSTER_NO_XVFB=1` to prevent automatic Xvfb startup.

## Tests

The [Test Lab](https://aliilyas.github.io/bruster/test-lab/) provides individual
HTML/CSS/JavaScript fixtures with executable assertions. Cargo builds Bruster
and runs 39 focused fixtures through both native JSONL and MCP (Python 3.10+
required; prefix with `xvfb-run -a` on headless Linux):

```sh
cargo test --release --test test_lab

# Opt-in check against the published site, including real React/Vue/Svelte apps.
cargo test --release --test test_lab -- --ignored --exact published_test_lab
```

See [test-lab setup and coverage](tests/site/README.md) for the complete core
suite (`full_test_lab`), individual case filters, stress cases, pinned framework
bundles, and reports. The Python runner also accepts an existing executable:

```sh
python3 scripts/test_lab.py run --binary target/release/bruster --case 'ref-*' --transport both
```

`tests/run_all.sh [--rounds N] [--no-e2e] [--no-lab]` runs the full test cycle:
build, unit, smoke, edge, focused test-lab groups, a leftover-process check, MCP
launch, and end-to-end tests including the published lab. `--no-e2e` keeps the
cycle local; `--no-lab` omits both lab runs. On Linux, run the script under
`xvfb-run -a`. CI runs the complete core lab on every platform and publishes
release archives on `v*` tags.

The Linux desktop-portal startup regression requires D-Bus, `python3-dbus`, and
`python3-gi`:

```sh
cargo build --release --locked
xvfb-run -a /usr/bin/python3 tests/startup_portal.py target/release/bruster
```

## Protocol

One JSON object per line, in both directions. Elements are addressed by `{"selector": "css"}` or by `{"ref": "eN"}` from the last `snapshot`/`find`. With `format: "text"`, a snapshot returns one line per element:

```text
https://example.com/
Example Domain
e1 heading "Example Domain"
e2 text "This domain is for use in..."
e3 link "Learn more" href=https://iana.org/help/example-domains
e4 checkbox "Remember me" checked=false
```

> [!NOTE]
> Same-origin hrefs lose the origin in the text format. Alert and prompt dialogs never block. bruster answers them as the current `dialog` setting specifies, and reports them as `dialog` events. `beforeunload` handlers are disarmed.

Calls routed through the page runtime (`eval`, `url`, `title`, `snapshot`, interactions and other DOM tools) have an outer `request_timeout` in milliseconds, defaulting to at least 30000 ms (or the requested `timeout`/`time` plus 5000 ms, whichever is longer). This deadline includes time spent waiting for navigation. Set it explicitly for unusually long operations. A timeout stops waiting for the reply; it does not interrupt JavaScript already running in the page. In particular, an infinite loop can make a web process unresponsive and may require restarting bruster. Late replies are discarded. Navigation uses its own `timeout`; native operations such as screenshots do not use `request_timeout`. MCP represents null results as the text `null`.

## API

| method | params | result |
|---|---|---|
| `navigate` | `url`, `until?` (`load` default, `dom`, `idle`), `timeout?` ms (default 30000) | `{tab, url}` on load/DOM/idle, or a failure on timeout, DNS/error, or download (Linux) |
| `reload` `back` `forward` | none | `{url}`, or `null` if there is nowhere to go |
| `url` `title` | none | string |
| `eval` | `expression` | JSON value. Promises are awaited. Compiled as a script |
| `snapshot` | `selector?`, `max?` (1000), `boxes?`, `format?` (native default `json`, MCP default `text`) | `{url,title,elements[],truncated?}` or text lines |
| `find` | `text?` or `regex?` + snapshot params | filtered snapshot |
| `screenshot` | `path?`, `full?`, `clip?` `{x,y,width,height}` | `{path,bytes}` or `{png_base64}`. Full pages are capped at 16000 px |
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
| `upload` | target, `paths[]` | file names set on the input |
| `scroll` | target or `x,y` deltas | `{x,y}` current position |
| `resize` | `width`, `height` (1 to 16000) | `{width,height}` |
| `text` `html` | target | string |
| `attr` | target, `name` | string or null |
| `count` | `selector` | number |
| `wait_for` | `selector`/`ref` + `state?` (visible, attached, hidden), `text`, `textGone`, `url`, `idle`, `time` ms; `timeout?` ms | `null` |
| `network` | `clear?` | fetch/XHR entries with index, method and status where available, plus resource timing entries |
| `network_request` | `index` | one entry with `req_headers`, `res_headers`, and `body` (first 16 KB) |
| `console` | `clear?` | `[{level,text,ms}]` console output and uncaught errors |
| `dialog` | `accept?`, `text?`, `clear?` | dialogs seen. Sets the answer for the next dialogs |
| `cookies` | none | list |
| `set_cookie` | `name`, `value`, `domain?`, `path?` (`/`) | `null` |
| `new_tab` | `url?`, `timeout?` ms (default 30000) | `{tab}`, or `{tab,url}` after load; does not switch the current tab |
| `tabs` | none | `[{tab,url,current}]` |
| `switch_tab` | `tab` | `null` |
| `close_tab` | (uses `tab`) | `null`; closing the last tab is rejected (use `close`) |
| `close` | none | exits |

## Events

`ready`, `navigating`, `load`, `tab_opened`, `tab_closed`, `dialog` (`type`, `message`, `accept`), `tls_error` (Linux), `load_failed`, and `download` (Linux).

## Limits

- Input uses synthetic DOM events (`isTrusted` is false). You do not get `:hover` styles, native `<select>` popups, or OS-level shortcuts.
- Network and console logs are patched in the page and reset on navigation. Network entries for fetch/XHR include status and an index; other resources use performance timings and may lack status or method. The document request is not included. Logs contain no request bodies. Use `--proxy` for real interception.
- Cross-origin iframes are out of reach. Same-origin iframes and open shadow roots work.
- Use HTTP(S) URLs for navigation. `data:` and `file:` URLs are unsupported; serve local pages over localhost instead.
- bruster does not intercept native file choosers. Use `upload` instead of a click on a file input.
- Without `--profile`, cookies and storage last for one session.
- Full-page screenshots are capped at 16000 px. On macOS, very tall pages can be cut when they are higher than the screen.
- WebKitGTK screenshots capture page content without non-overlay scrollbars, so their width can be narrower than the window viewport.
- On Windows (WebView2), `screenshot` has no `clip`. `--quiet` does nothing. The Linux-only flags have no effect.
- With `--hidden`, WebKit timer throttling can make `setTimeout`-driven pages slow.

## Development

- `bin/bruster` runs the development build from this checkout.
- `tests/run_all.sh` runs the build, unit tests, smoke tests, edge tests, test-lab groups, the MCP launch check, and end-to-end tests.
- CI (`.github/workflows/ci.yml`) builds all platforms, runs the tests, and publishes release archives on `v*` tags.
- Benchmarks: `scripts/bench_compare.py` compares five configurations; `scripts/bench_footprint.py` inventories runtime files and `scripts/bench_report.py` validates and publishes results. See [setup and methodology](benchmarks/README.md).
- Test Lab: `tests/test_lab.rs` integrates the shared fixtures into Cargo; `scripts/test_lab.py` builds, serves, and runs them. See [case authoring and verification](tests/site/README.md).
- Website: `site/` contains the GitHub Pages source. See [local preview and publishing](site/README.md).

## License

[MIT License](LICENSE)
