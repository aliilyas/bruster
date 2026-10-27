# Published benchmark review — 2026-10-27

Bruster's measured strengths are warm small-page operations and idle memory.
Its main published weakness is a repeatable **~30-second startup stall** on the
GitHub runners. Large extraction results depend strongly on the return format;
the object-return advantage does not carry over to JSON-string extraction.

## Evidence and latest results

Reviewed runs [1](https://github.com/aliilyas/bruster/actions/runs/40594030043),
[2](https://github.com/aliilyas/bruster/actions/runs/40594138104),
[3](https://github.com/aliilyas/bruster/actions/runs/40594943590), and
[4](https://github.com/aliilyas/bruster/actions/runs/40595366190): **200 sessions**,
40 per configuration. All passed the measurement validator, with matching
cross-tool extraction hashes, complete recorded memory samples, no recorded
competing work, and no forced process cleanup.

The table uses run 4, a same-commit repeat of run 3 at `1d60e7188f0a`.
[Immutable run report](https://aliilyas.github.io/bruster/benchmarks/runs/1d60e7188f0ab0e21219a8e75c76fccfefdc9052-40595366190-1/)
and [raw samples](https://aliilyas.github.io/bruster/benchmarks/runs/1d60e7188f0ab0e21219a8e75c76fccfefdc9052-40595366190-1/samples.json).
Values are medians of ten sessions or their repeated operations.

| Configuration | Launch → first page (s) | Warm tiny navigation (ms) | Large JSON-string extraction (ms) | Idle total PSS (MiB) | Runtime files, lower bound (MB) |
|---|---:|---:|---:|---:|---:|
| Bruster / WebKitGTK / Xvfb | 30.708 | 7.27 | 15.18 | 250.8 | 427.9 |
| Playwright / Headless Shell | 0.451 | 8.65 | 8.41 | 324.7 | 475.5 |
| Playwright / full Chrome | 0.629 | 14.40 | 12.72 | 507.6 | 630.8 |
| Puppeteer / full Chrome | 0.473 | 16.00 | 17.45 | 418.8 | 644.7 |
| agent-browser / full Chrome | 0.714 | 31.44 | 10.65 | 516.8 | 483.2 |

Versions: WebKitGTK 2.52.6, Playwright 1.64.1, Puppeteer 25.16.0,
agent-browser 0.40.0, Chrome/Headless Shell 156.0.8078.4, Node 26.12.1.
Runner: Ubuntu 24.04.5, AMD EPYC 9V74, four visible CPUs, 15.6 GiB RAM,
image `20261026.354.1`.

## Findings

1. **Startup is the priority.** In run 4, Bruster took 30,144.8 ms to report
   ready, followed by 564.1 ms for its first navigation. Startup alone ranged
   from 26,105.1 to 30,310.6 ms. All four published runs show the same pattern.
   Faster warm operations do not compensate for this cost in short sessions.

2. **Memory savings are real within this workload.** Bruster used approximately
   23% less total PSS than Playwright's normal Headless Shell configuration and
   40–51% less than the full-Chrome configurations. This includes WebKit helpers
   and Xvfb. It is small-page idle usage, not peak memory or a guarantee for
   complex sites. The runtime inventory is **427.9 MB**, not the ~1.46 MB Rust
   executable alone; even that inventory is an installed-file lower bound.

3. **Do not generalize from object-return extraction.** Bruster's large-object
   extraction was 15.07 ms versus Playwright Shell's 80.09 ms. Returning the same
   data as a JSON string reverses their ordering: 15.18 versus 8.41 ms. The
   Playwright result includes substantial object transport/serialization cost.
   Both formats use identical extraction code and matching results; neither
   supports a blanket claim that one engine executes JavaScript faster.

4. **The Playwright fault is specific and reproducible.** Both Playwright
   configurations failed immediate recovery after a refused connection in all
   40 reviewed sessions each. The follow-up navigation was interrupted by
   `chrome-error://chromewebdata/`; all separately recorded 100 ms retries
   succeeded. This occurs after the timed workloads. Bruster, Puppeteer and
   agent-browser passed these probes. It is evidence of an immediate-recovery
   race, not a general browser reliability ranking.

5. **Cross-run shifts are not necessarily code improvements.** Runs 2–4 have
   identical Bruster executable SHA-256
   `48adb34cc3956a14fb05c4b614387dbc8fd90b623b22c3bc0f299a6ae234dc3b`.
   Runs 3 and 4 even have the same source commit and CPU model, but different
   runner images and kernels. Bruster PSS changed from 286.4 to 250.8 MiB,
   and Playwright Shell's JSON-string extraction from 13.75 to 8.41 ms.
   These are not Bruster source changes. Compare configurations within a run;
   inspect hardware, image, runtime versions, ranges and hashes before comparing
   runs. The small localhost fixtures do not establish real-site throughput.

## Startup investigation and fixes

A controlled private D-Bus portal that accepts calls but withholds replies
reproduces the stall. `strace` identifies GTK's synchronous Inhibit-proxy setup
waiting approximately **25 seconds**, followed by Tao's synchronous portal
theme query waiting **5 seconds**. The theme query also runs for new tabs.
An unavailable accessibility service warning alone does not explain this delay.
The controlled failure matches the CI timing pattern; the original CI runs did
not retain D-Bus traces, so their exact portal failure remains unconfirmed.

The fix makes Linux hidden/MCP sessions skip desktop-session integration before
GTK starts. An explicit unavailable D-Bus transport prevents both waiting on the
desktop portal and silently autolaunching a replacement session bus. Visible
mode uses the desktop bus; `BRUSTER_USE_SESSION_BUS=1` opts hidden sessions into
it. A private-bus regression exercises responsive positive controls, a stalled
portal, hidden startup, MCP startup, and new-tab creation.

Three untraced local reproductions per binary measured median spawn-to-ready
times of **30,393.6 ms before the fix** and **300.0 ms after it**, with no forced
cleanup. The frozen pre-fix binary and the fixed build used the same machine,
runtime and withheld-reply fixture. These are diagnostic startup measurements,
not new GitHub comparison results.

The report now shows startup and first navigation separately, observed min–max
ranges, WebKit/Headless Shell versions, and runner hardware/image details.
Shutdown/cleanup failures have their own counts instead of being mislabeled as
fault-probe failures. GTK and desktop-session environment settings are retained
for future diagnosis. Xvfb is prestarted: its startup time is excluded, although
its memory is included.

The published table above predates these fixes. Post-fix GitHub-runner timings
must come from a new benchmark run; local regression timings are not a
replacement for those measurements.

Local verification passed: five Rust unit tests, 30 smoke tests, 19 edge tests,
the private-portal/MCP regression, nine publication/lifecycle tests, workflow
lint, validation of all 200 published sessions, and ten fresh comparison sessions
covering all five configurations with current npm tool versions (local Node
24.22.1 on Ubuntu 26.04). The updated report was also
rendered with the real published data. The changed Rust source passes formatting;
the repository-wide format check reports existing formatting in `tests/e2e.rs`.

To run the portal regression on Linux with `python3-dbus`, `python3-gi` and D-Bus
installed:

```sh
cargo build --release --locked
xvfb-run -a /usr/bin/python3 tests/startup_portal.py target/release/bruster
```

All fixes and local diagnostic evidence are in the dedicated
`fix/benchmark-review` worktree. Continuous comparisons still resolve npm
`@latest` releases and publish every merge's versioned results automatically.
