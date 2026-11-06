# Navigation and performance fixes

Implementation worktree: `performance-navigation`, originally on
`fix/performance-navigation` based on `9446519` (v0.3.2). This report is published
from `docs/navigation-performance-evidence`, based on November 6 `main` at
`d0440d6`. The earlier deep-dive worktree and its measurements are preserved.

The main changes were merged through [PR #8](https://github.com/aliilyas/bruster/pull/8).
The queued Windows start fix and benchmark guards were merged through
[PR #10](https://github.com/aliilyas/bruster/pull/10).
The remaining history acknowledgment fix was merged through
[PR #11](https://github.com/aliilyas/bruster/pull/11).
The baseline is `9446519`; the final candidate source is `d4c56d9` (identical
runtime files to the frozen build from `e1deba7`, before moving onto merged main).
These measurements isolate that implementation series; subsequent changes on
`main` have their own [optimization](optimizations.md) and
[memory](../docs/memory-audit.md) reports.

## Completed paired measurements

Measured November 5, 2026, **21:25:04–21:26:59 UTC**, on Ubuntu 26.04.1,
AMD Ryzen 5 PRO 5650U (four visible CPUs), 3.8 GiB RAM, WebKitGTK 2.52.6 and
GTK 3.24.52. Both frozen builds use the same runtime overlay. Values below
are **median [observed minimum–maximum]**; ranges are not confidence intervals.
All 54 paired sessions passed, with no recorded competing workload or forced
cleanup. These completed measurements are retained across the later server
restarts and competitor-comparison retries.

| Metric | Baseline `9446519` | Candidate `d4c56d9` | Median change |
|---|---:|---:|---:|
| Launch → loaded first page, including automatic Xvfb (ms) | 890.77 [872.82–918.90] | 302.27 [293.91–341.60] | −66.1% |
| Startup → ready (ms) | 265.48 [254.13–291.30] | 176.35 [165.08–194.30] | −33.6% |
| First navigation after ready (ms) | 622.80 [613.71–633.69] | 129.89 [120.76–155.64] | −79.1% |
| Warm tiny-page navigation (ms) | 12.08 [8.53–17.06] | 12.41 [7.96–18.97] | +2.7% |
| Large-page/screenshot workload, complete-process PSS (MiB) | 278.52 [277.49–279.92] | 239.72 [238.82–243.19] | −13.9% |
| Large-page PNG screenshot (ms) | 42.89 [40.14–43.73] | 32.64 [30.89–41.55] | −23.9% |
| Live 2,000-element extraction, object return (ms) | 7.96 [6.06–11.26] | 5.49 [4.60–7.76] | −31.0% |
| Live extraction, JSON-string return (ms) | 6.60 [5.49–8.76] | 5.79 [4.82–9.72] | −12.4% |
| Cached-object transport (ms) | 2.97 [2.49–4.12] | 1.65 [1.27–6.81] | −44.3% |
| Cached JSON-string transport (ms) | 2.90 [2.42–4.65] | 2.31 [1.70–4.83] | −20.4% |
| Ten-copy cached-object stress transport (ms) | 28.30 [25.20–37.66] | 11.93 [10.28–14.31] | −57.9% |

Startup has 20 alternating pairs; warm navigation pools five operations per
session (100 per build). Graphics has three pairs, using each session's median
of three complete PSS readings. Transport has three pairs, with three warm-up
calls discarded by the prespecified harness and 15 measured calls per format
per session (45 per build). Every returned extraction is checked for equality.
Warm navigation shows no improvement in this run; its ranges substantially
overlap. These are measurements of the complete fix series, not isolated causal
estimates for each individual change.

The single 200-navigation deadline burst shows bounded parent threads:

| Completed navigations | 0 | 50 | 100 | 150 | 200 |
|---|---:|---:|---:|---:|---:|
| Baseline parent threads | 24 | 74 | 124 | 174 | 224 |
| Candidate parent threads | 18 | 18 | 18 | 18 | 18 |

The burst completes before the old per-navigation sleeping deadlines expire;
the separate regression suite checks deadline cancellation, timeouts and tab
closure. Thread counts refer to the parent; memory figures cover the complete
browser forest, including WebKit helpers and automatic Xvfb.

## Latest-version competitor comparison

Measured on the same machine on **November 6, 00:39:30–00:42:07 UTC**, after
a fresh quiet interval and registry verification at 00:39:02 UTC. There are
five fresh sessions per configuration, with rotating order. Packages are
**Playwright 1.65.0, Puppeteer 25.16.0 and agent-browser 0.41.2**; full Chrome
and Headless Shell both use **157.0.8103.38**. Node is 24.22.1.

| Configuration | Launch → page (ms) | Warm tiny navigation (ms) | Large extraction, object (ms) | Idle total PSS (MiB) | Installed runtime (MB) |
|---|---:|---:|---:|---:|---:|
| Bruster `d4c56d9` / WebKitGTK | 284.55 [220.95–359.59] | 6.20 [4.66–12.58] | 16.92 [4.95–21.87] | 215.51 [213.64–216.03] | 442.47 |
| Playwright / full Chrome | 1114.83 [1084.13–1496.27] | 16.93 [12.92–24.76] | 111.76 [81.37–178.89] | 473.54 [457.65–475.49] | 655.81 |
| Puppeteer / full Chrome | 1494.02 [1378.86–1595.92] | 15.68 [12.89–20.63] | 27.12 [17.86–49.35] | 407.99 [405.80–410.97] | 672.88 |
| agent-browser / full Chrome | 4075.86 [3963.61–4122.02] | 23.12 [18.18–32.47] | 30.96 [24.40–39.65] | 483.54 [482.48–484.81] | 535.33 |
| Playwright / Headless Shell | 992.77 [860.86–1102.00] | 11.55 [8.49–16.35] | 105.42 [77.86–167.57] | 320.47 [318.67–323.27] | 455.50 |

Timings are medians [min–max], including controller round trips and, for
agent-browser, every native CLI launch. Warm navigation pools 50 operations
per configuration; large extraction pools 25. All configurations execute the
same extraction JavaScript, return all 2,000 elements and produce the same
result hash. Native snapshots have different semantics and remain in the raw
evidence rather than being ranked as equivalent work.

Unlike the paired startup probe, this comparison starts Xvfb beforehand:
**display launch time is excluded, but its full PSS is included for Bruster**.
Memory is small-page idle usage, taking the median of three readings per
session; it is not peak usage. Every owned browser, renderer, network helper,
daemon, crashpad helper and required Node adapter is counted. The Python
measurement controller and unrelated idle OS/search helpers are outside the
tool process forest.

The subsequent five-session baseline-only comparison measured 766.53
[761.01–858.33] ms launch-to-page and 254.55 [251.52–255.57] MiB idle PSS.
It corroborates the paired result but is a separate, non-alternating cohort.
Its prestarted Xvfb uses the original GLX default; the candidate's display uses
`-extension GLX`, matching the respective automatic hidden-display defaults.

### Runtime dependencies and fault probes

Installed sizes are deduplicated logical bytes, **lower bounds rather than
downloads or full OS images** (MB = 1,000,000 bytes; MiB = 1,048,576 bytes).
Bruster's executable is only 1.47 MB, but the measured runtime is **442.47 MB
across 242 files**, including WebKit helpers, Xvfb/display tools, linked libraries
and observed mapped files. The baseline inventory is 443.17 MB across 247 files.
Both still require **138.57 MB of LLVM and 45.62 MB of Gallium**; resident-memory
savings do not imply removing those installation dependencies. Chromium bundles,
tool packages, linked libraries and Node where required are included for the
competitors.

All 30 final comparison sessions have complete process accounting, no detected
overlaps and no forced cleanup. Fault probes run after timed workloads:

| Configuration | Sessions with fault-probe failures | Successful delayed recovery retries |
|---|---:|---:|
| Bruster candidate | 0/5 | Not needed |
| Bruster baseline | 0/5 | Not needed |
| Playwright / full Chrome | 5/5 | 5/5 |
| Playwright / Headless Shell | 5/5 | 5/5 |
| Puppeteer | 0/5 | Not needed |
| agent-browser | 0/5 | Not needed |

Both Playwright configurations failed immediate recovery after a refused
navigation: the new navigation was interrupted by `chrome-error://chromewebdata/`.
Every bounded retry after 100 ms succeeded. Initial failures remain counted;
these sessions are not described as universally passing.

## Implementation

- **Navigation identity:** explicit intent advances before native calls. Native
  provisional starts and commits bind runtime milestones to a document and
  generation. Late cancellations, duplicate load/idle messages, and queued
  flushes cannot complete a replacement navigation just because its URL matches.
  macOS also checks the native `WKNavigation` object; Windows observes native
  `NavigationId` on start, commit, and completion, including the initial blank
  warm-up. WebView2 can start its replacement before completing that blank,
  unlike GTK's retiring-load ordering. HTTP redirects keep their native ID.
  Native calls are serialized only until `NavigationStarting` acknowledges each
  call, associating its ID with the generation that dispatched it. Replacements
  received in that interval coalesce to the newest command; retired starts are
  cancelled. Same-document history releases the slot only after the native
  history flags and `popstate` acknowledge the call; same-URL history entries
  have neither `NavigationStarting` nor `SourceChanged`.
  Page replies and eval compilation callbacks carry a dispatch attempt, preventing an old callback
  from answering a redispatched request.
  The runtime's initial document announcement retries a commit-time bind that
  arrived before runtime installation; a deterministic regression reproduces
  the missing-bind timeout in the earlier build.
- **Hidden Linux painting:** mapped off-screen windows skip their unused GTK
  `draw` handler. WebKit's native snapshot API still renders the page. Unlike the
  research gate, this does not resume painting at `Finished`, which can precede
  backing-store availability and still incur the synchronous 500 ms wait.
- **Graphics:** hidden software rendering defaults to
  `WEBKIT_DISABLE_DMABUF_RENDERER=1`; automatic Xvfb starts without GLX. Existing
  environment settings take precedence. `BRUSTER_PAINT_HIDDEN=1` and
  `BRUSTER_XVFB_ARGS` provide explicit overrides. No Skia/EGL-vendor workaround
  is required.
- **Deadlines:** navigation, history fallback, and page IPC share one
  reschedulable worker. Completed/superseded/closed requests cancel their
  deadlines. Timeout events identify the waiting command independently of
  document changes. User-supplied durations use checked deadlines.
- **Transport:** a strict borrowed `RawValue` envelope validates native results
  and forwards them without allocating and reserializing a result tree. Error,
  event, and MCP formatting retain the regular conversion path. All output uses
  a buffered, immediately flushed record under one stdout lock. Custom multiline
  JSON falls back to normal serialization to preserve JSON-lines framing.

## Regression coverage

The regression suite covers queued and already-started same-URL replacements,
duplicate load messages, old-document idle messages, stale dispatch attempts,
timeouts/supersession, redirects, history, downloads, interrupted page calls,
initial blank-page calls, and tab closure. A state-machine regression checks a
timeout queued before a document change and a replacement reusing the public ID.
Windows also has an interleaved warm-up/replacement/redirect identity regression.
Queued native starts and pre-start timeouts have deterministic state regressions;
Windows CI repeats the two same-URL replacement cases and same-document history
checks five times.

The Linux thread regression completes 48 navigations plus reloads and new tabs
with 120-second deadlines, then verifies bounded parent threads and a working
200 ms timeout. The screenshot regression checks red and blue canvas pixels
drawn through `requestAnimationFrame`, both on the initial blank and a loaded
page. Existing viewport, clipped and tall/full-page screenshots also run.

Native and MCP tests cover null, scalars, nested objects, escaped Unicode,
large strings, errors, stale navigation hints and output framing. The stalled
portal regression and real TypeScript SDK, Python SDK and Inspector checks
exercise startup and MCP integration.

Local validation: **6 unit, 24 edge, and 32 smoke tests passed** after the
document-announcement fix. The public-site suite also passed all 10 tests.
Both macOS architectures and Windows passed cross-target compilation checks.
Native cross-platform execution and its retained failure history are linked
from [PR #8](https://github.com/aliilyas/bruster/pull/8).

The initial CI run exposed WebView2 warm-up ordering. Its follow-up passed
Windows fixtures/public sites and both macOS architectures, but reproduced
the Linux binding race on ARM. Both failures led to implementation fixes and
regressions; the original failing logs are retained.
The subsequent run passed both Linux architectures, both macOS targets, MCP,
and both public-site suites; its Windows queued-start failure led to the native
call acknowledgment gate described above.
That gate's first native run passed the replacement races and exposed the
missing same-URL history acknowledgment, now handled by the existing two-part
history handshake. Its failing log is also retained.

**[Final source CI is green](https://github.com/aliilyas/bruster/actions/runs/40659153121)**
at `d4c56d9`:

| Platform | Unit | Edge | Smoke | Additional coverage |
|---|---:|---:|---:|---|
| Linux x86_64 | 6 | 24 | 32 | Portal, MCP launch, 10 public-site tests |
| Linux ARM64 | 6 | 24 | 32 | Portal, MCP launch |
| macOS ARM64 | 6 | 22 | 27 | Four navigation regressions × 10 rounds, MCP launch |
| macOS Intel under Rosetta | 6 | 22 | 27 | Four navigation regressions × 10 rounds, MCP launch |
| Windows x86_64 | 10 | 22 | 27 | Three navigation/history regressions × 5 rounds, 9 public-site tests |

Counts are passed tests; macOS/Windows skip one Linux-specific edge test and
three inapplicable smoke tests. The separate MCP SDK/Inspector job also passes.
The first public-site attempt received DuckDuckGo's explicit “No results found
for webkitgtk” response on both runners. Both affected jobs passed on the single
retry without assertion changes; the failing attempt and retry logs are retained.

## Measurement provenance and validity

Frozen Linux executables (SHA-256):

| Build | Source revision | SHA-256 |
|---|---|---|
| Baseline | `9446519` | `e41dcaf1506d320f55458b053b41d324d5870136b08bd082a8ebadfeea5fb7d5` |
| Final candidate | `e1deba7` / `d4c56d9` | `0bda5deb9f950ff8390e7bdaa7bb4dda0578fbe19270b1fa220a67568f72ac53` |

The first implementation batch used `5873f49` and remains historical evidence.
The second batch in `final/` is excluded from final performance claims:
its startup probe records another Bruster process in nine samples, and its
competitor comparison overlaps the separate website campaign. The narrower
process detector then in use could miss other engines. The entire batch is
retained; no samples are silently removed to improve a median.

The expanded guard checks live frozen-build names, WebKit/Chromium helpers,
Node, agent-browser, and benchmark controllers between browser sessions.
It also recognizes Node's observed `MainThread` process name, covered by a live
process regression. The first completed November batch is retained as
`clean-pre-node-guard-2026-11-05/` and superseded in full by the rerun with this
additional detection.
It rejects a preexisting workload and records overlaps detected at measurement
checkpoints. Per-sample UTC timestamps support subsequent overlap audits.
The original three guard regressions and nine benchmark/publication tests
passed. The November 5 frozen harness also passes **4 concurrency, 3 runtime
inventory and 12 publication tests**, including the ownership-snapshot race.

The clean rerun records the external campaign's 1,000/1,000 primary-domain
progress, absence of its final completion marker, and two quiet minutes of
read-only process checks. The cancelled October preparation contains no browser
samples. The rerun rechecks current npm versions and freezes the harness from
November 5 `main` (`53be142`), including its process-ownership snapshot race fix.
One archived local harness patch recognizes the existing sleeping
`/usr/bin/xscreensaver` desktop controller, its idle systemd helper, and idle
OpenCode OpenSERP stdio servers. Their real executables and, for search servers,
exact command lines are verified on the host, then pinned by PID and kernel
start time inside the measurement sandbox. Sleeping state, no unapproved descendants and
a CPU budget of 0.05 seconds plus 0.5% of elapsed wall time are required at each
check. Other detected workloads still reject a sample. The scheduling and
validation records preserve these helpers' identities and CPU counters. The first
November attempt rejected all launches because sandboxed executable paths were
unreadable; those rows remain in `clean-rejected-2026-11-05/`.
The subsequent restart interrupted a quiet wait before any browser launched;
its 524 checks, including real Firefox/build activity, remain in
`clean-restart-wait-2026-11-05/`. In the final batch, the first comparison
overlapped a new Cargo build in its last session; the next stopped when external
WebKit processes appeared after ten sessions. Both attempts are retained and
excluded in full as `compare-candidate-overlap*`. The completed paired probes
were preserved, and only comparisons were repeated. The final wait recorded
175 process checks before its quiet interval; validation completed November 6
at 00:42:41 UTC.

The paired startup results include automatic display launch. The competitor
comparison uses an already-running Xvfb: display startup time is excluded,
but the entire display process is included in Bruster's PSS. These two startup
definitions must be kept distinct.

All reported memory includes the browser's complete process forest and runtime
dependencies. PSS apportions shared resident pages; summing process RSS instead
would double-count shared pages. Installed runtime bytes are reported separately
and still include LLVM/Gallium: reducing resident graphics overhead does not
remove those libraries from the installation.

Competitor packages are the latest installable stable versions checked on
November 6: **playwright-core 1.65.0, puppeteer-core 25.16.0, agent-browser
0.41.2**. Initially, npm advertised `playwright@1.65.0` while its required core
returned HTTP 404. After the restart, preflight detected the newly available
1.65.0 core and required an update before measurement. Both registry states are
retained. Puppeteer's wrapper and core both resolve to 25.16.0. The comparison
uses shared current stable **Chrome for Testing / Headless Shell
157.0.8103.38**, selected independently of Playwright's bundled browser manifest.

## Raw evidence

[Download the compressed evidence](evidence/navigation-performance-2026-11-05.tar.gz)
and its [SHA-256 checksum](evidence/navigation-performance-2026-11-05.tar.gz.sha256).
The [archive guide](evidence/README.md) describes the retained batches. The final
batch is `implementation/clean-2026-11-05/`; its `validation.json` checks sample
counts, lifecycle cleanup, concurrency records, complete PSS sums, extraction
equivalence and installed-file inventories. `report-summary.json` and
`summarize.py` expose the aggregation behind the tables. Every archived file has
a size and SHA-256 in `implementation/EVIDENCE_MANIFEST.json`.
The archive contains **1,257 paths in 8,021,098 compressed bytes**; identical
contents use tar hard links. Archive SHA-256:
`763337768abc8e6d0b320e3c050d8100611de73e192946e0e60ce0aa6aee2e9a`.

The archive also preserves historical and excluded measurements, failed and
successful CI attempts, cancelled waits, both frozen executables, exact harness
sources and the local harness patch. The source validation is the linked CI run;
the local measurements are a separate machine and dataset.

## Reproduction

Build the baseline and candidate with the same release toolchain and runtime.
Freeze their executables before measuring. The paired probe alternates build
order, uses isolated HOME/XDG directories and local fixtures, and preserves
failed samples. Run workloads serially without concurrent builds/tests:

```sh
env -u DISPLAY -u WAYLAND_DISPLAY python3 scripts/bench_performance.py \
  --baseline /path/to/baseline-bruster --candidate /path/to/candidate-bruster \
  --workload startup --rounds 20 --output /path/to/startup.json
```

Repeat with `--workload graphics --rounds 3`, `transport --rounds 3`, and
`timers --rounds 1`. With no inherited display, launch-to-page and process
memory include automatic Xvfb, its shell wrapper, and all browser descendants.
The transport probe uses a real 2,000-element page; its stress result repeats
the cached object ten times and is not a 20,000-element DOM traversal.

For latest-version comparisons use `scripts/bench_compare.py` with current
Playwright, Puppeteer and agent-browser packages and a shared selected Chromium
build. Use `scripts/bench_footprint.py` on its samples to inventory executables,
WebKit helpers, Node where required, browser bundles, display tools, linked
libraries and observed mapped files, deduplicated by device/inode.

OS page caches are not flushed. Process PSS includes runtime dependencies and
the display. Installed logical bytes are a separate lower-bound inventory,
not download size or a complete OS image. These local measurements must not be
mixed with timings from different CI machines.
