# Hacker News submission notes

Submit manually at <https://news.ycombinator.com/submit>.

[HN guidelines](https://news.ycombinator.com/newsguidelines.html) explicitly
require human-written text and prohibit automated posting. These are facts to
consult while writing your own title and introduction, not text to paste as a
submission or comment. A Show HN title begins with `Show HN:`.

## Links

- Submit the repository: https://github.com/aliilyas/bruster
- Runnable downloads: https://github.com/aliilyas/bruster/releases
- Demo: https://github.com/aliilyas/bruster/tree/main/launch
- Benchmarks: https://aliilyas.github.io/bruster/benchmarks/

## Verified facts

- Rust controller, JSON lines on stdio, optional stdio MCP mode.
- `wry` hosts WKWebView on macOS, WebKitGTK on Linux, and WebView2 on Windows.
- No Node.js runtime required. Native browser runtimes are separate dependencies.
- WebView2 is Chromium-based; a blanket “no Chromium” claim would be inaccurate.
- Release archives cover macOS and Linux x86_64/ARM64, plus Windows x86_64.
- Navigation, snapshots, forms, screenshots, tabs, persistent profiles, page-level logs.
- MIT license, public source, one-liner installer for macOS/Linux.
- Known limits include synthetic DOM events and no cross-origin iframe access.
- The benchmark chart is a particular Linux run, with total-process memory
  including Xvfb, and includes workloads where Bruster loses to other configurations.
- The demo is scripted MCP automation with real screenshots, held five seconds
  per step. It is not a live LLM session or performance measurement.

## Personal context to supply

Explain the actual problem that led you to build Bruster, why you chose native
webviews, what tradeoff surprised you most, and which kind of feedback would
help. Be available to answer questions after submitting. Check for an existing
submission before making another one.
