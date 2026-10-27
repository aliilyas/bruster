#!/usr/bin/env python3
"""Same-machine Linux comparison: Bruster, Playwright, Puppeteer, agent-browser.

Use an isolated dependency directory containing resolved playwright-core,
puppeteer-core, agent-browser packages and a shared full Chromium executable.
Run this controller under Xvfb. Chromium clients run headless without DISPLAY.
"""
import argparse
import ctypes
import hashlib
import json
import os
import platform
import queue
import signal
import socket
import statistics
import struct
import subprocess
import tempfile
import threading
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path

import bench_audit as audit


TOOLS = ['bruster', 'playwright', 'puppeteer', 'agent-browser', 'playwright-shell']
EXTRACT = """(() => ({
  title: document.title,
  elements: Array.from(document.querySelectorAll('h1,h2,h3,p,li,a,input,button,select,textarea'))
    .filter(e => { const r = e.getBoundingClientRect(); return r.width > 0 && r.height > 0; })
    .map(e => ({tag: e.tagName.toLowerCase(),
      name: (e.getAttribute('aria-label') || e.getAttribute('placeholder') || e.textContent || '').trim(),
      href: e.getAttribute('href'), value: 'value' in e ? e.value : null}))
}))()"""


def isolated_environment(temp, chromium):
    env = os.environ.copy()
    for key in list(env):
        if key.startswith('AGENT_BROWSER_'):
            del env[key]
    env['HOME'] = temp
    for key in ('XDG_CACHE_HOME', 'XDG_CONFIG_HOME', 'XDG_DATA_HOME', 'XDG_STATE_HOME'):
        env[key] = str(Path(temp) / key.lower())
    if chromium:
        env.pop('DISPLAY', None)
        env.pop('WAYLAND_DISPLAY', None)
    return env


class ProcessClient(audit.Browser):
    def __init__(self, command, chromium):
        self.timeout = 60
        self.close_error = None
        self.events, self.stderr, self.next_id = queue.Queue(), [], 0
        self.temp = tempfile.TemporaryDirectory(prefix='bruster-compare-')
        self.started_ns = time.perf_counter_ns()
        self.proc = subprocess.Popen(
            command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            env=isolated_environment(self.temp.name, chromium), start_new_session=True,
        )
        self.reader = threading.Thread(target=self._read, daemon=True)
        self.err_reader = threading.Thread(target=self._read_errors, daemon=True)
        self.reader.start()
        self.err_reader.start()
        try:
            stamp, self.ready, _ = self.wait(lambda o: o.get('event') == 'ready')
            self.startup_ms = (stamp - self.started_ns) / 1e6
        except BaseException:
            self.close()
            raise

    def close(self):
        if self.proc.poll() is None:
            try:
                self.call('close')
                self.proc.wait(timeout=15)
            except (OSError, RuntimeError, TimeoutError, subprocess.TimeoutExpired) as exc:
                self.close_error = str(exc)
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


class AgentClient:
    def __init__(self, executable, chrome, run_id):
        self.executable = executable
        self.temp = tempfile.TemporaryDirectory(prefix='agent-browser-compare-')
        self.env = isolated_environment(self.temp.name, True)
        self.env.update(AGENT_BROWSER_NAMESPACE=f'bruster-comparison-{os.getpid()}-{run_id}',
                        AGENT_BROWSER_SESSION='bench', AGENT_BROWSER_EXECUTABLE_PATH=str(chrome))
        self.stderr = []
        self.started_ns = time.perf_counter_ns()
        try:
            self.invoke('open', 'about:blank')
            self.invoke('set', 'viewport', '1280', '800')
            self.startup_ms = (time.perf_counter_ns() - self.started_ns) / 1e6
        except BaseException:
            self.close()
            raise

    def invoke(self, *args):
        command = [str(self.executable), '--json', '--args', '--no-sandbox', *args]
        start = time.perf_counter_ns()
        proc = subprocess.run(command, env=self.env, capture_output=True, timeout=60)
        elapsed = (time.perf_counter_ns() - start) / 1e6
        self.stderr.extend(proc.stderr.decode(errors='replace').splitlines())
        if proc.returncode:
            raise RuntimeError(f'agent-browser {args}: {proc.stdout!r} {proc.stderr!r}')
        obj = json.loads(proc.stdout)
        if not obj.get('success'):
            raise RuntimeError(f'agent-browser {args}: {obj}')
        return elapsed, obj['data'], len(proc.stdout)

    def call(self, method, params=None):
        params = params or {}
        if method == 'navigate':
            return self.invoke('open', params['url'])
        if method == 'eval':
            elapsed, data, size = self.invoke('eval', params['expression'])
            return elapsed, data['result'], size
        if method == 'snapshot':
            return self.invoke('snapshot')
        if method == 'screenshot':
            return self.invoke('screenshot', params['path'])
        if method == 'close':
            return self.invoke('close')
        raise ValueError(method)

    def navigate(self, url):
        elapsed, result, _ = self.call('navigate', {'url': url})
        assert result['url'] == url, result
        return elapsed

    def close(self):
        try:
            self.invoke('close')
        finally:
            self.temp.cleanup()


