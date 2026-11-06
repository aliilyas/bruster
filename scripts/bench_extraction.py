#!/usr/bin/env python3
"""Paired Linux reproduction of the public shared-JavaScript extraction workload.

Use the comparison driver's request-write to response-read timestamps. Preserve
post-navigation order, and report separately warmed extraction and order effects.
"""
import argparse
import ctypes
import hashlib
import json
import os
import platform
import shutil
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

import bench_audit as audit
import bench_compare as compare
from bench_optimizations import digest, summarize


FORMATS = ('object', 'json')


def extract(client, page, format_='object'):
    expression = compare.EXTRACT if format_ == 'object' else f'JSON.stringify({compare.EXTRACT})'
    elapsed, value, wire = client.call('eval', {'expression': expression})
    if format_ == 'json':
        value = json.loads(value)
    compare.validate_extract(value, 5 if page == 'tiny' else 2000,
                             'bench' if page == 'tiny' else 'large')
    return elapsed, value, wire


def large_pair(client, round_, iteration, row, warm=False, record=True):
    order = FORMATS[::-1] if (round_ + iteration) % 2 else FORMATS
    samples, values = [], []
    for position, format_ in enumerate(order):
        elapsed, value, wire = extract(client, 'large', format_)
        samples.append(elapsed)
        values.append(value)
        if record:
            key = 'large_extract' + ('_json' if format_ == 'json' else '') + ('_warm' if warm else '') + '_ms'
            row['timings'].setdefault(key, []).append(elapsed)
            row['order'].append({'phase': 'warm' if warm else 'post_navigation',
                                 'iteration': iteration, 'position': position,
                                 'format': format_, 'ms': elapsed, 'wire_bytes': wire})
    assert values[0] == values[1], 'object and JSON-string results differ'
    # Like the public comparison, hash after both calls. Hashing the first large
    # result before the second request would change the browser scheduling gap.
    result_hash = digest(values[0])
    assert row['correctness'].setdefault('large', result_hash) == result_hash, 'large result changed'
    if record and not warm:
        for name, value in [('first', samples[0]), ('second', samples[1]), ('pair', sum(samples))]:
            row['timings'].setdefault('large_extract_' + name + '_ms', []).append(value)


def workload(client, base, round_, iterations, row, memory_sample):
    client.navigate(f'{base}/tiny?first=bruster-{round_}')
    _, info, _ = client.call('eval', {'expression':
        '({width:innerWidth,height:innerHeight,state:document.readyState,userAgent:navigator.userAgent})'})
    assert (info['width'], info['height'], info['state']) == (1280, 800, 'complete'), info
    row['browser_info'] = info
    if round_ == 1:
        assert client.navigate(base + '/delayed') >= 240
    row['timings']['tiny_extract_ms'] = []
    for i in range(10):
        client.navigate(f'{base}/tiny?tool=bruster&round={round_}&i={i}')
        elapsed, value, _ = extract(client, 'tiny')
        result_hash = digest(value)
        row['timings']['tiny_extract_ms'].append(elapsed)
        assert row['correctness'].setdefault('tiny', result_hash) == result_hash
    # Match the public comparison's pause/memory sampling/native snapshot before
    # measuring the large page. No extra readiness probe precedes extraction.
    time.sleep(2)
    memory_sample()
    compare.native_snapshot(client, 'bruster', 5)
    for i in range(5):
        client.navigate(f'{base}/large?tool=bruster&round={round_}&i={i}')
        large_pair(client, round_, i, row)
    compare.native_snapshot(client, 'bruster', 2000)

    # Warmed diagnostics come after all public post-navigation measurements.
    client.navigate(base + '/tiny?warm=1')
    row['timings']['tiny_extract_warm_ms'] = []
    for i in range(iterations + 2):
        elapsed, value, _ = extract(client, 'tiny')
        assert row['correctness']['tiny'] == digest(value)
        if i >= 2:
            row['timings']['tiny_extract_warm_ms'].append(elapsed)
    client.navigate(base + '/large?warm=1')
    for i in range(iterations + 2):
        large_pair(client, round_, i, row, warm=True, record=i >= 2)


def measure(args, base, binary, round_, label):
    before = compare.process_table()
    row = {'round': round_, 'build': label, 'transport': 'native',
           'timings': {}, 'correctness': {}, 'order': [],
           'started_utc': datetime.now(timezone.utc).isoformat(),
           'load_before': os.getloadavg(), 'competing_before': compare.background_work()}
    client = None
    try:
        if row['competing_before'] and not args.diagnostic:
            raise RuntimeError(f"Concurrent workload: {row['competing_before']}")
        client = compare.ProcessClient([str(binary), '--hidden'], False)

        def memory_sample():
            row['competing_at_memory'] = compare.background_work(before=before)
            row['idle_memory'] = []
            for _ in range(3):
                sample = compare.memory_forest(before, True)
                assert sample['complete'], sample
                row['idle_memory'].append(sample)
                time.sleep(0.1)

        workload(client, base, round_, args.iterations, row, memory_sample)
        row['load_after'] = os.getloadavg()
        row['competing_after'] = compare.background_work(before=before)
        if (row['competing_at_memory'] or row['competing_after']) and not args.diagnostic:
            raise RuntimeError('Concurrent workload during extraction')
    except Exception as exc:
        row['error'] = repr(exc)
    finally:
        if client is not None:
            client.close()
            row['close_error'], row['stderr'] = client.close_error, client.stderr
            if client.close_error is not None:
                row.setdefault('error', 'graceful close failed: ' + client.close_error)
        row['forced_cleanup'] = compare.cleanup(compare.owned_processes(before))
        if row['forced_cleanup']:
            row.setdefault('error', 'forced process cleanup')
    return row


