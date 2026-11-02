# Browser comparison

Commit `0d18d8a1335bd4da5d480c2d5ca5b5884de406db` · [workflow run](https://github.com/aliilyas/bruster/actions/runs/41539087667)
Measured 2026-11-02T23:10:15.607917+00:00; 10 sessions per configuration. Values are medians [min–max].
WebKitGTK 2.52.6 · @browserbasehq/stagehand 4.3.0 · @modelcontextprotocol/sdk 1.32.2 · @playwright/mcp 0.0.84 · agent-browser 0.41.1 · biloba 0.20.0 · browse 0.11.3 · cypress 16.2.1 · playwright-core 1.64.1 · puppeteer-core 25.16.0 · rustwright 0.3.0 · rustwright-mcp 0.1.0 · uivision-mcp-bridge 1.7.20 · Google Chrome for Testing 156.0.8078.4 · Headless Shell Google Chrome for Testing 156.0.8078.4 · Node v26.13.0

Ubuntu 24.04.5 LTS · AMD EPYC 7763 64-Core Processor · 4 visible CPUs · 15.6 GiB RAM · runner image 20261026.354.1

| Metric | Bruster / WebKitGTK | Playwright / Headless Shell | Playwright / full Chrome | Puppeteer / full Chrome | agent-browser / full Chrome | Stagehand / full Chrome | browse.sh / full Chrome | Playwright MCP / full Chrome | Cypress / Chrome test runner | Ui.Vision MCP / browser extension | Rustwright / full Chrome | Rustwright MCP / full Chrome | Biloba / full Chrome |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Launch → first loaded page (ms) | 232.3 [222.7–481.4] | 612.8 [595.8–616.4] | 847.3 [820.4–862.7] | 642.7 [628.2–650.7] | 907.1 [848.3–940.5] | 1367.4 [1336.7–1569.5] | 2887.2 [2834.3–2996.1] | 2217.4 [2204.6–2243.0] | 5553.9 [5496.7–12918.8] | 5059.6 [4943.9–5216.9] | 870.5 [829.8–913.6] | 918.9 [887.7–948.5] | 929.3 [874.4–983.7] |
| Startup → ready / blank-page setup (ms) | 108.3 [103.8–239.6] | 592.8 [576.6–594.9] | 796.6 [772.6–816.7] | 607.3 [591.7–613.9] | 824.2 [765.5–849.7] | 1310.3 [1274.9–1499.2] | 2389.5 [2336.2–2458.6] | 1659.4 [1648.0–1680.5] | 5378.3 [5297.2–12746.2] | 2426.6 [2328.0–2619.4] | 809.2 [773.6–855.7] | 826.3 [789.9–856.3] | 835.4 [791.5–893.2] |
| First navigation after setup (ms) | 125.0 [113.1–241.1] | 19.8 [17.5–21.8] | 48.7 [40.7–72.1] | 36.4 [32.8–40.1] | 83.1 [74.2–108.4] | 58.2 [48.6–70.0] | 499.1 [493.7–537.5] | 558.1 [555.1–563.0] | 178.0 [170.8–299.6] | 2623.3 [2459.4–2691.6] | 59.0 [49.5–70.7] | 92.1 [75.9–109.6] | 89.5 [67.8–130.9] |
| Warm tiny-page navigation (ms) | 7.4 [4.9–13.8] | 12.5 [9.9–19.0] | 22.0 [16.1–39.8] | 21.4 [17.7–35.9] | 43.2 [24.6–100.7] | 37.0 [31.4–54.7] | 484.5 [465.2–525.5] | 555.9 [550.4–571.9] | 68.2 [58.1–95.4] | 810.6 [791.2–873.4] | 38.2 [26.1–53.2] | 35.4 [30.9–63.7] | 37.2 [26.1–80.0] |
| Tiny DOM extraction (ms) | 5.9 [1.0–9.3] | 3.5 [2.7–7.8] | 8.8 [3.7–22.6] | 7.2 [1.8–12.1] | 5.8 [3.7–22.1] | 6.2 [4.7–11.6] | 442.7 [415.7–487.0] | 507.2 [506.1–516.4] | 37.0 [31.5–62.5] | 117.6 [104.4–172.0] | 1.6 [1.2–10.1] | 3.8 [3.2–11.3] | 2.0 [1.2–8.5] |
| Large-page navigation (ms) | 57.3 [51.6–72.8] | 37.1 [23.5–40.2] | 45.4 [29.8–62.2] | 42.2 [36.7–50.2] | 93.4 [83.5–117.9] | 88.0 [55.8–104.4] | 525.8 [509.5–558.7] | 758.5 [749.3–781.4] | 102.1 [79.8–143.1] | 827.1 [812.2–852.8] | 67.8 [63.3–85.2] | 108.5 [98.5–117.9] | 67.7 [61.5–76.8] |
| Large DOM extraction, object return (ms) | 9.5 [5.8–26.5] | 108.5 [81.7–159.3] | 116.6 [84.9–176.0] | 34.7 [19.7–62.7] | 36.8 [28.5–46.5] | 59.1 [48.2–104.4] | 493.4 [474.7–516.7] | 602.5 [593.6–671.8] | 66.4 [55.7–119.4] | 1468.4 [1289.3–1615.9] | 41.6 [36.7–61.1] | 76.4 [68.8–95.6] | 29.2 [26.6–35.6] |
| Large DOM extraction, JSON-string return (ms) | 20.1 [6.2–26.2] | 22.4 [9.2–39.5] | 11.7 [9.0–43.7] | 26.0 [9.8–48.0] | 15.2 [12.5–28.5] | 22.1 [19.8–61.0] | 457.3 [427.9–490.4] | 520.3 [518.4–535.4] | 55.1 [47.7–90.5] | 1898.6 [1705.2–2240.0] | 11.6 [10.0–14.5] | 36.7 [33.0–52.8] | 15.7 [12.9–21.3] |
| Image-page navigation (ms) | 116.1 [112.5–127.6] | 121.4 [117.9–137.9] | 125.5 [122.7–144.3] | 130.1 [126.3–137.5] | 135.2 [131.5–142.6] | 137.9 [133.0–176.2] | 586.0 [569.3–629.2] | 660.9 [656.7–681.0] | 202.1 [192.8–215.8] | 833.3 [815.3–974.4] | 132.6 [127.8–148.9] | 134.4 [132.3–144.6] | 131.0 [125.6–141.7] |
| PNG screenshot (ms) | 40.6 [39.4–44.0] | 47.7 [43.3–60.7] | 49.8 [46.0–76.2] | 66.6 [54.4–95.9] | 66.5 [55.8–101.5] | 96.4 [89.3–132.4] | 531.1 [489.1–573.2] | 44.1 [40.6–51.5] | 369.5 [324.5–440.1] | 1386.5 [1325.0–1446.7] | 37.7 [20.3–51.2] | 30.7 [22.1–50.8] | 66.5 [61.8–105.9] |
| Idle total PSS, including display (MiB) | 220.1 [216.6–223.7] | 324.9 [322.6–326.5] | 506.5 [503.7–508.5] | 419.0 [415.2–422.1] | 516.7 [511.7–526.0] | 607.4 [604.8–609.0] | 696.7 [695.1–700.2] | 565.0 [563.3–571.0] | 1325.6 [1319.9–1339.5] | 834.5 [812.2–843.1] | 526.7 [517.4–527.6] | 531.4 [527.6–534.2] | 588.4 [586.0–591.2] |
| Idle process RSS, excluding display (MiB) | 344.1 [335.5–347.2] | 597.9 [592.2–599.8] | 1172.5 [1160.0–1176.3] | 1063.0 [1043.7–1069.6] | 1591.1 [1571.6–1687.0] | 1490.4 [1474.4–1503.3] | 1566.5 [1555.0–1583.6] | 1278.0 [1270.9–1287.1] | 2350.8 [2341.7–2372.5] | 1921.7 [1809.7–1934.1] | 1552.7 [1470.9–1567.8] | 1470.8 [1446.4–1478.8] | 1738.7 [1721.3–1749.3] |
| Installed runtime files, lower bound (MB) | 427.9 | 475.5 | 630.8 | 644.7 | 483.2 | 641.7 | 672.1 | 666.3 | 1660.4 | 675.5 | 644.8 | 644.3 | 628.9 |
| Sessions with failures (including cleanup) | 0/10 | 10/10 | 10/10 | 0/10 | 0/10 | 0/10 | 10/10 | 10/10 | 0/10 | 0/10 | 0/10 | 0/10 | 0/10 |

Ten sessions per configuration by default, with rotating order and fresh browser profiles. Values are medians [observed minimum–maximum], not confidence intervals. Startup and first navigation have one sample per session; repeated-operation timings pool all iterations; memory uses the median of three idle readings per session. Startup includes adapter/daemon/server initialization and blank-page/viewport setup. The combined launch-to-first-page measurement includes both setup and the first navigation. Xvfb is already running: its startup time is excluded, but its memory is included. 1280×800 viewport; localhost fixtures; no-store HTTP responses; navigation waits for load. OS filesystem caches are not flushed. Identical extraction JavaScript and cross-tool result hashes. Timings include controller round trips and per-command CLI launches. These deterministic workloads do not measure LLM inference or token efficiency. Memory covers the complete owned process forest (including detached daemons and helpers), plus Xvfb for Bruster. PSS apportions shared pages; summed RSS double-counts them. Memory is small-page idle usage, not peak usage. Native snapshots have different semantics and are retained in the raw artifacts rather than ranked as equal work. MB = 1,000,000 bytes; MiB = 1,048,576 bytes. Installed-file inventories are lower bounds including browser/engine, linked libraries, observed mapped files and Node where required; unobserved OS resources may add more. GitHub-hosted runner hardware and OS packages can change: compare the configurations within a run and inspect provenance before interpreting trends.

## Fault probes and cleanup

- Bruster / WebKitGTK: fault probes {}; shutdown/cleanup {}; successful 100 ms recovery retries: 0.
- Playwright / Headless Shell: fault probes {"recovery_after_navigation_error": 10}; shutdown/cleanup {}; successful 100 ms recovery retries: 10.
- Playwright / full Chrome: fault probes {"recovery_after_navigation_error": 10}; shutdown/cleanup {}; successful 100 ms recovery retries: 10.
- Puppeteer / full Chrome: fault probes {}; shutdown/cleanup {}; successful 100 ms recovery retries: 0.
- agent-browser / full Chrome: fault probes {}; shutdown/cleanup {}; successful 100 ms recovery retries: 0.
- Stagehand / full Chrome: fault probes {}; shutdown/cleanup {}; successful 100 ms recovery retries: 0.
- browse.sh / full Chrome: fault probes {"connection_refused": 10}; shutdown/cleanup {}; successful 100 ms recovery retries: 0.
- Playwright MCP / full Chrome: fault probes {"recovery_after_navigation_error": 10}; shutdown/cleanup {}; successful 100 ms recovery retries: 10.
- Cypress / Chrome test runner: fault probes {}; shutdown/cleanup {}; successful 100 ms recovery retries: 0.
- Ui.Vision MCP / browser extension: fault probes {}; shutdown/cleanup {}; successful 100 ms recovery retries: 0.
- Rustwright / full Chrome: fault probes {}; shutdown/cleanup {}; successful 100 ms recovery retries: 0.
- Rustwright MCP / full Chrome: fault probes {}; shutdown/cleanup {}; successful 100 ms recovery retries: 0.
- Biloba / full Chrome: fault probes {}; shutdown/cleanup {}; successful 100 ms recovery retries: 0.

## Hacker News competitor coverage

[Source discussion](https://news.ycombinator.com/item?id=49756671) · reviewed 2026-11-01

The linked story and its complete public comment tree, including replies, plus user-requested Rustwright, Rustwright MCP and Biloba. Additional stories are recorded separately from comments on the original thread. This is not a search of every Hacker News submission.

| Tool / repository | Coverage | Notes |
|---|---|---|
| [Bruster / WebKitGTK](https://github.com/aliilyas/bruster)  | Measured in this run | Native JSONL; system WebKitGTK and Xvfb. Reference implementation. |
| [Playwright / Headless Shell](https://github.com/microsoft/playwright) [HN comment](https://news.ycombinator.com/item?id=49756672) [HN comment](https://news.ycombinator.com/item?id=49767485) | Measured in this run | Public Playwright API; separate Headless Shell configuration. |
| [Playwright / full Chrome](https://github.com/microsoft/playwright) [HN comment](https://news.ycombinator.com/item?id=49756672) [HN comment](https://news.ycombinator.com/item?id=49767485) | Measured in this run | Public Playwright API. |
| [Puppeteer / full Chrome](https://github.com/puppeteer/puppeteer)  | Measured in this run | Existing baseline; not named in the linked HN thread. |
| [agent-browser / full Chrome](https://github.com/vercel-labs/agent-browser) [HN comment](https://news.ycombinator.com/item?id=49763636) [HN comment](https://news.ycombinator.com/item?id=49784241) | Measured in this run | Native CLI and persistent daemon; per-command CLI overhead included. |
| [Stagehand / full Chrome](https://github.com/browserbase/stagehand) [HN comment](https://news.ycombinator.com/item?id=49756672) | Measured in this run | Local v4 SDK and bundled extension; deterministic Page APIs. No LLM calls, act/extract inference, cloud caching, or token-efficiency claims. |
| [browse.sh / full Chrome](https://github.com/browserbase/stagehand/tree/main/packages/cli) [HN comment](https://news.ycombinator.com/item?id=49784241) | Measured in this run | Local browse CLI, Stagehand extension and persistent daemon; per-command Node CLI overhead included. Same monorepo as Stagehand. |
| [Playwright MCP / full Chrome](https://github.com/microsoft/playwright-mcp) [HN comment](https://news.ycombinator.com/item?id=49756672) | Measured in this run | Actual stdio MCP server and tool calls, including default response snapshots and client/server overhead; navigation explicitly waits for load. |
| [SleepyHollow / Apple WebKit](https://github.com/bensyverson/sleepyhollow) [HN comment](https://news.ycombinator.com/item?id=49762455) [HN comment](https://news.ycombinator.com/item?id=49767052) | macos-timing | Separate same-Mac Bruster/SleepyHollow timing job and artifact. Requires macOS 12+ and WebKit.framework. No Linux/PSS or runtime-footprint estimates; native validation requires the macOS workflow. |
| [Cypress / Chrome test runner](https://github.com/cypress-io/cypress) [HN comment](https://news.ycombinator.com/item?id=49766482) [HN comment](https://news.ycombinator.com/item?id=49773778) | Measured in this run | Real Cypress CLI/spec runner, application iframe, proxy and task IPC; one command per test with test isolation and retries disabled. Runner, bundled Electron runtime and owned Xvfb are counted. Native snapshot is unavailable; shared DOM extraction is measured. |
| [Ui.Vision MCP / browser extension](https://github.com/A9T9/RPA/tree/master/mcp) [HN comment](https://news.ycombinator.com/item?id=49765724) | Measured in this run | Official browser extension and real MCP bridge in an isolated headless Chrome profile with an open panel. Playwright provisions/closes the browser; measured operations use MCP. Macro-log extraction is chunked to respect transport limits; all calls and default response snapshots are counted. Native snapshots can truncate at 60,000 characters; shared extraction is complete. |
| [Rustwright / full Chrome](https://github.com/Skyvern-AI/rustwright) [HN story](https://news.ycombinator.com/item?id=48923788) [HN story](https://news.ycombinator.com/item?id=48932230) [HN story](https://news.ycombinator.com/item?id=49319583) | Measured in this run | User-requested addition, verified against separate HN stories identifying Skyvern-AI/rustwright. Public Node SDK over its in-process Rust CDP engine. The experimental Node API lacks a viewport setter: a CDP connection provisions the viewport at startup and remains idle in memory scope. All workload operations use the SDK. Native snapshot is unavailable in the Node SDK. |
| [Rustwright MCP / full Chrome](https://github.com/Skyvern-AI/rustwright/tree/main/mcp) [HN story](https://news.ycombinator.com/item?id=48923788) [HN story](https://news.ycombinator.com/item?id=48932230) [HN story](https://news.ycombinator.com/item?id=49319583) | Measured in this run | User confirmed that 'Rust MCP' means Rustwright MCP. Canonical native Rust stdio MCP server, launched directly from its official npm binary package. MCP client/server and automatic snapshots are counted; navigation explicitly waits for load. Native snapshots can truncate; shared extraction is complete. Distinct from the deprecated Python server and luka-loehr/browser-rs. |
| [Biloba / full Chrome](https://github.com/onsi/biloba) [HN story](https://news.ycombinator.com/item?id=49699819) | Measured in this run | User-requested addition, verified against its separate Show HN story. Public TypeScript SDK and real bilobad Go daemon over chromedp; a fresh local browser and session per round. Measures serial browser operations, including daemon transport; no Vitest/Ginkgo scheduling or parallel-suite claims. Native accessibility outlines can truncate; shared extraction is complete. |

## Provenance

```json
{
  "started_utc": "2026-11-02T22:41:20.692355+00:00",
  "platform": "Linux-7.0.0-1017-azure-x86_64-with-glibc2.39",
  "os": {
    "NAME": "Ubuntu",
    "ID": "ubuntu",
    "PRETTY_NAME": "Ubuntu 24.04.5 LTS",
    "VERSION_ID": "24.04",
    "VERSION": "24.04.5 LTS (Noble Numbat)",
    "VERSION_CODENAME": "noble",
    "ID_LIKE": "debian",
    "HOME_URL": "https://www.ubuntu.com/",
    "SUPPORT_URL": "https://help.ubuntu.com/",
    "BUG_REPORT_URL": "https://bugs.launchpad.net/ubuntu/",
    "PRIVACY_POLICY_URL": "https://www.ubuntu.com/legal/terms-and-policies/privacy-policy",
    "UBUNTU_CODENAME": "noble",
    "LOGO": "ubuntu-logo"
  },
  "node": "v26.13.0",
  "chrome": "Google Chrome for Testing 156.0.8078.4",
  "headless_shell": "Google Chrome for Testing 156.0.8078.4",
  "cpu_count": 4,
  "cpu_model": "AMD EPYC 7763 64-Core Processor",
  "mem_total_kib": 16371756,
  "runner_image": {
    "ImageOS": "ubuntu24",
    "ImageVersion": "20261026.354.1",
    "RUNNER_ARCH": "X64"
  },
  "session_environment": {
    "display_set": true,
    "session_bus_address_set": false,
    "XDG_CURRENT_DESKTOP": null,
    "GTK_USE_PORTAL": null,
    "GTK_MODULES": null,
    "NO_AT_BRIDGE": null,
    "BRUSTER_USE_SESSION_BUS": null
  },
  "rustc": "rustc 1.99.1 (58cf8f9c3 2026-10-13)",
  "gtk": "3.24.41",
  "webkitgtk": "2.52.6",
  "tools": [
    "bruster",
    "playwright-shell",
    "playwright",
    "puppeteer",
    "agent-browser",
    "stagehand",
    "browse",
    "playwright-mcp",
    "cypress",
    "uivision",
    "rustwright",
    "rustwright-mcp",
    "biloba"
  ],
  "competitors": {
    "source": "https://news.ycombinator.com/item?id=49756671",
    "reviewed": "2026-11-01",
    "scope": "The linked story and its complete public comment tree, including replies, plus user-requested Rustwright, Rustwright MCP and Biloba. Additional stories are recorded separately from comments on the original thread. This is not a search of every Hacker News submission.",
    "tools": [
      {
        "id": "bruster",
        "label": "Bruster / WebKitGTK",
        "github": "https://github.com/aliilyas/bruster",
        "status": "linux",
        "notes": "Native JSONL; system WebKitGTK and Xvfb. Reference implementation."
      },
      {
        "id": "playwright-shell",
        "label": "Playwright / Headless Shell",
        "github": "https://github.com/microsoft/playwright",
        "comments": [
          49756672,
          49767485
        ],
        "package": "playwright-core",
        "status": "linux",
        "notes": "Public Playwright API; separate Headless Shell configuration."
      },
      {
        "id": "playwright",
        "label": "Playwright / full Chrome",
        "github": "https://github.com/microsoft/playwright",
        "comments": [
          49756672,
          49767485
        ],
        "package": "playwright-core",
        "status": "linux",
        "notes": "Public Playwright API."
      },
      {
        "id": "puppeteer",
        "label": "Puppeteer / full Chrome",
        "github": "https://github.com/puppeteer/puppeteer",
        "package": "puppeteer-core",
        "status": "linux",
        "notes": "Existing baseline; not named in the linked HN thread."
      },
      {
        "id": "agent-browser",
        "label": "agent-browser / full Chrome",
        "github": "https://github.com/vercel-labs/agent-browser",
        "comments": [
          49763636,
          49784241
        ],
        "package": "agent-browser",
        "status": "linux",
        "notes": "Native CLI and persistent daemon; per-command CLI overhead included."
      },
      {
        "id": "stagehand",
        "label": "Stagehand / full Chrome",
        "github": "https://github.com/browserbase/stagehand",
        "comments": [
          49756672
        ],
        "package": "@browserbasehq/stagehand",
        "status": "linux",
        "notes": "Local v4 SDK and bundled extension; deterministic Page APIs. No LLM calls, act/extract inference, cloud caching, or token-efficiency claims."
      },
      {
        "id": "browse",
        "label": "browse.sh / full Chrome",
        "github": "https://github.com/browserbase/stagehand/tree/main/packages/cli",
        "comments": [
          49784241
        ],
        "package": "browse",
        "status": "linux",
        "notes": "Local browse CLI, Stagehand extension and persistent daemon; per-command Node CLI overhead included. Same monorepo as Stagehand."
      },
      {
        "id": "playwright-mcp",
        "label": "Playwright MCP / full Chrome",
        "github": "https://github.com/microsoft/playwright-mcp",
        "comments": [
          49756672
        ],
        "package": "@playwright/mcp",
        "adapter_packages": [
          "@modelcontextprotocol/sdk"
        ],
        "status": "linux",
        "notes": "Actual stdio MCP server and tool calls, including default response snapshots and client/server overhead; navigation explicitly waits for load."
      },
      {
        "id": "sleepyhollow",
        "label": "SleepyHollow / Apple WebKit",
        "github": "https://github.com/bensyverson/sleepyhollow",
        "comments": [
          49762455,
          49767052
        ],
        "status": "macos-timing",
        "notes": "Separate same-Mac Bruster/SleepyHollow timing job and artifact. Requires macOS 12+ and WebKit.framework. No Linux/PSS or runtime-footprint estimates; native validation requires the macOS workflow."
      },
      {
        "id": "cypress",
        "label": "Cypress / Chrome test runner",
        "github": "https://github.com/cypress-io/cypress",
        "comments": [
          49766482,
          49773778
        ],
        "package": "cypress",
        "status": "linux",
        "notes": "Real Cypress CLI/spec runner, application iframe, proxy and task IPC; one command per test with test isolation and retries disabled. Runner, bundled Electron runtime and owned Xvfb are counted. Native snapshot is unavailable; shared DOM extraction is measured."
      },
      {
        "id": "uivision",
        "label": "Ui.Vision MCP / browser extension",
        "github": "https://github.com/A9T9/RPA",
        "implementation": "https://github.com/A9T9/RPA/tree/master/mcp",
        "comments": [
          49765724
        ],
        "package": "uivision-mcp-bridge",
        "adapter_packages": [
          "playwright-core",
          "@modelcontextprotocol/sdk"
        ],
        "status": "linux",
        "notes": "Official browser extension and real MCP bridge in an isolated headless Chrome profile with an open panel. Playwright provisions/closes the browser; measured operations use MCP. Macro-log extraction is chunked to respect transport limits; all calls and default response snapshots are counted. Native snapshots can truncate at 60,000 characters; shared extraction is complete."
      },
      {
        "id": "rustwright",
        "label": "Rustwright / full Chrome",
        "github": "https://github.com/Skyvern-AI/rustwright",
        "stories": [
          48923788,
          48932230,
          49319583
        ],
        "package": "rustwright",
        "status": "linux",
        "notes": "User-requested addition, verified against separate HN stories identifying Skyvern-AI/rustwright. Public Node SDK over its in-process Rust CDP engine. The experimental Node API lacks a viewport setter: a CDP connection provisions the viewport at startup and remains idle in memory scope. All workload operations use the SDK. Native snapshot is unavailable in the Node SDK."
      },
      {
        "id": "rustwright-mcp",
        "label": "Rustwright MCP / full Chrome",
        "github": "https://github.com/Skyvern-AI/rustwright",
        "implementation": "https://github.com/Skyvern-AI/rustwright/tree/main/mcp",
        "stories": [
          48923788,
          48932230,
          49319583
        ],
        "package": "rustwright-mcp",
        "adapter_packages": [
          "@modelcontextprotocol/sdk"
        ],
        "status": "linux",
        "notes": "User confirmed that 'Rust MCP' means Rustwright MCP. Canonical native Rust stdio MCP server, launched directly from its official npm binary package. MCP client/server and automatic snapshots are counted; navigation explicitly waits for load. Native snapshots can truncate; shared extraction is complete. Distinct from the deprecated Python server and luka-loehr/browser-rs."
      },
      {
        "id": "biloba",
        "label": "Biloba / full Chrome",
        "github": "https://github.com/onsi/biloba",
        "stories": [
          49699819
        ],
        "package": "biloba",
        "status": "linux",
        "notes": "User-requested addition, verified against its separate Show HN story. Public TypeScript SDK and real bilobad Go daemon over chromedp; a fresh local browser and session per round. Measures serial browser operations, including daemon transport; no Vitest/Ginkgo scheduling or parallel-suite claims. Native accessibility outlines can truncate; shared extraction is complete."
      }
    ],
    "related_mentions": [
      {
        "name": "Jev / TypeSafe",
        "comments": [
          49768496
        ],
        "github": "https://github.com/browserbase/stagehand/pull/2952",
        "notes": "Typed decision model integrated with Stagehand, not a browser runtime. The verified GitHub link is the integration PR; no standalone Jev browser repository was identified. Requires a model-driven accuracy/cost evaluation."
      },
      {
        "name": "Browserbase",
        "comments": [
          49763632,
          49757218
        ],
        "github": "https://github.com/browserbase/sdk-node",
        "notes": "Hosted browser service; this is its client SDK, not the hosted browser source. Cloud/network latency needs a separate comparison."
      },
      {
        "name": "Codex",
        "comments": [
          49756672,
          49757944
        ],
        "github": "https://github.com/openai/codex",
        "notes": "Coding-agent harness using browser tools, not a browser backend."
      },
      {
        "name": "Claude Code",
        "comments": [
          49756672,
          49757944
        ],
        "github": "https://github.com/anthropics/claude-code",
        "notes": "Coding-agent product repository, not an open-source browser backend."
      },
      {
        "name": "Deep Agents",
        "comments": [
          49757944,
          49757129
        ],
        "github": "https://github.com/langchain-ai/deepagents",
        "notes": "Agent harness; browser tools and model must be specified for an end-to-end task evaluation."
      },
      {
        "name": "Mastra",
        "comments": [
          49757944
        ],
        "github": "https://github.com/mastra-ai/mastra",
        "notes": "Agent framework, not a browser runtime."
      },
      {
        "name": "Eve",
        "comments": [
          49757944,
          49757129
        ],
        "github": "https://github.com/vercel/eve",
        "notes": "Vercel agent framework, identified through Stagehand's Eve integration and the eve npm package repository. Uses a browser integration rather than implementing a browser."
      },
      {
        "name": "Fx",
        "comments": [
          49757129
        ],
        "github": "https://github.com/vercel-labs/fx",
        "notes": "Coding agent, identified through Stagehand's fx integration and fx.sh's repository link. Uses the Stagehand MCP integration for browser tasks."
      },
      {
        "name": "Astra computer use",
        "comments": [
          49756970,
          49757217
        ],
        "github": null,
        "notes": "Computer-use/model alternative, with no repository linked in the thread. No authoritative standalone browser repository identified; unrelated projects with the same name are not substituted. Requires a specified model and computer-use environment."
      }
    ]
  },
  "competitors_sha256": "a7ea594c9373720b11a51e597df3e96755af781d64be84256edbe9aa1eca91cc",
  "packages": {
    "@browserbasehq/stagehand": "4.3.0",
    "@modelcontextprotocol/sdk": "1.32.2",
    "@playwright/mcp": "0.0.84",
    "agent-browser": "0.41.1",
    "biloba": "0.20.0",
    "browse": "0.11.3",
    "cypress": "16.2.1",
    "playwright-core": "1.64.1",
    "puppeteer-core": "25.16.0",
    "rustwright": "0.3.0",
    "rustwright-mcp": "0.1.0",
    "uivision-mcp-bridge": "1.7.20"
  },
  "bruster_bytes": 1471808,
  "bruster_sha256": "0d27da883d9a03e4ca55e6397075e204920a14edac3da74c7ecd01069c22df44",
  "chrome_sha256": "377a9fc07b495c3b8d0ab8ec1fdfd153641759f9756fea34d8dfce4de82f5025",
  "headless_shell_sha256": "4fa61f0ba0b4f89b7bec242c32ca16d3bccf69dbfef0651924a9ba8fede5f9d6",
  "rounds": 10,
  "iterations": 10,
  "common_extraction_js": "(() => ({\n  title: document.title,\n  elements: Array.from(document.querySelectorAll('h1,h2,h3,p,li,a,input,button,select,textarea'))\n    .filter(e => { const r = e.getBoundingClientRect(); return r.width > 0 && r.height > 0; })\n    .map(e => ({tag: e.tagName.toLowerCase(),\n      name: (e.getAttribute('aria-label') || e.getAttribute('placeholder') || e.textContent || '').trim(),\n      href: e.getAttribute('href'), value: 'value' in e ? e.value : null}))\n}))()",
  "harness_sha256": {
    "bench_compare.py": "22bd6f5681b8cbb78fea5fd1009122edcf3570fe6869461cf672e3499b309910",
    "bench_competitor_driver.mjs": "091a04fe34ced734f2ba96c013ef2a373b668fe83e2a8e410496dcdcc062d9ca",
    "bench_mcp_driver.mjs": "d970d5f6d40e9055c36c7cbdd8572e17992f9bd245a3ec89d5c57de417f68f48",
    "bench_cypress_driver.mjs": "c7a795bf4149a7275f13ea7cce10e37439ccc7c6ca7b97480b2e631321498c22",
    "bench_cypress.config.cjs": "a0442f2fa87bd3f83ea2ef975e0bb6529edda9c735f8a45c25dfbd3473896c25",
    "bench_cypress.cy.js": "833b3469ecab1bbd443a81c4902899abd0ab1fb8ab58df055d992e1420169bd8",
    "bench_uivision_driver.mjs": "4a83601cbaf55df9b0b6d3725a2b351f81f04d6392acc90486216b8b2b07c0f1",
    "bench_install_uivision.py": "b44f264df9b9ad32e19276105d6d50533cc2943bb235bdb820ee03db30e10741",
    "bench_rustwright_mcp_driver.mjs": "f78b48216164af7ddca8bad23a0588ad7cecf3a255113add843f425c93451d99",
    "bench_footprint.py": "f6a70626b3cc160bd115e9a22d5677a990cfb45e48f32918259cd591b3b32ac4",
    "bench_tools.py": "4dfe872c7dc61eac092c1a7a402c322a0f4e3a3fc9404faff48658a3fea7ac91",
    "bench_audit.py": "df91d7a203077227c82fc6730033498ea20badaf519c6dd8f6bf10b1c6ae006c"
  },
  "package_lock_sha256": "72ff2dea7e56c11a30c6f5d1ed8999d0fe6f9c8361ada2ab305ae9e707468456",
  "args": {
    "bruster": "/home/runner/work/bruster/bruster/target/release/bruster",
    "node": "/opt/hostedtoolcache/node/26.13.0/x64/bin/node",
    "chrome": "/home/runner/work/_temp/benchmark-browsers/chromium-1248/chrome-linux64/chrome",
    "shell": "/home/runner/work/_temp/benchmark-browsers/chromium_headless_shell-1248/chrome-headless-shell-linux64/chrome-headless-shell",
    "deps": "/home/runner/work/_temp/benchmark-deps",
    "output": "/home/runner/work/_temp/benchmark-results",
    "rounds": 10,
    "iterations": 10,
    "tools": [
      "bruster",
      "playwright-shell",
      "playwright",
      "puppeteer",
      "agent-browser",
      "stagehand",
      "browse",
      "playwright-mcp",
      "cypress",
      "uivision",
      "rustwright",
      "rustwright-mcp",
      "biloba"
    ]
  },
  "uivision_extension": {
    "extension_id": "gcbalfbdmfieckjlnblleoemohcganoc",
    "version": "10.0.303",
    "source": "https://clients2.google.com/service/update2/crx?response=redirect&prodversion=156.0.8078.4&acceptformat=crx3&x=id%3Dgcbalfbdmfieckjlnblleoemohcganoc%26uc",
    "resolved_url": "https://clients2.googleusercontent.com/crx/blobs/ARGaeZLbm26tOXxwaO7G9nHFStm9MCxhn2FdYuO1H9c5BC5zaaCuLFzYiiPbzChvifYhssoWnxLzKpBKUmWpZw4ITUki7EKrdnZXKf0OKVsU-UHxojdC1dXXYpAJq5VVVz_IAMZSmuWgdOGcctPNE4bJ8DmNkgqogycQ8g/GCBALFBDMFIECKJLNBLLEOEMOHCGANOC_10_0_303_0.crx",
    "crx_sha256": "cabd81754af33b574d44a4908e061c67fd04e6ab6509fcc51af95b273fb76f9d",
    "setup_change": "Public CRX key added to manifest to retain the official ID when unpacked",
    "manifest_sha256": "af925e1f2298e07b96e9783d76540fafcfdd0738fbdf2f7cc1055075e48d4c6e"
  },
  "native_artifacts": {
    "rustwright": {
      "path": "node_modules/rustwright/rustwright.linux-x64-gnu.node",
      "bytes": 5585072,
      "sha256": "26ea8439f6f168fa7e1a68eee970705e1583eda9debf011b8f58bc1c16538131"
    },
    "rustwright-mcp": {
      "path": "node_modules/@skyvernai/rustwright-mcp-linux-x64-gnu/bin/rustwright-mcp",
      "bytes": 10090120,
      "sha256": "552f458fe2655807c624f560df6c9643c02a61dda21c00e179c44581af31676d"
    },
    "biloba": {
      "path": "node_modules/biloba-linux-x64/bin/bilobad",
      "bytes": 10600610,
      "sha256": "e0df92b2d1c96b8631541627fbce522ca41f2b538d60b9aaecc1ac0305f65590"
    }
  },
  "finished_utc": "2026-11-02T23:10:15.607917+00:00"
}
```
