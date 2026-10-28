//! Model Context Protocol over stdio, as a translation layer on top of the
//! native line protocol. Enabled with `--mcp`.
//!
//! ```text
//! MCP tools/call ──incoming()──▶ Request{id: internal} ──▶ event loop
//! {"id": internal, result} ◀──outgoing()── wraps back into JSON-RPC 2.0
//! ```
//!
//! initialize / ping / tools/list / logging/setLevel are answered here without
//! touching the browser. Browser events (load, tab_opened, ...) go out as
//! `notifications/message` at level info once the client has initialized.

use std::collections::HashMap;
use std::sync::atomic::{AtomicBool, AtomicU64, AtomicUsize, Ordering};
use std::sync::Mutex;

use serde_json::{json, Value};

use crate::Request;

/// Newest first; the client's choice is echoed when we support it.
const SUPPORTED_VERSIONS: &[&str] = &["2025-06-18", "2025-03-26", "2024-11-05"];
const JSONRPC: &str = "2.0";
const PARSE_ERROR: i64 = -32700;
const METHOD_NOT_FOUND: i64 = -32601;
const INVALID_PARAMS: i64 = -32602;

/// RFC 5424 order, as used by logging/setLevel. Events are sent at info.
const LOG_LEVELS: &[&str] = &[
    "debug",
    "info",
    "notice",
    "warning",
    "error",
    "critical",
    "alert",
    "emergency",
];
const EVENT_LEVEL: usize = 1;

static ENABLED: AtomicBool = AtomicBool::new(false);
static INITIALIZED: AtomicBool = AtomicBool::new(false);
static LOG_LEVEL: AtomicUsize = AtomicUsize::new(EVENT_LEVEL);
static NEXT_ID: AtomicU64 = AtomicU64::new(1);
static IN_FLIGHT: Mutex<Option<HashMap<u64, Value>>> = Mutex::new(None);

pub fn enable(on: bool) {
    ENABLED.store(on, Ordering::Relaxed);
    if on {
        *IN_FLIGHT.lock().unwrap() = Some(HashMap::new());
    }
}

pub fn enabled() -> bool {
    ENABLED.load(Ordering::Relaxed)
}

fn write(v: Value) {
    crate::write_json(&v);
}

fn rpc_result(id: Value, result: Value) {
    write(json!({ "jsonrpc": JSONRPC, "id": id, "result": result }));
}

fn rpc_error(id: Value, code: i64, msg: impl ToString) {
    write(
        json!({ "jsonrpc": JSONRPC, "id": id, "error": { "code": code, "message": msg.to_string() } }),
    );
}

