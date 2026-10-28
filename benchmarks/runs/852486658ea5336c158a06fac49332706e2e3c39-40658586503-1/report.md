# Browser comparison

Commit `852486658ea5336c158a06fac49332706e2e3c39` · [workflow run](https://github.com/aliilyas/bruster/actions/runs/40658586503)
Measured 2026-10-28T08:47:12.907968+00:00; 10 sessions per configuration. Values are medians [min–max].
WebKitGTK 2.52.6 · Playwright 1.64.1 · Puppeteer 25.16.0 · agent-browser 0.40.0 · Google Chrome for Testing 156.0.8078.4 · Headless Shell Google Chrome for Testing 156.0.8078.4 · Node v26.12.1

Ubuntu 24.04.5 LTS · AMD EPYC 7763 64-Core Processor · 4 visible CPUs · 15.6 GiB RAM · runner image 20261023.334.3

| Metric | Bruster / WebKitGTK | Playwright / Headless Shell | Playwright / full Chrome | Puppeteer / full Chrome | agent-browser / full Chrome |
|---|---:|---:|---:|---:|---:|
| Launch → first loaded page (ms) | 218.7 [212.3–1033.7] | 553.3 [543.8–564.0] | 759.9 [745.6–787.5] | 575.3 [563.5–598.2] | 799.2 [772.2–835.4] |
| Startup → ready / blank-page setup (ms) | 103.8 [99.2–795.8] | 534.0 [525.1–543.5] | 710.9 [698.4–749.7] | 539.8 [531.0–562.2] | 722.8 [701.1–752.4] |
| First navigation after setup (ms) | 114.5 [105.1–237.7] | 18.8 [17.3–22.3] | 47.5 [37.5–54.5] | 35.7 [32.1–39.4] | 79.1 [65.5–86.4] |
| Warm tiny-page navigation (ms) | 6.3 [4.5–13.5] | 11.1 [8.6–17.8] | 18.5 [14.0–38.2] | 19.4 [16.1–37.1] | 39.7 [23.0–103.0] |
| Tiny DOM extraction (ms) | 5.5 [0.8–7.8] | 3.2 [2.3–7.5] | 8.0 [3.4–21.3] | 6.5 [1.5–13.1] | 4.9 [3.3–29.0] |
| Large-page navigation (ms) | 49.6 [29.4–61.8] | 33.9 [22.2–47.0] | 42.2 [27.7–48.1] | 40.7 [35.8–46.6] | 81.4 [75.9–108.1] |
| Large DOM extraction, object return (ms) | 15.9 [5.0–23.0] | 101.2 [74.7–148.3] | 106.3 [77.3–155.2] | 30.5 [16.7–52.8] | 31.8 [26.8–47.1] |
| Large DOM extraction, JSON-string return (ms) | 12.8 [5.3–37.3] | 9.9 [8.4–35.2] | 24.3 [8.1–38.6] | 23.3 [8.2–42.3] | 13.0 [11.2–24.4] |
| Image-page navigation (ms) | 113.8 [112.0–122.8] | 118.5 [116.6–133.0] | 122.7 [121.1–139.7] | 127.2 [123.4–134.3] | 130.1 [127.6–137.8] |
| PNG screenshot (ms) | 39.9 [39.0–49.6] | 47.0 [40.6–58.2] | 49.4 [41.8–66.7] | 72.4 [47.5–91.8] | 72.7 [54.7–86.8] |
| Idle total PSS, including display (MiB) | 256.0 [252.5–258.0] | 328.4 [325.4–332.2] | 512.8 [510.7–517.0] | 421.5 [417.2–428.4] | 522.8 [516.1–532.3] |
| Idle process RSS, excluding display (MiB) | 379.3 [377.7–382.3] | 597.3 [593.7–601.4] | 1182.0 [1170.7–1189.5] | 1067.1 [1054.5–1078.1] | 1609.6 [1593.6–1697.4] |
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
  "started_utc": "2026-10-28T08:42:49.312107+00:00",
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
  "bruster_bytes": 1469152,
  "bruster_sha256": "914834712471a922de7ba8b7dee04e467978000a60579a3705a669a048819a1f",
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
  "finished_utc": "2026-10-28T08:47:12.907968+00:00"
}
```
