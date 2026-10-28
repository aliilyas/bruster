//! bruster: a native webview driven over stdio.
//!
//! ```text
//! agent --JSON line (stdin)--> stdin thread --EventLoopProxy--> main thread (tao + wry)
//!                                                                  |
//!       <--JSON line (stdout)-- ipc handler / page load handler <--+-- runtime.js
//! ```
//!
//! Request:  {"id":1,"method":"click","params":{"selector":"#go"},"tab":2}
//! Response: {"id":1,"result":...} or {"id":1,"error":"..."}
//! Event:    {"event":"load","tab":2,"url":"..."}
//!
//! Each tab is its own window + webview. `tab` defaults to the current one.
//! Navigation, cookies, screenshots and tab management are handled in Rust.
//! Every other method is forwarded to `__bruster.run(id, method, params)`
//! in runtime.js, which answers through `window.ipc.postMessage`.
//!
//! With `--mcp` stdin/stdout speak Model Context Protocol instead; see mcp.rs.

use std::cell::RefCell;
use std::collections::HashMap;
use std::io::{BufRead, Write};
use std::path::{Path, PathBuf};
use std::rc::Rc;
use std::time::Duration;

use serde::Deserialize;
use serde_json::{json, Value};
use tao::event::{Event, WindowEvent};
use tao::event_loop::{ControlFlow, EventLoopBuilder, EventLoopProxy, EventLoopWindowTarget};
use tao::window::{Window, WindowBuilder, WindowId};
use wry::{
    NewWindowResponse, PageLoadEvent, ProxyConfig, ProxyEndpoint, WebContext, WebView,
    WebViewBuilder,
};

mod mcp;
#[cfg(target_os = "macos")]
mod navigation_macos;
#[cfg(target_os = "windows")]
mod navigation_windows;
mod screenshot;
mod window_state;

use screenshot::{Clip, Region};

const RUNTIME_JS: &str = include_str!("runtime.js");
const HIDDEN_FLAG: &str = "--hidden";
const VISIBLE_FLAG: &str = "--visible";
const MCP_FLAG: &str = "--mcp";
const QUIET_FLAG: &str = "--quiet";
const INSECURE_FLAG: &str = "--insecure";
const NO_IMAGES_FLAG: &str = "--no-images";
const VIEWPORT_OPT: &str = "--viewport";
const USER_AGENT_OPT: &str = "--user-agent";
const PROFILE_OPT: &str = "--profile";
const PROXY_OPT: &str = "--proxy";
const INIT_SCRIPT_OPT: &str = "--init-script";
const DARK_FLAG: &str = "--dark";
const DEFAULT_VIEWPORT: (u32, u32) = (1280, 800);
const OFFSCREEN: i32 = -20_000;
/// Content types for `upload` by extension; anything else is octet-stream.
const MIME_TYPES: &[(&str, &str)] = &[
    ("png", "image/png"),
    ("jpg", "image/jpeg"),
    ("jpeg", "image/jpeg"),
    ("gif", "image/gif"),
    ("webp", "image/webp"),
    ("svg", "image/svg+xml"),
    ("pdf", "application/pdf"),
    ("txt", "text/plain"),
    ("csv", "text/csv"),
    ("json", "application/json"),
    ("html", "text/html"),
    ("zip", "application/zip"),
];
const OCTET_STREAM: &str = "application/octet-stream";
/// Full-page screenshots resize the window to the document height; cap it.
/// Also the largest viewport side: WebKitGTK exits above ~28000 px.
const MAX_FULL_HEIGHT: f64 = 16_000.0;
const MAX_VIEWPORT_SIDE: u32 = MAX_FULL_HEIGHT as u32;
/// `navigate` gives up after this unless `timeout` says otherwise.
const NAVIGATE_TIMEOUT: Duration = Duration::from_secs(30);
/// Bound page IPC even if a promise never resolves or the runtime stops responding.
const PAGE_TIMEOUT: Duration = Duration::from_secs(30);
const PAGE_TIMEOUT_MARGIN_MS: u64 = 5_000;
/// Some engines restore history without a load event. Check the URL then;
/// same-document history is also acknowledged by the runtime's popstate hook.
const HISTORY_START_TIMEOUT: Duration = Duration::from_millis(500);
/// A request re-run after this many navigations is given up on.
const MAX_REDISPATCH: u8 = 3;
/// cairo image surfaces cannot exceed this many pixels per side.
const CAIRO_MAX_SIDE: f64 = 32767.0;
/// WebView2 error pages load from here.
const CHROME_ERROR_SCHEME: &str = "chrome-error://";
/// Reply from the eval wrapper script when the expression compiled.
const EVAL_COMPILED: &str = "1";
/// Polling for the enlarged window before a tall capture (Linux).
const TALL_SHOT_POLL: Duration = Duration::from_millis(100);
const TALL_SHOT_TRIES: u8 = 30;
/// WebKit writes disk cache entries about a second after a load; exiting
/// earlier loses them for the next session.
const CACHE_FLUSH_DELAY: Duration = Duration::from_millis(1200);

type TabId = u32;

#[derive(Deserialize)]
struct Request {
    id: u64,
    method: String,
    #[serde(default)]
    params: Value,
    tab: Option<TabId>,
}

enum UserEvent {
    Command(Request),
    /// A page asked for a new window (target=_blank, window.open).
    OpenTab(String),
    /// macOS only: document height arrived, window can be resized for a full capture.
    FullShot {
        tab: TabId,
        id: u64,
        path: Option<String>,
        height: f64,
    },
    /// Puts the window back to the viewport size after a full capture.
    RestoreSize {
        tab: TabId,
        size: tao::dpi::LogicalSize<f64>,
    },
    /// Linux: the window was resized for a tall capture; poll until the page sees the new height.
    TallShot {
        tab: TabId,
        id: u64,
        path: Option<String>,
        height: f64,
        tries: u8,
        restore: tao::dpi::LogicalSize<f64>,
    },
    TallShotReady {
        tab: TabId,
        id: u64,
        path: Option<String>,
        restore: tao::dpi::LogicalSize<f64>,
    },
    /// back/forward/reload gave the webview HISTORY_START_TIMEOUT to start loading.
    HistoryTimeout {
        tab: TabId,
        id: u64,
        token: u64,
    },
    /// A navigate ran out of time.
    NavigateTimeout {
        tab: TabId,
        id: u64,
        token: u64,
    },
    /// Wake the event loop to expire requests, even when GTK has no events.
    Deadline,
    /// WebView2 has acknowledged the previous native navigation call.
    #[cfg(target_os = "windows")]
    StartNavigation(TabId),
    /// Bind runtime milestones to the document committed by this navigation.
    BindDocument {
        tab: TabId,
        generation: u64,
    },
    /// A load finished: release requests only if it is still the same navigation.
    Flush {
        tab: TabId,
        generation: u64,
    },
    /// The eval wrapper did not compile as an expression; try the statement form.
    EvalRetry {
        tab: TabId,
        id: u64,
        attempt: u64,
    },
    /// Neither form compiled.
    EvalFailed {
        tab: TabId,
        id: u64,
        attempt: u64,
    },
    Eof,
}

/// Which page milestone answers a `navigate`.
#[derive(Clone, Copy, PartialEq, Default)]
enum Until {
    /// DOMContentLoaded: the HTML is parsed, scripts ran, subresources may still load.
    Dom,
    /// The page's load event (default).
    #[default]
    Load,
    /// Load, then no fetch/xhr in flight and no resource finished for 500 ms (capped at 10 s).
    Idle,
}

impl Until {
    fn parse(v: Option<&Value>) -> Result<Self, String> {
        match v.and_then(Value::as_str) {
            None | Some("load") => Ok(Self::Load),
            Some("dom") => Ok(Self::Dom),
            Some("idle") => Ok(Self::Idle),
            Some(other) => Err(format!("until must be dom, load or idle, got '{other}'")),
        }
    }
}

/// A page request, kept so it can be re-run in the next document.
#[derive(Clone)]
struct Queued {
    method: String,
    params: Value,
    retries: u8,
    deadline: std::time::Instant,
    /// Set on dispatch, so an old document cannot answer a redispatched call.
    document: Option<String>,
    attempt: u64,
}

impl Queued {
    fn new(method: String, params: Value) -> Result<Self, String> {
        // Let action/wait timeouts complete first. request_timeout is a
        // separate outer deadline for page code that never replies.
        let timeout_ms = match params.get("request_timeout") {
            Some(value) => value
                .as_u64()
                .ok_or("request_timeout must be a non-negative integer")?,
            None => {
                let expected = ["timeout", "time"]
                    .iter()
                    .filter_map(|key| params.get(key).and_then(Value::as_u64))
                    .max()
                    .unwrap_or(0);
                (PAGE_TIMEOUT.as_millis() as u64)
                    .max(expected.saturating_add(PAGE_TIMEOUT_MARGIN_MS))
            }
        };
        let deadline = std::time::Instant::now()
            .checked_add(Duration::from_millis(timeout_ms))
            .ok_or("request_timeout is too large")?;
        Ok(Self {
            method,
            params,
            retries: 0,
            deadline,
            document: None,
            attempt: 0,
        })
    }
}

/// Requests still waiting for an answer from the page.
#[derive(Default)]
struct Pending {
    navigation_deadline: Option<std::time::Instant>,
    history_deadline: Option<std::time::Instant>,
    /// Identifies the waiting command even if a page-initiated load advances
    /// the document generation before an already-posted timeout is handled.
    navigation_token: u64,
    next_attempt: u64,
    /// Intent advances before calling native APIs, which can call back synchronously.
    generation: u64,
    /// The native load whose Started signal has actually arrived.
    native_generation: u64,
    #[cfg(target_os = "windows")]
    native_id: Option<u64>,
    #[cfg(target_os = "windows")]
    native_start: Option<u64>,
    #[cfg(target_os = "windows")]
    native_history: bool,
    #[cfg(target_os = "windows")]
    native_next: Option<navigation_windows::Navigation>,
    awaiting_start: bool,
    committed: bool,
    document: Option<String>,
    /// In flight inside the page.
    js: HashMap<u64, Queued>,
    /// Held back while a load is in flight; dispatched on Flush.
    queue: Vec<(u64, Queued)>,
    loading: bool,
    /// The action's default navigation was not cancelled, but its native start
    /// may still be pending. Keep requests queued until native completion or
    /// failure; their own deadlines bound the wait without reading the old page.
    hinted: Option<u64>,
    /// (request id, has the new load started yet). A Finished event for the
    /// previous page can arrive after load_url(); ignore it until Started.
    navigate: Option<(u64, bool)>,
    /// URL of the pending navigate, for error reporting.
    navigate_url: Option<String>,
    /// URL before a history operation, for same-document transitions with no load.
    history_url: Option<String>,
    /// WebView2 can deliver popstate IPC before its native history flags change.
    #[cfg(target_os = "windows")]
    history_changed: bool,
    #[cfg(target_os = "windows")]
    history_reply: Option<String>,
    navigate_until: Until,
    /// The about:blank warm-up load is still in flight; its events are not the agent's.
    warming: bool,
    /// The page's load event already answered this navigation; WebKit's later
    /// Finished must not report it again.
    loaded: bool,
}

