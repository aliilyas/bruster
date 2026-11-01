# Continuous browser comparisons

[`benchmarks.yml`](../.github/workflows/benchmarks.yml) runs after every push to
`main` (including merged, squashed and rebased PRs), and through **Run workflow**
on `main`. Each run builds that exact Bruster commit and resolves the **latest
stable npm releases** of Playwright, Puppeteer, agent-browser, Stagehand,
browse.sh, Playwright MCP, Cypress, Ui.Vision's MCP bridge, Rustwright,
Rustwright MCP, Biloba and the MCP client SDK. Transitive dependencies can
include prereleases selected by those upstream packages; the full lockfile
records them. Node uses the
latest release available to `setup-node`. Dependency installs explicitly request
`@latest` with online metadata; no previous run's lockfile selects versions.

Full Chrome for Testing and Headless Shell come from the newly resolved
Playwright release. Playwright's browser manifest determines those builds;
they are not independently selected from Chrome's stable channel. All
full-Chrome configurations use the same executable.
Ui.Vision's official extension is downloaded from the Chrome Web Store; its
version, CRX hash and unpacked-manifest change are recorded separately.

## Competitors from Hacker News

The inventory in [`competitors.json`](competitors.json) covers the story and
complete public comment tree of [this discussion](https://news.ycombinator.com/item?id=49756671),
reviewed on 2026-11-01, plus the user-requested Rustwright, Rustwright MCP and
Biloba additions from separate stories. It records GitHub repositories, individual source
comments or stories, execution status, and comparison boundaries. Each new measurement
embeds this inventory in its provenance and renders a coverage table on the
benchmark page, including tools that are not measured. It is not an exhaustive
search of all Hacker News submissions.

| Competitor | GitHub | Benchmark coverage |
|---|---|---|
| Playwright | [microsoft/playwright](https://github.com/microsoft/playwright) | Full Chrome and Headless Shell |
| agent-browser | [vercel-labs/agent-browser](https://github.com/vercel-labs/agent-browser) | Native CLI and daemon, full Chrome |
| Stagehand | [browserbase/stagehand](https://github.com/browserbase/stagehand) | Local v4 SDK, bundled extension, full Chrome |
| browse.sh | [Stagehand `packages/cli`](https://github.com/browserbase/stagehand/tree/main/packages/cli) | Real `browse` CLI and daemon, full Chrome |
| Playwright MCP | [microsoft/playwright-mcp](https://github.com/microsoft/playwright-mcp) | Actual stdio MCP server and tools, full Chrome |
| SleepyHollow | [bensyverson/sleepyhollow](https://github.com/bensyverson/sleepyhollow) | Separate same-Mac timing job against Bruster / Apple WebKit |
| Cypress | [cypress-io/cypress](https://github.com/cypress-io/cypress) | Real spec runner, proxy, application iframe and task IPC, full Chrome |
| Ui.Vision MCP | [A9T9/RPA](https://github.com/A9T9/RPA/tree/master/mcp) | Official extension, open panel and real MCP bridge, full Chrome |
| Rustwright | [Skyvern-AI/rustwright](https://github.com/Skyvern-AI/rustwright) | Public Node SDK with in-process Rust engine, full Chrome |
| Rustwright MCP (requested as “Rust MCP”) | [Rustwright `mcp/`](https://github.com/Skyvern-AI/rustwright/tree/main/mcp) | Actual native Rust MCP server and tools, full Chrome |
| Biloba | [onsi/biloba](https://github.com/onsi/biloba) | Public TypeScript SDK and Go daemon, full Chrome |

Rustwright's separate HN stories are [48923788](https://news.ycombinator.com/item?id=48923788),
[48932230](https://news.ycombinator.com/item?id=48932230) and
[49319583](https://news.ycombinator.com/item?id=49319583); Biloba's is
[49699819](https://news.ycombinator.com/item?id=49699819). “Rust MCP” was confirmed
to mean Rustwright's native MCP server in the same repository.

Puppeteer remains an additional baseline from the existing suite; it was not
named in this thread. Jev/TypeSafe is a **decision model integrated into
Stagehand**, not another browser. Browserbase is a hosting service. Codex,
Claude Code, Deep Agents, Mastra, Vercel Eve and Fx are agent harnesses/frameworks. Their
verified links and source comments are recorded under `related_mentions`.
Stagehand's integration docs resolve Eve to `vercel/eve` and Fx to
`vercel-labs/fx`. No authoritative standalone browser repository was identified
for the Astra computer-use mention; unrelated namesakes are not substituted.

### Adapter boundaries

- Rustwright uses its published Node SDK for navigation, evaluation and
  screenshots. The experimental SDK has no viewport setter, so startup uses
  its public CDP endpoint to provision 1280×800 at device scale 1. That setup
  connection remains idle during the workload (Chromium ties viewport overrides
  to the connection) and is included in memory accounting. The Node SDK has no
  native snapshot API; shared DOM extraction is measured normally.
- Rustwright MCP launches the native server directly from its official npm
  binary package, through the MCP client SDK. Its automatic response snapshots
  and an explicit load-boundary check are included in timings. Text-response
  limits are requested as unlimited so large evaluation results can be checked;
  the server's native snapshot traversal can still truncate, which is recorded.
- Biloba uses its public TypeScript `connect`/session APIs and the real `bilobad`
  Go daemon. The daemon launches a fresh full Chrome per round. Navigation uses
  `navigateWithStatus`, evaluation uses `evaluate`, and viewport PNG captures use
  `captureScreenshot`; daemon transport and file writes are counted. This serial
  workload does not measure Vitest/Ginkgo scheduling or parallel test-suite
  throughput. Native accessibility outlines can truncate, which is recorded.
- Ui.Vision runs its official extension in an isolated full-Chrome profile with
  its panel open and its actual stdio MCP bridge. Playwright only provisions and
  closes that browser. Navigation uses `browser_snapshot({url})`; extraction uses
  `run_macro` with `uiv.evaluate` and `uiv.log`; screenshots use the MCP `screenshot`
  tool. Large evaluated values are retrieved in 12,000-character chunks to fit
  its log transport, with every call and default post-run snapshot counted.
  The native snapshot's 60,000-character cap is recorded as truncation; shared
  extraction still validates all 2,000 elements. The extension, panel, bridge,
  provisioning SDK and browser are included in resource accounting. Browser
  tools work headlessly without the optional desktop helper.
- Cypress runs its real CLI and spec runner, with one protocol request per
  Cypress test, `testIsolation: false` and retries disabled. Navigation uses
  `cy.visit`, extraction uses `cy.window`, and screenshots use `cy.screenshot`.
  Timings include the controller, runner and task round trips, plus copying
  Cypress's named screenshot to the requested output path. Chrome's outer
  window leaves room for the 1280×800 application iframe; PNG dimensions are
  checked. Expected fault probes return protocol errors even though the spec
  continues to the next recovery test. Cypress has no native snapshot API, so
  that diagnostic is explicitly unsupported; the shared extraction is measured.
  The installed Cypress/Electron bundle and its owned Xvfb process are counted
  in addition to the full Chrome browser. Installation and verification happen
  before measurement; fresh project/spec setup remains inside startup timing.
- SleepyHollow runs in the workflow's `macos-timing` job alongside a native
  Bruster build on that same Mac (the `macos-26` runner, providing Swift 6.3+).
  It builds the current upstream source and
  records its commit, Swift version, lockfile and binary hash. `sleepy open`
  starts a fresh named session; `load`, `eval`, `shot` and `close` use that
  session. Timings include every CLI launch. Fixture checks cover delayed load,
  viewport, extraction hashes, images and screenshots. Both screenshots use
  that Mac's native display backing scale, verified from the PNG dimensions.
  Results and failures
  appear in the workflow summary and `macos-benchmarks-*` artifact. Apple's XPC
  helpers need different resource accounting, so this timing-only cohort is
  not inserted into the Linux PSS/footprint table. Native execution must be
  validated on the macOS runner.
- Stagehand uses `localBrowser.launch`, `Stagehand.create` and its public
  `Page` APIs. Its extension is loaded normally. These are deterministic
  navigation/extraction tests, not `act()`/`extract()` model inference tests.
- browse.sh invokes the installed CLI for every command. Startup includes its
  daemon, browser, extension and viewport setup. All commands explicitly use
  a fresh local session; update checks are disabled during measurement.
- Playwright MCP launches the installed server over stdio and uses its
  `browser_*` tools through the official MCP SDK. It retains default response
  snapshots. Since its navigation may finish at DOMContentLoaded, the adapter
  includes a subsequent MCP evaluation waiting for `load` in navigation timing.
  Client and server processes are both counted. Its own Playwright dependency
  can differ from the standalone API version; inspect the archived lockfile.
- The measurements do not establish LLM token efficiency, task success, cloud
  latency, or AI inference cost. Unmeasured entries have explicit reasons and
  no fabricated timings. A new adapter must pass all fixture checks before its
  status becomes `linux` in the registry.

## One-time repository setup

1. Set **Settings → Pages → Build and deployment → Source → GitHub Actions**.
2. The `github-pages` environment must permit deployment from `main`
   if you restrict deployment branches. Remove any obsolete
   branch-source-only restriction.
3. Repository rules must permit the workflow's `GITHUB_TOKEN` to push to
   `gh-pages`; the measurement job requests `contents: write`. No PAT is needed.
4. Merge these workflow files into `main`, or run **benchmarks** manually on
   `main` afterward. Both workflows must be on the default branch for the
   `workflow_run` deployment trigger to operate.

Results: <https://aliilyas.github.io/bruster/benchmarks/>. Existing site files and
custom domains are preserved. The legacy performance section, if present, is
replaced with a link to the corrected comparison page.

## Measurements and publication

- Ubuntu 24.04 x86_64; ten fresh sessions for each of thirteen configurations:
  Bruster/WebKitGTK/Xvfb, Playwright/Headless Shell, Playwright/full Chrome,
  Puppeteer/full Chrome, native agent-browser/full Chrome, Stagehand/full Chrome,
  browse.sh/full Chrome, Playwright MCP/full Chrome, Cypress/full Chrome,
  Ui.Vision MCP/full Chrome, Rustwright/full Chrome, Rustwright MCP/full Chrome,
  and Biloba/full Chrome.
- Rotating order; localhost HTTP fixtures; 1280×800 viewport; navigation waits
  for `load`; identical JavaScript for DOM extraction. Both object and JSON-string
  returns are measured. The delayed-load check, image counts, screenshot PNG
  dimensions and extraction hashes check that each tool actually did the work.
- Reports show startup/setup separately from first navigation, alongside the
  combined launch-to-first-page time. Timings and memory display medians and
  observed min–max ranges. Repeated-operation timings pool iterations; memory
  uses each session's median of three idle samples. Ranges are not confidence
  intervals. OS, CPU, RAM, runner image and engine versions appear above the table.
  Xvfb is started before measurement; its launch time is excluded from startup.
- Idle PSS covers the entire process forest, detached daemons and crashpad
  helpers. Bruster includes Xvfb. RSS is also recorded with its scope labeled.
- Installed-file sizes include tool packages, browsers/engines, Node where
  required, linked libraries and observed mapped files. They are **lower bounds**:
  unobserved OS resources can add more. MB means decimal bytes; memory uses MiB.
- Incomplete, contaminated, inconsistent or negative measurements fail
  validation. Fault-probe failures remain visible even if a retry recovers;
  they do not discard valid timings. A failing measurement retains available
  evidence as an artifact and leaves the last valid published comparison intact.
- Every run archives the generated exact dependency manifest/lockfile, actual
  versions, browser/executable hashes, hardware, runner image and harness hashes.
  Native Rustwright and Biloba runtime artifacts are hashed separately; installed
  optional platform packages and their linked libraries are included in inventories.
  Native OS packages follow Ubuntu updates; the WebKit version and installed
  Debian package versions are recorded, along with GTK and desktop-session
  environment settings that can affect startup.
- `report.md` appears in the Actions job summary. Raw samples, process listings,
  screenshots, snapshots, inventories and logs are retained as an Actions
  artifact for 90 days, including evidence from failed runs.

The `gh-pages` branch retains these files without the artifact expiry:

```text
benchmarks/index.html                        latest comparison and history
benchmarks/latest.json                       latest validated measurement
benchmarks/history.json                      all run links
benchmarks/runs/<commit>-<run-id>-<attempt>/  per-run HTML, Markdown, JSON,
                                            raw samples, file inventory,
                                            resolved npm manifest and lockfile
```

Measurement jobs have **no shared concurrency group**, so close merges do not
replace pending runs. Publication retries non-fast-forward pushes by fetching
the latest branch and regenerating history. Results are immutable per run
attempt; “latest” is chosen by workflow invocation number, not completion order.
Explicitly published local validations use a separate `local-<timestamp>` record
ID and a visible local-run label. Their context records the measured Bruster
commit, harness commit, publication time and the latest published workflow number.
They sort after that invocation; a later workflow run supersedes
them normally. Their downloadable `evidence.tar.gz` preserves screenshots,
native snapshots, logs and the exact harness, with its SHA-256 in the record.

[`benchmark-pages.yml`](../.github/workflows/benchmark-pages.yml) explicitly
deploys the accumulated, validated `gh-pages` measurements when the benchmark
workflow completes, with the [product website](../site/README.md) and
[Test Lab](../tests/site/README.md) generated from the latest `main`.
Relevant website and test-lab source changes on `main` also trigger the combined deployment.
A failure in the separate macOS job does not block validated Linux results.
If Linux validation fails, only the previously published measurements are deployed.
A `GITHUB_TOKEN` push alone does not trigger another push workflow or a Pages
build. Only deployments are coalesced; every measurement has already been
persisted. Each deployment reads both latest branches after taking the Pages lock,
builds the pinned framework fixtures, validates the lab, and assembles one artifact
containing documentation, benchmarks, and `test-lab/`. Benchmark history and
custom-domain configuration are preserved.
After manual `gh-pages` updates, use **Run workflow → main** on **benchmark pages**
to deploy the site. If a deployment fails, rerun **benchmark pages**; no
measurement rerun is necessary.

## Local execution

Install the Linux runtime dependencies used in the workflow, plus Rust, Node
and Python 3.12+. Use a fresh dependency directory; `@latest` resolves current
releases while `npm ci` against an archived manifest/lockfile reproduces a run.

```sh
export BENCH_DEPS=/tmp/opencode/bruster-bench-deps
export PLAYWRIGHT_BROWSERS_PATH=/tmp/opencode/bruster-bench-browsers
mkdir -p "$BENCH_DEPS"
cp benchmarks/package.json "$BENCH_DEPS/"
npm install --prefix "$BENCH_DEPS" --save-exact --prefer-online --ignore-scripts \
  playwright-core@latest puppeteer-core@latest agent-browser@latest \
  @browserbasehq/stagehand@latest browse@latest @playwright/mcp@latest @modelcontextprotocol/sdk@latest \
  cypress@latest uivision-mcp-bridge@latest rustwright@latest rustwright-mcp@latest biloba@latest
chmod +x "$BENCH_DEPS/node_modules/agent-browser/bin/agent-browser-linux-x64"
node "$BENCH_DEPS/node_modules/playwright-core/cli.js" install --with-deps chromium --no-shell
node "$BENCH_DEPS/node_modules/playwright-core/cli.js" install chromium-headless-shell
export CYPRESS_CACHE_FOLDER="$BENCH_DEPS/cypress-cache"
node "$BENCH_DEPS/node_modules/cypress/bin/cypress" install
node "$BENCH_DEPS/node_modules/cypress/bin/cypress" verify
node benchmarks/browser-paths.mjs "$BENCH_DEPS" > "$BENCH_DEPS/browser-paths.env"
. "$BENCH_DEPS/browser-paths.env"
python3 scripts/bench_install_uivision.py --chrome "$BENCH_CHROME" --deps "$BENCH_DEPS"
cargo build --release --locked
xvfb-run -a python3 scripts/bench_compare.py \
  --bruster target/release/bruster --node "$(command -v node)" \
  --chrome "$BENCH_CHROME" --shell "$BENCH_SHELL" \
  --deps "$BENCH_DEPS" --output benchmarks/results
python3 scripts/bench_footprint.py \
  --bruster target/release/bruster --node "$(command -v node)" \
  --chrome "$BENCH_CHROME" --shell "$BENCH_SHELL" --deps "$BENCH_DEPS" \
  --samples benchmarks/results/samples.json --output benchmarks/results/footprint.json
```

For a focused adapter check, append `--tools rustwright rustwright-mcp biloba
--rounds 1 --iterations 1` to the comparison command. The footprint and report
code use the selected configurations from the run, and archived five-tool
records retain their original columns. Full workflow measurements use the
entire registered Linux set.

On macOS, build SleepyHollow with `swift build -c release` in its checkout, then:

```sh
python3 scripts/bench_sleepyhollow.py --bruster target/release/bruster \
  --sleepy /path/to/sleepyhollow/.build/release/sleepy \
  --sleepy-source /path/to/sleepyhollow --output benchmarks/macos-results
```

Publication logic tests (no browsers or network required):

```sh
python3 -m unittest discover -s scripts -p 'test_bench_*.py'
```

Runner variance and changing competitor versions make cross-run changes
ambiguous; inspect versions and hardware before attributing a change to Bruster.
