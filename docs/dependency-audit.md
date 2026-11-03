# Dependency reduction audit

Audited 2026-11-03 at commit `9b32bed9c17a23b8a78eb9b89343e3633c05521f`
(Bruster 0.3.3). The investigation uses the checked-in lockfile, actual call
sites, the exact resolved upstream crate sources, target-specific Cargo graphs,
and isolated build experiments. Eleven key upstream source files were compared
with cached crate archives whose SHA-256 hashes match `Cargo.lock`.

## Recommendation

**Trim upstream features and unnecessary dependency edges first. Keep the
serialization and native ABI libraries.** The largest practical opportunity is
Tao's unconditional URL dependency, not any small helper in Bruster.

1. Disable **Wry's** `x11` feature; Bruster embeds through `build_gtk` on Linux.
2. Seek an upstream Tao change making URL-open events optional or platform-scoped.
   A small local experiment removes the URL/ICU tree on Linux and Windows.
3. Preserve desktop theme behavior when considering Tao's `dbus` feature. Removing
   it reduces size, but fails an existing behavioral test. Reusing GTK's GIO
   D-Bus support is a better follow-up if that behavior is required.
4. If substantially fewer dependencies are still valuable, prototype a small
   Linux GTK window/event-loop adapter replacing Tao. Measure that before taking
   ownership of a cross-platform webview implementation.

The behavior-preserving graph target from steps 1–2 is **142 → 115 packages on
Linux (−19.0%)**, **84 → 57 on Windows (−32.1%)**, and **83 on macOS**. Achieving
step 2 currently requires a Tao patch; it is not an existing feature switch.
This reduces the build dependency tree: the tested Linux executable actually
grows by about 2.7 KiB. Reducing installation size is a different goal, dominated
by the native browser runtime.

## What is actually being built?

Counts below are unique external package versions reachable for each target,
including build dependencies and procedural macros. They exclude Bruster itself
and upstream crates' development dependencies. A package count is neither a
runtime-library count nor a measurement of code retained after linking.

| Scope | Direct declarations | External packages |
|---|---:|---:|
| Entire `Cargo.toml` / `Cargo.lock` | 15 | 261 |
| Linux x86_64 or arm64 | 8 | 142 |
| macOS arm64 or x86_64 | 10 | 83 |
| Windows x86_64 MSVC | 6 | 84 |

The lockfile also resolves unsupported mobile targets. In particular, Wry's
`base64`, `dom_query`/HTML/CSS parsing, and `sha2` dependencies are Android paths,
not desktop browser parsing or screenshot encoding. Deleting those lockfile
entries would not reduce a desktop build and would not be a durable Cargo change.

### Direct dependency decisions

| Dependency | Actual use | Assessment |
|---|---|---|
| `wry` 0.57.0 | Webviews, IPC, scripts, navigation, cookies, profiles, proxy configuration | Keep; trim features. Replacing it means implementing three native backends. |
| `tao` 0.37.1 | Windows, sizes/positions, event loop, cross-thread event proxy | Best larger reduction target. First fix its unnecessary URL edge. |
| `serde` 1.0.229 | Request/envelope derives and saved window preferences | Keep. Handwritten serialization mostly moves tested behavior into Bruster. |
| `serde_json` 1.0.151 | Both wire protocols, arbitrary page values, MCP schemas, preferences, borrowed `RawValue` fast path | Keep. Broad, performance-sensitive use rather than a tiny replaceable parser call. |
| `libc` | Unix `dup2` and `flock` | Already required by native dependencies. Handwriting these declarations removes zero packages. |
| `gtk` 0.18.2 | Linux draw suppression in `trim_webkit`; GTK embedding through Tao/Wry | Already shared by Tao, Wry and WebKit bindings. Keep the explicit dependency. |
| `webkit2gtk` 2.0.2 | Snapshots, settings, data/cache policy, dialogs, downloads, TLS/load events, process cleanup | Extensively used beyond screenshots; already shared with Wry. |
| `cairo-rs` 0.18.5 | Native surface cropping and PNG encoding | Already shared by GTK/WebKit. The `png` feature adds native Cairo functionality, not a Rust image-codec tree. |
| `webview2-com`, `windows` | Windows navigation IDs/events, history, capture callback and COM stream | Already shared with Wry/Tao. Manual COM declarations would save no packages while those remain. |
| `objc2`, `block2`, `objc2-foundation`, `objc2-app-kit`, `objc2-web-kit` | macOS navigation delegate, retained objects/blocks, snapshots and PNG encoding | Already shared with Wry/Tao. Framework features are already explicitly selected. |