impl Pending {
    fn begin_navigation(&mut self) {
        self.generation += 1;
        self.awaiting_start = true;
        self.committed = false;
        self.loading = true;
        self.hinted = None;
    }

    fn provisional_start(&mut self) {
        if self.warming {
            return;
        }
        if !self.awaiting_start {
            self.begin_navigation();
        }
        self.awaiting_start = false;
        self.native_generation = self.generation;
        self.loading = true;
        self.hinted = None;
    }

    fn flush_event(&self, tab: TabId) -> UserEvent {
        UserEvent::Flush {
            tab,
            generation: self.generation,
        }
    }

    fn waiting_for(&self, id: u64, token: u64) -> bool {
        self.navigation_token == token && self.navigate.is_some_and(|(active, _)| active == id)
    }

    fn current_milestone(&self, document: Option<&str>, generation: Option<u64>) -> bool {
        !self.warming
            && !self.awaiting_start
            && self.committed
            && generation == Some(self.generation)
            && document.is_some()
            && document == self.document.as_deref()
    }

    fn take_page_reply(&mut self, id: u64, document: Option<&str>, attempt: Option<u64>) -> bool {
        if document.is_none()
            || !self.js.get(&id).is_some_and(|q| {
                Some(q.attempt) == attempt
                    && q.document
                        .as_deref()
                        .is_none_or(|expected| Some(expected) == document)
            })
        {
            return false;
        }
        self.js.remove(&id);
        true
    }
}

fn trace_navigation(stage: &str, tab: TabId, p: &Pending, url: &str) {
    if std::env::var_os("BRUSTER_TRACE_NAV").is_some() {
        eprintln!("navigation {stage}: tab={tab} url={url:?} generation={} native={} warming={} loading={} loaded={} hint={:?} navigate={:?}", p.generation, p.native_generation, p.warming, p.loading, p.loaded, p.hinted, p.navigate);
    }
}

fn page_load(
    p: &mut Pending,
    ev: PageLoadEvent,
    tab: TabId,
    url: &str,
    proxy: &EventLoopProxy<UserEvent>,
) {
    if p.warming {
        p.warming = !matches!(ev, PageLoadEvent::Finished);
        if !p.warming && p.navigate.is_none() {
            p.committed = true;
            let _ = proxy.send_event(p.flush_event(tab));
        }
        return;
    }
    match ev {
        PageLoadEvent::Started => {
            if p.native_generation != p.generation {
                return;
            }
            p.committed = true;
            p.document = None;
            let _ = proxy.send_event(UserEvent::BindDocument {
                tab,
                generation: p.generation,
            });
            trace_navigation("committed", tab, p, url);
            // The old document and its promises are gone. Re-run pending calls
            // in the new page, a few times at most, retaining their deadlines.
            p.loading = true;
            p.hinted = None;
            p.loaded = false;
            for (id, mut q) in p.js.drain().collect::<Vec<_>>() {
                q.retries += 1;
                if q.retries > MAX_REDISPATCH {
                    fail(id, "navigation interrupted");
                } else {
                    p.queue.push((id, q));
                }
            }
            if let Some(nav) = p.navigate.as_mut() {
                nav.1 = true;
            }
            emit(json!({ "event": "navigating", "tab": tab, "url": url }));
        }
        PageLoadEvent::Finished => page_loaded(p, tab, url, proxy),
    }
}

/// A page finished loading, by its own load event or WebKit's. Answers the
/// pending navigate, releases held requests, emits `load`, once per page.
fn page_loaded(p: &mut Pending, tab: TabId, url: &str, proxy: &EventLoopProxy<UserEvent>) {
    trace_navigation("loaded", tab, p, url);
    // The runtime load IPC can precede the native Finished callback. A click
    // may already have started the next provisional load in between them;
    // the duplicate must not release requests into the old document.
    if p.awaiting_start
        || p.native_generation != p.generation
        || !p.committed
        || std::mem::replace(&mut p.loaded, true)
    {
        return;
    }
    milestone(p, Until::Load, tab, url, proxy);
    emit(json!({ "event": "load", "tab": tab, "url": url }));
}

fn history_traversed(p: &mut Pending, tab: TabId, url: &str, proxy: &EventLoopProxy<UserEvent>) {
    #[cfg(target_os = "windows")]
    if p.native_start.is_some() && p.native_history {
        if !p.history_changed {
            p.history_reply = Some(url.to_owned());
            return;
        }
        // Same-URL pushState traversal has neither NavigationStarting nor
        // SourceChanged. Both native flags and popstate acknowledge this call.
        let current = p.windows_history_completed();
        let _ = proxy.send_event(UserEvent::StartNavigation(tab));
        if !current {
            return;
        }
    }
    if p.history_url.is_none() {
        return;
    }
    let Some((id, false)) = p.navigate else {
        return;
    };
    #[cfg(target_os = "windows")]
    if !p.history_changed {
        p.history_reply = Some(url.to_owned());
        return;
    }
    p.navigate = None;
    p.history_url = None;
    reply(id, json!({ "tab": tab, "url": url }));
    p.awaiting_start = false;
    let _ = proxy.send_event(p.flush_event(tab));
}

/// The page reached `stage`: answer a navigate that asked for it and release
/// the held requests. `load` always releases them, so a page that never
/// reaches idle still serves the agent.
fn milestone(
    p: &mut Pending,
    stage: Until,
    tab: TabId,
    url: &str,
    proxy: &EventLoopProxy<UserEvent>,
) {
    if let Some((id, true)) = p.navigate {
        // WebView2 shows its error page as a normal load; that is a failed navigate.
        if url.starts_with(CHROME_ERROR_SCHEME) {
            p.navigate = None;
            fail(
                id,
                format!(
                    "navigate {}: load failed",
                    p.navigate_url.take().unwrap_or_default()
                ),
            );
        } else if p.navigate_until == stage {
            p.navigate = None;
            // The rest of this load may still be cancelled by the agent's next
            // move; that is no longer this navigate's failure.
            p.navigate_url = None;
            reply(id, json!({ "tab": tab, "url": url }));
        }
    }
    if stage == Until::Load || p.navigate_until == stage {
        // Keep requests queued until Flush has submitted the current color
        // preference. The document-start script captures the tab's original
        // preference, which may have changed since the view was created.
        let _ = proxy.send_event(p.flush_event(tab));
    }
}

type Shared = Rc<RefCell<Pending>>;

struct Tab {
    webview: WebView,
    // WKWebView keeps a weak delegate; retain our forwarding observer per tab.
    #[cfg(target_os = "macos")]
    navigation: objc2::rc::Retained<navigation_macos::NavigationObserver>,
    window: Window,
    pending: Shared,
}

/// Command line options that shape every webview.
#[derive(Default)]
#[cfg_attr(not(target_os = "linux"), allow(dead_code))] // some only apply to WebKitGTK
struct Opts {
    hidden: bool,
    dark: bool,
    insecure: bool,
    no_images: bool,
    user_agent: Option<String>,
    proxy: Option<String>,
    init_script: Option<String>,
    profile: Option<PathBuf>,
    /// The data directory is the shared cache: drop cookies and storage left
    /// by an earlier session, keep the HTTP cache.
    fresh_session: bool,
    /// macOS: data store id of this run when there is no profile.
    #[cfg(target_os = "macos")]
    session_store: [u8; 16],
}

struct App {
    window_state: window_state::Store,
    tabs: HashMap<TabId, Tab>,
    next_tab: TabId,
    current: TabId,
    opts: Opts,
    viewport: (u32, u32),
    /// Shared across tabs so they see one profile (cookies, storage) and one
    /// network process.
    context: WebContext,
    /// Data directory of a session without --profile, removed at exit.
    scratch: Option<PathBuf>,
    /// Last page load, to let the disk cache settle before exit.
    last_load: std::time::Instant,
    proxy: EventLoopProxy<UserEvent>,
    deadline_timer: std::sync::mpsc::Sender<Option<std::time::Instant>>,
    next_deadline: Option<std::time::Instant>,
}

fn emit(v: Value) {
    let Some(v) = mcp::outgoing(v) else { return };
    write_json(&v);
}

/// Buffer a complete record under one stdout lock, then flush immediately.
/// Serde otherwise turns a large result into thousands of small pipe writes.
fn write_json(v: &impl serde::Serialize) {
    let mut out = std::io::BufWriter::new(std::io::stdout().lock());
    let _ = serde_json::to_writer(&mut out, &v);
    let _ = out.write_all(b"\n");
    let _ = out.flush();
}

fn reply(id: u64, result: Value) {
    emit(json!({ "id": id, "result": result }));
}

/// Borrow and validate the payload without allocating a Value tree. Unknown
/// envelopes (including errors and events) use the normal protocol path.
#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct PageReply<'a> {
    id: u64,
    #[serde(borrow)]
    result: &'a serde_json::value::RawValue,
    document: &'a str,
    attempt: u64,
    #[serde(rename = "generation")]
    _generation: u64,
    #[serde(default)]
    navigating: bool,
}

fn navigation_deadline(params: &Value) -> Result<std::time::Instant, String> {
    let timeout = match params.get("timeout") {
        Some(value) => Duration::from_millis(
            value
                .as_u64()
                .ok_or("timeout must be a non-negative integer")?,
        ),
        None => NAVIGATE_TIMEOUT,
    };
    std::time::Instant::now()
        .checked_add(timeout)
        .ok_or_else(|| "timeout is too large".into())
}

