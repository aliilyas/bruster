#!/usr/bin/env python3
"""Validate raw comparisons and render a versioned, dependency-free Pages site."""
import argparse
import collections
import hashlib
import html
import json
import math
import os
import re
import statistics
from pathlib import Path

from bench_audit import summary


LABELS = {
    'bruster': 'Bruster / WebKitGTK',
    'playwright-shell': 'Playwright / Headless Shell',
    'playwright': 'Playwright / full Chrome',
    'puppeteer': 'Puppeteer / full Chrome',
    'agent-browser': 'agent-browser / full Chrome',
}
SCALARS = ('startup_ms', 'first_navigation_ms', 'launch_to_first_page_ms')
VECTORS = ('tiny_navigation_ms', 'tiny_extract_ms', 'large_navigation_ms', 'large_extract_ms',
           'large_extract_json_ms', 'image_navigation_ms', 'screenshot_ms')
MEMORY = ('rss_mib', 'pss_mib', 'display_pss_mib', 'total_pss_mib', 'process_count')
METRICS = (
    ('launch_to_first_page_ms', 'Launch → first loaded page (ms)'),
    ('tiny_navigation_ms', 'Warm tiny-page navigation (ms)'),
    ('tiny_extract_ms', 'Tiny DOM extraction (ms)'),
    ('large_navigation_ms', 'Large-page navigation (ms)'),
    ('large_extract_ms', 'Large DOM extraction, object return (ms)'),
    ('large_extract_json_ms', 'Large DOM extraction, JSON-string return (ms)'),
    ('image_navigation_ms', 'Image-page navigation (ms)'),
    ('screenshot_ms', 'PNG screenshot (ms)'),
    ('total_pss_mib', 'Idle total PSS, including display (MiB)'),
    ('rss_mib', 'Idle process RSS, excluding display (MiB)'),
)
METHOD = (
    'Ten sessions per configuration by default, with rotating order and fresh browser profiles. '
    '1280×800 viewport; localhost fixtures; no-store HTTP responses; navigation waits for load. '
    'OS filesystem caches are not flushed. Identical extraction JavaScript and cross-tool result hashes. '
    'Timings include controller round trips; agent-browser includes its per-command native CLI. '
    'Memory covers the complete owned process forest (including detached daemons and helpers), '
    'plus Xvfb for Bruster. PSS apportions shared pages; summed RSS double-counts them. '
    'Memory is small-page idle usage, not peak usage. Native snapshots have different semantics '
    'and are retained in the raw artifacts rather than ranked as equal work. '
    'MB = 1,000,000 bytes; MiB = 1,048,576 bytes. Installed-file inventories are lower bounds '
    'including browser/engine, linked libraries, observed mapped files and Node where required; '
    'unobserved OS resources may add more. GitHub-hosted runner hardware and OS packages can change: '
    'compare the configurations within a run and inspect provenance before interpreting trends.'
)
PUBLIC_FILES = ('measurement.json', 'summary.json', 'samples.json', 'footprint.json', 'report.md',
                'package.json', 'package-lock.json')


def require(ok, message):
    if not ok:
        raise ValueError(message)


def number(value):
    require(type(value) in (int, float) and math.isfinite(value) and value >= 0,
            f'Expected a finite nonnegative measurement, got {value!r}')
    return value


def write_json(path, obj):
    path.write_text(json.dumps(obj, indent=2, allow_nan=False) + '\n')


