# Contributing

Report bugs and propose changes through [GitHub issues](https://github.com/aliilyas/bruster/issues).
Include your OS, Bruster version, and a small reproduction for bugs.

## Build

Install Rust 1.92 or newer and your platform's WebView development libraries. On Ubuntu/Debian:

```sh
sudo apt install libwebkit2gtk-4.1-dev libgtk-3-dev xvfb xauth
```

From a checkout:

```sh
cargo build --release --locked
```

Run `target/release/bruster` after building. See the
[installation guide](https://aliilyas.github.io/bruster/docs/#install) for other platforms.

The temporary GTK dependency patches and their upstream provenance are documented
in [`vendor/README.md`](vendor/README.md). Keep `vendor/` in source build contexts.

## Lint and format

Install Clippy and rustfmt for your active Rust toolchain:

```sh
rustup component add clippy rustfmt
```

From the repository root, run:

```sh
cargo lint
cargo fmt-check
```

`cargo lint` checks all targets (including tests) and features with the locked
dependencies, treating warnings as errors. It needs the same platform development
libraries as a build. Clippy reads the minimum supported Rust version from
`Cargo.toml`; keep fixes compatible with it. Run `cargo fmt --all` to apply
formatting. CI runs both checks on every supported platform.

## Tests

The user-facing `.bru` runner is covered by parser unit tests and real-browser
CLI tests. Run its focused checks with:

```sh
cargo test --release --locked --bin bruster testing::
cargo test --release --locked --test testing -- --test-threads=1
```

On headless Linux, prefix the second command with `xvfb-run -a`. See the
[DSL reference](docs/reference.md#ui-tests) and
[local example](examples/testing/greeting.bru) to author application tests.

Test the product website and demo-recording form with the DSL itself:

```sh
python3 scripts/site_test.py --binary target/release/bruster
```

The helper builds and serves a temporary site, then runs desktop and mobile
checks. It requires Python 3.11+. See the [example tests](example-tests/README.md)
for coverage, standalone commands, and failure artifacts.

The full test cycle needs Python 3.10+ and network access for end-to-end tests:

```sh
tests/run_all.sh
```

On Linux, prefix this with `xvfb-run -a`. The script runs the build, unit tests,
smoke and edge tests, focused Test Lab fixtures, process cleanup checks, MCP
launch, and public-site tests. Use `--no-e2e` for local tests, `--no-lab` to omit
the lab, or `--rounds N` to repeat smoke and edge tests.

CI runs smoke and edge tests **three times on each platform**, with one test at
a time and `--no-fail-fast`, so a failing edge binary does not hide smoke-test
failures. Every round must pass; these are repetitions, not retries that erase
an earlier failure. To reproduce locally:

```sh
RUST_TEST_THREADS=1 xvfb-run -a tests/run_all.sh --no-e2e --no-lab --rounds 3
```

Omit `xvfb-run -a` on macOS. Functional tests should assert replies, persisted
data, and observable page state. Use `GatedPage` in `tests/common/mod.rs` to
control resource completion when testing DOM/load/idle ordering, and
`Browser::wait_js` for asynchronous viewport changes. The shared reply/exit
watchdog catches hangs. Exact deadline-preservation rules belong in unit tests
that manipulate request state; latency measurements belong in
[`benchmarks/`](benchmarks/README.md).

Run the focused Test Lab fixtures through JSON lines and MCP:

```sh
cargo test --release --test test_lab
```

Check against the published site, including React, Vue, and Svelte apps:

```sh
cargo test --release --test test_lab -- --ignored --exact published_test_lab
```

The Python runner also accepts an existing executable and a case filter:

```sh
python3 scripts/test_lab.py run --binary target/release/bruster --case 'ref-*' --transport both
```

See [Test Lab setup and case authoring](tests/site/README.md) for the complete
core suite (`full_test_lab`), framework bundles, stress cases, and reports.
[CI](.github/workflows/ci.yml) runs the complete core lab on every platform
and publishes release archives on `v*` tags.

The Linux desktop-portal startup regression also needs D-Bus, `python3-dbus`,
and `python3-gi`:

```sh
xvfb-run -a /usr/bin/python3 tests/startup_portal.py target/release/bruster
```

## Docker

Build and test on a Linux Docker host using Python's standard library:

```sh
docker build -t bruster:local .
python3 tests/docker.py --image bruster:local --https
```

The checks cover MCP discovery, navigation, forms, JavaScript, screenshots,
tabs, HTTPS, and shutdown via MCP, stdin EOF, and SIGTERM. Containers run with
a 512 MiB memory limit, all capabilities dropped, and no new privileges.
The report includes image size, initialization time, and memory use.

The [Dockerfile](Dockerfile) pins both base images by digest. When updating
them, rerun checks for amd64 and arm64. [Docker CI](.github/workflows/docker.yml)
publishes the exact tested images after both architectures pass.

For the [Glama listing](https://glama.ai/mcp/servers/aliilyas/bruster), configure
the Dockerfile under **Admin → Docker builds**, use this repository as the build
context, and run its evaluation. The default command answers `initialize` and
`tools/list` without credentials.

## Documentation and benchmarks

- [CLI and API reference](docs/reference.md): source for the website's reference tables.
- [Website](site/README.md): local preview, publishing, and site checks (Python 3.11+).
- [Benchmarks](benchmarks/README.md): comparison setup, runtime footprint, and reporting.
- [Launch kit](launch/README.md): reproducible demo media and MCP bundle publication.
