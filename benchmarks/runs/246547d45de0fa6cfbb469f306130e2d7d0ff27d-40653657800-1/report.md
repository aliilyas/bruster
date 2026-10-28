# Browser comparison

Commit `246547d45de0fa6cfbb469f306130e2d7d0ff27d` · [workflow run](https://github.com/aliilyas/bruster/actions/runs/40653657800)
Measured 2026-10-28T08:04:41.544758+00:00; 10 sessions per configuration. Values are medians [min–max].
WebKitGTK 2.52.6 · Playwright 1.64.1 · Puppeteer 25.16.0 · agent-browser 0.40.0 · Google Chrome for Testing 156.0.8078.4 · Headless Shell Google Chrome for Testing 156.0.8078.4 · Node v26.12.1

Ubuntu 24.04.5 LTS · AMD EPYC 9V45 96-Core Processor · 4 visible CPUs · 15.6 GiB RAM · runner image 20261023.334.3

| Metric | Bruster / WebKitGTK | Playwright / Headless Shell | Playwright / full Chrome | Puppeteer / full Chrome | agent-browser / full Chrome |
|---|---:|---:|---:|---:|---:|
| Launch → first loaded page (ms) | 153.7 [140.7–993.8] | 342.9 [327.7–410.2] | 488.2 [473.1–562.7] | 366.7 [351.1–408.4] | 613.8 [552.6–645.7] |
| Startup → ready / blank-page setup (ms) | 72.5 [65.5–826.5] | 329.0 [312.9–390.0] | 452.8 [438.1–516.4] | 342.1 [332.6–384.4] | 544.6 [496.5–572.3] |
| First navigation after setup (ms) | 80.3 [72.5–166.9] | 14.4 [12.8–19.9] | 33.9 [28.5–44.5] | 23.9 [18.3–27.1] | 68.4 [52.1–81.6] |
| Warm tiny-page navigation (ms) | 4.8 [2.6–15.2] | 6.4 [5.3–12.1] | 12.2 [9.1–27.3] | 13.8 [10.1–25.5] | 22.3 [15.2–68.8] |
| Tiny DOM extraction (ms) | 3.9 [0.6–8.1] | 2.1 [1.6–5.5] | 4.9 [2.1–15.1] | 2.4 [0.9–8.1] | 4.2 [2.4–22.9] |
| Large-page navigation (ms) | 25.2 [23.7–29.4] | 23.0 [15.1–31.4] | 28.2 [19.4–42.0] | 27.4 [23.9–37.1] | 53.8 [49.5–63.8] |
| Large DOM extraction, object return (ms) | 7.0 [2.8–12.4] | 61.2 [44.7–104.0] | 65.4 [46.5–103.5] | 20.5 [12.8–39.7] | 22.6 [19.7–28.8] |
| Large DOM extraction, JSON-string return (ms) | 7.3 [3.2–12.8] | 12.9 [5.3–23.9] | 12.9 [5.3–23.2] | 13.0 [5.1–29.9] | 8.1 [6.9–23.1] |
| Image-page navigation (ms) | 111.0 [107.8–122.1] | 112.1 [111.2–124.7] | 115.6 [113.7–130.4] | 117.1 [114.5–125.9] | 120.6 [118.4–128.2] |
| PNG screenshot (ms) | 21.7 [20.8–23.8] | 30.5 [25.4–35.4] | 32.8 [25.3–48.6] | 48.4 [36.9–76.3] | 49.1 [38.3–75.5] |
| Idle total PSS, including display (MiB) | 253.0 [252.3–256.4] | 326.3 [322.9–331.6] | 511.6 [508.8–515.3] | 425.2 [422.0–427.3] | 525.2 [516.7–530.1] |
| Idle process RSS, excluding display (MiB) | 379.0 [378.2–384.2] | 595.9 [590.2–601.8] | 1175.6 [1169.2–1185.2] | 1069.5 [1061.3–1076.2] | 1606.4 [1589.1–1624.1] |
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
  "started_utc": "2026-10-28T08:00:58.249846+00:00",
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
  "cpu_model": "AMD EPYC 9V45 96-Core Processor",
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
  "bruster_bytes": 1469152,
  "bruster_sha256": "db405fcb2ac7c32ced75d9cd98b593fb1e3aef33145b05e66b90a6c1e6c1796b",
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
  "finished_utc": "2026-10-28T08:04:41.544758+00:00"
}
```
