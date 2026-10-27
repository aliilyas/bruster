# Bruster performance review — 2026-10-27

## Scope and conclusion

The published performance section is a Bruster-only microbenchmark. It contains
no controlled comparison with another automation tool or browser. Its current
numbers do not establish a cross-tool performance advantage.

The small-executable claim needs qualification: Bruster reuses substantial
native browser libraries. The published benchmark also has a confirmed invalid
page-load measurement, incomplete browser memory accounting, and a website unit
conversion error.

**Measured locally:** 1.453 MB executable; at least 229.426 MB including linked
native libraries; 221 ms median spawn-to-ready; 15.2 ms warm tiny-page load;
2.4 ms tiny-page snapshot; three browser processes using 217.1 MiB PSS
(260.6 MiB including the dedicated Xvfb server). These results support a small
executable with responsive small-page operations, not a self-contained sub-1 MB
browser or a proven advantage over other tools.

Sources captured for this review:

- <https://aliilyas.github.io/bruster/>
- <https://aliilyas.github.io/bruster/metrics.json>
- <https://raw.githubusercontent.com/aliilyas/bruster/gh-pages/index.html>
- <https://raw.githubusercontent.com/aliilyas/bruster/main/README.md>
- The local `scripts/bench.py`, `Cargo.toml`, and Linux startup implementation.

## Published snapshot

The captured metrics were published at **2026-10-27 19:55 UTC**, for commit
`9f59c5a48df01db74730198a9c494de8c57e7f10`. They identify their environment as
GitHub Actions, Ubuntu 24.04 x86_64.

| Published field | Value | Interpretation |
|---|---:|---|
| `binary_kb` | 1416.1 | Actually KiB; approximately 1.45 MB / 1.383 MiB |
| `cold_start_ms` | 32631 | 32.631 seconds; timer excludes part of startup |
| `page_load_ms` | -2 | Invalid duration |
| `snapshot_ms` | 2 | One observation on a tiny static page |
| `idle_rss_mb` | 172.3 | Actually MiB, for the main process only |

The website inserts `binary_kb` directly into a cell labeled **MB**, displaying
**1,416.1 MB** instead of converting it. Its static headline simultaneously says
“one process of less than 1 MB.”

## Methodology findings

### 1. Page-load timing matches an earlier navigation

`scripts/bench.py` waits for `EVT_LOAD` without advancing the search cursor.
`Lines.wait()` searches from index zero by default. The measured navigation can
therefore reuse the warm-up page's earlier load event. Subtracting the new
request time produces a negative duration. This explains the published **-2 ms**.

The timer also starts **after** sending page-load and snapshot requests. It
should start before writing the request and end at the matching response.
Replies should be parsed as JSON and matched by exact request ID; substring
matching can confuse IDs such as `1` and `10`.

### 2. “Idle memory” excludes browser subprocesses

The original script reads only `/proc/{proc.pid}/status`. WebKit's network and
web-content processes are separate. The audit measures the entire descendant
tree and records the external Xvfb server separately.

Summed RSS double-counts pages shared between processes. PSS apportions shared
pages and is a more useful companion metric for the physical memory footprint.
Neither number is an executable's disk size.

### 3. Startup labeling is incomplete

The original startup timer is set after `Popen`, reader-thread startup, and HTTP
server setup. It excludes that initialization time. The `ready` event is also
emitted before the first real page has loaded. The audit measures both
**spawn-to-ready** and **first navigation after ready**.

A fresh process is not a disk-cold machine: this audit isolates Bruster's XDG
cache/config/data/state directories, but does not flush the operating system's
page caches.

### 4. Workload and provenance are too narrow for broad claims

- The original page is **143 bytes of static HTML**, without images or scripts.
- Each original CI invocation records a single timing for each operation.
- The environment label is hardcoded to GitHub Actions / Ubuntu 24.04, even
  when the script runs elsewhere.
- The site labels the workload “local file,” although it is served over local
  HTTP.
- No baseline or workload supports a general “30% faster” image-blocking claim
  or a fixed “halves memory” software-rendering claim.
- Linux currently forces software rendering in the application. This review
  has no hardware-accelerated control measurement for a memory-halving claim.

## Rerun methodology

The independent audit is reproducible with `scripts/bench_audit.py`.

- Release build, locked dependencies, optimized with LTO and stripped symbols.
- Frozen executable: **1,453,480 bytes**; SHA-256
  `af8ae4251671f7f862f8e9bf561cea042e381f59847930178a2eae540b76e85d`.
- Source: local commit `677d0b8e105126b37a0c27c1954571829607fb33` plus existing
  working-tree changes, recorded separately with source hashes and a diff.
