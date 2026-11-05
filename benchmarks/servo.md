# Standalone Servo: installation, benchmarks, and shell operation

## Installed build

- Official [2026-11-03 nightly](https://github.com/servo/servo-nightly-builds/releases/tag/2026-11-03),
  reporting `Servo 0.8.0-189034510`.
- Exact source: [`1890345105cb3c1da550346a4a528538d996f819`](https://github.com/servo/servo/tree/1890345105cb3c1da550346a4a528538d996f819).
- Linux x86_64 archive: 49,109,690 bytes.
- Archive SHA-256, verified against the official release asset metadata:
  `0875e7d51b6a4809e0de191b9b7950fc883e40591743a78228c893a75a47df54`.
- Local installation: `/home/admin/.local/opt/servo-2026-11-03`.
- Launcher: `/home/admin/.local/bin/servo` (already on this machine's PATH).
- Application-menu entry: `Servo Nightly`.

The executable needed `libgstwebrtc-1.0.so.0`. Because sudo required an
interactive password, Ubuntu's `libgstreamer-plugins-bad1.0-0` package
(`1.28.2-1ubuntu1.2`, amd64) was downloaded and extracted into the installation's
`deps/` directory. The launcher supplies that private library path. No
system-package installation was needed.

Run the standalone graphical browser:

```sh
servo https://example.com
```

## Shell/headless operation

**Supported and tested without `DISPLAY`, `WAYLAND_DISPLAY`, or Xvfb.**
The same `servoshell` executable provides both the graphical demo browser and
headless execution. Its headless implementation uses software rendering and a
dedicated event loop that does not create an operating-system window.

For a one-shot screenshot:

```sh
servo --headless --exit --window-size=1023x640 \
  --output=/tmp/opencode/servo-page.png https://servo.org/
```

The CLI path was verified against a local HTML/CSS/JavaScript fixture: it wrote
a 1023×640 PNG and exited successfully in about 494 ms. **Include `--exit`:**
`--output` alone wrote its screenshot but remained running in this nightly.
The source's older comment claiming that output implies exit does not match
the current argument-to-preference assignment. Evidence is in
`results/servo-2026-11-04/cli-one-shot.json` and `cli-exit.png`.

Start a persistent automation instance:

```sh
servo --headless --webdriver=7000 --window-size=1023x640 about:blank
```

In another terminal, create a WebDriver session, navigate, and evaluate JavaScript:

```sh
SESSION=$(curl -fsS -H 'Content-Type: application/json' \
  -d '{"capabilities":{"alwaysMatch":{"pageLoadStrategy":"normal"}}}' \
  http://127.0.0.1:7000/session | python3 -c 'import json,sys; print(json.load(sys.stdin)["value"]["sessionId"])')

curl -fsS -H 'Content-Type: application/json' \
  -d '{"url":"https://example.com"}' \
  "http://127.0.0.1:7000/session/$SESSION/url"

curl -fsS -H 'Content-Type: application/json' \
  -d '{"script":"return {title:document.title, text:document.body.innerText};","args":[]}' \
  "http://127.0.0.1:7000/session/$SESSION/execute/sync"

curl -fsS -X DELETE "http://127.0.0.1:7000/session/$SESSION/servo/shutdown"
```

The built-in interface is WebDriver over HTTP, rather than Bruster's JSON-lines
stdio protocol or Chromium's CDP. In this revision its listening address is
hard-coded to `0.0.0.0`; the CLI accepts a port, not a bind-address argument.

The standalone benchmark also exercises CSS selectors, real WebDriver text
entry and clicking, synchronous JavaScript, asynchronous fetch, localStorage,
cookies, page-source retrieval, multiple tabs, PNG screenshots, and graceful
shutdown. It validates returned values rather than merely timing responses.

## Benchmark reproduction

```sh
python3 scripts/bench_servo.py \
  --bundle "$HOME/.local/opt/servo-2026-11-03" \
  --output benchmarks/results/servo-new-run \
  --rounds 5 --iterations 5
```

Add `--modes headless` for a terminal-only machine. Each run needs a new output
directory so previous evidence is preserved.

The [local report](results/servo-2026-11-04/report.md), JSON samples, process-tree
memory measurements, screenshots, logs, executable/harness hashes, machine
context, and runtime-file inventory are in `benchmarks/results/servo-2026-11-04/`.
These local results are gitignored; this is a standalone experiment and is not
published into the continuous competitor comparison.

### Measured results on this machine

Medians; five sessions per mode and 25 samples per repeated workload:

| Metric | Headless | Graphical |
|---|---:|---:|
| Process launch to WebDriver/JS ready | 149.73 ms | 430.27 ms |
| Launch, viewport setup, and first local page | 182.50 ms | 937.27 ms |
| Repeated small local page load | 11.02 ms | 29.51 ms |
| 2,000-control/link page load | 61.08 ms | 90.80 ms |
| Twelve images, each with a 50 ms server delay | 68.48 ms | 111.01 ms |
| Extract and validate 2,000 DOM records | 31.48 ms | 26.83 ms |
| Idle process-tree PSS | 225.57 MiB | 368.12 MiB |
| Idle process-tree RSS | 231.28 MiB | 374.57 MiB |

All ten sessions completed with graceful shutdown and no failed benchmark
checks. The installed bundle plus private GStreamer dependency is **139.07 MB**;
the runtime-file lower bound including observed system libraries/fonts is
**368.09 MB**. The latter includes already-installed shared files, not just
additional disk consumption.

The graphical setup column includes deliberate waits while matching viewport
dimensions, so it should not be interpreted as the browser's natural first-paint
latency. Full ranges are retained in the report: notably, headless large-page
navigation and extraction each had an approximately 0.65-second outlier.

Separate HTTPS smoke checks rendered `servo.org` and `example.com`. The first
example.com checker incorrectly assumed an `h1` existed; the retained follow-up
shows its valid `Example Domain` title, page source and screenshot with no `h1`.
These public-site checks are not included in performance statistics.

Method:

- Five fresh processes and config/cache directories per mode, alternating order.
- Identical, verified 1023×640 viewports at device scale 1. The headed X11/egui
  build rounded an even requested width to neighboring odd values, so both
  modes use the same attainable odd width. Failed geometry pilots are retained.
- Startup means process launch through WebDriver session creation and a successful
  JavaScript evaluation. Viewport adjustment is measured separately in setup.
- Local HTTP fixtures use `Cache-Control: no-store`. Navigation waits for `load`,
  checked with a deliberately delayed image, readyState and decoded image sizes.
- Small HTML, 1,000 links plus 1,000 inputs, and twelve 128×128 PNGs. Each image
  response has a controlled 50 ms delay. The server backlog is enlarged to avoid
  measuring TCP connection-queue retries when Servo fetches images concurrently.
- DOM extraction validates all 2,000 records. Screenshots validate PNG dimensions.
- JavaScript arithmetic and DOM/grid-layout tests are synthetic microbenchmarks,
  not Speedometer/JetStream or a claim about broad website performance.
- Idle memory is sampled three times after the first small page, before stress
  workloads. It includes Servo's process tree but excludes the Python controller
  and existing desktop display server. PSS apportions shared pages; RSS can
  double-count them.
- OS file caches are not flushed. Existing desktop applications remain running.
  This Ubuntu 26.04 x86_64 KVM guest has four vCPUs and about 3.8 GiB RAM; the
  headed display reports no accelerated DRI3. Results describe this environment.

## Source map and Bruster feasibility

All links below are pinned to the installed nightly's exact source revision.

| Concern | Source | Finding |
|---|---|---|
| Executable and CLI | [`ports/servoshell/prefs.rs`](https://github.com/servo/servo/blob/1890345105cb3c1da550346a4a528538d996f819/ports/servoshell/prefs.rs) | `--headless`, `--webdriver`, `--output`, `--exit`, `--config-dir`, `--temporary-storage`, `--multiprocess` |
| Console event loop | [`desktop/event_loop.rs`](https://github.com/servo/servo/blob/1890345105cb3c1da550346a4a528538d996f819/ports/servoshell/desktop/event_loop.rs) | Explicitly supports console execution without a display server |
| Headless rendering | [`desktop/headless_window.rs`](https://github.com/servo/servo/blob/1890345105cb3c1da550346a4a528538d996f819/ports/servoshell/desktop/headless_window.rs) | `SoftwareRenderingContext`, virtual viewport and screenshot support |
| Automation implementation | [`components/webdriver_server/lib.rs`](https://github.com/servo/servo/blob/1890345105cb3c1da550346a4a528538d996f819/components/webdriver_server/lib.rs) | Navigation, scripts, actions, cookies, windows/tabs and screenshots; Servo shutdown extension |
| Rust embedding interface | [`components/servo/webview.rs`](https://github.com/servo/servo/blob/1890345105cb3c1da550346a4a528538d996f819/components/servo/webview.rs) | `WebViewBuilder`, `load`, `evaluate_javascript`, `take_screenshot`, input and resize APIs |
| Minimal Rust embedder | [`examples/winit_minimal.rs`](https://github.com/servo/servo/blob/1890345105cb3c1da550346a4a528538d996f819/components/servo/examples/winit_minimal.rs) | `ServoBuilder`, `WebViewBuilder`, event-loop waking and rendering |

**A headless Servo backend for Bruster is technically feasible.** The lowest-effort
prototype would spawn the existing executable and translate Bruster operations
into WebDriver calls. The benchmark already demonstrates that control path using
only Python's standard library. A native Rust integration could instead own
`Servo` and `WebView` objects and use their asynchronous callbacks, with the
headless shell as the reference implementation for rendering and event-loop
ownership. That embedding path was inspected in source, not built here.

The nightly's WebDriver capability response reports `browserVersion: "0.0.1"`
despite `--version` reporting `0.8.0-189034510`; use the binary version and hash
for provenance. The results assess basic automation and local fixtures, not
compatibility with every modern website. Servo remains an experimental engine.
