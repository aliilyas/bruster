# TODO

- [x] Resolve Cargo deny CI failure (`.github/workflows/deny.yml`).
  Added a documented exception for the unmaintained GTK3 build dependency
  `proc-macro-error` (`RUSTSEC-2024-0370`).
  `cargo deny --locked check advisories sources` passes.
  [Failing run](https://github.com/aliilyas/bruster/actions/runs/42101199433).
- [x] Resolve OSV-Scanner CI failures (`.github/workflows/osv.yml`).
  Verified the merged Vue/Svelte upgrades clear the npm findings. Added
  root-lockfile exceptions for the unused GLib iterator (`RUSTSEC-2024-0429`)
  and the GTK3 build dependency (`RUSTSEC-2024-0370`). The recursive scan passes.
  [Failing run](https://github.com/aliilyas/bruster/actions/runs/42101199489).
- [x] Resolve Trivy CI failures (`.github/workflows/trivy.yml`).
  Added a GLib advisory exception scoped to `Cargo.lock` and `glib` 0.18.5,
  with the suppressed finding visible in the report. The scan passes with
  development dependencies included; the updated npm fixture lockfile is clean.
  [Failing run](https://github.com/aliilyas/bruster/actions/runs/42101199408).

Validated locally on 2026-11-05 with cargo-deny 0.20.2, OSV-Scanner 2.7.0 and
Trivy 0.76.2. OSV/Trivy ran against a clean snapshot of the working tree, matching
CI's files. Both still fail on an isolated vulnerable Vue fixture. Workflow lint
also passes. GitHub verification requires committing and pushing these changes.
See [the advisory review](docs/dependency-security.md#reviewed-exceptions) for
exception evidence and removal conditions.
