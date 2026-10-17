# Window controls

Native protocol methods `maximize` and `minimize` target the specified `tab`
(or the current tab). They return `"maximized"` or `"minimized"`. Each mode
clears the other mode. The requested mode is saved immediately and restored
for windows created in subsequent runs. Persistence failures are protocol
errors, not silent successes.

Hidden windows (including default MCP windows) save the requested mode but
keep their off-screen, fixed-size rendering behavior.

With `--profile PATH`, metadata is a sibling of the canonical profile directory,
named `PATH.bruster-window.json`, separate from WebView cookies/cache data.
Without a profile, the file is:

- Linux: `$XDG_STATE_HOME/bruster/window.json`, falling back to
  `$HOME/.local/state/bruster/window.json`.
- macOS: `$HOME/Library/Application Support/bruster/window.json`.
- Windows: `%LOCALAPPDATA%/bruster/window.json`.

The mode is profile-wide; the last successful command wins. Missing or malformed
metadata starts in normal mode. OS window-manager interactions are not recorded.

MCP exposes these controls, `close_tab`, and `close`. Native/MCP `close` shuts
down the whole process after replying; closing a window through the OS closes
only that tab. Closing stdin still shuts down the server.
