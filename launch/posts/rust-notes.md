# Rust technical article: outline and source references

These notes support a human-authored article about controlling native webviews
from Rust. Add your actual motivation, experiments, and lessons rather than
publishing this outline as an article.

Potential destinations:

- [r/rust](https://www.reddit.com/r/rust/): check its current project-sharing and
  AI-content rules; lead with concrete Rust engineering details.
- [This Week in Rust](https://github.com/rust-lang/this-week-in-rust): currently
  rejects AI-written articles and does not accept Project/Tooling Updates PRs.
  Once a human-authored technical article is public, submit its canonical title
  and URL to the appropriate community section of the current `drafts/` issue.

## 1. One command shape, two protocols

Source: [Request](../../src/main.rs), [MCP adapter](../../src/mcp.rs).

```rust
#[derive(Deserialize)]
struct Request {
    id: u64,
    method: String,
    #[serde(default)]
    params: Value,
    tab: Option<TabId>,
}
```

Discuss why line-delimited requests are convenient for subprocess clients.
Trace `tools/call` through `mcp::incoming`, the internal request ID, native
dispatch, and `mcp::outgoing`. The MCP layer also converts PNG responses into
image content and gates event notifications on initialization.

## 2. Hosting the webview and the page runtime

Sources: `build_webview` in [main.rs](../../src/main.rs),
[runtime.js](../../src/runtime.js), [Cargo dependencies](../../Cargo.toml).

The builder installs the page runtime with `with_initialization_script` and
receives replies through `with_ipc_handler`. `tao` provides the event loop and
native windows, while `wry` hosts each platform's webview. Explain where DOM
operations belong in JavaScript and where native platform calls are necessary.

## 3. Navigation is a lifecycle problem

Sources: `Pending` and page-load handling in [main.rs](../../src/main.rs),
[macOS navigation](../../src/navigation_macos.rs),
[Windows navigation](../../src/navigation_windows.rs).

Trace one navigation, a queued request, a stale document reply, and a timeout.
Discuss document/generation identity and callback ordering across the engines.
A request timeout stops waiting for a result; it does not interrupt an infinite
JavaScript loop.

## 4. The cross-platform boundary

Source: [screenshot.rs](../../src/screenshot.rs).

Explain how the screenshot implementation differs by OS, why viewport
restoration matters, and the explicit platform limitations. Discuss the cost
of native browser dependencies and helper processes alongside executable size.

## 5. Measure the whole runtime

Sources: [benchmark methodology](../../benchmarks/README.md),
[archived comparison](../README.md#benchmark-chart).

Use the complete process forest and PSS, including Xvfb. Separate controller
size, installed runtime files, startup, navigation, extraction, and screenshot
costs. Highlight engine/workload differences and the cases where another tool
wins; avoid extrapolating one Linux run to all platforms.

## 6. End with a runnable example

Link to the [local form workflow](../README.md#try-the-demo), describe the
synthetic-event and cross-origin iframe limitations, and ask a specific Rust
design question based on your own experience.
