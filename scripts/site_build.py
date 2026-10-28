#!/usr/bin/env python3
"""Build the product site and refresh benchmark HTML from published measurements."""
import argparse
import html
import re
import shutil
import tomllib
from datetime import datetime
from pathlib import Path
from urllib.parse import urlsplit
from xml.etree import ElementTree as ET

from bench_report import render_reports
from site_layout import ROOT, SITE, SITE_URL, render_page, site_url, substitute


PAGES = (
    ('', 'Bruster — Native Browser Automation for Scripts & Tests',
     'Automate native browsers with a small Rust controller. JSON-lines API, built-in MCP, '
     'and reproducible benchmarks. macOS, Linux, Windows. No Node.js required.', ''),
    ('docs/', 'Bruster Docs — Install, Docker, Python & Browser API',
     'Install Bruster or run its Docker image. Automate a browser with Python, JSON lines, '
     'or MCP. Platform setup, container commands, CLI options, and browser API.', 'Docs'),
    ('mcp/', 'Browser MCP Server Setup — Bruster',
     'Connect Bruster’s native browser MCP server to OpenCode, Claude Code, Cursor, Codex, '
     'or VS Code. Native and Docker configurations, browser tools, and troubleshooting.', 'MCP setup'),
    ('compare/', 'Bruster vs Playwright & Puppeteer — Browser Automation',
     'Compare Bruster, Playwright, and Puppeteer for browser automation and testing: '
     'engines, APIs, runtime requirements, limitations, and reproducible benchmarks.', 'Compare'),
)


def readme_table(heading, caption):
    """Render the two simple reference tables directly from their maintained source."""
    section = (ROOT / 'README.md').read_text().split(f'\n## {heading}\n', 1)[1].split('\n## ', 1)[0]
    lines = [line for line in section.splitlines() if line.startswith('|')]
    rows = [re.split(r'(?<!\\)\|', line.strip().strip('|')) for line in lines]
    if len(rows) < 3 or any(len(row) != len(rows[0]) for row in rows):
        raise ValueError(f'Invalid {heading} table in README.md')

    def inline(text):
        escaped = html.escape(text.strip().replace('\\|', '|'))
        return re.sub(r'`([^`]+)`', r'<code>\1</code>', escaped)

    label = html.escape(caption, quote=True)
    parts = [f'<div class="table-scroll" role="region" aria-label="{label}" tabindex="0">',
             f'<table class="api-table"><caption class="sr-only">{label}</caption><thead><tr>']
    parts.extend(f'<th scope="col">{inline(cell)}</th>' for cell in rows[0])
    parts.append('</tr></thead><tbody>')
    for row in rows[2:]:
        parts.append('<tr>' + ''.join(f'<td>{inline(cell)}</td>' for cell in row) + '</tr>')
    parts.append('</tbody></table></div>')
    return '\n'.join(parts)


def benchmark_preview(history):
    if not history:
        return ('<div class="benchmark-empty"><h3>Reproducible by design.</h3>'
                '<p>Published measurements will appear here after the first successful benchmark run.</p></div>')
    record = history[0]
    stats = record['summary']['bruster']
    metrics = (
        ('Launch → first loaded page', stats['launch_to_first_page_ms']['median'], 'ms', 'Median, including first navigation'),
        ('Idle process-tree memory', stats['total_pss_mib']['median'], 'MiB', 'Total PSS, including the Xvfb display'),
        ('Installed runtime files', record['footprint']['tool_totals']['bruster']['bytes'] / 1e6, 'MB', 'Lower bound, including native dependencies'),
    )
    parts = ['<dl class="benchmark-preview">']
    for name, value, unit, note in metrics:
        parts.append(f'<div class="metric-card"><dt>{name}</dt><dd>{value:,.1f} <span>{unit}</span></dd><dd class="metric-note">{note}</dd></div>')
    parts.append('</dl>')
    date = datetime.fromisoformat(record['metadata']['finished_utc'].replace('Z', '+00:00')).strftime('%d %b %Y')
    parts.append(f'<p class="benchmark-caption">Bruster / WebKitGTK · Linux · {date} · '
                 f'{record["metadata"]["rounds"]} sessions. Memory includes Xvfb; installed size is a lower bound. '
                 'See all configurations, ranges, versions, and conditions in the full report.</p>')
    return '\n'.join(parts)


def write_page(output, path, content):
    target = output / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding='utf-8')


