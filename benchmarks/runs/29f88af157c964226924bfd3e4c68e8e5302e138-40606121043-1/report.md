# Browser comparison

Commit `29f88af157c964226924bfd3e4c68e8e5302e138` · [workflow run](https://github.com/aliilyas/bruster/actions/runs/40606121043)
Measured 2026-10-28T00:07:34.395056+00:00; 10 sessions per configuration. Values are medians [min–max].
WebKitGTK 2.52.6 · Playwright 1.64.1 · Puppeteer 25.16.0 · agent-browser 0.40.0 · Google Chrome for Testing 156.0.8078.4 · Headless Shell Google Chrome for Testing 156.0.8078.4 · Node v26.12.1

Ubuntu 24.04.5 LTS · AMD EPYC 9V45 96-Core Processor · 4 visible CPUs · 15.6 GiB RAM · runner image 20261026.354.1

| Metric | Bruster / WebKitGTK | Playwright / Headless Shell | Playwright / full Chrome | Puppeteer / full Chrome | agent-browser / full Chrome |
|---|---:|---:|---:|---:|---:|
| Launch → first loaded page (ms) | 674.5 [191.8–703.6] | 417.1 [396.9–455.9] | 592.2 [566.6–642.9] | 459.2 [430.6–1640.5] | 711.8 [652.9–779.4] |
| Startup → ready / blank-page setup (ms) | 116.7 [108.6–428.1] | 398.4 [380.2–440.6] | 546.3 [524.8–593.8] | 424.0 [402.1–542.8] | 633.4 [590.8–701.9] |
| First navigation after setup (ms) | 558.5 [74.4–591.4] | 16.5 [14.5–26.2] | 41.9 [33.8–57.9] | 32.3 [27.8–1212.7] | 77.5 [58.0–90.6] |
| Warm tiny-page navigation (ms) | 8.1 [3.6–12.6] | 9.2 [7.2–19.4] | 15.7 [12.1–36.1] | 18.2 [14.4–142.3] | 30.7 [18.6–79.3] |
| Tiny DOM extraction (ms) | 1.0 [0.7–5.8] | 2.7 [2.0–5.9] | 5.9 [2.5–15.4] | 4.6 [1.3–8.8] | 4.1 [2.9–18.0] |
| Large-page navigation (ms) | 23.2 [20.3–65.9] | 26.4 [17.2–37.6] | 32.6 [22.8–43.9] | 31.6 [26.8–36.1] | 67.9 [57.3–91.5] |
| Large DOM extraction, object return (ms) | 14.9 [10.9–28.9] | 71.3 [50.5–120.7] | 75.8 [52.5–124.5] | 24.9 [15.3–42.8] | 27.6 [23.5–39.8] |
| Large DOM extraction, JSON-string return (ms) | 14.4 [6.9–46.0] | 11.4 [6.0–26.3] | 11.9 [5.9–29.6] | 17.0 [6.2–33.5] | 10.1 [8.4–24.5] |
| Image-page navigation (ms) | 113.7 [110.4–122.0] | 115.4 [113.2–128.4] | 118.4 [115.8–133.0] | 122.1 [117.8–129.5] | 126.5 [122.7–132.9] |
| PNG screenshot (ms) | 23.8 [22.3–33.2] | 30.7 [28.5–51.3] | 36.2 [30.3–48.6] | 60.7 [39.9–71.5] | 65.5 [45.1–72.5] |
| Idle total PSS, including display (MiB) | 247.1 [243.7–249.5] | 324.2 [322.9–325.1] | 506.0 [503.9–508.0] | 419.0 [414.6–421.8] | 516.6 [511.6–518.7] |
| Idle process RSS, excluding display (MiB) | 367.2 [364.2–377.8] | 596.2 [591.6–597.4] | 1170.6 [1148.3–1177.5] | 1062.2 [1050.7–1069.4] | 1591.8 [1575.2–1621.3] |
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
  "started_utc": "2026-10-28T00:03:29.729987+00:00",
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
  "cpu_model": "AMD EPYC 9V45 96-Core Processor",
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
  "bruster_bytes": 1452824,
  "bruster_sha256": "7fe32d1b8566891f93807f1bccdd80eadfb458accd0c470704ba508dbbc15447",
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
  "finished_utc": "2026-10-28T00:07:34.395056+00:00"
}
```
