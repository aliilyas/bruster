# Bruster website

The product pages live here on `main`. Python 3.11+ builds static HTML with no
third-party build dependencies. The API and CLI tables come from
[`docs/reference.md`](../docs/reference.md), and the displayed controller version
comes from `Cargo.toml`.

## Local preview

```sh
python3 scripts/site_build.py --output target/site --base-url http://localhost:8000/
python3 -m http.server 8000 --directory target/site
```

To include real benchmark data, pass `--measurements /path/to/gh-pages-checkout`.
The input checkout is read-only; the build copies its `benchmarks/` directory and
refreshes report HTML in the output. Without data, the preview explicitly says
measurements are unavailable. Use a fresh output directory when changing datasets.

`scripts/site_layout.py`, `_metadata.html`, and `_layout.html` provide shared
metadata, navigation, and the footer. The Test Lab catalog reuses the metadata
renderer. `scripts/bench_report.py` renders the current and archived reports with
the same shell. A small head script selects the mobile menu layout before first
paint; `assets/site.js` adds menu, copy, and client-tab interactions. The content
and navigation also work without JavaScript.

Check the publishing and site contracts with:

```sh
python3 -m unittest discover -s scripts -p 'test_site_*.py'
python3 -m unittest discover -s scripts -p 'test_bench_publish.py'
```

The social preview is a checked-in 1200×630 PNG with its editable SVG source next
to it. Regenerate it with librsvg (or another SVG renderer) when branding changes:

```sh
rsvg-convert site/assets/social.svg -o site/assets/social.png
```

## Publishing

`.github/workflows/benchmark-pages.yml` checks pull requests. On relevant changes
to `main`, benchmark workflow completion, or a manual dispatch, it takes the
deployment lock and reads the latest `main` source and `gh-pages` measurements.
It builds the product site, bundles the Test Lab's pinned framework fixtures with
Node.js 24, and assembles one artifact containing the site, benchmarks, and
`test-lab/`. Site edits can ship independently of the measurement workflow; raw
measurement records remain on `gh-pages`. Updating a report layout also refreshes
historical report HTML. The input checkout's `CNAME` is carried into the artifact.

The Pages-provided base URL controls canonical URLs, navigation, assets, social
metadata, and the sitemap, including custom-domain deployments. Existing homepage
bookmarks have visible links to the new docs and follow them automatically when
JavaScript is available.

## Search indexing

The comparison uses the projects' official documentation for capability claims,
not snippets or third-party performance claims. Production HTML includes unique
titles/descriptions, self-canonicals, Open Graph and Twitter cards, software/site
structured data, and breadcrumbs. Historical run pages use `noindex, follow` and
are excluded from the sitemap; their raw data and links remain available. The
current benchmark page is indexable once measurements exist.

The assembled sitemap also includes the Test Lab catalog, which has its own
canonical, social metadata, and `CollectionPage` structured data. Its fixture
links and coverage counts are rendered at build time so the catalog is useful
without JavaScript. Individual test cases and support documents use
`noindex, follow` and stay out of the sitemap. They remain crawlable so search
engines can see those directives.

The sitemap is at `https://aliilyas.github.io/bruster/sitemap.xml`. Submit it in a
verified Google Search Console URL-prefix property and Bing Webmaster Tools after
deployment. Verification requires the site owner's account.

For a project site, search engines only honor robots rules at
`https://aliilyas.github.io/robots.txt`, which belongs to the account-level site.
This project therefore uses HTML indexing directives and a project sitemap. A
root-domain build generates `robots.txt` with its sitemap URL automatically.
