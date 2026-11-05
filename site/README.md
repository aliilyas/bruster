# Bruster website

The product pages live here on `main`. Python 3.11+ builds static HTML with no
third-party build dependencies. The API and CLI tables come from
[`docs/reference.md`](../docs/reference.md), and the displayed controller version
comes from `Cargo.toml`.

The dedicated UI testing guide lives in `site/testing/index.html` and is published
at `/testing/`. Keep its examples and feature descriptions aligned with the `.bru`
grammar in `src/testing/parser.rs` and the full reference in `docs/reference.md`.

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

Run the real-browser website and demo checks with a source-built Bruster:

```sh
python3 scripts/site_test.py --binary target/release/bruster
```

This builds and serves a temporary preview, then runs the `.bru` website and
recording-demo suites at desktop and mobile widths. See
[`example-tests/README.md`](../example-tests/README.md) for individual commands,
coverage, and reports. CI retains the reports and screenshots on each platform.

## Web automation testing guide

[`guides/web-automation-testing/index.html`](guides/web-automation-testing/index.html)
is the beginner tutorial. Its code samples are embedded from executable `.bru`
files by `scripts/site_build.py`; update those source tests when changing a
workflow. The builder publishes the existing `examples/launch-demo/index.html`
at `demo/` with shared metadata, and copies downloadable tests from the repository's
`example-tests/` tree to the same paths on Pages. The recording fixture's body and
behavior are reused.

The guide has a search title/description, canonical and social metadata,
`TechArticle` structured data, a sitemap entry, and links from the homepage,
documentation, footer, and `llms.txt`. The interactive demo uses `noindex, follow`
and stays out of the sitemap, like the Test Lab's individual fixtures.

## Beginner learning site

[`learn-testin/`](learn-testin/) is a separate, minimal reading-focused site at
`/learn-testin/`. The spelling of this public path is intentional. It has exactly
twenty lesson pages, including the start page, for readers without programming
experience. Each lesson provides explanations, a concrete exercise, and a
checkpoint. The final lesson includes a five-check project and glossary.

`scripts/site_learn.py` owns the ordered lesson metadata, generates previous/next
links and course contents, and adds all lesson URLs to the main sitemap. Lesson
fragments live under `site/learn-testin/`; its own `_layout.html`, CSS, and optional
copy-button JavaScript provide the reading interface. Navigation, exercises,
answers, and downloads work without JavaScript. Keep lesson slugs stable.

Code blocks come directly from `example-tests/learn-testin/*.bru`. The same files
are downloadable individually and in the generated `learn-testin/practice-files.zip`.
The website runner executes all 15 course example tests against a local demo and
checks course navigation, answers, copying, and mobile layout. Static contracts
verify the complete twenty-page reading path, links, metadata, ZIP contents, and
source-backed snippets on root and project-path builds.

The setup lesson explicitly uses a source build because the v0.3.6 release
archives predate the testing DSL. Update its availability instructions when a
release containing the runner is published.

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
structured data, and breadcrumbs. Every page identifies Bruster as its subject;
the homepage connects the software entity to its Rust source repository, license,
runtime requirements, documentation, and version from `Cargo.toml`. Historical
run pages use `noindex, follow` and are excluded from the sitemap; their raw data
and links remain available. The current benchmark page is indexable once
measurements exist.

The homepage title and visible copy address AI agent browser automation and
Bruster's fit as a Playwright alternative for native-webview scripts and smoke
tests. Keep that qualification in the page description, software structured data,
and AI documentation. Comparisons with Playwright MCP and agent-browser link to
their official documentation; use concrete interface and engine differences
rather than unsupported rankings or performance claims.

The assembled sitemap also includes the Test Lab catalog, which has its own
canonical, social metadata, and `CollectionPage` structured data. Its fixture
links and coverage counts are rendered at build time so the catalog is useful
without JavaScript. Individual test cases and support documents use
`noindex, follow` and stay out of the sitemap. They remain crawlable so search
engines can see those directives.

The sitemap is at `https://aliilyas.github.io/bruster/sitemap.xml`. Submit it in a
verified Google Search Console URL-prefix property and Bing Webmaster Tools after
deployment. Verification requires the site owner's account.

After a homepage update is deployed, request a recrawl of the homepage through
Google Search Console and record the deployment date. Compare impressions, clicks,
and query coverage for `Playwright alternative`, `AI agent browser automation`,
`browser MCP server`, and branded Bruster queries over subsequent weeks. Fresh
agent-search traces can supplement these measurements; record the model, prompt,
search provider, queries, and cited URLs so changes in setup stay visible.

Google verification files matching `site/google*.html` are copied verbatim to the
published site root. Keep them in place after ownership verification succeeds.

For a project site, search engines only honor robots rules at
`https://aliilyas.github.io/robots.txt`, which belongs to the account-level site.
This project therefore uses HTML indexing directives and a project sitemap. A
root-domain build generates `robots.txt` with its sitemap URL automatically.

## AI-readable documentation (GEO)

The build publishes three linked resources for generative-engine optimization:

- `llms.txt`: a concise project description and annotated documentation index,
  maintained in `site/llms.txt`. Its URLs follow `--base-url`, and its version
  comes from `Cargo.toml`.
- `docs/reference.md`: the maintained CLI/API reference from `docs/reference.md`.
  Repository-relative links become absolute GitHub links, and website links use
  the deployment's base URL.
- `llms-full.txt`: the index and full reference combined into one plain-text file.

These files are generated during normal Pages builds and preserved when the Test
Lab is assembled. Update the source reference rather than a second copy of the API.
The site footer and documentation link to the index; the index links to the full
reference and human-readable pages. The homepage also has directly addressable
answers under `#faq`, including `#what-is-bruster`, `#bruster-vs-playwright`,
`#bruster-vs-agent-tools`, and `#autonomous-browser-agent`. Agent workflows have a
dedicated `#ai-agent-browser-automation` anchor. These passages are present in the
initial HTML and linked from the documentation index where relevant.

Keep facts, runtime requirements, and limitations consistent with the reference.
Performance claims should link to measured runs and their methodology. These
resources make the project easier to retrieve and cite; `llms.txt` is an emerging
convention, not a crawler permission file or a guarantee of search or AI placement.
