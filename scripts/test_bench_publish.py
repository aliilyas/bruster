"""Publication contracts: reject misleading data and preserve published results."""
import copy
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import bench_publish
import bench_report as report
from bench_compare import ProcessClient
from bench_tools import CATALOG, LINUX_TOOLS


def fixture(root, run=1, attempt=1, tools=None):
    root.mkdir(parents=True, exist_ok=True)
    lock = '{"lockfileVersion":3}\n'
    (root / 'package.json').write_text('{"private":true}\n')
    (root / 'package-lock.json').write_text(lock)
    metadata = {'rounds': 1, 'iterations': 2, 'finished_utc': '2026-10-27T00:00:00+00:00',
                'packages': {'playwright-core': 'test', 'puppeteer-core': 'test', 'agent-browser': 'test'},
                'chrome': 'Chrome test', 'node': 'test',
                'package_lock_sha256': hashlib.sha256(lock.encode()).hexdigest()}
    rows = []
    if tools is not None:
        metadata.update(tools=tools, competitors=copy.deepcopy(CATALOG))
    selected = list(report.LABELS) if tools is None else tools
    for tool in selected:
        display = [{'pss_kib': 1024, 'rss_kib': 2048}] if tool == 'bruster' else []
        sample = {'complete': True, 'processes': [{'pss_kib': 2048, 'rss_kib': 4096}], 'display': display,
                  'pss_mib': 2, 'rss_mib': 4, 'display_pss_mib': len(display),
                  'total_pss_mib': 2 + len(display), 'process_count': 1}
        row = {'tool': tool, 'round': 1, 'large_extract_sha256': 'a' * 64,
               'competing_before': [], 'competing_at_memory': [], 'competing_after': [],
               'image_requests': 36, 'delayed_validation_ms': 251,
               'browser_info': {'width': 1280, 'height': 800, 'state': 'complete'},
               'idle_memory': [copy.deepcopy(sample) for _ in range(3)],
               'failures': [], 'cleanup_forced_processes': [],
               'failure_checks': [{'name': name, 'pass': True} for name in (
                   'javascript_exception', 'javascript_syntax_error', 'recovery_after_javascript_errors',
                   'connection_refused', 'recovery_after_navigation_error')]}
        row.update({key: 10 for key in report.SCALARS})
        row.update({key: [10, 20] for key in ('tiny_navigation_ms', 'tiny_extract_ms', 'screenshot_ms')})
        row.update({key: [10] * 5 for key in ('large_navigation_ms', 'large_extract_ms', 'large_extract_json_ms')})
        row['image_navigation_ms'] = [10] * 3
        rows.append(row)
    footprint = {'tool_totals': {t: {'bytes': 2_000_000, 'files': 1} for t in selected},
                 'file_inventory': {t: [{'path': '/test/runtime', 'bytes': 2_000_000}] for t in selected}}
    for name, data in (('summary.json', {'metadata': metadata}), ('samples.json', rows), ('footprint.json', footprint)):
        report.write_json(root / name, data)
    context = {'repository': 'owner/project', 'sha': f'{run:040x}', 'run_id': run, 'run_number': run,
               'run_attempt': attempt, 'run_url': f'https://github.com/owner/project/actions/runs/{run}'}
    report.prepare(root, context)
    return metadata, rows, footprint, context


