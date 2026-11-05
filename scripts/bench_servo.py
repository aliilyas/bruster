#!/usr/bin/env python3
"""Benchmark standalone servoshell using its built-in WebDriver HTTP API.

Uses only Python's standard library and the existing localhost fixtures. Results
are exploratory local measurements, not part of the published tool comparison.
"""
import argparse
import base64
import hashlib
import json
import os
import platform
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
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, build_opener, ProxyHandler

import bench_audit as audit
from bench_compare import EXTRACT
from bench_footprint import files, inventory, libraries


INTERACTIVE = b"""<!doctype html><title>Servo interaction check</title>
<style>body{font:20px sans-serif;background:#edf6fc;padding:32px}
button,input{font:inherit;padding:12px}#result{color:#064b31}</style>
<h1>Servo standalone browser</h1><input id="name" aria-label="Name">
<button id="go" onclick="document.querySelector('#result').textContent =
  'Hello ' + document.querySelector('#name').value">Greet</button>
<p id="result">Ready</p>"""

COMPUTE = """const started = performance.now();
let result = 0;
for (let i = 0; i < 5000000; i++) result = (result + i) | 0;
return {ms: performance.now() - started, result};"""

DOM_WORK = """const started = performance.now();
const root = document.createElement('div');
root.style.cssText = 'display:grid;grid-template-columns:repeat(10,1fr);gap:2px';
for (let i = 0; i < 500; i++) {
  const child = document.createElement('div');
  child.textContent = 'Item ' + i;
  root.appendChild(child);
}
document.body.appendChild(root);
let checksum = 0;
for (let i = 0; i < 20; i++) {
  root.style.width = (800 + i) + 'px';
  checksum += root.getBoundingClientRect().width;
}
const count = root.children.length;
root.remove();
return {ms: performance.now() - started, count, checksum};"""


class Fixtures(audit.Fixtures):
    def do_GET(self):
        path = urlsplit(self.path).path
        if path not in ('/interactive', '/data.json', '/load-gate', '/slow.png'):
            return super().do_GET()
        kind = 'text/html; charset=utf-8'
        if path == '/interactive':
            body = INTERACTIVE
        elif path == '/data.json':
            kind, body = 'application/json', b'{"answer":42}'
        elif path == '/load-gate':
            body = b'<title>load gate</title><img src="/slow.png">'
        else:
            time.sleep(0.250)
            kind, body = 'image/png', audit.PNG
        self.send_response(200)
        self.send_header('Content-Type', kind)
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        try:
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            pass


class FixtureServer(audit.ThreadingHTTPServer):
    # Servo can open all twelve image connections simultaneously. Avoid measuring
    # TCP backlog retries caused by the stdlib server's small default queue.
    request_queue_size = 128


