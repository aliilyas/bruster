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
    b.open(&format!("{base}/beforeunload"));

    b.ok("click", json!({ "selector": "#l" }));
    assert_eq!(
        b.ok("title", json!({})),
        "other",
        "beforeunload prompt blocked the tab"
    );
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
    b.ok("back", json!({}));
    assert!(b.ok("url", json!({})).as_str().unwrap().ends_with("/spa"));

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
    let t = Instant::now();
    let all = b.ok("snapshot", json!({ "max": 100000 }));
    assert_eq!(all["elements"].as_array().unwrap().len(), 10000);
    assert!(t.elapsed() < Duration::from_secs(3), "{:?}", t.elapsed());
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

    // Closing the last tab leaves no current one; new_tab makes it current again.
    b.ok("close_tab", json!({}));
    assert!(b.err("title", json!({})).contains("no such tab"));
    b.ok("new_tab", json!({ "url": format!("{base}/form") }));
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
    std::fs::remove_dir_all(root).unwrap();
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
    std::fs::remove_dir_all(root).unwrap();
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