def process_table():
    table = {}
    for proc in Path('/proc').glob('[0-9]*'):
        try:
            fields = (proc / 'stat').read_text().rsplit(')', 1)[1].split()
            table[int(proc.name)] = {'state': fields[0], 'parent': int(fields[1]), 'start': fields[19]}
        except (OSError, ValueError, IndexError):
            continue
    return table


def owned_processes(before):
    # Subreaping captures detached daemons and orphaned Chrome crashpad helpers.
    table = process_table()
    owned = {pid for pid, row in table.items() if row['parent'] == os.getpid() and pid not in before}
    while True:
        more = {pid for pid, row in table.items() if row['parent'] in owned} - owned
        if not more:
            return {pid: table[pid] for pid in owned}
        owned.update(more)


def background_work(exclude=()):
    rows = []
    for path in Path('/proc').glob('[0-9]*/comm'):
        pid = int(path.parent.name)
        if pid in exclude:
            continue
        try:
            name = path.read_text().strip()
            if name in ('cargo', 'rustc', 'bruster') or name.startswith(('smoke-', 'edge-', 'e2e-')):
                rows.append({'pid': pid, 'name': name})
        except OSError:
            pass
    return rows


def memory_forest(before, include_display):
    owned = owned_processes(before)
    rows = [audit.memory(pid) for pid, state in owned.items() if state['state'] != 'Z']
    complete = bool(rows) and all(r['pss_kib'] is not None and r['rss_kib'] is not None for r in rows)
    display = audit.display_memory() if include_display else []
    assert not include_display or len(display) == 1, display
    display_complete = all(r['pss_kib'] is not None and r['rss_kib'] is not None for r in display)
    return {
        'processes': rows, 'display': display, 'complete': complete and display_complete,
        'process_count': len(rows),
        'rss_mib': sum(r['rss_kib'] for r in rows) / 1024 if complete else None,
        'pss_mib': sum(r['pss_kib'] for r in rows) / 1024 if complete else None,
        'display_pss_mib': sum(r['pss_kib'] for r in display) / 1024 if display_complete else None,
        'total_pss_mib': sum(r['pss_kib'] for r in rows + display) / 1024 if complete and display_complete else None,
    }


