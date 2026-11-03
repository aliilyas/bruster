# Browser comparison

Commit `e5715899d3b39a61f5a0d70fc1d02107782bd044` · [workflow run](https://github.com/aliilyas/bruster/actions/runs/41731814829)
Measured 2026-11-03T22:59:10.846835+00:00; 10 sessions per configuration. Values are medians [min–max].
WebKitGTK 2.52.6 · @browserbasehq/stagehand 4.3.0 · @modelcontextprotocol/sdk 1.32.2 · @playwright/mcp 0.0.84 · agent-browser 0.41.1 · biloba 0.21.0 · browse 0.11.3 · cypress 16.2.1 · playwright-core 1.64.1 · puppeteer-core 25.16.0 · rustwright 0.3.0 · rustwright-mcp 0.1.0 · uivision-mcp-bridge 1.7.20 · Google Chrome for Testing 156.0.8078.4 · Headless Shell Google Chrome for Testing 156.0.8078.4 · Node v26.13.0

Ubuntu 24.04.5 LTS · AMD EPYC 9V45 96-Core Processor · 4 visible CPUs · 15.6 GiB RAM · runner image 20261026.354.1

| Metric | Bruster / WebKitGTK | Playwright / Headless Shell | Playwright / full Chrome | Puppeteer / full Chrome | agent-browser / full Chrome | Stagehand / full Chrome | browse.sh / full Chrome | Playwright MCP / full Chrome | Cypress / Chrome test runner | Ui.Vision MCP / browser extension | Rustwright / full Chrome | Rustwright MCP / full Chrome | Biloba / full Chrome |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Launch → first loaded page (ms) | 182.6 [150.0–544.7] | 425.9 [391.6–438.3] | 596.3 [550.9–623.3] | 443.9 [414.8–474.5] | 693.9 [634.5–780.5] | 966.8 [892.2–1031.1] | 1972.7 [1854.4–2115.2] | 1822.8 [1766.6–1916.2] | 3877.6 [3682.1–4313.0] | 3559.3 [2324.1–4093.0] | 622.9 [584.7–673.0] | 628.4 [584.9–710.5] | 718.6 [644.7–786.2] |
| Startup → ready / blank-page setup (ms) | 83.8 [70.1–311.5] | 409.1 [374.0–422.9] | 554.7 [501.4–580.4] | 416.2 [386.4–443.2] | 627.4 [582.4–686.8] | 915.0 [843.7–987.8] | 1642.5 [1554.8–1733.4] | 1278.2 [1228.1–1352.9] | 3742.8 [3545.2–4190.0] | 1532.1 [1392.9–1856.0] | 576.0 [537.4–602.8] | 543.2 [519.0–617.0] | 654.0 [586.5–710.1] |
| First navigation after setup (ms) | 97.8 [79.6–232.8] | 16.3 [14.0–20.3] | 41.4 [38.0–53.2] | 28.3 [23.2–33.2] | 68.6 [47.7–93.6] | 44.3 [35.2–61.2] | 324.9 [299.6–381.7] | 544.0 [538.2–563.6] | 139.6 [122.6–180.4] | 2063.5 [930.9–2236.7] | 52.3 [40.3–69.6] | 80.4 [54.9–110.2] | 61.7 [50.3–78.7] |
| Warm tiny-page navigation (ms) | 5.8 [4.2–11.1] | 9.2 [6.5–16.1] | 16.0 [10.5–38.5] | 16.6 [12.9–30.5] | 32.1 [17.0–88.3] | 27.9 [20.4–38.7] | 330.4 [284.3–381.6] | 540.0 [534.5–565.4] | 49.9 [39.1–82.8] | 758.9 [735.8–813.3] | 27.9 [15.5–51.4] | 26.3 [17.4–68.5] | 30.3 [15.4–93.9] |
| Tiny DOM extraction (ms) | 4.9 [0.8–6.8] | 2.7 [1.8–7.5] | 5.6 [2.6–29.0] | 2.6 [1.0–10.1] | 4.7 [2.9–18.7] | 5.1 [3.2–12.9] | 296.7 [250.0–378.9] | 505.4 [503.8–513.0] | 27.3 [16.7–53.0] | 86.9 [61.7–133.2] | 1.3 [0.9–10.4] | 2.6 [2.0–13.2] | 1.7 [0.9–6.9] |
| Large-page navigation (ms) | 35.0 [28.6–44.2] | 26.2 [16.2–30.3] | 31.9 [21.5–52.0] | 31.6 [25.4–49.0] | 64.9 [56.1–92.3] | 62.2 [41.1–80.1] | 353.1 [319.6–516.8] | 669.6 [642.5–709.8] | 76.5 [59.1–117.0] | 775.1 [750.9–807.6] | 48.4 [41.9–56.9] | 76.9 [64.0–90.7] | 49.6 [42.2–94.6] |
| Large DOM extraction, object return (ms) | 12.4 [3.4–18.5] | 71.8 [48.3–123.2] | 75.2 [52.0–128.1] | 25.3 [14.1–48.8] | 27.5 [21.3–36.9] | 41.1 [32.9–71.2] | 332.6 [294.9–367.3] | 568.9 [556.0–629.7] | 45.4 [36.7–81.1] | 1079.8 [915.9–1314.4] | 31.2 [27.0–36.4] | 57.4 [46.7–95.0] | 20.9 [17.9–29.0] |
| Large DOM extraction, JSON-string return (ms) | 6.6 [3.5–20.8] | 12.2 [5.9–26.9] | 14.8 [5.7–33.1] | 16.2 [5.8–34.1] | 10.3 [8.2–21.3] | 14.5 [12.2–40.8] | 301.5 [269.8–371.3] | 512.6 [509.7–524.7] | 39.3 [32.1–85.5] | 1398.6 [1133.2–1714.7] | 7.0 [5.8–9.5] | 24.2 [19.7–40.4] | 9.6 [7.5–14.6] |
| Image-page navigation (ms) | 114.3 [109.3–129.7] | 115.9 [112.8–129.5] | 120.0 [114.8–133.6] | 122.2 [115.8–146.9] | 126.4 [121.4–138.3] | 128.4 [123.4–159.3] | 427.6 [394.3–518.3] | 643.8 [636.0–658.2] | 177.8 [163.1–199.6] | 791.5 [746.5–911.1] | 122.9 [117.8–137.1] | 126.7 [121.3–139.3] | 124.4 [118.1–136.7] |
| PNG screenshot (ms) | 23.9 [22.6–26.7] | 31.0 [28.5–42.9] | 40.5 [30.1–53.3] | 48.5 [41.6–72.1] | 58.7 [42.8–92.8] | 69.7 [60.0–114.1] | 356.8 [311.6–402.7] | 29.8 [27.5–49.4] | 252.6 [232.0–275.8] | 1321.7 [1282.5–1374.2] | 23.6 [12.8–41.2] | 21.5 [12.7–42.7] | 61.1 [45.6–81.0] |
| Idle total PSS, including display (MiB) | 219.3 [217.4–223.2] | 324.7 [322.9–325.5] | 508.7 [504.4–509.8] | 420.5 [417.7–423.3] | 517.2 [514.1–520.2] | 612.1 [605.0–616.1] | 697.4 [695.4–705.9] | 563.7 [562.4–568.1] | 1320.4 [1304.0–1330.1] | 825.8 [813.2–855.9] | 518.7 [516.7–525.3] | 523.7 [522.1–526.6] | 592.7 [591.4–593.7] |
| Idle process RSS, excluding display (MiB) | 344.4 [339.2–344.9] | 597.0 [594.0–600.0] | 1174.9 [1171.1–1178.4] | 1066.1 [1057.8–1069.7] | 1585.5 [1564.4–1603.9] | 1475.4 [1461.9–1506.3] | 1576.3 [1553.8–1588.3] | 1272.8 [1267.5–1282.4] | 2342.6 [2305.2–2362.7] | 1832.2 [1788.4–1932.0] | 1471.4 [1447.8–1553.0] | 1374.2 [1364.9–1394.0] | 1742.0 [1725.8–1749.7] |
| Installed runtime files, lower bound (MB) | 427.9 | 475.5 | 630.8 | 644.7 | 483.2 | 641.7 | 672.1 | 666.3 | 1660.4 | 675.5 | 644.8 | 644.3 | 628.7 |
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
  "started_utc": "2026-11-03T22:35:15.906477+00:00",
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
  "cpu_model": "AMD EPYC 9V45 96-Core Processor",
  "mem_total_kib": 16367524,
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
    "biloba": "0.21.0",
    "browse": "0.11.3",
    "cypress": "16.2.1",
    "playwright-core": "1.64.1",
    "puppeteer-core": "25.16.0",
    "rustwright": "0.3.0",
    "rustwright-mcp": "0.1.0",
    "uivision-mcp-bridge": "1.7.20"
  },
  "bruster_bytes": 1472080,
  "bruster_sha256": "790690d2263802ceb6f72bc82cd85cefaf08b6cc41e61ff2017f7832dab930c1",
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
  "package_lock_sha256": "62dcaa063b04da30c17029bc6237f554cbca31d30a282799813e153624ee4014",
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
      "bytes": 10444962,
      "sha256": "c2d55a61e6336259c28c7ed65da478d18554b11f7c4279e1a7d22795b0409d90"
    }
  },
  "finished_utc": "2026-11-03T22:59:10.846835+00:00"
}
```
