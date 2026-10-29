# Browser comparison

Commit `254e5d12ababb5d8f573ceb7443753ec275f90c4` · [workflow run](https://github.com/aliilyas/bruster/actions/runs/40790947958)
Measured 2026-10-29T00:04:03.765347+00:00; 10 sessions per configuration. Values are medians [min–max].
WebKitGTK 2.52.6 · Playwright 1.64.1 · Puppeteer 25.16.0 · agent-browser 0.40.0 · Google Chrome for Testing 156.0.8078.4 · Headless Shell Google Chrome for Testing 156.0.8078.4 · Node v26.13.0

Ubuntu 24.04.5 LTS · AMD EPYC 9V74 80-Core Processor · 4 visible CPUs · 15.6 GiB RAM · runner image 20261026.354.1

| Metric | Bruster / WebKitGTK | Playwright / Headless Shell | Playwright / full Chrome | Puppeteer / full Chrome | agent-browser / full Chrome |
|---|---:|---:|---:|---:|---:|
| Launch → first loaded page (ms) | 186.7 [178.3–1023.1] | 454.5 [447.5–473.5] | 627.0 [609.5–688.2] | 471.7 [459.2–485.2] | 691.1 [677.8–751.3] |
| Startup → ready / blank-page setup (ms) | 86.5 [82.1–370.3] | 439.0 [432.5–457.6] | 587.3 [575.6–645.2] | 442.7 [434.5–457.8] | 630.7 [623.7–677.5] |
| First navigation after setup (ms) | 100.6 [90.9–652.5] | 15.8 [13.2–17.4] | 34.9 [29.6–46.7] | 25.9 [23.0–30.8] | 57.8 [54.1–73.6] |
| Warm tiny-page navigation (ms) | 5.3 [3.2–8.2] | 8.3 [6.6–14.1] | 14.3 [10.5–32.0] | 16.2 [12.5–26.1] | 32.6 [18.3–80.2] |
| Tiny DOM extraction (ms) | 4.8 [0.7–6.9] | 2.6 [1.8–7.4] | 6.1 [2.7–16.6] | 2.4 [0.9–8.2] | 5.1 [2.9–16.5] |
| Large-page navigation (ms) | 35.7 [34.1–40.6] | 28.0 [18.1–29.1] | 33.6 [22.6–41.2] | 31.9 [28.6–35.3] | 66.6 [61.2–82.4] |
| Large DOM extraction, object return (ms) | 11.7 [3.8–16.8] | 83.2 [60.3–122.7] | 86.8 [60.9–124.2] | 23.9 [14.3–41.6] | 26.5 [21.9–40.4] |
| Large DOM extraction, JSON-string return (ms) | 10.1 [4.3–17.7] | 16.7 [7.2–28.0] | 18.7 [7.1–30.6] | 17.1 [6.8–34.6] | 10.8 [9.2–18.9] |
| Image-page navigation (ms) | 113.8 [109.9–119.9] | 114.9 [113.4–128.3] | 117.5 [115.7–131.2] | 119.8 [118.2–127.9] | 124.3 [121.2–129.6] |
| PNG screenshot (ms) | 28.7 [28.2–29.2] | 32.7 [29.0–45.0] | 34.1 [29.8–51.1] | 48.3 [44.5–76.4] | 49.2 [46.9–76.5] |
| Idle total PSS, including display (MiB) | 218.7 [216.7–222.7] | 324.8 [321.8–326.0] | 506.3 [504.6–508.0] | 419.5 [417.4–421.1] | 515.7 [513.5–518.6] |
| Idle process RSS, excluding display (MiB) | 344.2 [340.9–348.0] | 595.9 [587.8–599.4] | 1171.8 [1164.7–1175.2] | 1064.2 [1054.1–1069.2] | 1589.6 [1571.1–1599.4] |
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
  "started_utc": "2026-10-29T00:00:01.148517+00:00",
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
  "cpu_model": "AMD EPYC 9V74 80-Core Processor",
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
  "bruster_bytes": 1472144,
  "bruster_sha256": "016a2cf9de97003c0e7be3ea7628dbb5cbf29192c6dd30ff49be49fc22b05f9c",
  "chrome_sha256": "377a9fc07b495c3b8d0ab8ec1fdfd153641759f9756fea34d8dfce4de82f5025",
  "headless_shell_sha256": "4fa61f0ba0b4f89b7bec242c32ca16d3bccf69dbfef0651924a9ba8fede5f9d6",
  "rounds": 10,
  "iterations": 10,
  "common_extraction_js": "(() => ({\n  title: document.title,\n  elements: Array.from(document.querySelectorAll('h1,h2,h3,p,li,a,input,button,select,textarea'))\n    .filter(e => { const r = e.getBoundingClientRect(); return r.width > 0 && r.height > 0; })\n    .map(e => ({tag: e.tagName.toLowerCase(),\n      name: (e.getAttribute('aria-label') || e.getAttribute('placeholder') || e.textContent || '').trim(),\n      href: e.getAttribute('href'), value: 'value' in e ? e.value : null}))\n}))()",
  "harness_sha256": {
    "bench_compare.py": "ebfa32d27a3fbde2e272272fbbb8e8318bc13b01e9d0fb27f27c7db2fe6e6759",
    "bench_competitor_driver.mjs": "c9bb792d8d3a1a60f1b0f5fe6a1775e865ca715858f3b2da13ba2162f75077fe",
    "bench_audit.py": "df91d7a203077227c82fc6730033498ea20badaf519c6dd8f6bf10b1c6ae006c"
  },
  "package_lock_sha256": "210628238686d22733351fad6e50abaee12565f3664605aa8ac740ad9931716e",
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
      "playwright",
      "puppeteer",
      "agent-browser",
      "playwright-shell"
    ]
  },
  "finished_utc": "2026-10-29T00:04:03.765347+00:00"
}
```
