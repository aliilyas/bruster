# Bruster versus browser-automation competitors

Date: **2026-10-27**. This is a same-machine Linux experiment, with retained raw
samples, pinned tool versions, and correctness checks. It follows the audit in
[`PERFORMANCE_REVIEW.md`](PERFORMANCE_REVIEW.md).

## Configurations

| Label | Tool / runtime | Browser |
|---|---|---|
| Bruster | 0.3.1, frozen Rust release executable | WebKitGTK 2.52.6, hidden window under Xvfb |
| Playwright — shell | playwright-core 1.64.1, Node 24.22.1 | Chrome Headless Shell 156.0.8078.4 |
| Playwright — full Chrome | playwright-core 1.64.1, Node 24.22.1 | Chrome for Testing 156.0.8078.4, headless |
| Puppeteer | puppeteer-core 25.16.0, Node 24.22.1 | Same full Chrome executable, headless |
| agent-browser | 0.39.4, native Linux Rust executable and daemon | Same full Chrome executable, headless |

The shell is Playwright's usual Chromium headless engine; the full-Chrome row
controls for browser choice against the other two Chromium tools. This avoids
presenting a full-Chrome-only comparison as Playwright's default headless cost.
The agent-browser version tested has a **native Rust daemon**, not a Node daemon.

Host: Ubuntu 26.04.1, Linux x86_64, four visible CPUs, AMD Ryzen 5 PRO 5650U,
approximately 3.82 GiB RAM. Chromium launches use `--no-sandbox` because this
host's namespace restrictions prevent its normal sandbox from starting.

## Measurement design

### Timings and equal work

- A persistent JSON-lines controller drives Bruster and thin public-API adapters
  for Playwright/Puppeteer. The adapters' Node startup and memory are included.
- agent-browser uses its native CLI and persistent daemon. Its command timings
  include the short-lived CLI process; they are not daemon-only timings.
- Every browser uses a **1280×800 viewport**, fresh HOME/XDG directories, and a
  fresh browser session. OS filesystem caches are not flushed.
- Startup is measured **from spawning the tool through completion of the first
  page load**. This avoids comparing Bruster's early `ready` event to a fully
  initialized Chromium page.
- There are ten measured sessions per configuration. Configuration order rotates
  between rounds. Known competing compiler/test/browser work is recorded so
  contaminated samples can be excluded and replaced.
- Each session performs ten warm tiny-page navigations and matching DOM
  extractions; five large-page navigations with both object-return and JSON-string
  DOM extraction; three image-page navigations; and two PNG screenshots.
- Every navigation waits for `load`. The server uses localhost HTTP and
  `Cache-Control: no-store`; public-network latency is outside these timings.
- A 250 ms server-delay check verifies that navigation timings correspond to the
  requested load. Returned URLs and `document.readyState` are checked.

The tiny page is the original benchmark's **143-byte HTML document**. The large
page contains **1,000 links and 1,000 inputs**, with 72,729 HTML bytes. The image
page has twelve 49,363-byte PNGs and a controlled 50 ms server delay per image.
All images must actually load, and screenshots must be valid 1280×800 PNGs.

The **same JavaScript extraction expression** runs in every engine. It collects
the same tags, visible layout boxes, accessible-label/text fallback, hrefs, and
input values. Every large result is checked for 2,000 elements and matching
content. Canonical result hashes allow cross-tool equality checks.

Two return formats are measured:

1. Returning the JavaScript object through the tool's normal evaluator.
2. Returning `JSON.stringify` of the same object, then decoding it in the
   controller. Object/string order alternates to reduce ordering effects.

This matters because library serialization can dominate large-result latency.
Native snapshots are also measured, but their structures and semantics differ:
Bruster returns a DOM-derived element list, Playwright an ARIA text snapshot,
Puppeteer an accessibility tree, and agent-browser a tree with references.
Their timings alone are not an equal-work ranking.

### Memory and process accounting

- Idle memory is sampled three times after two seconds of settling on the tiny
  page, following the common navigation/extraction workload.
- The Linux controller acts as a **child subreaper**, so detached agent-browser
  daemons and orphaned Chromium crash-reporting helpers remain attributable.