fn fail(id: u64, msg: impl ToString) {
    emit(json!({ "id": id, "error": msg.to_string() }));
}

/// Value following `--name`, if any.
fn opt(args: &[String], name: &str) -> Option<String> {
    args.iter()
        .position(|a| a == name)
        .and_then(|i| args.get(i + 1))
        .cloned()
}

/// "1280x800" -> (1280, 800).
fn parse_viewport(s: &str) -> Option<(u32, u32)> {
    let (w, h) = s.split_once('x')?;
    Some((w.parse().ok()?, h.parse().ok()?))
}

fn main() -> wry::Result<()> {
    let args: Vec<String> = std::env::args().collect();
    let has = |flag: &str| args.iter().any(|a| a == flag);
    ensure_display(&args[1..]);
    mcp::enable(has(MCP_FLAG));
    if has(QUIET_FLAG) {
        silence_stderr();
    }

    let init_script = match opt(&args, INIT_SCRIPT_OPT) {
        Some(p) => Some(
            std::fs::read_to_string(&p).unwrap_or_else(|e| panic!("{INIT_SCRIPT_OPT} {p}: {e}")),
        ),
        None => None,
    };
    let opts = Opts {
        // MCP clients never want windows on the desktop; --visible brings them back.
        hidden: (has(HIDDEN_FLAG) || has(MCP_FLAG)) && !has(VISIBLE_FLAG),
        dark: has(DARK_FLAG),
        insecure: has(INSECURE_FLAG),
        no_images: has(NO_IMAGES_FLAG),
        user_agent: opt(&args, USER_AGENT_OPT),
        proxy: opt(&args, PROXY_OPT),
        init_script,
        profile: opt(&args, PROFILE_OPT).map(PathBuf::from),
        fresh_session: false,
        #[cfg(target_os = "macos")]
        session_store: session_store_id(),
    };
    let viewport = opt(&args, VIEWPORT_OPT)
        .map(|v| parse_viewport(&v).expect("--viewport WxH"))
        .unwrap_or(DEFAULT_VIEWPORT);

    // Must be set before GTK/WebKit initialise or any threads are started.
    #[cfg(target_os = "linux")]
    {
        // Software rendering saves ~200 MB under Xvfb.
        std::env::set_var("WEBKIT_DISABLE_COMPOSITING_MODE", "1");
        if opts.hidden && std::env::var_os("WEBKIT_DISABLE_DMABUF_RENDERER").is_none() {
            // The software renderer does not need the EGL/DMA-BUF transport probe.
            std::env::set_var("WEBKIT_DISABLE_DMABUF_RENDERER", "1");
        }
        if opts.hidden && std::env::var("BRUSTER_USE_SESSION_BUS").as_deref() != Ok("1") {
            // Hidden automation does not need desktop session integration. GTK's
            // Inhibit proxy and Tao's theme lookup can synchronously wait 25 + 5 s
            // for an unresponsive portal; the theme wait repeats for new tabs.
            // An explicit unsupported transport fails immediately; unsetting it can
            // instead autolaunch another bus. Visible mode keeps the desktop bus.
            std::env::set_var("DBUS_SESSION_BUS_ADDRESS", "disabled:");
        }
    }

    let event_loop = EventLoopBuilder::<UserEvent>::with_user_event().build();
    spawn_stdin_reader(event_loop.create_proxy());

    // Without a profile: the shared cache directory when no other bruster
    // holds it (warm HTTP cache, cookies and storage wiped at start), else a
    // scratch directory removed at exit. The lock lives as long as the process.
    let mut opts = opts;
    let (dir, scratch, _lock) = match &opts.profile {
        Some(p) => (p.clone(), None, None),
        None => match lock_cache_dir() {
            Some((dir, lock)) => {
                opts.fresh_session = true;
                (dir, None, Some(lock))
            }
            None => {
                let dir = std::env::temp_dir().join(format!("bruster-{}", std::process::id()));
                (dir.clone(), Some(dir), None)
            }
        },
    };
    let mut window_state = window_state::Store::load(opts.profile.as_deref());
    if opts.dark {
        window_state.save_dark(true)?;
    }
    opts.dark = window_state.dark;
    let mut app = App {
        window_state,
        tabs: HashMap::new(),
        next_tab: 1,
        current: 1,
        context: WebContext::new(Some(dir)),
        scratch,
        last_load: std::time::Instant::now() - CACHE_FLUSH_DELAY,
        opts,
        viewport,
        proxy: event_loop.create_proxy(),
        deadline_timer: spawn_deadline_timer(event_loop.create_proxy()),
        next_deadline: None,
    };
    app.open_tab(&event_loop, None)?;
    // Only once WebKit is up: calling into WKWebsiteDataStore before the
    // first webview exists crashes the process.
    #[cfg(target_os = "macos")]
    if app.opts.profile.is_none() {
        remove_stale_session_stores(app.opts.session_store);
    }

    emit(json!({ "event": "ready" }));

    event_loop.run(move |event, target, control_flow| {
        *control_flow = ControlFlow::Wait;

        match event {
            Event::UserEvent(UserEvent::Eof) => {
                app.shutdown();
                *control_flow = ControlFlow::Exit;
            }
            Event::WindowEvent {
                event: WindowEvent::CloseRequested,
                window_id,
                ..
            } => {
                app.close_window(window_id);
            }
            Event::UserEvent(UserEvent::OpenTab(url)) => {
                if let Ok(id) = app.open_tab(target, Some(&url)) {
                    emit(json!({ "event": "tab_opened", "tab": id, "url": url }));
                }
            }
            Event::UserEvent(UserEvent::FullShot {
                tab,
                id,
                path,
                height,
            }) => {
                app.full_shot(tab, id, path, height);
            }
            Event::UserEvent(UserEvent::TallShot {
                tab,
                id,
                path,
                height,
                tries,
                restore,
            }) => {
                app.tall_shot_poll(tab, id, path, height, tries, restore);
            }
            Event::UserEvent(UserEvent::TallShotReady {
                tab,
                id,
                path,
                restore,
            }) => {
                app.viewport_shot_then_restore(tab, id, path, restore);
            }
            Event::UserEvent(UserEvent::RestoreSize { tab, size }) => {
                if let Some(t) = app.tabs.get(&tab) {
                    t.window.set_inner_size(size);
                }
            }
            Event::UserEvent(UserEvent::Flush { tab, generation }) => {
                app.last_load = std::time::Instant::now();
                app.flush(tab, generation);
            }
            Event::UserEvent(UserEvent::BindDocument { tab, generation }) => {
                if let Some(t) = app.tabs.get(&tab) {
                    if t.pending.borrow().generation == generation {
                        let _ = t
                            .webview
                            .evaluate_script(&format!("window.__bruster?.bind({generation})"));
                    }
                }
            }
            #[cfg(target_os = "windows")]
            Event::UserEvent(UserEvent::StartNavigation(tab)) => {
                if let Some(t) = app.tabs.get(&tab) {
                    navigation_windows::resume(&t.webview, tab, &t.pending, &app.proxy);
                }
            }
            Event::UserEvent(UserEvent::EvalRetry { tab, id, attempt }) => {
                app.eval_retry(tab, id, attempt)
            }
            Event::UserEvent(UserEvent::EvalFailed { tab, id, attempt }) => {
                app.eval_failed(tab, id, attempt)
            }
            Event::UserEvent(UserEvent::NavigateTimeout { tab, id, token }) => {
                if let Some(t) = app.tabs.get(&tab) {
                    let mut p = t.pending.borrow_mut();
                    if p.waiting_for(id, token) {
                        let url = p.navigate_url.take().unwrap_or_default();
                        p.navigate = None;
                        p.loading = false;
                        p.awaiting_start = false;
                        let generation = p.generation;
                        #[cfg(target_os = "windows")]
                        let stop = p.native_start.is_none();
                        #[cfg(not(target_os = "windows"))]
                        let stop = true;
                        drop(p);
                        // A queued WebView2 start still needs to identify its
                        // call. The handler cancels it when it finally arrives.
                        if stop {
                            stop_loading(&t.webview);
                        }
                        fail(id, format!("navigate {url}: timed out"));
                        app.flush(tab, generation);
                    }
                }
            }
            Event::UserEvent(UserEvent::HistoryTimeout { tab, id, token }) => {
                // Fallback for engines restoring a page without load events.
                if let Some(t) = app.tabs.get(&tab) {
                    let mut p = t.pending.borrow_mut();
                    if p.waiting_for(id, token) && p.navigate == Some((id, false))
                        // WebView2 must acknowledge HistoryChanged before the
                        // next back/forward reads CanGoBack/CanGoForward.
                        && !cfg!(target_os = "windows")
                        && p.awaiting_start
                        && !navigation_in_progress(&t.webview)
                    {
                        let current = t.webview.url().ok();
                        if current.is_some() && current != p.history_url {
                            p.navigate = None;
                            p.history_url = None;
                            reply(id, json!({ "tab": tab, "url": current }));
                            p.awaiting_start = false;
                            let _ = app.proxy.send_event(p.flush_event(tab));
                        }
                    }
                }
            }
            Event::UserEvent(UserEvent::Command(req)) => {
                if req.method == "close" {
                    reply(req.id, Value::Null);
                    app.shutdown();
                    *control_flow = ControlFlow::Exit;
                    return;
                }
                app.dispatch(target, req);
            }
            _ => {}
        }
        if *control_flow != ControlFlow::Exit {
            app.deadlines();
        }
    });
}

/// MCP clients spawn servers with a scrubbed environment, so on a Linux box
/// with a desktop DISPLAY is often missing, and on a server there is none.
/// WebKitGTK needs one: re-run under a virtual display when available.
#[cfg(target_os = "linux")]
fn ensure_display(args: &[String]) {
    use std::os::unix::process::CommandExt;
    let has_display = ["DISPLAY", "WAYLAND_DISPLAY"]
        .iter()
        .any(|v| std::env::var_os(v).is_some_and(|d| !d.is_empty()));
    if has_display {
        return;
    }
    if std::env::var_os("BRUSTER_NO_XVFB").is_none() {
        if let Ok(me) = std::env::current_exe() {
            // exec only returns on failure. Never continue into GTK without a display.
            let error = std::process::Command::new("xvfb-run")
                .arg("-a")
                .arg("-s")
                .arg(std::env::var("BRUSTER_XVFB_ARGS").unwrap_or_else(|_| {
                    "-screen 0 1280x1024x24 -nolisten tcp -extension GLX".into()
                }))
                .arg(me)
                .args(args)
                .exec();
            eprintln!("bruster: could not start xvfb-run: {error}");
        }
    }
    eprintln!("bruster: WebKitGTK requires a display, even with --hidden/--mcp; set DISPLAY or WAYLAND_DISPLAY, or install Xvfb (xvfb-run).");
    std::process::exit(1);
}

