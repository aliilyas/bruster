# Browser comparison

Commit `869249d36768ef3cc6a56b6902a2dadf7b697698` · [workflow run](https://github.com/aliilyas/bruster/actions/runs/40600111057)
Measured 2026-10-27T23:15:12.138313+00:00; 10 sessions per configuration. Values are medians [min–max].
WebKitGTK 2.52.6 · Playwright 1.64.1 · Puppeteer 25.16.0 · agent-browser 0.40.0 · Google Chrome for Testing 156.0.8078.4 · Headless Shell Google Chrome for Testing 156.0.8078.4 · Node v26.12.1

Ubuntu 24.04.5 LTS · AMD EPYC 7763 64-Core Processor · 4 visible CPUs · 15.6 GiB RAM · runner image 20261023.334.3

| Metric | Bruster / WebKitGTK | Playwright / Headless Shell | Playwright / full Chrome | Puppeteer / full Chrome | agent-browser / full Chrome |
|---|---:|---:|---:|---:|---:|
| Launch → first loaded page (ms) | 722.6 [240.1–728.8] | 560.2 [556.7–574.2] | 778.6 [771.0–831.5] | 585.0 [573.5–613.0] | 813.9 [792.7–879.2] |
| Startup → ready / blank-page setup (ms) | 149.1 [143.3–503.7] | 540.3 [534.4–555.3] | 734.4 [712.8–790.1] | 549.7 [538.2–572.7] | 739.3 [727.4–798.6] |
| First navigation after setup (ms) | 573.2 [93.7–578.3] | 18.8 [16.8–24.4] | 44.7 [39.7–59.9] | 34.4 [28.7–40.4] | 75.8 [60.3–111.7] |
| Warm tiny-page navigation (ms) | 8.8 [3.6–12.2] | 11.0 [8.7–18.0] | 19.4 [13.8–40.7] | 20.6 [17.5–37.8] | 40.7 [24.3–107.1] |
| Tiny DOM extraction (ms) | 1.1 [0.8–6.3] | 3.3 [2.5–8.3] | 8.7 [3.3–22.8] | 6.9 [1.6–10.8] | 5.4 [3.4–23.5] |
| Large-page navigation (ms) | 31.9 [28.9–36.6] | 35.4 [23.2–52.7] | 42.7 [29.8–56.5] | 41.2 [36.7–48.5] | 86.9 [78.7–107.3] |
| Large DOM extraction, object return (ms) | 22.1 [14.6–43.3] | 107.2 [79.8–151.4] | 109.3 [80.3–159.0] | 32.4 [17.9–54.2] | 32.7 [26.8–44.6] |
| Large DOM extraction, JSON-string return (ms) | 22.0 [10.9–43.6] | 10.3 [8.5–36.7] | 10.6 [8.3–41.5] | 23.3 [8.5–44.6] | 13.4 [11.6–24.1] |
| Image-page navigation (ms) | 117.7 [112.1–121.1] | 120.8 [117.8–135.9] | 125.4 [120.3–141.2] | 128.0 [123.9–135.2] | 132.7 [128.3–140.7] |
| PNG screenshot (ms) | 39.9 [38.6–47.3] | 47.0 [42.6–57.5] | 59.0 [44.1–71.6] | 78.4 [54.9–92.3] | 65.8 [53.5–82.5] |
| Idle total PSS, including display (MiB) | 284.3 [276.6–285.4] | 325.9 [322.7–328.2] | 511.4 [507.9–517.9] | 423.1 [420.3–424.6] | 520.6 [515.5–527.7] |
| Idle process RSS, excluding display (MiB) | 403.1 [397.6–411.4] | 594.1 [590.7–597.8] | 1175.7 [1172.2–1191.1] | 1069.2 [1064.5–1078.2] | 1590.8 [1582.8–1614.9] |
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
  "started_utc": "2026-10-27T23:10:42.620811+00:00",
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
  "cpu_model": "AMD EPYC 7763 64-Core Processor",
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
  "finished_utc": "2026-10-27T23:15:12.138313+00:00"
}
```
