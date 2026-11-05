"""Course contracts: a complete reading path and examples that match the tested files."""
import contextlib
import io
import tempfile
import unittest
import zipfile
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit

import site_build
from site_layout import ROOT


class Lesson(HTMLParser):
    def __init__(self, content):
        super().__init__(convert_charrefs=True)
        self.previous = []
        self.next = []
        self.downloads = []
        self.code = {}
        self.capture = None
        self.feed(content)

    def handle_starttag(self, tag, attributes):
        attrs = dict(attributes)
        if tag == 'a':
            if attrs.get('rel') == 'prev':
                self.previous.append(attrs['href'])
            if attrs.get('rel') == 'next':
                self.next.append(attrs['href'])
            if 'download' in attrs:
                self.downloads.append(attrs['href'])
        if tag == 'code' and attrs.get('id', '').startswith('example-'):
            self.capture = attrs['id'].removeprefix('example-') + '.bru'
            self.code[self.capture] = ''

    def handle_data(self, text):
        if self.capture:
            self.code[self.capture] += text

    def handle_endtag(self, tag):
        if tag == 'code':
            self.capture = None


class LearningSite(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.output = Path(self.temp.name) / 'site'
        self.prefix = '/nested/bruster/'
        with contextlib.redirect_stdout(io.StringIO()):
            site_build.build(self.output, base_url='https://example.test' + self.prefix)
        self.pages = {self.prefix + file.relative_to(self.output).as_posix().removesuffix('index.html'):
                      Lesson(file.read_text(encoding='utf-8'))
                      for file in (self.output / 'learn-testin').rglob('index.html')}

    def test_twenty_lessons_form_one_complete_bidirectional_path(self):
        self.assertEqual(len(self.pages), 20)
        visited = []
        current = self.prefix + 'learn-testin/'
        while current:
            self.assertNotIn(current, visited, 'Course navigation contains a cycle')
            lesson = self.pages[current]
            self.assertEqual(lesson.previous, visited[-1:] if visited else [])
            visited.append(current)
            self.assertLessEqual(len(lesson.next), 1)
            current = lesson.next[0] if lesson.next else None
        self.assertEqual(set(visited), set(self.pages), 'Some lessons cannot be reached with Next')
        self.assertTrue(visited[-1].endswith('/your-first-testing-project/'))

    def test_downloads_zip_and_displayed_code_match_executable_examples(self):
        sources = {path.name: path.read_text(encoding='utf-8')
                   for path in (ROOT / 'example-tests/learn-testin').glob('*.bru')}
        self.assertEqual(len(sources), 8)
        shown = set()
        for lesson in self.pages.values():
            for name, code in lesson.code.items():
                self.assertEqual(code, sources[name].rstrip(), f'Stale displayed example: {name}')
                shown.add(name)
            for link in lesson.downloads:
                path = urlsplit(link).path
                self.assertTrue(path.startswith(self.prefix))
                self.assertTrue((self.output / path[len(self.prefix):]).is_file(), link)
        self.assertEqual(shown, set(sources))
        with zipfile.ZipFile(self.output / 'learn-testin/practice-files.zip') as archive:
            self.assertEqual(set(archive.namelist()), {*sources, 'READ-ME.txt'})
            for name, source in sources.items():
                self.assertEqual(archive.read(name).decode(), source)
                self.assertEqual((self.output / 'example-tests/learn-testin' / name).read_text(), source)
            self.assertIn(self.prefix + 'learn-testin/', archive.read('READ-ME.txt').decode())


if __name__ == '__main__':
    unittest.main()
