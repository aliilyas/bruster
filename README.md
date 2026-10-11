# bruster

Native webview (WKWebView / WebKitGTK / WebView2 via `wry`) driven by an agent
over JSON lines on stdio. No Chromium download, no Node, one process under 1 MB.

## Install

```
curl -fsSL https://raw.githubusercontent.com/iliyasalikhojayev/bruster/main/install.sh | sh
```

Prebuilt for macOS (arm64, x86_64) and Linux (x86_64, arm64); Windows builds
are on the releases page too. Linux needs WebKitGTK 4.1 at runtime
(`apt install libwebkit2gtk-4.1-0`, `apk add webkit2gtk-4.1`, `dnf install
webkit2gtk4.1`) and, without a desktop session, `xvfb` (bruster re-runs itself
under `xvfb-run -a` when no `DISPLAY` is set). From source: `cargo build
--release`.

Then add it to your MCP client:

```jsonc
// opencode (opencode.json), Claude Desktop (claude_desktop_config.json),
// Cursor (.cursor/mcp.json), Windsurf, Zed: same shape.
{ "mcpServers": { "bruster": { "command": "bruster", "args": ["--mcp", "--quiet"] } } }
```

```
claude mcp add bruster -- bruster --mcp --quiet          # Claude Code
codex mcp add bruster -- bruster --mcp --quiet           # Codex CLI
```

```jsonc
// VS Code (.vscode/mcp.json)
{ "servers": { "bruster": { "type": "stdio", "command": "bruster", "args": ["--mcp", "--quiet"] } } }
```

`--mcp` keeps windows hidden; add `--visible` to watch the browser.

## Run

```
bruster [--mcp] [--hidden|--visible] [--quiet] [options]
```

| flag | effect |
|---|---|
| `--mcp` | speak Model Context Protocol on stdio instead of the native protocol; implies `--hidden` |
| `--hidden` / `--visible` | park windows off-screen (an unmapped WebKitGTK view renders nothing, so screenshots would fail) / show them |
| `--quiet` | stderr to /dev/null; the webview libraries print GL, ALSA and GTK noise |
| `--viewport WxH` | initial window size, default 1280x800 |
| `--user-agent UA` | override the user agent |
| `--profile DIR` | persistent cookies and storage (Linux: data in DIR; macOS: a data store keyed by DIR). Without it the HTTP cache still persists in `$XDG_CACHE_HOME/bruster/default` (cookies and storage are wiped at start; a second concurrent bruster falls back to a temp dir), so repeat visits load about 2x faster |
| `--proxy URL` | `http://host:port` or `socks5://host:port` |
| `--init-script FILE` | JavaScript run in every page before its own scripts |
| `--insecure` | ignore TLS errors (Linux only) |
| `--no-images` | do not load images (Linux only): pages load ~30% faster, screenshots show no pictures |

Linux rendering is software only, which halves memory under Xvfb. The first
tab loads `about:blank` at start so the web process is warm by the first
`navigate`. Set `BRUSTER_NO_XVFB=1` to stop the automatic `xvfb-run`.

## Tests

`tests/run_all.sh [--rounds N] [--no-e2e]` runs the whole cycle: build, unit
tests, `tests/smoke.rs` (every method on local pages), `tests/edge.rs`
(protocol abuse, odd documents, hanging servers, limits, memory recovery),
a leftover-process check, `tests/mcp_launch.sh`, and `tests/e2e.rs` (public
sites, `--ignored` so plain `cargo test` stays offline). On Linux run it
under `xvfb-run -a`. `tests/integrations.sh <binary>` drives the server
through the MCP TypeScript SDK, the Python SDK and the Inspector CLI, with the
scrubbed environment desktop clients use. CI (`.github/workflows/ci.yml`) runs
build, unit, smoke and edge on macOS arm64 and x86_64, Ubuntu x86_64 and
arm64, Windows (build and unit only), plus e2e and the integrations on Linux,
and publishes release archives on a `v*` tag. `bin/bruster` runs the
development build from this checkout.

## MCP

`--mcp` speaks Model Context Protocol on stdio. Every method below is a tool;
`tab` is an optional argument on each. Screenshots come back as image content.
Events are sent as `notifications/message` at level `info` with the event in
`data`; `logging/setLevel` above `info` mutes them. `notifications/cancelled`
drops the reply of an in-flight call.

