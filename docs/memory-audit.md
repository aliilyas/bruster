# RAM reduction audit

Audited 2026-11-04 at `916bc9c` (Bruster 0.3.5). Covers application source,
`Cargo.lock`, the checksum-verified Wry 0.57.0 source archive, archived Linux
process measurements, and upstream browser documentation/source.

## Implementation follow-up — 2026-11-04

The working tree now implements the remaining instrumentation, allocation and
request-admission fixes from the main review. The sections below this follow-up
are historical analyses of the named commits, not descriptions of current code.

| Area | Implemented behavior |
|---|---|
| DNS prefetch | Routes through `App` and the originating tab's native `WebContext`; no global default context is created for prefetch. |
| DOM/XHR retention | Snapshot refs use weak references, with a token/DOM-walker fallback on engines without `WeakRef`. One observer per XHR tracks reuse, including opens that never send. Clearing diagnostics drops pending fetch/XHR entry references. |
| Network diagnostics | 500 entries / 2 MiB accounted text and metadata; four cloned readers with five-second deadlines; 4096-code-unit URL/header bounds. Clearing logs and page teardown cancel readers. Binary fetch responses are skipped; `network({bodies:false})` enables metadata-only capture. The page's original request is preserved. |
| Console/dialog diagnostics | Console formatting is admitted before bounded item/depth/text traversal; it avoids getters and `toJSON`. Dialogs have count, byte and message limits, with a dropped-record counter. Bounded diagnostic substrings are copied to avoid retaining oversized backing strings. |
| Screenshot peaks | One capture per tab / two globally; 24 × 1024² physical-pixel preflight budget, including scale and full-document width. The 16000-CSS-pixel full-height cap applies before choosing the capture path. Large Linux captures avoid the full RGB intermediate; Linux file output streams PNG directly to disk. |
| Screenshot lifecycle | Outer deadlines include the screenshot queue. Cancellation restores resized viewports; native callbacks retain their concurrency reservation through timeout/tab close. Unique capture tokens reject late geometry callbacks after public request IDs are reused. Inline replies borrow the base64 string instead of cloning it into a second JSON/MCP tree. |
| Uploads | At most 32 regular files / 16 MiB total; blockwise file reading, base64 encoding and page decoding, with file-growth checks. Large strings/arrays move into their final containers, and retry parameters share an immutable `Rc<Value>`. Unix FIFO inputs fail without blocking the UI. |
| Backpressure/cancellation | Stdin records are bounded at 8 MiB. Reference-counted permits bound outstanding browser work to 128 requests / 64 MiB of accounted input and expansion. MCP cancellation removes queued actions and propagates to navigation, captures, waits, actionability checks and delayed typing. Redispatch checks cancellation before running an abandoned action. |

