#!/usr/bin/env python3
"""Create launch media from real MCP calls or an archived benchmark run.

Requires Pillow; MP4 export additionally needs ffmpeg on PATH or imageio-ffmpeg.
The demo is a scripted MCP client, with screenshots held for five seconds each.
"""
import argparse
import base64
from functools import partial
import hashlib
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import queue
import shutil
import subprocess
import tempfile
import textwrap
import threading
import time

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
BG, PANEL, FG, MUTED, ACCENT = '#0d1422', '#182338', '#edf4ff', '#aebed5', '#77e7da'


def font(size, bold=False, mono=False):
    name = 'DejaVuSansMono' if mono else 'DejaVuSans'
    try:
        return ImageFont.truetype(name + ('-Bold' if bold else '') + '.ttf', size)
    except OSError:
        return ImageFont.load_default(size=size)


class MCP:
    def __init__(self, command, profile, log):
        self.log = log
        self.next_id = 0
        self.replies = queue.Queue()
        self.start = time.monotonic()
        self.process = subprocess.Popen(
            [*command, '--mcp', '--quiet', '--viewport', '840x660', '--profile', profile],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, bufsize=1,
        )
        threading.Thread(target=self.read, daemon=True).start()

    def read(self):
        for line in self.process.stdout:
            try:
                self.replies.put(json.loads(line))
            except json.JSONDecodeError:
                self.replies.put({'error': f'Non-JSON stdout: {line.strip()}'})
        self.replies.put({'error': 'Bruster exited before replying'})

    def send(self, message):
        self.process.stdin.write(json.dumps(message) + '\n')
        self.process.stdin.flush()

    def call(self, method, params):
        self.next_id += 1
        request = {'jsonrpc': '2.0', 'id': self.next_id, 'method': method, 'params': params}
        started = time.monotonic()
        self.send(request)
        deadline = started + 45
        while True:
            reply = self.replies.get(timeout=max(0, deadline - time.monotonic()))
            if reply.get('id') == self.next_id or ('error' in reply and 'id' not in reply):
                break
        if 'error' in reply or reply.get('result', {}).get('isError'):
            raise RuntimeError(reply)
        # Preserve the result while avoiding megabytes of embedded PNG data in the log.
        recorded = json.loads(json.dumps(reply))
        for content in recorded.get('result', {}).get('content', []):
            if content.get('type') == 'image':
                png = base64.b64decode(content.pop('data'))
                content['image_sha256'] = hashlib.sha256(png).hexdigest()
                content['image_bytes'] = len(png)
        self.log.append({'request': request, 'response': recorded,
                         'elapsed_ms': round((time.monotonic() - started) * 1000, 3)})
        return reply['result']

    def tool(self, name, **arguments):
        return self.call('tools/call', {'name': name, 'arguments': arguments})

    def stop(self):
        if self.process.poll() is None:
            self.process.stdin.close()
            try:
                self.process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.process.terminate()
                self.process.wait(timeout=10)


def text(result):
    return '\n'.join(c['text'] for c in result['content'] if c['type'] == 'text')


def screenshot(client, path):
    result = client.tool('screenshot')
    content = next(c for c in result['content'] if c['type'] == 'image')
    assert content['mimeType'] == 'image/png'
    path.write_bytes(base64.b64decode(content['data']))
    with Image.open(path) as image:
        assert image.width >= 800 and image.height >= 600, image.size


