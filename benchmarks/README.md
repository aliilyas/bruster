# Continuous browser comparisons

[`benchmarks.yml`](../.github/workflows/benchmarks.yml) runs after every push to
`main` (including merged, squashed and rebased PRs), and through **Run workflow**
on `main`. Each run builds that exact Bruster commit and resolves the **latest
stable npm releases** of Playwright, Puppeteer and agent-browser. Node uses the
latest release available to `setup-node`. Dependency installs explicitly request
`@latest` with online metadata; no previous run's lockfile selects versions.

Full Chrome for Testing and Headless Shell come from the newly resolved
Playwright release. Playwright's browser manifest determines those builds;
they are not independently selected from Chrome's stable channel. All
full-Chrome configurations use the same executable.

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
custom domains are preserved. The known legacy `scripts/bench.py` performance
section, if present, is replaced with a link to the corrected comparison page.

[Review of published runs 1–4 and the startup investigation](REVIEW.md).

## Measurements and publication

- Ubuntu 24.04 x86_64; ten fresh sessions for each of five configurations:
  Bruster/WebKitGTK/Xvfb, Playwright/Headless Shell, Playwright/full Chrome,
  Puppeteer/full Chrome, and native agent-browser/full Chrome.
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

[`benchmark-pages.yml`](../.github/workflows/benchmark-pages.yml) explicitly
deploys the accumulated `gh-pages` tree after a successful benchmark workflow.
A `GITHUB_TOKEN` push alone does not trigger another push workflow or a Pages
build. Only deployments are coalesced; every measurement has already been
persisted. Each deployment reads the latest branch after taking the Pages lock.
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
  playwright-core@latest puppeteer-core@latest agent-browser@latest
chmod +x "$BENCH_DEPS/node_modules/agent-browser/bin/agent-browser-linux-x64"
node "$BENCH_DEPS/node_modules/playwright-core/cli.js" install --with-deps chromium --no-shell
node "$BENCH_DEPS/node_modules/playwright-core/cli.js" install chromium-headless-shell
node benchmarks/browser-paths.mjs "$BENCH_DEPS" > "$BENCH_DEPS/browser-paths.env"
. "$BENCH_DEPS/browser-paths.env"
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

Publication logic tests (no browsers or network required):

```sh
python3 -m unittest discover -s scripts -p 'test_bench_*.py'
```

Runner variance and changing competitor versions make cross-run changes
ambiguous; inspect versions and hardware before attributing a change to Bruster.
The original controlled experiment and failure investigation are in
[`COMPETITOR_COMPARISON.md`](../COMPETITOR_COMPARISON.md). Its historical versions
describe that experiment; the continuous workflow always resolves latest releases.
