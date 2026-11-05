# Bruster example tests

These `.bru` suites exercise the built product website and the form from
[`examples/launch-demo`](../examples/launch-demo), originally used by
[`scripts/launch_media.py`](../scripts/launch_media.py) for demo recordings.
The [web automation testing guide](https://aliilyas.github.io/bruster/guides/web-automation-testing/)
embeds the executable test sources at build time.

- [`demo/recording.bru`](demo/recording.bru): the recorded form workflow and screenshots.
- [`demo/components.bru`](demo/components.bru): inputs, dropdown, checkbox, validation, and receipts.
- [`website/pages.bru`](website/pages.bru): page navigation, metadata, and the tutorial-to-demo journey.
- [`website/components.bru`](website/components.bru): FAQ, tabs, keyboard focus, and copy feedback.
- [`website/mobile.bru`](website/mobile.bru): mobile navigation and tutorial layout.

Try the [published demo](https://aliilyas.github.io/bruster/demo/) in a browser.
The tutorial links to downloadable copies of these files under `/example-tests/`.

## Run everything locally

Install the [build dependencies](../CONTRIBUTING.md#build) and Python 3.11+:

```sh
cargo build --release --locked
python3 scripts/site_test.py --binary target/release/bruster
```

Use `target/release/bruster.exe` on Windows. Older release executables may lack
`bruster test`; check with `bruster test --help`. Add `--visible` to watch the
windows, or `--output PATH` to change the default `target/website-results`.
On headless Linux, install Xvfb and xauth; you can prefix the command with
`xvfb-run -a` to share a virtual display across all tests.

The helper builds the actual website, binds an OS-assigned localhost port, serves
it under `/bruster/` to catch project-path mistakes, and runs four groups. It
shuts down the server afterward, preserves reports, and returns nonzero if any
group fails. Execution requires no network services, accounts, or Node.js.

| Group | Tests | What it checks |
| --- | --- | --- |
| Website desktop, 960×640 | `pages.bru`, `components.bru` | Product and install content, navigation/history, docs anchors, comparison/benchmarks, article metadata and demo link, FAQ, MCP tabs and keyboard focus, clipboard feedback |
| Website mobile, 375×640 | `mobile.bru` | Menu open/close, Escape/focus, link navigation, page overflow, tutorial code layout |
| Demo desktop, 960×640 | `recording.bru`, `components.bru` | Recorded submission with screenshots, default state, text editing, select options, check/uncheck, required-field validation and recovery, repeat submission, literal text rendering |
| Demo mobile, 375×640 | Same demo files | The same form workflows at a narrow viewport, including an overflow check |

Clipboard tests stub only the clipboard API to exercise both success and
rejection deterministically. They assert the passed text, UI feedback, and
fallback selection, rather than reading an OS clipboard. Screenshots are
inspection artifacts, not pixel-diff assertions. Native input and browser-engine
boundaries are described in the [DSL reference](../docs/reference.md#ui-tests).

## Run against an existing website preview

In one terminal:

```sh
python3 scripts/site_build.py --output target/site --base-url http://127.0.0.1:8000/
python3 -m http.server 8000 --bind 127.0.0.1 --directory target/site
```

In another:

```sh
target/release/bruster test example-tests/website/pages.bru example-tests/website/components.bru --viewport 960x640
target/release/bruster test example-tests/website/mobile.bru --viewport 375x640
target/release/bruster test example-tests/demo/recording.bru example-tests/demo/components.bru --base-url http://127.0.0.1:8000/demo/
```

For a deployed build containing the article and demo, override with
`--base-url https://aliilyas.github.io/bruster/` for website files and
`--base-url https://aliilyas.github.io/bruster/demo/` for demo files. Keep the
trailing slash: all navigation paths are relative to that directory. The
canonical checks expect the server URL to match the build's `--base-url`.

## Run only the original recording fixture

```sh
python3 -m http.server 8765 --bind 127.0.0.1 --directory examples/launch-demo
```

From a second terminal:

```sh
target/release/bruster test example-tests/demo/recording.bru example-tests/demo/components.bru
```

Each invocation writes a unique results directory with `results.json`, per-test
logs, requested screenshots, and attempted failure screenshots/DOM/console
diagnostics. The cross-platform CI workflow runs the helper and retains its
evidence. Tests remain readable, directly runnable `.bru` files; Python handles
only the local build/server and group invocation.
