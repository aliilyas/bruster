#!/usr/bin/env python3
"""Paired Bruster optimization workloads, through both JSONL and MCP.

Client-visible timings include request encoding and response decoding. Fresh
sessions, alternating AB/BA order, warm OS caches, prestarted display. Diagnostic
runs retain contamination evidence and cannot support published speedup claims.
"""
import argparse
import base64
import ctypes
import hashlib
import json
import math
import os
import platform
import random
import shutil
import statistics
import subprocess
import sys
import tempfile
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

import bench_audit as audit
import bench_compare as compare
from lab.client import Client
from lab.runner import png_pixels


class QuietClient(Client):
    def _record(self, direction, value):
        # Evidence hashing belongs outside the timed protocol path.
        pass


class Fixtures(audit.Fixtures):
    def do_GET(self):
        path = urlsplit(self.path).path
        if path == '/text-heavy':
            body = ('<html><title>text-heavy</title><body><ul>' + ''.join(
                f'<li><span>row {i} </span><a href="/item/{i}">open {i}</a></li>'
                for i in range(1000)) + '</ul></body></html>').encode()
        elif path == '/large-body':
            body = b'0123456789abcdef' * (1024 * 1024)
        else:
            return super().do_GET()
        self.send_response(200)
        self.send_header('Content-Type', 'text/plain' if path == '/large-body' else 'text/html')
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        try:
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            pass


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=True).encode()).hexdigest()


def timed(fn):
    start = time.perf_counter_ns()
    value = fn()
    return (time.perf_counter_ns() - start) / 1e6, value


def equal(actual, expected):
    assert actual == expected, (actual, expected)


