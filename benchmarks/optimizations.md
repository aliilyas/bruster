# Stepwise performance experiments

The candidate targets these costs, with each stage checked before proceeding:

1. **Snapshots:** cache text and ancestor predicates only for the duration of one
   snapshot; avoid naming text-role elements whose name would be discarded.
   Native visibility is still checked per element, including visibility overrides.
2. **MCP:** construct tool schemas once, and serialize validated borrowed page
   results directly into MCP content. JSON object member order is not significant;
   strings, image content, errors, cancellation and stale-document filtering keep
   their existing meanings.
3. **Network logging:** decode a bounded UTF-8 response prefix, cancel just the
   cloned stream branch, and stop cloning responses when the log fills. The
   decoder also slices oversized native chunks before decoding; a cached body
   cannot turn a prefix read into a full-body string allocation. The page's
   original response and request-idle accounting remain intact.
4. **Dynamic waits:** temporary mutation observers wake pending commands, with
   timer fallback for CSSOM edits, animations and new embedded roots. Observers
   are disconnected on every wake; idle pages have no extra permanent observer.
5. **Screenshots:** encode proven-opaque Linux surfaces as RGB with the existing
   GDK PNG writer at compression level 3; preserve Cairo's transparent-surface
   path. Convert the native CGImage directly on macOS. A level-1 RGBA prototype
   was rejected after diagnostic PNGs grew eightfold and inline latency rose.
   Record bytes alongside latency and verify pixels.
6. **Selectors:** native first-match lookup within each root, preserving root
   ordering and the walker semantics of `:scope`, `&` and escaped selectors. Counting
   no longer builds an array of every matching node.
7. **Startup:** opt-in stage tracing identifies engine construction versus
   controller work. Measure launch-to-first-page, including blank-page warmup,
   as well as the ready event. Existing sessions amortize engine startup.

### WebKitGTK streaming compatibility

The gated streaming regression exposed a WebKitGTK 2.52.0–2.52.6 bug:
`FetchBodySource::pull()` in the byte-stream source does not drain already
buffered bytes. A response can stall until another network chunk or EOF arrives,
even while the page and logger are both reading. Materializing `response.body`
before cloning and increasing the response size did not reliably resolve it.

On those versions, `src/webkit_compat.rs` disables
`ReadableByteStreamFetchSource`, selecting WebKit's existing non-byte source,
whose pull method drains buffered bytes. Fetch still exposes a readable stream;
BYOB readers on fetch responses are unavailable with this fallback. Other
WebKitGTK versions and platforms keep their native defaults. The optional
feature API is resolved dynamically to retain the existing 2.38 library minimum.

The regression retains gated EOF and full response equality, using a 40 KB
multibyte payload. The page must remain unfinished when the 16,384-code-unit
log prefix becomes available.
An additional single-chunk fixture checks BOM handling, split multibyte
characters and the maximum bytes passed to each decoder call.

### WebKit reader cleanup compatibility