class Servo:
    def __init__(self, executable, mode, output, timeout, width, height):
        self.timeout, self.width, self.height = timeout, width, height
        self.session = None
        self.shutdown = None
        self.opener = build_opener(ProxyHandler({}))
        self.profile = tempfile.TemporaryDirectory(prefix='servo-bench-', dir='/tmp/opencode')
        self.log = output.open('w')
        with socket.socket() as sock:
            sock.bind(('127.0.0.1', 0))
            port = sock.getsockname()[1]
        self.url = f'http://127.0.0.1:{port}'
        env = os.environ.copy()
        for key in ('XDG_CACHE_HOME', 'XDG_CONFIG_HOME', 'XDG_DATA_HOME', 'XDG_STATE_HOME'):
            env[key] = str(Path(self.profile.name) / key.lower())
        if mode == 'headless':
            env.pop('DISPLAY', None)
            env.pop('WAYLAND_DISPLAY', None)
        self.command = [str(executable), f'--webdriver={port}',
                        f'--config-dir={self.profile.name}/config',
                        f'--window-size={width}x{height}', '--device-pixel-ratio=1']
        if mode == 'headless':
            self.command.append('--headless')
        self.command.append('about:blank')
        start = time.perf_counter_ns()
        self.proc = subprocess.Popen(self.command, env=env, stdout=self.log,
                                     stderr=self.log, start_new_session=True)
        try:
            deadline = time.monotonic() + timeout
            while time.monotonic() < deadline:
                if self.proc.poll() is not None:
                    raise RuntimeError(f'Servo exited with {self.proc.returncode}; see {output}')
                try:
                    self.request('GET', '/status', timeout=1)
                    break
                except (URLError, TimeoutError):
                    time.sleep(0.01)
            else:
                raise TimeoutError('WebDriver startup timed out')
            self.listener_ms = (time.perf_counter_ns() - start) / 1e6
            session = self.request('POST', '/session', {
                'capabilities': {'alwaysMatch': {'pageLoadStrategy': 'normal',
                    'timeouts': {'pageLoad': timeout * 1000, 'script': timeout * 1000}}}})
            self.session = session['sessionId']
            self.capabilities = session['capabilities']
            assert self.evaluate('return 6 * 7;') == 42
            self.startup_ms = (time.perf_counter_ns() - start) / 1e6
            self.viewport = self.evaluate('return {width:innerWidth,height:innerHeight,dpr:devicePixelRatio};')
            # Headed window dimensions include the toolbar and WM decorations.
            requested = self.command_request('GET', '/window/rect')
            self.viewport_adjustments = []
            for _ in range(5):
                if (self.viewport['width'], self.viewport['height']) == (width, height):
                    break
                requested = {'width': requested['width'] + width - self.viewport['width'],
                             'height': requested['height'] + height - self.viewport['height']}
                self.command_request('POST', '/window/rect', requested)
                time.sleep(0.15)
                self.viewport = self.evaluate('return {width:innerWidth,height:innerHeight,dpr:devicePixelRatio};')
                self.viewport_adjustments.append({'requested': requested, 'actual': self.viewport})
            assert self.viewport == {'width': width, 'height': height, 'dpr': 1}, {
                'viewport': self.viewport, 'adjustments': self.viewport_adjustments}
            self.setup_ms = (time.perf_counter_ns() - start) / 1e6
        except BaseException:
            self.close()
            raise

    def request(self, method, path, data=None, timeout=None):
        raw = None if data is None else json.dumps(data).encode()
        request = Request(self.url + path, data=raw, method=method,
                          headers={'Content-Type': 'application/json'})
        try:
            with self.opener.open(request, timeout=timeout or self.timeout) as reply:
                obj = json.load(reply)
        except HTTPError as error:
            raise RuntimeError(f'{method} {path}: {error.code} {error.read().decode()}') from error
        value = obj['value']
        if isinstance(value, dict) and 'error' in value:
            raise RuntimeError(str(value))
        return value

    def command_request(self, method, path, data=None):
        return self.request(method, f'/session/{self.session}' + path, data)

    def evaluate(self, script):
        return self.command_request('POST', '/execute/sync', {'script': script, 'args': []})

    def navigate(self, url):
        start = time.perf_counter_ns()
        self.command_request('POST', '/url', {'url': url})
        elapsed = (time.perf_counter_ns() - start) / 1e6
        state = self.evaluate('return {url:location.href,state:document.readyState,title:document.title};')
        assert state['url'] == url and state['state'] == 'complete', state
        return elapsed, state

    def screenshot(self, path):
        start = time.perf_counter_ns()
        image = base64.b64decode(self.command_request('GET', '/screenshot'), validate=True)
        path.write_bytes(image)
        elapsed = (time.perf_counter_ns() - start) / 1e6
        assert image.startswith(b'\x89PNG\r\n\x1a\n')
        dimensions = struct.unpack('>II', image[16:24])
        assert dimensions == (self.width, self.height), dimensions
        return {'ms': elapsed, 'bytes': len(image), 'dimensions': dimensions, 'file': str(path)}

    def close(self):
        try:
            if self.proc.poll() is None and self.session:
                self.request('DELETE', f'/session/{self.session}/servo/shutdown', timeout=5)
                self.proc.wait(timeout=10)
                self.shutdown = {'graceful': True, 'exit_code': self.proc.returncode}
        except (OSError, RuntimeError, subprocess.TimeoutExpired) as exc:
            self.shutdown = {'graceful': False, 'error': str(exc)}
        finally:
            if self.proc.poll() is None:
                os.killpg(self.proc.pid, signal.SIGKILL)
                self.proc.wait(timeout=10)
                self.shutdown = self.shutdown or {'graceful': False, 'forced': True}
            self.log.close()
            self.profile.cleanup()


