//! Shared test helper: spawns the binary, serves fixture pages on localhost,
//! speaks the native protocol. Needs a display (Linux: `xvfb-run cargo test`).
#![allow(dead_code)]

use std::io::{BufRead, BufReader, Read, Write};
use std::net::TcpListener;
use std::process::{Child, Command, Stdio};
use std::time::{Duration, Instant};

use serde_json::{json, Value};

/// Generous: e2e tests wait on real sites. Hangs are still caught, just later.
pub const REPLY_TIMEOUT: Duration = Duration::from_secs(60);
pub const SLOW_DELAY: Duration = Duration::from_millis(300);

pub const PAGE: &str = r##"<html><head><title>smoke</title></head><body>
<h1>Hello</h1>
<input id="name" placeholder="Your name">
<button id="go" onclick="document.getElementById('out').textContent='hi '+document.getElementById('name').value">Go</button>
<p id="out"></p>
<a href="#x" style="display:none">hidden</a>
<a id="blank" href="/other" target="_blank">open</a>
<div style="height:3000px"></div>
<script>fetch('/api').catch(()=>{});</script>
</body></html>"##;

pub const FORM: &str = r##"<html><head><title>form</title></head><body>
<h1>Form</h1>
<form id="f" onsubmit="event.preventDefault(); document.getElementById('out').textContent='submitted:'+document.getElementById('q').value">
<input id="q" name="q" data-k="v">
<input id="typed" oninput="this.dataset.n=(+this.dataset.n||0)+1">
<div id="ce" contenteditable></div>
<select id="s"><option value="a">A</option><option value="b">B</option></select>
<select id="m" multiple><option value="x">X</option><option value="y">Y</option></select>
<input type="checkbox" id="c">
<button type="button" id="dis" disabled>Nope</button>
<div id="hov" onmouseover="this.textContent='hovered'">hover me</div>
<a id="lnk" href="/other">Other</a>
<div id="far" style="margin-top:2000px">far</div>
</form>
<p id="out"></p>
<script>
document.addEventListener('keydown', e => { if (e.key === 'Escape') document.getElementById('out').textContent = 'esc'; });
</script>
</body></html>"##;

pub const OTHER: &str =
    "<html><head><title>other</title></head><body><p>other page</p></body></html>";
// Inserts an iframe after load; WebKit's own "finished" waits for it, the page's load event does not.
pub const LATEFRAME: &str = r##"<html><head><title>lateframe</title></head><body><p>late</p>
<script>addEventListener('load', () => { window.__loadedAt = performance.now(); const f = document.createElement('iframe'); f.src = '/slower'; document.body.appendChild(f); });</script>
</body></html>"##;
// until=dom must answer before this image arrives; until=idle must wait for the late fetch.
pub const SLOWIMG: &str = r##"<html><head><title>slowimg</title></head><body><p>img</p><img src="/slower"></body></html>"##;
pub const LATEFETCH: &str = r##"<html><head><title>latefetch</title></head><body><p>fetch</p>
<script>addEventListener('load', () => setTimeout(() => fetch('/slow'), 50));</script></body></html>"##;
// Cached script with a hit counter: a warm HTTP cache serves it without a request.
// Fetches forever (no timer: hidden windows throttle timers): until=idle must give up at its cap instead of hanging.
pub const POLLING: &str = r##"<html><head><title>polling</title></head><body><p>poll</p>
<script>(function loop() { fetch('/other?' + Date.now()).then(loop, loop); })();</script></body></html>"##;
pub const CACHEDPAGE: &str = r##"<html><head><title>cached</title><script src="/cached.js"></script></head><body><p>cached</p></body></html>"##;
pub static CACHED_HITS: std::sync::atomic::AtomicUsize = std::sync::atomic::AtomicUsize::new(0);
// A beforeunload prompt is a native dialog; it must be answered, not block the tab.
pub const BEFOREUNLOAD: &str = r##"<html><head><title>bu</title></head><body>
<script>addEventListener('beforeunload', e => { e.preventDefault(); e.returnValue = 'x'; });</script>
<a id="l" href="/other">leave</a></body></html>"##;
pub const XML: &str = r##"<?xml version="1.0"?><root><item>x</item></root>"##;
pub const SPA: &str = r##"<html><head><title>spa</title></head><body><p id="p">home</p>
<a id="go" href="/spa/about" onclick="event.preventDefault(); history.pushState({}, '', '/spa/about'); document.getElementById('p').textContent = 'about'">about</a>
</body></html>"##;
pub const SHADOWDEEP: &str = r##"<html><head><title>shadow</title></head><body><div id="h"></div>
<script>let host = document.getElementById('h'); for (let i = 0; i < 5; i++) { const r = host.attachShadow({mode: 'open'}); r.innerHTML = `<div>level ${i}</div>`; host = r.querySelector('div'); }
host.innerHTML = '<button id="deep" onclick="document.title = \'deep-clicked\'">deep</button>';</script></body></html>"##;
pub const TALL: &str = r##"<html><head><title>tall</title></head><body style="margin:0"><div style="height:40000px;background:linear-gradient(red,blue)"></div><p id="end">END</p></body></html>"##;
pub const PROXIED: &str = "<html><head><title>proxied</title></head><body>via proxy</body></html>";