- Ubuntu **26.04.1**, Linux x86_64, four visible CPUs, AMD Ryzen 5 PRO 5650U,
  approximately 3.82 GiB RAM; Rust **1.99.1**, WebKitGTK **2.52.6**.
- Dedicated Xvfb display, hidden windows, software rendering. The existing local
  native-library overlay supplies the runtime dependencies.
- Three reruns of the **unmodified original** benchmark, then ten audit rounds
  per mode: default and `--no-images`, with alternating mode order.
- Each mode has ten new browser processes, 100 warm tiny-page navigations, 100
  tiny-page snapshots, and 50 image-fixture navigations. The pilot is excluded.
- Timing starts before each request and ends when its exact-ID response is
  received. Navigation URL, document readiness, snapshot content, and image
  loading are checked.
- A deliberate **250 ms server delay** validates that the timer measures the
  requested navigation rather than a stale event.
- Memory is sampled three times after two seconds of idle on the tiny page;
  the within-run median is used before aggregating the ten runs.
- The large fixture is 72,729 bytes of HTML with 1,000 links and 1,000 inputs;
  snapshots request a limit of 2,500 and verify all 2,000 elements are returned.
- The image fixture has 12 PNGs, 49,363 bytes each, and an artificial 50 ms delay
  per image request. All fixture responses use `Cache-Control: no-store`.

The local OS, browser-engine version, hardware, and source revision differ from
the published CI run. Differences between those environments are **not evidence
of a performance regression or improvement**. The controlled comparison is
between local default and image-blocking modes on the same frozen executable.

## Rerun results

### Original script: bug reproduced

| Local original-script run | Reported startup | Reported page load | Snapshot | Parent RSS |
|---|---:|---:|---:|---:|
| 1 | 261 ms | **-1 ms** | 8 ms | 172.2 MiB |
| 2 | 218 ms | **-2 ms** | 8 ms | 172.1 MiB |
| 3 | 214 ms | **-3 ms** | 8 ms | 171.7 MiB |

All three runs still identify themselves as “GitHub Actions · ubuntu-24.04
x86_64,” demonstrating the hardcoded provenance error on this Ubuntu 26.04 host.

### Corrected audit: default mode

Measured **20:17:36–20:19:21 UTC**, including both modes. Ranges are observed
minimum–maximum, not confidence intervals. Repeated operations within one
browser process are correlated; the 100 operation samples span ten processes.

| Metric | Samples | Median | Observed range |
|---|---:|---:|---:|
| New process → `ready` | 10 | **220.6 ms** | 197.9–258.3 ms |
| First tiny-page navigation after ready | 10 | **643.0 ms** | 628.1–663.2 ms |
| Warm tiny-page navigation | 100 | **15.15 ms** | 5.09–31.30 ms |
| Tiny-page JSON snapshot | 100 | **2.39 ms** | 1.11–11.87 ms |
| Large-page navigation, 2,000 controls | 10 | **51.04 ms** | 47.78–58.26 ms |
| Large-page JSON snapshot, all 2,000 controls | 10 | **59.00 ms** | 55.73–84.03 ms |
| Idle main-process RSS | 10 | **171.98 MiB** | 171.22–172.23 MiB |
| Idle browser-tree summed RSS | 10 | **388.95 MiB** | 388.46–389.54 MiB |
| Idle browser-tree PSS | 10 | **217.14 MiB** | 215.84–217.82 MiB |
| Browser process count | 10 | **3** | 3–3 |

The median of each run's startup plus first-navigation duration was **874.9 ms**.
The published CI startup of 32.6 seconds was not reproduced locally; the different
environment prevents attributing this difference to an application speedup.

Observed processes were `bruster`, `WebKitNetworkProcess`, and
`WebKitWebProcess`. The external Xvfb server added a median **78.52 MiB RSS /
43.44 MiB PSS**. Browser-tree plus Xvfb PSS was **260.56 MiB**. Shared desktop
services are outside this process tree.

The delayed-navigation check measured **273.78 ms** for the injected 250 ms
server delay. All 20 browser sessions passed the response/content assertions;
all 60 memory samples had complete RSS/PSS accounting. Normal Xvfb EGL/DRI
software-rendering warnings were captured. Observed one-minute system load
averages ranged approximately 0.75–1.44 on four visible CPUs.

### `--no-images`: useful, workload-dependent

| Workload | Default median | `--no-images` median | Interpretation |
|---|---:|---:|---|
| Image-free tiny page, 100 loads/mode | 15.15 ms | 15.51 ms | No measured speed benefit |
| 12-image delayed fixture, 50 loads/mode | 118.20 ms | 16.46 ms | **86.1% shorter load time** |

