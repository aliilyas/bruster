"""Shared, dependency-free HTML shell for the product site and benchmark reports."""
import html
import json
import re
from pathlib import Path
from urllib.parse import urlsplit


ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / 'site'
SITE_URL = 'https://aliilyas.github.io/bruster/'
REPOSITORY = 'https://github.com/aliilyas/bruster'
SOFTWARE_DESCRIPTION = (
    'Bruster is an open-source Rust browser automation tool and MCP server for AI agents. '
    'It is a native-webview alternative to Playwright for scripts and smoke tests, '
    'with JSON-lines control and no Node.js requirement.'
)


def project_version():
    # Only product-site builds need TOML; the shared Test Lab supports Python 3.10.
    import tomllib
    return tomllib.loads((ROOT / 'Cargo.toml').read_text())['package']['version']


def site_url(value):
    parsed = urlsplit(value)
    if parsed.scheme not in ('http', 'https') or not parsed.netloc or parsed.query or parsed.fragment:
        raise ValueError('The site URL must be an absolute HTTP(S) URL without a query or fragment')
    return value.rstrip('/') + '/'


def substitute(template, values):
    return re.sub(r'\{\{(\w+)\}\}', lambda match: str(values[match[1]]), template)


def render_metadata(title, description, path, *, base_url=SITE_URL, section='',
                    noindex=False, application=False, page_type='WebPage', article=''):
    base_url = site_url(base_url)
    e = lambda value: html.escape(str(value), quote=True)
    canonical = base_url + path
    webpage = {
        '@type': page_type, '@id': canonical + '#webpage', 'url': canonical,
        'name': title, 'description': description, 'inLanguage': 'en',
        'isPartOf': {'@id': base_url + '#website'},
        'about': {'@id': base_url + '#software'},
    }
    graph = [{
        '@type': 'WebSite', '@id': base_url + '#website', 'name': 'Bruster',
        'alternateName': 'bruster', 'url': base_url, 'inLanguage': 'en',
        'about': {'@id': base_url + '#software'},
    }, webpage]
    if article:
        webpage['mainEntity'] = {'@id': canonical + '#article'}
        graph.append({
            '@type': 'TechArticle', '@id': canonical + '#article', 'url': canonical,
            'headline': article, 'description': description, 'inLanguage': 'en',
            'mainEntityOfPage': {'@id': canonical + '#webpage'},
            'about': {'@id': base_url + '#software'},
            'image': base_url + 'assets/social.png', 'proficiencyLevel': 'Beginner',
            'author': {'@type': 'Organization', 'name': 'Bruster contributors', 'url': REPOSITORY},
        })
    if application:
        webpage['mainEntity'] = {'@id': base_url + '#software'}
        graph.append({
            '@type': 'SoftwareApplication', '@id': base_url + '#software', 'name': 'Bruster',
            'alternateName': 'bruster', 'url': base_url, 'description': SOFTWARE_DESCRIPTION,
            'applicationCategory': 'DeveloperApplication', 'softwareVersion': project_version(),
            'operatingSystem': 'macOS, Linux, Windows', 'isAccessibleForFree': True,
            'softwareRequirements': 'WKWebView on macOS; WebKitGTK 4.1 and a display or Xvfb on Linux; '
                                    'Microsoft Edge WebView2 Runtime on Windows.',
            'featureList': ['JSON-lines API over stdio', 'Built-in Model Context Protocol (MCP) server',
                            'DOM snapshots and element references', 'Form interaction and screenshots',
                            'Browser tabs and persistent profiles',
                            '.bru UI test runner with retrying assertions and failure screenshots'],
            'license': REPOSITORY + '/blob/main/LICENSE', 'downloadUrl': REPOSITORY + '/releases',
            'sameAs': [REPOSITORY], 'image': base_url + 'assets/social.png',
            'mainEntityOfPage': {'@id': base_url + '#webpage'},
            'softwareHelp': {'@id': base_url + 'docs/#webpage'},
            'subjectOf': {'@id': REPOSITORY + '#source'},
            'offers': {'@type': 'Offer', 'price': '0', 'priceCurrency': 'USD'},
        })
        graph.append({
            '@type': 'SoftwareSourceCode', '@id': REPOSITORY + '#source',
            'name': 'Bruster source code', 'url': REPOSITORY, 'codeRepository': REPOSITORY,
            'programmingLanguage': 'Rust', 'license': REPOSITORY + '/blob/main/LICENSE',
            'targetProduct': {'@id': base_url + '#software'},
        })
    if path and not noindex:
        webpage['breadcrumb'] = {'@id': canonical + '#breadcrumb'}
        graph.append({
            '@type': 'BreadcrumbList', '@id': canonical + '#breadcrumb', 'itemListElement': [
                {'@type': 'ListItem', 'position': 1, 'name': 'bruster', 'item': base_url},
                {'@type': 'ListItem', 'position': 2, 'name': section, 'item': canonical},
            ],
        })
    structured = json.dumps({'@context': 'https://schema.org', '@graph': graph}, ensure_ascii=False).replace('<', '\\u003c')
    return substitute((SITE / '_metadata.html').read_text(), {
        'title': e(title), 'description': e(description), 'canonical': e(canonical),
        'image': e(base_url + 'assets/social.png'), 'structured': structured,
        'og_type': 'article' if article else 'website',
        'robots': 'noindex, follow' if noindex else 'index, follow, max-image-preview:large',
    })


def render_page(title, description, path, content, *, base_url=SITE_URL, section='',
                body_class='', extra_head='', noindex=False, application=False, article=''):
    base_url = site_url(base_url)
    e = lambda value: html.escape(str(value), quote=True)
    base = urlsplit(base_url).path
    nav = []
    for name, target in (('Docs', 'docs/'), ('Testing', 'testing/'),
                         ('Benchmarks', 'benchmarks/'), ('Compare', 'compare/')):
        current = ' aria-current="page"' if section == name else ''
        nav.append(f'<a href="{e(base + target)}"{current}>{name}</a>')
    values = {
        'metadata': render_metadata(title, description, path, base_url=base_url,
                                    section=section, noindex=noindex, application=application, article=article),
        'base': e(base),
        'body_class': e(body_class), 'extra_head': extra_head, 'content': content,
        'nav': '\n'.join(nav), 'repository': REPOSITORY,
    }
    return substitute((SITE / '_layout.html').read_text(), values)
