#!/usr/bin/env python3
"""Same-Mac Bruster/SleepyHollow timing cohort using the shared localhost fixtures.

Apple's XPC WebKit helpers are not a Linux process forest. This cohort reports
validated operation timings only; it makes no PSS, RSS or runtime-size claims.
"""
import argparse
import hashlib
import json
import os
import platform
import struct
import subprocess
import tempfile
import threading
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path

import bench_audit as audit
from bench_compare import EXTRACT, ProcessClient, failure_checks, isolated_environment, validate_extract


class SleepyClient:
    def __init__(self, executable):
        self.executable = str(executable)
        # Keep the registry path short: macOS Unix sockets have a 104-byte limit.
        self.temp = tempfile.TemporaryDirectory(prefix='sh-')
        self.env = isolated_environment(self.temp.name, False)
        self.env['SLEEPYHOLLOW_HOME'] = self.temp.name
        self.stderr, self.close_error = [], None
        self.started_ns = time.perf_counter_ns()
        try:
            self.invoke('open', 'about:blank', '--name', 'bench', '--size', '1280x800',
                        '--wait-for', 'load', '--budget', '60000', '--idle-timeout', '120')
            self.startup_ms = (time.perf_counter_ns() - self.started_ns) / 1e6
        except BaseException:
            self.close()
            raise

    def invoke(self, *args, json_output=True):
        start = time.perf_counter_ns()
        proc = subprocess.run([self.executable, *args], env=self.env, capture_output=True, timeout=75)
        elapsed = (time.perf_counter_ns() - start) / 1e6
        self.stderr.extend(proc.stderr.decode(errors='replace').splitlines())
        # Sleepy's eval deliberately exits 1 for a valid Boolean false result.
        false_result = args[0] == 'eval' and proc.returncode == 1 and proc.stdout.strip() == b'false'
        if proc.returncode and not false_result:
            raise RuntimeError(f'sleepy {args}: {proc.stdout!r} {proc.stderr!r}')
        return elapsed, json.loads(proc.stdout) if json_output else None, len(proc.stdout)

    def call(self, method, params=None):
        params = params or {}
        if method == 'navigate':
            elapsed, facts, size = self.invoke('load', '--session', 'bench', params['url'])
            return elapsed, {'url': facts.get('finalURL'), 'status': facts.get('httpStatus')}, size
        if method == 'eval':
            return self.invoke('eval', '--session', 'bench', '--js', f"return ({params['expression']});")
        if method == 'screenshot':
            return self.invoke('shot', '--session', 'bench', '--scale', str(params['scale']),
                               '--out', params['path'], json_output=False)
        raise ValueError(method)

    def navigate(self, url):
        elapsed, result, _ = self.call('navigate', {'url': url})
        assert result['url'] == url and result['status'] == 200, result
        return elapsed

    def close(self):
        try:
            self.invoke('close', 'bench', json_output=False)
        except (OSError, RuntimeError, subprocess.TimeoutExpired) as exc:
            self.close_error = str(exc)
        finally:
            self.temp.cleanup()


