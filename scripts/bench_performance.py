#!/usr/bin/env python3
"""Paired Linux performance regression probe for frozen baseline/candidate builds.

Run without DISPLAY to include each build's automatic Xvfb launch and memory.
Uses the same local fixtures and complete process accounting as bench_compare.
OS caches are not flushed. Each sample uses a fresh HOME/XDG environment.
"""
import argparse
import ctypes
import hashlib
import json
import os
import platform
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

import bench_audit as audit
import bench_compare as compare


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def parent_status(before, binary):
    for pid in compare.owned_processes(before):
        try:
            if Path(f'/proc/{pid}/exe').resolve() == binary:
                status = dict(line.split(':', 1) for line in Path(f'/proc/{pid}/status').read_text().splitlines())
                return {key: int(status[key].split()[0]) for key in ('Threads', 'VmSize', 'VmRSS')}
        except OSError:
            pass
    raise RuntimeError('Bruster process not found')


def measure(args, server, label, round_):
    binary = getattr(args, label)
    before = compare.process_table()
    row = {'build': label, 'round': round_, 'started_utc': datetime.now(timezone.utc).isoformat(),
           'competing_before': compare.background_work()}
    client = None
    try:
        if row['competing_before']:
            raise RuntimeError(f"Concurrent browser/build workload: {row['competing_before']}")
        client = compare.ProcessClient([str(binary), '--hidden'], False)
        base = f'http://127.0.0.1:{server.server_port}'
        row['ready_ms'] = client.startup_ms
        row['navigate_ms'] = client.navigate(f'{base}/tiny?{label}-{round_}')
        row['launch_to_page_ms'] = (time.perf_counter_ns() - client.started_ns) / 1e6
        _, info, _ = client.call('eval', {'expression': '({state:document.readyState,title:document.title,width:innerWidth,height:innerHeight})'})
        assert info == {'state': 'complete', 'title': 'bench', 'width': 1280, 'height': 800}, info
        row['warm_navigation_ms'] = [client.navigate(f'{base}/tiny?warm={i}') for i in range(5)]
        if args.workload == 'graphics':
            client.navigate(f'{base}/large')
            _, result, _ = client.call('eval', {'expression': compare.EXTRACT})
            compare.validate_extract(result, 2000, 'large')
            row['extract_sha256'] = hashlib.sha256(json.dumps(result, sort_keys=True).encode()).hexdigest()
            path = args.output.with_suffix(f'.{label}-{round_}.png')
            row['screenshot_ms'], _, _ = client.call('screenshot', {'path': str(path)})
            row['png_sha256'] = digest(path)
            time.sleep(1)
            row['memory'] = [compare.memory_forest(before, bool(os.environ.get('DISPLAY'))) for _ in range(3)]
            assert all(sample['complete'] for sample in row['memory'])
        elif args.workload == 'transport':
            client.navigate(f'{base}/large')
            _, result, _ = client.call('eval', {'expression': f'window.cached = {compare.EXTRACT}'})
            compare.validate_extract(result, 2000, 'large')
            expressions = [('live_object', compare.EXTRACT), ('live_string', f'JSON.stringify({compare.EXTRACT})'),
                           ('cached_object', 'cached'), ('cached_string', 'JSON.stringify(cached)'),
                           ('stress_object', 'Array(10).fill(cached)')]
            row['transport'] = {}
            for name, expression in expressions:
                samples = []
                for i in range(18):
                    ms, value, wire = client.call('eval', {'expression': expression})
                    expected = [result] * 10 if name == 'stress_object' else result
                    assert (json.loads(value) if name.endswith('string') else value) == expected
                    if i >= 3:
                        samples.append({'ms': ms, 'wire_bytes': wire})
                row['transport'][name] = samples
        elif args.workload == 'timers':
            row['timers'] = []
            start = time.monotonic()
            for i in range(201):
                if i % 50 == 0:
                    row['timers'].append({'completed': i, 'elapsed_s': time.monotonic() - start,
                                          'parent': parent_status(before, binary),
                                          'memory': compare.memory_forest(before, bool(os.environ.get('DISPLAY')))})
                if i < 200:
                    client.navigate(f'{base}/tiny?timer={i}')
            assert all(sample['memory']['complete'] for sample in row['timers'])
        row['competing_after'] = compare.background_work(compare.owned_processes(before))
        if row['competing_after']:
            raise RuntimeError(f"Concurrent browser/build workload: {row['competing_after']}")
    except Exception as exc:
        row['error'] = repr(exc)
    finally:
        owned = compare.owned_processes(before)
        if client is not None:
            client.close()
            row['stderr'], row['close_error'] = client.stderr, client.close_error
        row['forced_cleanup'] = compare.cleanup(owned)
        row['finished_utc'] = datetime.now(timezone.utc).isoformat()
    return row


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('baseline', 'candidate', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--workload', choices=('startup', 'graphics', 'transport', 'timers'), default='startup')
    parser.add_argument('--rounds', type=int, default=20)
    args = parser.parse_args()
    if args.rounds < 1:
        parser.error('--rounds must be positive')
    args.baseline, args.candidate, args.output = args.baseline.resolve(), args.candidate.resolve(), args.output.resolve()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    if ctypes.CDLL(None, use_errno=True).prctl(36, 1, 0, 0, 0) != 0:
        raise OSError(ctypes.get_errno(), 'PR_SET_CHILD_SUBREAPER failed')
    report = {'metadata': {
        'started_utc': datetime.now(timezone.utc).isoformat(), 'platform': platform.platform(),
        'args': {key: str(value) if isinstance(value, Path) else value for key, value in vars(args).items()},
        'sha256': {name: digest(getattr(args, name)) for name in ('baseline', 'candidate')},
        'harness_sha256': {name: digest(Path(__file__).with_name(name)) for name in
                           ('bench_performance.py', 'bench_compare.py', 'bench_audit.py')},
        'environment': {key: value for key, value in os.environ.items()
                        if key.startswith(('BRUSTER_', 'WEBKIT_', 'GDK_')) or key in ('DISPLAY', 'WAYLAND_DISPLAY')},
    }, 'samples': []}
    server = audit.ThreadingHTTPServer(('127.0.0.1', 0), audit.Fixtures)
    server.image_hits, server.hits_lock = 0, threading.Lock()
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        for round_ in range(1, args.rounds + 1):
            for label in (('baseline', 'candidate') if round_ % 2 else ('candidate', 'baseline')):
                row = measure(args, server, label, round_)
                report['samples'].append(row)
                args.output.write_text(json.dumps(report, indent=2) + '\n')
                print(label, round_, row.get('launch_to_page_ms'), row.get('error', 'ok'), flush=True)
    finally:
        server.shutdown()
        server.server_close()
    report['metadata']['finished_utc'] = datetime.now(timezone.utc).isoformat()
    report['summary'] = {label: audit.summary([r['launch_to_page_ms'] for r in report['samples']
                                              if r['build'] == label and 'error' not in r])
                         for label in ('baseline', 'candidate')}
    args.output.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report['summary'], indent=2))
    if any(row.get('error') or row.get('close_error') or row['forced_cleanup'] for row in report['samples']):
        raise SystemExit('failed samples retained in output')


if __name__ == '__main__':
    main()