The server observed **600 image requests** in default mode and **zero** in
image-blocking mode. Image dimensions confirmed successful loads in default
mode and blocked loads with `--no-images`.

This fixture intentionally makes images a bottleneck. Its result is not a
real-world average, and it does not validate a universal “30% faster” claim.
The original image-free CI page cannot measure that benefit at all.

### Text versus JSON snapshot size

Both formats were requested for the same documents, with identical element
limits. The wire measurement includes the JSON-lines response envelope and
string escaping; payload-only measurements exclude that envelope.

| Document | JSON response bytes | Text response bytes | Wire reduction |
|---|---:|---:|---:|
| Tiny page, five elements | 318 | 173 | **45.6%** |
| Large page, 2,000 controls | 139,650 | 67,620 | **51.6%** |

Payload-only sizes were 298 versus 135 bytes for the tiny page and 139,630
versus 61,597 bytes for the large page. The site's “about 45% smaller” statement
matches the tiny fixture's wire size reasonably well, but the saving depends
on content and which representation is counted. This audit does not establish
a randomized JSON-versus-text latency comparison: JSON was requested first.

### Claim assessment

| Claim | Assessment |
|---|---|
| “Less than 1 MB” executable | False for the measured current Linux build |
| “One process” browser | False for this run: three browser processes, plus Xvfb |
| Small complete runtime | Unsupported: executable plus linked libraries exceed 229 MB before optional resources |
| Published -2 ms page load | Invalid; original-script bug reproduced three times |
| Published idle memory describes the whole browser | False: it measures only the parent |
| “About 30% faster” without images | Workload-dependent; no general percentage established |
| Software rendering “halves memory” | Unverified; no controlled accelerated baseline |
| Text snapshots “about 45% smaller” | Supported for the tiny fixture; 51.6% for the large fixture |
| Bruster is faster/lighter than another tool | No controlled competitor comparison is published or established here |

## Disk footprint

Sizes below are uncompressed file bytes, deduplicated by device/inode, with the
same runtime-library environment used for the audit. MB means 1,000,000 bytes;
MiB means 1,048,576 bytes.

| Component set | Size |
|---|---:|
| Release executable, including its compiled Rust dependency code | 1.453 MB / 1.386 MiB |
| 123 dynamically linked native libraries | 227.973 MB |
| Executable plus those libraries | **229.426 MB** |
| Above plus WebKit helper executables/bundle and their linked libraries | 229.484 MB |
| Above plus Xvfb and its linked libraries | **232.704 MB** |

These are **lower bounds** on a self-contained runtime distribution: dynamically
loaded plugins, fonts, other data files, and packaging resources can add more.
They exclude build tools and compiler caches. Existing system libraries are
shared, so this is not necessarily the additional installation or download size
on a particular machine. This is also not a RAM measurement.

## Recommended publication changes

1. Replace “one process of less than 1 MB” with a measured, platform-qualified
   executable size and an explicit system-browser dependency statement.
2. Correct the website's KiB-to-MB/MiB conversion and use consistent unit labels.
3. Correct the CI timing implementation and reject negative durations and failed
   requests before publishing metrics.
4. Publish parent RSS, process-tree RSS, process-tree PSS, process count, and
   display-server overhead with clear definitions.
5. Publish repeated measurements, sample counts, variability, actual environment,
   exact source/binary identity, and startup/cache semantics.
6. Qualify image-blocking, text-size, and software-rendering benefits by workload;
   remove fixed percentages that lack a reproducible comparison.
7. Require an equivalent workload, engine/version disclosure, equal startup/cache
   conditions, and full process accounting for any future cross-tool comparison.

## Reproduction and evidence

On a Linux machine with the required native libraries and Xvfb installed:

```sh
cargo build --release --locked
xvfb-run -a python3 scripts/bench_audit.py \
  --binary target/release/bruster \
  --output /tmp/opencode/bruster-performance-review \
  --rounds 10 --iterations 10
```

This machine's full evidence directory is:

```text
/home/admin/Projects/.bruster-build/performance-review-2026-10-27/
```

It includes the frozen executable, original and audit benchmark copies, source
provenance, captured published documents, original-run outputs, corrected raw
samples, summary statistics, and the library footprint inventory.

Key files: `published-metrics.json`, `original-{1,2,3}.json`,
`corrected/summary.json`, `corrected/samples.json`, `footprint.json`,
`provenance.json`, and `run-review.py`. The runner recreates the original three
runs and the corrected 20-session experiment against the frozen executable.
