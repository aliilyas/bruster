#!/usr/bin/env python3
"""Independent Linux audit of the published benchmark, using only the stdlib.

Run under Xvfb with a release executable. Results include every sample, exact
request/reply timing, fresh-cache process starts, and process-tree RSS/PSS.
OS page caches are not flushed. The external Xvfb server is measured separately.
"""
import argparse
import hashlib
import json
import os
import platform
import queue
import random
import signal
import statistics
import struct
import subprocess
import tempfile
import threading
import time
import zlib
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit


TINY = (
    "<html><head><title>bench</title></head><body>"
    "<h1>bench</h1><p>page load target</p>"
    "<ul><li>one</li><li>two</li><li>three</li></ul>"
    "</body></html>"
).encode()
LARGE = ("<html><head><title>large</title></head><body>" + "".join(
    f'<div><a href="/item/{i}">link {i}</a><input aria-label="input {i}"></div>'
    for i in range(1000)
) + "</body></html>").encode()


def png_fixture():
    def chunk(kind, data):
        return (struct.pack(">I", len(data)) + kind + data
                + struct.pack(">I", zlib.crc32(kind + data)))

    rng = random.Random(0)
    pixels = b"".join(b"\0" + rng.randbytes(128 * 3) for _ in range(128))
    return (b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", struct.pack(">IIBBBBB", 128, 128, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(pixels)) + chunk(b"IEND", b""))


PNG = png_fixture()


class Fixtures(BaseHTTPRequestHandler):
    def do_GET(self):
        path = urlsplit(self.path).path
        content_type = "text/html; charset=utf-8"
        body = TINY
        if path == "/delayed":
            time.sleep(0.250)
        elif path == "/large":
            body = LARGE
        elif path == "/images":
            token = urlsplit(self.path).query
            body = ("<html><head><title>images</title></head><body>" + "".join(
                f'<img src="/image/{i}.png?{token}" width="128" height="128">'
                for i in range(12)
            ) + "</body></html>").encode()
        elif path.startswith("/image/"):
            # A controlled network-latency fixture, not a real-world average.
            time.sleep(0.050)
            content_type, body = "image/png", PNG
            with self.server.hits_lock:
                self.server.image_hits += 1
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        try:
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def log_message(self, *args):
        pass


def descendants(root):
    parents = {}
    for proc in Path("/proc").iterdir():
        if not proc.name.isdigit():
            continue
        try:
            parents[int(proc.name)] = int((proc / "stat").read_text().rsplit(")", 1)[1].split()[1])
        except (OSError, ValueError, IndexError):
            continue
    found = {root}
    while True:
        more = {pid for pid, parent in parents.items() if parent in found} - found
        if not more:
            return sorted(found)
        found.update(more)


def memory(pid):
    path = Path(f"/proc/{pid}")
    row = {"pid": pid, "rss_kib": None, "pss_kib": None}
    try:
        row["name"] = (path / "comm").read_text().strip()
        row["command"] = (path / "cmdline").read_bytes().replace(b"\0", b" ").decode(errors="replace").strip()
        for line in (path / "smaps_rollup").read_text().splitlines():
            if line.startswith("Rss:"):
                row["rss_kib"] = int(line.split()[1])
            elif line.startswith("Pss:"):
                row["pss_kib"] = int(line.split()[1])
        # Retain file-backed mappings for the deployment inventory, including
        # dlopened libraries which ldd alone cannot discover.
        row["mapped_files"] = sorted({fields[5] for line in (path / "maps").read_text().splitlines()
                                      if len(fields := line.split(None, 5)) == 6
                                      and fields[5].startswith("/") and not fields[5].endswith(" (deleted)")})
    except OSError as exc:
        row["error"] = str(exc)
    return row


def memory_tree(root):
    rows = [memory(pid) for pid in descendants(root)]
    complete = all(r["rss_kib"] is not None and r["pss_kib"] is not None for r in rows)
    parent = next(r for r in rows if r["pid"] == root)
    return {
        "processes": rows,
        "complete": complete,
        "process_count": len(rows),
        "parent_rss_mib": parent["rss_kib"] / 1024 if parent["rss_kib"] is not None else None,
        "tree_rss_mib": sum(r["rss_kib"] for r in rows) / 1024 if complete else None,
        "tree_pss_mib": sum(r["pss_kib"] for r in rows) / 1024 if complete else None,
    }


def display_memory():
    rows = []
    for path in Path("/proc").glob("[0-9]*/cmdline"):
        try:
            args = path.read_bytes().split(b"\0")
            if args and Path(os.fsdecode(args[0])).name == "Xvfb" and os.fsencode(os.environ.get("DISPLAY", "")) in args:
                rows.append(memory(int(path.parent.name)))
        except OSError:
            pass
    return rows


class Browser:
    def __init__(self, binary, args, timeout):
        self.timeout = timeout
        self.events = queue.Queue()
        self.stderr = []
        self.next_id = 0
        self.temp = tempfile.TemporaryDirectory(prefix="bruster-audit-")
        env = os.environ.copy()
        for key in ("XDG_CACHE_HOME", "XDG_CONFIG_HOME", "XDG_DATA_HOME", "XDG_STATE_HOME"):
            env[key] = str(Path(self.temp.name) / key.lower())
        # The timer includes Popen, loader work, and all initialization to ready.
        start = time.perf_counter_ns()
        self.proc = subprocess.Popen(
            [str(binary), "--hidden", *args], stdin=subprocess.PIPE,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env,
            start_new_session=True,
        )
        self.reader = threading.Thread(target=self._read, daemon=True)
        self.reader.start()
        self.err_reader = threading.Thread(target=self._read_errors, daemon=True)
        self.err_reader.start()
        try:
            stamp, _, _ = self.wait(lambda obj: obj.get("event") == "ready")
            self.startup_ms = (stamp - start) / 1e6
        except BaseException:
            self.close()
            raise

    def _read(self):
        for raw in self.proc.stdout:
            stamp = time.perf_counter_ns()
            try:
                self.events.put((stamp, json.loads(raw), len(raw)))
            except ValueError:
                self.events.put((stamp, {"invalid_json": raw.decode(errors="replace")}, len(raw)))
        self.events.put((time.perf_counter_ns(), None, 0))

    def _read_errors(self):
        for raw in self.proc.stderr:
            self.stderr.append(raw.decode(errors="replace").rstrip())

    def wait(self, predicate):
        deadline = time.monotonic() + self.timeout
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError("bruster reply timed out")
            try:
                stamp, obj, size = self.events.get(timeout=remaining)
            except queue.Empty:
                raise TimeoutError("bruster reply timed out") from None
            if obj is None:
                raise RuntimeError(f"bruster exited: {self.stderr[-20:]}")
            if "invalid_json" in obj:
                raise RuntimeError(str(obj))
            if predicate(obj):
                return stamp, obj, size

    def call(self, method, params=None):
        self.next_id += 1
        request_id = self.next_id
        raw = (json.dumps({"id": request_id, "method": method, "params": params or {}}, separators=(",", ":")) + "\n").encode()
        start = time.perf_counter_ns()
        self.proc.stdin.write(raw)
        self.proc.stdin.flush()
        stamp, reply, size = self.wait(lambda obj: obj.get("id") == request_id)
        if "error" in reply:
            raise RuntimeError(f"{method}: {reply['error']}")
        elapsed = (stamp - start) / 1e6
        assert elapsed >= 0, "negative duration"
        return elapsed, reply["result"], size

    def navigate(self, url):
        elapsed, result, _ = self.call("navigate", {"url": url, "until": "load"})
        assert result["url"] == url, result
        return elapsed

    def close(self):
        if self.proc.poll() is None:
            try:
                self.call("close")
                self.proc.wait(timeout=15)
            except (OSError, RuntimeError, TimeoutError, subprocess.TimeoutExpired):
                pass
        # Dedicated session: cleanup only this audit's browser and descendants.
        try:
            os.killpg(self.proc.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        self.proc.wait(timeout=15)
        self.reader.join(timeout=2)
        self.err_reader.join(timeout=2)
        for stream in (self.proc.stdin, self.proc.stdout, self.proc.stderr):
            stream.close()
        self.temp.cleanup()


def summary(values):
    values = sorted(v for v in values if v is not None)
    if not values:
        return None
    return {"n": len(values), "median": statistics.median(values),
            "min": values[0], "max": values[-1]}


def run(binary, server, rounds, iterations, timeout, output):
    base = f"http://127.0.0.1:{server.server_port}"
    records = []
    for round_ in range(rounds):
        # Alternate mode ordering to reduce systematic cache/order bias.
        modes = [False, True] if round_ % 2 == 0 else [True, False]
        for no_images in modes:
            browser = Browser(binary, ["--no-images"] if no_images else [], timeout)
            row = {"round": round_ + 1, "no_images": no_images,
                   "startup_ms": browser.startup_ms, "load_average_before": os.getloadavg()}
            try:
                row["first_navigation_ms"] = browser.navigate(f"{base}/tiny?first={round_}")
                if round_ == 0 and not no_images:
                    row["delayed_validation_ms"] = browser.navigate(f"{base}/delayed")
                    assert row["delayed_validation_ms"] >= 240, "load timing missed the server delay"
                row["page_load_ms"], row["snapshot_ms"] = [], []
                for i in range(iterations):
                    row["page_load_ms"].append(browser.navigate(f"{base}/tiny?round={round_}&i={i}"))
                    elapsed, snap, _ = browser.call("snapshot")
                    assert snap["title"] == "bench" and snap["elements"] and not snap.get("truncated", False)
                    row["snapshot_ms"].append(elapsed)
                _, state, _ = browser.call("eval", {"expression": "document.readyState"})
                assert state == "complete", state
                time.sleep(2)
                row["idle_memory"] = []
                for _ in range(3):
                    row["idle_memory"].append(memory_tree(browser.proc.pid))
                    time.sleep(0.1)
                row["xvfb_memory"] = display_memory()
                row["snapshot_sizes"] = {}
                for page in ("tiny", "large"):
                    nav = browser.navigate(f"{base}/{page}")
                    json_ms, obj, json_wire = browser.call("snapshot", {"max": 2500})
                    text_ms, text, text_wire = browser.call("snapshot", {"max": 2500, "format": "text"})
                    assert not obj.get("truncated", False)
                    if page == "large":
                        assert len(obj["elements"]) == 2000, len(obj["elements"])
                    obj_bytes = len(json.dumps(obj, ensure_ascii=False, separators=(",", ":")).encode())
                    row["snapshot_sizes"][page] = {
                        "elements": len(obj["elements"]), "navigation_ms": nav,
                        "json_ms": json_ms, "text_ms": text_ms,
                        "json_payload_bytes": obj_bytes, "text_payload_bytes": len(text.encode()),
                        "json_wire_bytes": json_wire, "text_wire_bytes": text_wire,
                    }
                row["image_load_ms"] = []
                before = server.image_hits
                for i in range(5):
                    row["image_load_ms"].append(browser.navigate(f"{base}/images?round={round_}&i={i}"))
                row["image_requests"] = server.image_hits - before
                expected = 0 if no_images else 60
                assert row["image_requests"] == expected, row["image_requests"]
                _, dimensions, _ = browser.call("eval", {"expression": "Array.from(document.images, i => i.naturalWidth)"})
                assert dimensions == ([0] if no_images else [128]) * 12, dimensions
                row["load_average_after"] = os.getloadavg()
            finally:
                browser.close()
                row["stderr"] = browser.stderr
            records.append(row)
            output.write_text(json.dumps(records, indent=2) + "\n")
            print(f"round={round_ + 1} no_images={no_images} ready={row['startup_ms']:.1f}ms "
                  f"load={statistics.median(row['page_load_ms']):.2f}ms "
                  f"snapshot={statistics.median(row['snapshot_ms']):.2f}ms", flush=True)
    return records


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--binary", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--rounds", type=int, default=10)
    ap.add_argument("--iterations", type=int, default=10)
    ap.add_argument("--timeout", type=float, default=120)
    args = ap.parse_args()
    if args.rounds < 1 or args.iterations < 1:
        ap.error("rounds and iterations must be positive")
    binary = args.binary.resolve(strict=True)
    args.output.mkdir(parents=True, exist_ok=True)
    metadata = {
        "started_utc": datetime.now(timezone.utc).isoformat(),
        "platform": platform.platform(), "os": platform.freedesktop_os_release(),
        "python": platform.python_version(), "display": os.environ.get("DISPLAY"),
        "binary": str(binary), "binary_bytes": binary.stat().st_size,
        "binary_sha256": hashlib.sha256(binary.read_bytes()).hexdigest(),
        "rounds_per_mode": args.rounds, "iterations_per_round": args.iterations,
        "tiny_html_bytes": len(TINY), "large_html_bytes": len(LARGE),
        "image_bytes_each": len(PNG), "image_count": 12, "image_delay_ms": 50,
        "memory_units": "MiB; RSS sum double-counts shared pages; PSS apportions them",
        "startup": "new process and isolated XDG directories; OS page caches not flushed",
    }
    server = ThreadingHTTPServer(("127.0.0.1", 0), Fixtures)
    server.image_hits, server.hits_lock = 0, threading.Lock()
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        rows = run(binary, server, args.rounds, args.iterations, args.timeout,
                   args.output / "samples.json")
    finally:
        server.shutdown()
        server.server_close()
    metrics = {}
    for mode in (False, True):
        subset = [r for r in rows if r["no_images"] == mode]
        stats = {key: summary([r[key] for r in subset])
                 for key in ("startup_ms", "first_navigation_ms")}
        for key in ("page_load_ms", "snapshot_ms", "image_load_ms"):
            stats[key] = summary([v for r in subset for v in r[key]])
        for key in ("parent_rss_mib", "tree_rss_mib", "tree_pss_mib", "process_count"):
            stats[key] = summary([statistics.median(m[key] for m in r["idle_memory"])
                                  for r in subset if all(m[key] is not None for m in r["idle_memory"])])
        metrics["no_images" if mode else "default"] = stats
    metadata["finished_utc"] = datetime.now(timezone.utc).isoformat()
    report = {"metadata": metadata, "summary": metrics}
    (args.output / "summary.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