def measure(args, base, binary, transport, round_, label):
    linux = sys.platform.startswith('linux')
    before = compare.process_table() if linux else {}
    row = {'round': round_, 'build': label, 'transport': transport,
           'timings': {}, 'correctness': {}, 'started_utc': datetime.now(timezone.utc).isoformat(),
           'competing_before': compare.background_work() if linux else []}
    client = None
    try:
        if row['competing_before'] and not args.diagnostic:
            raise RuntimeError(f"Concurrent workload: {row['competing_before']}")
        with tempfile.TemporaryDirectory(prefix='bruster-paired-') as directory:
            launch = time.perf_counter_ns()
            client = QuietClient(binary, transport, Path(directory), viewport=(1280, 800))
            row['timings']['startup_ms'] = [(time.perf_counter_ns() - launch) / 1e6]
            ms, result = timed(lambda: client.call('navigate', {'url': base + '/tiny', 'until': 'load'}))
            assert result['url'] == base + '/tiny'
            row['timings']['first_navigation_ms'] = [ms]
            row['timings']['launch_to_first_page_ms'] = [(time.perf_counter_ns() - launch) / 1e6]
            assert client.call('eval', {'expression': '[innerWidth,innerHeight,document.readyState]'}) == [1280, 800, 'complete']
            dpr = client.call('eval', {'expression': 'devicePixelRatio'})
            row['device_pixel_ratio'] = dpr

            def repeat(name, fn, validate=lambda value: None, count=None):
                observations, hashes = [], set()
                for i in range((count or args.iterations) + 2):
                    ms, value = timed(fn)
                    validate(value)
                    hashes.add(digest(value))
                    if i >= 2:
                        observations.append(ms)
                assert len(hashes) == 1, (name, 'inconsistent result')
                row['correctness'][name] = hashes.pop()
                row['timings'][name] = observations

            for page, count in [('tiny', 5), ('large', 2000), ('text-heavy', 2000)]:
                client.call('navigate', {'url': base + '/' + page})
                def validate(snap):
                    assert len(snap['elements']) == count and not snap.get('truncated'), (page, snap)
                repeat(page + '_snapshot_json_ms', lambda: client.call('snapshot', {'max': 2500}), validate)
                repeat(page + '_snapshot_text_ms', lambda: client.call('snapshot', {'max': 2500, 'format': 'text'}),
                       lambda text: equal(text.startswith(base + '/' + page + '\n'), True))

            client.call('navigate', {'url': base + '/large'})
            client.call('eval', {'expression': "document.querySelector('input[aria-label=\"input 999\"]').id='last'"})
            repeat('selector_lookup_ms', lambda: client.call('attr', {'selector': '#last', 'name': 'aria-label'}),
                   lambda value: equal(value, 'input 999'))
            payload = client.call('eval', {'expression': 'window.cached = Array.from({length:2000}, (_,i) => ({index:i,text:"row "+i,values:[true,null,i]}))'})
            assert len(payload) == 2000
            repeat('cached_object_ms', lambda: client.call('eval', {'expression': 'cached'}),
                   lambda value: equal(value, payload))

            client.call('navigate', {'url': base + '/images'})
            assert client.call('eval', {'expression': 'Array.from(document.images,i=>i.naturalWidth)'}) == [128] * 12
            image_path = args.output / f'{transport}-{round_}-{label}.png'
            for mode in ('file', 'inline'):
                samples = []
                for i in range(5):
                    ms, image = timed(lambda: client.call('screenshot', {'path': str(image_path)} if mode == 'file' else {}))
                    data = image_path.read_bytes() if mode == 'file' else base64.b64decode(image['png_base64'], validate=True)
                    if i >= 2:
                        samples.append(ms)
                    if i == 0:
                        width, height, pixel = png_pixels(data)
                        assert (width, height) == (1280 * dpr, 800 * dpr)
                        # Full RGB equality on this opaque fixture, not PNG byte
                        # equality: compression and RGB/RGBA encoding may differ.
                        pixels = bytes(channel for y in range(height) for x in range(width) for channel in pixel(x, y))
                        row['correctness']['screenshot_' + mode] = hashlib.sha256(pixels).hexdigest()
                        row['screenshot_' + mode + '_bytes'] = len(data)
                row['timings']['screenshot_' + mode + '_ms'] = samples

            client.call('navigate', {'url': base + '/tiny'})
            row['timings']['dom_wait_ms'], row['timings']['action_wait_ms'] = [], []
            for i in range(args.iterations + 2):
                client.call('eval', {'expression': "document.body.innerHTML=''; setTimeout(() => { document.body.innerHTML='<input id=late disabled>'; }, 12)"})
                ms, _ = timed(lambda: client.call('wait_for', {'selector': '#late'}))
                assert client.call('count', {'selector': '#late'}) == 1
                client.call('eval', {'expression': "setTimeout(() => { document.querySelector('#late').disabled=false; }, 12)"})
                action_ms, _ = timed(lambda: client.call('fill', {'selector': '#late', 'value': 'done'}))
                assert client.call('eval', {'expression': "document.querySelector('#late').value"}) == 'done'
                if i >= 2:
                    row['timings']['dom_wait_ms'].append(ms)
                    row['timings']['action_wait_ms'].append(action_ms)

            def fetch_body():
                client.call('network', {'clear': True})
                size = client.call('eval', {'expression': "fetch('/large-body').then(r=>r.arrayBuffer()).then(b=>b.byteLength)"})
                assert size == 16 * 1024 * 1024
                deadline = time.monotonic() + 30
                while True:
                    entry = client.call('network_request', {'index': 0})
                    if 'body' in entry:
                        assert entry['body'] == '0123456789abcdef' * 1024
                        return size
                    if time.monotonic() > deadline:
                        raise TimeoutError('network prefix unavailable')
            repeat('fetch_with_capture_ms', fetch_body, count=3)
            if linux:
                time.sleep(1)
                memory = compare.memory_forest(before, True)
                assert memory['complete'], memory
                row['memory'] = memory
                row['timings']['idle_total_pss_mib'] = [memory['total_pss_mib']]
            row['competing_after'] = compare.background_work(before=before) if linux else []
            if row['competing_after'] and not args.diagnostic:
                raise RuntimeError(f"Concurrent workload: {row['competing_after']}")
            owned = compare.owned_processes(before) if linux else {}
            row['close_error'] = client.close()
            row['stderr'] = client.errors
            assert row['close_error'] is None, row['close_error']
            row['duplicates'] = client.duplicates
            assert not row['duplicates'], row['duplicates']
            client = None
            row['forced_cleanup'] = compare.cleanup(owned) if linux else []
            assert not row['forced_cleanup'], row['forced_cleanup']
    except Exception as exc:
        row['error'] = repr(exc)
    finally:
        if client is not None:
            row['close_error'] = client.close()
            row['stderr'] = client.errors
        if linux:
            forced = compare.cleanup(compare.owned_processes(before))
            if forced:
                row['forced_cleanup'] = forced
                row.setdefault('error', 'forced process cleanup')
    return row


def percentile(values, fraction):
    values = sorted(values)
    return values[min(len(values) - 1, math.ceil(len(values) * fraction) - 1)]