Evidence: [`Cargo.toml`](../Cargo.toml), [`src/main.rs`](../src/main.rs),
[`src/screenshot.rs`](../src/screenshot.rs),
[`src/navigation_macos.rs`](../src/navigation_macos.rs),
[`src/navigation_windows.rs`](../src/navigation_windows.rs),
[`src/window_state.rs`](../src/window_state.rs), and
[`src/mcp.rs`](../src/mcp.rs). Every direct dependency has an actual use.

Removing a direct declaration or replacing it with a re-export does not remove a
crate that another dependency still needs. Cargo also unifies dependency
features additively: narrowing Bruster's feature list cannot disable a feature
that Wry or Tao enables. [Cargo feature documentation][cargo-features]

## 1. Wry's X11 feature: a small, straightforward reduction

Wry 0.57.0 defaults to exactly `os-webview` and `x11`. Bruster's Linux path uses
`window.default_vbox()` and `WebViewBuilderExtUnix::build_gtk`, not Wry's
raw-window-handle/Xlib embedding path.

```toml
wry = { version = "0.57", default-features = false, features = ["os-webview"] }
```

This removes **`gdkx11`**, reducing Linux's graph from **142 to 141**. Tao still
uses `gdkx11-sys` and `x11-dl`, so those remain. GTK still supports X11 and Bruster
can still run under Xvfb. Keep **Tao's** `x11` feature for the existing desktop
and headless-display paths.

There is no desktop graph reduction on macOS or Windows. Advice about disabling
older Wry features such as `protocol` does not apply to this locked version;
those are not switches in Wry 0.57.0's feature table. [Wry manifest][wry-manifest],
[GTK backend][wry-gtk]

## 2. Tao → URL → ICU: the main opportunity

Tao declares `url` as a platform-independent dependency. Its public
`Event::Opened { urls: Vec<url::Url> }` keeps that dependency in every desktop
build. Actual URL parsing/event producers in this version are in macOS, iOS and
Android code. Bruster ignores the event.

On Linux and Windows, the resulting build graph includes `url`, `idna`,
`idna_adapter`, seven ICU packages, and supporting string/zero-copy/proc-macro
packages even though Bruster does not use this facility.

### Experiment

In a temporary copy of Tao 0.37.1:

- Move `[dependencies.url]` to
  `[target.'cfg(any(target_os = "macos", target_os = "ios", target_os = "android"))'.dependencies.url]`.
- Apply the same `cfg` to `Event::Opened` and its three match arms in
  `Clone`, `map_nonuser_event` and `to_static`.
- Point an isolated Bruster manifest at that copy using `[patch.crates-io]`.

That is five targeted edits to Tao, with no replacement URL parser.

| Configuration | Linux | macOS | Windows |
|---|---:|---:|---:|
| Baseline | 142 | 83 | 84 |
| Wry X11 off | 141 | 83 | 84 |
| Wry X11 off + Tao URL platform-scoped | **115** | **83** | **57** |
| Also disable Tao D-Bus | 113 | 83 | 57 |

The URL change alone removes **26 Linux packages** or **27 Windows packages**.
Windows additionally loses `percent-encoding`; Wry still needs it on Linux.
The Linux set accounts for about **3.42 MB of Rust source** and **1.81 MB of cached
crate archives**. These are source/archive measurements, not executable savings.