- All owned processes are counted, including the Node adapter where required.
- **PSS** apportions shared pages; summed RSS is also retained but double-counts
  sharing. PSS is the primary comparison metric.
- Bruster's required Xvfb server is included in its total PSS. Headless Chromium
  clients have DISPLAY removed and do not require that server.
- Page snapshots, image decoding, and screenshot workloads occur after the idle
  sample; the memory result describes the small-page idle workload, not a peak.
- Graceful shutdown is checked. Processes still alive after a two-second grace
  period are recorded before targeted cleanup.

### Identity and scope

Bruster's frozen executable is **1,453,480 bytes**, SHA-256:

```text
af8ae4251671f7f862f8e9bf561cea042e381f59847930178a2eae540b76e85d
```

Its source matches the previous performance audit and commit `165d4aaa`'s
application source. The working repository changed during the investigation;
subsequent fixes and their test results are identified separately below.
All comparison sessions use the frozen executable rather than a changing
`target/release/bruster`.

These workloads do not measure general website compatibility, complex SPAs,
media playback, WebGL, long sessions, or multi-tab scaling. Bruster disables
WebGL/media and uses synthetic DOM interactions; its capabilities are not
identical to Chromium automation. No universal performance winner follows from
these small local fixtures.

## Accepted performance results

**50 accepted sessions**, ten per configuration, from 52 executed sessions.
Playwright/full Chrome round 2 and Playwright/Shell round 1 overlapped another
Bruster process; they were excluded under the recorded contamination rule and
replaced independently of their performance. All accepted sessions produced
identical large-extraction hashes, complete memory samples, valid screenshots,
and no processes requiring forced cleanup.

Values below are medians. Startup and memory use ten session observations per
configuration; warm navigation/tiny extraction use 100 operations, large-page
workloads 50, image navigation 30, and screenshots 20. Memory first takes the
median of the three idle samples within each session.

| Metric | Bruster | Playwright shell | Playwright full | Puppeteer | agent-browser |
|---|---:|---:|---:|---:|---:|
| Launch through first loaded page, ms | **918** | 1,161 | 1,758 | 1,495 | 1,513 |
| Warm tiny navigation, ms | **16.2** | 17.7 | 31.0 | 30.8 | 50.6 |
| Tiny DOM extraction, ms | **3.7** | 6.2 | 11.9 | 9.6 | 9.4 |
| Large-page navigation, ms | 63.2 | **60.8** | 79.9 | 82.8 | 140.6 |
| Large DOM extraction, object return, ms | **37.6** | 176.7 | 202.7 | 61.2 | 57.8 |
| Large DOM extraction, JSON-string return, ms | 33.6 | 25.2 | **24.3** | 37.9 | 25.7 |
| Image-page navigation, ms | **130.9** | 150.6 | 155.1 | 168.5 | 166.3 |
| PNG screenshot, ms | **53.9** | 65.9 | 77.4 | 86.4 | 83.2 |
| Total idle PSS including required display, MiB | **250.2** | 322.1 | 498.9 | 402.1 | 505.2 |
| Process RSS excluding display, MiB | 387.0 | 561.9 | 1,097.4 | 896.6 | 1,491.2 |

Bruster had the lowest observed startup and idle memory medians here. Against
Playwright's normal Headless Shell configuration, its median total PSS was about
22% lower and launch-to-first-page about 21% shorter. Full Chrome costs more than
Headless Shell in this experiment. **Bruster was not fastest in every workload**:
JSON-string extraction reversed the object-return ranking, with Playwright and
agent-browser ahead. These are descriptive results from one host, not statistical
significance claims or universal application-performance predictions.

For context, launch-to-first-page ranges were 852–1,242 ms (Bruster),
1,026–1,481 ms (Playwright shell), 1,277–2,361 ms (Playwright full),
1,381–2,151 ms (Puppeteer), and 1,406–2,086 ms (agent-browser). The retained
`accepted-summary.json` includes every metric's count, minimum and maximum.

## Installed-file footprint

### Expanded runtime inventory used by automation