def build(output, measurements=None, base_url=SITE_URL):
    base_url = site_url(base_url)
    output = output.resolve()
    if output == ROOT or ROOT.is_relative_to(output) or output.is_relative_to(SITE):
        raise ValueError('Choose an output directory separate from the source files')
    output.mkdir(parents=True, exist_ok=True)
    if measurements is not None:
        measurements = measurements.resolve()
        if output.is_relative_to(measurements) or measurements.is_relative_to(output):
            raise ValueError('Output and measurement input directories must be separate')
        source = measurements / 'benchmarks'
        if not source.is_dir():
            raise ValueError(f'Missing published benchmarks directory: {source}')
        shutil.copytree(source, output / 'benchmarks', dirs_exist_ok=True)
        if (measurements / 'CNAME').is_file():
            shutil.copyfile(measurements / 'CNAME', output / 'CNAME')
    history = render_reports(output / 'benchmarks', base_url=base_url)
    shutil.copytree(SITE / 'assets', output / 'assets', dirs_exist_ok=True)
    shutil.copyfile(ROOT / 'assets/logo.svg', output / 'assets/logo.svg')
    base = html.escape(urlsplit(base_url).path, quote=True)
    version = tomllib.loads((ROOT / 'Cargo.toml').read_text())['package']['version']
    values = {
        'base': base, 'version': 'v' + html.escape(version),
        'api_table': readme_table('API', 'Browser methods, parameters, and results'),
        'flags_table': readme_table('Run', 'Command-line flags and their effects'),
        'benchmark_preview': benchmark_preview(history),
    }
    for path, title, description, section in PAGES:
        fragment = substitute((SITE / path / 'index.html').read_text(), values)
        write_page(output, path + 'index.html', render_page(
            title, description, path, fragment, base_url=base_url, section=section, application=not path))
    if not history:
        method = ('<main id="main" class="container article-layout prose"><header class="page-intro">'
                  '<p class="eyebrow">Evidence, included</p><h1>Browser benchmarks.</h1>'
                  '<p class="lead">Measurements have not been published yet.</p></header>'
                  '<section id="method"><h2>Reproducible measurements</h2><p>The suite compares Bruster, '
                  'Playwright, Puppeteer, and agent-browser across startup, navigation, extraction, '
                  'screenshots, memory, runtime footprint, and reliability.</p>'
                  '<p><a href="https://github.com/aliilyas/bruster/blob/main/benchmarks/README.md">'
                  'Read the setup and methodology →</a></p></section></main>')
        write_page(output, 'benchmarks/index.html', render_page(
            'Browser Benchmarks — Bruster', 'Browser automation benchmark setup and methodology.',
            'benchmarks/', method, base_url=base_url, section='Benchmarks', noindex=True))
    not_found = (f'<main id="main" class="container not-found"><p class="eyebrow">404 / Page not found</p>'
                 '<h1>This page took a different route.</h1><p>Find your way back to the project, '
                 'or jump into the documentation.</p><div class="hero-actions">'
                 f'<a class="button" href="{base}">Back to bruster →</a>'
                 f'<a class="text-link" href="{base}docs/">Open the docs →</a></div></main>')
    write_page(output, '404.html', render_page('Page Not Found — Bruster', 'Find Bruster documentation and browser automation tools.',
               '404.html', not_found, base_url=base_url, noindex=True))
    paths = [page[0] for page in PAGES] + (['benchmarks/'] if history else [])
    ET.register_namespace('', 'http://www.sitemaps.org/schemas/sitemap/0.9')
    namespace = '{http://www.sitemaps.org/schemas/sitemap/0.9}'
    sitemap = ET.Element(namespace + 'urlset')
    for path in paths:
        url = ET.SubElement(sitemap, namespace + 'url')
        ET.SubElement(url, namespace + 'loc').text = base_url + path
    ET.ElementTree(sitemap).write(output / 'sitemap.xml', encoding='utf-8', xml_declaration=True)
    # Crawlers only consult /robots.txt at the origin, not /bruster/robots.txt.
    if urlsplit(base_url).path == '/':
        write_page(output, 'robots.txt', f'User-agent: *\nAllow: /\nSitemap: {base_url}sitemap.xml\n')
    (output / '.nojekyll').touch()
    print(f'Built {len(PAGES) + 2 + len(history)} HTML pages in {output}; {len(history)} benchmark runs.')
    return history


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--measurements', type=Path, help='Checkout of the gh-pages branch (optional for previews)')
    parser.add_argument('--base-url', default=SITE_URL, help='Public URL including the project path, or a local preview URL')
    args = parser.parse_args()
    build(args.output, args.measurements, args.base_url)


if __name__ == '__main__':
    main()