The behavior-preserving variant still has **260 external lockfile entries**:
macOS and mobile targets retain the URL tree. Target-specific counts capture
this improvement; comparing lockfile length alone would almost entirely miss it.

**Upstream API design matters:** removing an enum variant on some platforms can
break other Tao consumers. A default-enabled, optional URL-event feature would
provide a more compatible upstream solution; Bruster could opt out. The
platform-scoping patch is a proof of feasibility for this application.

### Why macOS retains the tree

Both Tao's native open-URL events and Wry's `cookies_for_url` use `url` on macOS.
Removing only Tao's edge therefore saves nothing there. Bruster uses `cookies()`
rather than `cookies_for_url()`, so optionalizing both unused capabilities is a
further upstream opportunity: deleting both edges from the current macOS graph
disconnects **28 packages**. That is a graph analysis, not an implemented macOS
replacement. Keep a real URL implementation for any API that still parses
URLs; string splitting is not an equivalent substitute.

Sources: [Tao manifest][tao-manifest], [Tao events][tao-events],
[Wry macOS cookie implementation][wry-macos].

## 3. Tao's D-Bus feature: useful savings with a real behavior change

```toml
tao = { version = "0.37", default-features = false, features = ["rwh_06", "x11"] }
```

This removes `dbus` and `libdbus-sys` on Linux: **142 → 140**, or **141 → 139**
after the Wry change. Its purpose in Tao is the desktop portal's color-scheme
query and theme-change subscription. Bruster's hidden mode already bypasses the
session bus by default, but visible mode and `BRUSTER_USE_SESSION_BUS=1` retain it.

The audit ran [`tests/startup_portal.py`](../tests/startup_portal.py):

- Baseline passes.
- Disabling Tao's D-Bus feature fails the positive control: the portal observes
  `org.freedesktop.portal.Inhibit`, but not `org.freedesktop.portal.Settings`.

Consequently this is **not a behavior-preserving default change**. Choose an
explicit automation-only build policy, or preserve theme behavior by changing
Tao's portal implementation to use the GIO bindings already provided by GTK.
`gio::DBusProxy` can perform the settings query and receive signals without
introducing a second Rust D-Bus stack. That replacement has not been implemented
or measured in this audit. The required APIs (`for_bus_sync`, `call_sync`, and
`connect_g_signal`) exist in the already resolved GIO 0.18.4 bindings, re-exported
by GTK; preserve the existing five-second timeout and theme-change delivery.

The combined Wry-X11/Tao-D-Bus experiment also removes `libdbus-1.so.3` from the
executable's direct ELF dependencies. It does not establish that the entire
GTK/WebKit installation can drop D-Bus. Keep the hidden-startup handling for
GTK's separate portal interactions. [Tao portal implementation][tao-portal]

## 4. Where our own code or extraction could help

### A narrow Linux window adapter is the most plausible larger replacement

Bruster handles `UserEvent`, close requests, window identity, sizing, positioning,
visibility and state. It does not consume Tao's full native input/device API.
GTK and GLib are already present through Wry/WebKit, making a small adapter over
`gtk::Window`, the GLib main context and its cross-thread dispatch a credible
prototype.

Pruning Tao from the current graph while retaining Wry gives:

| Existing graph | Packages remaining without Tao |
|---|---:|
| Linux baseline | 102 |
| Linux after Wry X11 off and Tao D-Bus off | 98 |
| macOS | 72 |
| Windows | 44 |

These are **graph-pruning figures, not compiled replacements**. They retain
currently enabled features on remaining crates and exclude any dependencies a
replacement might need. They are not additive to the URL savings: most of the
Linux/Windows benefit already comes from dropping Tao's URL tree.
After the behavior-preserving Wry/URL changes, replacing all of Tao disconnects
only **17 additional Linux packages** or **13 additional Windows packages** before
accounting for the replacement. This makes the small upstream change the better
first investment.

