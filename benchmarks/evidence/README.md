# Navigation/performance evidence

[`navigation-performance-2026-11-05.tar.gz`](navigation-performance-2026-11-05.tar.gz)
supports [`PERFORMANCE_FIXES.md`](../PERFORMANCE_FIXES.md). Verify it with:

```sh
sha256sum -c navigation-performance-2026-11-05.tar.gz.sha256
```

The archive contains an `implementation/` directory:

- `clean-2026-11-05/`: final paired measurements, competitor sessions, process
  memory/mappings, installed-runtime inventories, screenshots, native snapshots,
  validation, dependency locks, environment, scheduling and exact harness.
- `baseline-bruster` and `final/candidate-bruster-d4c56d9`: frozen executables;
  their revisions and SHA-256 values appear in the report and provenance.
- Original top-level measurements: historical `5873f49` implementation batch.
- `final/` measurements: excluded second batch, retained with its raw overlap
  evidence. This directory also holds the final binary and platform CI logs;
  those are distinguished from the excluded measurement rows.
- `clean/`, `clean-scheduled-*`, waiting scripts and logs: cancelled/superseded
  preparation, with no completed measurements.
- `clean-rejected-*`, `clean-restart-wait-*`, `clean-pre-node-guard-*` and
  `clean-2026-11-05/compare-*-overlap*`: rejected, interrupted or superseded
  November attempts, excluded from final claims as documented in the ledger.
- `MEASUREMENT_STATUS.md`: batch validity ledger.
- `EVIDENCE_MANIFEST.json`: byte size and SHA-256 for every other archived file.

Identical files are stored as tar hard links to reduce the download size; every
original path and its contents remain present and are checked against the manifest.

Fault-probe failures and failed CI attempts remain present, including failures
that later retries resolved. Runtime dependency trees and browser download
caches are excluded from the archive; exact package locks, download URLs and
checksums are retained. Installed footprint inventories still count those
dependencies.

The paired probes ran November 5; the final competitor comparison and runtime
inventories completed November 6. The archive name retains the batch's start
date. This is a local Linux comparison of the named frozen revisions. It complements
the linked cross-platform source CI and does not measure subsequent `main`
optimizations. Archive paths retain their original meanings; scripts containing
absolute local paths require adjustment when reproduced elsewhere.