def validate(metadata, rows, footprint):
    rounds, iterations = metadata['rounds'], metadata['iterations']
    require(type(rounds) is int and rounds > 0 and type(iterations) is int and iterations > 0,
            'Invalid rounds/iterations')
    expected = {(tool, round_) for tool in LABELS for round_ in range(1, rounds + 1)}
    require(len(rows) == len(expected) and {(r['tool'], r['round']) for r in rows} == expected,
            'Missing, duplicate or unexpected sessions')
    hashes = {r['large_extract_sha256'] for r in rows}
    require(len(hashes) == 1 and re.fullmatch(r'[0-9a-f]{64}', next(iter(hashes))),
            'Cross-tool extraction hashes differ or are missing')
    for row in rows:
        require(not any(row[k] for k in ('competing_before', 'competing_at_memory', 'competing_after')),
                f"Competing processes: {row['tool']} round {row['round']}")
        require(row['image_requests'] == 36, 'Incomplete image workload')
        require(row['browser_info']['state'] == 'complete' and row['browser_info']['width'] == 1280
                and row['browser_info']['height'] == 800, 'Invalid page readiness or viewport')
        if row['round'] == 1:
            require(number(row['delayed_validation_ms']) >= 240, 'Navigation missed the delayed load')
        for key in SCALARS:
            number(row[key])
        for key in VECTORS:
            count = iterations if key.startswith('tiny_') else 2 if key == 'screenshot_ms' else 3 if key == 'image_navigation_ms' else 5
            require(len(row[key]) == count, f'Incomplete workload: {key}')
            for value in row[key]:
                number(value)
        require(len(row['idle_memory']) == 3, 'Missing idle memory samples')
        for sample in row['idle_memory']:
            require(sample['complete'] and sample['processes'], 'Incomplete process accounting')
            require(len(sample['display']) == (1 if row['tool'] == 'bruster' else 0), 'Missing/unexpected display')
            for key in MEMORY:
                number(sample[key])
            for proc in sample['processes'] + sample['display']:
                number(proc['rss_kib'])
                number(proc['pss_kib'])
            total = sum(p['pss_kib'] for p in sample['processes'] + sample['display']) / 1024
            require(math.isclose(total, sample['total_pss_mib']), 'PSS total/units mismatch')
        checks = {c['name'] for c in row['failure_checks']}
        require(checks >= {'javascript_exception', 'javascript_syntax_error', 'recovery_after_javascript_errors',
                           'connection_refused', 'recovery_after_navigation_error'}, 'Missing fault probes')
    require(set(footprint['tool_totals']) == set(LABELS), 'Missing runtime inventories')
    for tool, total in footprint['tool_totals'].items():
        require(number(total['bytes']) > 0 and total['files'] > 0, 'Empty runtime inventory')
        files = footprint['file_inventory'][tool]
        require(total['files'] == len(files) and total['bytes'] == sum(number(p['bytes']) for p in files),
                f'Runtime inventory total mismatch: {tool}')


def aggregate(rows):
    stats = {}
    for tool in LABELS:
        subset = [r for r in rows if r['tool'] == tool]
        result = {key: summary([r[key] for r in subset]) for key in SCALARS}
        result.update({key: summary([v for r in subset for v in r[key]]) for key in VECTORS})
        result.update({key: summary([statistics.median(m[key] for m in r['idle_memory']) for r in subset])
                       for key in MEMORY})
        result['sessions_with_failures'] = sum(bool(r['failures']) for r in subset)
        result['fault_probe_failures'] = dict(collections.Counter(f['name'] for r in subset for f in r['failures']))
        result['recovery_retry_passes'] = sum(c['pass'] for r in subset for c in r['failure_checks']
                                              if c['name'] == 'navigation_recovery_retry_100ms')
        result['failures'] = [{'round': r['round'], **f} for r in subset for f in r['failures']]
        stats[tool] = result
    return stats


def context_from_env():
    context = {key: os.environ['GITHUB_' + key.upper()] for key in ('repository', 'sha', 'run_id', 'run_number', 'run_attempt')}
    require(re.fullmatch(r'[\w.-]+/[\w.-]+', context['repository']), 'Invalid repository')
    require(re.fullmatch(r'[0-9a-f]{40}', context['sha']), 'Invalid commit SHA')
    for key in ('run_id', 'run_number', 'run_attempt'):
        context[key] = int(context[key])
        require(context[key] > 0, f'Invalid {key}')
    context['run_url'] = f"https://github.com/{context['repository']}/actions/runs/{context['run_id']}"
    return context


def record_id(record):
    c = record['context']
    return f"{c['sha']}-{c['run_id']}-{c['run_attempt']}"


