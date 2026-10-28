# Bruster website

The product pages live here on `main`. Python 3.11+ builds static HTML with no
third-party build dependencies. The API and CLI tables come from `README.md`,
and the displayed controller version comes from `Cargo.toml`.

## Local preview

```sh
python3 scripts/site_build.py --output target/site --base-url http://localhost:8000/
python3 -m http.server 8000 --directory target/site
```

To include real benchmark data, pass `--measurements /path/to/gh-pages-checkout`.
The input checkout is read-only; the build copies its `benchmarks/` directory and
refreshes report HTML in the output. Without data, the preview explicitly says
measurements are unavailable. Use a fresh output directory when changing datasets.

`scripts/site_layout.py` and `_layout.html` provide the shared navigation, metadata,
and footer. `scripts/bench_report.py` renders the current and archived reports with
the same shell. `assets/site.js` progressively adds menu, copy, and client-tab
interactions; the content and navigation also work without JavaScript.

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
to `main`, a successful benchmark workflow, or a manual dispatch, it takes the
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

## Search content and indexing

OpenSERP MCP research on **28 October 2026**, English / US, examined the first five
results for these queries. These are observed search results, not search-volume
or keyword-difficulty estimates:

| Query | Observed intent | Content destination |
| --- | --- | --- |
| native browser automation | Agent tools and browser infrastructure, including agent-browser and Browser Use | Homepage: explain native engines and the stdio interface |
| browser automation CLI | agent-browser, Playwright CLI, and Browser Use CLI setup | Docs: runnable quickstart, Python example, CLI reference |
| lightweight browser automation | Engine alternatives, including Lightpanda and headless-browser lists | Homepage + comparison: explain the complete runtime footprint |
| Playwright alternatives | Tool comparisons and discussions about testing maintenance | `/compare/`: practical selection criteria and explicit trade-offs |
| Playwright Puppeteer memory benchmarks | Memory questions and cross-tool performance comparisons | `/benchmarks/`: process-tree accounting, raw evidence, exact versions |
| browser automation without Node.js | Mixed results, often unrelated to the exact constraint | A supporting product distinction, not a dedicated thin landing page |

Google supplied the useful results. Bing was also queried for “native browser
automation,” “Playwright alternatives,” and “browser automation without Node.js”;
two queries failed and the remaining result was irrelevant, so it was not used
as supporting evidence. Representative research sources:

- https://agent-browser.dev/
- https://playwright.dev/
- https://pptr.dev/
- https://lightpanda.io/
- https://momentic.ai/blog/playwright-alternatives
- https://www.browserless.io/blog/playwright-alternative
- https://www.checklyhq.com/blog/puppeteer-vs-selenium-vs-playwright-speed-comparison/

The comparison uses the projects' official documentation for capability claims,
not snippets or third-party performance claims. Production HTML includes unique
titles/descriptions, self-canonicals, Open Graph and Twitter cards, software/site
structured data, and breadcrumbs. Historical run pages use `noindex, follow` and
are excluded from the sitemap; their raw data and links remain available. The
current benchmark page is indexable once measurements exist.

The sitemap is at `https://aliilyas.github.io/bruster/sitemap.xml`. Submit it in a
verified Google Search Console URL-prefix property and Bing Webmaster Tools after
deployment. Verification requires the site owner's account. Search performance
can then be compared against this query baseline.

For a project site, search engines only honor robots rules at
`https://aliilyas.github.io/robots.txt`, which belongs to the account-level site.
This project therefore uses HTML indexing directives and a project sitemap. A
root-domain build generates `robots.txt` with its sitemap URL automatically.

OpenSERP is a research-time integration configured locally in OpenCode. The
published website and CI build require no search API credentials.
