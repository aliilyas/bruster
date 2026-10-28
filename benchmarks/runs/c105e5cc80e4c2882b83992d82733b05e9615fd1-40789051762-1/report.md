# Browser comparison

Commit `c105e5cc80e4c2882b83992d82733b05e9615fd1` · [workflow run](https://github.com/aliilyas/bruster/actions/runs/40789051762)
Measured 2026-10-28T23:46:32.147062+00:00; 10 sessions per configuration. Values are medians [min–max].
WebKitGTK 2.52.6 · Playwright 1.64.1 · Puppeteer 25.16.0 · agent-browser 0.40.0 · Google Chrome for Testing 156.0.8078.4 · Headless Shell Google Chrome for Testing 156.0.8078.4 · Node v26.13.0

Ubuntu 24.04.5 LTS · INTEL(R) XEON(R) PLATINUM 8573C · 4 visible CPUs · 15.6 GiB RAM · runner image 20261026.354.1

| Metric | Bruster / WebKitGTK | Playwright / Headless Shell | Playwright / full Chrome | Puppeteer / full Chrome | agent-browser / full Chrome |
|---|---:|---:|---:|---:|---:|
| Launch → first loaded page (ms) | 168.4 [158.6–1920.8] | 435.3 [427.0–447.6] | 601.4 [585.1–665.1] | 448.1 [437.5–454.6] | 654.0 [613.8–670.6] |
| Startup → ready / blank-page setup (ms) | 81.8 [79.2–1071.6] | 419.9 [411.0–430.3] | 568.7 [557.2–619.1] | 422.7 [413.0–430.5] | 595.1 [569.8–615.0] |
| First navigation after setup (ms) | 85.0 [76.6–849.0] | 15.2 [13.3–16.9] | 31.4 [22.6–45.7] | 24.0 [22.0–26.6] | 53.7 [44.0–65.7] |
| Warm tiny-page navigation (ms) | 4.8 [3.6–8.8] | 8.4 [6.8–12.3] | 15.3 [9.9–29.4] | 15.6 [12.4–23.6] | 29.6 [16.2–65.2] |
| Tiny DOM extraction (ms) | 3.5 [0.7–5.2] | 2.6 [1.9–7.5] | 6.2 [2.6–23.3] | 2.6 [1.3–8.7] | 4.8 [2.3–15.4] |
| Large-page navigation (ms) | 32.0 [30.3–39.2] | 24.6 [18.1–36.8] | 30.4 [24.6–50.0] | 31.7 [26.6–37.5] | 63.4 [56.7–77.3] |
| Large DOM extraction, object return (ms) | 9.4 [4.0–16.5] | 78.9 [59.7–119.8] | 83.6 [61.4–125.4] | 21.6 [11.9–38.0] | 22.4 [19.3–37.0] |
| Large DOM extraction, JSON-string return (ms) | 10.0 [4.3–16.4] | 14.8 [5.5–26.2] | 7.5 [5.5–28.8] | 14.9 [6.0–34.0] | 9.3 [7.6–16.2] |
| Image-page navigation (ms) | 111.9 [109.3–119.0] | 114.8 [113.7–125.0] | 118.1 [116.3–127.8] | 120.2 [118.0–127.7] | 123.7 [121.0–131.3] |
| PNG screenshot (ms) | 26.1 [25.3–27.7] | 31.5 [29.1–46.3] | 47.4 [29.3–54.0] | 64.3 [44.4–84.0] | 55.4 [47.7–73.9] |
| Idle total PSS, including display (MiB) | 218.6 [216.8–222.5] | 324.7 [323.1–326.1] | 506.2 [504.8–508.7] | 418.4 [414.8–420.3] | 515.5 [512.9–518.4] |
| Idle process RSS, excluding display (MiB) | 347.4 [344.0–348.1] | 596.1 [591.2–599.3] | 1171.4 [1163.3–1177.6] | 1065.1 [1044.3–1069.1] | 1582.6 [1575.3–1600.9] |
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
  "started_utc": "2026-10-28T23:42:37.117604+00:00",
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
  "mem_total_kib": 16366500,
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
  "finished_utc": "2026-10-28T23:46:32.147062+00:00"
}
```