pub const EXTRA: &str = r##"<html><head><title>extra</title></head><body>
<button id="al" onclick="document.getElementById('out').textContent='c:'+confirm('sure?')">confirm</button>
<button id="pr" onclick="document.getElementById('out').textContent='p:'+prompt('name?','def')">prompt</button>
<p id="out"></p>
<iframe id="fr" srcdoc="<button id='in' onclick='parent.document.title=&quot;inner-clicked&quot;'>inner</button>"></iframe>
<div id="host"></div>
<button id="dis" disabled>Nope</button>
<div style="position:relative;width:200px;height:40px">
  <button id="under" style="position:absolute;inset:0" onclick="this.textContent='clicked'">under</button>
  <div id="over" style="position:absolute;inset:0;z-index:2"></div>
</div>
<input type="file" id="up" multiple onchange="document.getElementById('out').textContent='files:'+[...this.files].map(f=>f.name+':'+f.size+':'+f.type).join(',')">
<div id="src" draggable="true" ondragstart="event.dataTransfer.setData('text/plain','payload')">drag me</div>
<div id="dst" ondragover="event.preventDefault()" ondrop="this.textContent='got:'+event.dataTransfer.getData('text/plain')">drop here</div>
<input id="combo" onkeydown="if(event.ctrlKey&&event.key==='k')this.value='ctrl-k'">
<form id="sf" onsubmit="event.preventDefault();document.getElementById('out').textContent='sub:'+document.getElementById('sq').value"><input id="sq"></form>
<select id="sel"><option value="a">A</option><option value="b">B</option></select>
<input type="checkbox" id="cb"><input id="fi">
<span aria-hidden="true"><button id="ah">invisible to snapshot</button></span>
<script>
document.getElementById('host').attachShadow({mode:'open'}).innerHTML = '<button id="sh" onclick="document.title=\'shadow-clicked\'">shadow</button>';
console.log('hello', {a:1}); console.warn('careful');
setTimeout(() => { throw new Error('later boom'); }, 50);
</script>
</body></html>"##;

pub const TEXTS: &str = r##"<html><head><title>texts</title></head><body>
<div id="flash">You logged in <a href="#">&times;</a></div>
<div>Beta only text</div>
<span>Gamma <b>bold</b></span>
<pre>code block</pre>
<p>Para <a href="#">inline</a> tail</p>
<div><div>nested only text</div></div>
<div style="display:none">hidden text</div>
<script>var notText = 1;</script>
<a href="/other"><img alt="Fork me" src=""></a>
<input type="checkbox" id="nolabel">
<ul><li><a href="/other">Only link</a></li></ul>
</body></html>"##;

pub const FRAMES: &str = r##"<html><head><title>frames</title></head><frameset cols="50%,50%">
<frame src="/texts"><frame src="/other">
</frameset></html>"##;

