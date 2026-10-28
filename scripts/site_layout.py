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


def site_url(value):
    parsed = urlsplit(value)
    if parsed.scheme not in ('http', 'https') or not parsed.netloc or parsed.query or parsed.fragment:
        raise ValueError('The site URL must be an absolute HTTP(S) URL without a query or fragment')
    return value.rstrip('/') + '/'


def substitute(template, values):
    return re.sub(r'\{\{(\w+)\}\}', lambda match: str(values[match[1]]), template)


def render_page(title, description, path, content, *, base_url=SITE_URL, section='',
                body_class='', extra_head='', noindex=False, application=False):
    base_url = site_url(base_url)
    e = lambda value: html.escape(str(value), quote=True)
    base = urlsplit(base_url).path
    canonical = base_url + path
    graph = [{
        '@type': 'WebSite', '@id': base_url + '#website', 'name': 'bruster',
        'url': base_url, 'inLanguage': 'en',
    }]
    if application:
        graph.append({
            '@type': 'SoftwareApplication', '@id': base_url + '#software', 'name': 'bruster',
            'url': base_url, 'description': description, 'applicationCategory': 'DeveloperApplication',
            'operatingSystem': 'macOS, Linux, Windows', 'isAccessibleForFree': True,
            'license': REPOSITORY + '/blob/main/LICENSE', 'downloadUrl': REPOSITORY + '/releases',
            'sameAs': [REPOSITORY],
            'offers': {'@type': 'Offer', 'price': '0', 'priceCurrency': 'USD'},
        })
    if path and not noindex:
        graph.append({
            '@type': 'BreadcrumbList', 'itemListElement': [
                {'@type': 'ListItem', 'position': 1, 'name': 'bruster', 'item': base_url},
                {'@type': 'ListItem', 'position': 2, 'name': section, 'item': canonical},
            ],
        })
    structured = json.dumps({'@context': 'https://schema.org', '@graph': graph}, ensure_ascii=False).replace('<', '\\u003c')
    nav = []
    for name, target in (('Docs', 'docs/'), ('Benchmarks', 'benchmarks/'), ('Compare', 'compare/')):
        current = ' aria-current="page"' if section == name else ''
        nav.append(f'<a href="{e(base + target)}"{current}>{name}</a>')
    values = {
        'title': e(title), 'description': e(description), 'canonical': e(canonical),
        'base': e(base), 'image': e(base_url + 'assets/social.png'), 'structured': structured,
        'robots': 'noindex, follow' if noindex else 'index, follow, max-image-preview:large',
        'body_class': e(body_class), 'extra_head': extra_head, 'content': content,
        'nav': '\n'.join(nav), 'repository': REPOSITORY,
    }
    return substitute((SITE / '_layout.html').read_text(), values)
