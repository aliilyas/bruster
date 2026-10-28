//! End to end against public sites, driven like an agent would. Needs the
//! network, so these are ignored by default:
//!
//!     xvfb-run -a cargo test --release --test e2e -- --ignored --test-threads=2
//!
//! Sites change; assertions are structural (a result list, a title change),
//! not exact text.

mod common;

use std::time::{Duration, Instant};

use serde_json::{json, Value};

use common::*;

const SITE_TIMEOUT: u64 = 20_000;

fn names(snap: &Value) -> Vec<String> {
    snap["elements"].as_array().unwrap().iter().filter_map(|e| e["name"].as_str().or(e["text"].as_str())).map(str::to_owned).collect()
}

#[test]
#[ignore]
fn search_engine_results() {
    let mut b = Browser::spawn();
    b.open("https://duckduckgo.com/html/");
    b.ok("type", json!({ "selector": "input[name=q]", "text": "webkitgtk", "submit": true }));
    b.ok("wait_for", json!({ "text": "webkitgtk", "timeout": SITE_TIMEOUT }));
    let hits = b.ok("find", json!({ "regex": "webkit", "selector": "#links" }));
    assert!(hits["elements"].as_array().unwrap().len() >= 3, "{hits}");
}

#[test]
#[ignore]
fn login_form_error_under_csp() {
    let mut b = Browser::spawn();
    b.open("https://news.ycombinator.com/login");
    b.ok("fill_form", json!({ "fields": [
        { "selector": "input[name=acct]", "value": "bruster-no-such-user" },
        { "selector": "input[name=pw]", "value": "x" },
    ] }));
    b.ok("press", json!({ "selector": "input[name=pw]", "key": "Enter" }));
    let t = Instant::now();
    loop {
        let body = b.ok("text", json!({ "selector": "body" }));
        let body = body.as_str().unwrap();
        // HN answers cloud IPs with a bot check instead of the login error; both
        // prove the form was submitted and the reply rendered.
        if ["Bad login", "Validation required", "Sorry"].iter().any(|k| body.contains(*k)) {
            break;
        }
        assert!(t.elapsed() < Duration::from_millis(SITE_TIMEOUT), "{body}");
        b.ok("wait_for", json!({ "time": 500 }));
    }
    // HN sends a CSP without unsafe-eval.
    assert_eq!(b.ok("eval", json!({ "expression": "1 + 1" })), 2);
}

fn wiki_retry_rate_limit(b: &mut Browser) {
    // Wikimedia can return its CDN's 429 error document as a completed load.
    // Reload only that explicit response, with bounded exponential backoff;
    // reloading preserves the history entry the test is exercising.
    for attempt in 0..=3 {
        let page = b.ok("snapshot", json!({}));
        let limited = page["title"] == "Wikimedia Error" && page["elements"].as_array().unwrap().iter()
            .any(|e| e["text"].as_str().is_some_and(|s| s.contains("Error: 429")));
        if !limited {
            return;
        }
        assert!(attempt < 3, "Wikipedia still rate-limited after three reloads: {page}");
        let seconds = 15 << attempt;
        eprintln!("Wikipedia HTTP 429 at {}; waiting {seconds}s before reload {} of 3", page["url"], attempt + 1);
        std::thread::sleep(Duration::from_secs(seconds));
        b.ok("reload", json!({}));
    }
}

