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
from datetime import datetime, timezone
from pathlib import Path

from bench_audit import summary
from site_layout import SITE_URL, render_page
from bench_tools import LABELS as ALL_LABELS, LEGACY_TOOLS, LINUX_TOOLS, recorded_labels, recorded_tools


# Retained for callers constructing legacy records. New records declare tools.
LABELS = {tool: ALL_LABELS[tool] for tool in LEGACY_TOOLS}
SCALARS = ('startup_ms', 'first_navigation_ms', 'launch_to_first_page_ms')
VECTORS = ('tiny_navigation_ms', 'tiny_extract_ms', 'large_navigation_ms', 'large_extract_ms',
           'large_extract_json_ms', 'image_navigation_ms', 'screenshot_ms')
MEMORY = ('rss_mib', 'pss_mib', 'display_pss_mib', 'total_pss_mib', 'process_count')
METRICS = (
    ('launch_to_first_page_ms', 'Launch → first loaded page (ms)'),
    ('startup_ms', 'Startup → ready / blank-page setup (ms)'),
    ('first_navigation_ms', 'First navigation after setup (ms)'),
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
METHOD_SECTIONS = (
    ('Sampling',
    'Ten sessions per configuration by default, with rotating order and fresh browser profiles. '
    'Values are medians [observed minimum–maximum], not confidence intervals. '
    'Startup and first navigation have one sample per session; repeated-operation timings pool all '
    'iterations; memory uses the median of three idle readings per session.'),
    ('Startup and workloads',
    'Startup includes adapter/daemon/server initialization and blank-page/viewport setup. '
    'The combined launch-to-first-page measurement includes both setup and the first navigation. '
    'Xvfb is already running: its startup time is excluded, but its memory is included. '
    '1280×800 viewport; localhost fixtures; no-store HTTP responses; navigation waits for load. '
    'OS filesystem caches are not flushed. Identical extraction JavaScript and cross-tool result hashes. '
    'Timings include controller round trips and per-command CLI launches. '
    'These deterministic workloads do not measure LLM inference or token efficiency.'),
    ('Memory and scope',
    'Memory covers the complete owned process forest (including detached daemons and helpers), '
    'plus Xvfb for Bruster. PSS apportions shared pages; summed RSS double-counts them. '
    'Memory is small-page idle usage, not peak usage. Native snapshots have different semantics '
    'and are retained in the raw artifacts rather than ranked as equal work. '
    'MB = 1,000,000 bytes; MiB = 1,048,576 bytes.'),
    ('Footprint and comparability',
    'Installed-file inventories are lower bounds '
    'including browser/engine, linked libraries, observed mapped files and Node where required; '
    'unobserved OS resources may add more. GitHub-hosted runner hardware and OS packages can change: '
    'compare the configurations within a run and inspect provenance before interpreting trends.')
)
METHOD = ' '.join(text for _, text in METHOD_SECTIONS)
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
    tools = recorded_tools(metadata)
    require(isinstance(tools, list) and tools and all(isinstance(t, str) for t in tools), 'Invalid tools')
    require(len(tools) == len(set(tools)) and set(tools) <= set(LINUX_TOOLS), 'Unknown or duplicate tools')
    expected = {(tool, round_) for tool in tools for round_ in range(1, rounds + 1)}
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
    require(set(footprint['tool_totals']) == set(tools), 'Missing runtime inventories')
    for tool, total in footprint['tool_totals'].items():
        require(number(total['bytes']) > 0 and total['files'] > 0, 'Empty runtime inventory')
        files = footprint['file_inventory'][tool]
        require(total['files'] == len(files) and total['bytes'] == sum(number(p['bytes']) for p in files),
                f'Runtime inventory total mismatch: {tool}')


def aggregate(rows):
    stats = {}
    for tool in dict.fromkeys(r['tool'] for r in rows):
        subset = [r for r in rows if r['tool'] == tool]
        result = {key: summary([r[key] for r in subset]) for key in SCALARS}
        result.update({key: summary([v for r in subset for v in r[key]]) for key in VECTORS})
        result.update({key: summary([statistics.median(m[key] for m in r['idle_memory']) for r in subset])
                       for key in MEMORY})
        result['sessions_with_failures'] = sum(bool(r['failures']) for r in subset)
        result['fault_probe_failures'] = dict(collections.Counter(c['name'] for r in subset for c in r['failure_checks'] if not c['pass']))
        result['lifecycle_failures'] = dict(collections.Counter(f['name'] for r in subset for f in r['failures']
                                                               if f['name'] in ('graceful_close', 'process_cleanup')))
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
    if c.get('local_validation'):
        require(re.fullmatch(r'\d{8}T\d{6}Z', c['local_id']), 'Invalid local measurement ID')
        return f"{c['sha']}-local-{c['local_id']}"
    return f"{c['sha']}-{c['run_id']}-{c['run_attempt']}"


def history_order(record):
    c = record['context']
    if c.get('local_validation'):
        # A local publication follows its recorded published-workflow boundary.
        # Results from a later workflow invocation supersede it normally.
        return (c['after_workflow_run_number'], 1, c['published_utc'], c['local_id'])
    return (c['run_number'], 0, c['run_attempt'], c['run_id'])


def run_label(context):
    if context.get('local_validation'):
        return f"Local validation · {context['local_id']}"
    return f"Run #{context['run_number']} · attempt {context['run_attempt']}"


def public_files(record):
    return PUBLIC_FILES + (('evidence.tar.gz',) if record['context'].get('local_validation') else ())


def table_rows(record):
    stats = record['summary']
    tools = recorded_tools(record['metadata'])
    for key, label in METRICS:
        yield [label, *(f"{stats[t][key]['median']:.1f} [{stats[t][key]['min']:.1f}–{stats[t][key]['max']:.1f}]" for t in tools)]
    yield ['Installed runtime files, lower bound (MB)',
           *(f"{record['footprint']['tool_totals'][t]['bytes'] / 1e6:.1f}" for t in tools)]
    yield ['Sessions with failures (including cleanup)',
           *(f"{stats[t]['sessions_with_failures']}/{record['metadata']['rounds']}" for t in tools)]


def markdown(record):
    c, m = record['context'], record['metadata']
    labels = recorded_labels(record)
    source = (f"Local validation · Bruster commit `{c['sha']}`" if c.get('local_validation')
              else f"Commit `{c['sha']}` · [workflow run]({c['run_url']})")
    lines = ['# Browser comparison', '', source,
             f"Measured {m['finished_utc']}; {m['rounds']} sessions per configuration. Values are medians [min–max].",
             versions(m), '', environment(m), '',
             '| Metric | ' + ' | '.join(labels.values()) + ' |', '|---|' + '---:|' * len(labels)]
    lines.extend('| ' + ' | '.join(row) + ' |' for row in table_rows(record))
    lines.extend(['', METHOD, '', '## Fault probes and cleanup', ''])
    for tool, label in labels.items():
        s = record['summary'][tool]
        lines.append(f"- {label}: fault probes {json.dumps(s['fault_probe_failures'])}; "
                     f"shutdown/cleanup {json.dumps(s.get('lifecycle_failures', {}))}; "
                     f"successful 100 ms recovery retries: {s['recovery_retry_passes']}.")
    catalog = m.get('competitors')
    if catalog:
        lines.extend(['', '## Hacker News competitor coverage', '',
                      f"[Source discussion]({catalog['source']}) · reviewed {catalog['reviewed']}", '', catalog['scope'], '',
                      '| Tool / repository | Coverage | Notes |', '|---|---|---|'])
        for tool in catalog['tools']:
            coverage = 'Measured in this run' if tool['id'] in labels else tool['status'] if tool['status'] != 'linux' else 'Not selected'
            comments = ' '.join(f"[HN {kind}](https://news.ycombinator.com/item?id={id_})"
                                for kind, key in (('comment', 'comments'), ('story', 'stories'))
                                for id_ in tool.get(key, []))
            lines.append(f"| [{tool['label']}]({tool.get('implementation', tool['github'])}) {comments} | {coverage} | {tool['notes']} |")
    lines.extend(['', '## Provenance', '', '```json', json.dumps(m, indent=2), '```', ''])
    return '\n'.join(lines)


def prepare(results, context):
    original = json.loads((results / 'summary.json').read_text())
    rows = json.loads((results / 'samples.json').read_text())
    footprint = json.loads((results / 'footprint.json').read_text())
    validate(original['metadata'], rows, footprint)
    require(hashlib.sha256((results / 'package-lock.json').read_bytes()).hexdigest()
             == original['metadata']['package_lock_sha256'], 'Resolved dependency lockfile changed during measurement')
    if context.get('local_validation'):
        record_id({'context': context})
        require(type(context['after_workflow_run_number']) is int and context['after_workflow_run_number'] >= 0,
                'Invalid workflow publication anchor')
        require(re.fullmatch(r'[0-9a-f]{40}', context['harness_sha']), 'Invalid harness commit')
        datetime.fromisoformat(context['published_utc'])
        require(hashlib.sha256((results / 'evidence.tar.gz').read_bytes()).hexdigest()
                == context['evidence_sha256'], 'Local evidence archive changed')
    record = {'schema_version': 2, 'context': context, 'metadata': original['metadata'],
              'summary': aggregate(rows), 'footprint': {k: v for k, v in footprint.items() if k != 'file_inventory'}}
    write_json(results / 'measurement.json', record)
    (results / 'report.md').write_text(markdown(record))
    return record


def versions(metadata):
    packages = metadata['packages']
    return (f"WebKitGTK {metadata.get('webkitgtk', 'unrecorded')} · "
            + ' · '.join(f'{name} {version}' for name, version in packages.items()) + ' · '
            f"{metadata['chrome']} · Headless Shell {metadata.get('headless_shell', 'unrecorded')} · Node {metadata['node']}")


def environment(metadata):
    memory = metadata.get('mem_total_kib')
    return (f"{metadata.get('os', {}).get('PRETTY_NAME', 'OS unrecorded')} · "
            f"{metadata.get('cpu_model', 'CPU unrecorded')} · {metadata.get('cpu_count', '?')} visible CPUs · "
            f"{f'{memory / 1024**2:.1f}' if memory else '?'} GiB RAM · "
            f"runner image {metadata.get('runner_image', {}).get('ImageVersion') or 'unrecorded'}")


def page(record, history=None, base_url=SITE_URL):
    e = lambda value: html.escape(str(value), quote=True)
    c, m = record['context'], record['metadata']
    prefix = f"runs/{record_id(record)}/" if history is not None else ''
    home = '../' if history is not None else '../../../'
    repo = f'https://github.com/{c["repository"]}'
    source_url = f'{repo}/blob/{c.get("harness_sha", c["sha"])}/benchmarks/README.md'
    run_link = (f'<span class="badge badge-warn">Local validation · {m["rounds"]} session(s) per configuration</span>'
                if c.get('local_validation') else
                f'<a href="{e(c["run_url"])}">Workflow #{c["run_number"]} ↗</a>')
    evidence_link = (f'<a href="{e(prefix + "evidence.tar.gz")}">Local raw evidence ↓</a>' if c.get('local_validation')
                     else f'<a href="{e(c["run_url"])}">Workflow and raw artifacts ↗</a>')
    stats = record['summary']
    tool_labels = recorded_labels(record)
    metric_titles = {
        'launch_to_first_page_ms': ('Launch → page', 'ms'),
        'startup_ms': ('Startup / setup', 'ms'),
        'first_navigation_ms': ('First navigation', 'ms'),
        'tiny_navigation_ms': ('Tiny page · warm', 'ms'),
        'tiny_extract_ms': ('Tiny DOM', 'ms'),
        'large_navigation_ms': ('Large page', 'ms'),
        'large_extract_ms': ('Large DOM · object', 'ms'),
        'large_extract_json_ms': ('Large DOM · JSON', 'ms'),
        'image_navigation_ms': ('Image page', 'ms'),
        'screenshot_ms': ('PNG screenshot', 'ms'),
        'total_pss_mib': ('Idle PSS + display', 'MiB'),
        'rss_mib': ('Idle RSS − display', 'MiB'),
        'footprint': ('Runtime · lower bound', 'MB'),
        'failures': ('Sessions with failures', 'incl. cleanup'),
    }

    def tool_heading(label):
        tool, engine = label.split(' / ')
        engine = {'full Chrome': 'Chrome', 'Headless Shell': 'Shell',
                  'Chrome test runner': 'Chrome runner', 'browser extension': 'Extension'}.get(engine, engine)
        tool = e(tool).replace('wright', '<wbr>wright').replace('Puppeteer', 'Puppe<wbr>teer')
        tool = tool.replace('Stagehand', 'Stage<wbr>hand').replace('browse.sh', 'browse.<wbr>sh')
        return f'<span>{tool}</span><span class="engine">{e(engine)}</span>'

    def time_label(value):
        return datetime.fromisoformat(value.replace('Z', '+00:00')).astimezone(timezone.utc).strftime('%d %b %Y · %H:%M UTC')

    def metric_row(key, label):
        title, unit = metric_titles[key]
        cells = [f'<tr role="row"><th scope="row" role="rowheader" id="metric-{key}" title="{e(label)}" aria-label="{e(label)}">'
                 f'{e(title)}<span class="metric-unit">{e(unit)}</span></th>']
        for tool, tool_label in tool_labels.items():
            if key == 'footprint':
                value = record['footprint']['tool_totals'][tool]['bytes'] / 1e6
                content = f'<span class="number">{value:,.1f}</span>'
            elif key == 'failures':
                value = stats[tool]['sessions_with_failures']
                color = 'warn' if value else 'neutral'
                content = f'<span class="badge badge-{color}">{value}/{m["rounds"]}</span>'
            else:
                value = stats[tool][key]
                content = (f'<span class="number">{value["median"]:,.1f}</span>'
                           f'<span class="range"><span>[{value["min"]:,.1f}–</span><wbr>'
                           f'<span>{value["max"]:,.1f}]</span></span>')
            cells.append(f'<td role="cell" headers="metric-{key} tool-{e(tool)}">'
                         f'<span class="cell-tool" aria-hidden="true">{tool_heading(tool_label)}</span>{content}</td>')
        return ''.join(cells) + '</tr>'

    def details(items):
        return '<dl class="detail-list">' + ''.join(
            f'<div><dt>{e(label)}</dt><dd>{e(value)}</dd></div>' for label, value in items) + '</dl>'

    def failures(counts):
        if not counts:
            return '<span class="badge badge-neutral">None</span>'
        return '<ul class="probe-list">' + ''.join(
            f'<li>{e(name.replace("_", " "))}: <strong>{count}</strong></li>'
            for name, count in counts.items()) + '</ul>'

    parts = ['<main class="container benchmark-content" id="main">',
             f'<p class="breadcrumbs"><a href="{home}">bruster</a><span>/</span>Benchmarks</p>',
             '<p class="eyebrow">Performance, with the context attached</p><h1>Browser benchmarks.</h1>',
             f'<p class="lead">Compare timing, memory, runtime footprint, and reliability across {len(tool_labels)} browser configurations.</p>',
             '<div class="run-meta">',
             f'<span class="badge badge-blue">{"Latest measurement" if history is not None else "Archived measurement"}</span>',
             f'<time datetime="{e(m["finished_utc"])}">{e(time_label(m["finished_utc"]))}</time>',
             f'<a href="{e(repo)}/commit/{e(c["sha"])}" title="{e(c["sha"])}">Commit <code>{e(c["sha"][:12])}</code></a>',
              run_link + '</div>',
             '<dl class="facts">',
             f'<div><dt>Configurations</dt><dd>{len(tool_labels)}</dd></div>',
             f'<div><dt>Sessions / configuration</dt><dd>{m["rounds"]}</dd></div>',
             f'<div><dt>Tiny iterations / session</dt><dd>{m["iterations"]}</dd></div>',
             '<div><dt>Viewport (px)</dt><dd>1280 × 800</dd></div></dl>',
             '<nav class="section-nav" aria-label="Benchmark sections">',
             '<a href="#results">Results</a><a href="#environment">Environment</a><a href="#method">Method</a>',
             '<a href="#reliability">Reliability</a><a href="#downloads">Downloads</a>',
             '<a href="#history">History</a>' if history is not None else '<a href="../../#history">All measurements</a>',
             '</nav><section id="results" aria-labelledby="results-title">',
             '<div class="section-head"><div><h2 id="results-title">Performance results</h2>',
             '<p>Timings include controller round trips. Lower values mean less time, memory, or disk space.</p></div>',
             '<div class="legend"><strong>Median</strong><br>[observed min–max]</div></div>',
             '<div class="panel">',
             '<table class="results-table" role="table"><caption class="sr-only">Performance comparison. Values are medians with observed minimum and maximum beneath, except runtime footprint and failure counts.</caption>',
             '<colgroup><col>' + '<col>' * len(tool_labels) + '</colgroup><thead role="rowgroup"><tr role="row"><th scope="col" role="columnheader">Metric / unit</th>']
    for tool, label in tool_labels.items():
        parts.append(f'<th scope="col" role="columnheader" id="tool-{e(tool)}" title="{e(label)}" aria-label="{e(label)}">{tool_heading(label)}</th>')
    parts.append('</tr></thead>')
    labels = dict(METRICS)
    labels.update(footprint='Installed runtime files, lower bound (MB)', failures='Sessions with failures (including cleanup)')
    for group, keys in (
        ('Startup', ('launch_to_first_page_ms', 'startup_ms', 'first_navigation_ms')),
        ('Navigation', ('tiny_navigation_ms', 'large_navigation_ms', 'image_navigation_ms')),
        ('Extraction and screenshots', ('tiny_extract_ms', 'large_extract_ms', 'large_extract_json_ms', 'screenshot_ms')),
        ('Memory and runtime footprint', ('total_pss_mib', 'rss_mib', 'footprint')),
        ('Reliability', ('failures',)),
    ):
        parts.append(f'<tbody role="rowgroup"><tr class="group-row" role="row"><th scope="rowgroup" role="rowheader" colspan="{len(tool_labels) + 1}">{e(group)}</th></tr>')
        parts.extend(metric_row(key, labels[key]) for key in keys)
        parts.append('</tbody>')
    parts.extend(['</table><p class="table-note">Ranges show observed variation, not confidence intervals. '
                  'Memory is idle usage; installed runtime sizes are lower bounds. <a href="#method">Read the measurement method</a>.</p></div></section>',
                  '<section class="section" id="environment" aria-labelledby="environment-title">',
                  '<div class="section-head"><div><h2 id="environment-title">Environment &amp; versions</h2>',
                  '<p>The machine and exact runtime versions behind this measurement.</p></div></div>',
                  '<div class="environment-grid"><div class="panel environment-card"><h3>Runner</h3>'])
    memory = m.get('mem_total_kib')
    parts.extend([details((
        ('Operating system', m.get('os', {}).get('PRETTY_NAME', 'Unrecorded')),
        ('Processor', m.get('cpu_model', 'Unrecorded')),
        ('Visible CPUs', m.get('cpu_count', 'Unrecorded')),
        ('System memory', f'{memory / 1024**2:.1f} GiB' if memory else 'Unrecorded'),
        ('Runner image', m.get('runner_image', {}).get('ImageVersion') or 'Unrecorded'),
    )), '</div><div class="panel environment-card"><h3>Browser runtimes &amp; tools</h3>', details((
        ('WebKitGTK', m.get('webkitgtk', 'Unrecorded')),
        *m['packages'].items(),
        ('Chrome', m['chrome']),
        ('Headless Shell', m.get('headless_shell', 'Unrecorded')),
        ('Node.js', m['node']),
    )), '</div></div></section>',
        '<section class="section" id="method" aria-labelledby="method-title">',
        '<div class="section-head"><div><h2 id="method-title">How to read these results</h2>',
        '<p>Measurement conditions, accounting boundaries, and comparison guidance.</p></div></div><div class="method-grid">'])
    for title, text in METHOD_SECTIONS:
        parts.append(f'<article class="panel method-card"><h3>{e(title)}</h3><p>{e(text)}</p></article>')
    parts.extend(['</div></section><section class="section" id="reliability" aria-labelledby="reliability-title">',
                  '<div class="section-head"><div><h2 id="reliability-title">Fault probes &amp; cleanup</h2>',
                  '<p>These probes run after the timed workloads. Failed attempts remain counted even when a later retry succeeds.</p></div></div>',
                  '<p class="scroll-hint">Scroll horizontally for fault, cleanup, and recovery details.</p>',
                  '<div class="panel table-scroll" role="region" aria-labelledby="reliability-title" tabindex="0">',
                  '<table class="reliability-table"><caption class="sr-only">Post-workload fault probes and cleanup outcomes for each configuration.</caption>',
                  '<thead><tr><th scope="col">Configuration</th><th scope="col">Sessions with failures</th>',
                  '<th scope="col">Fault-probe failures</th><th scope="col">Shutdown / cleanup failures</th><th scope="col">Successful 100 ms retries</th></tr></thead><tbody>'])
    for tool, label in tool_labels.items():
        s = stats[tool]
        tool_name, engine = label.split(' / ')
        color = 'warn' if s['sessions_with_failures'] else 'neutral'
        parts.append(f'<tr><th scope="row">{e(tool_name)}<span class="engine">{e(engine)}</span></th>'
                     f'<td><span class="badge badge-{color}">{s["sessions_with_failures"]}/{m["rounds"]}</span></td>'
                     f'<td>{failures(s["fault_probe_failures"])}</td><td>{failures(s.get("lifecycle_failures", {}))}</td>'
                     f'<td>{s["recovery_retry_passes"]}</td></tr>')
    parts.append('</tbody></table></div></section>')
    parts.extend([
                  '<section class="section" id="downloads" aria-labelledby="downloads-title"><div class="section-head"><div>',
                  '<h2 id="downloads-title">Raw data &amp; reproducibility</h2>',
                  '<p>Download the measurements, runtime inventory, and resolved dependency files for this run.</p></div>',
                  evidence_link + '</div><ul class="files">'])
    for name in public_files(record):
        kind = 'Archive' if name.endswith('.tar.gz') else 'Markdown' if name.endswith('.md') else 'JSON'
        parts.append(f'<li><a href="{e(prefix + name)}"><code>{e(name)}</code><span>{kind} ↓</span></a></li>')
    parts.extend(['</ul><details class="panel provenance"><summary>Full environment, versions and hashes</summary>',
                  '<pre tabindex="0" aria-label="Measurement provenance">' + e(json.dumps(m, indent=2)) + '</pre></details></section>'])
    if history is not None:
        parts.extend(['<section class="section" id="history" aria-labelledby="history-title"><div class="section-head"><div>',
                      '<h2 id="history-title">Measurement history</h2>',
                      '<p>Workflow runs are ordered by invocation. Local validations follow their recorded workflow boundary. '
                      'Each run retains its own data and environment.</p></div></div>',
                      '<ol class="panel history-list">'])
        for item in history[:10]:
            ctx = item['context']
            latest = '<span class="badge badge-blue">Latest</span>' if record_id(item) == record_id(record) else ''
            date = item['metadata']['finished_utc']
            parts.append(f'<li class="history-entry"><div><a href="runs/{e(record_id(item))}/">{e(run_label(ctx))}</a>'
                         f'{latest}<code>{e(ctx["sha"][:12])}</code></div><div><time datetime="{e(date)}">{e(time_label(date))}</time>'
                         f'<p>{e(environment(item["metadata"]))}</p></div></li>')
        parts.append('</ol></section>')
    else:
        parts.append('<p class="back-link"><a href="../../">← All measurements</a></p>')
    parts.extend([f'<p class="benchmark-source"><a href="{e(source_url)}">Benchmark source &amp; methodology ↗</a></p>',
                  '</main>'])
    archive = history is None
    path = f'benchmarks/runs/{record_id(record)}/' if archive else 'benchmarks/'
    title = (f'Bruster Benchmark {run_label(c)}' if archive
             else 'Browser Benchmarks: Bruster & Browser Automation Tools')
    description = ('Bruster browser benchmarks: compare startup, navigation, memory, runtime footprint, '
                   'and reliability across automation tools. Raw data and methodology included.')
    if archive:
        description = f'Archived measurement from {m["finished_utc"]}. ' + description
    return render_page(title, description, path, '\n'.join(parts), base_url=base_url,
                       section='Benchmarks', body_class='benchmark-page', noindex=archive,
                       extra_head='<style>\n' + Path(__file__).with_suffix('.css').read_text() + '</style>')


def render_reports(root, base_url=SITE_URL):
    """Refresh presentation from immutable records without running measurements."""
    history = [json.loads(p.read_text()) for p in (root / 'runs').glob('*/measurement.json')]
    history.sort(key=history_order, reverse=True)
    if not history:
        return []
    for item in history:
        (root / 'runs' / record_id(item) / 'index.html').write_text(page(item, base_url=base_url))
    write_json(root / 'latest.json', history[0])
    write_json(root / 'history.json', [dict(r['context'], path=f'runs/{record_id(r)}/') for r in history])
    (root / 'index.html').write_text(page(history[0], history, base_url=base_url))
    return history


def install(results, site):
    record = json.loads((results / 'measurement.json').read_text())
    root = site / 'benchmarks'
    destination = root / 'runs' / record_id(record)
    destination.mkdir(parents=True, exist_ok=True)
    for name in public_files(record):
        target = destination / name
        content = (results / name).read_bytes()
        require(not target.exists() or target.read_bytes() == content, f'Refusing to overwrite immutable result: {target}')
        target.write_bytes(content)
    render_reports(root)
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
