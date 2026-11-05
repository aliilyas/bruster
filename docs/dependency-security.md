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

Findings retain the scanner's nonzero exit status. No vulnerability IDs are
suppressed. cargo-audit reports informational advisories as warnings, while
cargo-deny can fail on unmaintained dependencies. Inspect the linked logs as well
as the badge. A passing check describes the scanner's coverage and policy at that
run, rather than certifying code safety.

## Run locally

Install [cargo-audit and cargo-deny](https://rustsec.org/),
[OSV-Scanner](https://github.com/google/osv-scanner), and
[Trivy](https://trivy.dev/), then run from the repository root:

```sh
cargo audit --file Cargo.lock
cargo deny --locked check advisories sources
osv-scanner scan source --recursive .
trivy fs --scanners vuln --include-dev-deps --no-progress --exit-code 1 .
```

The `cargo-deny` workflow checks advisories and sources using [`deny.toml`](../deny.toml).
Rust checks include dependencies for all platforms in the lockfile. The test
fixtures' npm lockfile also provides exact JavaScript versions for OSV-Scanner
and Trivy. Benchmark tooling currently has floating `latest` dependencies and
no committed lockfile, so its resolved dependency versions depend on installation
time.

## GTK advisory remediation

The Linux dependency graph uses GTK 0.19 / GLib 0.22, removing GLib 0.18 and
`proc-macro-error`. Current Wry/Tao releases need temporary compatibility patches,
and the WebKit bindings are pinned to an upstream migration commit. See
[`vendor/README.md`](../vendor/README.md) for provenance, verification, and the
removal plan. No advisory suppressions are needed.

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
