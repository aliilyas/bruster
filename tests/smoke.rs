//! Spawns the binary, drives localhost pages over stdio, checks the answers.
//! Needs a display (macOS: none extra, Linux: `xvfb-run cargo test`).

mod common;

use std::io::{BufRead, BufReader, Read, Write};
use std::net::TcpListener;
use std::process::{Command, Stdio};
use std::time::{Duration, Instant};

use serde_json::{json, Value};

use common::*;

#[test]
fn drives_a_page() {
    let mut b = Browser::spawn();
    let base = serve();

    let nav = b.ok("navigate", json!({ "url": format!("{base}/") }));
    assert!(nav["url"].as_str().unwrap().starts_with("http://127.0.0.1"));

    assert_eq!(b.ok("title", json!({})), "smoke");
    assert_eq!(b.ok("eval", json!({ "expression": "1 + 2" })), 3);

    // Snapshot lists visible elements only; hidden link must be absent.
    let snap = b.ok("snapshot", json!({}));
    let els = snap["elements"].as_array().unwrap();
    assert!(els
        .iter()
        .any(|e| e["role"] == "heading" && e["name"] == "Hello"));
    assert!(els
        .iter()
        .any(|e| e["role"] == "button" && e["name"] == "Go"));
    assert!(!els.iter().any(|e| e["name"] == "hidden"));

    // Interact via ref from the snapshot, then via selector.
    let input_ref = els.iter().find(|e| e["role"] == "textbox").unwrap()["ref"].clone();
    b.ok("fill", json!({ "ref": input_ref, "value": "bob" }));
    b.ok("click", json!({ "selector": "#go" }));
    b.ok("wait_for", json!({ "text": "hi bob", "timeout": 2000 }));
    assert_eq!(b.ok("text", json!({ "selector": "#out" })), "hi bob");

    // PNG magic bytes prove the native snapshot path works.
    let path = std::env::temp_dir().join(format!("bruster-smoke-{}.png", std::process::id()));
    let shot = b.ok("screenshot", json!({ "path": path }));
    assert!(shot["bytes"].as_u64().unwrap() > 0);
    let bytes = std::fs::read(&path).unwrap();
    let _ = std::fs::remove_file(&path);
    assert_eq!(&bytes[..8], b"\x89PNG\r\n\x1a\n");

    // Element clip: PNG for the input only (WebView2 cannot crop).
    let rect = b.ok("rect", json!({ "selector": "#name" }));
    assert!(rect["width"].as_u64().unwrap() > 0);
    if !cfg!(target_os = "windows") {
        let clip = b.ok("screenshot", json!({ "clip": rect }));
        assert!(clip["png_base64"]
            .as_str()
            .unwrap()
            .starts_with("iVBORw0KGgo"));
    }
    let err = b.err(
        "screenshot",
        json!({ "clip": { "x": 0, "y": 0, "width": 0, "height": 0 } }),
    );
    assert!(err.contains("non-zero"));

    // Full page is taller than the viewport thanks to the 3000px spacer.
    let full = b.ok("screenshot", json!({ "full": true, "path": path }));
    let shot_bytes = shot["bytes"].as_u64().unwrap();
    let _ = std::fs::remove_file(&path);
    assert!(
        full["bytes"].as_u64().unwrap() > shot_bytes / 2,
        "full page capture suspiciously small"
    );

    // Network log sees the page's fetch; clear empties it.
    let net = b.ok("network", json!({ "clear": true }));
    assert!(net
        .as_array()
        .unwrap()
        .iter()
        .any(|e| e["type"] == "fetch" && e["url"].as_str().unwrap().ends_with("/api")));
    assert_eq!(b.ok("network", json!({})).as_array().unwrap().len(), 0);
}

#[test]
fn forms_and_input() {
    let mut b = Browser::spawn();
    let base = serve();
    b.open(&format!("{base}/form"));

    // type fires one input event per character.
    b.ok("type", json!({ "selector": "#typed", "text": "abc" }));
    assert_eq!(
        b.ok("attr", json!({ "selector": "#typed", "name": "data-n" })),
        "3"
    );
    assert_eq!(
        b.ok(
            "eval",
            json!({ "expression": "document.getElementById('typed').value" })
        ),
        "abc"
    );

    // type and fill both work on contenteditable.
    b.ok("type", json!({ "selector": "#ce", "text": "ab" }));
    assert_eq!(b.ok("text", json!({ "selector": "#ce" })), "ab");
    b.ok("fill", json!({ "selector": "#ce", "value": "zz" }));
    assert_eq!(b.ok("text", json!({ "selector": "#ce" })), "zz");

    // Enter submits the form; Escape reaches the document listener.
    b.ok("fill", json!({ "selector": "#q", "value": "zed" }));
    b.ok("press", json!({ "selector": "#q", "key": "Enter" }));
    assert_eq!(b.ok("text", json!({ "selector": "#out" })), "submitted:zed");
    b.ok("press", json!({ "key": "Escape" }));
    assert_eq!(b.ok("text", json!({ "selector": "#out" })), "esc");

    // select: single by value, multi by text.
    assert_eq!(
        b.ok("select", json!({ "selector": "#s", "value": "b" })),
        json!(["b"])
    );
    assert_eq!(
        b.ok("select", json!({ "selector": "#m", "value": ["X", "Y"] })),
        json!(["x", "y"])
    );

    // check is idempotent and reversible.
    assert_eq!(b.ok("check", json!({ "selector": "#c" })), true);
    assert_eq!(b.ok("check", json!({ "selector": "#c" })), true);
    assert_eq!(
        b.ok("check", json!({ "selector": "#c", "checked": false })),
        false
    );

    b.ok("hover", json!({ "selector": "#hov" }));
    assert_eq!(b.ok("text", json!({ "selector": "#hov" })), "hovered");

    assert_eq!(
        b.ok("attr", json!({ "selector": "#q", "name": "data-k" })),
        "v"
    );
    assert_eq!(
        b.ok("attr", json!({ "selector": "#q", "name": "missing" })),
        Value::Null
    );
    assert!(b
        .ok("html", json!({ "selector": "#lnk" }))
        .as_str()
        .unwrap()
        .starts_with("<a id=\"lnk\""));
    assert_eq!(b.ok("count", json!({ "selector": "select" })), 2);
    assert_eq!(b.ok("count", json!({ "selector": ".nothing" })), 0);

    // text with max truncates and appends an ellipsis.
    let short = b.ok("text", json!({ "selector": "body", "max": 5 }));
    assert_eq!(short.as_str().unwrap().chars().count(), 6);

    // scroll to an element, then back to the top by delta.
    let pos = b.ok("scroll", json!({ "selector": "#far" }));
    assert!(pos["y"].as_f64().unwrap() > 0.0);
    let pos = b.ok("scroll", json!({ "y": -100000 }));
    assert_eq!(pos["y"], 0);
}

#[test]
fn snapshot_details() {
    let mut b = Browser::spawn();
    let base = serve();
    b.open(&format!("{base}/form"));

    b.ok("fill", json!({ "selector": "#q", "value": "zed" }));
    b.ok("check", json!({ "selector": "#c" }));

    let snap = b.ok("snapshot", json!({}));
    let els = snap["elements"].as_array().unwrap();
    let by_role = |role: &str| els.iter().filter(|e| e["role"] == role).collect::<Vec<_>>();

    assert_eq!(snap["title"], "form");
    assert!(by_role("link")[0]["href"]
        .as_str()
        .unwrap()
        .ends_with("/other"));
    assert!(by_role("textbox").iter().any(|e| e["value"] == "zed"));
    assert_eq!(by_role("checkbox")[0]["checked"], true);
    assert_eq!(
        by_role("button")
            .iter()
            .find(|e| e["name"] == "Nope")
            .unwrap()["disabled"],
        true
    );
    assert_eq!(
        by_role("combobox").len(),
        1,
        "multi-select is a listbox, not a combobox"
    );

    // Scoped snapshot excludes the heading outside the form, refs restart.
    let scoped = b.ok("snapshot", json!({ "selector": "#f" }));
    let els = scoped["elements"].as_array().unwrap();
    assert!(!els.iter().any(|e| e["role"] == "heading"));
    assert_eq!(els[0]["ref"], "e1");

    // Old refs are invalid after a new snapshot.
    let err = b.err("click", json!({ "ref": "e99" }));
    assert!(err.contains("stale or unknown ref"));
}