The public limits and compatibility behavior are documented in
[`docs/reference.md`](reference.md#memory-budgets). These are admission and
instrumentation budgets, not a total-browser heap ceiling. Page code, native
renderer allocations and the browser's own console/cache have separate lifetimes.
Arbitrary `eval` JavaScript remains non-interruptible; cancelling its reply cannot
stop an application-owned loop or asynchronous side effect.

### Functional verification

Native Linux testing uses Rust 1.93.1, WebKitGTK 2.52.6 and Xvfb on Ubuntu 26.04.
Temporary local tool/runtime extraction made native verification possible without
changing system packages. The extracted WebKit library's helper-directory strings
were relocated to the extracted helper binaries; repository and system libraries
were not modified for this environment setup.

- Rust type-checking, JavaScript syntax validation and whitespace checks pass.
- **19 unit, 43 smoke, 24 edge and 8 focused Test Lab tests passed**, using full
  suite runs followed by targeted reruns for the changed cases. Two broader Test
  Lab tests remain intentionally ignored (framework bundles / published-site
  internet coverage). No macOS/Windows CI run had been triggered at that local
  verification checkpoint.
- Native regression coverage includes reader deadlines/clear, aggregate network
  saturation, metadata-only/binary skipping, XHR reuse, diagnostic formatting,
  abandoned actions, queued MCP cancellation, admission exhaustion/recovery,
  capture-token reuse, scale/clip validation, upload limits and block boundaries.
- macOS/Windows screenshot APIs were reviewed against the pinned upstream
  bindings; native execution on those platforms remains unverified locally.

Publication integration on 2026-11-05 used `main` at
`4c6324c5ca6bd7af59debdaa27ec6b42b3a92693`, retaining the upstream WebKit
reader-cleanup fix and its large-fetch GC regression, the UI-testing additions,
and package version 0.3.6. A fresh integrated build passed **19 unit, 3 UI-runner,
7 focused smoke and 2 focused edge tests**, including reader deadlines, network
budgets, the GC regression, queued cancellation, redispatch and admission recovery.
Rust formatting, JavaScript/Python syntax and whitespace checks also passed.

### Paired screenshot peak measurement

Measured frozen release binaries with the same Rust toolchain, Cargo manifest,
lockfile, runtime libraries and Xvfb display. Baseline application source is
`0c2bbcb9c82e90ba322af9a47caa22d2e3966de3`; the candidate was frozen from the
pre-publication working tree, including its concurrent testing-CLI additions.
These measurements predate integrating the upstream WebKit reader-cleanup fix
(`fe7caf6`) and the package version update to 0.3.6. The hashes below identify the
measured builds. Results compare the two complete builds rather than isolating
individual changes.

The workload is a deterministic, opaque **1280×16000** striped document injected
into the warmed blank page, with a **1280×800 viewport at scale 1**. Each output
mode has three alternating baseline/candidate pairs, with a fresh isolated
session each time. Measurements cover the browser's complete process forest,
**excluding the Python controller and Xvfb**. The requested 20 ms sampling delay
plus process-reading time produced median sample spacings of about 49–51 ms.
These are sampled peaks; shorter transients can be missed, and per-process reads
are not simultaneous.

| Output | Baseline peak PSS | Candidate peak PSS | Reduction | Median capture time, baseline → candidate |
|---|---:|---:|---:|---:|
| File | 448.44 MiB | 247.99 MiB | **44.70%** | 2102.38 → 2098.57 ms |
| Inline JSONL | 462.60 MiB | 248.28 MiB | **46.33%** | 2028.29 → 2018.88 ms |

Values are medians of per-session peaks. Peak USS fell from 365.35 to 165.19 MiB
for file output, and 379.37 to 165.43 MiB inline. Swap was zero. Before-capture
PSS was about 169 MiB for both builds: this demonstrates a large-capture peak
improvement, not a comparable reduction in idle RAM. Three pairs on one fixture
do not establish a general latency improvement.

All six file captures decode to **identical 1280×16000 pixels**. Each build also
produced identical encoded hashes across its file and inline captures, extending
that parity check to all twelve captures. Candidate PNGs are 102792 bytes versus
99233 baseline bytes (**3.59% larger**) on this fixture.

Reproducer: [`scripts/bench_memory_peaks.py`](../scripts/bench_memory_peaks.py).
With two frozen binaries and a configured Linux display/runtime:

```sh
python3 scripts/bench_memory_peaks.py --baseline /path/to/baseline-bruster \
  --candidate /path/to/candidate-bruster --rounds 3 \
  --output benchmarks/results/memory-budgets
```

Local raw samples, summaries, image files and frozen-source/runtime provenance
are in `benchmarks/results/memory-budgets/` (the existing results directory is
git-ignored). The run used display `:97`; the persistent desktop screensaver on
`:0` was recorded and excluded from competing-process detection. No competing
browser/compiler processes or forced browser cleanup were reported.

SHA-256 identifiers:

- Baseline binary: `ab179a97cebb5d8e73019ff8b897787989ac7c61168fe0a32058e2be59dbcd3e`.
- Candidate binary: `a0dcf3c8162dc9d731105ee7568ed10dcc46b0060d2a989dabbb23bb271a5245`.
- Shared `Cargo.lock`: `5b75bda0b91878a502491f77bb966fcda27aaeaeb2233f8ce9ab82617a695c62`.
- Final `samples.json`: `a125d78d3e2729f0c192fe206295593fe62836e4c83355184aa23ac71c6b2f76`.

### Remaining research

The Wry native-object reference-cycle investigation, optional engine low-memory
policies, memory-pressure construction hooks, lazy browser startup/discard and
alternate rendering backends remain research/architectural proposals. This patch
does not establish their benefit. The earlier merged report's 4.5% settled-PSS
figure is not a measurement of these new changes.

## Latest-main follow-up — 2026-11-04

Reviewed fetched `origin/main` at `0c2bbcb9c82e90ba322af9a47caa22d2e3966de3`
(“Merge stepwise performance improvements and verified benchmark results”), six
commits after the original audit baseline. The recommendation and numbered
sections below preserve the `916bc9c` analysis; this section records the updates.

### Findings addressed by the merge

| Original finding | Latest-main status |
|---|---|
| Full-body fetch logging and capture after log saturation | **Core fix implemented.** Admission happens before header collection/cloning; the cloned reader decodes bounded chunks, retains at most 16,384 UTF-16 code units and cancels its branch. This also handles an oversized cached chunk without decoding the whole chunk. See [`src/runtime.js:98–153`](../src/runtime.js#L98). |
| MCP result copies and repeated schema construction | **Implemented for successful page replies.** Validated borrowed JSON becomes MCP text/image content without a `Value` result tree; schemas use `OnceLock`. The schema cache trades a small permanent allocation for less per-call churn. See [`src/mcp.rs:188–264`](../src/mcp.rs#L188) and [`299–302`](../src/mcp.rs#L299). |
| Counting materializes every match | **Implemented.** Counting iterates the matcher without collecting a result array. Snapshot text/ancestor caches are scoped to one collection, and discarded text-role names are no longer computed. See [`src/runtime.js:576–628`](../src/runtime.js#L576) and [`698–702`](../src/runtime.js#L698). |
| macOS screenshot TIFF intermediate | **Removed.** Conversion now uses the snapshot's CGImage directly. See [`src/screenshot.rs:134–144`](../src/screenshot.rs#L134). |
| XHR capture after log saturation | **Partially addressed.** New logging listeners are skipped while the log is full, but previously installed listeners remain attached. Clearing logs permits further accumulation on a reused XHR. See [`src/runtime.js:155–175`](../src/runtime.js#L155). |

### RAM tradeoff requiring peak measurements

Linux's opaque screenshot path now constructs a full **3 × width × height** RGB
buffer while retaining the Cairo surface, then encodes into a PNG buffer
([`src/screenshot.rs:62–90`](../src/screenshot.rs#L62)). At 1280×16,000 physical
pixels, that RGB buffer alone is **58.59 MiB**, alongside a **78.13 MiB** Cairo
surface, encoded output and encoder/engine allocations. These are identifiable
simultaneous buffers, not a measured net increase versus Cairo's previous encoder.
Peak-memory sampling is needed to establish the overall before/after effect.
Pixel and capture-concurrency budgets remain a priority.

The merged [performance report](../benchmarks/optimizations.md) reports about
**4.5% lower settled Linux PSS**, roughly **18% faster Linux screenshots**,
**28–35% faster macOS screenshots**, and roughly **30% faster large MCP replies**
on its fixtures. Linux PNG bytes grew **8.54%**. Tiny native Linux JSON snapshots
and Linux MCP startup regressed **18.0%** and **1.86%**, respectively.

The harness samples Linux memory once per session, after a one-second settling
delay following the fetch workload
([`scripts/bench_optimizations.py:174–192`](../scripts/bench_optimizations.py#L174)).
That establishes a post-workload result; it does not measure screenshot peaks or
an idle-startup baseline. Do not apply its percentage to the separate archived
219.32 MiB workload below.

### Remaining priorities

1. **Reuse the tab context for DNS prefetch.** The handler still calls
   `WebContext::default()` ([`src/main.rs:1853–1860`](../src/main.rs#L1853)).
2. **Fix long-lived retention.** Persistent XHR listeners, strong DOM refs,
   unbounded dialogs and console formatting before admission remain.
3. **Finish capture budgets.** Fetch readers still need aggregate byte/concurrency
   limits, deadlines and cancellation on log clearing. Screenshot pixel/concurrency
   limits and large upload copies are also outstanding.
4. **Investigate lifetimes and backpressure.** The Wry reference-cycle candidate,
   engine low-memory policies, lazy startup, queued-work limits and cancellation
   propagation still require implementation or native validation.

The WebKitGTK 2.52.0–2.52.6 streaming workaround disables
`ReadableByteStreamFetchSource` on those releases: ordinary fetch streams remain
available, but fetch-response BYOB readers are unavailable. Dependency versions
were not reduced by this merge.

Validation: independently confirmed the reported candidate's
[paired CI run](https://github.com/aliilyas/bruster/actions/runs/41912450834)
completed successfully. Locally, both existing `test_bench_optimizations.py`
tests passed. Native profiling remains blocked by missing Cargo/rustc, Xvfb and
WebKitGTK/JavaScriptCore libraries. At review time, main's native matrix and fresh
[paired run](https://github.com/aliilyas/bruster/actions/runs/41918509583) were
still running; Docker amd64/arm64, Linux public-site E2E and MCP integrations had
passed.

## Original recommendation — `916bc9c`

**Fix instrumentation retention and large transient allocations first. For lower
idle RAM, manage browser lifetimes and native-engine policy.** The Rust dependency
graph offers much less leverage than the browser processes and display server.

| Priority | Change | Expected benefit | Effort |
|---|---|---|---|
| 1 | Route DNS prefetch through the existing tab context | Avoid an unnecessary context/network process after link snapshots | Small |
| 1 | Bound fetch-body capture before reading; stop capture when its budget is exhausted | Large-response/streaming memory spikes; unnecessary work on every request | Medium |
| 1 | Fix reused-XHR listeners; bound diagnostic data; release detached DOM refs | Long-running page memory growth | Small–medium |
| 1 | Budget screenshot pixels and concurrency; reduce upload/response copies | Potentially hundreds of MiB during large operations | Medium |
| 2 | Investigate Wry's GTK IPC reference cycle with repeated tab close tests | Possible host-process retention after tabs close | Medium; upstream patch candidate |
| 2 | Add an opt-in low-memory cache/resource policy on Linux | Lower page/resource cache residency; workload-dependent | Small–medium |
| 2 | Use Wry's existing Windows low-memory API when idle | Reduced inactive WebView2 residency | Small–medium |
| 2 | Bound queued work and propagate cancellation | Predictable memory under concurrency and abandoned requests | Medium |
| 3 | Lazy browser startup for MCP; explicitly discard idle tabs | Large savings when a browser/tab is unused | Medium–large |
| 3 | Configure WebKit memory pressure before context construction | Earlier cache reclamation in constrained deployments | Medium; Wry extension needed for web processes |
| 4 | Prototype a WPE Linux backend if the baseline is still too large | Potential removal of GTK/Xvfb overhead | Large; must measure |

Benefits above are source-based expectations, **not measured savings from an
implemented patch**. Workload-dependent gains are not additive.

## 1. Where the RAM goes

The archived release-0.3.4 benchmark provides ten sessions on Ubuntu 24.04 x86_64,
WebKitGTK 2.52.6, GTK 3.24.41, a 1280×800 viewport, and an external Xvfb. Each
session has three idle samples after small-page navigation/extraction, before
the large-page workload.

| Component | Median PSS, MiB |
|---|---:|
| Bruster host, including its native libraries and UI state | 69.12 |
| WebKit web process | 88.38 |
| WebKit network process | 24.58 |
| Xvfb | 35.89 |
| **Whole workload, including Xvfb** | **219.32** |

The total's observed session range is **217.41–223.17 MiB**. Component values
are medians of each session's median, so their sum need not equal the median
total. Browser-forest RSS, **excluding Xvfb**, is 344.40 MiB; it double-counts
shared pages and should not be compared directly with the inclusive PSS total.

Evidence directory:
`benchmarks/results/release-v0.3.4/benchmarks/benchmarks-e5715899d3b39a61f5a0d70fc1d02107782bd044-41731814829-1/`.
Files: `metadata.json`, `samples.json`, and `summary.json`. `samples.json` SHA-256:
`65164565daf58269b281dee5c58d71901648700b59b95bd888bb79cc758675af`.
The corresponding [published run][archived-run] identifies the benchmark.

`git diff e5715899d3b39a61f5a0d70fc1d02107782bd044 HEAD -- src Cargo.toml Cargo.lock`
shows only the package-version change: application source and dependency versions
match this audit. These remain **archived measurements**, not a fresh measurement
on the current host. That host currently lacks Cargo/rustc, Xvfb, and
`libwebkit2gtk-4.1.so.0`/`libjavascriptcoregtk-4.1.so.0`, preventing native build
and runtime profiling.

The 69 MiB host figure is not a Rust-heap measurement. Its mapped-file inventory
includes GTK, WebKit, JavaScriptCore, graphics and media libraries. Mapping a
library also does not imply that its entire file is resident.

### Existing optimizations worth preserving

- Software rendering, compositing disabled, and hidden-mode DMA-BUF suppression:
  [`src/main.rs:699–715`](../src/main.rs#L699).
- Page cache and WebGL disabled, media playback disabled, moderate
  `DocumentBrowser` caching: [`src/main.rs:2256–2266`](../src/main.rs#L2256).
- One shared Linux context/network session, and explicit web-process termination
  on normal tab close: [`src/main.rs:574–583`](../src/main.rs#L574),
  [`1118–1146`](../src/main.rs#L1118).
- TreeWalker-based DOM traversal, capped default snapshots, borrowed JSONL
  replies, buffered stdout, and one deadline thread:
  [`src/runtime.js:260–285`](../src/runtime.js#L260),
  [`src/main.rs:607–629`](../src/main.rs#L607),
  [`975–1005`](../src/main.rs#L975), [`1598–1623`](../src/main.rs#L1598).

WebKitGTK 2.52.6's [process-cache implementation][webkit-process-cache] disables
its idle web-process cache unless the cache model is `PrimaryWebBrowser`.
Bruster already selects `DocumentBrowser`; disabling that cache again should
not be counted as a new optimization. The deprecated
[`set_web_process_count_limit`][process-limit] is explicitly a no-op.

## 2. Highest-confidence source changes

### A. DNS prefetch creates a second context

[`src/runtime.js:529–538`](../src/runtime.js#L529) sends external link hosts to
Rust after a snapshot/find. [`src/main.rs:1833–1840`](../src/main.rs#L1833) then
calls `webkit2gtk::WebContext::default()`, rather than using the context of the
originating tab. Wry [constructs its own context/data manager][wry-context], so
this native global singleton is a different context.

In [WebKitGTK 2.52.6][webkit-context], `prefetch_dns` accesses that context's data
store and calls `networkProcess()`. For the legacy GLib API used by WebKitGTK
4.1, [`networkProcessForSession`][webkit-data-store] creates a network process
for each persistent session. Thus a snapshot with external hosts can initialize
another persistent context and network process just for speculative DNS work.

Route the prefetch request back to `App` with its tab ID and use
`tab.webview.webview().context()`, or otherwise retain the correct native context
for the callback. This is a much smaller change than replacing a dependency.
Verify process counts before/after a snapshot containing external links; the
one-network-process idle baseline above does not measure this path. The extra
process's actual PSS and runtime-version behavior still need a native run.

### B. Network body logging reads entire responses

[`src/runtime.js:71–99`](../src/runtime.js#L71):

```js
const logNet = (e) => { if (net.length < NET_MAX) net.push(e); };
// ...
res.clone().text().then((t) => { entry.body = t.slice(0, BODY_MAX); });
```

`BODY_MAX = 16384` limits the eventual string prefix, not the data read or
allocated. [`text()` reads to completion][response-text]; a 100 MiB response
still gets fully consumed/decoded by the instrumentation. A streaming response
may never finish. [`clone()` tees the stream][response-clone], and a slower or
unconsumed branch can accumulate buffered data without a fixed limit.

Furthermore, reaching `NET_MAX = 500` stops insertion but **does not stop cloning,
decoding, or collecting headers**. Requests after the first 500 still incur the
expense even though their diagnostic entries are not available to the caller.

Recommended implementation:

1. Have log admission return whether an entry was accepted. Continue minimal
   in-flight tracking for navigation/waits even when diagnostics are disabled.
2. Read only a bounded prefix using a clone's stream reader and `TextDecoder`;
   cancel that reader at the limit. Never cancel the page's original response.
3. Bound concurrent capture readers and total retained diagnostic bytes, with
   a time limit for stalled/streaming bodies. Skip inappropriate binary bodies.
4. Cancel capture readers on `network({clear:true})`, eviction, and teardown.
   Handle the clone branch's cancellation promise without delaying the page's
   fetch response or waiting indefinitely for the other branch.
5. Offer metadata-only logging, with body capture explicitly enabled before
   requests whose bodies the caller needs. Bodies cannot generally be recovered
   retrospectively after the page consumes them.

Even the intended prefixes can hold 500 × 16,384 = 8,192,000 characters:
approximately **7.81–15.63 MiB of character storage** at one/two bytes per
character, plus metadata and engine overhead. This is illustrative payload
arithmetic, not an actual heap bound: headers/URLs are uncapped and substring
backing storage is engine-dependent. A byte-budgeted log is more useful than
an entry-count limit alone.

### C. Reused XHRs accumulate listeners

[`src/runtime.js:104–115`](../src/runtime.js#L104) adds a fresh `loadend` closure
on **every `open()`**, without removing it or using `once`. A page that reuses
one XHR keeps every closure and captured entry alive while that XHR survives.
All old handlers also run on each later completion and update their old entries.
The 500-entry log cap and `network.clear` do not release those listener references.

Keep one observer per XHR with per-request state, or explicitly replace/remove
the previous listener on reopen, completion, abort and error. Test reopening an
XHR before completion as well as sequential reuse; adding `once` alone does not
fully address listeners installed for opens that never complete.

### D. Bound diagnostics before serialization; avoid pinning detached DOM

- **Console:** [`src/runtime.js:126–137`](../src/runtime.js#L126) stringifies all
  arguments before applying the 1,000-character limit, even when its 500-entry
  buffer is already full. Check admission before formatting and use a bounded
  formatter with depth/item limits. Preserve calls to the original console;
  changing native console retention is a separate behavior decision.
- **Dialogs:** [`src/runtime.js:142–146`](../src/runtime.js#L142) grows `dialogs`
  without any count or message-size cap. Add a bounded history/byte budget and
  report dropped/truncated records.
- **DOM refs:** [`src/runtime.js:49`](../src/runtime.js#L49),
  [`485–520`](../src/runtime.js#L485) stores strong element references until the
  next snapshot/find/navigation. A removed SPA subtree or old iframe document
  can remain reachable through them. Prefer `WeakRef<Element>` values with the
  existing stale-ref checks, feature-detected where necessary. Connected nodes
  remain owned by their DOM; stale refs should not own removed content.
- **Count:** [`src/runtime.js:597–599`](../src/runtime.js#L597) materializes all
  matches just to count them. Increment a counter while iterating `matching()`;
  this is a small, allocation-specific improvement.

Wry injects the default initialization script into the main frame on GTK/macOS,
but into subframes too on Windows ([Wry initialization API][wry-lib]). Account
for per-frame diagnostic buffers when profiling Windows iframe-heavy sites.

### E. Bound screenshot pixels, not just one dimension

[`src/main.rs:1465–1481`](../src/main.rs#L1465) takes Linux's full-document path
whenever the reported height is ≤32,767, **before** applying the 16,000-pixel
fallback cap. A 20,000-pixel document therefore uses the direct full snapshot.
Only height is queried; document width and physical backing scale also matter.
The CLI viewport and screenshot clips do not have the same validation as
`resize`.

For a single 4-byte-per-pixel surface at scale 1:

| Dimensions | Pixel storage |
|---|---:|
| 1280×800 | 3.91 MiB |
| 1280×16,000 | 78.13 MiB |
| 1280×32,767 | 160.00 MiB |
| 16,000×16,000 | 976.56 MiB |

Scale 2 multiplies pixel storage by four. Renderer backing stores, snapshot
transport, cropping, encoded PNGs and base64 are additional allocations. PNG
file size is not a measure of capture RAM.

Recommended changes:

- Validate all viewport/clip inputs consistently and enforce a total physical
  pixel/byte budget **before** capture, including full document width/height.
- Serialize captures per tab and bound global capture concurrency. Screenshots
  currently bypass `Pending` and its page-request deadlines.
- For huge full-page output, use bounded capture tiles and a streaming image
  writer; assembling every tile into a full-size image defeats the memory goal.
- Prefer the existing `path` option to avoid base64/JSON overhead. It still
  creates a complete PNG `Vec` first ([`src/main.rs:1568–1577`](../src/main.rs#L1568));
  Linux Cairo can instead encode directly to a file-backed writer.
- Linux clipping currently snapshots the entire viewport, then allocates a crop
  ([`src/screenshot.rs:27–75`](../src/screenshot.rs#L27)). A tiny output clip does
  not eliminate the initial viewport surface.
- On macOS, investigate encoding an available bitmap/CGImage directly rather
  than `NSImage → TIFF → NSBitmapImageRep → PNG → Vec`
  ([`src/screenshot.rs:88–103`](../src/screenshot.rs#L88)). Validate native scale,
  alpha and color handling before replacing this conversion.

### F. Reduce upload and MCP result copies

- [`attach_files`](../src/main.rs#L1991) reads files into memory, base64 encodes
  them, and puts them in a `Value`. [`tab_dispatch`](../src/main.rs#L2088) clones
  those parameters into retry state and creates JavaScript source containing
  the base64. [`upload`](../src/runtime.js#L748) then allocates an `atob` string,
  byte array and `File` data. A 100 MiB input alone becomes about 133.33 MiB of
  base64 per full copy. Share/move immutable request payloads instead of deep
  cloning, and investigate native file chooser integration or bounded binary
  transfer for large uploads. Preserve navigation/retry semantics.
- The borrowed `RawValue` reply path is disabled in MCP mode. MCP instead parses
  the page reply into a `Value`, serializes object results into text, and builds
  another envelope ([`src/main.rs:1598–1627`](../src/main.rs#L1598),
  [`src/mcp.rs:169–215`](../src/mcp.rs#L169)). Extend borrowed-envelope handling to
  MCP and write correctly escaped text/image fields directly to the buffered
  writer. For object results, raw JSON still has to be escaped as MCP **text**;
  it cannot simply be inserted as an object.
- [`src/mcp.rs:113`](../src/mcp.rs#L113) rebuilds every tool schema to validate a
  tool name. Validate against static names/specs instead. This is small transient
  allocation churn; keeping a second permanent schema cache is unnecessary.

## 3. Dependency-specific retention investigation

Wry 0.57.0's GTK [`attach_ipc_handler`][wry-gtk] captures a strong `WebView` in a
signal closure owned by its `UserContentManager`:

```text
WebView → UserContentManager → script-message signal closure → WebView
```

Bruster enables this path for every tab. Wry's `InnerWebView::drop` calls GTK
`destroy()`, but does not store/disconnect this manager's signal handler.
WebKitGTK 2.52.6's [view private state/disposal][webkit-view] retains the manager
as a GObject reference and its dispose function does not explicitly clear it;
the [base disposal][webkit-view-base] closes the page and rendering resources.

This is a **native reference-cycle candidate**, not a measured leak size. Renderer
termination on close does not by itself prove that host-side objects finalize.
Instrument a weak GObject reference/finalization callback, then open/close 100
tabs and check both finalization and host USS/PSS. A narrowly scoped Wry fix is
to capture a weak webview and upgrade it inside the callback, or explicitly
disconnect the saved handler during destruction. Validate teardown callbacks
and normal IPC before attributing savings to this change.

## 4. Native-engine and lifetime changes

### Linux: an opt-in low-memory policy

1. Benchmark `CacheModel::DocumentViewer` against today's `DocumentBrowser`.
   Upstream documents the former as [disabling caching][cache-model], including
   remote resources. Expect a tradeoff in repeated-navigation latency/network
   traffic; Bruster deliberately retains a warm disk cache today.
2. Use the existing `--no-images` for text-oriented work. This is implemented
   only on Linux. Smaller viewports reduce backing-store memory, while also
   changing responsive layouts and screenshot dimensions.
3. Wry explicitly enables WebAudio. Bruster disables media **element playback**,
   which is a [different setting][enable-media] from [WebAudio][enable-webaudio].
   Consider disabling WebAudio in the resource-restricted policy. Savings depend
   on pages actually creating audio resources; this does not unload all media
   libraries from the process.

### Linux: memory-pressure configuration has to happen early

[WebKitMemoryPressureSettings][memory-settings] is available since WebKit 2.34,
within Bruster's requested `v2_38` API level. It allows earlier conservative/strict
memory reclamation. Its documented default base limit is system RAM capped at
3 GB, with a 30-second poll interval; that is not a useful application-wide RAM
budget. The settings apply to individual engine processes.

- Web processes receive settings through the **construct-only**
  [`WebContext:memory-pressure-settings`][memory-property] property.
- The [network settings function][network-pressure] must be called before
  creating data managers; periodic checks are otherwise disabled for network
  processes by default.
- Wry 0.57.0 constructs its native data manager/context internally
  ([`src/webkitgtk/web_context.rs`][wry-context]). Its public `WebContext` API
  offers no constructor hook for these settings. Add a small upstream/local
  construction option; setting the property in `trim_webkit()` is too late.
- Keep the kill threshold at its [default zero][kill-threshold] while evaluating
  reclamation. A nonzero threshold can terminate a page; a small base limit is
  not a guaranteed whole-browser memory ceiling. Tune with heavy-page latency
  and peak-memory measurements rather than selecting an arbitrary universal cap.

### Windows: the required API is already in Wry

Wry 0.57.0 exposes:

```rust
use wry::{MemoryUsageLevel, WebViewExtWindows};
webview.set_memory_usage_level(MemoryUsageLevel::Low)?;
// Restore before active work:
webview.set_memory_usage_level(MemoryUsageLevel::Normal)?;
```

[Microsoft documents][webview2-memory] that scripts/network activity continue,
the change is best-effort, and some memory can be swapped out. Lower resident
memory therefore does not necessarily mean less committed memory. Apply after
an idle interval with no pending operation, and restore on any command targeting
that tab, not only `switch_tab`. Wry documents a no-op on older runtimes.

`TrySuspend` is a separate policy that pauses scripts and needs explicit resume;
avoid it for tabs still serving waits/navigation. Microsoft's guidance advises
choosing one policy rather than mixing the two. Explicitly sharing a WebView2
environment is also supported by Wry, but matching user-data folders/options may
already allow process sharing. Count actual processes before claiming a saving.

### Cross-platform: lazy startup, tab reuse and bounded work

- `main()` always opens and warms a blank tab before `ready`
  ([`src/main.rs:757`](../src/main.rs#L757)), including MCP discovery-only sessions.
  Defer browser creation until the first browser operation. Fully deferring
  Linux display costs needs a lifecycle redesign: `ensure_display()` currently
  execs `xvfb-run`, and GTK's event loop requires a display. A lazily started
  browser worker can preserve the MCP connection while postponing engine/display
  allocation. Measure the additional first-command latency.
- `switch_tab` only changes the default ID; all tab windows/webviews remain live.
  Reuse a tab for serial tasks, close completed tabs, and consider explicit
  discard/reload for inactive tabs. Preserve cookies/profile separately and make
  loss of DOM state/history explicit. Hidden macOS tabs intentionally disable
  background throttling to keep automation running; blanket suspension would
  change that behavior.
- Stdin lines/event forwarding, `Pending.js`, `Pending.queue`, and MCP's
  `IN_FLIGHT` have no aggregate request-byte/count budget. Deadlines bound time,
  not peak concurrent memory ([`src/main.rs:953–969`](../src/main.rs#L953),
  [`260–287`](../src/main.rs#L260)). Add bounded admission/backpressure.
- MCP cancellation only removes the public ID; the browser keeps working
  ([`src/mcp.rs:153–160`](../src/mcp.rs#L153)). Propagate cancellation to queued
  commands, cooperative runtime waits/captures and retained payloads. Generic
  page JavaScript cannot always be interrupted safely; do not equate dropping
  the reply with cancelling the allocation-producing work.

## 5. Dependency changes: likely RAM return

The [dependency audit](dependency-audit.md) reports 142 Linux, 83 macOS and
84 Windows reachable packages; the current lockfile still has 261 external
entries across all targets. These are build-graph counts, not resident objects.

| Candidate | RAM assessment |
|---|---|
| Disable Wry's unused `x11` feature | Reasonable cleanup; previous release experiment saved only 1,976 executable bytes. No demonstrated runtime-RAM saving. Tao/GTK/Xvfb remain. |
| Remove Tao's unused URL/ICU edge | Good build-graph reduction; the audited behavior-preserving binary actually grew 2,792 bytes. LTO already discards unused implementation code. |
| Replace Serde, libc, GTK/Cairo or platform bindings | Low return: several are already required by Wry/Tao. There is no production Node/Tokio/HTTP-client/image-codec stack to remove. |
| Swap the Rust allocator | Does not replace allocators in separate WebKit processes. Profile host anonymous memory first. |
| Replace Tao with a narrow GTK adapter | May simplify the graph, but retains GTK, WebKit and the display; substantial RAM savings are unproven. |
| Use WPE WebKit on Linux | Credible architectural experiment: [WPE targets lower-footprint embedded use][wpe]. Requires a new embedding/rendering/IPC/screenshot backend; Wry's current GTK backend cannot just switch crates. |

For multiple Bruster sessions, sharing one appropriately configured Xvfb can
amortize display overhead while keeping browser contexts separate. The archived
35.89 MiB is a display-server reference point, not a guaranteed per-session
saving. Bruster's own auto-Xvfb path already disables GLX; the archived external
Xvfb command did not, so it is not an A/B result for that optimization.

The existing local Servo study reports 225.57 MiB headless PSS. It used different
hardware, viewport and workload timing, so comparing it with the 219.32 MiB CI
figure cannot establish a saving. An engine replacement needs paired equivalent
workloads plus compatibility validation.

## 6. Practical steps available now

For Linux text extraction, where image loading and a smaller layout are acceptable:

```sh
bruster --mcp --quiet --no-images --viewport 1024x640
```

Reuse tabs, close completed extra tabs, scope snapshots with `selector`/`max`,
prefer text snapshots, and supply a screenshot `path` when an inline image is
unnecessary. Use `network`, `console`, and `dialog` with `clear: true` after
consuming their results. Clearing diagnostics helps retained entries but does
not repair full-body fetch capture or the XHR listener issue.

## 7. Validation plan

Freeze baseline/candidate release binaries from the same toolchain/dependency
set. Alternate run order and keep page, viewport, display, engine version,
profile/cache state and navigation milestone identical.

Use [`scripts/bench_compare.py`](../scripts/bench_compare.py)'s complete process
accounting and [`scripts/bench_performance.py`](../scripts/bench_performance.py)
for existing paired graphics/transport/timer scenarios. The latter's `startup`
workload currently records timing, not a memory series. Extend memory sampling
for these focused cases:

| Workload | What must be demonstrated |
|---|---|
| Blank/small page, one tab, JSONL and MCP | Idle baseline and first-command latency |
| Snapshot/find with external links | DNS prefetch reuses the tab's context/network process |
| Large fetches, endless streams, >500 requests, slow/unread original bodies | Bounded diagnostic allocation; original fetch behavior preserved |
| Reuse one XHR thousands of times; clear logs between batches | Listener count/state stable; no linear retained growth |
| SPA subtree replacement and same-origin iframe navigation after snapshot | Detached content collectible; live/stale refs still correct |
| 1/5/20 live tabs; 100 sequential open/close cycles | Per-tab slope, native object finalization, host and child-process cleanup |
| Full/clip screenshots, scale 1/2, concurrent requests | Pixel budget, valid image dimensions, peak memory and viewport restoration |
| Large uploads and large JSONL/MCP results | Correct values with fewer simultaneous full-size copies |
| Cancellation, slow stdout, pipelined requests | Queue bytes/count remain bounded; released work does not run later |
| Idle/repeated navigation under low-memory policies | Residency improvement versus latency, CPU and page-fault cost |

Record process-forest **PSS, USS/private dirty, RSS and swap**, plus per-process
breakdowns. Sample during operations as well as after 1/5/30 seconds of idle;
idle-only measurements miss transient peaks. A 50–100 ms sampler can still miss
very short peaks. For Docker, also record cgroup v2 `memory.current`,
`memory.peak`, and `memory.stat`, whose accounting includes more than process PSS.
Do not infer physical RAM from virtual address reservations or summed RSS.

Run existing navigation, tab, screenshot, profile and protocol tests on each
affected platform, then the focused retention/peak workloads above. Publish
absolute before/after values and functional results before promising a percentage
reduction. A fresh browser run remains the outstanding verification step here.

## Sources

[archived-run]: https://aliilyas.github.io/bruster/benchmarks/runs/e5715899d3b39a61f5a0d70fc1d02107782bd044-41731814829-1/
[response-clone]: https://github.com/mdn/content/blob/main/files/en-us/web/api/response/clone/index.md
[response-text]: https://github.com/mdn/content/blob/main/files/en-us/web/api/response/text/index.md
[cache-model]: https://webkitgtk.org/reference/webkit2gtk/stable/enum.CacheModel.html
[process-limit]: https://webkitgtk.org/reference/webkit2gtk/stable/method.WebContext.set_web_process_count_limit.html
[memory-settings]: https://webkitgtk.org/reference/webkit2gtk/stable/struct.MemoryPressureSettings.html
[memory-property]: https://webkitgtk.org/reference/webkit2gtk/stable/property.WebContext.memory-pressure-settings.html
[network-pressure]: https://webkitgtk.org/reference/webkit2gtk/stable/type_func.WebsiteDataManager.set_memory_pressure_settings.html
[kill-threshold]: https://webkitgtk.org/reference/webkit2gtk/stable/method.MemoryPressureSettings.set_kill_threshold.html
[enable-media]: https://webkitgtk.org/reference/webkit2gtk/stable/property.Settings.enable-media.html
[enable-webaudio]: https://webkitgtk.org/reference/webkit2gtk/stable/property.Settings.enable-webaudio.html
[wry-lib]: https://docs.rs/crate/wry/0.57.0/source/src/lib.rs
[wry-gtk]: https://docs.rs/crate/wry/0.57.0/source/src/webkitgtk/mod.rs
[wry-context]: https://docs.rs/crate/wry/0.57.0/source/src/webkitgtk/web_context.rs
[webkit-context]: https://github.com/WebKit/WebKit/blob/webkitgtk-2.52.6/Source/WebKit/UIProcess/API/glib/WebKitWebContext.cpp
[webkit-data-store]: https://github.com/WebKit/WebKit/blob/webkitgtk-2.52.6/Source/WebKit/UIProcess/WebsiteData/WebsiteDataStore.cpp
[webkit-process-cache]: https://github.com/WebKit/WebKit/blob/webkitgtk-2.52.6/Source/WebKit/UIProcess/WebProcessCache.cpp
[webkit-view]: https://github.com/WebKit/WebKit/blob/webkitgtk-2.52.6/Source/WebKit/UIProcess/API/glib/WebKitWebView.cpp
[webkit-view-base]: https://github.com/WebKit/WebKit/blob/webkitgtk-2.52.6/Source/WebKit/UIProcess/API/gtk/WebKitWebViewBase.cpp
[webview2-memory]: https://learn.microsoft.com/en-us/microsoft-edge/webview2/reference/win32/icorewebview2_19
[wpe]: https://wpewebkit.org/about/a-good-choice.html