The workflow validation added **observed file-backed process mappings** to the
linked-library inventory. This matters: WebKit/Xvfb dynamically load Mesa and
LLVM, including approximately **138.6 MB of LLVM and 45.6 MB of Gallium**, which
the initial `ldd` inventory missed. Chromium also maps additional fonts and
libraries. Counting only linked files substantially understates deployment size.

The complete five-configuration automation validation used the post-fix Bruster
build and freshly resolved latest packages: Playwright 1.64.1, Puppeteer 25.16.0,
and **agent-browser 0.40.0**. Its expanded installed-file lower bounds were:

| Configuration | Runtime files including observed mappings |
|---|---:|
| Bruster + WebKit + Xvfb | **443.2 MB** |
| Playwright + Headless Shell + Node | **450.4 MB** |
| agent-browser native + full Chrome | **528.4 MB** |
| Playwright + full Chrome + Node | **652.7 MB** |
| Puppeteer + full Chrome + Node | **666.5 MB** |

These are a **different inventory scope and a newer application/agent-browser
build** than the frozen timing experiment above. They validate the automated
inventory, not a replacement ten-session timing study. In this expanded view,
Bruster's runtime-file footprint is close to Playwright/Headless Shell, despite
its much smaller controller executable. The continuous workflow uses this
expanded scope, resolves latest versions each run, and retains the exact file
inventory and versions.

### Initial linked-file subtotals (historical experiment)

The initial inventory includes the selected browser bundle, the tool's runtime code,
Node where needed, and linked native libraries, deduplicated by file identity.
It excludes package-manager caches, build tools, and unrelated platform binaries.
MB is decimal; these are **uncompressed installed files**, not download sizes.

| Configuration | Inventoried runtime files |
|---|---:|
| Bruster + WebKit helpers/libraries + Xvfb | **232.7 MB** |
| Playwright + Headless Shell + Node + libraries | **445.6 MB** |
| agent-browser native binary + full Chrome + libraries | **472.5 MB** |
| Playwright + full Chrome + Node + libraries | **597.4 MB** |
| Puppeteer + full Chrome + Node + libraries | **610.7 MB** |

Relevant components:

| Component | Size |
|---|---:|
| Bruster executable | 1.453 MB |
| agent-browser Linux executable | 18.408 MB |
| Node executable | 126.880 MB |
| Full Chrome downloaded directory | 420.922 MB |
| Headless Shell downloaded directory | 285.085 MB |
| Playwright runtime package | 13.656 MB |
| Puppeteer and its runtime package dependencies | 26.986 MB |

Fonts, dynamically loaded OS plugins, and other system resources can add more,
so these older subtotals are **lower bounds, not complete deployment footprints**;
the expanded inventory above demonstrates the difference. Shared
system libraries or an existing compatible browser can reduce the incremental
installation cost. Optional video tooling such as FFmpeg is not included.
agent-browser's unrelated macOS/Windows/ARM binaries in its npm distribution are
excluded from its Linux runtime total; Node is not needed for the native binary
used here.

## Failure investigation

### Bruster functional suite

The first broad run against the frozen application build produced:

| Check | Result |
|---|---|
| Release build | Passed |
| Unit tests | 5 passed |
| Smoke tests | 30 passed |
| Edge tests | 18 passed, 1 failed |
| Public-site end-to-end tests | 10 passed |
| MCP launch | Passed |
| TypeScript MCP SDK | Passed, 43 tools |
| Python MCP SDK | Passed, 43 tools |
| MCP Inspector tools/list and tools/call | Both passed |
| Live descendants left by the suite | None |

The failing edge test was
`duplicate_load_does_not_release_requests_for_the_next_page`, which timed out
waiting for a protocol message. This regression test was being added in the
working tree while the review ran. A targeted rerun passed after the application
changed to binary SHA-256
`b03b81fac49ba9d33d66f93c02b324df33a68491062d6e9e05eb3fc5fa8bc8d5`.
That is a **different build**, not evidence that the original failure vanished
on an unchanged retry.

The subsequent commit `b10f8a368f9bd4bd1525a63dccdb34ff9f4e71e1`,
“Synchronize load and history completion across platforms,” moves duplicate-load
rejection ahead of request-release handling, adds Windows history-event
synchronization, and adjusts the Wikipedia test for collapsed search UI.

