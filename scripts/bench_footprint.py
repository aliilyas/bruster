#!/usr/bin/env python3
"""Inventory Linux runtime files, linked libraries and observed file mappings.

Logical bytes are deduplicated by inode, not summed package-manager estimates.
This is an installed-file lower bound: unobserved OS resources can add more.
"""
import argparse
import json
import os
import re
import shutil
import subprocess
from pathlib import Path


def files(root):
    return {p.resolve() for p in root.rglob('*') if p.is_file()}


def inventory(paths):
    unique = {}
    for path in sorted(paths):
        stat = path.stat()
        unique.setdefault((stat.st_dev, stat.st_ino), {'path': str(path), 'bytes': stat.st_size})
    return list(unique.values())


def libraries(paths):
    result = set()
    for path in sorted(paths):
        with path.open('rb') as stream:
            if stream.read(4) != b'\x7fELF':
                continue
        proc = subprocess.run(['ldd', str(path)], capture_output=True, text=True, timeout=30)
        output = proc.stdout + proc.stderr
        if 'not found' in output:
            raise RuntimeError(f'Missing runtime library for {path}: {output}')
        if proc.returncode and not any(s in output for s in ('not a dynamic executable', 'statically linked')):
            raise RuntimeError(f'ldd failed for {path}: {output}')
        for line in output.splitlines():
            match = re.search(r'(?:=>\s+)?(/[^\s]+)\s+\(', line)
            if match:
                result.add(Path(match.group(1)).resolve(strict=True))
    return result


def package_files(deps, name):
    seen, result = set(), set()
    pending = [deps / 'node_modules' / name]
    while pending:
        package = pending.pop().resolve(strict=True)
        if package in seen:
            continue
        seen.add(package)
        result.update(files(package))
        manifest = json.loads((package / 'package.json').read_text())
        for dependency in manifest.get('dependencies', {}):
            for parent in (package, *package.parents):
                resolved = parent / 'node_modules' / dependency
                if (resolved / 'package.json').is_file():
                    pending.append(resolved)
                    break
            else:
                raise RuntimeError(f'Missing dependency: {dependency}')
    return result


def measure(args):
    bruster_libraries = libraries({args.bruster})
    webkit_library = next(p for p in bruster_libraries if p.name.startswith('libwebkit2gtk-4.1'))
    helpers = Path(os.environ.get('WEBKIT_EXEC_PATH', webkit_library.parent / 'webkit2gtk-4.1'))
    if not (helpers / 'WebKitWebProcess').is_file() or not (helpers / 'WebKitNetworkProcess').is_file():
        raise RuntimeError(f'WebKit helper directory not found: {helpers}')
    bruster_files = {args.bruster} | files(helpers)
    for name in ('Xvfb', 'xvfb-run', 'xauth', 'sh'):
        executable = shutil.which(name)
        if not executable:
            raise RuntimeError(f'Missing display runtime: {name}')
        bruster_files.add(Path(executable).resolve())
    chrome, shell = files(args.chrome.parent), files(args.shell.parent)
    node = {args.node} | libraries({args.node})
    playwright = package_files(args.deps, 'playwright-core')
    puppeteer = package_files(args.deps, 'puppeteer-core')
    agent = {args.deps / 'node_modules/agent-browser/bin/agent-browser-linux-x64'}
    chrome_runtime, shell_runtime = chrome | libraries(chrome), shell | libraries(shell)
    groups = {
        'bruster': bruster_files | bruster_libraries | libraries(bruster_files),
        'playwright': playwright | node | chrome_runtime,
        'playwright-shell': playwright | node | shell_runtime,
        'puppeteer': puppeteer | node | chrome_runtime,
        'agent-browser': agent | libraries(agent) | chrome_runtime,
    }
    # Include observed dlopened libraries, mapped fonts and other runtime files.
    for row in json.loads(args.samples.read_text()):
        for sample in row['idle_memory']:
            for proc in sample['processes'] + sample['display']:
                for name in proc.get('mapped_files', []):
                    path = Path(name)
                    if path.is_file():
                        groups[row['tool']].add(path.resolve())
    inventories = {tool: inventory(paths) for tool, paths in groups.items()}
    return {
        'units': 'uncompressed logical bytes, deduplicated by device/inode',
        'scope': 'tool runtime, selected browser bundle, linked libraries, observed mapped files; '
                 'Bruster includes WebKit helpers and Xvfb; Node included where required',
        'limitation': 'Installed-file lower bound, not download size or complete OS image; '
                      'unobserved fonts, plugins and other OS resources may add more. '
                      'Build tools, package caches and optional video tooling are excluded.',
        'tool_totals': {tool: {'bytes': sum(p['bytes'] for p in rows), 'files': len(rows)}
                        for tool, rows in inventories.items()},
        'file_inventory': inventories,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for flag in ('bruster', 'node', 'chrome', 'shell', 'deps', 'samples', 'output'):
        parser.add_argument('--' + flag, type=Path, required=True)
    args = parser.parse_args()
    for flag in ('bruster', 'node', 'chrome', 'shell', 'deps', 'samples'):
        setattr(args, flag, getattr(args, flag).resolve(strict=True))
    args.output.write_text(json.dumps(measure(args), indent=2) + '\n')


if __name__ == '__main__':
    main()
