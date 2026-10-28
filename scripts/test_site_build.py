"""Deployment contracts: subpath links, indexing, and immutable benchmark evidence."""
import contextlib
import io
import json
import struct
import tempfile
import unittest
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urljoin, urlsplit
from xml.etree import ElementTree as ET

import bench_report
import site_build
from lab.build import assemble
from site_layout import ROOT, SITE
from test_bench_publish import fixture


class Document(HTMLParser):
    def __init__(self, content):
        super().__init__(convert_charrefs=True)
        self.ids = []
        self.links = []
        self.references = []
        self.meta = {}
        self.canonical = []
        self.titles = []
        self.headings = 0
        self.schemas = []
        self.capture = None
        self.buffer = []
        self.feed(content)

    def handle_starttag(self, tag, attributes):
        attrs = dict(attributes)
        if 'id' in attrs:
            self.ids.append(attrs['id'])
        for name in ('href', 'src'):
            if attrs.get(name):
                self.links.append(attrs[name])
        for name in ('aria-controls', 'aria-labelledby', 'data-copy'):
            self.references.extend(attrs.get(name, '').split())
        if tag == 'meta':
            self.meta[attrs.get('name', attrs.get('property'))] = attrs.get('content')
        if tag == 'link' and attrs.get('rel') == 'canonical':
            self.canonical.append(attrs['href'])
        if tag == 'h1':
            self.headings += 1
        if tag == 'title' or (tag == 'script' and attrs.get('type') == 'application/ld+json'):
            self.capture = tag
            self.buffer = []

    def handle_data(self, data):
        if self.capture:
            self.buffer.append(data)

    def handle_endtag(self, tag):
        if tag == self.capture:
            value = ''.join(self.buffer)
            if tag == 'title':
                self.titles.append(value)
            else:
                self.schemas.append(json.loads(value))
            self.capture = None