def table_rows(record):
    stats = record['summary']
    for key, label in METRICS:
        yield [label, *(f"{stats[t][key]['median']:.1f}" for t in LABELS)]
    yield ['Installed runtime files, lower bound (MB)',
           *(f"{record['footprint']['tool_totals'][t]['bytes'] / 1e6:.1f}" for t in LABELS)]
    yield ['Sessions with fault-probe failures',
           *(f"{stats[t]['sessions_with_failures']}/{record['metadata']['rounds']}" for t in LABELS)]


def markdown(record):
    c, m = record['context'], record['metadata']
    lines = ['# Browser comparison', '', f"Commit `{c['sha']}` · [workflow run]({c['run_url']})",
             f"Measured {m['finished_utc']}; {m['rounds']} sessions per configuration. Values are medians.",
             versions(m), '',
             '| Metric | ' + ' | '.join(LABELS.values()) + ' |', '|---|' + '---:|' * len(LABELS)]
    lines.extend('| ' + ' | '.join(row) + ' |' for row in table_rows(record))
    lines.extend(['', METHOD, '', '## Fault probes', ''])
    for tool, label in LABELS.items():
        s = record['summary'][tool]
        lines.append(f"- {label}: {json.dumps(s['fault_probe_failures'])}; successful 100 ms recovery retries: {s['recovery_retry_passes']}.")
    lines.extend(['', '## Provenance', '', '```json', json.dumps(m, indent=2), '```', ''])
    return '\n'.join(lines)


def prepare(results, context):
    original = json.loads((results / 'summary.json').read_text())
    rows = json.loads((results / 'samples.json').read_text())
    footprint = json.loads((results / 'footprint.json').read_text())
    validate(original['metadata'], rows, footprint)
    require(hashlib.sha256((results / 'package-lock.json').read_bytes()).hexdigest()
            == original['metadata']['package_lock_sha256'], 'Resolved dependency lockfile changed during measurement')
    record = {'schema_version': 1, 'context': context, 'metadata': original['metadata'],
              'summary': aggregate(rows), 'footprint': {k: v for k, v in footprint.items() if k != 'file_inventory'}}
    write_json(results / 'measurement.json', record)
    (results / 'report.md').write_text(markdown(record))
    return record


def versions(metadata):
    packages = metadata['packages']
    return (f"Playwright {packages['playwright-core']} · Puppeteer {packages['puppeteer-core']} · "
            f"agent-browser {packages['agent-browser']} · {metadata['chrome']} · Node {metadata['node']}")


