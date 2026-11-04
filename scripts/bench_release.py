#!/usr/bin/env python3
"""Alternate published release binaries through the production benchmark workload."""
import argparse
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
import threading
import traceback
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import bench_audit as audit
import bench_compare as compare


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def metrics(row):
    values = {key: row[key] for key in ('startup_ms', 'first_navigation_ms', 'launch_to_first_page_ms')}
    for key in ('tiny_navigation_ms', 'tiny_extract_ms', 'large_navigation_ms', 'large_extract_ms',
                'large_extract_json_ms', 'image_navigation_ms', 'screenshot_ms'):
        values[key] = statistics.median(row[key])
    for key in ('rss_mib', 'pss_mib', 'display_pss_mib', 'total_pss_mib'):
        values[key] = statistics.median(sample[key] for sample in row['idle_memory'])
    for page in ('tiny', 'large'):
        values[f'native_{page}_snapshot_ms'] = row[f'native_{page}_snapshot']['ms']
    return values


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('baseline', 'candidate', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--baseline-tag', default='v0.3.3')
    parser.add_argument('--candidate-tag', default='v0.3.4')
    parser.add_argument('--rounds', type=int, default=40)
    args = parser.parse_args()
    if args.rounds < 2:
        parser.error('--rounds must be at least 2')
    repo = Path(__file__).resolve().parents[1]
    if ctypes.CDLL(None, use_errno=True).prctl(36, 1, 0, 0, 0) != 0:
        raise OSError(ctypes.get_errno(), 'PR_SET_CHILD_SUBREAPER failed')
    args.output.mkdir(parents=True, exist_ok=True)
    binaries = {label: getattr(args, label).resolve(strict=True) for label in ('baseline', 'candidate')}
    sources = ['scripts/' + name for name in ('bench_release.py', 'bench_audit.py', 'bench_compare.py', 'bench_tools.py')]
    sources.append('benchmarks/competitors.json')
    for name in sources:
        destination = args.output / 'harness' / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(repo / name, destination)
    metadata = {
        'started_utc': datetime.now(timezone.utc).isoformat(),
        'platform': platform.platform(), 'cpu_count': os.cpu_count(),
        'cpuinfo': Path('/proc/cpuinfo').read_text().split('\n\n')[0],
        'memory': Path('/proc/meminfo').read_text(),
        'args': {key: str(value) if isinstance(value, Path) else value for key, value in vars(args).items()},
        'commits': {label: subprocess.check_output(['git', 'rev-parse', ref + '^{commit}'], cwd=repo, text=True).strip()
                    for label, ref in (('baseline', args.baseline_tag), ('candidate', args.candidate_tag), ('harness', 'HEAD'))},
        'binaries': {label: {'path': str(path), 'sha256': digest(path), 'bytes': path.stat().st_size}
                     for label, path in binaries.items()},
        'harness_sha256': {name: digest(repo / name) for name in sources},
        'libraries': subprocess.check_output(['pkg-config', '--modversion', 'webkit2gtk-4.1', 'gtk+-3.0'], text=True).splitlines(),
        'environment': {key: os.environ[key] for key in ('DISPLAY', 'WAYLAND_DISPLAY', 'ImageOS', 'ImageVersion', 'RUNNER_ARCH',
                                                        'GITHUB_REPOSITORY', 'GITHUB_RUN_ID', 'GITHUB_RUN_ATTEMPT') if key in os.environ},
        'methodology': 'Fresh HOME/XDG per session; alternating AB/BA order; OS caches retained; external Xvfb included in PSS '
                       'but excluded from startup. Unchanged bench_compare.measure with 10 tiny iterations. Per-session medians, '
                       'paired geometric ratios and seeded 10000-resample pointwise bootstrap intervals.',
    }
    report = {'metadata': metadata, 'samples': []}
    lifecycle = []
    original_client = compare.ProcessClient

    class RecordedClient(original_client):
        def close(self):
            try:
                super().close()
            finally:
                lifecycle.append({'returncode': self.proc.returncode, 'stderr': self.stderr, 'close_error': self.close_error})

    compare.ProcessClient = RecordedClient

    def save():
        (args.output / 'paired.json').write_text(json.dumps(report, indent=2) + '\n')

    server = audit.ThreadingHTTPServer(('127.0.0.1', 0), audit.Fixtures)
    server.image_hits, server.hits_lock = 0, threading.Lock()
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        for round_ in range(1, args.rounds + 1):
            pair = {}
            for label in (('baseline', 'candidate') if round_ % 2 else ('candidate', 'baseline')):
                output = args.output / label
                (output / 'screenshots').mkdir(parents=True, exist_ok=True)
                lifecycle.clear()
                try:
                    row = compare.measure(SimpleNamespace(bruster=binaries[label], output=output, iterations=10), server, 'bruster', round_)
                except Exception:
                    report['samples'].append({'build': label, 'round': round_, 'error': traceback.format_exc(), 'lifecycle': lifecycle.copy()})
                    save()
                    raise
                row['build'], row['lifecycle'] = label, lifecycle.copy()
                report['samples'].append(row)
                pair[label] = row
                save()
                print(label, round_, json.dumps(metrics(row)), 'failures:', row['failures'], flush=True)
                assert not row['failures'], row['failures']
                assert lifecycle and all(item['returncode'] == 0 for item in lifecycle), lifecycle
            assert pair['baseline']['large_extract_sha256'] == pair['candidate']['large_extract_sha256']
            for page in ('tiny', 'large'):
                assert pair['baseline'][f'native_{page}_snapshot']['result'] == pair['candidate'][f'native_{page}_snapshot']['result']
    finally:
        server.shutdown()
        server.server_close()
    rows = {label: [metrics(row) for row in report['samples'] if row['build'] == label] for label in binaries}
    rng = random.Random(0)
    summary = {}
    for key in rows['baseline'][0]:
        baseline, candidate = ([row[key] for row in rows[label]] for label in binaries)
        ratios = [math.log(c / b) for b, c in zip(baseline, candidate)]
        boot = sorted((math.exp(statistics.mean(rng.choices(ratios, k=len(ratios)))) - 1) * 100 for _ in range(10000))
        summary[key] = {'baseline': audit.summary(baseline), 'candidate': audit.summary(candidate),
                        'paired_change_percent': (math.exp(statistics.mean(ratios)) - 1) * 100,
                        'paired_bootstrap_95_percent': [boot[250], boot[9749]]}
    report['summary'] = summary
    metadata['finished_utc'] = datetime.now(timezone.utc).isoformat()
    metadata['all_correctness_and_cleanup_checks_passed'] = True
    save()
    (args.output / 'summary.json').write_text(json.dumps({'metadata': metadata, 'summary': summary}, indent=2) + '\n')
    lines = [f'# {args.candidate_tag} versus {args.baseline_tag}: paired Linux release comparison', '',
             f'{args.rounds} fresh sessions per release; alternating order on the same runner. All correctness and cleanup checks passed.', '',
             'Per-session medians; paired geometric percentage changes. Negative is better. '
             'Pointwise 95% bootstrap intervals are not simultaneous confidence bounds or an all-metric performance gate.', '',
             '| Metric | Baseline median | Candidate median | Paired change | 95% interval |', '|---|---:|---:|---:|---:|']
    for key, value in summary.items():
        lo, hi = value['paired_bootstrap_95_percent']
        lines.append(f"| {key} | {value['baseline']['median']:.3f} | {value['candidate']['median']:.3f} "
                     f"| {value['paired_change_percent']:+.2f}% | {lo:+.2f}% to {hi:+.2f}% |")
    (args.output / 'report.md').write_text('\n'.join(lines) + '\n')
    print('\n'.join(lines), flush=True)


if __name__ == '__main__':
    main()
