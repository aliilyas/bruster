# Bruster Test Lab

The [published catalog](https://aliilyas.github.io/bruster/test-lab/) and the
automated runner use the same executable case definitions. Each case has an
individual HTML route, setup, Bruster commands, and explicit observations.
The catalog supports search, category/contract/environment filters, source and
assertion inspection, and importing a matching `results.json` report.

## Build and run

Use Python 3.10+, Node 20+, a built Bruster executable, and its native browser
runtime. Node is needed only to bundle the three framework fixtures and validate
generated JavaScript; the runner and local HTTP server use Python's standard
library.

```sh
cargo build --release --locked
npm ci --prefix tests/site/frameworks --ignore-scripts --no-audit --no-fund
node tests/site/frameworks/build.mjs target/test-lab-frameworks
python3 scripts/test_lab.py serve --frameworks target/test-lab-frameworks
```

Open <http://127.0.0.1:8080/bruster/test-lab/>. The second loopback origin is
printed at startup. Ctrl-C stops both HTTP servers.

The runner builds its own site and starts both servers automatically:

```sh
python3 scripts/test_lab.py run --binary target/release/bruster \
  --frameworks target/test-lab-frameworks --transport both
```

On Linux, prefix the command with `xvfb-run -a` when there is no desktop display.
On Windows, use the path to `bruster.exe`. A launcher executable can also be
passed as `--binary`; the reported executable hash then identifies that launcher.

```sh
# One case, or repeated glob filters (quote globs to avoid shell expansion).
python3 scripts/test_lab.py run --binary target/release/bruster \
  --case select-invalid-multi --case 'ref-*' --transport native

# Stress cases are opt-in. --suite all includes core and stress.
python3 scripts/test_lab.py run --binary target/release/bruster --suite stress

# Exercise the published fixtures; local-server-only cases report explicit skips.
python3 scripts/test_lab.py run --binary target/release/bruster \
  --url https://aliilyas.github.io/bruster/test-lab/ --transport both
```

Without `--frameworks`, builds omit framework bundles and the three framework
cases report missing prerequisites. Bundles are pinned by
[`frameworks/package-lock.json`](frameworks/package-lock.json), served locally,
and include dependency license notices. No CDN is needed during test execution.

## What is checked

- **HTML and extraction:** headings, labels and accessible names, nested text,
  Unicode, snapshot limits, attributes versus properties, selectors and regexes.
- **Target identity:** duplicate names, moved/renamed/replaced nodes, stale and
  unknown references, refreshed find mappings, and wrong-target counters.
- **Forms and editing:** input types, textareas, contenteditable, disabled
  fieldsets, validation, submission/reset, radios, checkboxes, option matching,
  multiselect atomicity, and file names, contents, clearing, and failed uploads.
- **CSS and rendering:** flex/grid/table/columns, logical and vertical layout,
  transforms, visibility, clipping, overlays, nested scrolling, responsive and
  container queries, SVG, canvas, images, media, and screenshot pixel samples.
- **Events and composed trees:** propagation, cancellation, key modifiers,
  synthetic hover, drag payloads, open/closed shadow roots, slots, same-origin
  and cross-origin frames, and frame replacement.
- **JavaScript and lifecycle:** microtasks, promises, timers, observers, waits,
  deadlines and late responses, navigation/history/reloads, tabs and init scripts,
  serialization, console output, and nonblocking dialogs.
- **HTTP and persistence:** redirects, DOM/load milestones, request gates,
  fetch/XHR, status and header handling, body limits, aborts, CORS, network idle,
  cookies, local/session storage, profiles, IndexedDB, and workers.
- **Application flows:** real React/Vue/Svelte controlled inputs, duplicate-name
  search results, hidden login decoys, modal editing, and virtualized records.
- **Stress:** large DOMs, bounded console collection, large Unicode replies,
  and repeated tab creation/closure.

Tests launch a fresh Bruster process for every case and transport. Persistent
profile tests restart their own process with a temporary profile. Prerequisites
record unsupported native input types, platform-specific screenshot features,
server access, and framework availability as skips with reasons.

## Results and failure evidence

The default output is `target/test-lab-results/<UTC timestamp>/`. Override it
with `--output <fresh-directory>`. Existing reports are never overwritten.

| Status | Meaning |
| --- | --- |
| `pass` / `fail` | Required behavior satisfied / violated |
| `probe-pass` / `probe-fail` | Explicit compatibility question satisfied / violated |
| `skip` | A declared prerequisite is unavailable |
| `error` | Fixture setup, transport, runner, or cleanup failed |

Exit status is **1** for required failures or errors, **2** when every selected
case is skipped, and **0** otherwise. `--strict-probes` also makes probe failures
fatal. Probes are declared in source before execution; failures are never
automatically relabeled or silently retried.

`results.json` and `index.html` summarize observations. Every case retains its
step results, JSONL wire transcript, and stderr. Failures additionally request
the current state/event trace, snapshot, console, network log, and screenshot.
Screenshot assertions decode real PNG pixels, including device-pixel scaling;
a nonempty payload alone does not satisfy a color assertion. JSON equality
distinguishes booleans from numbers. Expected command errors cannot be satisfied
by transport failure. Reports record fixture source SHA-256, source commit,
executable hash, OS, browser user agent, viewport, and DPR. The local runner's
revision is recorded separately when testing a published manifest. State checks
use structured observations so MCP's plain scalar text cannot confuse a numeric
input string with a JavaScript number.

Import a report into the catalog to annotate its cases. The fixture source hash
must match, so an old report cannot label different assertions as passing.
Opening an HTML fixture by itself does not execute or grade Bruster.

## Add or change a case

Definitions live in `scripts/lab/cases.py`, `interactions.py`, and `lifecycle.py`.
Use a stable kebab-case ID and one focused behavioral question per case:

```python
case('example-save', 'Save activates exactly once', 'Events',
     '<button id="save" onclick="__lab.state.count++">Save</button>',
     [command('click', {'selector': '#save'}), check('__lab.state.count', 1)],
     setup='__lab.state.count=0')
```

`command()` supports `expect`, a JavaScript `verify` predicate over `result`,
`error` substring matching, typed `capture` values, and screenshot `image`
assertions. `{{name}}` substitutes a captured value without losing its JSON type.
`send` / `await` pairs support concurrent commands; explicit server gates release
HTTP work without relying on arbitrary sleeps. `__lab.ready` marks fixture setup
completion. The fixture instrumentation observes events; grading happens in the
external runner.

Validation commands:

```sh
python3 scripts/test_lab.py validate
python3 -m unittest discover -s scripts -p 'test_test_lab.py'
python3 scripts/test_lab.py build --frameworks target/test-lab-frameworks
node scripts/test_lab_check.mjs target/test-lab
python3 scripts/test_lab_ui.py --binary target/release/bruster
```

CI runs the core suite through native JSONL and MCP on its Linux, macOS, and
Windows matrix and retains reports/evidence for 30 days, including failed runs.

## Publication

[`benchmark-pages.yml`](../../.github/workflows/benchmark-pages.yml) checks out
the latest `main` and `gh-pages` after acquiring the existing Pages deployment
lock. It bundles frameworks, validates the lab, copies the existing docs and
benchmark tree, generates `test-lab/`, and adds a Test Lab navigation link.
The combined artifact preserves benchmark history and `CNAME`.

Deployment runs after relevant `main` changes, successful benchmark workflows,
or **Run workflow → main** on **benchmark pages**. Pages must use the existing
**GitHub Actions** source. Generated lab files are build output rather than
committed copies; merging the source and workflow changes enables publication.

To inspect the assembled artifact locally:

```sh
python3 scripts/test_lab.py assemble --existing /path/to/gh-pages-checkout \
  --output target/published --frameworks target/test-lab-frameworks
node scripts/test_lab_check.mjs target/published/test-lab
```

Assembly requires a fresh output directory. Never point it at the existing
documentation checkout.

## Research notes

The test design was informed by the
[`vercel-labs/agent-browser` test suite at `5801a50`](https://github.com/vercel-labs/agent-browser/tree/5801a50d262a4d3e1a2381996a962b22000d8289).
Useful patterns included recording event sequences, checking duplicate-label
and wrong-target behavior, asserting unchanged state after failed actions,
and inspecting screenshot pixels. These fixtures are authored for Bruster's
native-engine and synthetic-event contracts; compatibility probes make
differences such as caret editing and pointer-driven dragging observable.