/// Parses one stdin line. `Ok(None)` means it was consumed here.
pub fn incoming(line: &str) -> Result<Option<Request>, String> {
    if !enabled() {
        return serde_json::from_str(line)
            .map(Some)
            .map_err(|e| e.to_string());
    }

    let msg: Value = match serde_json::from_str(line) {
        Ok(v) => v,
        Err(e) => {
            rpc_error(Value::Null, PARSE_ERROR, e);
            return Ok(None);
        }
    };
    let id = msg.get("id").cloned().unwrap_or(Value::Null);
    let method = msg.get("method").and_then(Value::as_str).unwrap_or("");
    let params = msg.get("params").cloned().unwrap_or(Value::Null);

    match method {
        "initialize" => {
            let wanted = params.get("protocolVersion").and_then(Value::as_str);
            let version = wanted
                .filter(|v| SUPPORTED_VERSIONS.contains(v))
                .unwrap_or(SUPPORTED_VERSIONS[0]);
            rpc_result(
                id,
                json!({
                    "protocolVersion": version,
                    "capabilities": { "tools": {}, "logging": {} },
                    "serverInfo": { "name": "bruster", "version": env!("CARGO_PKG_VERSION") },
                }),
            )
        }
        "ping" => rpc_result(id, json!({})),
        "tools/list" => rpc_result(id, json!({ "tools": tools() })),
        "tools/call" => {
            let Some(name) = params.get("name").and_then(Value::as_str) else {
                rpc_error(id, INVALID_PARAMS, "tools/call: missing name");
                return Ok(None);
            };
            if !tools().iter().any(|t| t["name"] == name) {
                rpc_error(id, INVALID_PARAMS, format!("unknown tool '{name}'"));
                return Ok(None);
            }
            let mut args = params.get("arguments").cloned().unwrap_or(json!({}));
            let tab = args
                .as_object_mut()
                .and_then(|o| o.remove("tab"))
                .and_then(|t| t.as_u64())
                .map(|t| t as u32);
            // The model reads the result as text anyway; the line format is ~40% smaller than JSON.
            if matches!(name, "snapshot" | "find") && args.get("format").is_none() {
                args["format"] = json!("text");
            }

            let internal = NEXT_ID.fetch_add(1, Ordering::Relaxed);
            IN_FLIGHT
                .lock()
                .unwrap()
                .as_mut()
                .unwrap()
                .insert(internal, id);
            return Ok(Some(Request {
                id: internal,
                method: name.to_owned(),
                params: args,
                tab,
            }));
        }
        "logging/setLevel" => {
            let level = params.get("level").and_then(Value::as_str).unwrap_or("");
            match LOG_LEVELS.iter().position(|l| *l == level) {
                Some(i) => {
                    LOG_LEVEL.store(i, Ordering::Relaxed);
                    rpc_result(id, json!({}));
                }
                None => rpc_error(id, INVALID_PARAMS, format!("unknown level '{level}'")),
            }
        }
        "notifications/initialized" => INITIALIZED.store(true, Ordering::Relaxed),
        // The browser still finishes the work; its answer is dropped in outgoing().
        "notifications/cancelled" => {
            let Some(rpc_id) = params.get("requestId") else {
                return Ok(None);
            };
            if let Some(map) = IN_FLIGHT.lock().unwrap().as_mut() {
                map.retain(|_, v| *v != *rpc_id);
            }
        }
        m if m.starts_with("notifications/") => {}
        _ => rpc_error(id, METHOD_NOT_FOUND, format!("unknown method '{method}'")),
    }

    Ok(None)
}

/// Maps a native outgoing message to the wire format. `None` means drop it.
pub fn outgoing(v: Value) -> Option<Value> {
    if !enabled() {
        return Some(v);
    }

    let Some(internal) = v.get("id").and_then(Value::as_u64) else {
        return event_notification(v);
    };
    let rpc_id = IN_FLIGHT.lock().unwrap().as_mut()?.remove(&internal)?;

    let result = match v.get("error") {
        Some(e) => json!({ "content": [text(e.as_str().unwrap_or("error"))], "isError": true }),
        None => json!({ "content": [content(&v["result"])] }),
    };
    Some(json!({ "jsonrpc": JSONRPC, "id": rpc_id, "result": result }))
}

/// Browser events become log notifications. Nothing goes out before the
/// client says it is initialized, or above the level it asked for.
fn event_notification(v: Value) -> Option<Value> {
    if v.get("event").is_none() {
        return None;
    }
    if !INITIALIZED.load(Ordering::Relaxed) || LOG_LEVEL.load(Ordering::Relaxed) > EVENT_LEVEL {
        return None;
    }
    Some(json!({
        "jsonrpc": JSONRPC,
        "method": "notifications/message",
        "params": { "level": LOG_LEVELS[EVENT_LEVEL], "logger": "bruster", "data": v },
    }))
}

fn text(s: &str) -> Value {
    json!({ "type": "text", "text": s })
}

/// Screenshots become image content; everything else is JSON text.
fn content(result: &Value) -> Value {
    if let Some(png) = result.get("png_base64").and_then(Value::as_str) {
        return json!({ "type": "image", "data": png, "mimeType": "image/png" });
    }
    match result {
        Value::String(s) => text(s),
        Value::Null => text("null"),
        other => text(&other.to_string()),
    }
}