#[test]
fn waits() {
    let mut b = Browser::spawn();
    let base = serve();
    b.open(&format!("{base}/form"));

    // attached: element appears later.
    b.ok("eval", json!({ "expression": "setTimeout(() => { const d = document.createElement('div'); d.id = 'new'; document.body.appendChild(d); }, 200)" }));
    b.ok(
        "wait_for",
        json!({ "selector": "#new", "state": "attached", "timeout": 3000 }),
    );

    // hidden: element disappears later.
    b.ok("eval", json!({ "expression": "setTimeout(() => document.getElementById('hov').style.display = 'none', 200)" }));
    b.ok(
        "wait_for",
        json!({ "selector": "#hov", "state": "hidden", "timeout": 3000 }),
    );

    // url: hash change without navigation.
    b.ok(
        "eval",
        json!({ "expression": "setTimeout(() => location.hash = '#z', 200)" }),
    );
    b.ok("wait_for", json!({ "url": "#z", "timeout": 3000 }));

    // A pending wait is re-run in the next document instead of dying with the old one.
    let pending = b.send(
        "wait_for",
        json!({ "text": "other page", "timeout": 10000 }),
    );
    b.ok("navigate", json!({ "url": format!("{base}/other") }));
    assert!(b.recv(pending).is_ok());
}

#[test]
fn history_and_cookies() {
    let mut b = Browser::spawn();
    let base = serve();

    b.open(&format!("{base}/form"));
    b.open(&format!("{base}/other"));
    assert!(b.ok("url", json!({})).as_str().unwrap().ends_with("/other"));

    // History moves reply with the landed url once the page is loaded.
    let back = b.ok("back", json!({}));
    assert!(back["url"].as_str().unwrap().ends_with("/form"));
    assert!(b.ok("url", json!({})).as_str().unwrap().ends_with("/form"));

    let fwd = b.ok("forward", json!({}));
    assert!(fwd["url"].as_str().unwrap().ends_with("/other"));
    assert_eq!(b.ok("title", json!({})), "other");

    // Nowhere to go: null instead of a hang.
    assert_eq!(b.ok("forward", json!({})), Value::Null);

    b.ok(
        "eval",
        json!({ "expression": "document.body.dataset.mark = '1'" }),
    );
    b.ok("reload", json!({}));
    assert_eq!(
        b.ok(
            "eval",
            json!({ "expression": "document.body.dataset.mark" })
        ),
        Value::Null
    );

    // Server-set and client-set cookies both show up.
    b.open(&format!("{base}/cookie"));
    b.ok(
        "set_cookie",
        json!({ "name": "cli", "value": "2", "domain": "127.0.0.1", "path": "/" }),
    );
    let cookies = b.ok("cookies", json!({}));
    let names: Vec<&str> = cookies
        .as_array()
        .unwrap()
        .iter()
        .map(|c| c["name"].as_str().unwrap())
        .collect();
    assert!(names.contains(&"srv"), "server cookie missing: {names:?}");
    assert!(names.contains(&"cli"), "client cookie missing: {names:?}");
    assert!(b
        .err("set_cookie", json!({ "name": "x" }))
        .contains("need name and value"));
}

#[test]
fn tabs() {
    let mut b = Browser::spawn();
    let base = serve();
    b.open(&format!("{base}/"));

    // Explicit new_tab, then target=_blank opens one too.
    let t2 = b.ok("new_tab", json!({ "url": format!("{base}/form") }))["tab"]
        .as_u64()
        .unwrap();
    b.wait_load(t2);
    assert_eq!(b.ok("title", json!({ "tab": t2 })), "form");
    assert_eq!(b.ok("tabs", json!({})).as_array().unwrap().len(), 2);

    b.ok("click", json!({ "selector": "#blank" }));
    let opened = b.wait_event("tab_opened");
    assert!(opened["url"].as_str().unwrap().ends_with("/other"));
    let t3 = opened["tab"].as_u64().unwrap();
    b.wait_load(t3);
    assert_eq!(b.ok("title", json!({ "tab": t3 })), "other");

    // switch_tab changes the default target.
    b.ok("switch_tab", json!({ "tab": t2 }));
    assert_eq!(b.ok("title", json!({})), "form");
    let tabs = b.ok("tabs", json!({}));
    assert!(tabs
        .as_array()
        .unwrap()
        .iter()
        .any(|t| t["tab"] == t2 && t["current"] == true));

    // Closing the current tab fails its pending work and moves current to the lowest id.
    let pending = b.send(
        "wait_for",
        json!({ "selector": "#never", "timeout": 10000 }),
    );
    b.ok("close_tab", json!({}));
    assert_eq!(b.recv(pending).unwrap_err(), "tab closed");
    assert_eq!(b.ok("title", json!({})), "smoke");
    assert_eq!(b.ok("tabs", json!({})).as_array().unwrap().len(), 2);

    assert!(b
        .err("close_tab", json!({ "tab": 99 }))
        .contains("no such tab"));
    assert!(b
        .err("switch_tab", json!({ "tab": 99 }))
        .contains("no such tab"));
    assert!(b
        .err("switch_tab", json!({}))
        .contains("missing params.tab"));
    assert!(b.err("title", json!({ "tab": 99 })).contains("no such tab"));
}

#[test]
fn close_answers_pending_navigate() {
    let mut b = Browser::spawn();
    let base = serve();

    // The page takes SLOW_DELAY to answer; close arrives while navigate is
    // still waiting for the load. Shutdown must fail it, not drop it.
    let nav = b.send("navigate", json!({ "url": format!("{base}/slow") }));
    let closing = b.send("close", Value::Null);

    assert!(b.recv(closing).is_ok(), "close itself must still answer");
    assert!(
        b.recv(nav).is_err(),
        "pending navigate must get a reply instead of being dropped by exit"
    );
    b.closed = true;
}

#[test]
fn errors_do_not_hang() {
    let mut b = Browser::spawn();
    let base = serve();
    b.open(&format!("{base}/"));

    assert!(b
        .err("click", json!({ "selector": "#nope", "timeout": 200 }))
        .contains("no element matches"));
    assert!(b
        .err("click", json!({}))
        .contains("need params.selector or params.ref"));
    assert!(b
        .err("wait_for", json!({ "selector": "#nope", "timeout": 200 }))
        .contains("timed out"));
    assert!(b.err("bogus", json!({})).contains("unknown method"));
    assert!(b.err("navigate", json!({})).contains("missing params.url"));
    assert!(b
        .err("eval", json!({ "expression": "throw new Error('boom')" }))
        .contains("boom"));
    assert_eq!(
        b.ok("eval", json!({ "expression": "undefined" })),
        Value::Null
    );

    // Malformed line: error without id, process keeps serving.
    writeln!(b.stdin, "not json").unwrap();
    let v = b.next_line();
    assert!(v["error"].as_str().unwrap().starts_with("bad request"));
    assert!(v.get("id").is_none());
    assert_eq!(b.ok("title", json!({})), "smoke");
}