#[cfg(not(target_os = "linux"))]
fn ensure_display(_args: &[String]) {}

/// WebKitGTK, GTK, ALSA and Mesa all write warnings to stderr that the
/// agent cannot act on. Point fd 2 at /dev/null for the whole process.
#[cfg(unix)]
fn silence_stderr() {
    use std::os::fd::AsRawFd;
    if let Ok(null) = std::fs::OpenOptions::new().write(true).open("/dev/null") {
        unsafe { libc::dup2(null.as_raw_fd(), libc::STDERR_FILENO) };
    }
}

#[cfg(not(unix))]
fn silence_stderr() {}

/// Reads one JSON request per line and forwards it to the event loop.
fn spawn_stdin_reader(proxy: EventLoopProxy<UserEvent>) {
    std::thread::spawn(move || {
        for line in std::io::stdin().lock().lines() {
            let Ok(line) = line else { break };
            if line.trim().is_empty() {
                continue;
            }

            match mcp::incoming(&line) {
                Ok(Some(req)) => {
                    let _ = proxy.send_event(UserEvent::Command(req));
                }
                Ok(None) => {} // handled entirely by the mcp layer
                Err(e) => emit(json!({ "error": format!("bad request: {e}") })),
            }
        }

        let _ = proxy.send_event(UserEvent::Eof);
    });
}

/// One reschedulable timer for all page and navigation calls. Tao's GTK WaitUntil path can
/// block in gtk::main_iteration_do(true) until unrelated activity arrives;
/// sending a user event wakes it reliably. Completed calls cancel the timer,
/// rather than leaving a sleeping thread behind for every request.
fn spawn_deadline_timer(
    proxy: EventLoopProxy<UserEvent>,
) -> std::sync::mpsc::Sender<Option<std::time::Instant>> {
    use std::sync::mpsc::{channel, RecvTimeoutError};
    let (tx, rx) = channel::<Option<std::time::Instant>>();
    std::thread::spawn(move || {
        let mut next: Option<std::time::Instant> = None;
        loop {
            let update = match next {
                Some(deadline) => {
                    rx.recv_timeout(deadline.saturating_duration_since(std::time::Instant::now()))
                }
                None => rx.recv().map_err(|_| RecvTimeoutError::Disconnected),
            };
            match update {
                Ok(deadline) => next = deadline,
                Err(RecvTimeoutError::Timeout) => {
                    if proxy.send_event(UserEvent::Deadline).is_err() {
                        break;
                    }
                    next = None;
                }
                Err(RecvTimeoutError::Disconnected) => break,
            }
        }
    });
    tx
}

impl App {
    /// Expire unanswered calls and arrange a wakeup for the next deadline.
    fn deadlines(&mut self) {
        let now = std::time::Instant::now();
        let mut next = None;
        for (&tab_id, tab) in &self.tabs {
            let mut pending = tab.pending.borrow_mut();
            for history in [false, true] {
                let deadline = if history {
                    pending.history_deadline.take()
                } else {
                    pending.navigation_deadline.take()
                };
                if let (Some(at), Some((id, started))) = (deadline, pending.navigate) {
                    if history && started {
                        continue;
                    }
                    if at <= now {
                        let token = pending.navigation_token;
                        let event = if history {
                            UserEvent::HistoryTimeout {
                                tab: tab_id,
                                id,
                                token,
                            }
                        } else {
                            UserEvent::NavigateTimeout {
                                tab: tab_id,
                                id,
                                token,
                            }
                        };
                        let _ = self.proxy.send_event(event);
                    } else {
                        next = Some(next.map_or(at, |n: std::time::Instant| n.min(at)));
                        if history {
                            pending.history_deadline = Some(at);
                        } else {
                            pending.navigation_deadline = Some(at);
                        }
                    }
                }
            }
            pending.js.retain(|id, request| {
                if request.deadline <= now {
                    fail(*id, format!("{}: page request timed out", request.method));
                    false
                } else {
                    next = Some(next.map_or(request.deadline, |n: std::time::Instant| {
                        n.min(request.deadline)
                    }));
                    true
                }
            });
            pending.queue.retain(|(id, request)| {
                if request.deadline <= now {
                    fail(*id, format!("{}: page request timed out", request.method));
                    false
                } else {
                    next = Some(next.map_or(request.deadline, |n: std::time::Instant| {
                        n.min(request.deadline)
                    }));
                    true
                }
            });
        }
        if next != self.next_deadline {
            self.next_deadline = next;
            let _ = self.deadline_timer.send(next);
        }
    }
    fn open_tab(
        &mut self,
        target: &EventLoopWindowTarget<UserEvent>,
        url: Option<&str>,
    ) -> wry::Result<TabId> {
        let id = self.next_tab;
        self.next_tab += 1;

        // An unmapped window never renders, which breaks screenshots on WebKitGTK.
        // "Hidden" therefore means a fixed-size window parked off-screen.
        let mut builder = WindowBuilder::new()
            .with_title(format!("bruster {id}"))
            .with_inner_size(tao::dpi::LogicalSize::new(self.viewport.0, self.viewport.1));
        if self.opts.hidden {
            builder = builder
                .with_position(tao::dpi::LogicalPosition::new(OFFSCREEN, OFFSCREEN))
                .with_decorations(false);
        }
        let window = builder.build(target).expect("window");
        if !self.opts.hidden {
            self.window_state.state.apply(&window);
        }

        let pending: Shared = Rc::default();
        pending.borrow_mut().warming = url.is_none();
        pending.borrow_mut().loading = true;
        if url.is_some() {
            pending.borrow_mut().begin_navigation();
        }
        let webview = build_webview(
            &window,
            id,
            pending.clone(),
            self.proxy.clone(),
            url,
            &self.opts,
            &mut self.context,
        )?;
        #[cfg(target_os = "macos")]
        let navigation =
            navigation_macos::observe(&webview, id, pending.clone(), self.proxy.clone());

        self.tabs.insert(
            id,
            Tab {
                window,
                webview,
                #[cfg(target_os = "macos")]
                navigation,
                pending,
            },
        );
        if self.tabs.len() == 1 {
            self.current = id;
        }
        Ok(id)
    }

    fn close_tab(&mut self, id: TabId) -> bool {
        self.close_tab_inner(id, true)
    }

    fn close_tab_inner(&mut self, id: TabId, _terminate: bool) -> bool {
        let Some(tab) = self.tabs.remove(&id) else {
            return false;
        };
        let mut pending = tab.pending.borrow_mut();
        let Pending { js, queue, .. } = &mut *pending;
        for (js, _) in js.drain().chain(queue.drain(..)) {
            fail(js, "tab closed");
        }
        if let Some((nav_id, _)) = pending.navigate.take() {
            fail(nav_id, "tab closed");
        }
        drop(pending);
        // Wry creates independent views, not related-view children (popups are
        // denied and opened through open_tab). Release this tab's web process
        // instead of leaving it in WebKit's idle process cache after close.
        #[cfg(target_os = "linux")]
        if _terminate {
            use webkit2gtk::WebViewExt;
            use wry::WebViewExtUnix;
            tab.webview.webview().terminate_web_process();
        }
        // Tab declares the WebView before its parent window, so Wry's own
        // destructor destroys the native child before Tao tears down the parent.
        drop(tab);
        if self.current == id {
            self.current = self.tabs.keys().min().copied().unwrap_or(0);
        }
        true
    }

    /// Fails every request still waiting on a tab before the process exits,
    /// instead of dropping the stdout pipe out from under them.
    fn shutdown(&mut self) {
        let persistent = self.opts.profile.is_some();
        if persistent {
            // Storage may have changed long after the last load. Let WebKit's
            // processes persist it while the views are still alive, and do not
            // forcibly kill them on this graceful profile shutdown path.
            std::thread::sleep(CACHE_FLUSH_DELAY);
        }
        for id in self.tabs.keys().copied().collect::<Vec<_>>() {
            self.close_tab_inner(id, !persistent);
        }
        match &self.scratch {
            Some(dir) => {
                let _ = std::fs::remove_dir_all(dir);
            }
            // Persistent directory: give the network process time to write the cache.
            None => std::thread::sleep(CACHE_FLUSH_DELAY.saturating_sub(self.last_load.elapsed())),
        }
        // The webviews are gone (close_tab dropped them); the session store can go too.
        #[cfg(target_os = "macos")]
        if self.opts.profile.is_none() {
            use wry::WebViewExtDarwin;
            WebView::remove_data_store(&self.opts.session_store, |_| {});
            std::thread::sleep(STORE_REMOVE_WAIT);
        }
    }

    /// Runs the requests that waited for a load to finish.
    fn flush(&self, t: TabId, generation: u64) {
        let Some(tab) = self.tabs.get(&t) else { return };
        if tab.pending.borrow().generation != generation {
            return;
        }
        let _ = tab
            .webview
            .evaluate_script(&color_scheme_script(self.opts.dark));
        let queued = {
            let mut pending = tab.pending.borrow_mut();
            trace_navigation("flush", t, &pending, "");
            pending.loading = false;
            pending.hinted = None;
            std::mem::take(&mut pending.queue)
        };
        for (id, q) in queued {
            tab_dispatch(tab, t, id, q, &self.proxy);
        }
    }

    /// Second try of an eval whose expression form did not compile.
    fn eval_retry(&self, t: TabId, id: u64, attempt: u64) {
        let Some(tab) = self.tabs.get(&t) else { return };
        let Some(q) = tab.pending.borrow().js.get(&id).cloned() else {
            return;
        };
        if q.attempt != attempt {
            return;
        }
        let expr = q.params["expression"].as_str().unwrap_or("");
        let proxy = self.proxy.clone();
        let done = move |compiled: String| {
            if compiled != EVAL_COMPILED {
                let _ = proxy.send_event(UserEvent::EvalFailed {
                    tab: t,
                    id,
                    attempt,
                });
            }
        };
        let src = format!(
            "(__bruster.evalFn({id}, async () => {{\n{expr}\n}}, {attempt}), {EVAL_COMPILED})"
        );
        if let Err(e) = tab.webview.evaluate_script_with_callback(&src, done) {
            tab.pending.borrow_mut().js.remove(&id);
            fail(id, e);
        }
    }

