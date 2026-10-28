# Browser comparison

Commit `74f591bc55737514dacb6e12b1a200afa26f282a` · [workflow run](https://github.com/aliilyas/bruster/actions/runs/40782184966)
Measured 2026-10-28T22:49:45.365877+00:00; 10 sessions per configuration. Values are medians [min–max].
WebKitGTK 2.52.6 · Playwright 1.64.1 · Puppeteer 25.16.0 · agent-browser 0.40.0 · Google Chrome for Testing 156.0.8078.4 · Headless Shell Google Chrome for Testing 156.0.8078.4 · Node v26.13.0

Ubuntu 24.04.5 LTS · AMD EPYC 7763 64-Core Processor · 4 visible CPUs · 15.6 GiB RAM · runner image 20261026.354.1

| Metric | Bruster / WebKitGTK | Playwright / Headless Shell | Playwright / full Chrome | Puppeteer / full Chrome | agent-browser / full Chrome |
|---|---:|---:|---:|---:|---:|
| Launch → first loaded page (ms) | 230.8 [215.0–1226.4] | 595.8 [578.9–641.6] | 820.9 [803.1–855.6] | 621.0 [603.6–632.7] | 866.2 [839.7–920.3] |
| Startup → ready / blank-page setup (ms) | 106.1 [101.2–1015.6] | 575.5 [559.2–618.0] | 770.1 [750.5–789.6] | 581.9 [569.1–596.8] | 784.3 [764.9–831.7] |
| First navigation after setup (ms) | 123.2 [110.4–210.5] | 19.4 [18.8–22.1] | 45.3 [37.2–99.3] | 35.6 [30.9–42.7] | 81.2 [62.6–111.2] |
| Warm tiny-page navigation (ms) | 6.8 [4.6–14.1] | 12.1 [9.1–18.8] | 18.1 [14.6–42.6] | 21.4 [17.0–31.2] | 43.0 [25.5–98.0] |
| Tiny DOM extraction (ms) | 6.0 [1.0–8.4] | 3.6 [2.4–5.9] | 8.0 [3.4–19.0] | 6.6 [1.5–13.1] | 5.8 [3.6–19.5] |
| Large-page navigation (ms) | 53.6 [32.7–71.5] | 35.0 [22.8–57.7] | 41.7 [28.4–58.9] | 39.7 [35.5–47.1] | 87.1 [77.5–128.7] |
| Large DOM extraction, object return (ms) | 13.1 [5.1–25.4] | 104.3 [78.3–173.1] | 108.7 [79.1–155.5] | 30.6 [17.8–52.7] | 33.3 [27.4–46.7] |
| Large DOM extraction, JSON-string return (ms) | 14.3 [6.0–58.7] | 11.2 [8.5–36.6] | 16.4 [8.4–41.6] | 22.6 [8.3–45.6] | 13.3 [11.7–27.5] |
| Image-page navigation (ms) | 117.9 [112.7–124.5] | 119.6 [118.0–135.3] | 125.1 [121.3–141.0] | 127.1 [124.4–141.0] | 133.2 [128.0–142.8] |
| PNG screenshot (ms) | 39.7 [38.9–40.9] | 47.0 [42.2–58.5] | 50.1 [44.2–67.8] | 69.2 [53.3–89.4] | 65.7 [58.6–100.1] |
| Idle total PSS, including display (MiB) | 217.7 [216.5–219.4] | 324.7 [323.4–327.4] | 505.6 [504.4–507.5] | 418.6 [415.0–420.2] | 517.3 [512.6–520.2] |
| Idle process RSS, excluding display (MiB) | 344.3 [338.7–348.2] | 596.2 [591.0–599.0] | 1172.4 [1167.2–1174.9] | 1063.1 [1051.0–1067.8] | 1590.9 [1565.4–1600.1] |
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
  "started_utc": "2026-10-28T22:45:14.568333+00:00",
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
  "cpu_model": "AMD EPYC 7763 64-Core Processor",
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
  "bruster_sha256": "d01261cbfdaccd9ab87f702cc2a213d183a23feb39b065136190bd6e2a6dd5d4",
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
  "finished_utc": "2026-10-28T22:49:45.365877+00:00"
}
```