/// Tool definitions. Target tools accept `selector` or `ref` (from snapshot).
fn tools() -> Vec<Value> {
    const TARGET: &str = "target";
    let specs: &[(&str, &str, &str, &[&str])] = &[
        ("navigate", "Open a URL and wait for it. until: load (default), dom (DOMContentLoaded, fastest, fine for server-rendered pages) or idle (load plus a quiet network).", "url,until,timeout", &["url"]),
        ("snapshot", "List visible elements and text with refs usable in other tools, one per line: ref role \"name\" href=... selector scopes to a subtree, max caps the list, boxes adds rects, format=json for objects.", "selector,max,boxes,format", &[]),
        ("find", "Snapshot narrowed to elements whose name, text, value or href contains text or matches regex.", "text,regex,selector,max,boxes,format", &[]),
        ("screenshot", "PNG of the viewport. full=true for the whole page, or clip={x,y,width,height}. path writes the file instead of returning it.", "full,clip,path", &[]),
        ("click", "Click an element, or a viewport point with x,y. Waits until it is visible, enabled and not covered; force skips that.", "target,x,y,force,timeout", &[]),
        ("hover", "Hover an element.", "target,force,timeout", &[]),
        ("fill", "Set an input's value (fires input/change).", "target,value,force,timeout", &["value"]),
        ("fill_form", "Fill several fields at once: [{selector|ref, value}]. Checkboxes take a boolean, selects a value or array.", "fields", &["fields"]),
        ("type", "Type text key by key into an element. submit presses Enter afterwards.", "target,text,delay,submit,force,timeout", &["text"]),
        ("press", "Press a key, e.g. Enter, Escape, Tab, Control+a.", "target,key", &["key"]),
        ("select", "Choose option(s) in a <select>.", "target,value,force,timeout", &["value"]),
        ("check", "Set a checkbox or radio.", "target,checked,force,timeout", &[]),
        ("drag", "Drag one element onto another (HTML5 drag events).", "from,to", &["from", "to"]),
        ("upload", "Set files on a file input from local paths.", "target,paths", &["paths"]),
        ("scroll", "Scroll an element into view, or by x/y.", "target,x,y", &[]),
        ("resize", "Resize the viewport.", "width,height", &["width", "height"]),
        ("maximize", "Maximize this window and persist the requested mode for future runs. Hidden windows only persist the mode.", "", &[]),
        ("minimize", "Hide this native window and persist minimized mode. Hidden windows stay off-screen and only persist the mode.", "", &[]),
        ("dark", "Persist dark color-scheme for all existing and future pages.", "", &[]),
        ("light", "Persist light color-scheme for all existing and future pages.", "", &[]),
        ("close", "Shut down Bruster, closing all tabs and the stdio server. Use close_tab to close only one tab.", "", &[]),
        ("text", "innerText of an element, truncated to max characters.", "target,max", &[]),
        ("html", "outerHTML of an element.", TARGET, &[]),
        ("attr", "Attribute value of an element.", "target,name", &["name"]),
        ("rect", "Bounding box of an element (for screenshot clip).", TARGET, &[]),
        ("count", "Number of elements matching a selector.", "selector", &["selector"]),
        ("eval", "Evaluate a JavaScript expression in the page.", "expression", &["expression"]),
        ("wait_for", "Wait for selector state (visible/attached/hidden), text present or gone, url substring, network idle, or time ms.", "target,state,text,textGone,url,idle,time,timeout", &[]),
        ("network", "Requests made by the page: fetch, xhr and resources. index feeds network_request.", "clear", &[]),
        ("network_request", "Headers and body prefix of one fetch/xhr entry from network.", "index", &["index"]),
        ("console", "Console messages and page errors since the last navigation.", "clear", &[]),
        ("dialog", "Set how alert/confirm/prompt are answered from now on, and list dialogs seen so far.", "accept,text,clear", &[]),
        ("cookies", "All cookies.", "", &[]),
        ("set_cookie", "Set a cookie.", "name,value,domain,path", &["name", "value"]),
        ("url", "Current URL.", "", &[]),
        ("title", "Page title.", "", &[]),
        ("back", "History back.", "", &[]),
        ("forward", "History forward.", "", &[]),
        ("reload", "Reload the page.", "", &[]),
        ("new_tab", "Open a new tab, optionally at a URL. Returns its id; use switch_tab to make it current.", "url,timeout", &[]),
        ("tabs", "List open tabs.", "", &[]),
        ("switch_tab", "Make a tab the default for later calls.", "tab", &["tab"]),
        ("close_tab", "Close a tab; the last tab cannot be closed (use close to shut down).", "", &[]),
    ];

    specs
        .iter()
        .map(|(name, desc, props, required)| {
            let mut properties = serde_json::Map::new();
            for p in props.split(',').filter(|p| !p.is_empty()) {
                if p == TARGET {
                    properties.insert(
                        "selector".into(),
                        json!({ "type": "string", "description": "CSS selector" }),
                    );
                    properties.insert(
                        "ref".into(),
                        json!({ "type": "string", "description": "ref from snapshot, e.g. e3" }),
                    );
                    continue;
                }
                properties.insert(p.into(), prop_schema(p));
            }
            properties.insert(
                "tab".into(),
                json!({ "type": "integer", "description": "tab id, defaults to current" }),
            );
            if !matches!(*name, "navigate" | "reload" | "back" | "forward" | "cookies" | "set_cookie" | "screenshot" | "resize" | "maximize" | "minimize" | "dark" | "light" | "close" | "new_tab" | "tabs" | "switch_tab" | "close_tab") {
                properties.insert(
                    "request_timeout".into(),
                    json!({ "type": "integer", "minimum": 0, "description": "Outer page request deadline in milliseconds; defaults to at least 30000" }),
                );
            }

            json!({
                "name": name,
                "description": desc,
                "inputSchema": { "type": "object", "properties": properties, "required": required },
            })
        })
        .collect()
}

