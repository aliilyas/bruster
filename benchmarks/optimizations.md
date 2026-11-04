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

## Reproduce

Build baseline and candidate with the same Rust toolchain and release flags,
using **separate Cargo target directories**, then freeze both executables. Cargo
can reuse stale artifacts across same-name worktrees sharing a target directory;
the workflow isolates the baseline build and checks that the measured candidate
matches the correctness-tested executable. On an otherwise idle Linux runner:

```sh
xvfb-run -a python3 scripts/bench_optimizations.py \
  --baseline /path/to/baseline-bruster --candidate /path/to/candidate-bruster \
  --output results --rounds 20 --iterations 12
```

On macOS omit `xvfb-run -a`. Native screenshot dimensions follow the measured
device pixel ratio. `.github/workflows/performance.yml` runs the build, native
regressions and paired measurements on Linux and macOS for `perf/**` branches,
and is also manually dispatchable. It uploads evidence without updating the
public competitor rankings.

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
12 observations per repeated workload by default. Screenshot and fetch samples
are smaller; their p95s are observed upper samples rather than robust tail estimates.
Bootstrap intervals are not an all-metric performance gate.

Raw samples, executable hashes, harness sources/hashes, screenshots, environment,
process inventories, stderr and source/toolchain provenance are retained. Local
desktop runs require `--diagnostic` when other browsers or screensavers are
present; those reports are explicitly ineligible for published speedup claims.

Performance claims require the clean paired run and native platform correctness
checks. Stage tracing (`BRUSTER_TRACE_PERF=1`) is diagnostic and disabled in the
timed comparison.
