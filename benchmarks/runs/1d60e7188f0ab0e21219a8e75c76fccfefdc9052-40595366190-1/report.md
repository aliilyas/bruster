# Browser comparison

Commit `1d60e7188f0ab0e21219a8e75c76fccfefdc9052` · [workflow run](https://github.com/aliilyas/bruster/actions/runs/40595366190)
Measured 2026-10-27T22:41:51.009959+00:00; 10 sessions per configuration. Values are medians.
Playwright 1.64.1 · Puppeteer 25.16.0 · agent-browser 0.40.0 · Google Chrome for Testing 156.0.8078.4 · Node v26.12.1

| Metric | Bruster / WebKitGTK | Playwright / Headless Shell | Playwright / full Chrome | Puppeteer / full Chrome | agent-browser / full Chrome |
|---|---:|---:|---:|---:|---:|
| Launch → first loaded page (ms) | 30707.8 | 451.3 | 628.7 | 473.3 | 714.2 |
| Warm tiny-page navigation (ms) | 7.3 | 8.6 | 14.4 | 16.0 | 31.4 |
| Tiny DOM extraction (ms) | 0.8 | 2.7 | 6.2 | 2.3 | 4.8 |
| Large-page navigation (ms) | 24.5 | 27.7 | 33.4 | 32.6 | 66.0 |
| Large DOM extraction, object return (ms) | 15.1 | 80.1 | 84.0 | 23.7 | 26.2 |
| Large DOM extraction, JSON-string return (ms) | 15.2 | 8.4 | 12.7 | 17.5 | 10.6 |
| Image-page navigation (ms) | 114.2 | 114.6 | 118.2 | 119.8 | 125.2 |
| PNG screenshot (ms) | 29.0 | 31.5 | 40.3 | 64.3 | 58.1 |
| Idle total PSS, including display (MiB) | 250.8 | 324.7 | 507.6 | 418.8 | 516.8 |
| Idle process RSS, excluding display (MiB) | 371.9 | 597.3 | 1174.0 | 1064.3 | 1589.7 |
| Installed runtime files, lower bound (MB) | 427.9 | 475.5 | 630.8 | 644.7 | 483.2 |
| Sessions with fault-probe failures | 0/10 | 10/10 | 10/10 | 0/10 | 0/10 |

Ten sessions per configuration by default, with rotating order and fresh browser profiles. 1280×800 viewport; localhost fixtures; no-store HTTP responses; navigation waits for load. OS filesystem caches are not flushed. Identical extraction JavaScript and cross-tool result hashes. Timings include controller round trips; agent-browser includes its per-command native CLI. Memory covers the complete owned process forest (including detached daemons and helpers), plus Xvfb for Bruster. PSS apportions shared pages; summed RSS double-counts them. Memory is small-page idle usage, not peak usage. Native snapshots have different semantics and are retained in the raw artifacts rather than ranked as equal work. MB = 1,000,000 bytes; MiB = 1,048,576 bytes. Installed-file inventories are lower bounds including browser/engine, linked libraries, observed mapped files and Node where required; unobserved OS resources may add more. GitHub-hosted runner hardware and OS packages can change: compare the configurations within a run and inspect provenance before interpreting trends.

## Fault probes

- Bruster / WebKitGTK: {}; successful 100 ms recovery retries: 0.
- Playwright / Headless Shell: {"recovery_after_navigation_error": 10}; successful 100 ms recovery retries: 10.
- Playwright / full Chrome: {"recovery_after_navigation_error": 10}; successful 100 ms recovery retries: 10.
- Puppeteer / full Chrome: {}; successful 100 ms recovery retries: 0.
- agent-browser / full Chrome: {}; successful 100 ms recovery retries: 0.

## Provenance

```json
{
  "started_utc": "2026-10-27T22:32:51.970062+00:00",
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
  "cpu_model": "AMD EPYC 9V74 80-Core Processor",
  "mem_total_kib": 16367524,
  "runner_image": {
    "ImageOS": "ubuntu24",
    "ImageVersion": "20261026.354.1",
    "RUNNER_ARCH": "X64"
  },
  "rustc": "rustc 1.99.1 (58cf8f9c3 2026-10-13)",
  "webkitgtk": "2.52.6",
  "packages": {
    "playwright-core": "1.64.1",
    "puppeteer-core": "25.16.0",
    "agent-browser": "0.40.0"
  },
  "bruster_bytes": 1455632,
  "bruster_sha256": "48adb34cc3956a14fb05c4b614387dbc8fd90b623b22c3bc0f299a6ae234dc3b",
  "chrome_sha256": "377a9fc07b495c3b8d0ab8ec1fdfd153641759f9756fea34d8dfce4de82f5025",
  "headless_shell_sha256": "4fa61f0ba0b4f89b7bec242c32ca16d3bccf69dbfef0651924a9ba8fede5f9d6",
  "rounds": 10,
  "iterations": 10,
  "common_extraction_js": "(() => ({\n  title: document.title,\n  elements: Array.from(document.querySelectorAll('h1,h2,h3,p,li,a,input,button,select,textarea'))\n    .filter(e => { const r = e.getBoundingClientRect(); return r.width > 0 && r.height > 0; })\n    .map(e => ({tag: e.tagName.toLowerCase(),\n      name: (e.getAttribute('aria-label') || e.getAttribute('placeholder') || e.textContent || '').trim(),\n      href: e.getAttribute('href'), value: 'value' in e ? e.value : null}))\n}))()",
  "harness_sha256": {
    "bench_compare.py": "f1476d7cf9f694d55356c6212549680f001471b55c5f91df36447465fc82bedb",
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
  "finished_utc": "2026-10-27T22:41:51.009959+00:00"
}
```