    fn eval_failed(&self, t: TabId, id: u64, attempt: u64) {
        let Some(tab) = self.tabs.get(&t) else { return };
        if !tab
            .pending
            .borrow()
            .js
            .get(&id)
            .is_some_and(|q| q.attempt == attempt)
        {
            return;
        }
        if tab.pending.borrow_mut().js.remove(&id).is_some() {
            fail(
                id,
                "eval: not valid JavaScript (as an expression or as statements)",
            );
        }
    }

    fn close_window(&mut self, wid: WindowId) {
        let id = self
            .tabs
            .iter()
            .find(|(_, t)| t.window.id() == wid)
            .map(|(id, _)| *id);
        if let Some(id) = id {
            if self.tabs.len() == 1 {
                return;
            }
            self.close_tab(id);
            emit(json!({ "event": "tab_closed", "tab": id }));
        }
    }

    fn dispatch(&mut self, target: &EventLoopWindowTarget<UserEvent>, req: Request) {
        let Request {
            id,
            method,
            params,
            tab,
        } = req;
        if !params.is_null() && !params.is_object() {
            return fail(id, format!("{method}: params must be an object"));
        }

        // Tab management does not need a live tab.
        match method.as_str() {
            "new_tab" => {
                let url = params.get("url").and_then(Value::as_str);
                if let Some(url) = url.filter(|u| !valid_url(u)) {
                    return fail(id, format!("new_tab: invalid url '{url}'"));
                }
                let deadline = match navigation_deadline(&params) {
                    Ok(at) => at,
                    Err(e) => return fail(id, format!("new_tab: {e}")),
                };
                return match self.open_tab(target, url) {
                    // With a url the load handler answers {tab, url} once the page is in.
                    Ok(t) if url.is_some() => {
                        let mut pending = self.tabs[&t].pending.borrow_mut();
                        pending.navigate = Some((id, false));
                        pending.navigation_token = pending.generation;
                        pending.navigate_url = url.map(str::to_owned);
                        pending.navigation_deadline = Some(deadline);
                    }
                    Ok(t) => reply(id, json!({ "tab": t })),
                    Err(e) => fail(id, e),
                };
            }
            "close_tab" => {
                let t = tab.unwrap_or(self.current);
                if self.tabs.len() == 1 && self.tabs.contains_key(&t) {
                    return fail(
                        id,
                        "close_tab: cannot close the last tab; use close to shut down",
                    );
                }
                return match self.close_tab(t) {
                    true => reply(id, Value::Null),
                    false => fail(id, format!("no such tab {t}")),
                };
            }
            "switch_tab" => {
                // MCP lifts `tab` out of the arguments, so accept it at either level.
                let Some(t) = params
                    .get("tab")
                    .and_then(Value::as_u64)
                    .map(|t| t as TabId)
                    .or(tab)
                else {
                    return fail(id, "switch_tab: missing params.tab");
                };
                if !self.tabs.contains_key(&t) {
                    return fail(id, format!("no such tab {t}"));
                }
                self.current = t;
                return reply(id, Value::Null);
            }
            "tabs" => {
                let mut list: Vec<Value> = self
                    .tabs
                    .iter()
                    .map(|(t, tab)| json!({ "tab": t, "url": tab.webview.url().unwrap_or_default(), "current": *t == self.current }))
                    .collect();
                list.sort_by_key(|v| v["tab"].as_u64());
                return reply(id, json!(list));
            }
            _ => {}
        }

        let t = tab.unwrap_or(self.current);
        let Some(tab) = self.tabs.get(&t) else {
            return fail(id, format!("no such tab {t}"));
        };

        if let Some(state) = window_state::State::command(&method) {
            if let Err(e) = self.window_state.save(state) {
                return fail(id, format!("{method}: save window state: {e}"));
            }
            if !self.opts.hidden {
                state.apply(&tab.window);
            }
            return reply(id, json!(state));
        }

        if matches!(method.as_str(), "dark" | "light") {
            let dark = method == "dark";
            if let Err(e) = self.window_state.save_dark(dark) {
                return fail(id, format!("{method}: save color preference: {e}"));
            }
            self.opts.dark = dark;
            for tab in self.tabs.values() {
                if let Err(e) = tab.webview.evaluate_script(&color_scheme_script(dark)) {
                    return fail(id, e);
                }
            }
            return reply(id, json!(method));
        }

        if method == "screenshot" {
            return self.screenshot(t, id, &params);
        }

        if method == "resize" {
            let size = |k: &str| params.get(k).and_then(Value::as_u64).map(|v| v as u32);
            let (Some(w), Some(h)) = (size("width"), size("height")) else {
                return fail(id, "resize: need width and height");
            };
            if !(1..=MAX_VIEWPORT_SIDE).contains(&w) || !(1..=MAX_VIEWPORT_SIDE).contains(&h) {
                return fail(
                    id,
                    format!("resize: width and height must be between 1 and {MAX_VIEWPORT_SIDE}"),
                );
            }
            self.viewport = (w, h);
            tab.window.set_inner_size(tao::dpi::LogicalSize::new(w, h));
            return reply(id, json!({ "width": w, "height": h }));
        }

        // Files are read here; the page gets them as base64.
        let params = match method.as_str() {
            "upload" => match attach_files(params) {
                Ok(p) => p,
                Err(e) => return fail(id, e),
            },
            _ => params,
        };

        match Queued::new(method, params) {
            Ok(request) => tab_dispatch(tab, t, id, request, &self.proxy),
            Err(e) => fail(id, e),
        }
    }

    fn screenshot(&self, t: TabId, id: u64, params: &Value) {
        let tab = &self.tabs[&t];
        let path = params
            .get("path")
            .and_then(Value::as_str)
            .map(str::to_owned);
        let full = params.get("full").and_then(Value::as_bool).unwrap_or(false);

        let region = match params.get("clip") {
            Some(c) => {
                let f = |k: &str| c.get(k).and_then(Value::as_f64);
                match (f("x"), f("y"), f("width"), f("height")) {
                    (Some(x), Some(y), Some(width), Some(height))
                        if width >= 1.0 && height >= 1.0 =>
                    {
                        Region::Clip(Clip {
                            x,
                            y,
                            width,
                            height,
                        })
                    }
                    _ => return fail(id, "screenshot: clip needs x, y and non-zero width, height"),
                }
            }
            None if full => Region::Full,
            None => Region::Viewport,
        };

        // A full capture first asks the page for its height: WKWebView only
        // renders the visible area, and cairo cannot hold a very tall surface.
        if matches!(region, Region::Full) {
            let proxy = self.proxy.clone();
            let fallback = tab
                .window
                .inner_size()
                .to_logical::<f64>(tab.window.scale_factor())
                .height;
            let res = tab.webview.evaluate_script_with_callback(
                "Math.max(document.documentElement.scrollHeight, document.body.scrollHeight)",
                move |h| {
                    let height = h.parse::<f64>().unwrap_or(fallback);
                    let _ = proxy.send_event(UserEvent::FullShot {
                        tab: t,
                        id,
                        path: path.clone(),
                        height,
                    });
                },
            );
            if let Err(e) = res {
                fail(id, e);
            }
            return;
        }

        screenshot::capture(&tab.webview, region, finish_shot(id, path));
    }

    fn full_shot(&self, t: TabId, id: u64, path: Option<String>, height: f64) {
        let Some(tab) = self.tabs.get(&t) else {
            return fail(id, format!("no such tab {t}"));
        };

        // WebKitGTK renders the whole document in one go when it fits in cairo.
        if cfg!(target_os = "linux") && height <= CAIRO_MAX_SIDE {
            return screenshot::capture(&tab.webview, Region::Full, finish_shot(id, path));
        }

        let height = height.min(MAX_FULL_HEIGHT);
        let restore = tab
            .window
            .inner_size()
            .to_logical::<f64>(tab.window.scale_factor());
        tab.window
            .set_inner_size(tao::dpi::LogicalSize::new(restore.width, height));

        // GTK applies the resize asynchronously; WKWebView is ready right away.
        if cfg!(target_os = "linux") {
            let _ = self.proxy.send_event(UserEvent::TallShot {
                tab: t,
                id,
                path,
                height,
                tries: 0,
                restore,
            });
            return;
        }
        self.viewport_shot_then_restore(t, id, path, restore);
    }

    /// Captures once the page reports the enlarged viewport, or after TALL_SHOT_TRIES polls.
    fn tall_shot_poll(
        &self,
        t: TabId,
        id: u64,
        path: Option<String>,
        height: f64,
        tries: u8,
        restore: tao::dpi::LogicalSize<f64>,
    ) {
        let Some(tab) = self.tabs.get(&t) else {
            return fail(id, format!("no such tab {t}"));
        };
        let proxy = self.proxy.clone();
        let res = tab
            .webview
            .evaluate_script_with_callback("innerHeight", move |h| {
                let seen = h.parse::<f64>().unwrap_or(0.0);
                let ev = if seen >= height - 1.0 || tries >= TALL_SHOT_TRIES {
                    UserEvent::TallShotReady {
                        tab: t,
                        id,
                        path: path.clone(),
                        restore,
                    }
                } else {
                    std::thread::sleep(TALL_SHOT_POLL);
                    UserEvent::TallShot {
                        tab: t,
                        id,
                        path: path.clone(),
                        height,
                        tries: tries + 1,
                        restore,
                    }
                };
                let _ = proxy.send_event(ev);
            });
        if let Err(e) = res {
            tab.window.set_inner_size(restore);
            fail(id, e);
        }
    }

    fn viewport_shot_then_restore(
        &self,
        t: TabId,
        id: u64,
        path: Option<String>,
        restore: tao::dpi::LogicalSize<f64>,
    ) {
        let Some(tab) = self.tabs.get(&t) else {
            return fail(id, format!("no such tab {t}"));
        };
        let proxy = self.proxy.clone();
        let done = finish_shot(id, path);
        screenshot::capture(
            &tab.webview,
            Region::Viewport,
            Box::new(move |png| {
                let _ = proxy.send_event(UserEvent::RestoreSize {
                    tab: t,
                    size: restore,
                });
                done(png);
            }),
        );
    }
}