def functionality(browser, base):
    browser.navigate(base + '/interactive')
    element_key = 'element-6066-11e4-a52e-4f735466cecf'
    def element(selector):
        return browser.command_request('POST', '/element', {
            'using': 'css selector', 'value': selector})[element_key]
    name, go = element('#name'), element('#go')
    browser.command_request('POST', f'/element/{name}/value', {'text': 'Servo'})
    browser.command_request('POST', f'/element/{go}/click', {})
    greeting = browser.evaluate("return document.querySelector('#result').textContent;")
    assert greeting == 'Hello Servo', greeting
    asynchronous = browser.command_request('POST', '/execute/async', {
        'script': "const done=arguments[arguments.length-1]; fetch('/data.json').then(r=>r.json()).then(done);",
        'args': []})
    assert asynchronous == {'answer': 42}, asynchronous
    storage = browser.evaluate("localStorage.setItem('servo-benchmark','works'); return localStorage.getItem('servo-benchmark');")
    assert storage == 'works', storage
    browser.command_request('POST', '/cookie', {'cookie': {'name': 'servo_bench', 'value': '42'}})
    assert any(c['name'] == 'servo_bench' and c['value'] == '42'
               for c in browser.command_request('GET', '/cookie'))
    source = browser.command_request('GET', '/source')
    assert 'Hello Servo' in source, source
    original = browser.command_request('GET', '/window')
    tab = browser.command_request('POST', '/window/new', {'type': 'tab'})
    browser.command_request('POST', '/window', {'handle': tab['handle']})
    browser.navigate(base + '/tiny?new-tab')
    browser.command_request('DELETE', '/window')
    browser.command_request('POST', '/window', {'handle': original})
    assert browser.evaluate('return document.title;') == 'Servo interaction check'
    return {'selectors': True, 'keyboard': True, 'click': True, 'javascript': True,
            'async_fetch': True, 'local_storage': True, 'cookies': True,
            'page_source': True, 'tabs': True}


def measure(args, server, mode, round_):
    base = f'http://127.0.0.1:{server.server_port}'
    row = {'mode': mode, 'round': round_, 'load_before': os.getloadavg()}
    browser = Servo(args.servo, mode, args.output / f'{mode}-{round_}.log',
                    args.timeout, args.width, args.height)
    try:
        row.update(command=browser.command, viewport=browser.viewport,
                   viewport_adjustments=browser.viewport_adjustments,
                   capabilities=browser.capabilities, listener_ms=browser.listener_ms,
                   startup_ms=browser.startup_ms, setup_ms=browser.setup_ms)
        row['first_navigation_ms'], _ = browser.navigate(base + '/tiny?first')
        row['launch_to_first_page_ms'] = browser.setup_ms + row['first_navigation_ms']
        time.sleep(1)
        row['idle_memory'] = []
        for _ in range(3):
            sample = audit.memory_tree(browser.proc.pid)
            assert sample['complete'], sample
            row['idle_memory'].append(sample)
            time.sleep(0.1)
        if round_ == 1:
            row['delayed_load_ms'], _ = browser.navigate(base + '/load-gate')
            assert row['delayed_load_ms'] >= 240, row['delayed_load_ms']
            assert browser.evaluate('return document.images[0].naturalWidth;') == 128
            row['functionality'] = functionality(browser, base)
            row['interaction_screenshot'] = browser.screenshot(args.output / f'{mode}-interactive.png')
        row['tiny_load_ms'], row['large_load_ms'], row['images_load_ms'] = [], [], []
        row['extract_ms'], row['js_compute_ms'], row['dom_layout_ms'] = [], [], []
        browser.navigate(base + '/tiny?warmup')
        browser.evaluate(COMPUTE)
        browser.evaluate(DOM_WORK)
        for i in range(args.iterations):
            elapsed, state = browser.navigate(f'{base}/tiny?round={round_}&i={i}')
            assert state['title'] == 'bench', state
            row['tiny_load_ms'].append(elapsed)
            result = browser.evaluate(COMPUTE)
            assert result['result'] == 1642668640, result
            row['js_compute_ms'].append(result['ms'])
            result = browser.evaluate(DOM_WORK)
            assert result['count'] == 500 and result['checksum'] == 16190, result
            row['dom_layout_ms'].append(result['ms'])
        for i in range(args.iterations):
            elapsed, _ = browser.navigate(f'{base}/large?round={round_}&i={i}')
            row['large_load_ms'].append(elapsed)
            start = time.perf_counter_ns()
            result = browser.evaluate('return ' + EXTRACT + ';')
            row['extract_ms'].append((time.perf_counter_ns() - start) / 1e6)
            expected = []
            for n in range(1000):
                expected.extend([{'tag':'a','name':f'link {n}','href':f'/item/{n}','value':None},
                                 {'tag':'input','name':f'input {n}','href':None,'value':''}])
            assert result == {'title': 'large', 'elements': expected}, 'DOM extraction content mismatch'
        row['large_memory'] = audit.memory_tree(browser.proc.pid)
        before = server.image_hits
        for i in range(args.iterations):
            elapsed, _ = browser.navigate(f'{base}/images?round={round_}&i={i}')
            row['images_load_ms'].append(elapsed)
            assert browser.evaluate('return Array.from(document.images,i=>i.naturalWidth);') == [128] * 12
        row['image_requests'] = server.image_hits - before
        assert row['image_requests'] == 12 * args.iterations, row['image_requests']
        row['screenshot'] = browser.screenshot(args.output / f'{mode}-{round_}-images.png')
        row['load_after'] = os.getloadavg()
    except BaseException:
        row['error'] = traceback.format_exc()
        raise
    finally:
        browser.close()
        row['shutdown'] = browser.shutdown
        (args.output / f'{mode}-{round_}.json').write_text(json.dumps(row, indent=2) + '\n')
    assert row['shutdown']['graceful'], row['shutdown']
    return row


