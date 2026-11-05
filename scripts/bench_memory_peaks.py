#!/usr/bin/env python3
"""Paired Linux screenshot peak sampling with frozen baseline/candidate binaries.

Run under the same display/runtime used by the native tests. PSS/USS/RSS/swap
cover the complete browser process forest, excluding this controller and Xvfb.
Sampling is observational: short peaks can fall between samples.
"""
import argparse
import base64
import ctypes
import hashlib
import json
import os
import platform
import statistics
import struct
import threading
import time
from pathlib import Path

import bench_compare as compare


FIXTURE = """(() => {
    document.documentElement.style.cssText = 'margin:0;overflow:hidden';
    document.body.style.cssText = 'margin:0;width:1280px;height:16000px;background:repeating-linear-gradient(0deg,#acf 0px,#acf 8px,#639 8px,#639 16px)';
    return [innerWidth, innerHeight, devicePixelRatio];
})()"""
METRICS = ('pss_kib', 'uss_kib', 'rss_kib', 'swap_kib')


def sample(before, root):
    started = time.monotonic()
    rows, errors = [], []
    for pid, process in compare.owned_processes(before).items():
        if process['state'] == 'Z':
            continue
        path = Path('/proc') / str(pid)
        try:
            fields = {}
            for line in (path / 'smaps_rollup').read_text().splitlines()[1:]:
                key, value, *_ = line.split()
                fields[key.rstrip(':')] = int(value)
            rows.append({
                'pid': pid, 'host': pid == root, 'name': (path / 'comm').read_text().strip(),
                'pss_kib': fields['Pss'], 'rss_kib': fields['Rss'],
                'uss_kib': sum(fields.get(k, 0) for k in ('Private_Clean', 'Private_Dirty', 'Private_Hugetlb')),
                'swap_kib': fields['Swap'],
            })
        except (OSError, ValueError, KeyError) as exc:
            errors.append({'pid': pid, 'error': str(exc)})
    complete = not errors and any(row['host'] for row in rows)
    return {
        'at': started, 'sample_ms': (time.monotonic() - started) * 1000,
        'complete': complete, 'processes': rows, 'errors': errors,
        **{key: sum(row[key] for row in rows) if complete else None for key in METRICS},
    }


def measure(binary, label, round_, mode, interval, output, ignore):
    before = compare.process_table()
    browser = compare.ProcessClient([str(binary), '--hidden', '--viewport', '1280x800'], False)
    row = {'build': label, 'round': round_, 'mode': mode, 'samples': []}
    try:
        # Both builds warm an about:blank document before page commands run.
        _, geometry, _ = browser.call('eval', {'expression': FIXTURE})
        assert geometry == [1280, 800, 1], f'requires scale 1: {geometry}'
        time.sleep(1)
        row['before'] = sample(before, browser.proc.pid)
        stop, ready = threading.Event(), threading.Event()

        def sampler():
            while not stop.is_set():
                row['samples'].append(sample(before, browser.proc.pid))
                ready.set()
                stop.wait(interval)

        worker = threading.Thread(target=sampler)
        worker.start()
        ready.wait()
        params = {'full': True}
        path = output / f'{label}-{round_}-{mode}.png'
        if mode == 'file':
            params['path'] = str(path)
        try:
            row['duration_ms'], result, row['wire_bytes'] = browser.call('screenshot', params)
        finally:
            stop.set()
            worker.join()
        row['samples'].append(sample(before, browser.proc.pid))
        png = path.read_bytes() if mode == 'file' else base64.b64decode(result['png_base64'], validate=True)
        assert png[:8] == b'\x89PNG\r\n\x1a\n'
        row['dimensions'] = struct.unpack('>II', png[16:24])
        assert row['dimensions'] == (1280, 16000), row['dimensions']
        row['png_bytes'] = len(png)
        row['png_sha256'] = hashlib.sha256(png).hexdigest()
        del png, result
        time.sleep(1)
        row['after'] = sample(before, browser.proc.pid)
        assert all(s['complete'] for s in [row['before'], *row['samples'], row['after']]), row
        row['peak_mib'] = {key.replace('_kib', '_mib'): max(s[key] for s in row['samples']) / 1024 for key in METRICS}
        row['competing_after'] = compare.background_work(exclude=ignore, before=before)
    finally:
        owned = compare.owned_processes(before)
        browser.close()
        row['forced_cleanup'] = compare.cleanup(owned)
    return row


def summarize(runs):
    return {
        mode: {label: {
            **{key: statistics.median(r['peak_mib'][key] for r in runs
                                      if r['mode'] == mode and r['build'] == label)
               for key in (metric.replace('_kib', '_mib') for metric in METRICS)},
            'duration_ms': statistics.median(r['duration_ms'] for r in runs
                                            if r['mode'] == mode and r['build'] == label),
        } for label in ('baseline', 'candidate')} for mode in ('file', 'inline')
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline', type=Path, required=True)
    parser.add_argument('--candidate', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--rounds', type=int, default=3)
    parser.add_argument('--interval', type=float, default=0.02)
    parser.add_argument('--ignore-pid', type=int, action='append', default=[],
                        help='record but exclude this background process from competition detection')
    args = parser.parse_args()
    if platform.system() != 'Linux' or args.rounds < 1 or args.interval <= 0:
        parser.error('requires Linux, positive rounds and positive sample interval')
    # Include reparented native helpers in ownership/cleanup.
    assert ctypes.CDLL(None).prctl(36, 1, 0, 0, 0) == 0
    args.output = args.output.resolve()
    args.output.mkdir(parents=True, exist_ok=True)
    binaries = {key: getattr(args, key).resolve() for key in ('baseline', 'candidate')}
    report = {
        'platform': platform.platform(), 'display': os.environ.get('DISPLAY'),
        'interval_seconds': args.interval, 'fixture': FIXTURE,
        'accounting': 'browser forest; excludes controller and display; per-process reads are not simultaneous',
        'binaries': {key: {'path': str(path), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
                     for key, path in binaries.items()},
        'competing_before': compare.background_work(exclude=args.ignore_pid),
        'ignored_background': [row for row in compare.background_work() if row['pid'] in args.ignore_pid],
        'runs': [],
    }
    if report['competing_before']:
        raise RuntimeError(f"competing browser/compiler processes: {report['competing_before']}")
    for round_ in range(1, args.rounds + 1):
        order = ('baseline', 'candidate') if round_ % 2 else ('candidate', 'baseline')
        for mode in ('file', 'inline'):
            for label in order:
                row = measure(binaries[label], label, round_, mode, args.interval, args.output, args.ignore_pid)
                report['runs'].append(row)
                (args.output / 'samples.json').write_text(json.dumps(report, indent=2) + '\n')
                print(label, round_, mode, row['peak_mib'], flush=True)
                if row['competing_after'] or row['forced_cleanup']:
                    raise RuntimeError('competing processes or forced cleanup; see samples.json')
    report['summary'] = summarize(report['runs'])
    (args.output / 'samples.json').write_text(json.dumps(report, indent=2) + '\n')
    (args.output / 'summary.json').write_text(json.dumps(report['summary'], indent=2) + '\n')
    print(json.dumps(report['summary'], indent=2))


if __name__ == '__main__':
    main()
