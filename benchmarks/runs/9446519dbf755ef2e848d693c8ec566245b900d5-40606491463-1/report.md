# Browser comparison

Commit `9446519dbf755ef2e848d693c8ec566245b900d5` · [workflow run](https://github.com/aliilyas/bruster/actions/runs/40606491463)
Measured 2026-10-28T00:11:49.230645+00:00; 10 sessions per configuration. Values are medians [min–max].
WebKitGTK 2.52.6 · Playwright 1.64.1 · Puppeteer 25.16.0 · agent-browser 0.40.0 · Google Chrome for Testing 156.0.8078.4 · Headless Shell Google Chrome for Testing 156.0.8078.4 · Node v26.12.1

Ubuntu 24.04.5 LTS · AMD EPYC 9V74 80-Core Processor · 4 visible CPUs · 15.6 GiB RAM · runner image 20261023.334.3

| Metric | Bruster / WebKitGTK | Playwright / Headless Shell | Playwright / full Chrome | Puppeteer / full Chrome | agent-browser / full Chrome |
|---|---:|---:|---:|---:|---:|
| Launch → first loaded page (ms) | 689.7 [684.7–2310.5] | 447.0 [430.2–471.8] | 633.7 [595.4–668.5] | 480.2 [467.3–766.7] | 716.0 [672.1–894.6] |
| Startup → ready / blank-page setup (ms) | 126.6 [123.3–2188.6] | 430.6 [413.7–454.1] | 583.5 [552.5–628.1] | 442.8 [417.4–498.1] | 642.3 [609.4–809.9] |
| First navigation after setup (ms) | 562.5 [121.6–565.5] | 15.9 [15.2–19.3] | 45.0 [36.7–51.9] | 29.9 [26.1–348.7] | 67.7 [56.9–84.7] |
| Warm tiny-page navigation (ms) | 7.7 [3.8–9.4] | 9.4 [6.9–16.5] | 15.6 [11.1–36.3] | 17.8 [14.8–140.8] | 29.6 [19.1–87.4] |
| Tiny DOM extraction (ms) | 0.9 [0.7–4.7] | 2.8 [2.0–7.4] | 6.0 [2.7–17.8] | 5.7 [1.3–8.0] | 3.9 [2.9–29.8] |
| Large-page navigation (ms) | 25.3 [21.5–27.6] | 28.8 [18.7–41.3] | 34.5 [23.3–56.8] | 33.6 [29.6–42.9] | 71.5 [62.7–91.3] |
| Large DOM extraction, object return (ms) | 16.5 [11.3–24.9] | 84.2 [63.3–168.2] | 89.4 [64.2–130.2] | 26.4 [15.1–46.2] | 27.2 [21.9–37.0] |
| Large DOM extraction, JSON-string return (ms) | 15.7 [7.3–23.8] | 17.3 [7.3–30.9] | 8.8 [7.3–32.9] | 18.7 [7.8–61.0] | 11.7 [10.1–38.8] |
| Image-page navigation (ms) | 115.5 [110.1–126.7] | 116.2 [114.6–129.2] | 119.7 [117.6–133.2] | 122.4 [119.3–132.2] | 125.7 [121.5–133.1] |
| PNG screenshot (ms) | 29.1 [28.4–32.5] | 31.9 [26.4–45.9] | 47.8 [30.6–56.4] | 61.1 [48.0–74.9] | 60.1 [45.4–74.9] |
| Idle total PSS, including display (MiB) | 284.0 [279.0–293.3] | 326.3 [323.0–330.5] | 513.5 [507.6–518.6] | 424.4 [418.1–428.7] | 526.4 [513.8–534.4] |
| Idle process RSS, excluding display (MiB) | 401.7 [400.1–413.5] | 594.8 [590.7–601.1] | 1180.6 [1173.1–1189.3] | 1068.3 [1065.4–1078.7] | 1602.4 [1580.9–1706.5] |
| Installed runtime files, lower bound (MB) | 427.9 | 475.5 | 630.8 | 644.7 | 483.2 |
| Sessions with failures (including cleanup) | 0/10 | 10/10 | 10/10 | 0/10 | 0/10 |

Ten sessions per configuration by default, with rotating order and fresh browser profiles. Values are medians [observed minimum–maximum], not confidence intervals. Startup and first navigation have one sample per session; repeated-operation timings pool all iterations; memory uses the median of three idle readings per session. Startup ends at the adapter ready event, or after blank-page/viewport setup for agent-browser. The combined launch-to-first-page measurement includes both setup and the first navigation. Xvfb is already running: its startup time is excluded, but its memory is included. 1280×800 viewport; localhost fixtures; no-store HTTP responses; navigation waits for load. OS filesystem caches are not flushed. Identical extraction JavaScript and cross-tool result hashes. Timings include controller round trips; agent-browser includes its per-command native CLI. Memory covers the complete owned process forest (including detached daemons and helpers), plus Xvfb for Bruster. PSS apportions shared pages; summed RSS double-counts them. Memory is small-page idle usage, not peak usage. Native snapshots have different semantics and are retained in the raw artifacts rather than ranked as equal work. MB = 1,000,000 bytes; MiB = 1,048,576 bytes. Installed-file inventories are lower bounds including browser/engine, linked libraries, observed mapped files and Node where required; unobserved OS resources may add more. GitHub-hosted runner hardware and OS packages can change: compare the configurations within a run and inspect provenance before interpreting trends.

## Fault probes and cleanup

- Bruster / WebKitGTK: fault probes {}; shutdown/cleanup {}; successful 100 ms recovery retries: 0.
- Playwright / Headless Shell: fault probes {"recovery_after_navigation_error": 10}; shutdown/cleanup {}; successful 100 ms recovery retries: 10.
- Playwright / full Chrome: fault probes {"recovery_after_navigation_error": 10}; shutdown/cleanup {}; successful 100 ms recovery retries: 10.
- Puppeteer / full Chrome: fault probes {}; shutdown/cleanup {}; successful 100 ms recovery retries: 0.
- agent-browser / full Chrome: fault probes {}; shutdown/cleanup {}; successful 100 ms recovery retries: 0.

## Provenance

```json
{
  "started_utc": "2026-10-28T00:07:38.116106+00:00",
  "platform": "Linux-6.17.0-1022-azure-x86_64-with-glibc2.39",
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
  "node": "v26.12.1",
  "chrome": "Google Chrome for Testing 156.0.8078.4",
  "headless_shell": "Google Chrome for Testing 156.0.8078.4",
  "cpu_count": 4,
  "cpu_model": "AMD EPYC 9V74 80-Core Processor",
  "mem_total_kib": 16373452,
  "runner_image": {
    "ImageOS": "ubuntu24",
    "ImageVersion": "20261023.334.3",
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
  "packages": {
    "playwright-core": "1.64.1",
    "puppeteer-core": "25.16.0",
    "agent-browser": "0.40.0"
  },
  "bruster_bytes": 1452808,
  "bruster_sha256": "c593fd6b16f85396b07601e6bb14c5284d3b7c0ce68e11674b90ffab63d5971a",
  "chrome_sha256": "377a9fc07b495c3b8d0ab8ec1fdfd153641759f9756fea34d8dfce4de82f5025",
  "headless_shell_sha256": "4fa61f0ba0b4f89b7bec242c32ca16d3bccf69dbfef0651924a9ba8fede5f9d6",
  "rounds": 10,
  "iterations": 10,
  "common_extraction_js": "(() => ({\n  title: document.title,\n  elements: Array.from(document.querySelectorAll('h1,h2,h3,p,li,a,input,button,select,textarea'))\n    .filter(e => { const r = e.getBoundingClientRect(); return r.width > 0 && r.height > 0; })\n    .map(e => ({tag: e.tagName.toLowerCase(),\n      name: (e.getAttribute('aria-label') || e.getAttribute('placeholder') || e.textContent || '').trim(),\n      href: e.getAttribute('href'), value: 'value' in e ? e.value : null}))\n}))()",
  "harness_sha256": {
    "bench_compare.py": "b0ae6d143db99830cb3dc0dac2c20f953c5b4cb545005cb42f8b3830ea834155",
    "bench_competitor_driver.mjs": "c9bb792d8d3a1a60f1b0f5fe6a1775e865ca715858f3b2da13ba2162f75077fe",
    "bench_audit.py": "df91d7a203077227c82fc6730033498ea20badaf519c6dd8f6bf10b1c6ae006c"
  },
  "package_lock_sha256": "210628238686d22733351fad6e50abaee12565f3664605aa8ac740ad9931716e",
  "args": {
    "bruster": "/home/runner/work/bruster/bruster/target/release/bruster",
    "node": "/opt/hostedtoolcache/node/26.12.1/x64/bin/node",
    "chrome": "/home/runner/work/_temp/benchmark-browsers/chromium-1248/chrome-linux64/chrome",
    "shell": "/home/runner/work/_temp/benchmark-browsers/chromium_headless_shell-1248/chrome-headless-shell-linux64/chrome-headless-shell",
    "deps": "/home/runner/work/_temp/benchmark-deps",
    "output": "/home/runner/work/_temp/benchmark-results",
    "rounds": 10,
    "iterations": 10,
    "tools": [
      "bruster",
      "playwright",
      "puppeteer",
      "agent-browser",
      "playwright-shell"
    ]
  },
  "finished_utc": "2026-10-28T00:11:49.230645+00:00"
}
```