pub const MORE: &str = r##"<html><head><title>more</title></head><body>
<input id="k"><input id="num" type="number"><p id="p">plain</p>
<select id="s"><option value="a">A</option><option value="b">B</option></select>
<a id="away" href="/slow">away</a>
<form id="gf" action="/slow"><input id="go" name="go"></form>
<script>
window.keys = [];
document.addEventListener('keydown', e => keys.push([e.key, e.code, e.keyCode, e.which]));
</script>
</body></html>"##;

pub struct Browser {
    pub child: Child,
    pub stdin: std::process::ChildStdin,
    /// Lines from stdout, read on a thread so a silent server cannot hang a test.
    pub lines: std::sync::mpsc::Receiver<String>,
    pub next_id: u64,
    pub stash: Vec<Value>,
    /// Set once a test has already sent its own `close`, so Drop does not
    /// send a second one to a process that has already exited.
    pub closed: bool,
}

impl Browser {
    pub fn spawn() -> Self {
        Self::spawn_with(&[])
    }

    pub fn spawn_with(args: &[&str]) -> Self {
        Self::spawn_env(args, &[])
    }

    pub fn spawn_env(args: &[&str], envs: &[(&str, &str)]) -> Self {
        let mut child = Command::new(env!("CARGO_BIN_EXE_bruster"))
            .arg("--hidden")
            .args(args)
            .envs(envs.iter().copied())
            .stdin(Stdio::piped())
            .stdout(Stdio::piped())
            .stderr(test_stderr())
            .spawn()
            .expect("spawn bruster");
        let stdin = child.stdin.take().unwrap();
        let stdout = child.stdout.take().unwrap();
        let (tx, lines) = std::sync::mpsc::channel();
        std::thread::spawn(move || {
            for line in BufReader::new(stdout).lines().map_while(Result::ok) {
                if tx.send(line).is_err() {
                    break;
                }
            }
        });
        let mut b = Browser {
            child,
            stdin,
            lines,
            next_id: 0,
            stash: Vec::new(),
            closed: false,
        };
        b.wait_event("ready");
        b
    }

    pub fn next_line(&mut self) -> Value {
        let line = self
            .lines
            .recv_timeout(REPLY_TIMEOUT)
            .expect("no line from bruster within REPLY_TIMEOUT");
        serde_json::from_str(&line).unwrap()
    }

    /// Takes the first stashed or incoming message matching `pick`. Events and
    /// replies interleave freely, so anything else read meanwhile is stashed.
    pub fn take(&mut self, what: &str, pick: impl Fn(&Value) -> bool) -> Value {
        let start = Instant::now();
        loop {
            if let Some(i) = self.stash.iter().position(&pick) {
                return self.stash.remove(i);
            }
            assert!(
                start.elapsed() < REPLY_TIMEOUT,
                "timeout waiting for {what}"
            );
            let v = self.next_line();
            self.stash.push(v);
        }
    }

    pub fn wait_event(&mut self, name: &str) -> Value {
        self.take(&format!("event {name}"), |v| v["event"] == name)
    }

    /// Loads of other tabs may already be stashed, so match the tab.
    pub fn wait_load(&mut self, tab: u64) -> Value {
        self.take(&format!("load of tab {tab}"), |v| {
            v["event"] == "load" && v["tab"] == tab
        })
    }

    /// Sends a request without waiting. `tab` inside params is lifted to the top level.
    pub fn send(&mut self, method: &str, params: Value) -> u64 {
        self.next_id += 1;
        let id = self.next_id;
        let mut params = params;
        let tab = params.as_object_mut().and_then(|o| o.remove("tab"));
        let req = json!({ "id": id, "method": method, "params": params, "tab": tab });
        // A dead server shows up as a missing reply, not as a second panic in Drop.
        let _ = writeln!(self.stdin, "{req}");
        id
    }

    pub fn recv(&mut self, id: u64) -> Result<Value, String> {
        let v = self.take(&format!("reply {id}"), |v| v["id"] == id);
        if let Some(e) = v.get("error") {
            return Err(e.as_str().unwrap_or("?").to_owned());
        }
        Ok(v["result"].clone())
    }

