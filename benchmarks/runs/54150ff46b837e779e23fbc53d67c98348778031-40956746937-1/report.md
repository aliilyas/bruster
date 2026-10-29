# Browser comparison

Commit `54150ff46b837e779e23fbc53d67c98348778031` · [workflow run](https://github.com/aliilyas/bruster/actions/runs/40956746937)
Measured 2026-10-29T21:24:50.185924+00:00; 10 sessions per configuration. Values are medians [min–max].
WebKitGTK 2.52.6 · Playwright 1.64.1 · Puppeteer 25.16.0 · agent-browser 0.41.0 · Google Chrome for Testing 156.0.8078.4 · Headless Shell Google Chrome for Testing 156.0.8078.4 · Node v27.0.0-alpha.0.0.0

Ubuntu 24.04.5 LTS · AMD EPYC 7763 64-Core Processor · 4 visible CPUs · 15.6 GiB RAM · runner image 20261026.354.1

| Metric | Bruster / WebKitGTK | Playwright / Headless Shell | Playwright / full Chrome | Puppeteer / full Chrome | agent-browser / full Chrome |
|---|---:|---:|---:|---:|---:|
| Launch → first loaded page (ms) | 220.1 [202.4–1294.9] | 574.2 [565.0–587.2] | 791.1 [757.2–827.9] | 591.9 [578.2–606.2] | 844.8 [809.8–898.0] |
| Startup → ready / blank-page setup (ms) | 102.4 [98.8–978.8] | 557.6 [544.4–567.4] | 746.1 [724.2–779.6] | 559.0 [545.7–570.8] | 770.0 [732.7–797.1] |
| First navigation after setup (ms) | 116.3 [102.1–315.8] | 18.7 [16.0–21.5] | 39.8 [31.2–50.1] | 32.1 [30.0–35.1] | 76.0 [62.3–100.8] |
| Warm tiny-page navigation (ms) | 6.5 [4.1–15.1] | 10.2 [8.3–16.1] | 18.3 [13.3–40.2] | 20.1 [16.4–33.0] | 40.6 [23.0–93.8] |
| Tiny DOM extraction (ms) | 5.7 [0.8–8.5] | 2.9 [2.2–6.8] | 7.2 [3.2–23.0] | 6.2 [1.3–11.0] | 5.6 [3.4–19.0] |
| Large-page navigation (ms) | 51.0 [48.5–66.6] | 33.7 [21.8–49.3] | 40.1 [27.5–54.9] | 38.5 [35.7–45.6] | 83.4 [74.4–105.0] |
| Large DOM extraction, object return (ms) | 12.4 [4.9–23.0] | 100.2 [75.1–131.6] | 106.1 [76.3–140.7] | 29.3 [16.2–52.2] | 31.3 [25.1–45.0] |
| Large DOM extraction, JSON-string return (ms) | 13.2 [5.3–22.8] | 9.9 [8.3–34.5] | 22.9 [8.3–37.8] | 19.6 [8.3–44.7] | 12.6 [11.3–22.6] |
| Image-page navigation (ms) | 116.7 [112.3–123.5] | 119.3 [116.9–133.9] | 123.3 [120.7–138.8] | 125.7 [122.2–133.3] | 130.7 [126.5–138.3] |
| PNG screenshot (ms) | 39.4 [38.7–44.0] | 47.5 [42.2–58.2] | 58.6 [43.3–65.6] | 78.9 [48.0–87.7] | 82.0 [58.4–86.8] |
| Idle total PSS, including display (MiB) | 219.8 [216.7–222.0] | 317.7 [316.6–318.4] | 500.4 [498.4–502.4] | 423.0 [420.8–424.2] | 516.7 [512.9–520.2] |
| Idle process RSS, excluding display (MiB) | 344.4 [343.8–347.3] | 589.6 [586.2–591.7] | 1165.1 [1157.5–1167.4] | 1068.8 [1057.7–1072.7] | 1591.5 [1570.5–1598.3] |
| Installed runtime files, lower bound (MB) | 427.9 | 483.8 | 639.1 | 653.1 | 483.2 |
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
  "started_utc": "2026-10-29T21:20:23.731033+00:00",
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
  "node": "v27.0.0-alpha.0.0.0",
  "chrome": "Google Chrome for Testing 156.0.8078.4",
  "headless_shell": "Google Chrome for Testing 156.0.8078.4",
  "cpu_count": 4,
  "cpu_model": "AMD EPYC 7763 64-Core Processor",
  "mem_total_kib": 16371756,
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
    "agent-browser": "0.41.0"
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
  "package_lock_sha256": "899cd275611ad5cb31ac6ecb7634ca47cbc203c97364e351ab9300f8a4525b0d",
  "args": {
    "bruster": "/home/runner/work/bruster/bruster/target/release/bruster",
    "node": "/opt/hostedtoolcache/node/27.0.0-alpha.0.0.0/x64/bin/node",
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
  "finished_utc": "2026-10-29T21:24:50.185924+00:00"
}
```
