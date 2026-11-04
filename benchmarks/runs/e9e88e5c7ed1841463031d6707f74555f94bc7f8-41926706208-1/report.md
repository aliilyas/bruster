# Browser comparison

Commit `e9e88e5c7ed1841463031d6707f74555f94bc7f8` · [workflow run](https://github.com/aliilyas/bruster/actions/runs/41926706208)
Measured 2026-11-04T23:03:53.264345+00:00; 10 sessions per configuration. Values are medians [min–max].
WebKitGTK 2.52.6 · @browserbasehq/stagehand 4.4.0 · @modelcontextprotocol/sdk 1.32.2 · @playwright/mcp 0.0.84 · agent-browser 0.41.2 · biloba 0.22.0 · browse 0.11.3 · cypress 16.2.1 · playwright-core 1.64.1 · puppeteer-core 25.16.0 · rustwright 0.3.0 · rustwright-mcp 0.1.0 · uivision-mcp-bridge 1.7.20 · Google Chrome for Testing 156.0.8078.4 · Headless Shell Google Chrome for Testing 156.0.8078.4 · Node v26.13.0

Ubuntu 24.04.5 LTS · Intel(R) Xeon(R) 6975P-C · 4 visible CPUs · 15.3 GiB RAM · runner image 20261018.96.1

| Metric | Bruster / WebKitGTK | Playwright / Headless Shell | Playwright / full Chrome | Puppeteer / full Chrome | agent-browser / full Chrome | Stagehand / full Chrome | browse.sh / full Chrome | Playwright MCP / full Chrome | Cypress / Chrome test runner | Ui.Vision MCP / browser extension | Rustwright / full Chrome | Rustwright MCP / full Chrome | Biloba / full Chrome |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Launch → first loaded page (ms) | 160.5 [151.9–289.6] | 397.3 [387.4–402.9] | 540.4 [530.1–561.4] | 403.4 [398.2–420.3] | 747.7 [693.3–796.5] | 867.8 [826.0–906.5] | 1891.3 [1837.3–1944.8] | 1792.0 [1774.2–1819.6] | 3689.6 [3545.5–16456.7] | 3585.6 [3411.5–3612.0] | 543.7 [524.5–592.1] | 567.6 [557.3–592.6] | 614.6 [579.7–631.7] |
| Startup → ready / blank-page setup (ms) | 80.0 [73.9–120.8] | 382.6 [372.6–387.9] | 510.5 [504.4–524.8] | 381.2 [375.2–398.3] | 698.3 [628.7–755.4] | 823.1 [783.8–862.6] | 1562.2 [1519.9–1612.1] | 1248.4 [1233.7–1276.5] | 3562.5 [3431.3–16337.3] | 1622.0 [1438.9–1663.2] | 501.5 [482.3–543.5] | 512.0 [485.2–541.3] | 555.3 [521.1–568.5] |
| First navigation after setup (ms) | 80.8 [71.0–168.5] | 13.6 [12.1–15.5] | 30.5 [18.6–38.3] | 22.7 [20.4–27.1] | 47.1 [38.8–66.1] | 44.8 [41.7–49.4] | 324.9 [317.3–334.1] | 542.5 [540.2–546.6] | 127.8 [114.0–158.3] | 1955.1 [1933.4–1993.3] | 42.1 [34.7–52.8] | 57.0 [45.1–70.6] | 60.0 [48.4–75.9] |
| Warm tiny-page navigation (ms) | 4.3 [3.2–10.0] | 7.4 [5.9–11.9] | 15.1 [8.6–24.5] | 13.9 [10.7–27.6] | 23.6 [15.6–43.3] | 20.7 [15.4–37.9] | 316.8 [284.6–346.7] | 541.1 [537.9–554.9] | 43.6 [33.3–53.2] | 760.9 [745.6–794.7] | 22.6 [15.2–36.5] | 22.6 [16.6–48.5] | 21.9 [15.4–48.0] |
| Tiny DOM extraction (ms) | 3.1 [0.6–4.4] | 2.5 [1.7–6.4] | 6.2 [2.3–15.6] | 4.3 [0.9–7.7] | 3.1 [2.3–11.1] | 3.6 [2.7–8.7] | 289.2 [274.0–312.7] | 506.4 [505.5–516.9] | 21.0 [13.6–34.7] | 84.3 [77.4–127.6] | 1.2 [0.8–6.7] | 2.9 [2.1–11.6] | 1.4 [0.9–5.4] |
| Large-page navigation (ms) | 30.0 [22.0–35.5] | 23.3 [16.2–33.6] | 28.7 [21.8–31.4] | 28.1 [24.2–32.4] | 57.7 [52.7–76.5] | 52.6 [36.2–62.2] | 339.0 [315.2–355.4] | 666.6 [655.1–680.4] | 65.0 [56.7–95.0] | 770.6 [758.6–788.6] | 43.5 [39.4–59.2] | 70.6 [63.6–76.1] | 43.5 [40.9–48.0] |
| Large DOM extraction, object return (ms) | 10.9 [3.6–15.6] | 70.6 [54.0–117.5] | 75.5 [55.0–123.1] | 21.1 [11.3–35.7] | 22.1 [19.4–33.3] | 36.6 [31.1–70.2] | 316.1 [297.2–347.6] | 572.1 [565.7–627.8] | 39.8 [33.9–73.6] | 1012.0 [904.5–1140.6] | 26.0 [23.4–34.2] | 51.4 [45.9–65.2] | 17.5 [15.2–23.7] |
| Large DOM extraction, JSON-string return (ms) | 8.9 [3.7–18.2] | 7.4 [5.1–23.2] | 14.4 [5.4–26.8] | 12.9 [5.4–30.7] | 8.9 [7.5–16.6] | 14.2 [11.4–30.7] | 293.4 [274.5–315.9] | 514.4 [512.0–521.7] | 33.0 [23.0–70.8] | 1308.8 [1197.9–1439.6] | 6.7 [5.7–9.6] | 21.8 [20.3–35.6] | 9.2 [7.7–12.0] |
| Image-page navigation (ms) | 111.7 [108.1–120.3] | 114.5 [111.7–124.0] | 117.4 [114.7–128.3] | 119.4 [116.8–127.6] | 124.0 [120.3–131.1] | 131.9 [125.3–164.1] | 418.1 [406.1–439.6] | 644.4 [642.1–654.0] | 166.5 [157.9–178.1] | 770.6 [759.9–919.6] | 122.2 [118.2–128.9] | 124.4 [121.4–130.5] | 120.6 [117.6–127.9] |
| PNG screenshot (ms) | 20.5 [19.4–22.0] | 32.3 [29.1–42.5] | 48.2 [31.6–52.0] | 48.4 [42.8–82.9] | 55.5 [48.3–74.3] | 78.5 [60.2–102.8] | 358.6 [328.9–380.1] | 31.1 [25.7–55.4] | 268.2 [228.3–301.1] | 1346.8 [1289.3–1393.8] | 28.0 [12.8–40.3] | 25.6 [12.5–46.3] | 54.3 [44.6–81.2] |
| Idle total PSS, including display (MiB) | 219.1 [214.9–222.9] | 324.7 [322.2–326.0] | 507.1 [505.2–508.7] | 420.6 [417.3–422.2] | 518.5 [516.3–522.2] | 569.6 [566.8–571.7] | 696.8 [688.6–704.3] | 564.1 [560.1–566.1] | 1321.3 [1304.5–1335.1] | 829.6 [823.2–851.9] | 518.9 [515.9–520.0] | 521.5 [520.3–523.3] | 594.0 [590.7–597.0] |
| Idle process RSS, excluding display (MiB) | 336.5 [334.9–344.9] | 597.7 [595.0–601.3] | 1161.6 [1151.7–1177.2] | 1058.9 [1047.3–1069.8] | 1591.8 [1577.6–1605.8] | 1454.5 [1437.0–1462.9] | 1572.9 [1553.1–1583.4] | 1272.2 [1254.6–1281.1] | 2342.0 [2311.3–2360.9] | 1824.4 [1804.2–1937.2] | 1459.6 [1453.1–1469.6] | 1375.0 [1356.3–1388.6] | 1742.7 [1721.4–1756.6] |
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
  "started_utc": "2026-11-04T22:40:40.255805+00:00",
  "platform": "Linux-7.0.0-1014-aws-x86_64-with-glibc2.39",
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
  "cpu_model": "Intel(R) Xeon(R) 6975P-C",
  "mem_total_kib": 16078424,
  "runner_image": {
    "ImageOS": "ubuntu24",
    "ImageVersion": "20261018.96.1",
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
  "bruster_bytes": 1502008,
  "bruster_sha256": "a33dd56c4c2eb691c26fb879dc77d53dc7f8c353aad855efdf0fad3e0081c0e3",
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
  "finished_utc": "2026-11-04T23:03:53.264345+00:00"
}
```
