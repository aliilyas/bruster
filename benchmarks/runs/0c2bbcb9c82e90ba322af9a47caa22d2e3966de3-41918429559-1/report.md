# Browser comparison

Commit `0c2bbcb9c82e90ba322af9a47caa22d2e3966de3` · [workflow run](https://github.com/aliilyas/bruster/actions/runs/41918429559)
Measured 2026-11-04T22:10:46.116110+00:00; 10 sessions per configuration. Values are medians [min–max].
WebKitGTK 2.52.6 · @browserbasehq/stagehand 4.4.0 · @modelcontextprotocol/sdk 1.32.2 · @playwright/mcp 0.0.84 · agent-browser 0.41.2 · biloba 0.22.0 · browse 0.11.3 · cypress 16.2.1 · playwright-core 1.64.1 · puppeteer-core 25.16.0 · rustwright 0.3.0 · rustwright-mcp 0.1.0 · uivision-mcp-bridge 1.7.20 · Google Chrome for Testing 156.0.8078.4 · Headless Shell Google Chrome for Testing 156.0.8078.4 · Node v26.13.0

Ubuntu 24.04.5 LTS · INTEL(R) XEON(R) PLATINUM 8573C · 4 visible CPUs · 15.6 GiB RAM · runner image 20261026.354.1

| Metric | Bruster / WebKitGTK | Playwright / Headless Shell | Playwright / full Chrome | Puppeteer / full Chrome | agent-browser / full Chrome | Stagehand / full Chrome | browse.sh / full Chrome | Playwright MCP / full Chrome | Cypress / Chrome test runner | Ui.Vision MCP / browser extension | Rustwright / full Chrome | Rustwright MCP / full Chrome | Biloba / full Chrome |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Launch → first loaded page (ms) | 201.9 [189.5–386.4] | 515.6 [506.5–529.2] | 715.5 [698.3–744.7] | 537.7 [526.2–571.8] | 1051.7 [960.9–1173.2] | 1168.9 [1132.9–1183.1] | 2493.0 [2458.0–2539.5] | 2040.0 [2014.8–2075.3] | 4777.1 [4705.1–10475.0] | 4611.4 [2996.4–5115.1] | 755.2 [715.6–787.6] | 784.7 [744.8–833.9] | 814.1 [798.9–890.2] |
| Startup → ready / blank-page setup (ms) | 95.3 [91.8–158.4] | 497.0 [488.1–510.4] | 675.2 [660.8–702.6] | 505.7 [496.5–539.8] | 995.8 [919.5–1125.7] | 1109.7 [1074.5–1128.1] | 2068.7 [2027.8–2120.3] | 1485.4 [1459.0–1519.7] | 4614.6 [4547.8–10315.6] | 2061.7 [1985.5–2212.5] | 692.3 [651.4–727.3] | 695.2 [658.6–746.7] | 746.7 [709.3–833.8] |
| First navigation after setup (ms) | 104.0 [93.8–227.6] | 18.1 [15.5–21.5] | 37.8 [33.3–49.1] | 30.7 [27.5–37.5] | 54.6 [41.4–61.9] | 59.0 [54.7–62.8] | 418.7 [410.9–433.6] | 554.6 [552.6–556.3] | 159.9 [153.8–200.6] | 2543.5 [1010.5–2902.1] | 63.8 [50.9–75.8] | 87.3 [73.7–99.5] | 67.1 [55.4–89.5] |
| Warm tiny-page navigation (ms) | 5.8 [4.3–12.6] | 10.1 [7.7–14.9] | 19.0 [12.6–38.6] | 19.7 [14.8–38.2] | 27.6 [21.3–54.4] | 29.1 [21.9–52.2] | 403.1 [376.7–452.8] | 552.3 [548.5–565.6] | 57.9 [47.6–81.7] | 791.6 [770.5–861.5] | 32.7 [20.5–56.0] | 30.7 [24.0–66.5] | 30.7 [21.6–58.2] |
| Tiny DOM extraction (ms) | 4.4 [0.7–6.5] | 3.2 [2.3–7.0] | 8.5 [3.3–21.7] | 6.0 [1.5–12.2] | 4.3 [3.0–10.9] | 4.7 [3.4–9.5] | 366.2 [340.1–398.3] | 507.0 [505.9–517.9] | 29.5 [24.5–57.8] | 103.1 [93.5–170.2] | 1.4 [1.0–11.1] | 3.4 [2.9–7.8] | 1.9 [1.1–7.2] |
| Large-page navigation (ms) | 39.5 [37.0–44.9] | 31.1 [21.5–48.5] | 39.1 [28.2–52.9] | 38.5 [34.9–45.0] | 76.2 [68.6–99.1] | 73.1 [48.6–88.0] | 438.4 [419.1–463.3] | 713.4 [702.2–738.9] | 88.6 [73.2–128.6] | 807.3 [785.5–861.5] | 59.9 [55.6–67.1] | 94.3 [85.3–100.3] | 58.5 [54.1–64.5] |
| Large DOM extraction, object return (ms) | 11.2 [4.9–19.4] | 94.9 [74.6–138.6] | 101.2 [74.8–146.9] | 28.4 [14.8–47.6] | 28.1 [24.8–38.9] | 47.7 [43.4–97.1] | 408.4 [387.5–441.5] | 595.4 [585.7–660.0] | 52.3 [44.5–90.2] | 1281.7 [1150.3–1403.8] | 34.5 [29.6–45.7] | 67.5 [59.6–83.3] | 23.5 [20.8–28.1] |
| Large DOM extraction, JSON-string return (ms) | 11.6 [5.4–20.2] | 8.9 [7.2–30.7] | 8.8 [7.1–34.0] | 16.8 [7.6–39.1] | 11.4 [9.9–23.0] | 17.3 [15.1–45.0] | 377.9 [352.5–393.7] | 516.9 [514.9–525.5] | 45.9 [37.4–94.0] | 1634.9 [1502.8–1769.1] | 8.5 [7.4–13.4] | 28.8 [26.4–46.2] | 11.9 [10.3–15.9] |
| Image-page navigation (ms) | 116.0 [112.2–123.4] | 119.0 [116.1–133.4] | 124.0 [121.0–138.2] | 126.6 [123.7–136.6] | 131.1 [128.0–139.2] | 142.2 [135.5–179.3] | 506.6 [495.6–556.5] | 656.7 [654.0–672.1] | 189.8 [182.6–210.8] | 815.6 [797.8–967.7] | 129.2 [124.2–146.9] | 132.5 [129.3–138.7] | 127.9 [124.6–136.2] |
| PNG screenshot (ms) | 25.9 [25.5–26.3] | 43.5 [29.6–54.0] | 49.8 [30.1–68.9] | 64.8 [47.5–88.4] | 64.1 [48.5–96.4] | 93.1 [72.9–126.1] | 446.1 [427.5–484.5] | 38.7 [32.1–47.1] | 341.6 [289.8–386.8] | 1371.5 [1311.6–1432.9] | 34.2 [20.2–48.6] | 30.6 [21.4–48.7] | 65.0 [47.9–100.3] |
| Idle total PSS, including display (MiB) | 220.7 [217.3–224.7] | 324.3 [323.5–326.1] | 505.8 [502.5–509.4] | 419.6 [416.8–422.3] | 518.4 [516.3–521.8] | 568.6 [566.9–572.2] | 699.2 [691.0–702.7] | 563.3 [561.2–565.9] | 1323.5 [1310.9–1335.3] | 823.8 [815.2–844.6] | 519.5 [514.9–529.1] | 521.2 [518.3–526.7] | 593.2 [590.8–601.7] |
| Idle process RSS, excluding display (MiB) | 345.1 [336.1–349.1] | 597.7 [594.3–600.8] | 1167.4 [1158.3–1177.6] | 1060.1 [1047.9–1069.8] | 1592.5 [1566.8–1660.5] | 1444.6 [1432.8–1450.5] | 1571.1 [1556.8–1588.6] | 1271.7 [1262.8–1277.9] | 2352.3 [2321.4–2362.9] | 1825.0 [1798.0–1938.6] | 1470.9 [1447.7–1564.6] | 1379.0 [1365.0–1460.0] | 1745.7 [1718.2–1841.7] |
| Installed runtime files, lower bound (MB) | 427.9 | 475.5 | 630.8 | 644.7 | 483.4 | 643.9 | 673.4 | 667.8 | 1660.4 | 677.1 | 644.8 | 645.9 | 628.7 |
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
  "started_utc": "2026-11-04T21:44:27.719622+00:00",
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
  "cpu_model": "INTEL(R) XEON(R) PLATINUM 8573C",
  "mem_total_kib": 16366512,
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
    "@browserbasehq/stagehand": "4.4.0",
    "@modelcontextprotocol/sdk": "1.32.2",
    "@playwright/mcp": "0.0.84",
    "agent-browser": "0.41.2",
    "biloba": "0.22.0",
    "browse": "0.11.3",
    "cypress": "16.2.1",
    "playwright-core": "1.64.1",
    "puppeteer-core": "25.16.0",
    "rustwright": "0.3.0",
    "rustwright-mcp": "0.1.0",
    "uivision-mcp-bridge": "1.7.20"
  },
  "bruster_bytes": 1501752,
  "bruster_sha256": "1a50a8fd05de8ac762ce6f82db644e82783c6defd9967a2adb528d75ab7df83e",
  "chrome_sha256": "377a9fc07b495c3b8d0ab8ec1fdfd153641759f9756fea34d8dfce4de82f5025",
  "headless_shell_sha256": "4fa61f0ba0b4f89b7bec242c32ca16d3bccf69dbfef0651924a9ba8fede5f9d6",
  "rounds": 10,
  "iterations": 10,
  "common_extraction_js": "(() => ({\n  title: document.title,\n  elements: Array.from(document.querySelectorAll('h1,h2,h3,p,li,a,input,button,select,textarea'))\n    .filter(e => { const r = e.getBoundingClientRect(); return r.width > 0 && r.height > 0; })\n    .map(e => ({tag: e.tagName.toLowerCase(),\n      name: (e.getAttribute('aria-label') || e.getAttribute('placeholder') || e.textContent || '').trim(),\n      href: e.getAttribute('href'), value: 'value' in e ? e.value : null}))\n}))()",
  "harness_sha256": {
    "bench_compare.py": "d4da9e833d91d6ca515ae22a0f85fad8a60fc26d3d99391910b61d2c389cddd0",
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
  "package_lock_sha256": "cf197ea51d53877738f76871d6342d83b48de9937fff27ebfa67e47bfddb976e",
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
      "bytes": 10453154,
      "sha256": "a2926a4535a1a7dd63148ddc8322d556e126afd3b2d7e1cc4899bead2d754428"
    }
  },
  "finished_utc": "2026-11-04T22:10:46.116110+00:00"
}
```