A complete local post-fix rerun then passed: release build, **5 unit tests,
30 smoke tests, all 19 edge tests, MCP launch, and all 10 public-site E2E tests**.
No live descendants remained. This run ended with executable SHA-256
`f3ae4e3731b3d845aa7468a1504677b2801b21c2ad2030c3a4105ab1a1b79a5f`.
These passing results apply to the post-fix build; the numerical comparison above
continues to identify its original frozen build explicitly.

### GitHub CI evidence

The completed CI run for `165d4aaa` failed:

<https://github.com/aliilyas/bruster/actions/runs/40585900199>

- **Intel macOS:** “Smoke and edge tests (macOS)” failed with exit code 101.
- **Windows public-site E2E:** “Public-site tests (Windows)” failed with exit code 1.
- Linux x86_64/ARM64, ARM macOS, the Windows build job, Linux public-site E2E,
  and MCP integrations succeeded.

The public API exposed job/step results and annotations, but downloading the
detailed logs returned HTTP 403. Exact failing assertions in those two jobs
were therefore not independently verified here. The newer CI run for
`b10f8a3` also completed with failures in the same Intel macOS smoke/edge and
Windows public-site E2E steps; the other build/test jobs succeeded. The successful
local Linux rerun does not establish that those cross-platform failures are fixed:

<https://github.com/aliilyas/bruster/actions/runs/40588684288>

### Controlled cross-tool fault probes

After timing measurements, each session checks JavaScript exceptions, syntax
errors, recovery with another evaluation, refused-connection navigation, and
immediate subsequent navigation to a healthy local page. Failures are retained;
they do not silently disappear through retries.

All **20 accepted Playwright sessions** (ten full Chrome, ten Shell) exposed a
recovery race: after a refused connection, immediately calling `page.goto` for a healthy page was interrupted by the
previous navigation's `chrome-error://chromewebdata/` load. A separately recorded
100 ms delayed retry recovered in every case. Bruster, Puppeteer and agent-browser
had no fault-probe failures in the accepted sessions. This describes that particular recovery sequence,
not a failure to navigate ordinary healthy pages.

## Reproduction and evidence

Harness files:

- `scripts/bench_compare.py`
- `scripts/bench_competitor_driver.mjs`
- `scripts/bench_audit.py` (shared fixtures and protocol helpers)

Install the pinned packages into an isolated directory:

These versions reproduce this **historical experiment**. The new
[`benchmarks` workflow](.github/workflows/benchmarks.yml) instead resolves the
latest stable competitor releases on every merge and archives its generated
lockfile. See [`benchmarks/README.md`](benchmarks/README.md) for continuous
publication and latest-version local execution.

```sh
npm install --prefix /tmp/opencode/bruster-competitors \
  playwright-core@1.64.1 puppeteer-core@25.16.0 agent-browser@0.39.4
```

Use Playwright's CLI to install `chromium --no-shell` and
`chromium-headless-shell` with `PLAYWRIGHT_BROWSERS_PATH` pointing at a dedicated
browser directory. Pass the resulting full-Chrome and headless-shell executables
explicitly:

```sh
xvfb-run -a python3 scripts/bench_compare.py \
  --bruster /path/to/frozen/bruster \
  --node /path/to/node \
  --chrome /path/to/chrome-linux64/chrome \
  --shell /path/to/chrome-headless-shell-linux64/chrome-headless-shell \
  --deps /tmp/opencode/bruster-competitors \
  --output /tmp/opencode/bruster-comparison-results \
  --rounds 10 --iterations 10
```

This machine's evidence directory:

```text
/home/admin/Projects/.bruster-build/competitor-review-2026-10-27/
```

It contains the exact npm lockfile, browser executables, frozen harness copies,
raw timing/process samples, native snapshot outputs, screenshots, footprint
inventory, functional-test logs, and captured GitHub CI metadata.
The later automation-validation evidence is retained under
`/tmp/opencode/bruster-benchmark-validation/`, including the expanded runtime
inventory and generated report/site preview.