    pub fn call(&mut self, method: &str, params: Value) -> Result<Value, String> {
        let id = self.send(method, params);
        self.recv(id)
    }

    pub fn ok(&mut self, method: &str, params: Value) -> Value {
        self.call(method, params)
            .unwrap_or_else(|e| panic!("{method} failed: {e}"))
    }

    pub fn err(&mut self, method: &str, params: Value) -> String {
        self.call(method, params)
            .expect_err(&format!("{method} should fail"))
    }

    /// Drops our end of the pipe; bruster treats EOF as close.
    pub fn close_stdin(&mut self) {
        let dummy = Command::new("true")
            .stdin(Stdio::piped())
            .spawn()
            .unwrap()
            .stdin
            .take()
            .unwrap();
        drop(std::mem::replace(&mut self.stdin, dummy));
    }

    pub fn open(&mut self, url: &str) {
        self.ok("navigate", json!({ "url": url }));
    }
}

impl Drop for Browser {
    fn drop(&mut self) {
        if std::thread::panicking() {
            let _ = self.child.kill(); // a dead or wedged server must not hang the run
        } else if !self.closed {
            let _ = self.call("close", Value::Null);
        }
        let _ = self.child.wait();
    }
}

/// WebView2's child processes can briefly retain profile handles after the
/// bruster process exits. Retry Windows sharing/access errors during cleanup.
pub fn remove_profile_dir(path: &std::path::Path) {
    let start = Instant::now();
    loop {
        match std::fs::remove_dir_all(path) {
            Ok(()) => return,
            Err(e) if e.kind() == std::io::ErrorKind::NotFound => return,
            Err(e)
                if cfg!(target_os = "windows")
                    && matches!(e.raw_os_error(), Some(5 | 32 | 33 | 145))
                    && start.elapsed() < Duration::from_secs(10) =>
            {
                std::thread::sleep(Duration::from_millis(100));
            }
            Err(e) => panic!("remove profile {}: {e}", path.display()),
        }
    }
}

// Tiny HTTP server on a random port. data: URLs are not usable: wry drops
// IPC messages whose page URL is not a valid http::Uri.
//
//   /        PAGE
//   /form    FORM
//   /other   OTHER
//   /cookie  OTHER + Set-Cookie: srv=1
//   /extra   EXTRA
//   /slow    OTHER after 300 ms
//   /texts   TEXTS
//   /frames  FRAMES
//   /more    MORE
//   /download  attachment
//   /slowbody  TEXTS, head first, body after 300 ms
//   /csp     MORE under a CSP without unsafe-eval
//   /tall    a 40000 px document
//   /lateframe  LATEFRAME
//   /slower  OTHER after 5 x SLOW_DELAY
//   /slowimg  SLOWIMG     /latefetch  LATEFETCH
//   /cachedpage  CACHEDPAGE, /cached.js counts hits, max-age 1h
/// Where bruster's stderr goes: /dev/null, or the test output with BRUSTER_TEST_STDERR=1.
pub fn test_stderr() -> Stdio {
    if std::env::var_os("BRUSTER_TEST_STDERR").is_some() {
        Stdio::inherit()
    } else {
        Stdio::null()
    }
}

pub fn serve() -> String {
    let listener = TcpListener::bind("127.0.0.1:0").unwrap();
    let base = format!("http://{}", listener.local_addr().unwrap());

    std::thread::spawn(move || {
        for stream in listener.incoming().flatten() {
            std::thread::spawn(move || handle(stream));
        }
    });

    base
}

fn send(stream: &mut std::net::TcpStream, status: &str, ctype: &str, extra: &str, body: &str) {
    let _ = write!(stream, "HTTP/1.1 {status}\r\nContent-Type: {ctype}\r\nContent-Length: {}\r\n{extra}Connection: close\r\n\r\n{body}", body.len());
}