/// Builds the screenshot completion: write to `path` or return base64.
fn finish_shot(id: u64, path: Option<String>) -> screenshot::Done {
    Box::new(move |png| match (png, path) {
        (Err(e), _) => fail(id, e),
        (Ok(png), Some(p)) => match std::fs::write(&p, &png) {
            Ok(_) => reply(id, json!({ "path": p, "bytes": png.len() })),
            Err(e) => fail(id, e),
        },
        (Ok(png), None) => reply(id, json!({ "png_base64": screenshot::base64(&png) })),
    })
}

fn build_webview(
    window: &Window,
    tab: TabId,
    pending: Shared,
    proxy: EventLoopProxy<UserEvent>,
    url: Option<&str>,
    opts: &Opts,
    context: &mut WebContext,
) -> wry::Result<WebView> {
    let ipc_pending = pending.clone();
    let ipc_proxy = proxy.clone();
    let window_proxy = proxy.clone();

    let mut builder = WebViewBuilder::new_with_web_context(context);
    builder = builder
        .with_initialization_script(color_scheme_script(opts.dark))
        .with_initialization_script(RUNTIME_JS)
        .with_ipc_handler(move |req| {
            if !mcp::enabled() {
                if let Ok(body) = serde_json::from_str::<PageReply>(req.body()) {
                    // Raw JSON may contain whitespace supplied by page code.
                    // Preserve the one-line protocol even for custom IPC.
                    if !body.result.get().contains(['\n', '\r']) {
                        let mut p = ipc_pending.borrow_mut();
                        if !p.take_page_reply(body.id, Some(body.document), Some(body.attempt)) {
                            return;
                        }
                        if body.navigating && !p.loading {
                            p.begin_navigation();
                            p.hinted = Some(body.id);
                            trace_navigation("hint", tab, &p, "");
                        }
                        #[derive(serde::Serialize)]
                        struct Reply<'a> {
                            id: u64,
                            result: &'a serde_json::value::RawValue,
                        }
                        write_json(&Reply {
                            id: body.id,
                            result: body.result,
                        });
                        return;
                    }
                }
            }
            // runtime.js answers with {"id":..,"result":..} or {"id":..,"error":..},
            // asks for a tab with {"open": url}, or reports {"event": ..}.
            let Ok(mut body) = serde_json::from_str::<Value>(req.body()) else {
                return;
            };
            let document = body
                .get("document")
                .and_then(Value::as_str)
                .map(str::to_owned);
            let generation = body.get("generation").and_then(Value::as_u64);
            if body.get("bound") == Some(&Value::Bool(true)) {
                let mut p = ipc_pending.borrow_mut();
                if generation == Some(p.generation) && !p.awaiting_start {
                    p.document = document;
                } else if generation == Some(0)
                    && document.is_some()
                    && p.committed
                    && !p.awaiting_start
                    && p.document.is_none()
                {
                    // Commit can arrive before the document-start runtime is
                    // installed. Its initial announcement retries an early
                    // BindDocument that found no __bruster yet.
                    let _ = ipc_proxy.send_event(UserEvent::BindDocument {
                        tab,
                        generation: p.generation,
                    });
                }
                return;
            }
            if let Some(url) = body.get("open").and_then(Value::as_str) {
                let _ = ipc_proxy.send_event(UserEvent::OpenTab(url.to_owned()));
                return;
            }
            if let Some(url) = body.get("loaded").and_then(Value::as_str) {
                let mut p = ipc_pending.borrow_mut();
                if p.current_milestone(document.as_deref(), generation) {
                    page_loaded(&mut p, tab, url, &ipc_proxy);
                }
                return;
            }
            if let Some(url) = body.get("history").and_then(Value::as_str) {
                let mut p = ipc_pending.borrow_mut();
                if document.is_some() && document == p.document {
                    history_traversed(&mut p, tab, url, &ipc_proxy);
                }
                return;
            }
            for (key, stage) in [("dom", Until::Dom), ("idle", Until::Idle)] {
                if let Some(url) = body.get(key).and_then(Value::as_str) {
                    let mut p = ipc_pending.borrow_mut();
                    if p.current_milestone(document.as_deref(), generation) {
                        milestone(&mut p, stage, tab, url, &ipc_proxy);
                    }
                    return;
                }
            }
            if let Some(hosts) = body.get("prefetch").and_then(Value::as_array) {
                prefetch_dns(hosts.iter().filter_map(Value::as_str));
                return;
            }
            if let Some(id) = body.get("id").and_then(Value::as_u64) {
                let mut p = ipc_pending.borrow_mut();
                // A timed-out request can still finish later. Never emit a
                // second reply or apply a stale navigation hint.
                if !p.take_page_reply(
                    id,
                    document.as_deref(),
                    body.get("attempt").and_then(Value::as_u64),
                ) {
                    return;
                }
                if body
                    .as_object_mut()
                    .and_then(|o| o.remove("navigating"))
                    .is_some_and(|value| value == Value::Bool(true))
                    && !p.loading
                {
                    p.begin_navigation();
                    p.hinted = Some(id);
                    trace_navigation("hint", tab, &p, "");
                }
            }
            if body.get("event").is_some() {
                body["tab"] = json!(tab);
            }
            if let Some(object) = body.as_object_mut() {
                object.remove("document");
                object.remove("generation");
                object.remove("attempt");
            }
            emit(body);
        })
        .with_new_window_req_handler(move |url, _| {
            let _ = window_proxy.send_event(UserEvent::OpenTab(url));
            NewWindowResponse::Deny
        });

    #[cfg(not(target_os = "windows"))]
    {
        let load_pending = pending.clone();
        let load_proxy = proxy.clone();
        builder = builder.with_on_page_load_handler(move |ev, url| {
            page_load(&mut load_pending.borrow_mut(), ev, tab, &url, &load_proxy);
        });
        // Warm the renderer. Windows attaches ID-bearing handlers before its
        // initial load below: overlapping NavigationCompleted is not ordered.
        builder = builder.with_url(url.unwrap_or("about:blank"));
    }

    if let Some(js) = &opts.init_script {
        builder = builder.with_initialization_script(js.clone());
    }
    if let Some(ua) = &opts.user_agent {
        builder = builder.with_user_agent(ua.clone());
    }
    if let Some(p) = &opts.proxy {
        builder = builder.with_proxy_config(parse_proxy(p)?);
    }
    // WKWebView has no data directory; a profile maps to a data store id.
    // Without one the default store would be shared by every bruster on the
    // machine and an incognito store by nothing (one per tab), so each
    // session gets its own id, removed at exit or by the next start.
    #[cfg(target_os = "macos")]
    {
        use wry::WebViewBuilderExtDarwin;
        if opts.hidden {
            // Automation must keep DOM timers and network-idle checks running
            // when WKWebView considers an off-screen tab inactive (macOS 14+).
            // Animation frames still require a visible window.
            builder = builder.with_background_throttling(wry::BackgroundThrottlingPolicy::Disabled);
        }
        builder = builder.with_data_store_identifier(
            opts.profile
                .as_deref()
                .map(profile_id)
                .unwrap_or(opts.session_store),
        );
    }

    #[cfg(not(target_os = "linux"))]
    let webview = builder.build(window)?;
    #[cfg(target_os = "windows")]
    {
        navigation_windows::observe(&webview, tab, pending.clone(), proxy.clone())?;
        track_history(&webview, tab, pending.clone(), proxy)?;
        navigation_windows::navigate(
            &webview,
            &pending,
            "navigate",
            Some(url.unwrap_or("about:blank")),
        )?;
    }
    #[cfg(target_os = "linux")]
    let webview = {
        use tao::platform::unix::WindowExtUnix;
        use wry::WebViewBuilderExtUnix;
        let vbox = window.default_vbox().expect("tao default vbox");
        let wv = builder.build_gtk(vbox)?;
        trim_webkit(&wv, tab, opts, pending, proxy);
        wv
    };

    Ok(webview)
}

/// Portable fallback: request native dark/light form controls and page defaults.
/// Do not spoof matchMedia: CSS media queries would disagree with that shim.
fn color_scheme_script(dark: bool) -> String {
    let scheme = if dark { "dark" } else { "light" };
    format!(
        r#"(() => {{
        const apply = () => document.documentElement.style.setProperty('color-scheme', '{scheme}', 'important');
        if (document.documentElement) apply();
        else {{
            const observer = new MutationObserver(() => {{
                if (document.documentElement) {{ apply(); observer.disconnect(); }}
            }});
            observer.observe(document, {{childList: true, subtree: true}});
        }}
    }})()"#
    )
}

/// `$XDG_CACHE_HOME/bruster/default` (or `~/.cache/...`) with an exclusive
/// lock, or None when it does not exist and cannot be made, or another
/// bruster is using it. Two processes on one WebKit data directory corrupt it.
fn lock_cache_dir() -> Option<(PathBuf, std::fs::File)> {
    let home = std::env::var_os("XDG_CACHE_HOME")
        .map(PathBuf::from)
        .or_else(|| std::env::var_os("HOME").map(|h| PathBuf::from(h).join(".cache")))?;
    let dir = home.join("bruster").join("default");
    std::fs::create_dir_all(&dir).ok()?;
    let lock = std::fs::File::create(dir.join("lock")).ok()?;
    try_flock(&lock).then_some((dir, lock))
}

#[cfg(unix)]
fn try_flock(f: &std::fs::File) -> bool {
    use std::os::fd::AsRawFd;
    unsafe { libc::flock(f.as_raw_fd(), libc::LOCK_EX | libc::LOCK_NB) == 0 }
}

#[cfg(not(unix))]
fn try_flock(_: &std::fs::File) -> bool {
    false
}

/// Warms DNS for hosts the agent is likely to visit next (Linux; WebKitGTK has no preconnect).
#[cfg(target_os = "linux")]
fn prefetch_dns<'a>(hosts: impl Iterator<Item = &'a str>) {
    use webkit2gtk::WebContextExt;
    if let Some(ctx) = webkit2gtk::WebContext::default() {
        for h in hosts {
            ctx.prefetch_dns(h);
        }
    }
}