```json
{ "mcpServers": { "bruster": { "command": "bruster", "args": ["--mcp", "--quiet"] } } }
```

## Native protocol

One JSON object per line, both directions.

```
→ {"id":1,"method":"navigate","params":{"url":"https://example.com"}}
← {"event":"navigating","tab":1,"url":"https://example.com/"}
← {"id":1,"result":{"url":"https://example.com/"}}
← {"event":"load","tab":1,"url":"https://example.com/"}
→ {"id":2,"method":"snapshot"}
← {"id":2,"result":{"url":"...","title":"...","elements":[{"ref":"e1","role":"heading","name":"Example Domain"}, ...]}}
→ {"id":3,"method":"click","params":{"ref":"e4"},"tab":1}
← {"id":3,"result":null}
→ {"id":4,"method":"click","params":{"selector":"#nope"}}
← {"id":4,"error":"no element matches '#nope'"}
```

Elements are addressed by `{"selector": "css"}` or `{"ref": "e3"}` from the
last `snapshot` or `find`. Refs die on the next snapshot, find or navigation.
Selectors reach into open shadow roots and same-origin iframes. `tab` at the
top level picks a tab; default is the current one. Tabs share one profile:
cookies and storage set in one tab are visible in the others.

Actions (`click`, `hover`, `fill`, `type`, `press` with a target, `select`,
`check`, `drag`) wait up to `timeout` ms (default 5000) for the element to
appear, be visible, enabled and not covered, then fail with the reason
(`no element matches '#go'`, `<button#go> is covered by <div#overlay>`).
`force: true` skips the visibility checks.

A click or submit that starts a load makes the following calls wait for the
new page, so `click` then `snapshot` reads the page the click led to. Calls
that were still running when a page was replaced are re-run in the new one.
`fill`, `type`, `select` and `check` also fail on the wrong kind of element
(`<p#out> is not editable`, `no option matches 'x'`).

Snapshots list controls, headings, links and every visible text node, so a
`<div>Saved!</div>` shows up as `{role: "text", text: "Saved!"}` and its ref
acts on the div. A `<li>` or `<p>` holding a single link is folded into the
link. With `format: "text"` (the MCP default) the result is one line per
element, about 45% smaller than JSON:

```
https://example.com/
Example Domain
e1 heading "Example Domain"
e2 text "This domain is for use in..."
e3 link "Learn more" href=https://iana.org/help/example-domains
e4 checkbox "Remember me" checked=false
```

Same-origin hrefs lose the origin in the text format.

`alert`, `confirm` and `prompt` never block: they are answered with the
current `dialog` setting (accept by default) and reported as a `dialog` event.
`beforeunload` handlers are disarmed before the page installs them, so leaving
a page never prompts.