def page(record, history=None):
    e = lambda value: html.escape(str(value), quote=True)
    c, m = record['context'], record['metadata']
    prefix = f"runs/{record_id(record)}/" if history is not None else ''
    parts = ['<!doctype html><html lang="en"><meta charset="utf-8">',
             '<meta name="viewport" content="width=device-width, initial-scale=1">',
             '<title>Bruster browser benchmarks</title><style>',
             'body{font:16px/1.6 system-ui,sans-serif;margin:2rem auto;padding:0 1rem;max-width:1200px;color:#202938}',
             'a{color:#075ab4}.scroll{overflow:auto}table{border-collapse:collapse;width:100%}',
             'th,td{padding:.6rem;border:1px solid #ccd3dc;text-align:right}th:first-child,td:first-child{text-align:left}',
             'th{background:#edf2f7}pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#f5f7fa;padding:1rem}',
             '</style><body><h1>Browser benchmarks</h1>',
             f'<p>Commit <code>{e(c["sha"])}</code> · <a href="{e(c["run_url"])}">Workflow and raw artifacts</a></p>',
             f'<p>Measured {e(m["finished_utc"])} · {e(m["rounds"])} sessions per configuration. Values are medians.</p>',
             f'<p>{e(versions(m))}</p>',
             '<div class="scroll"><table><thead><tr><th>Metric</th>' + ''.join(f'<th>{e(v)}</th>' for v in LABELS.values()) + '</tr></thead><tbody>']
    parts.extend('<tr>' + ''.join(f'<td>{e(cell)}</td>' for cell in row) + '</tr>' for row in table_rows(record))
    parts.extend(['</tbody></table></div><h2>Method</h2>', f'<p>{e(METHOD)}</p>',
                  '<p>' + ' · '.join(f'<a href="{e(prefix + name)}">{e(name)}</a>' for name in PUBLIC_FILES) + '</p>',
                  '<h2>Fault probes</h2><p>Failures remain visible even when a later retry succeeds. '
                  'These probes run after the timed workloads.</p><ul>'])
    for tool, label in LABELS.items():
        s = record['summary'][tool]
        counts = ', '.join(f'{name}: {count}' for name, count in s['fault_probe_failures'].items()) or 'none'
        parts.append(f'<li>{e(label)} — failures: {e(counts)}; successful 100 ms recovery retries: {s["recovery_retry_passes"]}</li>')
    parts.extend(['</ul><details><summary>Environment, versions and hashes</summary>',
                  '<pre>' + e(json.dumps(m, indent=2)) + '</pre></details>'])
    if history is not None:
        parts.append('<h2>History</h2><p>Newest workflow invocation first; late-finishing older runs never replace latest.</p><ul>')
        for item in history:
            ctx = item['context']
            parts.append(f'<li><a href="runs/{e(record_id(item))}/">{e(ctx["sha"][:12])} · run {ctx["run_number"]}, '
                         f'attempt {ctx["run_attempt"]}</a> · {e(item["metadata"]["finished_utc"])}</li>')
        parts.append('</ul>')
    else:
        parts.append('<p><a href="../../">All measurements</a></p>')
    parts.append('</body></html>\n')
    return '\n'.join(parts)


def install(results, site):
    record = json.loads((results / 'measurement.json').read_text())
    root = site / 'benchmarks'
    destination = root / 'runs' / record_id(record)
    destination.mkdir(parents=True, exist_ok=True)
    for name in PUBLIC_FILES:
        target = destination / name
        content = (results / name).read_bytes()
        require(not target.exists() or target.read_bytes() == content, f'Refusing to overwrite immutable result: {target}')
        target.write_bytes(content)
    (destination / 'index.html').write_text(page(record))
    history = [json.loads(p.read_text()) for p in (root / 'runs').glob('*/measurement.json')]
    history.sort(key=lambda r: (r['context']['run_number'], r['context']['run_attempt'], r['context']['run_id']), reverse=True)
    write_json(root / 'latest.json', history[0])
    write_json(root / 'history.json', [dict(r['context'], path=f'runs/{record_id(r)}/') for r in history])
    (root / 'index.html').write_text(page(history[0], history))
    (site / '.nojekyll').touch()
    index = site / 'index.html'
    if not index.exists():
        index.write_text('<!doctype html><meta charset="utf-8"><a href="benchmarks/">Browser benchmarks</a>\n')
    else:
        # Migrate only the known retired benchmark block, preserving site docs.
        content = index.read_text()
        legacy = re.search(r'<h2 id="performance">.*?(?=<h2 id="development">)', content, re.S)
        if legacy and 'scripts/bench.py' in legacy.group():
            content = content[:legacy.start()] + ('<h2 id="performance">Performance</h2>\n'
                '<p><a href="benchmarks/">Live comparison, runtime footprint and measurement history</a>. '
                'Includes Bruster, Playwright, Puppeteer and agent-browser.</p>\n\n    ') + content[legacy.end():]
            content = re.sub(r'<script>\s*function get\(id\).*?fetch\("\./metrics.json"\).*?</script>', '', content, flags=re.S)
            index.write_text(content)
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('prepare', 'install'))
    parser.add_argument('--results', type=Path, required=True)
    parser.add_argument('--site', type=Path)
    args = parser.parse_args()
    if args.command == 'prepare':
        prepare(args.results, context_from_env())
    else:
        if args.site is None:
            parser.error('install requires --site')
        install(args.results, args.site)


if __name__ == '__main__':
    main()