#[test]
fn dialogs_frames_and_actionability() {
    let mut b = Browser::spawn();
    let base = serve();
    b.open(&format!("{base}/extra"));

    // Dialogs are answered instead of blocking; default is accept.
    b.ok("click", json!({ "selector": "#al" }));
    assert_eq!(b.ok("text", json!({ "selector": "#out" })), "c:true");
    let ev = b.wait_event("dialog");
    assert_eq!(ev["type"], "confirm");
    assert_eq!(ev["message"], "sure?");
    assert_eq!(ev["tab"], 1);
    b.ok("dialog", json!({ "accept": false }));
    b.ok("click", json!({ "selector": "#al" }));
    assert_eq!(b.ok("text", json!({ "selector": "#out" })), "c:false");
    b.ok("dialog", json!({ "accept": true, "text": "zoe" }));
    b.ok("click", json!({ "selector": "#pr" }));
    assert_eq!(b.ok("text", json!({ "selector": "#out" })), "p:zoe");
    let seen = b.ok("dialog", json!({ "clear": true }));
    assert_eq!(seen.as_array().unwrap().len(), 3);
    assert_eq!(b.ok("dialog", json!({})).as_array().unwrap().len(), 0);

    // Selectors reach into same-origin iframes and open shadow roots.
    assert_eq!(b.ok("count", json!({ "selector": "#in" })), 1);
    b.ok("click", json!({ "selector": "#in" }));
    assert_eq!(b.ok("title", json!({})), "inner-clicked");
    b.ok("click", json!({ "selector": "#sh" }));
    assert_eq!(b.ok("title", json!({})), "shadow-clicked");
    let snap = b.ok("snapshot", json!({}));
    let names: Vec<&str> = snap["elements"]
        .as_array()
        .unwrap()
        .iter()
        .filter_map(|e| e["name"].as_str())
        .collect();
    assert!(
        names.contains(&"inner") && names.contains(&"shadow"),
        "{names:?}"
    );
    assert!(
        !names.iter().any(|n| n.starts_with("invisible")),
        "aria-hidden leaked: {names:?}"
    );

    // Actionability: disabled and covered elements fail with a reason; force bypasses.
    assert!(b
        .err("click", json!({ "selector": "#dis", "timeout": 300 }))
        .contains("is disabled"));
    assert!(b
        .err("click", json!({ "selector": "#under", "timeout": 300 }))
        .contains("covered by <div#over>"));
    b.ok("click", json!({ "selector": "#under", "force": true }));
    assert_eq!(b.ok("text", json!({ "selector": "#under" })), "clicked");
    b.ok(
        "eval",
        json!({ "expression": "setTimeout(() => document.getElementById('over').remove(), 200)" }),
    );
    b.ok("click", json!({ "selector": "#under" }));

    // Click by viewport coordinates.
    b.ok(
        "eval",
        json!({ "expression": "document.getElementById('under').textContent = 'reset'" }),
    );
    let r = b.ok("rect", json!({ "selector": "#under" }));
    let (x, y) = (
        r["x"].as_f64().unwrap() + 5.0,
        r["y"].as_f64().unwrap() + 5.0,
    );
    b.ok("click", json!({ "x": x, "y": y }));
    assert_eq!(b.ok("text", json!({ "selector": "#under" })), "clicked");

    // Console captures log, warn and uncaught errors.
    b.ok("wait_for", json!({ "time": 200 }));
    let log = b.ok("console", json!({ "clear": true }));
    let log = log.as_array().unwrap();
    assert!(
        log.iter()
            .any(|m| m["level"] == "log" && m["text"] == "hello {\"a\":1}"),
        "{log:?}"
    );
    assert!(log
        .iter()
        .any(|m| m["level"] == "warn" && m["text"] == "careful"));
    assert!(log
        .iter()
        .any(|m| m["level"] == "error" && m["text"].as_str().unwrap().contains("later boom")));
    assert_eq!(b.ok("console", json!({})).as_array().unwrap().len(), 0);
}

#[test]
fn input_extras() {
    let mut b = Browser::spawn();
    let base = serve();
    b.open(&format!("{base}/extra"));

    // Modifier combos, type with submit, drag and drop.
    b.ok("press", json!({ "selector": "#combo", "key": "Control+k" }));
    assert_eq!(
        b.ok(
            "eval",
            json!({ "expression": "document.getElementById('combo').value" })
        ),
        "ctrl-k"
    );
    b.ok(
        "type",
        json!({ "selector": "#sq", "text": "zz", "submit": true }),
    );
    assert_eq!(b.ok("text", json!({ "selector": "#out" })), "sub:zz");
    b.ok(
        "drag",
        json!({ "from": { "selector": "#src" }, "to": { "selector": "#dst" } }),
    );
    assert_eq!(b.ok("text", json!({ "selector": "#dst" })), "got:payload");

    // fill_form dispatches on field type.
    b.ok(
        "fill_form",
        json!({ "fields": [
        { "selector": "#sel", "value": "b" },
        { "selector": "#cb", "value": true },
        { "selector": "#fi", "value": "x" },
    ] }),
    );
    assert_eq!(
        b.ok(
            "eval",
            json!({ "expression": "[sel.value, cb.checked, fi.value].join()" })
        ),
        "b,true,x"
    );

    // upload reads local files and fires change.
    let dir = std::env::temp_dir();
    let f1 = dir.join(format!("bruster-up-{}.txt", std::process::id()));
    let f2 = dir.join(format!("bruster-up-{}.png", std::process::id()));
    std::fs::write(&f1, "hello").unwrap();
    std::fs::write(&f2, [0u8; 10]).unwrap();
    let names = b.ok("upload", json!({ "selector": "#up", "paths": [f1, f2] }));
    assert_eq!(names.as_array().unwrap().len(), 2);
    let out = b.ok("text", json!({ "selector": "#out" }));
    assert!(out.as_str().unwrap().contains(":5:text/plain,"), "{out}");
    assert!(out.as_str().unwrap().contains(":10:image/png"), "{out}");
    let _ = std::fs::remove_file(&f1);
    let _ = std::fs::remove_file(&f2);
    assert!(b
        .err(
            "upload",
            json!({ "selector": "#up", "paths": ["/nope/missing"] })
        )
        .contains("upload /nope/missing"));
    assert!(b
        .err("upload", json!({ "selector": "#fi", "paths": [] }))
        .contains("not a file input"));

    // find filters a snapshot, snapshot honours max and boxes.
    let found = b.ok("find", json!({ "text": "drag" }));
    let els = found["elements"].as_array().unwrap();
    assert_eq!(els.len(), 1);
    assert_eq!(els[0]["ref"], "e1");
    b.ok("click", json!({ "ref": "e1" }));
    let found = b.ok("find", json!({ "regex": "^inner$" }));
    assert_eq!(found["elements"].as_array().unwrap().len(), 1);
    let snap = b.ok("snapshot", json!({ "max": 2, "boxes": true }));
    assert_eq!(snap["elements"].as_array().unwrap().len(), 2);
    assert_eq!(snap["truncated"], true);
    assert!(snap["elements"][0]["box"]["width"].as_u64().unwrap() > 0);

    // wait_for: textGone and network idle; network_request exposes details.
    b.ok("eval", json!({ "expression": "out.textContent = 'gone-me'; setTimeout(() => out.textContent = '', 200)" }));
    b.ok(
        "wait_for",
        json!({ "textGone": "gone-me", "timeout": 3000 }),
    );
    b.ok("network", json!({ "clear": true }));
    b.ok(
        "eval",
        json!({ "expression": "fetch('/slow', { headers: { 'X-Req': '1' } })" }),
    );
    let t = Instant::now();
    b.ok("wait_for", json!({ "idle": true, "timeout": 5000 }));
    assert!(
        t.elapsed() >= SLOW_DELAY,
        "idle returned before the slow request finished"
    );
    let net = b.ok("network", json!({}));
    let slow = net
        .as_array()
        .unwrap()
        .iter()
        .find(|e| e["url"].as_str().unwrap().ends_with("/slow"))
        .unwrap();
    assert_eq!(slow["status"], 200);
    assert!(slow.get("body").is_none(), "list must not carry bodies");
    let detail = b.ok("network_request", json!({ "index": slow["index"] }));
    assert_eq!(detail["req_headers"]["x-req"], "1");
    assert_eq!(detail["res_headers"]["content-type"], "text/html");
    assert!(detail["body"].as_str().unwrap().contains("other page"));
    assert!(b
        .err("network_request", json!({ "index": 99 }))
        .contains("no fetch/xhr entry"));

    // resize changes the viewport the page sees.
    assert_eq!(
        b.ok("resize", json!({ "width": 800, "height": 600 })),
        json!({ "width": 800, "height": 600 })
    );
    b.ok("wait_for", json!({ "time": 200 }));
    assert_eq!(
        b.ok(
            "eval",
            json!({ "expression": "innerWidth + 'x' + innerHeight" })
        ),
        "800x600"
    );
    assert!(b
        .err("resize", json!({ "width": 10 }))
        .contains("need width and height"));
}