def report_markdown(report):
    metadata = report['metadata']
    lines = ['# Paired shared-JavaScript extraction', '',
             f'{metadata["rounds"]} alternating JSONL pairs. Publishable: {metadata["publishable"]}.',
             'The public EXTRACT expression and driver timing boundaries are reused.',
             'Post-navigation: ten tiny navigations; five large navigations with alternating object/string order.',
             'Warm: two discarded warmups per format, then repeated calls on the loaded page.',
             'First/second metrics separate order effects; pair is the sum of both call latencies per navigation.',
             'All decoded extraction hashes matched. Negative changes are better.',
             'Session medians, paired geometric changes and pointwise 95% bootstrap intervals.',
             'Five post-navigation samples per format can yield unstable medians for bimodal timings.', '',
             '| Metric | Baseline ms | Candidate ms | Paired change | 95% interval |',
             '|---|---:|---:|---:|---:|']
    for key, value in report['summary'].items():
        lo, hi = value['interval95_percent']
        lines.append(f'| {key} | {value["baseline_median"]:.3f} | {value["candidate_median"]:.3f} | '
                     f'{value["paired_change_percent"]:+.2f}% | {lo:+.2f}% to {hi:+.2f}% |')
    return '\n'.join(lines) + '\n'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('baseline', 'candidate', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--rounds', type=int, default=20)
    parser.add_argument('--iterations', type=int, default=24, help='warmed samples per format')
    parser.add_argument('--diagnostic', action='store_true')
    args = parser.parse_args()
    if not sys.platform.startswith('linux'):
        parser.error('the public comparison and this paired probe use Linux')
    if min(args.rounds, args.iterations) < 1:
        parser.error('rounds and iterations must be positive')
    if os.environ.get('BRUSTER_TRACE_PERF') == '1' and not args.diagnostic:
        parser.error('disable BRUSTER_TRACE_PERF for performance measurements')
    args.baseline, args.candidate, args.output = args.baseline.resolve(), args.candidate.resolve(), args.output.resolve()
    args.output.mkdir(parents=True, exist_ok=False)
    if ctypes.CDLL(None, use_errno=True).prctl(36, 1, 0, 0, 0) != 0:
        raise OSError(ctypes.get_errno(), 'PR_SET_CHILD_SUBREAPER failed')
    harness = args.output / 'harness'
    harness.mkdir()
    for name in ('bench_extraction.py', 'bench_optimizations.py', 'bench_compare.py', 'bench_audit.py', 'bench_tools.py'):
        shutil.copy2(Path(__file__).with_name(name), harness / name)
    shutil.copytree(Path(__file__).with_name('lab'), harness / 'lab', ignore=shutil.ignore_patterns('__pycache__'))
    (args.output / 'benchmarks').mkdir()
    shutil.copy2(compare.CATALOG_PATH, args.output / 'benchmarks' / compare.CATALOG_PATH.name)
    sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
    report = {'metadata': {'diagnostic': args.diagnostic, 'publishable': False,
        'platform': platform.platform(), 'python': sys.version, 'rounds': args.rounds,
        'args': {k: str(v) for k, v in vars(args).items()}, 'extract': compare.EXTRACT,
        'binary_sha256': {label: sha(getattr(args, label)) for label in ('baseline', 'candidate')},
        'harness_sha256': {str(p.relative_to(harness)): sha(p) for p in harness.rglob('*.py')},
        'cpu': Path('/proc/cpuinfo').read_text(),
        'environment': {k: v for k, v in os.environ.items() if k in (
            'DISPLAY', 'BRUSTER_TRACE_PERF', 'BRUSTER_USE_SESSION_BUS', 'BRUSTER_PAINT_HIDDEN',
            'WEBKIT_DISABLE_COMPOSITING_MODE', 'WEBKIT_DISABLE_DMABUF_RENDERER',
            'GITHUB_RUN_ID', 'GITHUB_RUN_ATTEMPT', 'GITHUB_SHA', 'GITHUB_REF',
            'GITHUB_WORKFLOW', 'GITHUB_REPOSITORY', 'ImageOS', 'ImageVersion')}}, 'samples': []}
    server = audit.ThreadingHTTPServer(('127.0.0.1', 0), audit.Fixtures)
    server.image_hits, server.hits_lock = 0, threading.Lock()
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        for round_ in range(1, args.rounds + 1):
            for label in (('baseline', 'candidate') if round_ % 2 else ('candidate', 'baseline')):
                row = measure(args, f'http://127.0.0.1:{server.server_port}', getattr(args, label), round_, label)
                report['samples'].append(row)
                (args.output / 'results.json').write_text(json.dumps(report, indent=2) + '\n')
                print(round_, label, row.get('error', 'ok'), flush=True)
                if 'error' in row:
                    raise RuntimeError(row['error'])
        report['summary'] = summarize(report['samples'])
        report['metadata']['publishable'] = not args.diagnostic and args.rounds >= 20
        (args.output / 'results.json').write_text(json.dumps(report, indent=2) + '\n')
        (args.output / 'report.md').write_text(report_markdown(report))
    finally:
        server.shutdown()
        server.server_close()


if __name__ == '__main__':
    main()
