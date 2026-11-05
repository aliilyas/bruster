# TODO

- [x] Resolve Cargo deny CI failure (`.github/workflows/deny.yml`).
  Upgraded the GTK macro bindings to remove the unmaintained build dependency
  `proc-macro-error` (`RUSTSEC-2024-0370`) and retired its temporary exception.
  `cargo deny --locked check advisories sources` passes.
  [Failing run](https://github.com/aliilyas/bruster/actions/runs/42101199433).
- [x] Resolve OSV-Scanner CI failures (`.github/workflows/osv.yml`).
  The merged Vue/Svelte upgrades clear the npm findings. GTK 0.19 / GLib 0.22
  fixes the GLib iterator (`RUSTSEC-2024-0429`) and removes the obsolete macro
  dependency (`RUSTSEC-2024-0370`). The recursive scan passes without exceptions.
  [Failing run](https://github.com/aliilyas/bruster/actions/runs/42101199489).
- [x] Resolve Trivy CI failures (`.github/workflows/trivy.yml`).
  Removed the GLib advisory exception after upgrading the binding stack.
  The scan passes with
  development dependencies included; the updated npm fixture lockfile is clean.
  [Failing run](https://github.com/aliilyas/bruster/actions/runs/42101199408).

The dependency upgrade passed [OSV](https://github.com/aliilyas/bruster/actions/runs/42111248736),
[cargo-deny](https://github.com/aliilyas/bruster/actions/runs/42111248816),
[cargo-audit](https://github.com/aliilyas/bruster/actions/runs/42111248747), and
[Trivy](https://github.com/aliilyas/bruster/actions/runs/42111248676) on GitHub
without advisory exceptions. See [the remediation notes](docs/dependency-security.md#gtk-advisory-remediation)
and [patch provenance](vendor/README.md).
