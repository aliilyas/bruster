//! Robustness: protocol abuse, odd documents, hanging loads, limits, memory.
//! Local pages only; needs a display like smoke.rs.

mod common;

use std::io::Write;
use std::time::{Duration, Instant};

use serde_json::{json, Value};

use common::*;

/// RSS in MB of the bruster process tree (Linux only; 0 elsewhere).
fn rss_mb(root: u32) -> u64 {
    let Ok(procs) = std::fs::read_dir("/proc") else {
        return 0;
    };
    let mut parent = std::collections::HashMap::new();
    for e in procs.flatten() {
        let Ok(pid) = e.file_name().to_string_lossy().parse::<u32>() else {
            continue;
        };
        let Ok(stat) = std::fs::read_to_string(e.path().join("stat")) else {
            continue;
        };
        let ppid = stat
            .rsplit(')')
            .next()
            .and_then(|s| s.split_whitespace().nth(1))
            .and_then(|p| p.parse::<u32>().ok());
        parent.insert(pid, ppid.unwrap_or(0));
    }
    let mut total = 0;
    for (&pid, _) in &parent {
        let mut p = pid;
        let mine = loop {
            if p == root {
                break true;
            }
            match parent.get(&p) {
                Some(&pp) if pp > 1 => p = pp,
                _ => break false,
            }
        };
        if !mine {
            continue;
        }
        let Ok(status) = std::fs::read_to_string(format!("/proc/{pid}/status")) else {
            continue;
        };
        if let Some(l) = status.lines().find(|l| l.starts_with("VmRSS:")) {
            total += l
                .split_whitespace()
                .nth(1)
                .and_then(|v| v.parse::<u64>().ok())
                .unwrap_or(0);
        }
    }
    total / 1024
}

#[test]
fn beforeunload_does_not_block() {
    let mut b = Browser::spawn();
    let base = serve();
    for path in ["/other", "/slower"] {
        b.open(&format!("{base}/beforeunload"));
        b.ok(
            "eval",
            json!({ "expression": format!("document.getElementById('l').href = '{path}'; document.getElementById('l').target = '{}'", if path == "/slower" { "_self" } else { "" }) }),
        );
        b.ok("click", json!({ "selector": "#l" }));
        // WKWebView has not committed while /slower is waiting. Title must
        // wait for that document rather than read the old page.
        assert_eq!(
            b.ok("title", json!({})),
            "other",
            "beforeunload prompt blocked the tab or title read the old page: {path}; events: {:?}",
            b.stash
        );
    }
}

#[cfg(target_os = "linux")]
#[test]
fn completed_navigations_do_not_retain_timer_threads() {
    let mut b = Browser::spawn();
    let base = serve();
    b.open(&format!("{base}/other"));
    let threads = |pid| {
        std::fs::read_to_string(format!("/proc/{pid}/status"))
            .unwrap()
            .lines()
            .find_map(|line| {
                line.strip_prefix("Threads:")
                    .map(|n| n.trim().parse::<u32>().unwrap())
            })
            .unwrap()
    };
    let before = threads(b.child.id());
    // Finish well before these deadlines. A sleeping worker per navigation
    // would still be alive at the measurement, even though every call replied.
    for i in 0..48 {
        b.ok(
            "navigate",
            json!({ "url": format!("{base}/other?{i}"), "timeout": 120_000 }),
        );
        if i % 12 == 0 {
            b.ok("reload", json!({ "timeout": 120_000 }));
            let tab = b.ok(
                "new_tab",
                json!({ "url": format!("{base}/form"), "timeout": 120_000 }),
            )["tab"]
                .clone();
            b.ok("close_tab", json!({ "tab": tab }));
        }
    }
    let after = threads(b.child.id());
    assert!(
        after <= before + 8,
        "completed calls retained threads: {before} -> {after}"
    );
    // The same worker must still wake a genuinely stalled navigation.
    let start = Instant::now();
    assert!(b
        .call(
            "navigate",
            json!({ "url": format!("{base}/hang"), "timeout": 200 })
        )
        .unwrap_err()
        .contains("timed out"));
    assert!(start.elapsed() < Duration::from_secs(5));
    b.open(&format!("{base}/other"));
}