A Linux prototype must preserve mapped off-screen windows for screenshots,
viewport/DPI conversion, close and shutdown ordering, event-proxy wakeups, and
request deadlines. `spawn_deadline_timer` already documents a Tao/GTK wakeup
pitfall. On macOS and Windows, replacing Tao also transfers responsibility for
the native application/message loop and parent-window lifetimes to Bruster.

Prefer a small Bruster-specific interface over copying an entire general-purpose
windowing crate. Extracted Tao code remains Apache-2.0 code; retain its notices
and record the upstream version and local patch.

### Smaller upstream extraction opportunities

Counts here describe disconnected packages in the current graph, not measured
working forks. Each needs upstream changes or a maintained patch.

| Candidate | Possible reduction | Assessment |
|---|---|---|
| Make Wry's default download-directory handling optional | 3 on Linux/macOS: `dirs`, `dirs-sys`, `option-ext` | Worth discussing upstream. Linux Bruster cancels downloads and provides no Wry download-destination callback. Preserve behavior on other platforms. |
| Replace Wry `once_cell` use with `std::sync::{LazyLock, OnceLock}` | 1 on macOS/Windows; 0 on Linux | Small, reasonable upstream cleanup; GTK and X11 dependencies retain it on Linux. Both standard types fit Wry's declared Rust floor. |
| Handwrite Wry's error implementation instead of `thiserror` | 2 on Linux/macOS; 0 on Windows | Low priority. Windows retains thiserror through `webview2-com-sys`'s build dependency; other macros keep `syn`/`quote`. |
| Replace Wry's `cookie` representation with a small native-cookie record | 7 on Linux; 8 on macOS/Windows | Larger API/backend change. Bruster exposes few cookie fields, but Wry converts expiry, SameSite and other native state. Not a small caller-side substitution. |
| Replace Bruster's Serde derives with manual implementations | 1 on every desktop target: `serde_derive` | Poor tradeoff. `syn`, `quote` and `proc-macro2` remain for other users. Adds request/default/borrowed-envelope/persistence maintenance. |

Removing Wry entirely while keeping today's direct native bindings disconnects
only 16 baseline Linux packages, 17 macOS packages, or 13 Windows packages. Its
larger value is working native integration. Replacing Wry and Tao together is a
backend rewrite, including IPC installation, initialization scripts, profiles,
cookies, popups, async evaluation and navigation lifecycle handling.

Pruning both leaves 80 Linux, 25 macOS or 28 Windows packages before adding any
replacement code/dependencies. Linux's remaining GTK/GLib bindings and their
build machinery are substantial. Extracting only their used FFI calls would
require eliminating every remaining consumer of the full wrappers and taking
ownership of GObject reference counts, signal closures and thread-affinity rules.
Vendoring a library without changing that dependency graph does not reduce it.

## 5. Reductions that would not pay off

- **Handwritten JSON:** `serde_json` itself and its exclusive number-formatting
  dependency account for only two exclusively reachable Linux packages; macOS
  and Windows add `memchr`. Arbitrary page results, escaping, numeric IDs,
  borrowed `RawValue` validation and MCP serialization are substantial behavior.
- **Handwritten native bindings:** replacing only Bruster's calls removes zero
  GTK/Cairo/WebKit, Objective-C or Windows packages while Wry/Tao use them.
- **A custom PNG encoder:** Cairo already encodes the native surface; macOS and
  Windows likewise use native encoders. It would add maintenance without removing
  the existing graphics dependencies.
- **Pruning framework feature lists only in Bruster:** upstream enables the
  union. `windows` 0.62.2 also declares `windows-collections`, `windows-future`
  and `windows-numerics` unconditionally; setting `default-features = false`
  here would not remove them.