class Reports(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.results = self.root / 'results'
        self.metadata, self.rows, self.footprint, self.context = fixture(self.results)

    def test_rejects_incomplete_contaminated_or_invalid_measurements(self):
        mutations = [
            lambda rows: rows.pop(),
            lambda rows: rows.append(rows[0]),
            lambda rows: rows[0]['tiny_navigation_ms'].__setitem__(0, -1),
            lambda rows: rows[0]['tiny_navigation_ms'].__setitem__(0, float('nan')),
            lambda rows: rows[0].__setitem__('large_extract_sha256', 'b' * 64),
            lambda rows: rows[0]['competing_at_memory'].append({'pid': 123, 'name': 'rustc'}),
            lambda rows: rows[0]['idle_memory'][0].__setitem__('complete', False),
            lambda rows: rows[0]['idle_memory'][0].__setitem__('display', []),
            lambda rows: rows[0]['idle_memory'][0].__setitem__('total_pss_mib', 3000),
            lambda rows: rows[0].__setitem__('failure_checks', []),
        ]
        for mutate in mutations:
            with self.subTest(mutate=mutate):
                rows = copy.deepcopy(self.rows)
                mutate(rows)
                with self.assertRaises(ValueError):
                    report.validate(self.metadata, rows, self.footprint)

    def test_retry_preserves_failure_and_units(self):
        row = self.rows[1]
        failure = {'name': 'recovery_after_navigation_error', 'pass': False, 'error': 'interrupted'}
        row['failures'].append(failure)
        row['failure_checks'][-1] = failure
        row['failure_checks'].append({'name': 'navigation_recovery_retry_100ms', 'pass': True})
        report.write_json(self.results / 'samples.json', self.rows)
        record = report.prepare(self.results, self.context)
        stat = record['summary']['playwright-shell']
        self.assertEqual(stat['sessions_with_failures'], 1)
        self.assertEqual(stat['recovery_retry_passes'], 1)
        table = dict((r[0], r[1:]) for r in report.table_rows(record))
        self.assertEqual(table['Installed runtime files, lower bound (MB)'], ['2.0'] * 5)
        self.assertEqual(table['Idle total PSS, including display (MiB)'],
                         ['3.0 [3.0–3.0]'] + ['2.0 [2.0–2.0]'] * 4)

    def test_startup_phases_ranges_and_lifecycle_failures(self):
        row = self.rows[0]
        row.update(startup_ms=30_000, first_navigation_ms=500, launch_to_first_page_ms=30_500)
        row['failures'].append({'name': 'graceful_close', 'pass': False, 'error': 'close refused'})
        report.write_json(self.results / 'samples.json', self.rows)
        record = report.prepare(self.results, self.context)
        stats = record['summary']['bruster']
        self.assertEqual(stats['sessions_with_failures'], 1)
        self.assertEqual(stats['fault_probe_failures'], {})
        self.assertEqual(stats['lifecycle_failures'], {'graceful_close': 1})
        table = {r[0]: r[1:] for r in report.table_rows(record)}
        self.assertEqual(table['Startup → ready / blank-page setup (ms)'][0], '30000.0 [30000.0–30000.0]')
        self.assertEqual(table['First navigation after setup (ms)'][0], '500.0 [500.0–500.0]')
        self.assertEqual(table['Warm tiny-page navigation (ms)'][0], '15.0 [10.0–20.0]')

    def test_lockfile_identity(self):
        (self.results / 'package-lock.json').write_text('{}\n')
        with self.assertRaisesRegex(ValueError, 'lockfile changed'):
            report.prepare(self.results, self.context)

    def test_history_is_ordered_by_invocation_not_finish_or_publication(self):
        site, newer = self.root / 'site', self.root / 'newer'
        fixture(newer, run=2)
        report.install(newer, site)
        report.install(self.results, site)
        latest = json.loads((site / 'benchmarks/latest.json').read_text())
        self.assertEqual(latest['context']['run_number'], 2)
        self.assertEqual(len(json.loads((site / 'benchmarks/history.json').read_text())), 2)
        report.install(self.results, site)  # Idempotent republishing.
        (self.results / 'samples.json').write_text('changed')
        with self.assertRaisesRegex(ValueError, 'immutable'):
            report.install(self.results, site)

    def test_preserves_site_and_migrates_only_known_legacy_metrics(self):
        site = self.root / 'site'
        site.mkdir()
        (site / 'CNAME').write_text('example.test')
        (site / 'index.html').write_text('docs<h2 id="performance">Performance</h2>scripts/bench.py'
                                         '<h2 id="development">Development</h2>more docs')
        report.install(self.results, site)
        content = (site / 'index.html').read_text()
        self.assertIn('href="benchmarks/"', content)
        self.assertTrue(content.startswith('docs'))
        self.assertTrue(content.endswith('more docs'))
        self.assertEqual((site / 'CNAME').read_text(), 'example.test')
        self.assertTrue((site / '.nojekyll').is_file())

    def test_local_publication_is_labeled_and_future_workflows_supersede_it(self):
        local, site = self.root / 'local', self.root / 'site'
        fixture(local, tools=LINUX_TOOLS)
        evidence = b'local raw evidence'
        (local / 'evidence.tar.gz').write_bytes(evidence)
        context = {'repository': 'owner/project', 'sha': 'a' * 40, 'harness_sha': 'b' * 40,
                   'local_validation': True, 'local_id': '20261101T180138Z',
                   'published_utc': '2026-11-01T19:00:00+00:00', 'after_workflow_run_number': 1,
                   'evidence_sha256': hashlib.sha256(evidence).hexdigest()}
        record = report.prepare(local, context)
        report.install(self.results, site)
        report.install(local, site)
        root = site / 'benchmarks'
        latest = json.loads((root / 'latest.json').read_text())
        self.assertTrue(latest['context']['local_validation'])
        page = (root / 'index.html').read_text()
        self.assertIn('Local validation · 1 session(s) per configuration', page)
        self.assertIn('evidence.tar.gz', page)
        self.assertNotIn('Workflow #', page)
        self.assertIn(f'/blob/{context["harness_sha"]}/benchmarks/README.md', page)
        archive = root / 'runs' / report.record_id(record)
        self.assertEqual((archive / 'evidence.tar.gz').read_bytes(), evidence)
        self.assertIn('Local validation', (local / 'report.md').read_text())
        self.assertNotIn('[workflow run]', (local / 'report.md').read_text())
        newer = self.root / 'next-workflow'
        fixture(newer, run=2, tools=LINUX_TOOLS)
        report.install(newer, site)
        report.install(self.results, site)  # An older workflow finishing late cannot win.
        latest = json.loads((root / 'latest.json').read_text())
        self.assertEqual(latest['context']['run_number'], 2)
        history = json.loads((root / 'history.json').read_text())
        self.assertTrue(history[1]['local_validation'])
        (local / 'evidence.tar.gz').write_bytes(b'changed evidence')
        with self.assertRaisesRegex(ValueError, 'evidence archive changed'):
            report.prepare(local, context)
        with self.assertRaisesRegex(ValueError, 'immutable'):
            report.install(local, site)

    def test_html_escapes_provenance(self):
        record = json.loads((self.results / 'measurement.json').read_text())
        record['metadata']['chrome'] = '<script>alert(1)</script>'
        page = report.page(record)
        self.assertNotIn(record['metadata']['chrome'], page)
        self.assertIn('&lt;script&gt;alert(1)&lt;/script&gt;', page)

    def test_new_competitors_and_old_history_keep_their_own_columns(self):
        newer, site = self.root / 'expanded', self.root / 'site'
        fixture(newer, run=2, tools=LINUX_TOOLS)
        report.install(self.results, site)
        report.install(newer, site)
        root = site / 'benchmarks'
        old = (root / 'runs' / report.record_id({'context': self.context}) / 'index.html').read_text()
        latest = (root / 'index.html').read_text()
        self.assertIn('colspan="6"', old)
        self.assertNotIn('Stagehand', old)
        self.assertIn(f'colspan="{len(LINUX_TOOLS) + 1}"', latest)
        self.assertIn('Playwright MCP', latest)
        self.assertIn('https://github.com/bensyverson/sleepyhollow', latest)
        self.assertIn('macos-timing', latest)
        self.assertIn('Rustwright MCP', latest)
        record = json.loads((newer / 'measurement.json').read_text())
        self.assertEqual(set(record['summary']), set(LINUX_TOOLS))
        self.assertNotIn('sleepyhollow', record['summary'])
        self.assertEqual(len(next(report.table_rows(record))), len(LINUX_TOOLS) + 1)

    def test_subset_is_explicit_and_missing_or_unknown_tools_are_rejected(self):
        subset = self.root / 'subset'
        tools = ['stagehand', 'playwright-mcp']
        metadata, rows, footprint, _ = fixture(subset, tools=tools)
        record = json.loads((subset / 'measurement.json').read_text())
        self.assertEqual(set(record['summary']), set(tools))
        self.assertIn('colspan="3"', report.page(record))
        for invalid in ([], tools + ['stagehand'], tools + ['sleepyhollow'], ['invented-tool']):
            with self.subTest(tools=invalid), self.assertRaises(ValueError):
                report.validate(dict(metadata, tools=invalid), rows, footprint)
        with self.assertRaisesRegex(ValueError, 'Missing'):
            report.validate(metadata, rows[:-1], footprint)
        del footprint['tool_totals']['stagehand']
        with self.assertRaisesRegex(ValueError, 'inventories'):
            report.validate(metadata, rows, footprint)


class ProcessLifecycle(unittest.TestCase):
    def test_shutdown_failure_is_recorded_and_process_reaped(self):
        for refuse_close in (False, True):
            with self.subTest(refuse_close=refuse_close):
                child = '''
import json, sys
print(json.dumps({'event': 'ready'}), flush=True)
for line in sys.stdin:
    request = json.loads(line)
    reply = {'id': request['id']}
    if REFUSE:
        reply['error'] = 'close refused'
    else:
        reply['result'] = None
    print(json.dumps(reply), flush=True)
    if not REFUSE:
        break
'''.replace('REFUSE', str(refuse_close))
                client = ProcessClient([sys.executable, '-u', '-c', child], chromium=True)
                client.close()
                self.assertIsNotNone(client.proc.poll())
                if refuse_close:
                    self.assertIn('close refused', client.close_error)
                    self.assertLess(client.proc.returncode, 0)
                else:
                    self.assertIsNone(client.close_error)
                    self.assertEqual(client.proc.returncode, 0)


class GitPublication(unittest.TestCase):
    def test_creation_race_retry_and_existing_site_preservation(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            remote, repo, other = (root / name for name in ('remote.git', 'repo', 'other'))
            subprocess.run(['git', 'init', '--bare', str(remote)], check=True, capture_output=True)
            subprocess.run(['git', 'init', str(repo)], check=True, capture_output=True)
            git = bench_publish.git
            (repo / 'source.txt').write_text('source checkout remains intact')
            git(repo, 'add', '.')
            git(repo, 'commit', '-m', 'source')
            git(repo, 'remote', 'add', 'origin', str(remote))
            git(repo, 'push', 'origin', 'HEAD:main')
            subprocess.run(['git', 'clone', '-b', 'main', str(remote), str(other)], check=True, capture_output=True)
            initial, older, newer = (root / name for name in ('initial', 'older', 'newer'))
            fixture(initial, run=1)
            fixture(older, run=2)
            fixture(newer, run=3)
            bench_publish.publish(repo, initial, root / 'first-site')  # Branch does not yet exist.
            git(other, 'fetch', 'origin', 'gh-pages')
            git(other, 'checkout', '--detach', 'FETCH_HEAD')
            (other / 'CNAME').write_text('custom.example')
            git(other, 'add', 'CNAME')
            git(other, 'commit', '-m', 'custom domain')
            git(other, 'push', 'origin', 'HEAD:gh-pages')
            raced = False

            def racing_git(directory, *args, **kwargs):
                nonlocal raced
                if args[0] == 'push' and Path(directory) == root / 'older-site' and not raced:
                    raced = True
                    bench_publish.publish(other, newer, root / 'newer-site')
                return git(directory, *args, **kwargs)

            with patch.object(bench_publish, 'git', racing_git), patch.object(bench_publish.time, 'sleep'):
                bench_publish.publish(repo, older, root / 'older-site')
            self.assertTrue(raced)
            git(repo, 'fetch', 'origin', 'gh-pages')
            latest = json.loads(git(repo, 'show', 'FETCH_HEAD:benchmarks/latest.json').stdout)
            history = json.loads(git(repo, 'show', 'FETCH_HEAD:benchmarks/history.json').stdout)
            self.assertEqual(latest['context']['run_number'], 3)
            self.assertEqual([r['run_number'] for r in history], [3, 2, 1])
            self.assertEqual(git(repo, 'show', 'FETCH_HEAD:CNAME').stdout, 'custom.example')
            self.assertEqual((repo / 'source.txt').read_text(), 'source checkout remains intact')
            self.assertFalse((root / 'older-site').exists())


if __name__ == '__main__':
    unittest.main()