#[cfg(not(target_os = "linux"))]
fn prefetch_dns<'a>(_hosts: impl Iterator<Item = &'a str>) {}

/// Absolute url with a scheme and a host, or an about: page.
fn valid_url(url: &str) -> bool {
    let Ok(uri) = url.parse::<wry::http::Uri>() else {
        return false;
    };
    match uri.scheme_str() {
        Some("about") => true,
        Some(_) => uri.host().is_some(),
        None => false,
    }
}

#[cfg(target_os = "linux")]
fn stop_loading(wv: &WebView) {
    use webkit2gtk::WebViewExt;
    use wry::WebViewExtUnix;
    wv.webview().stop_loading();
}

#[cfg(target_os = "macos")]
fn stop_loading(wv: &WebView) {
    use wry::WebViewExtMacOS;
    unsafe { wv.webview().stopLoading() };
}

#[cfg(target_os = "windows")]
fn stop_loading(wv: &WebView) {
    use wry::WebViewExtWindows;
    let _ = unsafe { wv.webview().Stop() };
}

#[cfg(target_os = "windows")]
fn track_history(
    wv: &WebView,
    tab: TabId,
    pending: Shared,
    proxy: EventLoopProxy<UserEvent>,
) -> wry::Result<()> {
    use webview2_com::HistoryChangedEventHandler;
    use wry::WebViewExtWindows;
    let handler = HistoryChangedEventHandler::create(Box::new(move |_, _| {
        let mut p = pending.borrow_mut();
        p.history_changed = true;
        if let Some(url) = p.history_reply.take() {
            history_traversed(&mut p, tab, &url, &proxy);
        }
        Ok(())
    }));
    let mut token = 0;
    unsafe { wv.webview().add_HistoryChanged(&handler, &mut token) }?;
    Ok(())
}

#[cfg(target_os = "macos")]
fn navigation_in_progress(wv: &WebView) -> bool {
    use wry::WebViewExtMacOS;
    unsafe { wv.webview().isLoading() }
}

#[cfg(target_os = "linux")]
fn navigation_in_progress(wv: &WebView) -> bool {
    use webkit2gtk::WebViewExt;
    use wry::WebViewExtUnix;
    wv.webview().is_loading()
}

// WebView2's NavigationStarting handler above already clears the hint.
#[cfg(not(any(target_os = "macos", target_os = "linux")))]
fn navigation_in_progress(_wv: &WebView) -> bool {
    false
}

/// "http://host:port" or "socks5://host:port".
fn parse_proxy(s: &str) -> wry::Result<ProxyConfig> {
    let bad = || {
        wry::Error::Io(std::io::Error::other(format!(
            "{PROXY_OPT}: expected http://host:port or socks5://host:port, got {s}"
        )))
    };
    let (scheme, rest) = s.split_once("://").ok_or_else(bad)?;
    let (host, port) = rest
        .trim_end_matches('/')
        .rsplit_once(':')
        .ok_or_else(bad)?;
    let endpoint = ProxyEndpoint {
        host: host.to_owned(),
        port: port.to_owned(),
    };
    match scheme {
        "http" => Ok(ProxyConfig::Http(endpoint)),
        "socks5" => Ok(ProxyConfig::Socks5(endpoint)),
        _ => Err(bad()),
    }
}

/// Session data stores start with this marker so stale ones can be told from profiles.
#[cfg(target_os = "macos")]
const SESSION_STORE_MARK: [u8; 8] = *b"bruster\0";
/// Removing a data store is asynchronous; give it this long at exit.
#[cfg(target_os = "macos")]
const STORE_REMOVE_WAIT: Duration = Duration::from_millis(500);

/// Per-process data store id: marker plus the pid and start time.
#[cfg(target_os = "macos")]
fn session_store_id() -> [u8; 16] {
    let nanos = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .map(|d| d.subsec_nanos())
        .unwrap_or(0);
    let mut id = [0u8; 16];
    id[..8].copy_from_slice(&SESSION_STORE_MARK);
    id[8..12].copy_from_slice(&std::process::id().to_le_bytes());
    id[12..].copy_from_slice(&nanos.to_le_bytes());
    id
}

/// Removes session stores left by earlier runs (a crash skips the exit cleanup).
#[cfg(target_os = "macos")]
fn remove_stale_session_stores(keep: [u8; 16]) {
    use wry::WebViewExtDarwin;
    let _ = WebView::fetch_data_store_identifiers(move |ids| {
        for id in ids
            .into_iter()
            .filter(|id| id[..8] == SESSION_STORE_MARK && *id != keep)
        {
            WebView::remove_data_store(&id, |_| {});
        }
    });
}

/// Stable 16-byte id for a profile path (FNV-1a over two seeds).
#[cfg(target_os = "macos")]
fn profile_id(dir: &Path) -> [u8; 16] {
    let fnv = |seed: u64| {
        dir.to_string_lossy()
            .bytes()
            .fold(seed, |h, b| (h ^ b as u64).wrapping_mul(0x100000001b3))
    };
    let mut id = [0u8; 16];
    id[..8].copy_from_slice(&fnv(0xcbf29ce484222325).to_le_bytes());
    id[8..].copy_from_slice(&fnv(0x84222325cbf29ce4).to_le_bytes());
    id
}

/// Reads `paths` and adds `files: [{name, type, data}]` for runtime.js.
fn attach_files(mut params: Value) -> Result<Value, String> {
    let paths: Vec<String> =
        serde_json::from_value(params.get("paths").cloned().unwrap_or(Value::Null))
            .map_err(|_| "upload: need params.paths (array of file paths)")?;
    let mut files = Vec::with_capacity(paths.len());
    for p in &paths {
        let path = Path::new(p);
        let bytes = std::fs::read(path).map_err(|e| format!("upload {p}: {e}"))?;
        let ext = path
            .extension()
            .and_then(|e| e.to_str())
            .unwrap_or("")
            .to_ascii_lowercase();
        let mime = MIME_TYPES
            .iter()
            .find(|(e, _)| *e == ext)
            .map(|(_, m)| *m)
            .unwrap_or(OCTET_STREAM);
        files.push(json!({
            "name": path.file_name().and_then(|n| n.to_str()).unwrap_or("file"),
            "type": mime,
            "data": screenshot::base64(&bytes),
        }));
    }
    params["files"] = json!(files);
    Ok(params)
}

fn start_navigation(tab: &Tab, _id: u64, method: &str, url: Option<&str>) -> wry::Result<()> {
    #[cfg(target_os = "macos")]
    return tab.navigation.navigate(&tab.webview, _id, method, url);
    #[cfg(target_os = "windows")]
    return navigation_windows::navigate(&tab.webview, &tab.pending, method, url);
    #[cfg(not(any(target_os = "macos", target_os = "windows")))]
    match method {
        "navigate" => tab.webview.load_url(url.unwrap()),
        "reload" => tab.webview.reload(),
        "back" => tab.webview.go_back(),
        "forward" => tab.webview.go_forward(),
        _ => unreachable!("not a native navigation"),
    }
}

/// `retries` counts how many navigations this request has already outlived.
fn tab_dispatch(tab: &Tab, t: TabId, id: u64, request: Queued, proxy: &EventLoopProxy<UserEvent>) {
    let wv = &tab.webview;
    let pending = &tab.pending;
    let method = request.method.as_str();
    let params = &request.params;

    // Answered by the load handler once the new page finishes. Registered
    // before the call in case the webview reports Started synchronously.
    let await_load = |url: Option<&str>, go: &dyn Fn() -> wry::Result<()>| {
        let until = Until::parse(params.get("until"))
            .map_err(|e| wry::Error::Io(std::io::Error::other(format!("{method}: {e}"))))?;
        let deadline = navigation_deadline(params)
            .map_err(|e| wry::Error::Io(std::io::Error::other(format!("{method}: {e}"))))?;
        let mut p = pending.borrow_mut();
        // One pending navigation per tab: a new one takes over, the old one hears about it.
        if let Some((old, _)) = p.navigate.take() {
            fail(
                old,
                format!(
                    "navigate {}: superseded by a new navigation",
                    p.navigate_url.take().unwrap_or_default()
                ),
            );
        }
        p.navigate = Some((id, false));
        p.begin_navigation();
        p.navigation_token = p.generation;
        p.navigate_until = until;
        p.navigate_url = url.map(str::to_owned);
        p.history_url = if matches!(method, "back" | "forward") {
            wv.url().ok()
        } else {
            None
        };
        p.navigation_deadline = Some(deadline);
        p.history_deadline = p
            .history_url
            .as_ref()
            .map(|_| std::time::Instant::now() + HISTORY_START_TIMEOUT);
        drop(p);
        go().map(|_| None)
    };

    // Page requests sent while a load is in flight run in the new page,
    // like an agent expects after clicking a link.
    let in_page = |p: &mut Pending| -> bool {
        // Flush may run after the deadline but before the event-loop sweep.
        // Expired queued actions must never be dispatched to the new page.
        if request.deadline <= std::time::Instant::now() {
            fail(id, format!("{method}: page request timed out"));
            return false;
        }
        if !p.loading {
            let mut dispatched = request.clone();
            dispatched.document = p.document.clone();
            p.next_attempt += 1;
            dispatched.attempt = p.next_attempt;
            p.js.insert(id, dispatched);
            return true;
        }
        p.queue.push((id, request.clone()));
        false
    };

    let native: wry::Result<Option<Value>> = match method {
        "navigate" => {
            let Some(url) = params.get("url").and_then(Value::as_str) else {
                return fail(id, "navigate: missing params.url");
            };
            // A page at a malformed url cannot answer: wry drops IPC from it.
            if !valid_url(url) {
                return fail(id, format!("navigate: invalid url '{url}'"));
            }
            await_load(Some(url), &|| start_navigation(tab, id, method, Some(url)))
        }
        "reload" => await_load(None, &|| start_navigation(tab, id, method, None)),
        "back" | "forward" => {
            let can_go = if method == "back" {
                wv.can_go_back()
            } else {
                wv.can_go_forward()
            };
            match can_go {
                Ok(false) => return reply(id, Value::Null),
                Err(e) => return fail(id, e),
                Ok(true) => {}
            }
            await_load(None, &|| start_navigation(tab, id, method, None))
        }
        "cookies" => wv.cookies().map(|cs| Some(cookies_json(&cs))),
        "set_cookie" => set_cookie(wv, params).map(|_| Some(Value::Null)),
        // The expression is compiled as script source, not passed to eval(),
        // so a page CSP without 'unsafe-eval' cannot refuse it. The wrapper
        // answers EVAL_COMPILED when it parsed; the statement form is the
        // fallback (see App::eval_retry) and the page posts the real result.
        "eval" => {
            let Some(expr) = params.get("expression").and_then(Value::as_str) else {
                return fail(id, "eval: missing params.expression");
            };
            if !in_page(&mut pending.borrow_mut()) {
                return;
            }
            let proxy = proxy.clone();
            let attempt = pending.borrow().js[&id].attempt;
            let src = format!(
                "(__bruster.evalFn({id}, async () => (\n{expr}\n), {attempt}), {EVAL_COMPILED})"
            );
            wv.evaluate_script_with_callback(&src, move |compiled| {
                if compiled != EVAL_COMPILED {
                    let _ = proxy.send_event(UserEvent::EvalRetry {
                        tab: t,
                        id,
                        attempt,
                    });
                }
            })
            .map(|_| None)
        }
        _ => {
            if !in_page(&mut pending.borrow_mut()) {
                return;
            }
            let attempt = pending.borrow().js[&id].attempt;
            let js = format!(
                "__bruster.run({id}, {}, {}, {attempt})",
                json!(method),
                params
            );
            wv.evaluate_script(&js).map(|_| None)
        }
    };

    match native {
        Ok(Some(v)) => reply(id, v),
        Ok(None) => {} // answered later by the page or the load handler
        Err(e) => {
            let mut p = pending.borrow_mut();
            p.js.remove(&id);
            if p.navigate.is_some_and(|(nid, _)| nid == id) {
                p.navigate = None;
                p.awaiting_start = false;
                let _ = proxy.send_event(p.flush_event(t));
            }
            fail(id, e);
        }
    }
}