#[test]
fn page_replies_preserve_json_and_reject_stale_attempts() {
    let mut b = Browser::spawn();
    // A page request before the first navigate also exercises blank warm-up.
    assert_eq!(b.ok("eval", json!({ "expression": "40 + 2" })), 42);
    b.open(&format!("{}/other", serve()));
    for value in [
        Value::Null,
        json!(true),
        json!(-1.25),
        json!("quote\"\\\r\n雪🚀"),
        json!({"rows": [null, 1, false, {"text": "a\nb"}]}),
        json!("x".repeat(120_000)),
    ] {
        let id = b.send("eval", json!({ "expression": format!("({value})") }));
        let reply = b.take("eval reply", |v| v["id"] == id);
        assert_eq!(reply, json!({ "id": id, "result": value }));
    }
    b.ok("eval", json!({ "expression": r#"
        const original = __bruster.run;
        __bruster.run = (id, method, params, attempt) => {
            if (method !== 'title') return original(id, method, params, attempt);
            const reply = { id, result: { text: 'escaped\n雪' }, attempt,
                document: __bruster.document, generation: __bruster.generation };
            window.ipc.postMessage(JSON.stringify({...reply, attempt: attempt - 1,
                result: 'stale', navigating: true}));
            window.ipc.postMessage(JSON.stringify({...reply, document: 'old-document', result: 'stale'}));
            // Custom IPC with literal newlines must be normalized to one line.
            window.ipc.postMessage(JSON.stringify(reply, null, 2));
        };
    "# }));
    assert_eq!(b.ok("title", json!({})), json!({ "text": "escaped\n雪" }));
    assert_eq!(
        b.ok(
            "eval",
            json!({ "expression": "6 * 7", "request_timeout": 1000 })
        ),
        42
    );
}

#[test]
fn document_announcement_retries_an_early_native_bind() {
    let script = std::env::temp_dir().join(format!("bruster-bind-edge-{}.js", std::process::id()));
    std::fs::write(&script, r#"
        const bind = __bruster.bind;
        window.skippedBind = false;
        __bruster.bind = generation => {
            if (window.skippedBind) return bind(generation);
            // Model a commit-time evaluation before the runtime existed.
            // The runtime's initial document announcement arrives afterwards.
            window.skippedBind = true;
            window.ipc.postMessage(JSON.stringify({ bound: true, generation: 0, document: __bruster.document }));
        };
    "#).unwrap();
    let mut b = Browser::spawn_with(&["--init-script", script.to_str().unwrap()]);
    let base = serve();
    for until in ["dom", "load", "idle"] {
        b.ok(
            "navigate",
            json!({ "url": format!("{base}/other?{until}"), "until": until, "timeout": 5000 }),
        );
        assert_eq!(b.ok("eval", json!({ "expression": "skippedBind" })), true);
        assert_eq!(b.ok("title", json!({})), "other");
    }
    std::fs::remove_file(script).unwrap();
}

#[test]
fn duplicate_load_does_not_release_requests_for_the_next_page() {
    let mut b = Browser::spawn_env(&[], &[("BRUSTER_TRACE_NAV", "1")]);
    let base = serve();
    b.open(&format!("{base}/more"));
    // The page's load IPC answers navigate before WebKit's native Finished.
    // Reproduce that later duplicate while the next navigation is provisional.
    // Send it immediately after the click reply on the same IPC channel;
    // this avoids hidden-window timers and loads cancelled by navigation.
    b.ok(
        "eval",
        json!({ "expression": r#"
        document.getElementById('away').href = '/hang';
        const run = __bruster.run;
        __bruster.run = async (id, method, params, attempt) => {
            await run(id, method, params, attempt);
            if (method === 'click') {
                window.ipc.postMessage(JSON.stringify({ loaded: location.href,
                    document: __bruster.document, generation: __bruster.generation }));
                window.ipc.postMessage(JSON.stringify({ event: 'duplicate_load_sent' }));
            }
        };
    "# }),
    );
    b.ok("click", json!({ "selector": "#away" }));
    let start = Instant::now();
    let id = b.send("title", json!({ "request_timeout": 3000 }));
    b.wait_event("duplicate_load_sent");
    let result = b.recv(id);
    assert!(
        result.as_ref().is_err_and(|e| e.contains("timed out")),
        "{result:?} after {:?}; events: {:?}",
        start.elapsed(),
        b.stash
    );
    b.open(&format!("{base}/other"));
    assert_eq!(b.ok("title", json!({})), "other");
}

#[test]
fn cancelled_navigation_hint_releases_page_requests() {
    let mut b = Browser::spawn();
    let base = serve();
    b.open(&format!("{base}/more"));
    // Registered after the runtime's bubble listener: the reply must still
    // see the final cancellation of both links and form submissions.
    b.ok(
        "eval",
        json!({ "expression": "window.addEventListener('click', e => e.preventDefault()); window.addEventListener('submit', e => e.preventDefault())" }),
    );
    b.ok("click", json!({ "selector": "#away" }));
    assert_eq!(b.ok("title", json!({ "request_timeout": 5000 })), "more");
    b.ok(
        "type",
        json!({ "selector": "#go", "text": "cancelled", "submit": true }),
    );
    assert_eq!(b.ok("title", json!({ "request_timeout": 5000 })), "more");
}

#[test]
fn navigate_times_out_and_is_superseded() {
    let mut b = Browser::spawn();
    let base = serve();
    b.open(&format!("{base}/other"));

    // A server that never answers: navigate fails at its timeout, the tab still works.
    let t = Instant::now();
    let err = b.err(
        "navigate",
        json!({ "url": format!("{base}/hang"), "timeout": 1000 }),
    );
    assert!(err.contains("timed out"), "{err}");
    assert!(t.elapsed() >= Duration::from_millis(900) && t.elapsed() < Duration::from_secs(5));
    assert_eq!(b.ok("title", json!({})), "other");

    // A second navigate while one is pending fails the first instead of leaving it silent.
    let first = b.send("navigate", json!({ "url": format!("{base}/hang") }));
    b.ok("navigate", json!({ "url": format!("{base}/form") }));
    assert!(b.recv(first).unwrap_err().contains("superseded"));
    assert_eq!(b.ok("title", json!({})), "form");

    for delay in [0, 30] {
        // Cover both queued and already-started loads. GTK used to attribute
        // the older cancellation to its replacement when their URLs matched.
        let first = b.send("navigate", json!({ "url": format!("{base}/hang") }));
        std::thread::sleep(Duration::from_millis(delay));
        let next = b.send(
            "navigate",
            json!({ "url": format!("{base}/hang"), "timeout": 1000 }),
        );
        assert!(b.recv(first).unwrap_err().contains("superseded"));
        let err = b.recv(next).unwrap_err();
        assert!(
            err.contains("timed out"),
            "replacement failed on an old callback: {err}"
        );
        b.open(&format!("{base}/other"));
        assert_eq!(b.ok("title", json!({})), "other");
    }
}

#[test]
fn same_url_replacement_loads_the_new_document() {
    let mut b = Browser::spawn();
    let base = serve();
    b.open(&format!("{base}/form"));
    for delay in [0, 30] {
        let url = format!("{base}/slow");
        let first = b.send("navigate", json!({ "url": url }));
        std::thread::sleep(Duration::from_millis(delay));
        let next = b.send("navigate", json!({ "url": url }));
        assert!(b.recv(first).unwrap_err().contains("superseded"));
        assert_eq!(b.recv(next).unwrap()["url"], url);
        assert_eq!(b.ok("title", json!({})), "other");
    }
}

#[test]
fn old_document_cannot_finish_the_new_pages_idle_wait() {
    let mut b = Browser::spawn();
    let url = format!("{}/other", serve());
    b.open(&url);
    let old = b.ok("eval", json!({ "expression": "({document: __bruster.document, generation: __bruster.generation})" }));
    let start = Instant::now();
    let nav = b.send("navigate", json!({ "url": url, "until": "idle" }));
    // Load releases page requests even while navigate is waiting for idle.
    b.ok(
        "eval",
        json!({ "expression": format!(
        "window.ipc.postMessage(JSON.stringify({{...{old},idle:location.href}}))") }),
    );
    assert_eq!(b.recv(nav).unwrap()["url"], url);
    assert!(
        start.elapsed() >= Duration::from_millis(450),
        "old idle answered the new navigation"
    );
}

#[test]
fn page_requests_time_out_without_duplicate_replies() {
    let mut b = Browser::spawn();
    let base = serve();
    b.open(&format!("{base}/other"));
    for invalid in [json!(-1), json!(1.5), json!("200"), Value::Null] {
        assert!(b
            .err(
                "eval",
                json!({ "expression": "1", "request_timeout": invalid })
            )
            .contains("request_timeout"));
    }
    assert!(b
        .err(
            "eval",
            json!({ "expression": "window.zeroTimeoutRan = true", "request_timeout": 0 })
        )
        .contains("timed out"));
    assert_eq!(
        b.ok(
            "eval",
            json!({ "expression": "window.zeroTimeoutRan === undefined" })
        ),
        true
    );

    let start = Instant::now();
    let err = b.err(
        "eval",
        json!({ "expression": "new Promise(() => {})", "request_timeout": 200 }),
    );
    assert!(err.contains("timed out"), "{err}");
    assert!(
        start.elapsed() < Duration::from_secs(3),
        "{:?}",
        start.elapsed()
    );
    assert_eq!(b.ok("title", json!({})), "other");

    let id = b.send("eval", json!({ "expression": "new Promise(r => { window.finishLate = r; })", "request_timeout": 200 }));
    assert!(b.recv(id).unwrap_err().contains("timed out"));
    // Explicitly resolve the old promise: background timer throttling must not
    // turn this into a false pass where the late reply never actually happened.
    b.ok("eval", json!({ "expression": "finishLate(42)" }));
    assert_eq!(b.ok("title", json!({})), "other");
    assert!(
        !b.stash.iter().any(|v| v["id"] == id),
        "late reply: {:?}",
        b.stash
    );
}

#[test]
fn queued_page_requests_expire_without_running_after_navigation() {
    let mut b = Browser::spawn_env(&[], &[("BRUSTER_TRACE_NAV", "1")]);
    let base = serve();
    b.open(&format!("{base}/more"));
    b.ok(
        "eval",
        json!({ "expression": "document.getElementById('away').href = '/hang'" }),
    );
    b.ok("click", json!({ "selector": "#away" }));
    let start = Instant::now();
    assert!(b
        .err(
            "eval",
            json!({ "expression": "window.expiredCallRan = true", "request_timeout": 200 })
        )
        .contains("timed out"));
    assert!(start.elapsed() < Duration::from_secs(3));
    b.open(&format!("{base}/other"));
    assert_eq!(
        b.ok(
            "eval",
            json!({ "expression": "window.expiredCallRan === undefined" })
        ),
        true
    );
}

#[test]
fn page_request_deadlines_survive_redispatch() {
    let mut b = Browser::spawn();
    let base = serve();
    b.open(&format!("{base}/other"));
    let start = Instant::now();
    let id = b.send(
        "eval",
        json!({ "expression": "new Promise(() => {})", "request_timeout": 2000 }),
    );
    // Let most of the deadline pass, then commit a new document. The old
    // promise is re-dispatched, but must not get a fresh two-second budget.
    std::thread::sleep(Duration::from_millis(1400));
    b.open(&format!("{base}/form"));
    assert!(b.recv(id).unwrap_err().contains("timed out"));
    assert!(
        start.elapsed() < Duration::from_millis(3000),
        "{:?}",
        start.elapsed()
    );
    assert_eq!(b.ok("title", json!({})), "form");
}

#[test]
fn busy_page_does_not_block_native_commands() {
    let mut b = Browser::spawn();
    let base = serve();
    b.open(&format!("{base}/other"));
    let start = Instant::now();
    assert!(b
        .err(
            "eval",
            json!({ "expression": "(() => { for (;;) {} })()", "request_timeout": 200 })
        )
        .contains("timed out"));
    assert!(start.elapsed() < Duration::from_secs(3));
    assert_eq!(b.ok("tabs", json!({})).as_array().unwrap().len(), 1);
    assert!(b
        .err("title", json!({ "request_timeout": 200 }))
        .contains("timed out"));
}

#[test]
fn page_cannot_break_ipc_by_replacing_json_stringify() {
    let mut b = Browser::spawn();
    let base = serve();
    b.open(&format!("{base}/other"));
    b.ok("eval", json!({ "expression": "JSON.stringify = () => 'broken'; document.querySelector = () => null" }));
    assert_eq!(b.ok("text", json!({ "selector": "p" })), "other page");
    assert!(b
        .ok("snapshot", json!({ "format": "text" }))
        .as_str()
        .unwrap()
        .contains("other page"));
}

#[test]
fn last_tab_stays_open_and_new_tab_load_is_bounded() {
    let mut b = Browser::spawn();
    let base = serve();
    b.open(&format!("{base}/other"));
    assert!(b.err("close_tab", json!({})).contains("last tab"));
    assert_eq!(b.ok("title", json!({})), "other");
    let id = b.send(
        "new_tab",
        json!({ "url": format!("{base}/hang"), "timeout": 300 }),
    );
    // Native window/web-process construction is synchronous and can take
    // seconds on CI. Its timeout cannot be handled until construction returns.
    let tabs = b.ok("tabs", json!({}));
    assert_eq!(tabs.as_array().unwrap().len(), 2);
    let start = Instant::now();
    assert!(b.recv(id).unwrap_err().contains("timed out"));
    assert!(
        start.elapsed() < Duration::from_secs(3),
        "{:?}",
        start.elapsed()
    );
    assert_eq!(b.ok("title", json!({})), "other");
    let tab = tabs
        .as_array()
        .unwrap()
        .iter()
        .find(|t| t["current"] == false)
        .unwrap()["tab"]
        .clone();
    b.ok(
        "navigate",
        json!({ "tab": tab, "url": format!("{base}/form") }),
    );
    assert_eq!(b.ok("title", json!({ "tab": tab })), "form");
    b.ok("close_tab", json!({ "tab": tab }));
    assert_eq!(b.ok("title", json!({})), "other");
}

#[test]
fn odd_documents() {
    let mut b = Browser::spawn();
    let base = serve();

    // XML and JSON have no <body>: snapshot and text still answer.
    b.open(&format!("{base}/xml"));
    let snap = b.ok("snapshot", json!({ "format": "text" }));
    assert!(snap.as_str().unwrap().contains("x"), "{snap}");
    b.open(&format!("{base}/json"));
    // WebView2 pretty-prints JSON, so only the key is stable across engines.
    assert!(b
        .ok("text", json!({ "selector": "body" }))
        .as_str()
        .unwrap()
        .contains("\"a\""));

    // Redirects land on the final url.
    let r = b.ok("navigate", json!({ "url": format!("{base}/redirect") }));
    assert!(r["url"].as_str().unwrap().ends_with("/other"));

    // pushState navigation: url follows, back returns, no load event needed.
    b.open(&format!("{base}/spa"));
    b.ok("click", json!({ "selector": "#go" }));
    assert!(b
        .ok("url", json!({}))
        .as_str()
        .unwrap()
        .ends_with("/spa/about"));
    assert_eq!(b.ok("text", json!({ "selector": "#p" })), "about");
    let back = b.ok("back", json!({}));
    assert!(back["url"].as_str().unwrap().ends_with("/spa"));
    assert!(b.ok("url", json!({})).as_str().unwrap().ends_with("/spa"));
    let forward = b.ok("forward", json!({}));
    assert!(forward["url"].as_str().unwrap().ends_with("/spa/about"));
    assert_eq!(b.ok("forward", json!({})), Value::Null);
    b.ok("eval", json!({ "expression": "history.pushState({step: 1}, '', location.href); history.pushState({step: 2}, '', location.href)" }));
    assert!(b.ok("back", json!({}))["url"]
        .as_str()
        .unwrap()
        .ends_with("/spa/about"));
    assert_eq!(
        b.ok("eval", json!({ "expression": "history.state.step" })),
        1
    );
    assert!(b.ok("forward", json!({}))["url"]
        .as_str()
        .unwrap()
        .ends_with("/spa/about"));
    assert_eq!(
        b.ok("eval", json!({ "expression": "history.state.step" })),
        2
    );

    // Five nested open shadow roots.
    b.open(&format!("{base}/shadowdeep"));
    b.ok("click", json!({ "selector": "#deep" }));
    assert_eq!(b.ok("title", json!({})), "deep-clicked");
}

#[test]
fn protocol_abuse_keeps_serving() {
    let mut b = Browser::spawn();
    let base = serve();
    b.open(&format!("{base}/other"));

    for line in [
        r#"{"id":"abc","method":"title"}"#,
        r#"{"id":1,"method":"title","tab":"1"}"#,
        r#"{"id":1}"#,
        r#"[1,2,3]"#,
        r#"null"#,
    ] {
        writeln!(b.stdin, "{line}").unwrap();
        let v = b.take("bad request error", |v| {
            v["error"]
                .as_str()
                .is_some_and(|e| e.starts_with("bad request"))
        });
        assert!(v.get("id").is_none(), "{v}");
    }
    assert!(b
        .err("title", json!([1, 2]))
        .contains("params must be an object"));
    assert!(b
        .err("click", json!("x"))
        .contains("params must be an object"));
    assert!(b
        .err("click", json!({ "selector": "###", "timeout": 100 }))
        .contains("not a valid selector"));
    assert!(b
        .err("find", json!({ "regex": "(" }))
        .contains("regular expression"));
    assert!(b.err("attr", json!({ "selector": "p" })).contains("name"));
    assert!(b
        .err("navigate", json!({ "url": "nope" }))
        .contains("invalid url"));
    assert!(b
        .err("new_tab", json!({ "url": "nope" }))
        .contains("invalid url"));

    // A 3 MB line is fine.
    let long = "x".repeat(3_000_000);
    assert_eq!(
        b.ok("eval", json!({ "expression": format!("'{long}'.length") })),
        3_000_000
    );

    // 20 requests sent without waiting come back in order.
    let ids: Vec<u64> = (0..20)
        .map(|i| b.send("eval", json!({ "expression": i.to_string() })))
        .collect();
    for (i, id) in ids.iter().enumerate() {
        assert_eq!(b.recv(*id).unwrap(), i);
    }
    assert_eq!(b.ok("title", json!({})), "other");
}

#[test]
fn limits() {
    let mut b = Browser::spawn();
    let base = serve();
    b.open(&format!("{base}/other"));

    // Oversized windows crash WebKit; refuse them.
    for (w, h) in [(30000, 30000), (0, 0), (1, 100000)] {
        assert!(
            b.err("resize", json!({ "width": w, "height": h }))
                .contains("between"),
            "{w}x{h}"
        );
    }
    assert_eq!(
        b.ok("resize", json!({ "width": 320, "height": 200 }))["width"],
        320
    );
    assert_eq!(
        b.ok("resize", json!({ "width": 1280, "height": 800 }))["width"],
        1280
    );

    // 10000 elements: default snapshot caps and flags it, full one is bounded in time.
    b.open(&format!("{base}/big"));
    let snap = b.ok("snapshot", json!({}));
    assert_eq!(snap["elements"].as_array().unwrap().len(), 1000);
    assert_eq!(snap["truncated"], true);
    // Bound hangs without treating shared CI runners as performance benchmarks.
    // Intel macOS can take more than three seconds while other browser tests run.
    let all = b.ok(
        "snapshot",
        json!({ "max": 100000, "request_timeout": 10000 }),
    );
    assert_eq!(all["elements"].as_array().unwrap().len(), 10000);
    assert_eq!(
        b.ok("find", json!({ "text": "link 4999" }))["elements"]
            .as_array()
            .unwrap()
            .len(),
        1
    );
    b.ok("click", json!({ "selector": "#i4999" }));
    assert_eq!(
        b.ok("eval", json!({ "expression": "document.activeElement.id" })),
        "i4999"
    );

    // Unicode survives fill and type.
    b.open(&format!("{base}/form"));
    let text = "héllo 日本語 🎉 مرحبا";
    b.ok("fill", json!({ "selector": "#q", "value": text }));
    assert_eq!(b.ok("eval", json!({ "expression": "q.value" })), text);
    b.ok("type", json!({ "selector": "#ce", "text": "a🎉b" }));
    assert_eq!(b.ok("text", json!({ "selector": "#ce" })), "a🎉b");
}

#[test]
fn tabs_and_memory_recover() {
    let mut b = Browser::spawn();
    let base = serve();
    b.open(&format!("{base}/other"));
    let pid = b.child.id();
    let before = rss_mb(pid);

    // Ten tabs, then closed: memory comes back.
    let tabs: Vec<u64> = (0..10)
        .map(|_| {
            b.ok("new_tab", json!({ "url": format!("{base}/other") }))["tab"]
                .as_u64()
                .unwrap()
        })
        .collect();
    assert_eq!(b.ok("tabs", json!({})).as_array().unwrap().len(), 11);
    let peak = rss_mb(pid);
    for t in tabs {
        b.ok("close_tab", json!({ "tab": t }));
        assert_eq!(
            b.ok("title", json!({})),
            "other",
            "closing a tab terminated the surviving view"
        );
    }
    b.ok("wait_for", json!({ "time": 2000 }));
    let after = rss_mb(pid);
    if before > 0 {
        assert!(
            after < before + (peak - before) / 4,
            "before {before} peak {peak} after {after}"
        );
    }

    // Closing the last tab is rejected; the current tab remains usable.
    assert!(b.err("close_tab", json!({})).contains("last tab"));
    b.open(&format!("{base}/form"));
    assert_eq!(b.ok("title", json!({})), "form");

    // 30 navigations with snapshots, then idle: the web process gives memory back.
    let start = rss_mb(pid);
    for i in 0..30 {
        b.open(&format!(
            "{base}/{}",
            if i % 2 == 0 { "big" } else { "other" }
        ));
        b.ok("snapshot", json!({}));
    }
    let busy = rss_mb(pid);
    if start > 0 {
        // GC and cache purges run on their own timers; give them up to 40 s.
        let t = Instant::now();
        let mut settled = busy;
        while settled >= start + (busy - start) / 2 && t.elapsed() < Duration::from_secs(40) {
            b.ok("wait_for", json!({ "time": 2000 }));
            settled = rss_mb(pid);
        }
        assert!(
            settled < start + (busy - start) / 2,
            "start {start} busy {busy} settled {settled}"
        );
    }
}

#[test]
fn stdin_eof_exits_cleanly() {
    let mut b = Browser::spawn();
    let base = serve();
    b.open(&format!("{base}/other"));
    b.closed = true;
    b.close_stdin();
    let status = b.child.wait().unwrap();
    assert!(status.success(), "{status}");
}

#[test]
fn window_commands_persist_in_hidden_runs() {
    let root = std::env::temp_dir().join(format!("bruster-window-edge-{}", std::process::id()));
    std::fs::create_dir_all(&root).unwrap();
    let profile = root.join("profile");
    let metadata = root.join("profile.bruster-window.json");
    for command in ["maximize", "minimize", "maximize"] {
        let mut b = Browser::spawn_with(&["--profile", profile.to_str().unwrap()]);
        let expected = if command == "maximize" {
            "maximized"
        } else {
            "minimized"
        };
        assert!(b
            .err(command, json!({ "tab": 999 }))
            .contains("no such tab"));
        assert_eq!(b.ok(command, json!({})), expected);
        assert_eq!(
            serde_json::from_slice::<Value>(&std::fs::read(&metadata).unwrap()).unwrap()["state"],
            expected
        );
        b.ok("close", json!({}));
        b.closed = true;
        assert!(b.child.wait().unwrap().success());
    }
    remove_profile_dir(&root);
}

#[test]
fn dark_and_light_persist_across_pages_and_runs() {
    let root = std::env::temp_dir().join(format!("bruster-dark-edge-{}", std::process::id()));
    std::fs::create_dir_all(&root).unwrap();
    let profile = root.join("profile");
    let script = root.join("init.js");
    std::fs::write(&script, "window.customInit = 42;").unwrap();
    let base = serve();
    for (flags, expected) in [(true, "dark"), (false, "dark"), (false, "light")] {
        let mut args = vec![
            "--profile",
            profile.to_str().unwrap(),
            "--init-script",
            script.to_str().unwrap(),
        ];
        if flags {
            args.push("--dark");
        }
        let mut b = Browser::spawn_with(&args);
        b.open(&format!("{base}/other"));
        let scheme = "getComputedStyle(document.documentElement).colorScheme";
        assert_eq!(b.ok("eval", json!({"expression": scheme})), expected);
        assert_eq!(b.ok("eval", json!({"expression": "customInit"})), 42);
        for mode in ["dark", "light"] {
            assert_eq!(b.ok(mode, json!({})), mode);
            assert_eq!(b.ok("eval", json!({"expression": scheme})), mode);
            b.open(&format!("{base}/form"));
            assert_eq!(b.ok("eval", json!({"expression": scheme})), mode);
            // The document-start script still holds the preference the tab
            // was created with. Every navigation milestone must apply the
            // current preference before serving the next page request.
            for until in ["dom", "load", "idle"] {
                for page in ["other", "form"] {
                    b.ok(
                        "navigate",
                        json!({"url": format!("{base}/{page}"), "until": until}),
                    );
                    assert_eq!(b.ok("eval", json!({"expression": scheme})), mode);
                }
            }
            let tab = b.ok("new_tab", json!({"url": format!("{base}/other")}))["tab"].clone();
            assert_eq!(
                b.ok("eval", json!({"tab": tab, "expression": scheme})),
                mode
            );
            b.ok("close_tab", json!({"tab": tab}));
        }
        if flags {
            b.ok("dark", json!({}));
        }
        b.ok("close", json!({}));
        b.closed = true;
        assert!(b.child.wait().unwrap().success());
    }
    remove_profile_dir(&root);
}

#[test]
#[cfg_attr(not(target_os = "linux"), ignore = "--no-images is WebKitGTK only")]
fn no_images_flag() {
    let mut b = Browser::spawn_with(&["--no-images"]);
    let base = serve();
    b.open(&format!("{base}/"));
    // The smoke page has no images; inject one and check it never loads.
    b.ok("eval", json!({ "expression": "const i = new Image(); i.src = '/other?img'; document.body.appendChild(i); window.__i = i; 1" }));
    b.ok("wait_for", json!({ "time": 500 }));
    assert_eq!(b.ok("eval", json!({ "expression": "__i.naturalWidth" })), 0);
    assert_eq!(b.ok("eval", json!({ "expression": "performance.getEntriesByType('resource').filter(e => e.name.includes('img')).length" })), 0);
}

#[test]
fn text_and_value_edges() {
    let mut b = Browser::spawn();
    let base = serve();
    b.open(&format!("{base}/form"));
    assert_eq!(
        b.ok("type", json!({ "selector": "#q", "text": "" })),
        Value::Null
    );
    assert_eq!(b.ok("press", json!({ "key": "Escape" })), Value::Null);
    assert_eq!(
        b.ok("wait_for", json!({ "idle": true, "timeout": 3000 })),
        Value::Null
    );
}