def summarize(records):
    result = {}
    for mode in sorted({row['mode'] for row in records}):
        rows = [row for row in records if row['mode'] == mode]
        metrics = {}
        for key in ('startup_ms', 'setup_ms', 'first_navigation_ms', 'launch_to_first_page_ms',
                    'tiny_load_ms', 'large_load_ms', 'images_load_ms', 'extract_ms',
                    'js_compute_ms', 'dom_layout_ms'):
            values = []
            for row in rows:
                value = row[key]
                values.extend(value if isinstance(value, list) else [value])
            metrics[key] = audit.summary(values)
        for key in ('tree_pss_mib', 'tree_rss_mib'):
            metrics['idle_' + key] = audit.summary([
                statistics.median(sample[key] for sample in row['idle_memory']) for row in rows])
        metrics['screenshot_ms'] = audit.summary([row['screenshot']['ms'] for row in rows])
        result[mode] = metrics
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--servo', type=Path, default=Path.home() / '.local/bin/servo')
    parser.add_argument('--bundle', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--modes', nargs='+', choices=('headless', 'headed'), default=['headless', 'headed'])
    parser.add_argument('--rounds', type=int, default=5)
    parser.add_argument('--iterations', type=int, default=5)
    parser.add_argument('--timeout', type=int, default=30)
    # This X11/egui build rounds even viewport widths to the adjacent odd pixel.
    # Use the same attainable, verified viewport in both rendering modes.
    parser.add_argument('--width', type=int, default=1023)
    parser.add_argument('--height', type=int, default=640)
    args = parser.parse_args()
    if min(args.rounds, args.iterations, args.timeout, args.width, args.height) <= 0:
        parser.error('rounds, iterations, timeout and dimensions must be positive')
    args.servo, args.bundle = args.servo.resolve(strict=True), args.bundle.resolve(strict=True)
    args.output.mkdir(parents=True, exist_ok=False)
    binary = args.bundle / 'servoshell'
    version = subprocess.check_output([str(args.servo), '--version'], text=True).strip()
    context = {'utc': datetime.now(timezone.utc).isoformat(), 'version': version,
               'binary_sha256': hashlib.file_digest(binary.open('rb'), 'sha256').hexdigest(),
               'harness_sha256': hashlib.file_digest(Path(__file__).open('rb'), 'sha256').hexdigest(),
               'system': platform.platform(), 'cpu': platform.processor(), 'cores': os.cpu_count(),
               'cpuinfo': Path('/proc/cpuinfo').read_text(), 'meminfo_before': Path('/proc/meminfo').read_text(),
               'display': os.environ.get('DISPLAY'), 'rounds': args.rounds, 'iterations': args.iterations,
               'viewport': [args.width, args.height],
               'method': 'Fresh config/cache per process; normal WebDriver page-load strategy; localhost no-store fixtures. '
                         'Headless unsets DISPLAY and WAYLAND_DISPLAY. OS file caches are not flushed. '
                         'Startup ends after NewSession and successful JS evaluation; setup additionally sizes viewport. '
                         'Memory is browser process-tree PSS/RSS, excludes shared desktop X server and Python controller. '
                         'JS/layout microbenchmarks use performance.now; other times use host monotonic clock. '
                         'Existing desktop applications remain running; exploratory VM results, not CI comparison data.'}
    (args.output / 'context.json').write_text(json.dumps(context, indent=2) + '\n')
    server = FixtureServer(('127.0.0.1', 0), Fixtures)
    server.image_hits, server.hits_lock = 0, threading.Lock()
    threading.Thread(target=server.serve_forever, daemon=True).start()
    records, failures = [], []
    try:
        for round_ in range(1, args.rounds + 1):
            modes = args.modes if round_ % 2 else list(reversed(args.modes))
            for mode in modes:
                try:
                    row = measure(args, server, mode, round_)
                    records.append(row)
                    print(f'{mode} round {round_}: startup={row["startup_ms"]:.1f}ms '
                          f'tiny={statistics.median(row["tiny_load_ms"]):.1f}ms '
                          f'PSS={statistics.median(s["tree_pss_mib"] for s in row["idle_memory"]):.1f}MiB', flush=True)
                except Exception:
                    failures.append({'mode': mode, 'round': round_, 'error': traceback.format_exc()})
                    print(f'{mode} round {round_} FAILED: {failures[-1]["error"]}', flush=True)
                    # A broken rendering mode needs diagnosis, not repeated failing runs.
                    raise
                finally:
                    (args.output / 'samples.json').write_text(json.dumps(records, indent=2) + '\n')
                    (args.output / 'failures.json').write_text(json.dumps(failures, indent=2) + '\n')
    finally:
        server.shutdown()
        server.server_close()
        summary = summarize(records)
        (args.output / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
        (args.output / 'meminfo-after.txt').write_text(Path('/proc/meminfo').read_text())
        # Resolve dlopened files from measurements as well as linked ELF libraries.
        bundle_files = files(args.bundle)
        observed = {Path(path) for row in records for sample in row['idle_memory']
                    for proc in sample['processes'] for path in proc.get('mapped_files', [])
                    if Path(path).is_file()}
        old = os.environ.get('LD_LIBRARY_PATH')
        os.environ['LD_LIBRARY_PATH'] = str(args.bundle / 'deps/usr/lib/x86_64-linux-gnu') + (':' + old if old else '')
        runtime_files = bundle_files | libraries({binary}) | observed
        footprint = {'bundle': inventory(bundle_files), 'runtime_lower_bound': inventory(runtime_files)}
        footprint['bundle_bytes'] = sum(x['bytes'] for x in footprint['bundle'])
        footprint['runtime_lower_bound_bytes'] = sum(x['bytes'] for x in footprint['runtime_lower_bound'])
        (args.output / 'footprint.json').write_text(json.dumps(footprint, indent=2) + '\n')
        report = ['# Standalone Servo benchmark', '', version, '', context['method'], '',
                  f'Viewport: {args.width}×{args.height}; {args.rounds} fresh sessions/mode; '
                  f'{args.iterations} iterations/session.', '',
                  '| Metric | ' + ' | '.join(summary) + ' |',
                  '|---|' + '---:|' * len(summary)]
        if summary:
            for metric in next(iter(summary.values())):
                cells = []
                for metrics in summary.values():
                    value = metrics[metric]
                    cells.append(f'{value["median"]:.2f} ({value["min"]:.2f}–{value["max"]:.2f}; n={value["n"]})')
                report.append('| ' + metric + ' | ' + ' | '.join(cells) + ' |')
        report.extend(['', 'Values: median (observed min–max; sample count).', '',
                       f'Installed bundle incl. private dependency: {footprint["bundle_bytes"]/1e6:.2f} MB.',
                       f'Runtime file lower bound incl. mapped OS libraries/fonts: '
                       f'{footprint["runtime_lower_bound_bytes"]/1e6:.2f} MB.', '',
                       f'Completed sessions: {len(records)}. Failures: {len(failures)}.', ''])
        (args.output / 'report.md').write_text('\n'.join(report))


if __name__ == '__main__':
    main()