def demo_frame(page_path, number, heading, command, response, version):
    image = Image.new('RGB', (1280, 800), BG)
    draw = ImageDraw.Draw(image)
    draw.text((24, 18), 'bruster', font=font(30, bold=True), fill=ACCENT)
    draw.text((170, 27), f'Native-webview browser automation  /  v{version}', font=font(20), fill=FG)
    draw.text((24, 68), f'{number}/6  {heading}', font=font(23, bold=True), fill=FG)
    with Image.open(page_path) as page:
        page = page.convert('RGB')
        page.thumbnail((840, 620), Image.Resampling.LANCZOS)
        image.paste(page, (20, 116))
    draw.rounded_rectangle((868, 116, 1260, 740), radius=12, fill=PANEL)
    draw.text((886, 137), 'MCP  /  stdio', font=font(19, bold=True), fill=ACCENT)
    y = 180
    for line in textwrap.wrap(command, 34):
        draw.text((886, y), line, font=font(17, mono=True), fill=FG)
        y += 25
    draw.text((886, y + 20), 'Actual response', font=font(17, bold=True), fill=ACCENT)
    draw.text((24, 765), 'Scripted MCP client · actual WebKitGTK captures · 5 s per step; not a speed test', font=font(17), fill=MUTED)
    y += 58
    for source in response.splitlines():
        for line in textwrap.wrap(source, 36) or ['']:
            if y > 702:
                return image
            draw.text((886, y), line, font=font(16, mono=True), fill=MUTED)
            y += 23
    return image


def demo(args):
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=True)
    log, frames = [], []

    class QuietHandler(SimpleHTTPRequestHandler):
        def log_message(self, *_):
            pass

    server = ThreadingHTTPServer(('127.0.0.1', 0), partial(QuietHandler, directory=str(ROOT / 'examples/launch-demo')))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        with tempfile.TemporaryDirectory(prefix='bruster-demo-') as profile:
            client = MCP(args.command, profile, log)
            try:
                info = client.call('initialize', {'protocolVersion': '2024-11-05', 'capabilities': {},
                                                  'clientInfo': {'name': 'bruster-launch-demo', 'version': '1'}})
                version = info['serverInfo']['version']
                client.send({'jsonrpc': '2.0', 'method': 'notifications/initialized'})
                available = client.call('tools/list', {})
                required = {'navigate', 'snapshot', 'fill_form', 'click', 'screenshot', 'text'}
                assert required <= {tool['name'] for tool in available['tools']}

                def capture(number, heading, command, response):
                    page = out / f'page-{number:02}.png'
                    screenshot(client, page)
                    frame = demo_frame(page, number, heading, command, response, version)
                    frame.save(out / f'frame-{number:02}.png')
                    frames.append(frame)

                url = f'http://127.0.0.1:{server.server_port}/'
                result = client.tool('navigate', url=url)
                capture(1, 'Navigate to a local web app', 'navigate({url: localhost})', text(result))
                result = client.tool('snapshot')
                capture(2, 'Read the page and its controls', 'snapshot()', text(result))
                fields = [{'selector': '#name', 'value': 'Ada Lovelace'}, {'selector': '#project', 'value': 'Bruster'}]
                result = client.tool('fill_form', fields=fields)
                capture(3, 'Fill the form', 'fill_form(name="Ada Lovelace", project="Bruster")', text(result))
                fields = [{'selector': '#workflow', 'value': 'forms'}, {'selector': '#screenshots', 'value': True}]
                result = client.tool('fill_form', fields=fields)
                capture(4, 'Select a workflow and check an option', 'fill_form(workflow="forms", screenshots=true)', text(result))
                client.tool('click', selector='button[type=submit]')
                result = client.tool('text', selector='#result')
                confirmed = text(result)
                assert 'Smoke test created for Bruster' in confirmed
                assert 'Ada Lovelace' in confirmed and 'Screenshots: on' in confirmed
                capture(5, 'Submit and verify the result', 'click(button); text(#result)', confirmed)
                capture(6, 'Return a native PNG through MCP', 'screenshot()', 'MCP image content\nimage/png\n\nForm submission verified.\nNo Node.js runtime needed.')
            finally:
                client.stop()
    finally:
        server.shutdown()
        server.server_close()

    frames[0].save(out / 'demo.gif', save_all=True, append_images=frames[1:], duration=5000, loop=0, optimize=True)
    ffmpeg = shutil.which('ffmpeg')
    if not ffmpeg:
        try:
            import imageio_ffmpeg
            ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
        except ImportError:
            pass
    if ffmpeg:
        subprocess.run([ffmpeg, '-y', '-loglevel', 'error', '-framerate', '1/5', '-i', str(out / 'frame-%02d.png'),
                        '-t', '30', '-r', '24', '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-movflags', '+faststart',
                        str(out / 'demo.mp4')], check=True)
    (out / 'transcript.json').write_text(json.dumps({'server': info['serverInfo'], 'presentation': 'Six actual screenshots, each held for five seconds. Scripted MCP client, not an LLM recording or a timing benchmark.', 'calls': log}, indent=2) + '\n')
    print(f'PASS: MCP form workflow verified; media written to {out}')


