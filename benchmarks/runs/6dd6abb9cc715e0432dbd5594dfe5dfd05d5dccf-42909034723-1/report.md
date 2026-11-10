# Browser comparison

Commit `6dd6abb9cc715e0432dbd5594dfe5dfd05d5dccf` · [workflow run](https://github.com/aliilyas/bruster/actions/runs/42909034723)
Measured 2026-11-10T22:19:07.758956+00:00; 10 sessions per configuration. Values are medians [min–max].
WebKitGTK 2.52.6 · @browserbasehq/stagehand 4.4.0 · @modelcontextprotocol/sdk 1.32.2 · @playwright/mcp 0.0.85 · agent-browser 0.42.0 · biloba 0.23.0 · browse 0.11.3 · cypress 16.3.0 · playwright-core 1.65.0 · puppeteer-core 25.17.0 · rustwright 0.3.0 · rustwright-mcp 0.1.0 · uivision-mcp-bridge 1.7.20 · Google Chrome for Testing 158.0.8127.18 · Headless Shell Google Chrome for Testing 158.0.8127.18 · Node v26.13.0

Ubuntu 24.04.5 LTS · AMD EPYC 9V45 96-Core Processor · 4 visible CPUs · 15.6 GiB RAM · runner image 20261101.360.1

| Metric | Bruster / WebKitGTK | Playwright / Headless Shell | Playwright / full Chrome | Puppeteer / full Chrome | agent-browser / full Chrome | Stagehand / full Chrome | browse.sh / full Chrome | Playwright MCP / full Chrome | Cypress / Chrome test runner | Ui.Vision MCP / browser extension | Rustwright / full Chrome | Rustwright MCP / full Chrome | Biloba / full Chrome |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Launch → first loaded page (ms) | 154.8 [147.0–552.3] | 376.0 [359.8–388.2] | 506.9 [484.7–819.9] | 399.8 [379.3–459.3] | 911.1 [797.2–1000.9] | 815.0 [776.1–1094.8] | 1722.4 [1660.1–2104.8] | 1735.6 [1702.5–1979.0] | 3074.7 [3002.0–12463.9] | 4531.6 [4425.7–5222.7] | 499.0 [478.0–526.6] | 523.2 [493.0–894.0] | 538.2 [515.4–840.2] |
| Startup → ready / blank-page setup (ms) | 72.5 [68.7–330.1] | 359.3 [346.2–372.6] | 477.5 [460.9–798.3] | 373.2 [353.3–384.2] | 882.0 [767.9–977.0] | 771.7 [736.4–1052.6] | 1433.2 [1387.8–1820.4] | 1198.2 [1166.1–1442.6] | 2964.0 [2891.8–12352.3] | 2312.6 [2233.6–2611.1] | 463.5 [424.0–487.8] | 467.9 [414.3–831.4] | 484.6 [447.4–796.9] |
| First navigation after setup (ms) | 82.5 [74.4–222.0] | 15.1 [12.0–17.6] | 25.7 [21.3–40.6] | 23.3 [21.2–104.7] | 23.7 [20.4–37.5] | 42.5 [39.5–54.1] | 285.0 [272.2–327.3] | 536.5 [534.4–538.4] | 110.3 [103.3–137.5] | 2193.8 [2158.2–2949.1] | 38.5 [31.7–53.2] | 59.5 [52.6–78.4] | 57.9 [36.3–76.9] |
| Warm tiny-page navigation (ms) | 5.0 [3.5–9.2] | 7.2 [5.7–14.9] | 13.1 [8.4–31.4] | 12.3 [9.6–24.0] | 16.3 [14.2–28.1] | 18.3 [14.4–35.5] | 283.2 [250.7–338.8] | 535.2 [531.0–555.8] | 43.3 [33.8–69.7] | 798.0 [775.0–965.0] | 20.7 [14.3–304.3] | 21.0 [14.8–42.7] | 20.8 [14.6–38.4] |
| Tiny DOM extraction (ms) | 4.4 [0.6–5.8] | 2.2 [1.7–5.1] | 3.9 [2.4–10.1] | 2.2 [1.0–5.2] | 2.7 [2.4–5.3] | 3.0 [2.3–8.1] | 262.0 [229.7–333.6] | 504.3 [503.1–512.8] | 23.7 [14.0–46.3] | 112.6 [102.0–147.9] | 1.3 [0.9–6.4] | 2.3 [1.8–7.8] | 1.3 [0.9–6.9] |
| Large-page navigation (ms) | 28.5 [19.7–51.5] | 30.8 [16.0–46.8] | 36.3 [20.0–43.9] | 26.4 [24.0–33.2] | 50.0 [44.2–66.7] | 55.2 [37.3–77.8] | 315.9 [285.8–389.7] | 648.9 [636.3–680.0] | 64.9 [50.9–112.3] | 815.0 [784.5–847.8] | 39.0 [36.0–62.0] | 62.9 [58.8–88.1] | 38.7 [35.8–80.5] |
| Large DOM extraction, object return (ms) | 9.7 [3.1–20.2] | 61.5 [42.8–128.0] | 64.2 [44.6–135.7] | 17.7 [11.4–61.6] | 21.3 [17.6–28.9] | 34.0 [29.4–68.5] | 292.8 [272.0–340.8] | 563.1 [551.5–618.4] | 45.6 [39.3–82.7] | 1584.5 [1379.9–1732.2] | 26.4 [23.5–53.3] | 46.2 [41.8–82.4] | 17.4 [14.6–33.0] |
| Large DOM extraction, JSON-string return (ms) | 8.1 [3.4–16.2] | 18.5 [5.6–36.1] | 18.5 [5.4–29.9] | 12.3 [4.9–24.1] | 8.4 [7.2–21.7] | 12.4 [10.6–31.5] | 262.6 [246.2–871.8] | 510.7 [508.7–525.8] | 36.7 [31.6–75.9] | 2046.9 [1807.6–2245.8] | 6.1 [5.5–12.7] | 19.8 [17.4–36.8] | 8.4 [6.4–11.3] |
| Image-page navigation (ms) | 112.8 [108.7–121.0] | 113.9 [112.1–137.6] | 117.3 [114.6–144.5] | 118.7 [115.7–126.7] | 122.4 [118.2–128.9] | 126.0 [122.4–153.6] | 391.3 [370.0–465.9] | 639.0 [636.0–656.7] | 160.0 [153.6–179.1] | 825.5 [810.8–975.9] | 118.9 [117.1–124.4] | 123.2 [119.2–129.8] | 120.1 [117.4–126.9] |
| PNG screenshot (ms) | 12.4 [11.6–13.0] | 31.4 [27.0–40.2] | 37.9 [25.7–53.4] | 55.4 [39.5–77.8] | 48.9 [36.8–66.0] | 68.0 [59.4–88.8] | 321.7 [279.6–376.7] | 30.1 [25.1–38.3] | 240.1 [183.3–283.0] | 1366.3 [1316.5–1411.9] | 19.4 [12.3–35.3] | 24.2 [12.3–34.2] | 48.9 [41.0–70.5] |
| Idle total PSS, including display (MiB) | 221.7 [218.2–224.6] | 310.8 [308.6–311.5] | 473.9 [472.0–476.2] | 417.6 [416.3–419.9] | 487.6 [483.5–494.3] | 545.6 [539.7–548.2] | 663.3 [660.1–665.1] | 543.6 [541.1–545.2] | 1264.0 [1249.1–1278.9] | 758.3 [738.1–761.3] | 496.9 [495.6–499.5] | 501.9 [500.2–504.0] | 534.6 [531.4–537.4] |
| Idle process RSS, excluding display (MiB) | 345.6 [336.1–349.0] | 587.8 [579.5–591.5] | 1137.2 [1126.7–1142.2] | 1062.9 [1050.9–1070.5] | 1563.2 [1541.4–1660.7] | 1520.2 [1419.0–1548.6] | 1547.4 [1535.2–1554.0] | 1251.5 [1232.9–1259.4] | 2269.5 [2256.0–2286.2] | 1858.2 [1763.5–1873.7] | 1536.6 [1518.9–1549.9] | 1452.8 [1435.5–1467.2] | 1601.8 [1587.4–1616.0] |
| Installed runtime files, lower bound (MB) | 428.4 | 486.1 | 638.3 | 655.3 | 495.6 | 654.9 | 684.4 | 675.5 | 1613.0 | 687.9 | 655.2 | 656.3 | 639.1 |
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
  "started_utc": "2026-11-10T21:54:36.030977+00:00",
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
  "chrome": "Google Chrome for Testing 158.0.8127.18",
  "headless_shell": "Google Chrome for Testing 158.0.8127.18",
  "cpu_count": 4,
  "cpu_model": "AMD EPYC 9V45 96-Core Processor",
  "mem_total_kib": 16367524,
  "runner_image": {
    "ImageOS": "ubuntu24",
    "ImageVersion": "20261101.360.1",
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
    "@browserbasehq/stagehand": "4.4.0",
    "@modelcontextprotocol/sdk": "1.32.2",
    "@playwright/mcp": "0.0.85",
    "agent-browser": "0.42.0",
    "biloba": "0.23.0",
    "browse": "0.11.3",
    "cypress": "16.3.0",
    "playwright-core": "1.65.0",
    "puppeteer-core": "25.17.0",
    "rustwright": "0.3.0",
    "rustwright-mcp": "0.1.0",
    "uivision-mcp-bridge": "1.7.20"
  },
  "bruster_bytes": 2010032,
  "bruster_sha256": "13b16fdf27fe7634ed2f5598ec1d0e37596e42e8cb157c2e6aa3fd22955e1042",
  "chrome_sha256": "76bcde21a2f8c9d4fbbf42afbeab011817d000552d093e5f5e89c9b8808f4231",
  "headless_shell_sha256": "41ff61e6e65b8d16b40631f4f094b46ec02f1a0f5375ae477c1d478f1fc2d89d",
  "rounds": 10,
  "iterations": 10,
  "common_extraction_js": "(() => ({\n  title: document.title,\n  elements: Array.from(document.querySelectorAll('h1,h2,h3,p,li,a,input,button,select,textarea'))\n    .filter(e => { const r = e.getBoundingClientRect(); return r.width > 0 && r.height > 0; })\n    .map(e => ({tag: e.tagName.toLowerCase(),\n      name: (e.getAttribute('aria-label') || e.getAttribute('placeholder') || e.textContent || '').trim(),\n      href: e.getAttribute('href'), value: 'value' in e ? e.value : null}))\n}))()",
  "harness_sha256": {
    "bench_compare.py": "20029f2fb633966567e1fc609bf4639d06303dee8062ad95725ca0c514b541f9",
    "bench_competitor_driver.mjs": "091a04fe34ced734f2ba96c013ef2a373b668fe83e2a8e410496dcdcc062d9ca",
    "bench_mcp_driver.mjs": "d970d5f6d40e9055c36c7cbdd8572e17992f9bd245a3ec89d5c57de417f68f48",
    "bench_cypress_driver.mjs": "c7a795bf4149a7275f13ea7cce10e37439ccc7c6ca7b97480b2e631321498c22",
    "bench_cypress.config.cjs": "a0442f2fa87bd3f83ea2ef975e0bb6529edda9c735f8a45c25dfbd3473896c25",
    "bench_cypress.cy.js": "833b3469ecab1bbd443a81c4902899abd0ab1fb8ab58df055d992e1420169bd8",
    "bench_uivision_driver.mjs": "ed9bc9cdc608532af98994e0276b740c8944d72053c1a7c2355257bacc69195a",
    "bench_install_uivision.py": "b44f264df9b9ad32e19276105d6d50533cc2943bb235bdb820ee03db30e10741",
    "bench_rustwright_mcp_driver.mjs": "f78b48216164af7ddca8bad23a0588ad7cecf3a255113add843f425c93451d99",
    "bench_footprint.py": "f6a70626b3cc160bd115e9a22d5677a990cfb45e48f32918259cd591b3b32ac4",
    "bench_tools.py": "4dfe872c7dc61eac092c1a7a402c322a0f4e3a3fc9404faff48658a3fea7ac91",
    "bench_audit.py": "df91d7a203077227c82fc6730033498ea20badaf519c6dd8f6bf10b1c6ae006c"
  },
  "package_lock_sha256": "dae5e4a15cf425863be7cc1b162ea704320e89ba99882e40d5360e946b8178c7",
  "args": {
    "bruster": "/home/runner/work/bruster/bruster/target/release/bruster",
    "node": "/opt/hostedtoolcache/node/26.13.0/x64/bin/node",
    "chrome": "/home/runner/work/_temp/benchmark-browsers/chromium-1254/chrome-linux64/chrome",
    "shell": "/home/runner/work/_temp/benchmark-browsers/chromium_headless_shell-1254/chrome-headless-shell-linux64/chrome-headless-shell",
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
    "version": "10.0.305",
    "source": "https://clients2.google.com/service/update2/crx?response=redirect&prodversion=158.0.8127.18&acceptformat=crx3&x=id%3Dgcbalfbdmfieckjlnblleoemohcganoc%26uc",
    "resolved_url": "https://clients2.googleusercontent.com/crx/blobs/ARGaeZK-C4RaWn7VtRTVx1_lum8D0NXWg9XXG8EO6kSqXockArpAWI84dAAc8SO5UVAVom2MsahblTkVat4B83R3UfySugRNH6fIFim53QqRoz5aReyeWMcbPnu50OMYoO2sAMZSmuWWLy93G3tY7ObpiljLZ5n9oIDSRA/GCBALFBDMFIECKJLNBLLEOEMOHCGANOC_10_0_305_0.crx",
    "crx_sha256": "f168313dd905b33dabaae36c44967aadeb5672b80d5025ac88c6311b90da4447",
    "setup_change": "Public CRX key added to manifest to retain the official ID when unpacked",
    "manifest_sha256": "66c5653607411a181586884a415cb9bd7dc09cdee97c623ff829fbc04ee62edd"
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
      "bytes": 10432674,
      "sha256": "31ac33d42fe019d0fd8c8eae9a9b44876d1b77870c991ca1fc5aec956f6daeaf"
    }
  },
  "finished_utc": "2026-11-10T22:19:07.758956+00:00"
}
```