fn wiki_history_page(b: &mut Browser, url: &Value) -> Value {
    // MediaWiki replaces analytics and default namespace/profile parameters
    // after rendering. Compare the actual page and decoded search query.
    b.ok("eval", json!({ "expression": format!(r#"(() => {{
        const u = new URL({url});
        return {{ origin: u.origin, path: u.pathname, fragment: u.hash,
            title: u.searchParams.get('title'), search: u.searchParams.get('search') }};
    }})()"#) }))
}

fn wiki_back_page(b: &mut Browser) -> Value {
    let back = b.ok("back", json!({}));
    assert!(back["url"].is_string(), "Wikipedia history ended before the entry page: {back}");
    wiki_retry_rate_limit(b);
    let current = b.ok("url", json!({}));
    let page = wiki_history_page(b, &back["url"]);
    assert_eq!(page, wiki_history_page(b, &current), "back reply disagrees with live URL: {back}; {current}");
    eprintln!("Wikipedia back: {}", back["url"]);
    page
}

#[test]
#[ignore]
fn wiki_search_then_back() {
    // Cover the expanded header, responsive toggle, and Special:Search even
    // when the toggle's JavaScript happens to expand the header inline.
    // Reuse the browser's asset cache and pace the routes to avoid bursts of
    // uncached requests from fresh WebView2 profiles.
    let mut b = Browser::spawn_with(&["--viewport", "1400x800"]);
    for (route, (width, page)) in [(1400, "Main_Page"), (900, "Main_Page"), (900, "Special:Search")].into_iter().enumerate() {
        if route > 0 {
            std::thread::sleep(Duration::from_secs(15));
            b.ok("resize", json!({ "width": width, "height": 800 }));
        }
        let viewport = format!("{width}x800");
        eprintln!("Wikipedia {viewport} {page}: opening search");
        b.open(&format!("https://en.wikipedia.org/wiki/{page}"));
        wiki_retry_rate_limit(&mut b);
        // Special:Search can have an empty label, so find by role and form
        // name rather than filtering snapshot elements by accessible name.
        // Its scripts can replace the form after load. An absent input does
        // not necessarily mean the responsive header toggle is available.
        let mut start = Instant::now();
        let mut toggled = false;
        let input = loop {
            if let Some(input) = visible_input_named(&mut b, "search") {
                break input;
            }
            assert!(start.elapsed() < Duration::from_millis(SITE_TIMEOUT), "no visible Wikipedia search input at {viewport} {page}: {:?}", b.call("snapshot", json!({})));
            if !toggled && b.ok("eval", json!({ "expression": "!!document.querySelector('#p-search .search-toggle')?.checkVisibility()" })) == true {
                // The toggle can expand inline or follow its Special:Search href.
                b.ok("click", json!({ "selector": "#p-search .search-toggle" }));
                wiki_retry_rate_limit(&mut b);
                start = Instant::now();
                toggled = true;
            } else {
                std::thread::sleep(Duration::from_millis(100));
            }
        };
        let entry_url = b.ok("url", json!({}));
        b.ok("type", json!({ "ref": input, "text": "WebKitGTK", "submit": true }));
        wiki_retry_rate_limit(&mut b);
        let mut result_url = b.ok("url", json!({}));
        // Special:Search submits a full-text search rather than jumping
        // straight to the article as the header's search does.
        let results_page = !result_url.as_str().unwrap().contains("/wiki/WebKit");
        if results_page {
            let found = b.ok("find", json!({ "regex": "^WebKit(?:GTK)?$", "selector": "#mw-content-text" }));
            let link = found["elements"].as_array().unwrap().iter()
                .find(|e| e["role"] == "link" && e["href"].as_str().is_some_and(|url| url.contains("/wiki/WebKit")))
                .unwrap_or_else(|| panic!("no WebKit result at {result_url}: {found}"));
            result_url = b.ok("url", json!({}));
            b.ok("click", json!({ "ref": link["ref"] }));
            wiki_retry_rate_limit(&mut b);
        }
        b.ok("wait_for", json!({ "url": "/wiki/WebKit", "timeout": SITE_TIMEOUT }));
        assert!(b.ok("title", json!({})).as_str().unwrap().contains("WebKit"));
        let snap = b.ok("snapshot", json!({ "format": "text" }));
        assert!(snap.as_str().unwrap().lines().count() > 100, "thin snapshot");
        eprintln!("Wikipedia {viewport} {page}: entry={entry_url}, search={result_url}");
        let entry_page = wiki_history_page(&mut b, &entry_url);
        let search_page = wiki_history_page(&mut b, &result_url);
        if results_page {
            assert_eq!(wiki_back_page(&mut b), search_page);
        }
        // AdvancedSearch pushes a same-document history entry for default
        // namespaces (MediaWiki T217445). Only equivalent result pages may
        // intervene before back reaches the original search-entry page.
        for step in 0..4 {
            let back = wiki_back_page(&mut b);
            if back == entry_page {
                break;
            }
            assert!(results_page, "unexpected intermediate history page: {back}");
            assert_eq!(back, search_page);
            assert!(step < 3, "back never reached the search-entry page: {entry_url}");
        }
    }
}

#[test]
#[ignore]
fn github_tab_navigation() {
    let mut b = Browser::spawn();
    b.open("https://github.com/tauri-apps/wry");
    let issues = b.ok("find", json!({ "regex": "^Issues" }));
    let link = issues["elements"].as_array().unwrap().iter().find(|e| e["role"] == "link").expect("issues link");
    b.ok("click", json!({ "ref": link["ref"] }));
    b.ok("wait_for", json!({ "url": "/issues", "timeout": SITE_TIMEOUT }));
    // The call after a navigating click reads the new page.
    let snap = b.ok("snapshot", json!({}));
    assert!(names(&snap).iter().any(|n| n.to_lowercase().contains("issue")), "{:?}", &names(&snap)[..10]);
    // GitHub sends a CSP without unsafe-eval; eval must still work.
    assert!(b.ok("eval", json!({ "expression": "location.pathname" })).as_str().unwrap().ends_with("/issues"));
}

#[test]
#[ignore]
fn mdn_sidebar_link() {
    let mut b = Browser::spawn();
    b.open("https://developer.mozilla.org/en-US/docs/Web/API/TreeWalker");
    let link = b.ok("find", json!({ "regex": "^NodeIterator$" }));
    let link = link["elements"].as_array().unwrap().iter().find(|e| e["role"] == "link").expect("link");
    b.ok("click", json!({ "ref": link["ref"] }));
    b.ok("wait_for", json!({ "url": "NodeIterator", "timeout": SITE_TIMEOUT }));
    assert_eq!(b.ok("text", json!({ "selector": "h1" })).as_str().unwrap().trim(), "NodeIterator");
}

#[test]
#[ignore]
fn news_site_headlines_and_screenshot() {
    let mut b = Browser::spawn();
    b.open("https://www.bbc.com/news");
    let snap = b.ok("snapshot", json!({}));
    let headings = snap["elements"].as_array().unwrap().iter().filter(|e| e["role"] == "heading").count();
    assert!(headings > 10, "{headings} headings");
    let shot = b.ok("screenshot", json!({}));
    assert!(shot["png_base64"].as_str().unwrap().len() > 20_000);
    let full = b.ok("screenshot", json!({ "full": true }));
    assert!(full["png_base64"].as_str().unwrap().len() > shot["png_base64"].as_str().unwrap().len());
}

#[test]
#[ignore]
fn react_app_keyboard() {
    let mut b = Browser::spawn();
    b.open("https://demo.playwright.dev/todomvc/");
    b.ok("fill", json!({ "selector": ".new-todo", "value": "walk the dog" }));
    b.ok("press", json!({ "selector": ".new-todo", "key": "Enter" }));
    b.ok("wait_for", json!({ "text": "walk the dog", "selector": ".todo-list", "timeout": 5000 }));
    assert_eq!(b.ok("count", json!({ "selector": ".todo-list li" })), 1);
    b.ok("check", json!({ "selector": ".todo-list .toggle" }));
    assert_eq!(b.ok("count", json!({ "selector": ".todo-list li.completed" })), 1);
}

#[test]
#[ignore]
fn interaction_playground() {
    let mut b = Browser::spawn();
    let site = "https://the-internet.herokuapp.com";

    // A free Heroku dyno can take a while to wake up.
    let open = |b: &mut Browser, path: &str| b.ok("navigate", json!({ "url": format!("{site}{path}"), "timeout": 90_000 }));
    open(&mut b, "/login");
    b.ok("fill_form", json!({ "fields": [{ "selector": "#username", "value": "tomsmith" }, { "selector": "#password", "value": "SuperSecretPassword!" }] }));
    b.ok("click", json!({ "selector": "button[type=submit]" }));
    b.ok("wait_for", json!({ "url": "/secure", "timeout": SITE_TIMEOUT }));
    assert!(b.ok("find", json!({ "text": "logged into" }))["elements"].as_array().unwrap().len() >= 1);

    open(&mut b, "/javascript_alerts");
    b.ok("dialog", json!({ "accept": true, "text": "bruster" }));
    let prompt = b.ok("find", json!({ "regex": "JS Prompt$" }));
    b.ok("click", json!({ "ref": prompt["elements"].as_array().unwrap().iter().find(|e| e["role"] == "button").unwrap()["ref"] }));
    assert_eq!(b.ok("text", json!({ "selector": "#result" })), "You entered: bruster");

    open(&mut b, "/drag_and_drop");
    b.ok("drag", json!({ "from": { "selector": "#column-a" }, "to": { "selector": "#column-b" } }));
    assert_eq!(b.ok("text", json!({ "selector": "#column-a header" })), "B");

    open(&mut b, "/dynamic_loading/2");
    b.ok("click", json!({ "selector": "#start button" }));
    b.ok("wait_for", json!({ "text": "Hello World!", "timeout": SITE_TIMEOUT }));

    open(&mut b, "/windows");
    b.ok("click", json!({ "selector": "a[href='/windows/new']" }));
    let opened = b.wait_event("tab_opened");
    let t = opened["tab"].as_u64().unwrap();
    b.wait_load(t);
    assert_eq!(b.ok("text", json!({ "tab": t, "selector": "h3" })), "New Window");
    b.ok("close_tab", json!({ "tab": t }));

    open(&mut b, "/dropdown");
    assert_eq!(b.ok("select", json!({ "selector": "#dropdown", "value": "Option 2" })), json!(["2"]));
    open(&mut b, "/checkboxes");
    assert_eq!(b.ok("check", json!({ "selector": "#checkboxes input:first-child" })), true);
}

#[test]
#[ignore]
#[cfg(target_os = "linux")] // Native download cancellation/reporting is WebKitGTK-only.
fn download_is_cancelled_and_reported() {
    let mut b = Browser::spawn();
    b.open("https://example.com/");
    let err = b.err("navigate", json!({ "url": "https://httpbin.org/response-headers?Content-Disposition=attachment%3B%20filename%3Dx.json" }));
    assert!(err.contains("download"), "{err}");
    b.wait_event("download");
    assert_eq!(b.ok("title", json!({})), "Example Domain");
}

#[test]
#[ignore]
fn cold_and_warm_navigation_budget() {
    // Guard against regressions in navigate latency; generous for a shared network.
    let mut b = Browser::spawn();
    let t = Instant::now();
    b.open("https://en.wikipedia.org/wiki/WebKit");
    assert!(t.elapsed() < Duration::from_secs(8), "cold {:?}", t.elapsed());
    let t = Instant::now();
    b.ok("navigate", json!({ "url": "https://en.wikipedia.org/wiki/Blink_(browser_engine)", "until": "dom" }));
    assert!(t.elapsed() < Duration::from_secs(4), "warm dom {:?}", t.elapsed());
    let t = Instant::now();
    b.ok("snapshot", json!({ "format": "text" }));
    assert!(t.elapsed() < Duration::from_millis(500), "snapshot {:?}", t.elapsed());
}