fn prop_schema(name: &str) -> Value {
    match name {
        "full" | "clear" | "checked" | "force" | "boxes" | "submit" | "idle" | "accept" => {
            json!({ "type": "boolean" })
        }
        "timeout" | "delay" | "x" | "y" | "tab" | "max" | "width" | "height" | "time" | "index" => {
            json!({ "type": "integer" })
        }
        "paths" => {
            json!({ "type": "array", "items": { "type": "string" }, "description": "local file paths" })
        }
        "fields" => json!({ "type": "array", "items": { "type": "object", "properties": {
            "selector": { "type": "string" }, "ref": { "type": "string" }, "value": {} } } }),
        "from" | "to" => json!({ "type": "object", "properties": {
            "selector": { "type": "string" }, "ref": { "type": "string" } } }),
        "clip" => json!({ "type": "object", "properties": {
            "x": { "type": "number" }, "y": { "type": "number" },
            "width": { "type": "number" }, "height": { "type": "number" } } }),
        "value" => json!({ "description": "string, or array of strings for multi-select" }),
        "state" => json!({ "type": "string", "enum": ["visible", "attached", "hidden"] }),
        "format" => {
            json!({ "type": "string", "enum": ["text", "json"], "description": "text (default) or json" })
        }
        "until" => {
            json!({ "type": "string", "enum": ["dom", "load", "idle"], "description": "page milestone to wait for, default load" })
        }
        _ => json!({ "type": "string" }),
    }
}

#[cfg(test)]
mod tests {
    #[test]
    fn window_controls_are_exposed() {
        let tools = super::tools();
        for name in [
            "maximize",
            "minimize",
            "dark",
            "light",
            "close",
            "close_tab",
        ] {
            assert!(tools.iter().any(|t| t["name"] == name), "missing {name}");
        }
    }
}