- **Forcing duplicate major versions together:** Linux legitimately contains
  `syn` 1/2/3, `thiserror` 1/2, `bitflags` 1/2, two `proc-macro-crate` versions,
  and their older TOML helpers. Their APIs are not interchangeable. Removing
  Bruster's one derive feature does not collapse these trees.

The code already makes sensible small-code substitutions: base64 encoding,
argument parsing, MIME lookup, state-directory selection, timers/channels and
the stdio MCP adapter use local code or the standard library. There is no
production Node, async executor, HTTP-client, CLI-parser or image-codec dependency
to remove.

## 6. Tooling and native-runtime dependencies

- **Framework fixtures:** five direct packages and 70 lockfile entries, including
  25 optional entries, in `tests/site/frameworks`. React, Vue and Svelte are the
  actual systems under test; reproducing their behavior locally would weaken
  coverage. Esbuild already bundles and minifies them. Vue deliberately uses
  templates and its compiler-enabled entry point. These packages do not ship in
  the Bruster executable.
- **MCP integrations:** this checkout's generated, gitignored manifest/lock has
  two direct packages and 233 entries. The Inspector brings its own UI/server
  stack. Splitting Inspector into a dedicated compatibility job can reduce
  routine setup costs, but replacing the official clients would remove the
  independent interoperability check. `tests/integrations.sh` currently installs
  live versions; a committed manifest/lock and `npm ci` would make these tests
  reproducible. The current 233 count is local state, not a guaranteed CI graph.
- **Benchmarks:** 12 direct competitor/client packages. Resolving `latest` is an
  intentional, documented benchmark policy, with per-run manifests and locks
  archived. Install only selected competitors for targeted local runs; preserve
  complete comparative runs and their provenance.
- **Website:** the product site's Python build already uses the standard library.
- **Linux runtime:** WebKitGTK, GTK and a display remain necessary with either
  feature configuration. The Dockerfile already uses a separate build stage and
  `--no-install-recommends`. Rust feature trimming does not remove the browser
  engine, Xvfb or the system libraries from the runtime installation.

Two relevant maintenance facts from the resolved sources:

- `gtk` 0.18.2's README explicitly marks the GTK 3 Rust bindings unmaintained.
  Wry/Tao require this family; switching only Bruster's direct dependency to GTK 4
  is not a compatible upgrade. A future Linux-backend redesign should include
  this consideration.
- The manifest advertises Rust 1.85, but resolved ICU packages and `time` 0.3.55
  declare Rust 1.88 requirements (`idna_adapter` requires 1.86). Align the stated
  minimum or resolve/test an MSRV-compatible lockfile. Removing the URL tree
  alone leaves the `time` requirement.

## Measurements, validation and reproduction

Release builds use the repository's existing settings: `opt-level = 3`, LTO,
one codegen unit and stripping, with Rust 1.99.1 on Linux x86_64. Experiments use
separate temporary manifests and the same application sources. Build caches are
warm; elapsed build times are **not** comparable clean-build benchmarks.

| Isolated Linux release configuration | Packages | Executable bytes | Change from baseline |
|---|---:|---:|---:|
| Baseline | 142 | 1,474,104 | — |
| Wry X11 off | 141 | 1,472,128 | −1,976 (−0.13%) |
| Tao D-Bus off | 140 | 1,404,480 | −69,624 (−4.72%) |
| Both feature changes | 139 | 1,402,456 | −71,648 (−4.86%) |
| Wry X11 off + Tao URL platform-scoped; D-Bus retained | **115** | **1,476,896** | **+2,792 (+0.19%)** |
| Both feature changes + Tao URL platform-scoped | 113 | 1,407,240 | −66,864 (−4.54%) |

The three-crate feature reduction saves about 70 KiB, mostly through removal of
theme integration. The much larger URL-tree reduction does not shrink the
executable. LTO can already eliminate unused URL/ICU implementation code;
dependency count and executable size need separate measurements. No clean-build
speedup, runtime-memory improvement or installation-size reduction is claimed.

