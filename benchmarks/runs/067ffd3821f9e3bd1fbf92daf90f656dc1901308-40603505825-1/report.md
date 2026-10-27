# Browser comparison

Commit `067ffd3821f9e3bd1fbf92daf90f656dc1901308` · [workflow run](https://github.com/aliilyas/bruster/actions/runs/40603505825)
Measured 2026-10-27T23:44:06.273948+00:00; 10 sessions per configuration. Values are medians [min–max].
WebKitGTK 2.52.6 · Playwright 1.64.1 · Puppeteer 25.16.0 · agent-browser 0.40.0 · Google Chrome for Testing 156.0.8078.4 · Headless Shell Google Chrome for Testing 156.0.8078.4 · Node v26.12.1

Ubuntu 24.04.5 LTS · AMD EPYC 9V74 80-Core Processor · 4 visible CPUs · 15.6 GiB RAM · runner image 20261023.334.3

| Metric | Bruster / WebKitGTK | Playwright / Headless Shell | Playwright / full Chrome | Puppeteer / full Chrome | agent-browser / full Chrome |
|---|---:|---:|---:|---:|---:|
| Launch → first loaded page (ms) | 681.5 [676.2–1994.5] | 422.6 [417.9–426.5] | 583.5 [561.3–644.1] | 446.3 [436.1–849.9] | 660.5 [636.8–732.8] |
| Startup → ready / blank-page setup (ms) | 120.9 [114.0–1367.4] | 406.1 [402.5–410.1] | 546.7 [525.6–607.3] | 418.7 [409.7–691.8] | 598.6 [582.1–653.0] |
| First navigation after setup (ms) | 561.7 [558.8–626.9] | 16.0 [13.8–17.0] | 34.5 [29.5–46.7] | 25.0 [24.4–157.9] | 65.6 [47.3–87.0] |
| Warm tiny-page navigation (ms) | 6.6 [2.8–7.8] | 7.7 [6.6–16.6] | 13.7 [10.5–29.9] | 15.7 [12.7–26.7] | 28.3 [17.7–75.2] |
| Tiny DOM extraction (ms) | 0.7 [0.6–4.8] | 2.5 [1.8–5.5] | 5.7 [2.4–19.6] | 2.6 [1.1–9.1] | 4.9 [2.8–22.1] |
| Large-page navigation (ms) | 22.7 [21.1–23.4] | 27.1 [18.0–28.3] | 32.2 [21.9–38.1] | 30.6 [27.9–34.2] | 62.9 [59.0–77.3] |
| Large DOM extraction, object return (ms) | 13.9 [10.2–21.6] | 79.4 [59.0–116.0] | 81.8 [59.1–120.5] | 22.8 [13.8–40.8] | 24.9 [20.7–39.2] |
| Large DOM extraction, JSON-string return (ms) | 15.5 [7.4–21.2] | 16.1 [6.9–26.6] | 17.1 [6.9–29.9] | 18.1 [6.7–33.9] | 10.1 [9.0–18.1] |
| Image-page navigation (ms) | 113.5 [109.7–118.9] | 114.3 [112.9–126.5] | 118.6 [115.6–131.8] | 119.6 [117.9–127.4] | 123.2 [120.3–129.7] |
| PNG screenshot (ms) | 28.6 [27.9–35.5] | 31.2 [29.9–45.1] | 36.3 [29.8–51.4] | 48.1 [42.8–74.8] | 51.4 [47.3–74.1] |
| Idle total PSS, including display (MiB) | 284.1 [277.6–285.9] | 328.0 [324.4–330.6] | 515.2 [510.3–520.0] | 424.7 [421.8–429.6] | 521.5 [516.6–524.5] |
| Idle process RSS, excluding display (MiB) | 402.0 [398.9–405.2] | 596.9 [592.4–599.7] | 1180.5 [1159.6–1190.0] | 1068.4 [1053.8–1081.2] | 1595.8 [1584.7–1615.8] |
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
  "started_utc": "2026-10-27T23:40:04.170054+00:00",
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
  "mem_total_kib": 16373448,
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
  "bruster_bytes": 1452824,
  "bruster_sha256": "7fe32d1b8566891f93807f1bccdd80eadfb458accd0c470704ba508dbbc15447",
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
  "finished_utc": "2026-10-27T23:44:06.273948+00:00"
}
```
