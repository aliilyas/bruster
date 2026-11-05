#!/usr/bin/env python3
"""Build and serve the website, then run its Bruster DSL suites on desktop and mobile."""
import argparse
import functools
import subprocess
import sys
import tempfile
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from site_build import build
from site_layout import ROOT


class Handler(SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        pass


def run(binary, output, visible=False):
    temporary_root = '/tmp/opencode' if Path('/tmp/opencode').is_dir() else None
    with tempfile.TemporaryDirectory(prefix='bruster-website-', dir=temporary_root) as temp:
        # Bind before building: an OS-assigned port avoids races and fixed-port conflicts.
        handler = functools.partial(Handler, directory=temp)
        with ThreadingHTTPServer(('127.0.0.1', 0), handler) as server:
            base_url = f'http://127.0.0.1:{server.server_port}/bruster/'
            build(Path(temp) / 'bruster', base_url=base_url)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            suites = (
                ('website-desktop', '960x640', base_url,
                 ['example-tests/website/pages.bru', 'example-tests/website/components.bru',
                  'example-tests/website/learn-testin.bru']),
                ('website-mobile', '375x640', base_url, ['example-tests/website/mobile.bru']),
                ('demo-desktop', '960x640', base_url + 'demo/',
                 ['example-tests/demo/recording.bru', 'example-tests/demo/components.bru']),
                ('demo-mobile', '375x640', base_url + 'demo/',
                 ['example-tests/demo/recording.bru', 'example-tests/demo/components.bru']),
                ('course-examples', '960x640', base_url + 'demo/',
                 [path.relative_to(ROOT).as_posix()
                  for path in sorted((ROOT / 'example-tests/learn-testin').glob('*.bru'))]),
            )
            status = 0
            try:
                for name, viewport, url, files in suites:
                    print(f'\n{name}: {url} ({viewport})', flush=True)
                    command = [str(binary), 'test', *[str(ROOT / file) for file in files],
                               '--base-url', url, '--viewport', viewport, '--output', str(output / name)]
                    if visible:
                        command.append('--visible')
                    result = subprocess.run(command, cwd=ROOT, check=False)
                    # A browser crash may be reported as a negative signal number on POSIX.
                    status = max(status, 1 if result.returncode < 0 else result.returncode)
            finally:
                server.shutdown()
                thread.join()
    return status


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--binary', type=Path, default=ROOT / 'target/release' /
                        ('bruster.exe' if sys.platform == 'win32' else 'bruster'),
                        help='Bruster executable or launcher with the test subcommand')
    parser.add_argument('--output', type=Path, default=ROOT / 'target/website-results')
    parser.add_argument('--visible', action='store_true', help='Show browser windows')
    args = parser.parse_args()
    if not args.binary.is_file():
        parser.error(f'Bruster executable not found: {args.binary}; build with cargo build --release --locked')
    try:
        return run(args.binary.resolve(), args.output.resolve(), args.visible)
    except OSError as error:
        parser.exit(2, f'Website tests could not start: {error}\n')


if __name__ == '__main__':
    raise SystemExit(main())