| method | params | result |
|---|---|---|
| `navigate` | `url`, `until?` (`load` default, `dom`, `idle`), `timeout?` ms (default 30000) | `{tab, url}` at the page's load event, at DOMContentLoaded (`dom`: 2-4x sooner on server-rendered pages, too early for SPAs), or once the network has been quiet for 500 ms after load (`idle`, capped at 10 s). Fails on a malformed url, a connection or DNS error, a download (Linux), its timeout, or when a newer navigation supersedes it |
| `reload` `back` `forward` | | `{url}` after load finishes, `null` if there was nowhere to go |
| `url` `title` | | string |
| `eval` | `expression` | JSON value; an expression, or statements with `return`; promises are awaited. Compiled as script, so a page CSP without `unsafe-eval` cannot block it |
| `snapshot` | `selector?`, `max?` (default 1000), `boxes?`, `format?` (`json` default, `text`) | `{url, title, elements[], truncated?}` or the text lines |
| `find` | `text?` or `regex?`, plus snapshot params | snapshot filtered on name, text, value or href (each field on its own, so `^...$` works) |
| `screenshot` | `path?`, `full?`, `clip?` `{x,y,width,height}` | `{path, bytes}` or `{png_base64}`; full pages are capped at 16000 px |
| `rect` | target | `{x, y, width, height}` viewport-relative, feeds `clip` |
| `click` | target or `x`,`y`; `force?`, `timeout?` | `null` |
| `hover` | target | `null` |
| `fill` | target, `value` | `null` |
| `fill_form` | `fields: [{selector\|ref, value}]` | `null`; checkboxes take a bool, selects a value or array |
| `type` | target, `text`, `delay?`, `submit?` | `null` |
| `press` | target?, `key` (`Enter`, `Control+a`) | `null` (a printable key inserts its character, Enter submits the form; events carry `code`, `keyCode` and `which`) |
| `select` | target, `value` (string or array) | selected values |
| `check` | target, `checked?` | bool |
| `drag` | `from` target, `to` target | `null` (HTML5 drag events with a shared DataTransfer) |
| `upload` | target, `paths[]` | file names set on the input |
| `scroll` | target or `x`,`y` | `{x, y}` |
| `resize` | `width`, `height` (1 to 16000) | `{width, height}` |
| `text` `html` | target | string |
| `attr` | target, `name` | string or null |
| `count` | `selector` | number |
| `wait_for` | `selector`/`ref` + `state?` (visible, attached, hidden), or `text`, `textGone`, `url`, `idle` (no fetch/xhr for 500 ms), `time` ms; `timeout?` ms | `null` |
| `network` | `clear?` | `[{index, type, method, url, status, ms}]`; fetch/xhr have status and index, other resources do not |
| `network_request` | `index` | one fetch/xhr entry with `req_headers`, `res_headers`, `body` (first 16 KB) |
| `console` | `clear?` | `[{level, text, ms}]` console output and uncaught errors since navigation |
| `dialog` | `accept?`, `text?`, `clear?` | dialogs seen so far; sets the answer for the next ones |
| `cookies` | | list |
| `set_cookie` | `name`, `value`, `domain?` (default: current host), `path?` (default `/`) | `null` |
| `new_tab` | `url?` | `{tab}`, or `{tab, url}` after the page loads when `url` is given |
| `tabs` | | `[{tab, url, current}]` |
| `switch_tab` | `tab` | `null` |
| `close_tab` | (uses `tab`) | `null` |
| `close` | | exits |

Events: `ready`, `navigating`, `load`, `tab_opened` (target=_blank or
window.open landed in a new tab), `tab_closed`, `dialog` (`type`, `message`,
`accept`), `tls_error` (Linux; the page stays blank unless `--insecure`),
`load_failed` and `download` (Linux; downloads are cancelled, nothing is
written to disk).

## Limits

- Input is synthetic DOM events (`isTrusted` is false): no `:hover` styles,
  no native `<select>` popups, no OS level shortcuts, and sites that check
  `isTrusted` will ignore it.
- Network and console logs are in-page (patched fetch/XHR/console + Performance
  API), so no request bodies, no blocking, and they reset on navigation. Use
  `--proxy` for real interception.
- Cross-origin iframes are out of reach; same-origin ones and open shadow
  roots work.
- `data:` and `file:` pages load but in-page calls get no reply (wry drops
  messages whose page URL is not a valid `http::Uri`). Serve pages over
  localhost instead.
- Native file choosers are not intercepted; use `upload` instead of clicking
  a file input.
- An `eval` that keeps a `querySelectorAll` NodeList of a large page can pin
  that page in memory until the next full GC; prefer a `TreeWalker` or
  `count`/`snapshot`.
- Full-page screenshot on macOS, and on Linux above cairo's 32767 px, resizes
  the window to the document height (capped at 16000px) and back; on macOS
  the window cannot grow past the screen, so very tall pages are cut there.
- Without `--profile`, cookies and storage live for one session. On Linux the
  HTTP cache is kept across sessions (exit waits up to 1.2 s after the last
  load so WebKit can write it); on macOS the session is fully non-persistent.
- Off-screen windows get WebKit's background timer throttling (macOS; also
  Linux without a compositor), so `setTimeout`-driven pages run slower under
  `--hidden`. Use `--visible` when timing matters.
- On macOS a `navigate` to a host that refuses or does not resolve ends with
  its `timeout` (default 30 s) instead of an immediate error; `--proxy` and
  `back`/`forward` with `until` are verified on Linux only.
- Snapshots prefetch DNS for the hosts of the links they list (Linux).
- The webview starts blank; send `navigate` first.
- Windows (WebView2): `screenshot` has no `clip`, failed loads show as
  "load failed" (the WebView2 error page), `--quiet` is a no-op, and the
  Linux-only flags do nothing.
