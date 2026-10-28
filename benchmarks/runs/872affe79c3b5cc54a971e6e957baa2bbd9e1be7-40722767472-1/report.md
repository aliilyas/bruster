# Browser comparison

Commit `872affe79c3b5cc54a971e6e957baa2bbd9e1be7` · [workflow run](https://github.com/aliilyas/bruster/actions/runs/40722767472)
Measured 2026-10-28T16:14:51.779868+00:00; 10 sessions per configuration. Values are medians [min–max].
WebKitGTK 2.52.6 · Playwright 1.64.1 · Puppeteer 25.16.0 · agent-browser 0.40.0 · Google Chrome for Testing 156.0.8078.4 · Headless Shell Google Chrome for Testing 156.0.8078.4 · Node v26.12.1

Ubuntu 24.04.5 LTS · AMD EPYC 7763 64-Core Processor · 4 visible CPUs · 15.6 GiB RAM · runner image 20261026.354.1

| Metric | Bruster / WebKitGTK | Playwright / Headless Shell | Playwright / full Chrome | Puppeteer / full Chrome | agent-browser / full Chrome |
|---|---:|---:|---:|---:|---:|
| Launch → first loaded page (ms) | 223.0 [216.1–1847.4] | 595.4 [589.7–606.2] | 814.0 [794.8–897.5] | 624.4 [609.4–708.5] | 866.9 [807.3–916.9] |
| Startup → ready / blank-page setup (ms) | 105.8 [99.8–1368.4] | 576.1 [568.5–587.6] | 773.1 [749.5–852.5] | 587.7 [572.6–663.4] | 782.0 [730.0–834.9] |
| First navigation after setup (ms) | 119.1 [111.6–478.6] | 18.5 [17.0–22.9] | 45.4 [36.7–60.6] | 36.0 [32.8–44.8] | 76.5 [67.4–92.2] |
| Warm tiny-page navigation (ms) | 6.7 [5.0–14.2] | 11.5 [9.3–16.2] | 18.9 [14.8–38.5] | 21.0 [16.2–36.5] | 39.5 [23.0–101.3] |
| Tiny DOM extraction (ms) | 5.8 [1.1–8.5] | 3.5 [2.4–7.4] | 8.2 [3.4–20.8] | 6.7 [1.2–12.3] | 6.1 [3.5–22.7] |
| Large-page navigation (ms) | 53.8 [31.9–70.3] | 35.0 [22.9–47.6] | 42.5 [29.2–55.4] | 41.2 [35.0–49.3] | 86.6 [76.6–118.6] |
| Large DOM extraction, object return (ms) | 17.5 [4.9–45.1] | 105.9 [78.5–150.9] | 111.2 [79.1–158.1] | 29.0 [17.2–59.6] | 32.9 [26.9–43.1] |
| Large DOM extraction, JSON-string return (ms) | 20.0 [5.7–42.8] | 10.5 [8.5–36.3] | 14.3 [8.6–42.3] | 21.9 [8.5–44.7] | 13.1 [11.6–31.0] |
| Image-page navigation (ms) | 117.4 [112.4–124.2] | 119.9 [117.3–136.8] | 124.8 [119.7–141.8] | 127.5 [124.0–136.3] | 132.4 [129.0–138.2] |
| PNG screenshot (ms) | 39.8 [39.0–48.0] | 47.7 [44.2–54.6] | 52.8 [42.4–67.8] | 69.8 [63.8–91.9] | 66.9 [55.9–86.6] |
| Idle total PSS, including display (MiB) | 221.1 [216.5–222.8] | 324.3 [323.0–326.8] | 507.4 [506.0–508.5] | 418.4 [413.9–420.9] | 516.1 [511.8–525.7] |
| Idle process RSS, excluding display (MiB) | 344.4 [343.8–348.0] | 596.0 [593.4–598.5] | 1174.9 [1172.5–1177.8] | 1065.3 [1049.4–1072.6] | 1589.8 [1575.8–1693.2] |
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
  "started_utc": "2026-10-28T16:10:19.905039+00:00",
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
  "bruster_bytes": 1469152,
  "bruster_sha256": "9ad469a9e51bec04561f0b9f248354ee394f97d29c3c4c9e4be016cac59180b0",
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
  "finished_utc": "2026-10-28T16:14:51.779868+00:00"
}
```