#[test]
fn snapshot_reads_plain_text() {
    let mut b = Browser::spawn();
    let base = serve();
    b.open(&format!("{base}/texts"));

    let snap = b.ok("snapshot", json!({}));
    let els = snap["elements"].as_array().unwrap();
    let texts: Vec<&str> = els
        .iter()
        .filter(|e| e["role"] == "text")
        .filter_map(|e| e["text"].as_str())
        .collect();
    for want in [
        "You logged in",
        "Beta only text",
        "Gamma",
        "bold",
        "code block",
        "Para inline tail",
        "nested only text",
    ] {
        assert!(texts.contains(&want), "missing {want:?} in {texts:?}");
    }
    assert!(
        !texts
            .iter()
            .any(|t| t.contains("hidden") || t.contains("notText")),
        "{texts:?}"
    );
    assert!(
        !texts
            .iter()
            .any(|t| t.starts_with("Para") && *t != "Para inline tail"),
        "p text must stay one item: {texts:?}"
    );

    // Document order: the flash text comes before its close link.
    let flash = els
        .iter()
        .position(|e| e["text"] == "You logged in")
        .unwrap();
    let close = els
        .iter()
        .position(|e| e["role"] == "link" && e["name"] == "×")
        .unwrap();
    assert!(flash < close);

    // A text ref acts on its element.
    let beta = els.iter().find(|e| e["text"] == "Beta only text").unwrap();
    assert_eq!(
        b.ok("text", json!({ "ref": beta["ref"] })),
        "Beta only text"
    );

    // find sees plain text too; link named from its image; unlabeled checkbox has no name.
    assert_eq!(
        b.ok("find", json!({ "text": "logged in" }))["elements"]
            .as_array()
            .unwrap()
            .len(),
        1
    );
    assert!(
        els.iter()
            .any(|e| e["role"] == "link" && e["name"] == "Fork me"),
        "{els:?}"
    );
    assert_eq!(
        els.iter().find(|e| e["role"] == "checkbox").unwrap()["name"],
        ""
    );

    // max 0 means no elements, not the default cap.
    assert_eq!(
        b.ok("snapshot", json!({ "max": 0 }))["elements"]
            .as_array()
            .unwrap()
            .len(),
        0
    );

    // Frameset documents are walked like iframes.
    b.open(&format!("{base}/frames"));
    let snap = b.ok("snapshot", json!({}));
    let texts: Vec<&str> = snap["elements"]
        .as_array()
        .unwrap()
        .iter()
        .filter_map(|e| e["text"].as_str())
        .collect();
    assert!(
        texts.contains(&"Beta only text") && texts.contains(&"other page"),
        "{texts:?}"
    );

    // Snapshot right after the load starts waits for the body instead of crashing.
    b.send("navigate", json!({ "url": format!("{base}/slowbody") }));
    b.wait_event("navigating");
    let snap = b.ok("snapshot", json!({}));
    assert!(snap["elements"]
        .as_array()
        .unwrap()
        .iter()
        .any(|e| e["text"] == "Beta only text"));
}

#[test]
fn keys_carry_legacy_codes() {
    let mut b = Browser::spawn();
    let base = serve();
    b.open(&format!("{base}/more"));

    b.ok("press", json!({ "selector": "#k", "key": "Shift+A" }));
    b.ok("press", json!({ "selector": "#k", "key": "Enter" }));
    b.ok("press", json!({ "selector": "#k", "key": "ArrowDown" }));
    b.ok("type", json!({ "selector": "#k", "text": "7 " }));
    let keys = b.ok("eval", json!({ "expression": "JSON.stringify(keys)" }));
    assert_eq!(
        keys,
        r#"[["A","KeyA",65,65],["Enter","Enter",13,13],["ArrowDown","ArrowDown",40,40],["7","Digit7",55,55],[" ","Space",32,32]]"#
    );

    // A printable press inserts its character, like type does.
    b.ok("fill", json!({ "selector": "#k", "value": "" }));
    b.ok("press", json!({ "selector": "#k", "key": "x" }));
    assert_eq!(b.ok("eval", json!({ "expression": "k.value" })), "x");

    // Number inputs: each prefix of a valid number is kept, letters are dropped.
    b.ok("type", json!({ "selector": "#num", "text": "-1.5e3" }));
    assert_eq!(b.ok("eval", json!({ "expression": "num.value" })), "-1.5e3");
    b.ok("fill", json!({ "selector": "#num", "value": "" }));
    b.ok("type", json!({ "selector": "#num", "text": "12a3" }));
    assert_eq!(b.ok("eval", json!({ "expression": "num.value" })), "123");
}

#[test]
fn rejects_wrong_targets() {
    let mut b = Browser::spawn();
    let base = serve();
    b.open(&format!("{base}/more"));

    assert!(b
        .err("fill", json!({ "selector": "#p", "value": "x" }))
        .contains("not editable"));
    assert!(b
        .err("type", json!({ "selector": "#p", "text": "x" }))
        .contains("not editable"));
    assert!(b
        .err("check", json!({ "selector": "#p" }))
        .contains("not a checkbox"));
    assert!(b
        .err("select", json!({ "selector": "#p", "value": "x" }))
        .contains("not a select"));
    let err = b.err("select", json!({ "selector": "#s", "value": ["a", "zzz"] }));
    assert!(err.contains("no option matches 'zzz'"), "{err}");
    assert_eq!(
        b.ok("eval", json!({ "expression": "s.value" })),
        "a",
        "selection must not change on a miss"
    );
    assert_eq!(b.ok("text", json!({ "selector": "#p" })), "plain");

    let t = Instant::now();
    assert!(b.err("wait_for", json!({})).contains("need"));
    assert!(
        t.elapsed() < Duration::from_secs(1),
        "must fail at once, not after the timeout"
    );
}

#[test]
fn navigate_failures_reply() {
    let mut b = Browser::spawn();
    let base = serve();
    b.open(&format!("{base}/other"));

    assert!(b
        .err("navigate", json!({ "url": "not a url" }))
        .contains("invalid url"));
    assert_eq!(
        b.ok("title", json!({})),
        "other",
        "a rejected url must leave the page alone"
    );

    // A closed port (WebKit answers blocked ports like 1 with about:blank, so pick a free one).
    // Native load failures must answer the request and leave the tab usable.
    let closed = TcpListener::bind("127.0.0.1:0")
        .unwrap()
        .local_addr()
        .unwrap();
    let err = b.err(
        "navigate",
        json!({ "url": format!("http://{closed}/"), "timeout": 3000 }),
    );
    assert!(
        err.contains("refused")
            || (!cfg!(target_os = "linux")
                && (err.contains("timed out") || err.contains("load failed"))),
        "{err}"
    );
    if cfg!(target_os = "macos") {
        assert!(
            err.contains("load failed"),
            "native failure was missed: {err}"
        );
        assert_eq!(b.ok("title", json!({ "request_timeout": 5000 })), "other");
    }

    if cfg!(target_os = "linux") {
        let err = b.err("navigate", json!({ "url": format!("{base}/download") }));
        assert!(err.contains("download"), "{err}");
        let ev = b.wait_event("download");
        assert!(ev["url"].as_str().unwrap().ends_with("/download"));
    }

    // The tab still answers.
    b.open(&format!("{base}/other"));
    assert_eq!(b.ok("title", json!({})), "other");
}

