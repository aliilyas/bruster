"""Render the twenty-page, beginner-friendly learning site without build dependencies."""
import html
import shutil
import zipfile
from urllib.parse import urlsplit

from site_layout import ROOT, SITE, article_byline, render_metadata, site_url, substitute


COURSE_PATH = 'learn-testin/'
SOURCE = SITE / COURSE_PATH
# The start page is lesson one: exactly twenty reading pages, not twenty plus an index.
LESSONS = (
    ('', 'Start here', 'Learn website testing, one small step at a time',
     'A free, twenty-lesson course for people new to website testing. Learn with clear explanations, a practice form, and downloadable Bruster tests.'),
    ('what-a-test-checks/', 'What a test checks', 'What does a website test actually check?',
     'Understand actions, expected results, and actual results using a simple website form. No programming experience needed.'),
    ('meet-the-practice-page/', 'Meet the practice page', 'Get to know your practice website',
     'Try the Bruster practice form by hand. Learn what its text fields, dropdown, checkbox, preview, and receipt do.'),
    ('write-a-test-plan/', 'Write a small test plan', 'Make a plan before you automate',
     'Turn a website task into a small test plan with starting conditions, steps, and a clear expected result.'),
    ('set-up-bruster/', 'Set up Bruster', 'Get a test-ready copy of Bruster',
     'Set up the Bruster test runner on macOS, Windows, or Linux. Understand the terminal, source builds, and the help check.'),
    ('make-a-test-file/', 'Make a test file', 'Create a folder and your first test file',
     'Save a plain-text .bru file, avoid hidden file extensions, and organize a small practice folder for website tests.'),
    ('run-your-first-test/', 'Run your first test', 'Run a test and read the result',
     'Run your first Bruster test step by step, watch the browser, and understand a passing result and report folder.'),
    ('understand-the-commands/', 'Read the test commands', 'Understand every line of your first test',
     'Read base_url, test, navigate, expect title, and end in plain English. Learn the small rules of a Bruster test file.'),
    ('find-the-right-element/', 'Find the right element', 'Tell the browser which thing you mean',
     'Learn simple CSS selectors using visible IDs on the practice page. Find text fields, buttons, and result messages.'),
    ('fill-and-submit-a-form/', 'Fill and submit a form', 'Let the browser fill in a form',
     'Use fill and click to complete a form, then check its receipt. Follow a complete, downloadable Bruster example.'),
    ('check-the-result/', 'Check the result', 'Check that the right thing happened',
     'Choose useful assertions for text, visibility, and page titles. Understand the difference between exact and partial text checks.'),
    ('test-dropdowns-and-checkboxes/', 'Dropdowns and checkboxes', 'Test choices as well as text',
     'Test dropdown options and checkbox states with select, check, and uncheck, then verify their effect in a receipt.'),
    ('test-required-fields/', 'Required fields', 'Check what happens when information is missing',
     'Test required fields, blocked submissions, and recovery after a mistake with two small Bruster examples.'),
    ('keep-tests-independent/', 'Independent tests', 'Give every test a clean starting point',
     'Use before_each and fresh browser sessions to keep tests independent. Learn why tests should not rely on a previous test.'),
    ('wait-without-guessing/', 'Waiting and timeouts', 'Wait for a result without guessing',
     'Understand retrying assertions and per-step timeouts. Learn why checking a result is more reliable than a fixed pause.'),
    ('save-screenshots-and-reports/', 'Screenshots and reports', 'Keep useful evidence from a test run',
     'Save screenshots, locate results.json, and use failure evidence to explain what happened during a website test.'),
    ('fix-a-failing-test/', 'Fix a failing test', 'Read a failure and find the next step',
     'Create a harmless practice failure, read the message, and fix it. Work through common file, selector, and connection problems.'),
    ('test-your-own-website/', 'Try your own website', 'Move from the demo to a real website',
     'Adapt a small test to your own website by changing its address, selectors, and expected results. Learn about local previews.'),
    ('make-a-small-regression-suite/', 'Build a useful routine', 'Choose a small set of tests to run again',
     'Build a focused regression suite, run several files, try a narrow viewport, and understand where CI fits.'),
    ('your-first-testing-project/', 'Your first testing project', 'Put it together: your first testing project',
     'Finish the beginner course with a five-check practice project, a worked solution, and a plain-English testing glossary.'),
)

EXAMPLES = ('first-check.bru', 'form-submit.bru', 'result-checks.bru', 'choices.bru',
            'required-fields.bru', 'independent-tests.bru', 'evidence.bru', 'final-project.bru')