class SiteBuild(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.measurements = self.root / 'published'
        for run in (2, 1):  # Publish out of order, like concurrent benchmark jobs.
            results = self.root / f'results-{run}'
            fixture(results, run=run)
            bench_report.install(results, self.measurements)

    def build(self, output, base_url, measurements=None):
        with contextlib.redirect_stdout(io.StringIO()):
            return site_build.build(output, measurements, base_url)

    def assert_site_links(self, output, base_url):
        documents = {path.relative_to(output).as_posix(): Document(path.read_text())
                     for path in output.rglob('*.html')}
        origin = urlsplit(base_url)
        titles = []
        for name, document in documents.items():
            with self.subTest(page=name):
                self.assertEqual(document.headings, 1)
                self.assertEqual(len(document.ids), len(set(document.ids)), 'Duplicate IDs')
                self.assertTrue(set(document.references) <= set(document.ids), 'Missing interactive target')
                self.assertEqual(len(document.titles), 1)
                titles.extend(document.titles)
                path = name.removesuffix('index.html')
                self.assertEqual(document.canonical, [base_url + path])
                self.assertEqual(document.meta['og:url'], base_url + path)
                self.assertEqual(document.meta['og:image'], base_url + 'assets/social.png')
                self.assertTrue(document.meta['description'])
                self.assertTrue(document.schemas)
                self.assertNotIn('{{', (output / name).read_text())
                for link in document.links:
                    target = urlsplit(urljoin(base_url + path, link))
                    if (target.scheme, target.netloc) != (origin.scheme, origin.netloc):
                        continue
                    self.assertTrue(target.path.startswith(origin.path), f'Escaped project path: {link}')
                    target_name = unquote(target.path[len(origin.path):])
                    target_file = output / target_name
                    if target_file.is_dir():
                        target_file /= 'index.html'
                    self.assertTrue(target_file.is_file(), f'{name}: missing {link}')
                    if target.fragment and target_file.suffix == '.html':
                        resolved = target_file.relative_to(output).as_posix()
                        self.assertIn(unquote(target.fragment), documents[resolved].ids, f'{name}: missing anchor {link}')
        self.assertEqual(len(titles), len(set(titles)), 'Every page should have its own search title')
        return documents

    def test_project_and_custom_domain_builds_keep_all_links_and_evidence(self):
        (self.measurements / 'CNAME').write_text('docs.example.test')
        before = {p.relative_to(self.measurements): p.read_bytes()
                  for p in self.measurements.rglob('*') if p.is_file()}
        (self.measurements / 'private-source.txt').write_text('not a public asset')
        for index, base_url in enumerate(('https://example.test/bruster/', 'https://docs.example.test/')):
            output = self.root / f'site-{index}'
            history = self.build(output, base_url, self.measurements)
            documents = self.assert_site_links(output, base_url)
            self.assertEqual([r['context']['run_number'] for r in history], [2, 1])
            self.assertFalse((output / 'private-source.txt').exists())
            self.assertEqual((output / 'CNAME').read_text(), 'docs.example.test')
            for name, content in before.items():
                self.assertEqual((self.measurements / name).read_bytes(), content, 'Input checkout was modified')
                if name.suffix in ('.json', '.md'):
                    self.assertEqual((output / name).read_bytes(), content, 'Published evidence was altered')
            sitemap = ET.parse(output / 'sitemap.xml')
            locations = [item.text for item in sitemap.findall('.//{*}loc')]
            self.assertEqual(set(locations), {base_url + path for path in ('', 'docs/', 'mcp/', 'compare/', 'benchmarks/')})
            for name, document in documents.items():
                archived = '/runs/' in name or name == '404.html'
                self.assertEqual('noindex' in document.meta['robots'], archived)
            self.assertEqual((output / 'robots.txt').exists(), index == 1)
            if index == 1:
                self.assertIn(base_url + 'sitemap.xml', (output / 'robots.txt').read_text())
            self.assertEqual(struct.unpack('>II', (output / 'assets/social.png').read_bytes()[16:24]), (1200, 630))
            self.assertEqual((output / 'assets/logo.svg').read_bytes(), (ROOT / 'assets/logo.svg').read_bytes())
            self.assertIn('selector|ref', (output / 'docs/index.html').read_text())

    def test_empty_preview_has_working_navigation_and_no_fake_measurements(self):
        output = self.root / 'empty'
        history = self.build(output, 'https://example.test/bruster/')
        self.assertEqual(history, [])
        documents = self.assert_site_links(output, 'https://example.test/bruster/')
        self.assertIn('noindex', documents['benchmarks/index.html'].meta['robots'])
        self.assertIn('after the first successful benchmark run', (output / 'index.html').read_text())
        self.assertNotIn('https://example.test/bruster/benchmarks/', (output / 'sitemap.xml').read_text())

    def test_test_lab_assembly_preserves_product_pages_and_benchmark_evidence(self):
        output, published = self.root / 'product', self.root / 'combined'
        base_url = 'https://example.test/bruster/'
        self.build(output, base_url, self.measurements)
        manifest = assemble(output, published)
        self.assertGreaterEqual(len(manifest['cases']), 300)
        home = (published / 'index.html').read_text()
        self.assertEqual(home.count('data-bruster-test-lab'), 1)
        self.assertIn('Browser automation.<br>', home)
        self.assertEqual(Document(home).canonical, [base_url])
        for name in ('sitemap.xml', 'docs/index.html', 'benchmarks/latest.json', 'benchmarks/history.json'):
            self.assertEqual((published / name).read_bytes(), (output / name).read_bytes())
        self.assertTrue((published / 'test-lab/index.html').is_file())
        self.assertTrue((published / 'test-lab/manifest.json').is_file())

    def test_rejects_output_over_source_and_missing_measurement_input(self):
        for path in (ROOT, SITE, SITE / 'generated'):
            with self.subTest(path=path), self.assertRaises(ValueError):
                self.build(path, 'https://example.test/')
        with self.assertRaisesRegex(ValueError, 'must be separate'):
            self.build(self.measurements, 'https://example.test/', self.measurements)
        with self.assertRaisesRegex(ValueError, 'Missing published benchmarks'):
            self.build(self.root / 'missing', 'https://example.test/', self.root / 'does-not-exist')


if __name__ == '__main__':
    unittest.main()
