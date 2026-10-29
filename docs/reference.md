# Bruster reference

[Getting started](../README.md) ·
[Installation and Docker](https://aliilyas.github.io/bruster/docs/#install) ·
[MCP client setup](https://aliilyas.github.io/bruster/mcp/)

Bruster uses WKWebView on macOS, WebKitGTK on Linux, and WebView2 on Windows
through [wry](https://github.com/tauri-apps/wry). WebView2 is Chromium-based.
Browser runtimes and their helper processes are separate from the Rust controller.

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
| `--no-images` | do not load images (Linux only) |

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

### Linux runtime

`--hidden` and `--mcp` move windows off-screen; WebKitGTK still requires a
display or Xvfb. With no `DISPLAY`, Bruster automatically tries `xvfb-run -a`.
Install WebKitGTK 4.1, Xvfb, and xauth as described in the
[Linux setup guide](https://aliilyas.github.io/bruster/docs/#linux).

Hidden/MCP mode skips the desktop session bus to avoid waiting for unavailable
desktop portals. Set `BRUSTER_USE_SESSION_BUS=1` for desktop session integration
in hidden mode. `--visible` uses the normal session bus.

Linux uses software rendering. Hidden views skip off-screen GTK painting while
remaining mapped for layout, animation, and native screenshots. Set
`BRUSTER_PAINT_HIDDEN=1` to enable those window paints. Hidden mode also defaults
`WEBKIT_DISABLE_DMABUF_RENDERER=1` to avoid an unnecessary graphics transport
probe; an explicitly supplied value (including `0`) takes precedence.

Automatic Xvfb launches disable GLX. `BRUSTER_XVFB_ARGS` overrides the server
arguments (default: `-screen 0 1280x1024x24 -nolisten tcp -extension GLX`). Set
`BRUSTER_NO_XVFB=1` to prevent automatic Xvfb startup.

## MCP

With `--mcp`, every native method becomes an MCP tool. Screenshots return as
image content and page events as notifications. See the
[client setup guide](https://aliilyas.github.io/bruster/mcp/) for configurations.

Clients that support MCP bundles can use
[`bruster-0.3.2.mcpb`](https://github.com/aliilyas/bruster/releases/download/v0.3.2/bruster-0.3.2.mcpb).
It contains executables for all five OS/CPU combinations. Linux still needs
WebKitGTK 4.1 and a display or Xvfb; Windows needs WebView2. The official MCP
Registry name is `io.github.aliilyas/bruster`; [server.json](../server.json) pins
the bundle and its SHA-256 hash.

## Protocol

One JSON object per line, in both directions. Responses carry the request's `id`
and either `result` or `error`; page events share stdout. Wait for the matching
response before sending a dependent request. Keep stdin open for the session.

Elements are addressed by `{"selector": "css"}` or by `{"ref": "eN"}` from the
last `snapshot`/`find`. With `format: "text"`, a snapshot returns one line per
element:

```text
https://example.com/
Example Domain
e1 heading "Example Domain"
e2 text "This domain is for use in..."
e3 link "Learn more" href=https://iana.org/help/example-domains
```

Same-origin hrefs lose the origin in the text format. Alert and prompt dialogs
never block. Bruster answers them as the current `dialog` setting specifies and
reports them as `dialog` events. `beforeunload` handlers are disarmed.

Calls routed through the page runtime (`eval`, `url`, `title`, `snapshot`,
interactions, and other DOM tools) have an outer `request_timeout` in milliseconds,
defaulting to at least 30000 ms (or the requested `timeout`/`time` plus 5000 ms,
whichever is longer). This deadline includes time spent waiting for navigation.
Set it explicitly for unusually long operations.

A timeout stops waiting for the reply; it does not interrupt JavaScript already
running in the page. An infinite loop can make a web process unresponsive and may
require restarting Bruster. Late replies are discarded. Navigation uses its own
`timeout`; native operations such as screenshots do not use `request_timeout`.
MCP represents null results as the text `null`.

## API

These methods are available through JSON lines and MCP. A target is a CSS
`selector` or snapshot `ref`. Include `tab` to address a particular tab where
supported.

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
- With `--hidden`, WebKit timer throttling can make `setTimeout`-driven pages slow. macOS WKWebView suspends animation frames in off-screen windows; use `--visible` for animation-driven workflows.
