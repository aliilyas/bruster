# Temporary GTK 0.19 compatibility patches

Bruster uses GTK 0.19 and GLib 0.22 throughout its Linux dependency graph. This
removes vulnerable GLib 0.18 (`RUSTSEC-2024-0429`) and the unmaintained
`proc-macro-error` (`RUSTSEC-2024-0370`). GLib and the GTK macro crates come from
their released, fixed versions on crates.io. Rust 1.92 or newer is required.

Released Wry and Tao still depend on GTK 0.18. These directories contain their
current release sources with the GTK migration from the upstream pull requests
applied. Keeping the current releases preserves fixes added after those pull
requests branched. This is temporary application-maintained third-party code;
review upstream updates along with the regular dependency scans.

## Provenance

| Directory | Published release / source commit | Migration |
| --- | --- | --- |
| `wry/` | `wry 0.57.1`, [`2446feadae623d6f2ac8d2136e3ccef3d7197e0e`](https://github.com/tauri-apps/wry/commit/2446feadae623d6f2ac8d2136e3ccef3d7197e0e) | [PR #1843](https://github.com/tauri-apps/wry/pull/1843), head `327242ae73301c5e34dcc158e31ae453e8afe837` |
| `tao/` | `tao 0.37.2`, [`2d9b2ba15247879787878ae565e350bcc1b9f622`](https://github.com/tauri-apps/tao/commit/2d9b2ba15247879787878ae565e350bcc1b9f622) | [PR #1332](https://github.com/tauri-apps/tao/pull/1332), head `08660027c723e09a45b10badf60a73a661c94a95` |

The published crate archives were verified against the original `Cargo.lock`
checksums before import:

```text
759c50ddad0ef9913bb5496cb9d509a50433a3b78cb0238d61105526589cf0e9  wry-0.57.1.crate
d5777b06fe6435126ae8d816eba269e050e1e10d302cf5461e9c49eccabc3548  tao-0.37.2.crate
```

Upstream licenses, source attribution, and `.cargo_vcs_info.json` are retained.
The registry's `.cargo-ok` marker, redundant `Cargo.toml.orig`, upstream
development lockfiles, and Wry's development-only `.cargo/` configuration
(including its audit exceptions) are omitted; Bruster's root lockfile and Cargo
configuration resolve the build.
Upstream's `LICENSE.spdx` metadata text is retained as `LICENSE.spdx.txt`
(with a trailing newline normalized where needed):
it is not a valid SPDX SBOM (`DataFormat` is an unknown tag), and the `.txt`
extension prevents OSV from trying to parse the license notice as a lockfile.
One trailing space in Wry's `SECURITY.md` is also normalized for `git diff --check`.

Changes from the published sources:

- Both normalized `Cargo.toml` files: Rust 1.92 and the new GTK-related
  dependency requirements; Tao also adds `async-channel` as upstream does.
- Wry: `src/webkitgtk/{mod,web_context}.rs` use the new GLib imports and
  `clone!` syntax.
- Tao: `src/platform/unix.rs`, and `src/platform_impl/linux/{device,event_loop,
  portal,util,window}.rs` adopt the new imports and replace removed GLib channels
  with `async-channel` receivers driven by the GLib main context.

The root manifest also pins **both** `webkit2gtk` and `webkit2gtk-sys` to the
upstream GTK migration [PR #167](https://github.com/tauri-apps/webkit2gtk-rs/pull/167),
commit `f5c3825c3f21c44ce346a5aa42e8c33a762f9f72`. This supplies matching GTK 0.19 /
GLib 0.22 bindings. `deny.toml` allows that repository and requires revision-pinned
Git dependencies. All four overrides are necessary to keep one GTK/GLib stack.

## Verification and removal

Run the standard release build, Clippy, unit tests, and native smoke/edge tests
from `CONTRIBUTING.md`. The release unit test
`webkit_compat::tests::variant_string_iterator_handles_both_ends` exercises every
iterator entry point affected by the GLib advisory. Native tests cover navigation,
window sizing, events, and screenshot encoding after the binding migration.

Run OSV-Scanner, cargo-audit, and cargo-deny using
[`docs/dependency-security.md`](../docs/dependency-security.md). The root lockfile
must contain only GLib 0.22 and no `proc-macro-error` or `proc-macro-error-attr`.

Once released Wry, Tao, and WebKit bindings all support GTK 0.19 / GLib 0.22,
update them together, remove the four root overrides, these vendored sources,
the WebKit Git allowlist entry, and the Docker vendor copy. Regenerate the
lockfile and rerun the scans and native tests. Until then the direct Wry/Tao
requirements are exact so a version update explicitly revisits these patches.
