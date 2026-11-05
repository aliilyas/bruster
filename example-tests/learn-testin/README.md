# Learn website testing: course practice files

These eight files accompany the [twenty-page beginner course](https://aliilyas.github.io/bruster/learn-testin/).
They contain 15 tests in total, including the five-check final project. The course
embeds these exact files in its lessons and provides individual downloads and a
[practice ZIP](https://aliilyas.github.io/bruster/learn-testin/practice-files.zip).

Start with `first-check.bru`. The default URL is the published practice form.
Use a source-built Bruster containing `bruster test`; v0.3.6 release archives
predate the test runner. Installation is explained in course lesson 5.

From the repository root:

```sh
target/release/bruster test example-tests/learn-testin/first-check.bru --visible
```

To run every course example against an automatically built local demo:

```sh
python3 scripts/site_test.py --binary target/release/bruster
```

That helper also checks the product website, the learning site's desktop/mobile
navigation, and the original recording fixture. Its `course-examples` report
contains these 15 checks. It overrides the base URL to use localhost, so CI does
not depend on the deployed website. All files can also be passed directly to
`bruster test` with `--base-url http://127.0.0.1:8765/` when serving the demo locally.
