# Browser comparison

Commit `fb694ab4400bd4616525eb89d0dc716c31e2a52e` · [workflow run](https://github.com/aliilyas/bruster/actions/runs/40957570970)
Measured 2026-10-29T21:30:37.713996+00:00; 10 sessions per configuration. Values are medians [min–max].
WebKitGTK 2.52.6 · Playwright 1.64.1 · Puppeteer 25.16.0 · agent-browser 0.41.0 · Google Chrome for Testing 156.0.8078.4 · Headless Shell Google Chrome for Testing 156.0.8078.4 · Node v27.0.0-alpha.0.0.0

Ubuntu 24.04.5 LTS · AMD EPYC 7763 64-Core Processor · 4 visible CPUs · 15.6 GiB RAM · runner image 20261026.354.1

| Metric | Bruster / WebKitGTK | Playwright / Headless Shell | Playwright / full Chrome | Puppeteer / full Chrome | agent-browser / full Chrome |
|---|---:|---:|---:|---:|---:|
| Launch → first loaded page (ms) | 222.7 [218.7–970.1] | 588.5 [568.4–616.6] | 809.1 [777.4–819.0] | 603.3 [586.2–700.1] | 851.6 [772.5–882.9] |
| Startup → ready / blank-page setup (ms) | 104.3 [99.5–739.9] | 568.1 [550.3–596.8] | 760.5 [723.1–771.3] | 565.3 [544.7–657.2] | 770.0 [692.8–810.3] |
| First navigation after setup (ms) | 118.0 [106.4–229.5] | 18.4 [16.2–21.2] | 43.9 [37.0–57.0] | 38.5 [31.6–42.1] | 80.1 [59.1–93.3] |
| Warm tiny-page navigation (ms) | 6.8 [4.6–12.7] | 10.7 [8.8–17.0] | 20.0 [13.5–44.0] | 20.7 [16.5–32.3] | 40.0 [26.4–110.9] |
| Tiny DOM extraction (ms) | 5.9 [0.8–8.7] | 3.0 [2.3–7.8] | 7.3 [3.4–20.5] | 6.6 [1.5–11.1] | 4.9 [3.5–22.7] |
| Large-page navigation (ms) | 52.7 [48.2–71.2] | 34.3 [22.5–50.4] | 41.6 [28.4–55.2] | 39.8 [36.3–47.9] | 85.5 [76.1–105.9] |
| Large DOM extraction, object return (ms) | 17.5 [4.8–23.7] | 102.1 [75.7–137.5] | 107.7 [78.6–147.9] | 29.2 [18.7–64.6] | 31.3 [25.9–41.5] |
| Large DOM extraction, JSON-string return (ms) | 9.0 [5.5–24.2] | 10.1 [8.5–36.4] | 10.3 [8.4–39.8] | 21.5 [8.5–44.1] | 13.0 [11.2–22.3] |
| Image-page navigation (ms) | 114.6 [112.4–124.8] | 120.8 [117.8–134.8] | 124.8 [121.6–141.2] | 126.9 [121.8–132.6] | 131.8 [129.1–141.0] |
| PNG screenshot (ms) | 39.7 [38.9–46.7] | 47.1 [42.2–59.0] | 60.0 [44.9–69.9] | 79.1 [63.8–91.8] | 74.5 [53.6–100.2] |
| Idle total PSS, including display (MiB) | 218.9 [216.6–222.7] | 318.5 [317.0–319.6] | 498.6 [496.6–501.8] | 421.8 [418.4–423.1] | 514.8 [512.8–524.0] |
| Idle process RSS, excluding display (MiB) | 347.3 [343.7–347.8] | 591.0 [587.9–592.0] | 1164.9 [1155.5–1173.3] | 1065.8 [1054.9–1072.0] | 1589.4 [1557.9–1670.3] |
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
  "started_utc": "2026-10-29T21:26:08.352492+00:00",
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
  "finished_utc": "2026-10-29T21:30:37.713996+00:00"
}
```
