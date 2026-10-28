# Browser comparison

Commit `990b7e6179d5fe17688c2b5361ce753a45b5aa4c` · [workflow run](https://github.com/aliilyas/bruster/actions/runs/40653568407)
Measured 2026-10-28T08:04:47.120238+00:00; 10 sessions per configuration. Values are medians [min–max].
WebKitGTK 2.52.6 · Playwright 1.64.1 · Puppeteer 25.16.0 · agent-browser 0.40.0 · Google Chrome for Testing 156.0.8078.4 · Headless Shell Google Chrome for Testing 156.0.8078.4 · Node v26.12.1

Ubuntu 24.04.5 LTS · Intel(R) Xeon(R) Platinum 8370C CPU @ 2.80GHz · 4 visible CPUs · 15.6 GiB RAM · runner image 20261023.334.3

| Metric | Bruster / WebKitGTK | Playwright / Headless Shell | Playwright / full Chrome | Puppeteer / full Chrome | agent-browser / full Chrome |
|---|---:|---:|---:|---:|---:|
| Launch → first loaded page (ms) | 714.2 [700.3–1399.5] | 542.3 [522.5–558.9] | 763.4 [727.3–818.6] | 579.0 [551.7–610.1] | 853.7 [801.7–903.1] |
| Startup → ready / blank-page setup (ms) | 142.5 [132.7–1267.1] | 522.6 [503.4–539.1] | 710.2 [680.4–764.8] | 536.9 [518.3–569.5] | 750.5 [721.6–811.9] |
| First navigation after setup (ms) | 571.6 [132.1–574.8] | 19.6 [18.7–20.8] | 52.0 [45.1–56.1] | 39.0 [33.0–49.9] | 97.0 [60.9–121.8] |
| Warm tiny-page navigation (ms) | 8.3 [3.9–10.7] | 11.7 [9.9–17.0] | 23.2 [14.8–39.0] | 22.3 [18.4–42.8] | 42.4 [25.3–110.2] |
| Tiny DOM extraction (ms) | 1.1 [0.9–4.5] | 3.6 [2.6–7.7] | 9.5 [3.5–20.3] | 7.3 [1.7–12.5] | 5.1 [3.3–25.3] |
| Large-page navigation (ms) | 30.2 [28.6–34.6] | 34.5 [23.5–49.3] | 42.7 [29.6–55.1] | 44.3 [38.4–51.1] | 86.0 [77.9–116.7] |
| Large DOM extraction, object return (ms) | 21.5 [13.2–35.5] | 105.6 [81.3–165.0] | 111.6 [82.6–157.1] | 31.2 [17.3–63.8] | 30.2 [25.6–42.8] |
| Large DOM extraction, JSON-string return (ms) | 21.7 [11.2–35.5] | 22.9 [8.1–36.6] | 16.6 [8.0–39.0] | 19.9 [8.3–45.1] | 12.9 [11.6–24.1] |
| Image-page navigation (ms) | 116.6 [111.0–118.9] | 120.2 [118.4–133.3] | 126.1 [122.7–148.6] | 130.1 [125.9–146.3] | 133.1 [129.9–146.9] |
| PNG screenshot (ms) | 35.2 [34.4–36.5] | 44.5 [30.8–52.9] | 48.9 [31.5–66.5] | 65.1 [47.7–77.0] | 65.8 [48.5–79.7] |
| Idle total PSS, including display (MiB) | 284.8 [279.9–294.1] | 328.1 [326.0–330.4] | 513.3 [509.8–515.3] | 423.6 [421.7–426.8] | 526.5 [515.7–535.8] |
| Idle process RSS, excluding display (MiB) | 403.2 [400.8–414.4] | 595.4 [592.5–599.7] | 1177.9 [1162.5–1188.6] | 1068.7 [1057.9–1082.1] | 1602.9 [1579.9–1703.8] |
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
  "started_utc": "2026-10-28T08:00:21.503031+00:00",
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
  "cpu_model": "Intel(R) Xeon(R) Platinum 8370C CPU @ 2.80GHz",
  "mem_total_kib": 16372436,
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
  "finished_utc": "2026-10-28T08:04:47.120238+00:00"
}
```