### Validation completed

- **Wry X11 off:** release build, all 34 smoke tests and the desktop-portal
  regression pass under Xvfb.
- **Wry X11 off + platform-scoped Tao URL, with D-Bus retained:** release build;
  8 unit, 24 edge, 34 smoke and 2 focused Test Lab tests pass (**68 Rust tests**).
  The lab groups cover navigation/tabs and rendering/application workflows over
  both native JSONL and MCP. The desktop-portal regression also passes.
- **Windows:** `cargo check --release --locked --target x86_64-pc-windows-msvc`
  passes for the combined feature experiment, its URL-patched variant, and the
  final D-Bus-retaining Wry/URL variant. Windows binaries were not executed.
- **macOS:** dependency graphs were resolved for both architectures. Cross-checks
  of the feature and URL experiments were blocked while building
  `objc2-exception-helper`: this Linux environment lacks an Apple-capable C/ObjC
  compiler. No successful macOS build/runtime validation is claimed.
- **Linux arm64:** target graph verified; build/runtime validation was on x86_64.
- **Known behavioral failure:** the D-Bus-removing configuration fails the portal
  positive control described above. It is not a drop-in replacement.

The Linux browser runtime is locally unpacked in this environment. Initial test
attempts outside its filesystem overlay could not start WebKit helpers; baseline
portal startup failed for the same reason. The successful native tests above use
the existing read-only `/usr` overlay with those libraries. Those initial runs
are not counted as application validation.

To reproduce the graph investigation on a machine with Rust installed:

```sh
cargo tree --locked --target x86_64-unknown-linux-gnu -e normal,build
cargo tree --locked --target x86_64-unknown-linux-gnu -e features -i tao
cargo tree --locked --target x86_64-unknown-linux-gnu -i url
cargo tree --locked --target x86_64-unknown-linux-gnu --duplicates
cargo metadata --locked --format-version 1 --filter-platform aarch64-apple-darwin
cargo metadata --locked --format-version 1 --filter-platform x86_64-pc-windows-msvc
```

For the tested Wry/URL variant on a normally provisioned Linux host:

```sh
cargo build --release --locked
xvfb-run -a cargo test --release --locked --no-fail-fast \
  --bin bruster --test smoke --test edge -- --test-threads=1
xvfb-run -a cargo test --release --locked --test test_lab -- \
  --exact navigation_and_tabs rendering_and_application_workflows --test-threads=1
xvfb-run -a python3 tests/startup_portal.py target/release/bruster
```

Count reachable package IDs from `resolve.root`, not all lockfile entries or all
packages mentioned in an unfiltered metadata document. To compare variants,
copy the manifest and lock into a temporary checkout, apply the changes described
above, and let Cargo update only that copy's lockfile. Subsequent builds should
use `--locked`. Measure the stripped executables, and run the native smoke/edge,
rendering, profile, navigation and portal tests before adopting a variant.

The audit's local experiment manifests, patched Tao source, graph JSON, binaries
and logs are under `/tmp/opencode/bruster-dependency-audit/`. Production dependency
declarations are not modified by this report.

[cargo-features]: https://doc.rust-lang.org/cargo/reference/features.html#feature-unification
[wry-manifest]: https://docs.rs/crate/wry/0.57.0/source/Cargo.toml
[wry-gtk]: https://docs.rs/crate/wry/0.57.0/source/src/webkitgtk/mod.rs
[wry-macos]: https://docs.rs/crate/wry/0.57.0/source/src/wkwebview/mod.rs
[tao-manifest]: https://docs.rs/crate/tao/0.37.1/source/Cargo.toml
[tao-events]: https://docs.rs/crate/tao/0.37.1/source/src/event.rs
[tao-portal]: https://docs.rs/crate/tao/0.37.1/source/src/platform_impl/linux/portal.rs
