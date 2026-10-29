# Contributing

Report bugs and propose changes through [GitHub issues](https://github.com/aliilyas/bruster/issues).
Include your OS, Bruster version, and a small reproduction for bugs.

## Build

Install Rust and your platform's WebView development libraries. On Ubuntu/Debian:

```sh
sudo apt install libwebkit2gtk-4.1-dev libgtk-3-dev xvfb xauth
```

From a checkout:

```sh
cargo build --release --locked
```

Run `target/release/bruster` after building. See the
[installation guide](https://aliilyas.github.io/bruster/docs/#install) for other platforms.

## Tests

The full test cycle needs Python 3.10+ and network access for end-to-end tests:

```sh
tests/run_all.sh
```

On Linux, prefix this with `xvfb-run -a`. The script runs the build, unit tests,
smoke and edge tests, focused Test Lab fixtures, process cleanup checks, MCP
launch, and public-site tests. Use `--no-e2e` for local tests, `--no-lab` to omit
the lab, or `--rounds N` to repeat smoke and edge tests.

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