fn cookies_json(cookies: &[wry::cookie::Cookie<'_>]) -> Value {
    cookies
        .iter()
        .map(|c| {
            json!({
                "name": c.name(),
                "value": c.value(),
                "domain": c.domain(),
                "path": c.path(),
                "secure": c.secure(),
                "http_only": c.http_only(),
            })
        })
        .collect()
}

fn set_cookie(wv: &WebView, params: &Value) -> wry::Result<()> {
    let s = |k: &str| params.get(k).and_then(Value::as_str).map(str::to_owned);
    let (Some(name), Some(value)) = (s("name"), s("value")) else {
        return Err(wry::Error::Io(std::io::Error::other(
            "set_cookie: need name and value",
        )));
    };

    // Without a domain the store keeps an orphan the page never sees, so
    // default to the current page's host and root path.
    let host = wv
        .url()?
        .parse::<wry::http::Uri>()
        .ok()
        .and_then(|u| u.host().map(str::to_owned));
    let Some(domain) = s("domain").or(host) else {
        return Err(wry::Error::Io(std::io::Error::other(
            "set_cookie: need domain when no page is loaded",
        )));
    };
    let b = wry::cookie::Cookie::build((name, value))
        .domain(domain)
        .path(s("path").unwrap_or_else(|| "/".into()));
    wv.set_cookie(&b.build())
}

/// Software rendering and a document-viewer cache model. An agent browser
/// has no GPU to speak of and never goes back/forward through cached pages.
#[cfg(target_os = "linux")]
fn trim_webkit(
    wv: &WebView,
    tab: TabId,
    opts: &Opts,
    pending: Shared,
    proxy: EventLoopProxy<UserEvent>,
) {
    use webkit2gtk::{
        gio, glib, CacheModel, DownloadExt, HardwareAccelerationPolicy, LoadEvent, PolicyError,
        ScriptDialogType, SettingsExt, TLSErrorsPolicy, URIRequestExt, WebContextExt, WebViewExt,
        WebsiteDataManagerExt, WebsiteDataManagerExtManual, WebsiteDataTypes,
    };
    use wry::WebViewExtUnix;

    // Every tab shares the default WebContext, so hook its downloads once.
    static DOWNLOADS_HOOKED: std::sync::Once = std::sync::Once::new();
    static DATA_CLEARED: std::sync::Once = std::sync::Once::new();

    let inner = wv.webview();
    if opts.hidden && std::env::var("BRUSTER_PAINT_HIDDEN").as_deref() != Ok("1") {
        use gtk::prelude::WidgetExt;
        // Hidden windows stay mapped for layout, animation and native snapshots.
        // Their off-screen GTK paint is unused, and WebKit can synchronously
        // wait 500 ms for an empty backing store here. A load-finished gate is
        // too early: the backing store can still be absent after that signal.
        inner.connect_draw(|_, _| glib::Propagation::Stop);
    }
    if let Some(s) = inner.settings() {
        s.set_hardware_acceleration_policy(HardwareAccelerationPolicy::Never);
        s.set_enable_page_cache(false);
        s.set_enable_webgl(false);
        s.set_enable_media(false);
        s.set_auto_load_images(!opts.no_images);
    }
    if let Some(ctx) = inner.context() {
        // DocumentBrowser keeps the disk cache with moderate memory caches;
        // DocumentViewer turns all caching off, WebBrowser costs ~100 MB more RSS.
        ctx.set_cache_model(CacheModel::DocumentBrowser);
        if opts.insecure {
            if let Some(dm) = ctx.website_data_manager() {
                dm.set_tls_errors_policy(TLSErrorsPolicy::Ignore);
            }
        }
        // Shared cache directory: keep the HTTP cache, forget the last session's
        // cookies and storage. Once per process, before the first real load.
        if opts.fresh_session {
            DATA_CLEARED.call_once(|| {
                if let Some(dm) = ctx.website_data_manager() {
                    let site_data = WebsiteDataTypes::ALL
                        - WebsiteDataTypes::DISK_CACHE
                        - WebsiteDataTypes::MEMORY_CACHE;
                    dm.clear(
                        site_data,
                        glib::TimeSpan::from_seconds(0),
                        None::<&gio::Cancellable>,
                        |_| {},
                    );
                }
            });
        }
        // An agent browser never wants files dropped into its working directory.
        DOWNLOADS_HOOKED.call_once(|| {
            ctx.connect_download_started(|_, dl| {
                let url = dl.request().and_then(|r| r.uri()).unwrap_or_default();
                dl.cancel();
                emit(json!({ "event": "download", "url": url.as_str() }));
            });
        });
    }
    // A rejected certificate otherwise shows up as a silent blank page.
    inner.connect_load_failed_with_tls_errors(|_, url, _, flags| {
        emit(json!({ "event": "tls_error", "url": url, "flags": format!("{flags:?}") }));
        false
    });
    // runtime.js answers alert/confirm/prompt in JS; beforeunload is native
    // and would block the tab forever. Confirm it and tell the agent.
    inner.connect_script_dialog(move |_, dialog| {
        if dialog.dialog_type() != ScriptDialogType::BeforeUnloadConfirm {
            return false;
        }
        dialog.confirm_set_confirmed(true);
        emit(json!({ "event": "dialog", "tab": tab, "type": "beforeunload", "message": dialog.message().unwrap_or_default().as_str(), "accept": true }));
        true
    });
    // wry reports Committed as Started. The provisional start comes earlier,
    // right after a click: from here on page requests are held for the new page.
    let start_pending = pending.clone();
    inner.connect_load_changed(move |_, ev| {
        if ev == LoadEvent::Started {
            let mut p = start_pending.borrow_mut();
            p.provisional_start();
        }
    });
    // DNS errors, refused connections and cancelled downloads: fail the
    // navigate instead of answering with the error page as if it had loaded.
    // Returning true also skips WebKit's error page, whose own load events
    // would otherwise leak into the agent's next navigate.
    inner.connect_load_failed(move |_, _, url, err| {
        let mut p = pending.borrow_mut();
        // GTK reports the retiring load's cancellation before the next Started.
        // Identical URLs are still distinct operations. Never attribute the old
        // failure (or its following Finished) to the newly installed waiter.
        if p.warming || p.native_generation != p.generation {
            return true;
        }
        let why = match err.kind::<PolicyError>() {
            Some(PolicyError::FrameLoadInterruptedByPolicyChange) => {
                "download started, cancelled".to_owned()
            }
            _ => err.to_string(),
        };
        p.loading = false;
        p.awaiting_start = false;
        if let Some((id, _)) = p.navigate.take() {
            fail(id, format!("navigate {url}: {why}"));
        }
        emit(json!({ "event": "load_failed", "url": url, "error": why }));
        // The old page is still there: run what waited for the failed load.
        let _ = proxy.send_event(p.flush_event(tab));
        true
    });
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn navigation_timeout_follows_the_waiter_across_document_changes() {
        let mut p = Pending::default();
        p.begin_navigation();
        p.navigate = Some((7, true));
        p.navigation_token = p.generation;
        let expired_token = p.navigation_token;
        // The timeout is queued, then a redirect starts before it is handled.
        p.begin_navigation();
        assert!(p.waiting_for(7, expired_token));
        // A replacement command, even with a reused public ID, invalidates it.
        p.begin_navigation();
        p.navigation_token = p.generation;
        assert!(!p.waiting_for(7, expired_token));
        assert!(p.waiting_for(7, p.navigation_token));
        p.navigate = None;
        assert!(!p.waiting_for(7, p.navigation_token));
    }

    #[test]
    fn parses_options() {
        assert_eq!(parse_viewport("640x480"), Some((640, 480)));
        assert_eq!(parse_viewport("640"), None);
        assert!(
            matches!(parse_proxy("http://h:3128"), Ok(ProxyConfig::Http(e)) if e.host == "h" && e.port == "3128")
        );
        assert!(matches!(
            parse_proxy("socks5://h:1080/"),
            Ok(ProxyConfig::Socks5(_))
        ));
        assert!(parse_proxy("ftp://h:1").is_err());
        assert!(parse_proxy("h:1").is_err());
        let args: Vec<String> = ["bruster", "--viewport", "1x1", "--mcp"]
            .map(String::from)
            .to_vec();
        assert_eq!(opt(&args, "--viewport").as_deref(), Some("1x1"));
        assert_eq!(opt(&args, "--profile"), None);
    }
}
