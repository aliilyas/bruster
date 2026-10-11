#!/usr/bin/env python3
"""Measure bruster so the project site can publish real speed numbers.

Reads nothing from the network: cold start, page-load latency to a local
file, a snapshot round-trip, idle memory (RSS), and binary size.

Usage (run under a display when headless):
    xvfb-run -a python3 scripts/bench.py --binary target/release/bruster \
        --output metrics.json --commit "$GITHUB_SHA"

A fresh WebKitGTK cold start can take over a minute on an overloaded CI
runner, so the first `ready` wait is generous. Increase it with --timeout.

Stdlib only.
"""
import argparse
import json
import os
import subprocess
import sys
import threading
import time
from datetime import datetime, timezone

EVT_READY = '"event":"ready"'
EVT_LOAD = '"event":"load"'


def drain(stream, sink):
    for line in stream:
        sink.append((time.perf_counter(), line.rstrip("\n")))
    sink.append((time.perf_counter(), None))  # EOF sentinel


class Lines:
    def __init__(self):
        self.rows = []
        self._lock = threading.Lock()

    def append(self, row):
        with self._lock:
            self.rows.append(row)

    def since(self, idx):
        with self._lock:
            return list(self.rows[idx:]), len(self.rows)

    def tail(self, count):
        with self._lock:
            return [line for _, line in self.rows[-count:]]

    def all_text(self):
        with self._lock:
            return [line for _, line in self.rows if line is not None]

    def wait(self, needle, timeout, from_idx=0):
        """Return (timestamp, line) for the first line containing needle."""
        start = time.monotonic()
        idx = from_idx
        while time.monotonic() - start < timeout:
            rows, idx = self.since(idx)
            for ts, line in rows:
                if line is None:
                    raise RuntimeError("bruster exited before producing a match")
                if needle in line:
                    return ts, line
            time.sleep(0.01)
        raise RuntimeError(f"no output matched {needle!r} within {timeout}s")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--binary", default="target/release/bruster")
    ap.add_argument("--output", default="metrics.json")
    ap.add_argument("--commit", default="")
    ap.add_argument("--timeout", type=int, default=120, help="seconds to wait for cold start")
    args = ap.parse_args()

    binary = os.path.abspath(args.binary)
    if not os.path.exists(binary):
        sys.exit(f"{binary}: not found")

    # No --quiet: keep stderr so a failed run is diagnosable. The benchmark
    # ignores stderr unless something goes wrong.
    proc = subprocess.Popen(
        [binary, "--hidden"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
        cwd=os.path.dirname(binary) or ".",
    )
    lines = Lines()
    errs = Lines()
    threading.Thread(target=drain, args=(proc.stdout, lines), daemon=True).start()
    threading.Thread(target=drain, args=(proc.stderr, errs), daemon=True).start()

    def send(obj):
        proc.stdin.write(json.dumps(obj) + "\n")
        proc.stdin.flush()

    def wait_reply(obj_id, timeout=60):
        needle = f'"id":{obj_id}'
        return lines.wait(needle, timeout)

    t0 = time.perf_counter()
    try:
        # 1. Cold start: spawn -> {"event":"ready"}
        ts, _ = lines.wait(EVT_READY, args.timeout)
        cold_start_ms = (ts - t0) * 1000

        # 2. Warm the web process on about:blank.
        send({"id": 1, "method": "navigate", "params": {"url": "about:blank"}})
        wait_reply(1)
        lines.wait(EVT_LOAD, 60)

        # 3. Page load latency to a local file.
        with __import__("tempfile").NamedTemporaryFile("w", suffix=".html", delete=False) as f:
            f.write("<html><body><h1>bench</h1><p>page load target</p></body></html>")
            page = f.name
        send({"id": 2, "method": "navigate", "params": {"url": f"file://{page}"}})
        t_sent = time.perf_counter()
        ts, _ = lines.wait(EVT_LOAD, 60)
        page_load_ms = (ts - t_sent) * 1000
        wait_reply(2)

        # 4. Snapshot round-trip.
        send({"id": 3, "method": "snapshot"})
        t_sent = time.perf_counter()
        ts, _ = wait_reply(3)
        snapshot_ms = (ts - t_sent) * 1000

        # 5. Idle memory once the web process settles.
        time.sleep(2.0)
        idle_rss_kb = 0
        try:
            with open(f"/proc/{proc.pid}/status") as st:
                for ln in st:
                    if ln.startswith("VmRSS"):
                        idle_rss_kb = int(ln.split()[1])
                        break
        except (FileNotFoundError, ValueError):
            idle_rss_kb = 0

        # 6. Close cleanly.
        send({"id": 99, "method": "close"})
        try:
            proc.wait(timeout=15)
        except subprocess.TimeoutExpired:
            proc.kill()
    except Exception as e:
        # Surface everything the process said so the next fix is obvious.
        print(f"bench failed: {e}", file=sys.stderr)
        print("stdout seen:\n" + "\n".join(lines.all_text()[-20:]), file=sys.stderr)
        print("stderr seen (last 20):\n" + "\n".join(errs.tail(20)), file=sys.stderr)
        proc.kill()
        raise
    finally:
        if proc.poll() is None:
            proc.kill()

    metrics = {
        "updated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "commit": args.commit,
        "environment": "GitHub Actions · ubuntu-24.04 x86_64",
        "binary_kb": round(os.path.getsize(binary) / 1024, 1),
        "cold_start_ms": round(cold_start_ms),
        "page_load_ms": round(page_load_ms),
        "snapshot_ms": round(snapshot_ms),
        "idle_rss_mb": round(idle_rss_kb / 1024, 1),
    }
    with open(args.output, "w") as out:
        json.dump(metrics, out, indent=2)
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()