def cleanup(owned):
    deadline = time.monotonic() + 2
    while True:
        current = process_table()
        live = {pid: original for pid, original in owned.items()
                if pid in current and current[pid]['start'] == original['start'] and current[pid]['state'] != 'Z'}
        if not live or time.monotonic() >= deadline:
            break
        time.sleep(0.05)
    forced = [audit.memory(pid) for pid in live]
    for pid in live:
        try:
            os.kill(pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    for pid in owned:
        try:
            os.waitpid(pid, 0)
        except ChildProcessError:
            pass
    return forced


def failure_checks(client, base):
    checks = []
    for name, method, params in [
        ('javascript_exception', 'eval', {'expression': '(() => { throw new Error("expected-comparison-error"); })()'}),
        ('javascript_syntax_error', 'eval', {'expression': 'const = ;'}),
    ]:
        start = time.perf_counter_ns()
        try:
            client.call(method, params)
            checks.append({'name': name, 'pass': False, 'error': 'unexpected success'})
        except RuntimeError as exc:
            checks.append({'name': name, 'pass': True, 'error': str(exc),
                           'ms': (time.perf_counter_ns() - start) / 1e6})
    try:
        _, result, _ = client.call('eval', {'expression': '21 * 2'})
        checks.append({'name': 'recovery_after_javascript_errors', 'pass': result == 42})
    except RuntimeError as exc:
        checks.append({'name': 'recovery_after_javascript_errors', 'pass': False, 'error': str(exc)})
    with socket.socket() as refused:
        refused.bind(('127.0.0.1', 0))
        url = f'http://127.0.0.1:{refused.getsockname()[1]}/'
        start = time.perf_counter_ns()
        try:
            client.navigate(url)
            checks.append({'name': 'connection_refused', 'pass': False, 'error': 'unexpected success'})
        except RuntimeError as exc:
            checks.append({'name': 'connection_refused', 'pass': True, 'error': str(exc),
                           'ms': (time.perf_counter_ns() - start) / 1e6})
    try:
        client.navigate(f'{base}/tiny?recovery=1')
        _, result, _ = client.call('eval', {'expression': 'document.title'})
        checks.append({'name': 'recovery_after_navigation_error', 'pass': result == 'bench'})
    except RuntimeError as exc:
        checks.append({'name': 'recovery_after_navigation_error', 'pass': False, 'error': str(exc)})
        # Preserve the initial failure; check whether a bounded delayed retry recovers.
        time.sleep(0.1)
        try:
            client.navigate(f'{base}/tiny?recovery=retry')
            _, result, _ = client.call('eval', {'expression': 'document.title'})
            checks.append({'name': 'navigation_recovery_retry_100ms', 'pass': result == 'bench'})
        except RuntimeError as exc:
            checks.append({'name': 'navigation_recovery_retry_100ms', 'pass': False, 'error': str(exc)})
    return checks


def native_snapshot(client, tool, expected):
    elapsed, result, wire = client.call('snapshot', {'max': 2500})
    if tool == 'bruster':
        assert len(result['elements']) == expected and not result.get('truncated', False)
        controls = sum(e.get('role') in ('link', 'textbox') for e in result['elements'])
    elif tool == 'agent-browser':
        assert result['snapshot']
        controls = sum(v.get('role') in ('link', 'textbox') for v in result['refs'].values())
    elif tool.startswith('playwright'):
        assert isinstance(result, str) and result
        controls = sum(line.lstrip().startswith(('- link ', '- textbox ')) for line in result.splitlines())
    else:
        def count(node):
            return int(node.get('role') in ('link', 'textbox')) + sum(count(c) for c in node.get('children', []))
        controls = count(result)
    if expected == 2000:
        assert controls == 2000, (tool, controls)
    return {'ms': elapsed, 'wire_bytes': wire, 'controls': controls, 'result': result}


def validate_extract(result, expected, title):
    assert result['title'] == title and len(result['elements']) == expected, (result.get('title'), len(result.get('elements', [])))
    if expected == 2000:
        assert sum(e['tag'] == 'a' for e in result['elements']) == 1000
        assert sum(e['tag'] == 'input' for e in result['elements']) == 1000
        assert result['elements'][0]['name'] == 'link 0'
        assert result['elements'][-1]['name'] == 'input 999'


def measure(args, server, tool, round_):
    before = set(process_table())
    competing_before = background_work()
    if tool == 'bruster':
        client = ProcessClient([str(args.bruster), '--hidden'], False)
    elif tool == 'agent-browser':
        client = AgentClient(args.deps / 'node_modules/agent-browser/bin/agent-browser-linux-x64', args.chrome, round_)
    else:
        client = ProcessClient([str(args.node), str(Path(__file__).with_name('bench_competitor_driver.mjs')),
                                tool, str(args.shell if tool == 'playwright-shell' else args.chrome), str(args.deps)], True)
    base = f'http://127.0.0.1:{server.server_port}'
    row = {'tool': tool, 'round': round_, 'startup_ms': client.startup_ms,
           'load_before': os.getloadavg(), 'failures': [], 'competing_before': competing_before}
    try:
        row['first_navigation_ms'] = client.navigate(f'{base}/tiny?first={tool}-{round_}')
        row['launch_to_first_page_ms'] = (time.perf_counter_ns() - client.started_ns) / 1e6
        _, info, _ = client.call('eval', {'expression': '({width:innerWidth,height:innerHeight,state:document.readyState,userAgent:navigator.userAgent})'})
        assert info['width'] == 1280 and info['height'] == 800 and info['state'] == 'complete', info
        row['browser_info'] = info
        if round_ == 1:
            row['delayed_validation_ms'] = client.navigate(f'{base}/delayed')
            assert row['delayed_validation_ms'] >= 240, row['delayed_validation_ms']
        row['tiny_navigation_ms'], row['tiny_extract_ms'] = [], []
        for i in range(args.iterations):
            row['tiny_navigation_ms'].append(client.navigate(f'{base}/tiny?tool={tool}&round={round_}&i={i}'))
            elapsed, obj, wire = client.call('eval', {'expression': EXTRACT})
            validate_extract(obj, 5, 'bench')
            row['tiny_extract_ms'].append(elapsed)
        time.sleep(2)
        row['idle_memory'] = []
        row['competing_at_memory'] = background_work(owned_processes(before))
        for _ in range(3):
            sample = memory_forest(before, tool == 'bruster')
            assert sample['complete'], sample
            row['idle_memory'].append(sample)
            time.sleep(0.1)
        row['native_tiny_snapshot'] = native_snapshot(client, tool, 5)
        row['large_navigation_ms'], row['large_extract_ms'], row['large_extract_json_ms'] = [], [], []
        for i in range(5):
            row['large_navigation_ms'].append(client.navigate(f'{base}/large?tool={tool}&round={round_}&i={i}'))
            formats = [('large_extract_ms', EXTRACT), ('large_extract_json_ms', f'JSON.stringify({EXTRACT})')]
            if (round_ + i) % 2:
                formats.reverse()
            extracted = []
            for key, expression in formats:
                elapsed, obj, wire = client.call('eval', {'expression': expression})
                if key == 'large_extract_json_ms':
                    obj = json.loads(obj)
                validate_extract(obj, 2000, 'large')
                row[key].append(elapsed)
                extracted.append(obj)
            assert extracted[0] == extracted[1]
            row['large_extract_sha256'] = hashlib.sha256(json.dumps(extracted[0], sort_keys=True).encode()).hexdigest()
        row['native_large_snapshot'] = native_snapshot(client, tool, 2000)
        row['image_navigation_ms'] = []
        image_hits = server.image_hits
        for i in range(3):
            row['image_navigation_ms'].append(client.navigate(f'{base}/images?tool={tool}&round={round_}&i={i}'))
        row['image_requests'] = server.image_hits - image_hits
        assert row['image_requests'] == 36, row['image_requests']
        _, dimensions, _ = client.call('eval', {'expression': 'Array.from(document.images, i => i.naturalWidth)'})
        assert dimensions == [128] * 12, dimensions
        row['screenshot_ms'] = []
        for i in range(2):
            path = args.output / 'screenshots' / f'{tool}-{round_}-{i}.png'
            elapsed, result, _ = client.call('screenshot', {'path': str(path)})
            data = path.read_bytes()
            assert data[:8] == b'\x89PNG\r\n\x1a\n' and struct.unpack('>II', data[16:24]) == (1280, 800)
            assert len(data) > 1000
            row['screenshot_ms'].append(elapsed)
        row['load_after'] = os.getloadavg()
        row['competing_after'] = background_work(owned_processes(before))
        row['failure_checks'] = failure_checks(client, base)
        row['failures'].extend(c for c in row['failure_checks'] if not c['pass'])
    finally:
        owned = owned_processes(before)
        try:
            client.close()
        finally:
            if getattr(client, 'close_error', None) is not None:
                row['failures'].append({'name': 'graceful_close', 'pass': False, 'error': client.close_error})
            row['cleanup_forced_processes'] = cleanup(owned)
            if row['cleanup_forced_processes']:
                row['failures'].append({'name': 'process_cleanup', 'pass': False,
                                        'remaining_pids': [p['pid'] for p in row['cleanup_forced_processes']]})
        row['stderr'] = client.stderr
    return row


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    for flag in ('bruster', 'node', 'chrome', 'shell', 'deps', 'output'):
        ap.add_argument('--' + flag, type=Path, required=True)
    ap.add_argument('--rounds', type=int, default=10)
    ap.add_argument('--iterations', type=int, default=10)
    ap.add_argument('--tools', nargs='+', choices=TOOLS, default=TOOLS)
    args = ap.parse_args()
    if args.rounds < 1 or args.iterations < 1 or len(set(args.tools)) != len(args.tools):
        ap.error('rounds/iterations must be positive and tools must be unique')
    for flag in ('bruster', 'node', 'chrome', 'shell', 'deps'):
        setattr(args, flag, getattr(args, flag).resolve(strict=True))
    args.output = args.output.resolve()
    (args.output / 'screenshots').mkdir(parents=True, exist_ok=True)
    if ctypes.CDLL(None, use_errno=True).prctl(36, 1, 0, 0, 0) != 0:
        raise OSError(ctypes.get_errno(), 'PR_SET_CHILD_SUBREAPER failed')
    metadata = {
        'started_utc': datetime.now(timezone.utc).isoformat(), 'platform': platform.platform(),
        'os': platform.freedesktop_os_release(), 'node': subprocess.check_output([str(args.node), '--version'], text=True).strip(),
        'chrome': subprocess.check_output([str(args.chrome), '--version'], text=True).strip(),
        'headless_shell': subprocess.check_output([str(args.shell), '--version'], text=True).strip(),
        'cpu_count': os.cpu_count(),
        'cpu_model': next((line.split(':', 1)[1].strip() for line in Path('/proc/cpuinfo').read_text().splitlines()
                           if line.startswith('model name')), platform.machine()),
        'mem_total_kib': int(next(line.split()[1] for line in Path('/proc/meminfo').read_text().splitlines()
                                  if line.startswith('MemTotal:'))),
        'runner_image': {key: os.environ.get(key) for key in ('ImageOS', 'ImageVersion', 'RUNNER_ARCH')},
        'rustc': subprocess.check_output(['rustc', '--version'], text=True).strip(),
        'webkitgtk': subprocess.check_output(['pkg-config', '--modversion', 'webkit2gtk-4.1'], text=True).strip(),
        'packages': {name: json.loads((args.deps / 'node_modules' / name / 'package.json').read_text())['version']
                     for name in ('playwright-core', 'puppeteer-core', 'agent-browser')},
        'bruster_bytes': args.bruster.stat().st_size,
        'bruster_sha256': hashlib.sha256(args.bruster.read_bytes()).hexdigest(),
        'chrome_sha256': hashlib.sha256(args.chrome.read_bytes()).hexdigest(),
        'headless_shell_sha256': hashlib.sha256(args.shell.read_bytes()).hexdigest(),
        'rounds': args.rounds, 'iterations': args.iterations, 'common_extraction_js': EXTRACT,
        'harness_sha256': {name: hashlib.sha256(Path(__file__).with_name(name).read_bytes()).hexdigest()
                           for name in ('bench_compare.py', 'bench_competitor_driver.mjs', 'bench_audit.py')},
        'package_lock_sha256': hashlib.sha256((args.deps / 'package-lock.json').read_bytes()).hexdigest(),
        'args': {k: str(v) if isinstance(v, Path) else v for k, v in vars(args).items()},
    }
    (args.output / 'metadata.json').write_text(json.dumps(metadata, indent=2) + '\n')
    server = audit.ThreadingHTTPServer(('127.0.0.1', 0), audit.Fixtures)
    server.image_hits, server.hits_lock = 0, threading.Lock()
    threading.Thread(target=server.serve_forever, daemon=True).start()
    rows = []
    try:
        for round_ in range(1, args.rounds + 1):
            shift = (round_ - 1) % len(args.tools)
            for tool in args.tools[shift:] + args.tools[:shift]:
                try:
                    row = measure(args, server, tool, round_)
                except Exception:
                    (args.output / 'error.json').write_text(json.dumps({
                        'tool': tool, 'round': round_, 'traceback': traceback.format_exc(),
                    }, indent=2) + '\n')
                    raise
                for name in ('native_tiny_snapshot', 'native_large_snapshot'):
                    native = row[name].pop('result')
                    (args.output / f'{tool}-{round_}-{name}.json').write_text(json.dumps(native, indent=2) + '\n')
                rows.append(row)
                (args.output / 'samples.json').write_text(json.dumps(rows, indent=2) + '\n')
                print(f"{round_}: {tool} first-page={row['launch_to_first_page_ms']:.1f}ms "
                      f"warm={statistics.median(row['tiny_navigation_ms']):.2f}ms "
                      f"PSS={statistics.median(m['total_pss_mib'] for m in row['idle_memory']):.1f}MiB", flush=True)
    finally:
        server.shutdown()
        server.server_close()
    stats = {}
    for tool in args.tools:
        subset = [r for r in rows if r['tool'] == tool]
        result = {}
        for key in ('startup_ms', 'first_navigation_ms', 'launch_to_first_page_ms'):
            result[key] = audit.summary([r[key] for r in subset])
        for key in ('tiny_navigation_ms', 'tiny_extract_ms', 'large_navigation_ms', 'large_extract_ms', 'large_extract_json_ms', 'image_navigation_ms', 'screenshot_ms'):
            result[key] = audit.summary([v for r in subset for v in r[key]])
        for key in ('rss_mib', 'pss_mib', 'display_pss_mib', 'total_pss_mib', 'process_count'):
            result[key] = audit.summary([statistics.median(m[key] for m in r['idle_memory']) for r in subset])
        for page in ('tiny', 'large'):
            for key in ('ms', 'wire_bytes', 'controls'):
                result[f'native_{page}_snapshot_{key}'] = audit.summary([r[f'native_{page}_snapshot'][key] for r in subset])
        result['sessions_with_failures'] = sum(bool(r['failures']) for r in subset)
        result['failures'] = [{'round': r['round'], **failure} for r in subset for failure in r['failures']]
        stats[tool] = result
    metadata['finished_utc'] = datetime.now(timezone.utc).isoformat()
    report = {'metadata': metadata, 'summary': stats}
    (args.output / 'summary.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