/// 5000 links and inputs: 10000 snapshot elements.
pub fn big_page() -> String {
    let mut s = String::from("<html><head><title>big</title></head><body>");
    for i in 0..5000 {
        s.push_str(&format!(
            "<div><a href=\"/x{i}\">link {i}</a><input id=\"i{i}\"></div>"
        ));
    }
    s + "</body></html>"
}

fn handle(mut stream: std::net::TcpStream) {
    {
        {
            let mut buf = [0u8; 4096];
            let n = stream.read(&mut buf).unwrap_or(0);
            let head = String::from_utf8_lossy(&buf[..n]);
            let path = head.split_whitespace().nth(1).unwrap_or("/");
            let path = path.split('?').next().unwrap_or(path);

            let (status, extra, body) = match path {
                "/" => ("200 OK", "", PAGE),
                "/form" => ("200 OK", "", FORM),
                "/other" => ("200 OK", "", OTHER),
                "/cookie" => ("200 OK", "Set-Cookie: srv=1; Path=/\r\n", OTHER),
                "/cookie_persistent" => (
                    "200 OK",
                    "Set-Cookie: keep=1; Path=/; Max-Age=3600\r\n",
                    OTHER,
                ),
                "/extra" => ("200 OK", "", EXTRA),
                "/texts" | "/slowbody" => ("200 OK", "", TEXTS),
                "/frames" => ("200 OK", "", FRAMES),
                "/more" => ("200 OK", "", MORE),
                "/download" => (
                    "200 OK",
                    "Content-Disposition: attachment; filename=x.bin\r\n",
                    "bytes",
                ),
                "/csp" => (
                    "200 OK",
                    "Content-Security-Policy: script-src 'self' 'unsafe-inline'\r\n",
                    MORE,
                ),
                "/tall" => ("200 OK", "", TALL),
                "/beforeunload" => ("200 OK", "", BEFOREUNLOAD),
                "/xml" => return send(&mut stream, "200 OK", "application/xml", "", XML),
                "/json" => {
                    return send(&mut stream, "200 OK", "application/json", "", r#"{"a":1}"#)
                }
                "/redirect" => ("301 Moved Permanently", "Location: /other\r\n", ""),
                "/spa" | "/spa/about" => ("200 OK", "", SPA),
                "/shadowdeep" => ("200 OK", "", SHADOWDEEP),
                "/big" => return send(&mut stream, "200 OK", "text/html", "", &big_page()),
                // Accepts the request, never answers.
                "/hang" => {
                    std::thread::sleep(Duration::from_secs(600));
                    return;
                }
                "/lateframe" => ("200 OK", "", LATEFRAME),
                "/slowimg" => ("200 OK", "", SLOWIMG),
                "/latefetch" => ("200 OK", "", LATEFETCH),
                "/polling" => ("200 OK", "", POLLING),
                "/cachedpage" => ("200 OK", "", CACHEDPAGE),
                "/cached.js" => {
                    CACHED_HITS.fetch_add(1, std::sync::atomic::Ordering::SeqCst);
                    (
                        "200 OK",
                        "Cache-Control: max-age=3600\r\n",
                        "window.cached = 1;",
                    )
                }
                "/slower" => {
                    std::thread::sleep(SLOW_DELAY * 5);
                    ("200 OK", "", OTHER)
                }
                "/slow" => {
                    std::thread::sleep(SLOW_DELAY);
                    ("200 OK", "", OTHER)
                }
                _ => ("404 Not Found", "", ""),
            };
            let _ = write!(
                stream,
                "HTTP/1.1 {status}\r\nContent-Type: text/html\r\nContent-Length: {}\r\n{extra}Connection: close\r\n\r\n",
                body.len()
            );
            // The parser sees a head without a body for a while.
            let (first, rest) = if path == "/slowbody" {
                body.split_at(body.find("<body>").unwrap())
            } else {
                (body, "")
            };
            let _ = stream.write_all(first.as_bytes());
            let _ = stream.flush();
            if !rest.is_empty() {
                std::thread::sleep(SLOW_DELAY);
                let _ = stream.write_all(rest.as_bytes());
            }
        }
    }
}