def summarize(rows):
    result = {}
    for transport in sorted({row['transport'] for row in rows}):
        selected = [row for row in rows if row['transport'] == transport]
        a = {r['round']: r for r in selected if r['build'] == 'baseline'}
        b = {r['round']: r for r in selected if r['build'] == 'candidate'}
        assert a.keys() == b.keys()
        for n in a:
            assert a[n]['correctness'] == b[n]['correctness'], (transport, n, 'different results/pixels')
        for key in a[next(iter(a))]['timings']:
            left = [statistics.median(a[n]['timings'][key]) for n in a]
            right = [statistics.median(b[n]['timings'][key]) for n in a]
            logs = [math.log(y / x) for x, y in zip(left, right)]
            rng = random.Random(20261104)
            boot = [statistics.mean(rng.choices(logs, k=len(logs))) for _ in range(5000)]
            change = lambda x: (math.exp(x) - 1) * 100
            result[transport + '/' + key] = {
                'baseline_median': statistics.median(left), 'candidate_median': statistics.median(right),
                'baseline_p95': statistics.median(percentile(a[n]['timings'][key], .95) for n in a),
                'candidate_p95': statistics.median(percentile(b[n]['timings'][key], .95) for n in a),
                'paired_change_percent': change(statistics.mean(logs)),
                'interval95_percent': [change(percentile(boot, .025)), change(percentile(boot, .975))],
            }
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('baseline', 'candidate', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--rounds', type=int, default=20)
    parser.add_argument('--iterations', type=int, default=12)
    parser.add_argument('--transport', choices=('native', 'mcp', 'both'), default='both')
    parser.add_argument('--diagnostic', action='store_true')
    args = parser.parse_args()
    if min(args.rounds, args.iterations) < 1:
        parser.error('rounds and iterations must be positive')
    if os.environ.get('BRUSTER_TRACE_PERF') == '1' and not args.diagnostic:
        parser.error('disable BRUSTER_TRACE_PERF for performance measurements')
    args.baseline, args.candidate, args.output = args.baseline.resolve(), args.candidate.resolve(), args.output.resolve()
    args.output.mkdir(parents=True, exist_ok=True)
    if sys.platform.startswith('linux') and ctypes.CDLL(None, use_errno=True).prctl(36, 1, 0, 0, 0) != 0:
        raise OSError(ctypes.get_errno(), 'PR_SET_CHILD_SUBREAPER failed')
    harness = args.output / 'harness'
    harness.mkdir(exist_ok=True)
    for name in ('bench_optimizations.py', 'bench_compare.py', 'bench_audit.py', 'bench_tools.py'):
        shutil.copy2(Path(__file__).with_name(name), harness / name)
    shutil.copytree(Path(__file__).with_name('lab'), harness / 'lab', dirs_exist_ok=True, ignore=shutil.ignore_patterns('__pycache__'))
    (args.output / 'benchmarks').mkdir(exist_ok=True)
    shutil.copy2(compare.CATALOG_PATH, args.output / 'benchmarks' / compare.CATALOG_PATH.name)
    report = {'metadata': {'platform': platform.platform(), 'python': sys.version, 'diagnostic': args.diagnostic,
        'args': {k: str(v) for k, v in vars(args).items()},
        'binary_sha256': {name: hashlib.sha256(getattr(args, name).read_bytes()).hexdigest() for name in ('baseline', 'candidate')},
        'harness_sha256': {str(p.relative_to(harness)): hashlib.sha256(p.read_bytes()).hexdigest() for p in harness.rglob('*.py')},
        'environment': {k:v for k,v in os.environ.items() if k.startswith(('BRUSTER_', 'WEBKIT_', 'GITHUB_', 'Image')) or k == 'DISPLAY'},
        'cpu': Path('/proc/cpuinfo').read_text() if sys.platform.startswith('linux') else subprocess.check_output(['sysctl','-n','machdep.cpu.brand_string'], text=True).strip(),
    }, 'samples': []}
    server = audit.ThreadingHTTPServer(('127.0.0.1', 0), Fixtures)
    server.image_hits, server.hits_lock = 0, threading.Lock()
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        for n in range(1, args.rounds + 1):
            for transport in (('native', 'mcp') if args.transport == 'both' else (args.transport,)):
                for label in (('baseline', 'candidate') if n % 2 else ('candidate', 'baseline')):
                    row = measure(args, f'http://127.0.0.1:{server.server_port}', getattr(args, label), transport, n, label)
                    report['samples'].append(row)
                    (args.output / 'results.json').write_text(json.dumps(report, indent=2) + '\n')
                    print(transport, n, label, row.get('error', 'ok'), flush=True)
                    if 'error' in row:
                        raise RuntimeError(row['error'])
        report['summary'] = summarize(report['samples'])
        report['metadata']['publishable'] = not args.diagnostic and args.rounds >= 20
        (args.output / 'results.json').write_text(json.dumps(report, indent=2) + '\n')
        lines = ['# Paired optimization comparison', '',
                 f'{args.rounds} alternating pairs per transport. Publishable: {report["metadata"]["publishable"]}.',
                 'All result and opaque screenshot RGB hashes matched. Negative changes are better.',
                 'Session medians; paired geometric changes and pointwise 95% bootstrap intervals.',
                 'p95 columns are medians of within-session p95s, diagnostic with these sample counts.', '',
                 '| Metric | Baseline | Candidate | Paired change | 95% interval | Baseline p95 | Candidate p95 |',
                 '|---|---:|---:|---:|---:|---:|---:|']
        for key, value in report['summary'].items():
            lo, hi = value['interval95_percent']
            lines.append(f'| {key} | {value["baseline_median"]:.3f} | {value["candidate_median"]:.3f} | {value["paired_change_percent"]:+.2f}% | {lo:+.2f}% to {hi:+.2f}% | {value["baseline_p95"]:.3f} | {value["candidate_p95"]:.3f} |')
        (args.output / 'report.md').write_text('\n'.join(lines) + '\n')
    finally:
        server.shutdown()
        server.server_close()


if __name__ == '__main__':
    main()