def chart(args):
    data = json.loads(args.input.read_text())
    summary, meta, context = data['summary'], data['metadata'], data['context']
    image = Image.new('RGB', (1600, 1080), BG)
    draw = ImageDraw.Draw(image)
    draw.text((48, 30), 'bruster / measured browser comparison', font=font(36, bold=True), fill=FG)
    draw.text((48, 84), f"Ubuntu 24.04 x86_64 · {meta['rounds']} fresh sessions · localhost fixtures · medians · lower is better", font=font(23), fill=MUTED)
    tools = [('bruster', 'Bruster / WebKitGTK + Xvfb'), ('playwright-shell', 'Playwright / Headless Shell'),
             ('playwright', 'Playwright / full Chrome'), ('puppeteer', 'Puppeteer / full Chrome'),
             ('agent-browser', 'agent-browser / full Chrome')]
    metrics = [('launch_to_first_page_ms', 'Launch to first loaded page', 'ms'),
               ('total_pss_mib', 'Total idle process memory (PSS)', 'MiB'),
               ('large_navigation_ms', 'Large-page navigation', 'ms'),
               ('screenshot_ms', 'Viewport screenshot', 'ms')]
    for index, (metric, title, unit) in enumerate(metrics):
        x, y = 48 + (index % 2) * 770, 146 + (index // 2) * 350
        draw.text((x, y), title, font=font(25, bold=True), fill=FG)
        maximum = max(summary[key][metric]['median'] for key, _ in tools)
        for row, (key, label) in enumerate(tools):
            value = summary[key][metric]['median']
            assert summary[key][metric]['n'] > 0 and value > 0
            top = y + 49 + row * 54
            draw.text((x, top), label, font=font(17), fill=MUTED)
            width = value / maximum * 545
            draw.rectangle((x, top + 25, x + width, top + 40), fill=ACCENT if key == 'bruster' else '#57718f')
            draw.text((x + width + 10, top + 19), f'{value:.1f} {unit}', font=font(17), fill=FG)
    lines = [
        f"Run #{context['run_number']} · {meta['started_utc'][:10]} · Bruster commit {context['sha'][:12]} · {meta['cpu_model']}",
        f"Playwright {meta['packages']['playwright-core']} · Puppeteer {meta['packages']['puppeteer-core']} · agent-browser {meta['packages']['agent-browser']} · WebKitGTK {meta['webkitgtk']}",
        f"{meta['chrome']} · Node {meta['node']} · 1280 × 800 viewport",
        'Memory includes browser helpers and Xvfb for Bruster. Different browser engines; results are workload-specific.',
        'Selected metrics: see the complete report for extraction, installed-file footprint, variability, and fault probes.',
        'Reproducible data and methodology: aliilyas.github.io/bruster/benchmarks/',
    ]
    for index, line in enumerate(lines):
        draw.text((48, 865 + index * 30), line, font=font(18), fill=ACCENT if index == 5 else MUTED)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    image.save(args.output)
    print(args.output)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='mode', required=True)
    capture = commands.add_parser('demo')
    capture.add_argument('--output', type=Path, required=True)
    capture.add_argument('command', nargs=argparse.REMAINDER, help='Bruster executable (and optional launcher); put it last')
    plot = commands.add_parser('chart')
    plot.add_argument('--input', type=Path, required=True)
    plot.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.mode == 'demo':
        if not args.command:
            parser.error('demo requires a Bruster executable')
        demo(args)
    else:
        chart(args)


if __name__ == '__main__':
    main()