#[test]
fn visible_search_input_with_empty_label() {
    let mut b = Browser::spawn();
    b.open(&format!("{}/form", serve()));
    b.ok(
        "eval",
        json!({ "expression": r#"document.body.innerHTML = `
        <input name="search" hidden>
        <input name="language" role="combobox">
        <label for="generated-search-id"></label>
        <input id="generated-search-id" name="search" role="combobox" title="Search Wikipedia">
    `"# }),
    );
    let input = visible_input_named(&mut b, "search").expect("visible unnamed search input");
    b.ok("type", json!({ "ref": input, "text": "WebKitGTK" }));
    assert_eq!(
        b.ok(
            "eval",
            json!({ "expression": "document.getElementById('generated-search-id').value" })
        ),
        "WebKitGTK"
    );
    assert_eq!(
        b.ok(
            "eval",
            json!({ "expression": "document.querySelector('input[hidden]').value" })
        ),
        ""
    );
}

#[test]
fn cookie_defaults_and_tab_load() {
    let mut b = Browser::spawn();
    let base = serve();
    b.open(&format!("{base}/other"));

    // No domain or path: the cookie belongs to the current page.
    b.ok("set_cookie", json!({ "name": "d", "value": "1" }));
    assert_eq!(
        b.ok(
            "eval",
            json!({ "expression": "document.cookie.includes('d=1')" })
        ),
        true
    );

    // new_tab with a url answers once the page is loaded, so the next call works.
    let t = b.ok("new_tab", json!({ "url": format!("{base}/slow") }));
    assert!(t["url"].as_str().unwrap().ends_with("/slow"));
    assert_eq!(b.ok("title", json!({ "tab": t["tab"] })), "other");
}

#[test]
fn calls_wait_for_navigation() {
    let mut b = Browser::spawn();
    let base = serve();
    b.open(&format!("{base}/more"));

    // A call sent while a click-triggered load is in flight runs in the new page.
    b.ok("click", json!({ "selector": "#away" }));
    let t = Instant::now();
    assert_eq!(b.ok("title", json!({})), "other");
    assert!(
        t.elapsed() >= SLOW_DELAY / 2,
        "title answered from the old page"
    );

    // Same for a form submit through type, and a wait that was already pending.
    b.open(&format!("{base}/more"));
    b.ok(
        "type",
        json!({ "selector": "#go", "text": "x", "submit": true }),
    );
    b.ok("wait_for", json!({ "text": "other page", "timeout": 5000 }));
    assert!(b
        .ok("url", json!({}))
        .as_str()
        .unwrap()
        .ends_with("/slow?go=x"));
    b.open(&format!("{base}/more"));
    let pending = b.send("wait_for", json!({ "text": "other page", "timeout": 5000 }));
    b.ok("click", json!({ "selector": "#away" }));
    assert!(b.recv(pending).is_ok());

    // Actions wait for their element to appear; a miss still reports after the timeout.
    b.ok("eval", json!({ "expression": "setTimeout(() => { const x = document.createElement('button'); x.id = 'late'; x.textContent = 'late'; x.onclick = () => x.textContent = 'hit'; document.body.appendChild(x); }, 300)" }));
    b.ok("click", json!({ "selector": "#late", "timeout": 3000 }));
    assert_eq!(b.ok("text", json!({ "selector": "#late" })), "hit");
    let t = Instant::now();
    assert!(b
        .err("click", json!({ "selector": "#never", "timeout": 300 }))
        .contains("no element matches"));
    assert!(t.elapsed() >= Duration::from_millis(300));
}

#[test]
fn navigate_returns_at_page_load() {
    let mut b = Browser::spawn();
    let base = serve();

    // Subframes added after load must not hold the navigate reply.
    b.open(&format!("{base}/lateframe"));
    let since = b.ok(
        "eval",
        json!({ "expression": "performance.now() - window.__loadedAt" }),
    );
    assert!(
        since.as_f64().unwrap() < (SLOW_DELAY * 3).as_millis() as f64,
        "navigate waited for the late iframe: {since}"
    );
    assert_eq!(b.ok("text", json!({ "selector": "p" })), "late");
    // One load event per page, even though WebKit finishes later.
    b.ok(
        "wait_for",
        json!({ "time": (SLOW_DELAY * 6).as_millis() as u64 }),
    );
    b.ok("title", json!({}));
    let loads = b
        .stash
        .iter()
        .filter(|v| v["event"] == "load" && v["url"].as_str().unwrap().ends_with("/lateframe"))
        .count();
    assert_eq!(loads, 1, "{:?}", b.stash);
}

#[test]
fn navigate_until() {
    let mut b = Browser::spawn();
    let base = serve();

    // dom: back before the slow image, so the load event has not happened yet.
    b.ok(
        "navigate",
        json!({ "url": format!("{base}/slowimg"), "until": "dom" }),
    );
    assert_eq!(
        b.ok(
            "eval",
            json!({ "expression": "performance.getEntriesByType('navigation')[0].loadEventEnd" })
        ),
        0,
        "until=dom waited for the image"
    );
    assert_eq!(b.ok("text", json!({ "selector": "p" })), "img");

    // idle: the fetch started after load has finished when navigate answers.
    b.ok(
        "navigate",
        json!({ "url": format!("{base}/latefetch"), "until": "idle" }),
    );
    let net = b.ok("network", json!({}));
    let slow = net
        .as_array()
        .unwrap()
        .iter()
        .find(|e| e["url"].as_str().unwrap().ends_with("/slow"));
    assert_eq!(slow.map(|e| e["status"].clone()), Some(json!(200)), "{net}");

    // load stays the default; unknown values are rejected.
    b.ok("navigate", json!({ "url": format!("{base}/slowimg") }));
    assert!(
        b.ok(
            "eval",
            json!({ "expression": "performance.getEntriesByType('navigation')[0].loadEventEnd" })
        )
        .as_f64()
        .unwrap()
            > 0.0
    );
    assert!(b
        .err(
            "navigate",
            json!({ "url": format!("{base}/other"), "until": "soon" })
        )
        .contains("until"));
}

#[test]
fn sessions_do_not_share_state() {
    let base = serve();
    let cache_home = std::env::temp_dir().join(format!("bruster-state-{}", std::process::id()));
    let env = [("XDG_CACHE_HOME", cache_home.to_str().unwrap())];
    {
        let mut b = Browser::spawn_env(&[], &env);
        b.open(&format!("{base}/other"));
        b.ok(
            "eval",
            json!({ "expression": "localStorage.setItem('k', 'v')" }),
        );
        b.open(&format!("{base}/cookie"));
    }
    let mut b = Browser::spawn_env(&[], &env);
    b.open(&format!("{base}/other"));
    assert_eq!(
        b.ok("eval", json!({ "expression": "localStorage.getItem('k')" })),
        Value::Null,
        "storage leaked across sessions"
    );
    assert!(
        b.ok("cookies", json!({})).as_array().unwrap().is_empty(),
        "cookies leaked across sessions"
    );
    drop(b);
    let _ = std::fs::remove_dir_all(&cache_home);
}

#[test]
#[cfg_attr(
    not(target_os = "linux"),
    ignore = "the shared HTTP cache is WebKitGTK only"
)]
fn cache_outlives_the_session_cookies_do_not() {
    let base = serve();
    let cache_home = std::env::temp_dir().join(format!("bruster-cache-{}", std::process::id()));
    let env = [("XDG_CACHE_HOME", cache_home.to_str().unwrap())];

    {
        let mut b = Browser::spawn_env(&[], &env);
        b.open(&format!("{base}/cachedpage"));
        b.ok(
            "eval",
            json!({ "expression": "localStorage.setItem('k', 'v')" }),
        );
        b.open(&format!("{base}/cookie"));
        assert_eq!(CACHED_HITS.load(std::sync::atomic::Ordering::SeqCst), 1);
    }

    let mut b = Browser::spawn_env(&[], &env);
    b.open(&format!("{base}/cachedpage"));
    assert_eq!(b.ok("eval", json!({ "expression": "window.cached" })), 1);
    assert_eq!(
        CACHED_HITS.load(std::sync::atomic::Ordering::SeqCst),
        1,
        "script fetched again: cache not persisted"
    );
    assert_eq!(
        b.ok("eval", json!({ "expression": "localStorage.getItem('k')" })),
        Value::Null,
        "storage leaked across sessions"
    );
    let cookies = b.ok("cookies", json!({}));
    assert!(
        cookies.as_array().unwrap().is_empty(),
        "cookies leaked across sessions: {cookies}"
    );

    // A second bruster on the same cache dir must not share it: it still works, on its own scratch dir.
    let mut other = Browser::spawn_env(&[], &env);
    other.open(&format!("{base}/cookie"));
    assert_eq!(
        other.ok("eval", json!({ "expression": "document.cookie" })),
        "srv=1"
    );
    assert_eq!(
        b.ok("eval", json!({ "expression": "document.cookie" })),
        "",
        "cookie jar shared between two instances"
    );
    drop(other);
    assert_eq!(
        b.ok("title", json!({})),
        "cached",
        "first instance broken by the second one leaving"
    );
    drop(b);
    let _ = std::fs::remove_dir_all(&cache_home);
}

#[test]
fn profile_keeps_cookies_and_exit_waits_for_the_cache() {
    let base = serve();
    let profile = std::env::temp_dir().join(format!("bruster-prof-{}", std::process::id()));
    let args = ["--profile", profile.to_str().unwrap()];

    // Exit right after a load waits for WebKit to write its cache; a quiet exit does not.
    // Session cookies (no Max-Age) die with the process, as in any browser; persistent ones stay.
    let t = Instant::now();
    {
        let mut b = Browser::spawn_with(&args);
        b.open(&format!("{base}/cookie_persistent"));
        b.open(&format!("{base}/cookie"));
    }
    if cfg!(target_os = "linux") {
        assert!(
            t.elapsed() >= Duration::from_millis(1000),
            "exit did not wait for the cache write: {:?}",
            t.elapsed()
        );
    }
    let mut b = Browser::spawn_with(&args);
    let names: Vec<String> = b
        .ok("cookies", json!({}))
        .as_array()
        .unwrap()
        .iter()
        .map(|c| c["name"].as_str().unwrap().to_owned())
        .collect();
    assert!(
        names.contains(&"keep".to_owned()) && !names.contains(&"srv".to_owned()),
        "profile cookies: {names:?}"
    );
    b.ok("wait_for", json!({ "time": 1300 }));
    let t = Instant::now();
    drop(b);
    assert!(
        t.elapsed() < Duration::from_millis(1500),
        "exit waited although the cache had settled: {:?}",
        t.elapsed()
    );
    let _ = std::fs::remove_dir_all(&profile);
}

#[test]
fn until_on_history_and_idle_edges() {
    let mut b = Browser::spawn();
    let base = serve();

    // reload and back accept until too (history moves on WKWebView restore from
    // the back/forward cache without load events; verified on WebKitGTK only).
    if cfg!(target_os = "linux") {
        b.open(&format!("{base}/other"));
        b.open(&format!("{base}/slowimg"));
        b.ok("reload", json!({ "until": "dom" }));
        assert_eq!(b.ok("eval", json!({ "expression": "performance.getEntriesByType('navigation')[0].loadEventEnd" })), 0, "reload until=dom waited for the image");
        let back = b.ok("back", json!({ "until": "dom" }));
        assert!(back["url"].as_str().unwrap().ends_with("/other"));
    }

    // idle on a quiet page: shortly after load, not before the quiet period.
    let t = Instant::now();
    b.ok(
        "navigate",
        json!({ "url": format!("{base}/other"), "until": "idle" }),
    );
    let took = t.elapsed();
    assert!(
        took >= Duration::from_millis(500) && took < Duration::from_secs(3),
        "{took:?}"
    );

    // idle on a page that never stops fetching: the cap, not a hang.
    let t = Instant::now();
    b.ok(
        "navigate",
        json!({ "url": format!("{base}/polling"), "until": "idle" }),
    );
    let took = t.elapsed();
    assert!(
        took >= Duration::from_secs(9) && took < Duration::from_secs(14),
        "{took:?}"
    );
    assert_eq!(b.ok("text", json!({ "selector": "p" })), "poll");
}

#[test]
fn eval_under_csp() {
    let mut b = Browser::spawn();
    let base = serve();
    b.open(&format!("{base}/csp"));

    assert_eq!(b.ok("eval", json!({ "expression": "1 + 1" })), 2);
    assert_eq!(
        b.ok("eval", json!({ "expression": "({ a: 1 })" })),
        json!({ "a": 1 })
    );
    assert_eq!(
        b.ok("eval", json!({ "expression": "const a = 2; return a * 3" })),
        6
    );
    assert_eq!(
        b.ok("eval", json!({ "expression": "Promise.resolve('later')" })),
        "later"
    );
    assert!(b
        .err("eval", json!({ "expression": "throw new Error('boom')" }))
        .contains("boom"));
    assert!(b
        .err("eval", json!({ "expression": "@@@" }))
        .contains("not valid JavaScript"));
    assert_eq!(
        b.ok("eval", json!({ "expression": "document.title" })),
        "more"
    );
}

#[test]
fn tabs_share_cookies() {
    let mut b = Browser::spawn();
    let base = serve();
    b.open(&format!("{base}/cookie"));

    let t2 = b.ok("new_tab", json!({ "url": format!("{base}/other") }))["tab"]
        .as_u64()
        .unwrap();
    assert_eq!(
        b.ok(
            "eval",
            json!({ "tab": t2, "expression": "document.cookie" })
        ),
        "srv=1"
    );
    let names: Vec<String> = b
        .ok("cookies", json!({ "tab": t2 }))
        .as_array()
        .unwrap()
        .iter()
        .map(|c| c["name"].as_str().unwrap().to_owned())
        .collect();
    assert!(names.contains(&"srv".to_owned()), "{names:?}");
}

/// Width and height from a PNG header.
fn png_size(bytes: &[u8]) -> (u32, u32) {
    let be = |i: usize| u32::from_be_bytes(bytes[i..i + 4].try_into().unwrap());
    (be(16), be(20))
}

#[test]
#[cfg_attr(
    not(target_os = "linux"),
    ignore = "WKWebView renders the visible area only; the window cannot grow past the screen"
)]
fn tall_full_screenshot() {
    let mut b = Browser::spawn_with(&["--viewport", "960x640"]);
    let base = serve();
    b.open(&format!("{base}/tall"));

    // Resizing a second tab must not change the first tab's capture or restore.
    let other = b.ok("new_tab", json!({ "url": format!("{base}/other") }))["tab"].clone();
    b.ok(
        "resize",
        json!({ "tab": other, "width": 640, "height": 480 }),
    );
    let path = std::env::temp_dir().join(format!("bruster-tall-{}.png", std::process::id()));
    for overflow in ["auto", "hidden"] {
        b.ok("eval", json!({ "expression": format!("document.documentElement.style.overflow = '{overflow}'") }));
        let size = b.ok("eval", json!({ "expression": "[innerWidth, innerHeight]" }));
        // WebKit snapshots exclude non-overlay scrollbars. Measure the content
        // viewport instead of assuming every GTK theme uses overlay scrollbars.
        let width = b.ok(
            "eval",
            json!({ "expression": "document.scrollingElement.clientWidth * devicePixelRatio" }),
        );
        b.ok("screenshot", json!({ "full": true, "path": path }));
        let bytes = std::fs::read(&path).unwrap();
        let _ = std::fs::remove_file(&path);
        let (w, h) = png_size(&bytes);
        assert_eq!(w as u64, width.as_u64().unwrap(), "overflow={overflow}");
        assert!(h > 640 && h <= 16000, "height {h}");
        // Taller than cairo allows: capped, then both dimensions restored.
        let t = Instant::now();
        while b.ok("eval", json!({ "expression": "[innerWidth, innerHeight]" })) != size {
            assert!(
                t.elapsed() < Duration::from_secs(5),
                "window not restored to {size}"
            );
            std::thread::sleep(Duration::from_millis(50));
        }
    }
}

#[test]
fn snapshot_text_format() {
    let mut b = Browser::spawn();
    let base = serve();
    b.open(&format!("{base}/texts"));

    let out = b.ok("snapshot", json!({ "format": "text" }));
    let out = out.as_str().unwrap();
    let lines: Vec<&str> = out.lines().collect();
    assert!(lines[0].ends_with("/texts"), "{out}");
    assert_eq!(lines[1], "texts");
    assert!(
        lines
            .iter()
            .any(|l| l.starts_with("e1 text \"You logged in\"")),
        "{out}"
    );
    // Same-origin hrefs are relative to the page origin.
    assert!(
        lines
            .iter()
            .any(|l| l.ends_with(" link \"Fork me\" href=/other")),
        "{out}"
    );
    assert!(
        lines.iter().any(|l| l.contains(" checkbox checked=false")),
        "{out}"
    );

    // A text ref from the text format works like a JSON one.
    assert_eq!(b.ok("text", json!({ "ref": "e1" })), "You logged in ×");

    // JSON stays the default on the native protocol and keeps absolute hrefs.
    let snap = b.ok("snapshot", json!({}));
    assert!(snap["elements"]
        .as_array()
        .unwrap()
        .iter()
        .any(|e| e["href"].as_str().is_some_and(|h| h.starts_with("http://"))));

    // A container whose text is just one link is folded into the link.
    let found = b.ok("find", json!({ "text": "Only link" }));
    let els = found["elements"].as_array().unwrap();
    assert_eq!(els.len(), 1, "{els:?}");
    assert_eq!(els[0]["role"], "link");
    // Anchors apply per field, the href must not spoil ^...$ on the name.
    assert_eq!(
        b.ok("find", json!({ "regex": "^Only link$" }))["elements"]
            .as_array()
            .unwrap()
            .len(),
        1
    );
}

/// Fake forward proxy: answers every request, whatever the target, with PROXIED.
fn serve_proxy() -> String {
    let listener = TcpListener::bind("127.0.0.1:0").unwrap();
    let addr = listener.local_addr().unwrap();
    std::thread::spawn(move || {
        for mut stream in listener.incoming().flatten() {
            let mut buf = [0u8; 4096];
            let _ = stream.read(&mut buf);
            let _ = write!(stream, "HTTP/1.1 200 OK\r\nContent-Type: text/html\r\nContent-Length: {}\r\nConnection: close\r\n\r\n{PROXIED}", PROXIED.len());
        }
    });
    format!("http://{addr}")
}

#[test]
#[cfg_attr(
    not(target_os = "linux"),
    ignore = "proxy support on macOS is unverified"
)]
fn proxy_option() {
    let proxy = serve_proxy();
    let mut b = Browser::spawn_with(&["--proxy", &proxy]);
    b.open("http://bruster.invalid/anything");
    assert_eq!(b.ok("title", json!({})), "proxied");
}

#[test]
fn launch_options() {
    let base = serve();
    let profile = std::env::temp_dir().join(format!("bruster-profile-{}", std::process::id()));
    let init = std::env::temp_dir().join(format!("bruster-init-{}.js", std::process::id()));
    std::fs::write(&init, "window.__injected = 42;").unwrap();
    let args = [
        "--viewport",
        "640x480",
        "--user-agent",
        "bruster-test-ua",
        "--profile",
        profile.to_str().unwrap(),
        "--init-script",
        init.to_str().unwrap(),
    ];

    {
        let mut b = Browser::spawn_with(&args);
        b.open(&format!("{base}/other"));
        assert_eq!(
            b.ok(
                "eval",
                json!({ "expression": "innerWidth + 'x' + innerHeight" })
            ),
            "640x480"
        );
        assert_eq!(
            b.ok("eval", json!({ "expression": "navigator.userAgent" })),
            "bruster-test-ua"
        );
        assert_eq!(
            b.ok("eval", json!({ "expression": "window.__injected" })),
            42
        );
        // Make the last load older than the cache grace period: shutdown must
        // also preserve storage written immediately before close, not just load data.
        b.ok("wait_for", json!({ "time": 1500 }));
        b.ok(
            "eval",
            json!({ "expression": "localStorage.setItem('k', 'kept')" }),
        );
    }

    // Same profile dir, new process: storage survives.
    let mut b = Browser::spawn_with(&args);
    b.open(&format!("{base}/other"));
    assert_eq!(
        b.ok("eval", json!({ "expression": "localStorage.getItem('k')" })),
        "kept"
    );
    drop(b);
    let _ = std::fs::remove_file(&init);
    let _ = std::fs::remove_dir_all(&profile);
}

#[test]
#[cfg(target_os = "linux")]
fn missing_display_fails_cleanly() {
    for mode in ["--hidden", "--mcp"] {
        for no_xvfb in [false, true] {
            let mut command = Command::new(env!("CARGO_BIN_EXE_bruster"));
            command
                .args([mode, "--quiet"])
                .env_remove("DISPLAY")
                .env_remove("WAYLAND_DISPLAY")
                .env_remove("BRUSTER_NO_XVFB")
                .env("PATH", "");
            if no_xvfb {
                command.env("BRUSTER_NO_XVFB", "1");
            }
            let output = command.output().unwrap();
            let stderr = String::from_utf8_lossy(&output.stderr);
            assert_eq!(output.status.code(), Some(1), "{stderr}");
            assert!(stderr.contains("WebKitGTK requires a display"), "{stderr}");
            assert!(stderr.contains("install Xvfb"), "{stderr}");
            assert!(!stderr.contains("panicked"), "{stderr}");
            assert!(output.stdout.is_empty());
        }
    }
}

#[test]
fn speaks_mcp() {
    let mut child = Command::new(env!("CARGO_BIN_EXE_bruster"))
        .args(["--hidden", "--mcp"])
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(test_stderr())
        .spawn()
        .unwrap();
    let stdin = std::cell::RefCell::new(child.stdin.take().unwrap());
    let lines = std::cell::RefCell::new(BufReader::new(child.stdout.take().unwrap()).lines());
    // Server notifications (no id) are collected here while waiting for a reply.
    let notes = std::cell::RefCell::new(Vec::<Value>::new());
    let raw = |line: String| -> Value {
        writeln!(stdin.borrow_mut(), "{line}").unwrap();
        loop {
            let v: Value =
                serde_json::from_str(&lines.borrow_mut().next().unwrap().unwrap()).unwrap();
            if v.get("id").is_some() {
                return v;
            }
            notes.borrow_mut().push(v);
        }
    };
    let rpc = |req: Value| raw(req.to_string());
    let notify = |method: &str, params: Value| {
        writeln!(
            stdin.borrow_mut(),
            "{}",
            json!({ "jsonrpc": "2.0", "method": method, "params": params })
        )
        .unwrap();
    };
    let call = |id: Value, name: &str, args: Value| json!({ "jsonrpc": "2.0", "id": id, "method": "tools/call", "params": { "name": name, "arguments": args } });
    let events = || -> Vec<String> {
        notes
            .borrow()
            .iter()
            .filter_map(|n| n["params"]["data"]["event"].as_str().map(str::to_owned))
            .collect()
    };

    // Version: echoed when supported, newest otherwise. Nothing is sent before initialized.
    let init = rpc(
        json!({ "jsonrpc": "2.0", "id": 1, "method": "initialize", "params": { "protocolVersion": "2024-11-05" } }),
    );
    assert_eq!(init["result"]["serverInfo"]["name"], "bruster");
    assert_eq!(init["result"]["protocolVersion"], "2024-11-05");
    assert!(init["result"]["capabilities"]["logging"].is_object());
    assert_eq!(init["jsonrpc"], "2.0");
    assert!(
        notes.borrow().is_empty(),
        "ready leaked before initialized: {:?}",
        notes.borrow()
    );
    notify("notifications/initialized", json!({}));

    let tools = rpc(json!({ "jsonrpc": "2.0", "id": 2, "method": "tools/list" }));
    let tools = tools["result"]["tools"].as_array().unwrap();
    assert!(tools.iter().any(|t| t["name"] == "snapshot"));
    let fill = tools.iter().find(|t| t["name"] == "fill").unwrap();
    assert_eq!(fill["inputSchema"]["required"], json!(["value"]));
    assert!(fill["inputSchema"]["properties"]["ref"].is_object());
    assert!(fill["inputSchema"]["properties"]["tab"].is_object());

    // Every native param the runtime accepts is visible to MCP clients.
    let prop = |tool: &str, p: &str| {
        tools.iter().find(|t| t["name"] == tool).unwrap()["inputSchema"]["properties"][p].clone()
    };
    assert!(prop("screenshot", "path").is_object());
    assert_eq!(prop("text", "max")["type"], "integer");
    assert!(prop("snapshot", "selector").is_object());
    assert_eq!(prop("upload", "paths")["type"], "array");
    assert_eq!(prop("drag", "from")["type"], "object");
    assert_eq!(prop("click", "force")["type"], "boolean");
    assert_eq!(prop("eval", "request_timeout")["type"], "integer");
    assert_eq!(prop("url", "request_timeout")["type"], "integer");
    assert_eq!(prop("navigate", "timeout")["type"], "integer");
    assert_eq!(prop("new_tab", "timeout")["type"], "integer");
    assert!(prop("screenshot", "request_timeout").is_null());
    assert!(tools.iter().any(|t| t["name"] == "dialog"));

    assert_eq!(
        rpc(json!({ "jsonrpc": "2.0", "id": 3, "method": "ping" }))["result"],
        json!({})
    );

    let base = serve();
    let nav = rpc(call(
        json!("n"),
        "navigate",
        json!({ "url": format!("{base}/"), "until": "dom" }),
    ));
    assert_eq!(nav["id"], "n");
    assert_eq!(
        prop("navigate", "until")["enum"],
        json!(["dom", "load", "idle"])
    );
    assert!(nav["result"]["content"][0]["text"]
        .as_str()
        .unwrap()
        .contains("127.0.0.1"));

    // Browser events arrive as info log notifications.
    let note = notes
        .borrow()
        .iter()
        .find(|n| n["params"]["data"]["event"] == "navigating")
        .cloned();
    let note = note.unwrap_or_else(|| panic!("no navigating notification in {:?}", notes.borrow()));
    assert_eq!(note["method"], "notifications/message");
    assert_eq!(note["params"]["level"], "info");
    assert_eq!(note["params"]["data"]["tab"], 1);

    let err = rpc(call(json!(4), "click", json!({ "selector": "#nope" })));
    assert_eq!(err["result"]["isError"], true);
    assert!(err["result"]["content"][0]["text"]
        .as_str()
        .unwrap()
        .contains("no element matches"));

    // Unknown tool is a protocol error, not a page error.
    let bad_tool = rpc(call(json!("bt"), "teleport", json!({})));
    assert_eq!(bad_tool["error"]["code"], -32602);

    // Snapshots default to the compact text format over MCP; json on request.
    let snap = rpc(call(json!("s"), "snapshot", json!({})));
    let snap = snap["result"]["content"][0]["text"].as_str().unwrap();
    assert!(
        snap.lines().nth(1) == Some("smoke") && snap.contains("\ne1 "),
        "{snap}"
    );
    let snap = rpc(call(json!("sj"), "snapshot", json!({ "format": "json" })));
    assert!(snap["result"]["content"][0]["text"]
        .as_str()
        .unwrap()
        .starts_with("{\"elements\""));

    // Screenshots are image content, null results remain distinguishable.
    let shot = rpc(call(json!(5), "screenshot", json!({})));
    assert_eq!(shot["result"]["content"][0]["type"], "image");
    assert_eq!(shot["result"]["content"][0]["mimeType"], "image/png");
    let clicked = rpc(call(json!(6), "click", json!({ "selector": "#go" })));
    assert_eq!(clicked["result"]["content"][0]["text"], "null");
    let missing = rpc(call(
        json!("missing"),
        "attr",
        json!({ "selector": "#go", "name": "data-missing" }),
    ));
    assert_eq!(missing["result"]["content"][0]["text"], "null");
    let undefined = rpc(call(
        json!("undefined"),
        "eval",
        json!({ "expression": "undefined" }),
    ));
    assert_eq!(undefined["result"]["content"][0]["text"], "null");
    let timeout = rpc(call(
        json!("timeout"),
        "eval",
        json!({ "expression": "new Promise(() => {})", "request_timeout": 200 }),
    ));
    assert_eq!(timeout["result"]["isError"], true);
    assert!(timeout["result"]["content"][0]["text"]
        .as_str()
        .unwrap()
        .contains("timed out"));
    let alive = rpc(call(json!("alive"), "eval", json!({ "expression": "42" })));
    assert_eq!(alive["result"]["content"][0]["text"], "42");

    // tab argument is routed, not passed to the page.
    let t2 = rpc(call(json!(7), "new_tab", json!({})));
    let t2: Value =
        serde_json::from_str(t2["result"]["content"][0]["text"].as_str().unwrap()).unwrap();
    let t2 = t2["tab"].as_u64().unwrap();
    rpc(call(
        json!(8),
        "navigate",
        json!({ "url": format!("{base}/form"), "tab": t2 }),
    ));
    let title = rpc(call(json!(9), "title", json!({ "tab": t2 })));
    assert_eq!(title["result"]["content"][0]["text"], "form");
    let title = rpc(call(json!(10), "title", json!({})));
    assert_eq!(title["result"]["content"][0]["text"], "smoke");

    // Protocol errors: unknown method, parse error, unknown notifications are silent.
    let unknown = rpc(json!({ "jsonrpc": "2.0", "id": 11, "method": "resources/list" }));
    assert_eq!(unknown["error"]["code"], -32601);
    let bad = raw("{not json".into());
    assert_eq!(bad["error"]["code"], -32700);
    assert_eq!(bad["id"], Value::Null);
    notify("notifications/progress", json!({}));
    let pong = rpc(json!({ "jsonrpc": "2.0", "id": 12, "method": "ping" }));
    assert_eq!(pong["id"], 12, "notification must not produce a reply");

    // Cancelled request never gets a reply, even once the browser answers it.
    writeln!(
        stdin.borrow_mut(),
        "{}",
        call(
            json!("c"),
            "wait_for",
            json!({ "selector": "#never", "timeout": 10000 })
        )
    )
    .unwrap();
    notify("notifications/cancelled", json!({ "requestId": "c" }));
    let nav = rpc(call(
        json!(13),
        "navigate",
        json!({ "url": format!("{base}/other") }),
    ));
    assert_eq!(nav["id"], 13, "cancelled wait_for must stay silent");

    // logging/setLevel above info mutes events; back to info restores them.
    assert_eq!(
        rpc(
            json!({ "jsonrpc": "2.0", "id": 14, "method": "logging/setLevel", "params": { "level": "warning" } })
        )["result"],
        json!({})
    );
    notes.borrow_mut().clear();
    rpc(call(
        json!(15),
        "navigate",
        json!({ "url": format!("{base}/form") }),
    ));
    rpc(json!({ "jsonrpc": "2.0", "id": 16, "method": "ping" }));
    assert!(
        notes.borrow().is_empty(),
        "events must be muted at warning: {:?}",
        notes.borrow()
    );
    rpc(
        json!({ "jsonrpc": "2.0", "id": 17, "method": "logging/setLevel", "params": { "level": "info" } }),
    );
    rpc(call(
        json!(18),
        "navigate",
        json!({ "url": format!("{base}/") }),
    ));
    assert!(events().contains(&"navigating".to_owned()));
    let lvl = rpc(
        json!({ "jsonrpc": "2.0", "id": 19, "method": "logging/setLevel", "params": { "level": "loud" } }),
    );
    assert_eq!(lvl["error"]["code"], -32602);

    drop(stdin.into_inner());
    let _ = child.wait();
}
