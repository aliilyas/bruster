#!/usr/bin/env python3
"""Bundle verified Bruster release binaries as one cross-platform MCPB package."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import tarfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
TARGETS = ['aarch64-apple-darwin', 'x86_64-apple-darwin', 'aarch64-unknown-linux-gnu',
           'x86_64-unknown-linux-gnu', 'x86_64-pc-windows-msvc']
LAUNCHER = '''#!/bin/sh
set -eu
case "$(uname -s)-$(uname -m)" in
  Darwin-arm64) target=aarch64-apple-darwin ;;
  Darwin-x86_64) target=x86_64-apple-darwin ;;
  Linux-aarch64|Linux-arm64) target=aarch64-unknown-linux-gnu ;;
  Linux-x86_64) target=x86_64-unknown-linux-gnu ;;
  *) echo "Unsupported platform; see https://github.com/aliilyas/bruster" >&2; exit 1 ;;
esac
dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
exec "$dir/$target/bruster" "$@"
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--release-dir', type=Path, required=True)
    parser.add_argument('--version', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    checksums = {}
    for line in (args.release_dir / 'SHA256SUMS').read_text().splitlines():
        digest, filename = line.split(maxsplit=1)
        checksums[filename.lstrip('*')] = digest
    manifest = {
        'manifest_version': '0.3', 'name': 'bruster', 'display_name': 'Bruster', 'version': args.version,
        'description': 'Native-webview browser automation for agents: navigation, forms, snapshots, and screenshots.',
        'long_description': 'A Rust MCP server using WKWebView on macOS, WebKitGTK on Linux, and WebView2 on Windows. No Node.js required. Linux needs WebKitGTK 4.1 and a display or Xvfb; Windows needs WebView2. Browser runtimes and their libraries are not bundled. Unix binaries support x86_64 and ARM64; Windows supports x86_64. See the repository for installation requirements and API limits.',
        'author': {'name': 'aliilyas', 'url': 'https://github.com/aliilyas'},
        'repository': {'type': 'git', 'url': 'https://github.com/aliilyas/bruster.git'},
        'homepage': 'https://aliilyas.github.io/bruster/',
        'documentation': 'https://github.com/aliilyas/bruster#readme',
        'support': 'https://github.com/aliilyas/bruster/issues',
        'license': 'MIT', 'keywords': ['browser', 'automation', 'webview', 'rust', 'mcp'],
        'compatibility': {'platforms': ['darwin', 'linux', 'win32']},
        'server': {'type': 'binary', 'entry_point': 'server/bruster', 'mcp_config': {
            'command': '${__dirname}/server/bruster', 'args': ['--mcp', '--quiet'],
            'platform_overrides': {'win32': {'command': '${__dirname}/server/x86_64-pc-windows-msvc/bruster.exe'}}}},
        'tools_generated': True,
    }
    files = {'manifest.json': (json.dumps(manifest, indent=2).encode() + b'\n', 0o644),
             'server/bruster': (LAUNCHER.encode(), 0o755)}
    for name in ['README.md', 'LICENSE', 'assets/logo.svg']:
        files[name] = ((ROOT / name).read_bytes(), 0o644)
    for target in TARGETS:
        windows = target.endswith('msvc')
        stem = f'bruster-{args.version}-{target}'
        filename = stem + ('.zip' if windows else '.tar.gz')
        data = (args.release_dir / filename).read_bytes()
        if hashlib.sha256(data).hexdigest() != checksums[filename]:
            raise ValueError(f'Checksum mismatch: {filename}')
        binary = 'bruster.exe' if windows else 'bruster'
        if windows:
            with zipfile.ZipFile(io.BytesIO(data)) as archive:
                payload = archive.read(f'{stem}/{binary}')
        else:
            with tarfile.open(fileobj=io.BytesIO(data), mode='r:gz') as archive:
                payload = archive.extractfile(f'{stem}/{binary}').read()
        files[f'server/{target}/{binary}'] = (payload, 0o755)
    args.output.mkdir(parents=True, exist_ok=True)
    package = args.output / f'bruster-{args.version}.mcpb'
    with zipfile.ZipFile(package, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name, (data, mode) in sorted(files.items()):
            info = zipfile.ZipInfo(name)
            info.create_system = 3
            info.external_attr = (0o100000 | mode) << 16
            archive.writestr(info, data, compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
    digest = hashlib.sha256(package.read_bytes()).hexdigest()
    server = {
        '$schema': 'https://static.modelcontextprotocol.io/schemas/2025-12-11/server.schema.json',
        'name': 'io.github.aliilyas/bruster', 'title': 'Bruster', 'version': args.version,
        'description': 'Native-webview browser automation: navigate, fill forms, inspect pages, and capture screenshots.',
        'repository': {'url': 'https://github.com/aliilyas/bruster', 'source': 'github'},
        'websiteUrl': 'https://aliilyas.github.io/bruster/',
        'packages': [{'registryType': 'mcpb', 'identifier': f'https://github.com/aliilyas/bruster/releases/download/v{args.version}/{package.name}',
                      'fileSha256': digest, 'transport': {'type': 'stdio'}}],
    }
    (args.output / 'server.json').write_text(json.dumps(server, indent=2) + '\n')
    (args.output / 'MCP-SHA256SUMS').write_text(f'{digest}  {package.name}\n')
    print(f'{package}: {package.stat().st_size} bytes, sha256:{digest}')


if __name__ == '__main__':
    main()