GROUPS = {0: 'Start with the basics', 4: 'Set up and run', 8: 'Build useful checks', 14: 'Make testing a habit'}


def paths():
    return [COURSE_PATH + lesson[0] for lesson in LESSONS]


def contents(base, current):
    parts = ['<nav class="course-contents" aria-label="All twenty lessons">']
    for index, (slug, label, title, description) in enumerate(LESSONS):
        if index in GROUPS:
            if index:
                parts.append('</ol>')
            parts.append(f'<p class="contents-group">{GROUPS[index]}</p><ol start="{index + 1}">')
        active = ' aria-current="page"' if index == current else ''
        parts.append(f'<li><a href="{base}{COURSE_PATH}{slug}"{active}>'
                     f'<span class="lesson-number" aria-hidden="true">{index + 1:02}</span>'
                     f'<span>{html.escape(label)}</span></a></li>')
    return '\n'.join(parts + ['</ol></nav>'])


def code_block(source, identifier, label):
    return (f'<div class="code-example"><div class="code-heading"><span>{html.escape(label)}</span>'
            f'<button type="button" data-copy="{identifier}" aria-label="Copy {html.escape(label, quote=True)}" hidden>Copy</button>'
            f'</div><pre tabindex="0"><code id="{identifier}">{html.escape(source.rstrip())}</code></pre></div>')


def build(output, base_url):
    base_url = site_url(base_url)
    base = html.escape(urlsplit(base_url).path, quote=True)
    example_dir = ROOT / 'example-tests/learn-testin'
    examples = {name: (example_dir / name).read_text(encoding='utf-8') for name in EXAMPLES}
    snippets = {name.removesuffix('.bru').replace('-', '_'): code_block(source, 'example-' + name[:-4], name)
                for name, source in examples.items()}
    course_output = output / COURSE_PATH
    course_output.mkdir(parents=True, exist_ok=True)
    shutil.copytree(SOURCE / 'assets', course_output / 'assets', dirs_exist_ok=True)
    with zipfile.ZipFile(course_output / 'practice-files.zip', 'w', zipfile.ZIP_DEFLATED) as archive:
        for name, source in examples.items():
            archive.writestr(name, source)
        archive.writestr('READ-ME.txt',
                         'Learn website testing with Bruster\n\n'
                         f'Course: {base_url}{COURSE_PATH}\n'
                         'Start with lesson 5 to obtain a test-ready Bruster executable.\n'
                         'Place the executable and these .bru files in your practice folder.\n'
                         'macOS/Linux: ./bruster test first-check.bru --visible\n'
                         'Windows PowerShell: .\\bruster.exe test first-check.bru --visible\n'
                         'The default website is the public Bruster demo.\n'
                         'Use --base-url URL to point the tests at another copy of that demo.\n')
    template = (SOURCE / '_layout.html').read_text(encoding='utf-8')
    for index, (slug, label, title, description) in enumerate(LESSONS):
        path = COURSE_PATH + slug
        content = substitute((SOURCE / slug / 'index.html').read_text(encoding='utf-8'), {
            'base': base, 'course': base + COURSE_PATH, **snippets,
        })
        previous = '' if index == 0 else (
            f'<a class="previous-lesson" rel="prev" href="{base}{COURSE_PATH}{LESSONS[index - 1][0]}">'
            f'<span>← Previous lesson</span><strong>{html.escape(LESSONS[index - 1][1])}</strong></a>')
        following = (f'<a class="next-lesson" rel="next" href="{base}{COURSE_PATH}{LESSONS[index + 1][0]}">'
                     f'<span>Next lesson →</span><strong>{html.escape(LESSONS[index + 1][1])}</strong></a>'
                     if index + 1 < len(LESSONS) else
                     f'<a class="next-lesson" href="{base}{COURSE_PATH}"><span>Course complete</span>'
                     '<strong>Return to the course start →</strong></a>')
        rendered = substitute(template, {
            'base': base, 'course': base + COURSE_PATH, 'number': f'{index + 1:02}',
            'title': html.escape(title), 'description': html.escape(description),
            'byline': article_byline(path),
            'contents': contents(base, index), 'content': content,
            'previous': previous, 'next': following,
            'metadata': render_metadata('Learn Website Testing — 20 Lessons for Beginners' if index == 0
                                        else f'{label} — Learn Website Testing, Lesson {index + 1}',
                                        description, path, base_url=base_url,
                                        section='Learn website testing', article=title),
        })
        target = output / path / 'index.html'
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(rendered, encoding='utf-8')
    return paths()
