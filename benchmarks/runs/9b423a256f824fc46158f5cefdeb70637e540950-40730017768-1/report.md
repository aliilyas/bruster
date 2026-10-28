# Browser comparison

Commit `9b423a256f824fc46158f5cefdeb70637e540950` · [workflow run](https://github.com/aliilyas/bruster/actions/runs/40730017768)
Measured 2026-10-28T16:56:51.324769+00:00; 10 sessions per configuration. Values are medians [min–max].
WebKitGTK 2.52.6 · Playwright 1.64.1 · Puppeteer 25.16.0 · agent-browser 0.40.0 · Google Chrome for Testing 156.0.8078.4 · Headless Shell Google Chrome for Testing 156.0.8078.4 · Node v26.12.1

Ubuntu 24.04.5 LTS · INTEL(R) XEON(R) PLATINUM 8573C · 4 visible CPUs · 15.6 GiB RAM · runner image 20261026.354.1

| Metric | Bruster / WebKitGTK | Playwright / Headless Shell | Playwright / full Chrome | Puppeteer / full Chrome | agent-browser / full Chrome |
|---|---:|---:|---:|---:|---:|
| Launch → first loaded page (ms) | 194.5 [178.0–805.4] | 501.7 [467.3–519.5] | 696.5 [654.5–757.9] | 517.0 [462.9–539.4] | 765.5 [730.6–813.1] |
| Startup → ready / blank-page setup (ms) | 94.1 [90.3–697.1] | 483.4 [451.9–501.2] | 653.3 [615.6–731.8] | 488.4 [438.1–509.1] | 690.7 [667.8–725.1] |
| First navigation after setup (ms) | 98.9 [86.1–113.5] | 15.9 [15.2–19.8] | 36.5 [25.7–59.2] | 28.9 [24.5–33.1] | 73.5 [61.9–92.4] |
| Warm tiny-page navigation (ms) | 5.3 [4.1–10.9] | 9.8 [7.5–13.9] | 18.6 [11.3–34.2] | 17.7 [13.9–29.6] | 33.9 [19.5–91.0] |
| Tiny DOM extraction (ms) | 4.2 [0.6–6.9] | 3.1 [2.2–6.0] | 7.1 [2.6–17.6] | 5.6 [1.3–13.0] | 4.7 [2.6–25.9] |
| Large-page navigation (ms) | 37.8 [32.8–46.0] | 30.4 [20.8–44.3] | 38.3 [27.6–44.4] | 36.8 [32.9–41.3] | 73.2 [64.9–91.2] |
| Large DOM extraction, object return (ms) | 6.5 [4.5–18.9] | 94.8 [68.5–144.2] | 97.5 [70.0–142.4] | 26.6 [14.7–45.7] | 27.8 [23.1–42.6] |
| Large DOM extraction, JSON-string return (ms) | 14.7 [4.6–19.5] | 8.6 [6.5–30.7] | 17.4 [6.3–33.5] | 19.3 [6.5–38.1] | 11.1 [8.9–22.6] |
| Image-page navigation (ms) | 113.7 [110.9–121.9] | 118.5 [116.0–130.8] | 121.8 [119.3–137.4] | 125.4 [122.4–132.7] | 130.2 [125.4–138.8] |
| PNG screenshot (ms) | 30.3 [26.6–32.3] | 38.1 [28.7–48.8] | 49.0 [29.3–62.3] | 65.0 [48.8–82.9] | 65.6 [48.9–81.7] |
| Idle total PSS, including display (MiB) | 219.5 [216.5–222.0] | 324.3 [323.8–325.9] | 505.4 [504.3–506.7] | 419.6 [415.8–420.3] | 515.5 [511.9–526.3] |
| Idle process RSS, excluding display (MiB) | 344.4 [338.9–347.9] | 596.7 [590.8–600.6] | 1173.6 [1152.1–1176.0] | 1067.1 [1052.9–1068.4] | 1592.3 [1571.0–1691.3] |
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
  "started_utc": "2026-10-28T16:52:43.380077+00:00",
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
  "cpu_model": "INTEL(R) XEON(R) PLATINUM 8573C",
  "mem_total_kib": 16366512,
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
  "finished_utc": "2026-10-28T16:56:51.324769+00:00"
}
```