Fresh main validation exposed an intermittent large-fetch timeout. A local
stress reproduction stopped responding to all page commands; native stacks
showed garbage collection waiting on the reader's stream lock, matching
[WebKit bug 326046](https://bugs.webkit.org/show_bug.cgi?id=326046).
`ReadableStreamDefaultReader.releaseLock()` holds that lock while running an
allocating JavaScript builtin, whose collector can try to acquire it again.

The logger now cancels its private cloned branch and discards its reader without
calling `releaseLock()`. Nothing reuses that clone, and the cancelled reader and
stream can be collected together. The original page response is unaffected.
A regression repeatedly consumes 32 complete 16 MiB responses, checks their log
prefixes, and verifies that page commands remain responsive.

## Verified comparison — 2026-11-04

[Run 41912450834](https://github.com/aliilyas/bruster/actions/runs/41912450834)
passed native correctness and pixel checks on Ubuntu 24.04 x86_64 and macOS
15.8.2 arm64. Both platforms completed 20 alternating pairs per transport with
identical decoded results and screenshot RGB pixels. Rust was 1.99.1 on both.

- Baseline: v0.3.5, `6d94c2fe885f5f186d8fafd98f90688556a8f6c9`.
- Candidate: `14d37b2e51fb438c2c2d320aba9274e91dc4c625` (runtime identical to
  `007311dc0322ea428ae094c9d204225e4896b70f`; later changes repair the workflow).
- The run's two `paired-performance-*` artifacts retain every sample, complete
  metric tables and pointwise 95% intervals, harness sources, binary hashes,
  PNGs, native package/toolchain provenance and correctness evidence.

Paired latency reductions (positive means faster in this summary):

| Workload | Linux JSONL | Linux MCP | macOS JSONL | macOS MCP |
|---|---:|---:|---:|---:|
| Selector lookup | 65.0% | 68.4% | 63.2% | 66.8% |
| DOM insertion wait | 77.0% | 77.0% | 73.1% | 72.7% |
| Actionability wait | 75.6% | 75.7% | 70.4% | 70.3% |
| Text-heavy JSON snapshot | 18.2% | 22.0% | 16.3% | 18.8% |
| Text-heavy text snapshot | 20.1% | 19.5% | 22.3% | 17.6% |
| File screenshot | 18.7% | 17.8% | 35.1% | 30.8% |
| Inline screenshot | 18.0% | 18.1% | 30.8% | 28.3% |
| Fetch with body capture | 11.8% | 10.9% | 20.0% | 27.8% |

Every reduction in this table has a pointwise 95% interval excluding zero.
Large cached-object MCP replies improved 30.8% on Linux and 29.1% on macOS;
native replies were statistically unresolved. Large-control JSON snapshots
improved 9.0%/11.2% over MCP on Linux/macOS. Linux native large snapshots and
large text-format snapshots had intervals crossing zero. Linux settled PSS
after this workload was about 4.5% lower through either transport.

### Tradeoffs and limits

- **Linux tiny native JSON snapshots:** 0.638 → 0.731 ms median; paired latency
  increased 18.0% (95% interval +14.0% to +22.3%). This is a measured small-page
  regression, retained alongside the larger text-heavy and MCP improvements.
- **Linux MCP startup:** 91.937 → 92.861 ms median; paired latency increased
  1.86% (95% interval +0.17% to +3.53%). Launch-to-first-page intervals crossed
  zero for both Linux transports. There is no cross-platform startup speedup
  claim; the macOS native ready-event improvement did not repeat through MCP.
- **PNG size:** Linux increased from 111,056 to 120,539 bytes (+8.54%) while file
  and inline latency both improved about 18%. macOS stayed at 143,239 bytes.
  Pixels matched on both platforms. The Linux size result differs from the
  local GDK/Glycin diagnostic encoder; native runner evidence takes precedence.
- These are fixture-specific measurements with warm OS caches, a prestarted
  display and DPR 1, not guarantees for every page or a pooled overall speedup.
  The reports include all metrics, including neutral and slower results.

## Bounded Linux PNG encoder follow-up

File and inline captures now share a streaming RGB encoder for proven-opaque
Cairo image surfaces. It converts one row at a time and uses a 64 KiB IDAT buffer,
avoiding full-image RGB intermediates even for large captures. Transparent and
non-image surfaces use Cairo's alpha-preserving encoder. Physical pixel limits,
capture reservations and cancellation still apply. Tests cover padded rows,
native byte order, transparency, backing scale, large RGB24 surfaces and write
failures.

This integrates the PNG change first tested as `ce2042a` on
`perf/regression-followup`. In that branch's
[paired CI run 42116247340](https://github.com/aliilyas/bruster/actions/runs/42116247340),
20 pairs per transport compared `bdbd986` with `f48fc05`. Linux JSONL file
captures went from **29.593 to 15.756 ms**, paired **−46.28%** (95% interval
−47.01% to −45.30%); MCP file captures improved **46.10%**. Decoded opaque pixels
matched, and file sizes were **111,056 versus 111,060 bytes**. This earlier
candidate also included small protocol/snapshot changes, so retain its exact
commit provenance when quoting the evidence. macOS screenshot intervals crossed
zero. The PNG encoder is Linux-specific.

## Reproduce

Build baseline and candidate with the same Rust toolchain and release flags,
using **separate Cargo target directories**, then freeze both executables. Cargo
can reuse stale artifacts across same-name worktrees sharing a target directory;
the workflow isolates the baseline build and checks that the measured candidate
matches the correctness-tested executable. On an otherwise idle Linux runner:

```sh
xvfb-run -a python3 scripts/bench_optimizations.py \
  --baseline /path/to/baseline-bruster --candidate /path/to/candidate-bruster \
  --output results --rounds 20 --iterations 24
```

On macOS omit `xvfb-run -a`. Native screenshot dimensions follow the measured
device pixel ratio. `.github/workflows/performance.yml` runs the build, native
regressions and paired measurements on Linux and macOS for `perf/**` branches,
and is also manually dispatchable. Its default baseline is `origin/main`; supply
a tag or commit SHA to compare another revision. Baseline-specific concurrency
groups allow independent comparisons against main and an older revision. It
uploads evidence without updating the public competitor rankings.

Each transport gets 20 fresh sessions per executable, alternating AB/BA. Each
session has fresh XDG state (and HOME on macOS); OS caches stay warm. The display
starts before timing. MCP startup includes initialization and the first native
`tabs` response; JSONL startup waits for `ready`. Both measure real first-page
completion separately. Timed operations include Python request encoding and
response decoding, identical for baseline and candidate.

Workloads cover small, 2,000-control and text-heavy snapshots in both formats;
indexed selector lookup; large cached object transport; file and inline PNGs;
delayed DOM insertion and enablement; and a 16 MiB fetch plus retained log prefix.
Checks cover element counts, equal decoded results, complete response bytes,
full opaque screenshot RGB equality, normal shutdown and process cleanup. PNG
compression bytes are intentionally compared separately from pixel correctness.

Two warmup operations precede repeated timings. Reports use per-session medians
and paired geometric ratios with seeded, pointwise 95% bootstrap intervals.
The p95 columns are medians of each session's p95: useful diagnostics, with only
12 observations per repeated workload by CLI default (24 in CI). Screenshot and fetch samples
are smaller; their p95s are observed upper samples rather than robust tail estimates.
Bootstrap intervals are not an all-metric performance gate.

Raw samples, executable hashes, harness sources/hashes, screenshots, environment,
process inventories, stderr and source/toolchain provenance are retained. Local
desktop runs require `--diagnostic` when other browsers or screensavers are
present; those reports are explicitly ineligible for published speedup claims.

Performance claims require the clean paired run and native platform correctness
checks. Stage tracing (`BRUSTER_TRACE_PERF=1`) is diagnostic and disabled in the
timed comparison.

## Paired public extraction

The continuous comparison's **Extraction** metrics use the shared `EXTRACT`
JavaScript through `eval`, rather than Bruster's native `snapshot` command.
[`bench_extraction.py`](../scripts/bench_extraction.py) reuses that expression,
fixture server, result validation and JSONL driver's timestamp boundaries:
request write through complete response-line read. Request serialization and
client-side result parsing are outside those recorded boundaries. These differ
from the end-to-end client timings of `bench_optimizations.py` above.

```sh
xvfb-run -a python3 scripts/bench_extraction.py \
  --baseline /path/to/baseline-bruster --candidate /path/to/candidate-bruster \
  --output extraction-results --rounds 20 --iterations 24
```

The Linux paired-performance job runs this after the native optimization suite:

- Ten tiny-page navigations, extracting immediately after each load.
- Five large-page navigations, extracting both object and JSON-string returns in
  alternating order, matching the public comparison's counts and order.
- First-call, second-call and combined-call diagnostics from those same samples.
  The combined metric sums both recorded call latencies, excluding validation
  between the requests.
- Separate warmed tiny/large extraction: two discarded warmups per format,
  then 24 repetitions per format on the loaded page in CI.

First and second calls can have very different timings after navigation. With
five samples per format, a bimodal distribution can move a median substantially.
Inspect raw samples, call order and pointwise paired intervals alongside the
per-format medians. Cross-run competitor charts alone do not assign a regression
to Bruster. The warmed diagnostics describe a different workload and are not a
replacement for the post-navigation results.

Every decoded extraction is validated; hashes must match across formats,
repetitions and baseline/candidate sessions. Overlapping browser/compiler
workloads or forced cleanup fail normal runs. `--diagnostic` preserves desktop
contamination evidence and disables publication eligibility. The workflow keeps
the source and binary hashes, raw samples, process accounting and report under
the artifact's `extraction/` directory.