def measure(args, server, tool, round_):
    client = SleepyClient(args.sleepy) if tool == 'sleepyhollow' else ProcessClient([str(args.bruster), '--hidden'], False)
    row = {'tool': tool, 'round': round_, 'startup_ms': client.startup_ms, 'failures': []}
    base = f'http://127.0.0.1:{server.server_port}'
    try:
        row['first_navigation_ms'] = client.navigate(f'{base}/tiny?first={tool}-{round_}')
        row['launch_to_first_page_ms'] = (time.perf_counter_ns() - client.started_ns) / 1e6
        _, info, _ = client.call('eval', {'expression': '({width:innerWidth,height:innerHeight,scale:devicePixelRatio,state:document.readyState,userAgent:navigator.userAgent})'})
        assert (info['width'], info['height'], info['state']) == (1280, 800, 'complete'), info
        assert info['scale'] in (1, 2, 3), info
        row['browser_info'] = info
        row['delayed_validation_ms'] = client.navigate(f'{base}/delayed')
        assert row['delayed_validation_ms'] >= 240
        for page, count, title in [('tiny', 5, 'bench'), ('large', 2000, 'large')]:
            row[f'{page}_navigation_ms'], row[f'{page}_extract_ms'] = [], []
            for i in range(args.iterations):
                row[f'{page}_navigation_ms'].append(client.navigate(f'{base}/{page}?tool={tool}&round={round_}&i={i}'))
                elapsed, result, _ = client.call('eval', {'expression': EXTRACT})
                validate_extract(result, count, title)
                row[f'{page}_extract_ms'].append(elapsed)
                if page == 'large':
                    row['large_extract_sha256'] = hashlib.sha256(json.dumps(result, sort_keys=True).encode()).hexdigest()
        hits = server.image_hits
        row['image_navigation_ms'] = [client.navigate(f'{base}/images?tool={tool}&i={i}') for i in range(3)]
        assert server.image_hits - hits == 36
        _, widths, _ = client.call('eval', {'expression': 'Array.from(document.images, i => i.naturalWidth)'})
        assert widths == [128] * 12
        row['screenshot_ms'] = []
        for i in range(2):
            path = args.output / f'{tool}-{round_}-{i}.png'
            params = {'path': str(path)}
            if tool == 'sleepyhollow':
                # Bruster's WKSnapshot uses this Mac's native backing scale.
                params['scale'] = int(info['scale'])
            elapsed, _, _ = client.call('screenshot', params)
            data = path.read_bytes()
            assert data[:8] == b'\x89PNG\r\n\x1a\n'
            assert struct.unpack('>II', data[16:24]) == (1280 * info['scale'], 800 * info['scale'])
            assert len(data) > 1000
            row['screenshot_ms'].append(elapsed)
        row['failure_checks'] = failure_checks(client, base)
        row['failures'].extend(c for c in row['failure_checks'] if not c['pass'])
    finally:
        client.close()
        if client.close_error:
            row['failures'].append({'name': 'graceful_close', 'pass': False, 'error': client.close_error})
        row['stderr'] = client.stderr
        (args.output / f'{tool}-{round_}.json').write_text(json.dumps(row, indent=2) + '\n')
        if client.close_error:
            # No Linux subreaper here: stop instead of timing the next session
            # alongside a possibly still-running WebKit helper.
            raise RuntimeError(f'{tool} shutdown failed: {client.close_error}')
    return row


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('bruster', 'sleepy', 'sleepy-source', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--rounds', type=int, default=10)
    parser.add_argument('--iterations', type=int, default=10)
    args = parser.parse_args()
    if platform.system() != 'Darwin':
        parser.error('SleepyHollow requires macOS; run this cohort on a Mac')
    if args.rounds < 1 or args.iterations < 1:
        parser.error('rounds and iterations must be positive')
    for name in ('bruster', 'sleepy', 'sleepy_source'):
        setattr(args, name, getattr(args, name).resolve(strict=True))
    args.output = args.output.resolve()
    args.output.mkdir(parents=True, exist_ok=True)
    metadata = {
        'cohort': 'macos-timing', 'platform': platform.platform(), 'machine': platform.machine(),
        'cpu': subprocess.check_output(['sysctl', '-n', 'machdep.cpu.brand_string'], text=True).strip(),
        'started_utc': datetime.now(timezone.utc).isoformat(), 'rounds': args.rounds, 'iterations': args.iterations,
        'sleepyhollow_github': 'https://github.com/bensyverson/sleepyhollow',
        'sleepyhollow_commit': subprocess.check_output(['git', '-C', str(args.sleepy_source), 'rev-parse', 'HEAD'], text=True).strip(),
        'bruster_commit': subprocess.check_output(['git', '-C', str(Path(__file__).resolve().parent.parent), 'rev-parse', 'HEAD'], text=True).strip(),
        'swift': subprocess.check_output(['swift', '--version'], text=True).strip(),
        'rustc': subprocess.check_output(['rustc', '--version'], text=True).strip(),
        'sleepyhollow_package_resolved_sha256': hashlib.sha256((args.sleepy_source / 'Package.resolved').read_bytes()).hexdigest(),
        'bruster_sha256': hashlib.sha256(args.bruster.read_bytes()).hexdigest(),
        'sleepy_sha256': hashlib.sha256(args.sleepy.read_bytes()).hexdigest(),
        'harness_sha256': {name: hashlib.sha256(Path(__file__).with_name(name).read_bytes()).hexdigest()
                           for name in ('bench_sleepyhollow.py', 'bench_compare.py', 'bench_audit.py', 'bench_tools.py')},
        'run_url': f"https://github.com/{os.environ.get('GITHUB_REPOSITORY', 'aliilyas/bruster')}/actions/runs/{os.environ.get('GITHUB_RUN_ID', '')}",
        'common_extraction_js': EXTRACT,
        'scope': 'Same-Mac timings only. No memory/footprint estimates. CLI process launches included. '
                 '1280x800 CSS viewport; both screenshots use the native display backing scale. '
                 'Fresh sessions, rotating order, same fixtures and extraction as Linux; separate cohort, not cross-OS rankings.',
    }
    (args.output / 'metadata.json').write_text(json.dumps(metadata, indent=2) + '\n')
    server = audit.ThreadingHTTPServer(('127.0.0.1', 0), audit.Fixtures)
    server.image_hits, server.hits_lock = 0, threading.Lock()
    threading.Thread(target=server.serve_forever, daemon=True).start()
    rows = []
    try:
        for round_ in range(1, args.rounds + 1):
            tools = ['bruster', 'sleepyhollow'] if round_ % 2 else ['sleepyhollow', 'bruster']
            for tool in tools:
                rows.append(measure(args, server, tool, round_))
                (args.output / 'samples.json').write_text(json.dumps(rows, indent=2) + '\n')
        assert len({row['large_extract_sha256'] for row in rows}) == 1, 'Cross-tool extraction mismatch'
        assert len({row['browser_info']['scale'] for row in rows}) == 1, 'Cross-tool screenshot scales differ'
    except BaseException:
        (args.output / 'error.txt').write_text(traceback.format_exc())
        raise
    finally:
        server.shutdown()
        server.server_close()
    metrics = [key for key in rows[0] if key.endswith('_ms') and key != 'delayed_validation_ms']
    stats = {}
    for tool in ('bruster', 'sleepyhollow'):
        subset = [row for row in rows if row['tool'] == tool]
        stats[tool] = {key: audit.summary([value for row in subset
                       for value in (row[key] if isinstance(row[key], list) else [row[key]])]) for key in metrics}
    metadata['finished_utc'] = datetime.now(timezone.utc).isoformat()
    (args.output / 'summary.json').write_text(json.dumps({'metadata': metadata, 'summary': stats}, indent=2) + '\n')
    lines = ['# macOS: Bruster and SleepyHollow', '', metadata['scope'], '',
             f"SleepyHollow commit: `{metadata['sleepyhollow_commit']}`. {args.rounds} sessions each.", '',
             '| Metric (ms) | Bruster / Apple WebKit | SleepyHollow / Apple WebKit |', '|---|---:|---:|']
    for key in metrics:
        cells = [f"{stats[t][key]['median']:.1f} [{stats[t][key]['min']:.1f}–{stats[t][key]['max']:.1f}]" for t in stats]
        lines.append('| ' + ' | '.join([key, *cells]) + ' |')
    for tool in stats:
        failures = [{'round': r['round'], **f} for r in rows if r['tool'] == tool for f in r['failures']]
        lines.extend(['', f'{tool} fault/close failures: `{json.dumps(failures)}`'])
    (args.output / 'report.md').write_text('\n'.join(lines) + '\n')


if __name__ == '__main__':
    main()
