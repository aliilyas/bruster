# Browser comparison

Commit `869249d36768ef3cc6a56b6902a2dadf7b697698` · [workflow run](https://github.com/aliilyas/bruster/actions/runs/40600226323)
Measured 2026-10-27T23:15:27.476320+00:00; 10 sessions per configuration. Values are medians [min–max].
WebKitGTK 2.52.6 · Playwright 1.64.1 · Puppeteer 25.16.0 · agent-browser 0.40.0 · Google Chrome for Testing 156.0.8078.4 · Headless Shell Google Chrome for Testing 156.0.8078.4 · Node v26.12.1

Ubuntu 24.04.5 LTS · AMD EPYC 9V45 96-Core Processor · 4 visible CPUs · 15.6 GiB RAM · runner image 20261026.354.1

| Metric | Bruster / WebKitGTK | Playwright / Headless Shell | Playwright / full Chrome | Puppeteer / full Chrome | agent-browser / full Chrome |
|---|---:|---:|---:|---:|---:|
| Launch → first loaded page (ms) | 652.6 [170.3–1237.4] | 358.4 [352.5–381.3] | 508.1 [476.6–1538.0] | 378.5 [368.6–398.7] | 623.8 [587.3–656.5] |
| Startup → ready / blank-page setup (ms) | 100.6 [96.4–1100.3] | 344.9 [339.4–366.5] | 471.2 [441.8–1506.6] | 354.1 [343.4–375.2] | 565.9 [529.2–593.0] |
| First navigation after setup (ms) | 551.7 [69.8–555.6] | 13.5 [12.7–16.1] | 33.7 [29.8–39.8] | 23.5 [20.0–26.5] | 60.1 [45.0–67.9] |
| Warm tiny-page navigation (ms) | 6.5 [2.6–9.4] | 7.8 [5.6–11.7] | 13.0 [8.6–30.1] | 13.1 [10.0–22.0] | 27.1 [15.3–65.4] |
| Tiny DOM extraction (ms) | 0.7 [0.5–4.2] | 2.3 [1.7–5.6] | 4.8 [2.2–13.6] | 2.4 [0.9–9.7] | 4.2 [2.5–12.1] |
| Large-page navigation (ms) | 18.7 [18.2–21.3] | 23.0 [15.2–31.8] | 27.9 [19.8–35.4] | 26.3 [23.9–31.7] | 54.1 [47.7–66.3] |
| Large DOM extraction, object return (ms) | 11.6 [8.6–16.9] | 60.4 [43.4–113.4] | 64.2 [46.5–106.5] | 21.2 [12.1–35.8] | 22.8 [19.2–34.0] |
| Large DOM extraction, JSON-string return (ms) | 11.8 [5.5–15.9] | 9.1 [5.4–22.9] | 9.6 [5.3–24.2] | 12.9 [4.9–26.4] | 8.4 [7.1–21.3] |
| Image-page navigation (ms) | 112.2 [107.8–114.4] | 112.6 [110.4–123.3] | 115.2 [113.6–127.4] | 117.5 [113.9–126.4] | 121.6 [117.8–129.6] |
| PNG screenshot (ms) | 21.5 [20.9–22.5] | 30.8 [25.1–40.7] | 34.0 [29.9–50.0] | 64.5 [38.0–78.9] | 49.3 [37.0–65.7] |
| Idle total PSS, including display (MiB) | 244.3 [243.3–249.3] | 324.1 [322.8–326.4] | 507.3 [498.1–508.6] | 419.2 [415.6–420.6] | 516.7 [513.5–519.4] |
| Idle process RSS, excluding display (MiB) | 365.9 [361.5–371.5] | 595.5 [592.7–599.9] | 1173.3 [1159.0–1177.7] | 1063.3 [1054.8–1067.7] | 1592.6 [1575.5–1601.3] |
| Installed runtime files, lower bound (MB) | 428.0 | 475.5 | 630.8 | 644.7 | 483.2 |
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
  "started_utc": "2026-10-27T23:11:36.582504+00:00",
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
  "node": "v26.12.1",
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
  "packages": {
    "playwright-core": "1.64.1",
    "puppeteer-core": "25.16.0",
    "agent-browser": "0.40.0"
  },
  "bruster_bytes": 1456544,
  "bruster_sha256": "e70cfa4f07bfb809b7301eafcd2b95d237904c34c686c954e93c5e7818dd77a0",
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
  "finished_utc": "2026-10-27T23:15:27.476320+00:00"
}
```
