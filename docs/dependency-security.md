# Dependency security checks

The README badges link to the latest scan results for `main`. Each scanner runs
on pushes, pull requests, daily, and through **Actions → Run workflow**. Scan logs
are retained as workflow artifacts for 30 days, including when findings fail a
check.

| Check | Scope | Daily schedule (UTC) |
| --- | --- | --- |
| [cargo-audit](../.github/workflows/audit.yml) | `Cargo.lock` against RustSec, including yanked-crate checks | 06:23 |
| [cargo-deny](../.github/workflows/deny.yml) | Rust advisories and dependency sources, with all features enabled | 06:28 |
| [OSV-Scanner](../.github/workflows/osv.yml) | Recursively discovered supported manifests and lockfiles | 06:33 |
| [Trivy](../.github/workflows/trivy.yml) | Repository dependency vulnerabilities, including supported development dependencies | 06:38 |

Findings retain the scanner's nonzero exit status, except for the two
[reviewed GTK3 advisories](#reviewed-exceptions) below. cargo-audit reports
informational advisories as warnings, while cargo-deny can fail on unmaintained
dependencies. Inspect the linked logs as well as the badge. A passing check
describes the scanner's coverage and policy at that run, rather than certifying
code safety.

## Run locally

Install [cargo-audit and cargo-deny](https://rustsec.org/),
[OSV-Scanner](https://github.com/google/osv-scanner), and
[Trivy](https://trivy.dev/), then run from the repository root:

```sh
cargo audit --file Cargo.lock
cargo deny --locked check advisories sources
osv-scanner scan source --recursive .
trivy fs --scanners vuln --include-dev-deps --no-progress \
  --ignorefile .trivyignore.yaml --show-suppressed --exit-code 1 .
```

The `cargo-deny` workflow checks advisories and sources using [`deny.toml`](../deny.toml).
Rust checks include dependencies for all platforms in the lockfile. The test
fixtures' npm lockfile also provides exact JavaScript versions for OSV-Scanner
and Trivy. Benchmark tooling currently has floating `latest` dependencies and
no committed lockfile, so its resolved dependency versions depend on installation
time.

Trivy also scans gitignored files. Use a clean checkout when reproducing CI;
local benchmark archives can contain historical lockfiles that CI never sees.

## Reviewed exceptions

Reviewed on 2026-11-05 against the locked GTK3 dependency graph. These are
advisory-specific exceptions, not dependency upgrades or fixes to upstream code.
Other advisories, including new findings in these packages, still fail the checks.

| Advisory | Dependency | Reason |
| --- | --- | --- |
| [RUSTSEC-2024-0370](https://rustsec.org/advisories/RUSTSEC-2024-0370.html) | `proc-macro-error` 1.0.4 | Unmaintained build-time diagnostic helper required by `glib-macros` 0.18.5 and `gtk3-macros` 0.18.2. The advisory does not identify a runtime vulnerability. Replacing it with `proc-macro-error2` requires changes in those upstream macros; it is not a compatible Cargo version bump. |
| [RUSTSEC-2024-0429](https://rustsec.org/advisories/RUSTSEC-2024-0429.html) / `GHSA-wrw7-89jp-8q8g` | `glib` 0.18.5 | The affected `VariantStrIter` iterator is not called by Bruster or its resolved Linux dependencies. Fixed GLib versions (`>=0.20`) are incompatible with the GTK3/WebKitGTK bindings' `^0.18` requirement. |

For the GLib review, `cargo metadata --locked --format-version=1
--filter-platform x86_64-unknown-linux-gnu` resolved 143 packages including
Bruster. Searching their Rust sources for `array_iter_str` and `VariantStrIter`
found references only in GLib's definition/re-export, documentation and unit
tests. The iterator's sole public constructor is `Variant::array_iter_str()`;
no application or dependency calls it. Upstream has
[declined a 0.18 patch release](https://github.com/gtk-rs/gtk-rs-core/issues/2010).

The exceptions are recorded in [`deny.toml`](../deny.toml),
[`osv-scanner.toml`](../osv-scanner.toml), and
[`.trivyignore.yaml`](../.trivyignore.yaml). OSV's configuration applies only to
the root lockfile and also matches the GLib advisory's alias. Trivy's exception
matches only `Cargo.lock` and `pkg:cargo/glib@0.18.5`; its report includes the
suppressed finding and rationale. The npm fixture lockfile has no exceptions;
its Vue/Svelte findings were resolved by dependency updates.

Recheck these decisions when the GTK dependency graph changes or code starts
using `Variant::array_iter_str`/`VariantStrIter`. Remove the entries when the
Linux backend moves to maintained bindings, a compatible patched release becomes
available, or the affected dependencies disappear.

## Dependabot

[`dependabot.yml`](../.github/dependabot.yml) requests daily dependency updates
for Cargo, the npm test fixtures and benchmarks, GitHub Actions, and Docker.
Repository administrators also enable **Dependabot alerts** and **Dependabot
security updates** under **Settings → Advanced Security**. Alerts appear under
**Security → Dependabot**, and update proposals appear as pull requests.

Dependabot's hosted checks run when manifests or advisory data change. Its alerts
and pull requests are separate from the four workflow badges above.

## Socket

[`socket.yml`](../socket.yml) enables pull-request alerts, dependency-overview
comments, and commit project reports once the GitHub App has access.

A repository administrator must
[install Socket Security](https://github.com/apps/socket-security/installations/new)
and select `aliilyas/bruster`. Committing the configuration alone does not install
the App. After installation, check for **Socket Security: Project Report** on a
default-branch commit and **Socket Security: Pull Request Alerts** on a dependency
pull request. No Socket API key is needed for the GitHub App integration.
