//! Sequential native-protocol client with deadlines and owned browser processes.
use std::fmt;
use std::fs::File;
use std::io::{BufRead, BufReader, Write};
use std::path::Path;
use std::process::{Child, ChildStdin, Command, Stdio};
use std::sync::mpsc::{self, Receiver};
use std::time::{Duration, Instant};

use serde_json::{json, Value};

#[derive(Debug)]
pub enum Error {
    Command(String),
    Transport(String),
}

impl fmt::Display for Error {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::Command(message) | Self::Transport(message) => f.write_str(message),
        }
    }
}

pub struct Browser {
    child: Child,
    stdin: Option<ChildStdin>,
    messages: Receiver<Result<Value, String>>,
    id: u64,
    finished: bool,
}

impl Browser {
    pub fn start(directory: &Path, visible: bool, viewport: &str) -> Result<Self, String> {
        let stderr = File::create(directory.join("stderr.log")).map_err(|e| e.to_string())?;
        let mut command = Command::new(std::env::current_exe().map_err(|e| e.to_string())?);
        command
            .arg(if visible { "--visible" } else { "--hidden" })
            .arg("--viewport")
            .arg(viewport)
            .arg("--profile")
            .arg(directory.join("profile"))
            .stdin(Stdio::piped())
            .stdout(Stdio::piped())
            .stderr(stderr);
        #[cfg(unix)]
        {
            use std::os::unix::process::CommandExt;
            command.process_group(0);
        }
        let mut child = command
            .spawn()
            .map_err(|e| format!("starting browser: {e}"))?;
        let stdin = child.stdin.take();
        let stdout = child.stdout.take().expect("piped stdout");
        let (send, messages) = mpsc::sync_channel(64);
        std::thread::spawn(move || {
            for line in BufReader::new(stdout).lines() {
                let message = line.map_err(|e| e.to_string()).and_then(|line| {
                    serde_json::from_str::<Value>(&line)
                        .map_err(|e| format!("invalid browser reply: {e}"))
                });
                let invalid = message.is_err();
                if send.send(message).is_err() || invalid {
                    return;
                }
            }
            let _ = send.send(Err("browser closed stdout".into()));
        });
        let browser = Self {
            child,
            stdin,
            messages,
            id: 0,
            finished: false,
        };
        browser
            .receive(Instant::now() + Duration::from_secs(30), |v| {
                v["event"] == "ready"
            })
            .map_err(|e| format!("browser startup: {e}; see stderr.log"))?;
        Ok(browser)
    }

    fn receive(&self, deadline: Instant, matches: impl Fn(&Value) -> bool) -> Result<Value, Error> {
        loop {
            let remaining = deadline
                .checked_duration_since(Instant::now())
                .ok_or_else(|| Error::Transport("browser response deadline exceeded".into()))?;
            let value = self
                .messages
                .recv_timeout(remaining)
                .map_err(|e| Error::Transport(format!("waiting for browser: {e}")))?
                .map_err(Error::Transport)?;
            if matches(&value) {
                return Ok(value);
            }
            // Events and late replies must not reset the absolute deadline.
        }
    }

    pub fn call(
        &mut self,
        method: &str,
        mut params: Value,
        deadline: Instant,
    ) -> Result<Value, Error> {
        let remaining = deadline
            .checked_duration_since(Instant::now())
            .ok_or_else(|| Error::Transport("browser request deadline exceeded".into()))?
            .as_millis()
            .max(1) as u64;
        params["timeout"] = json!(remaining);
        params["request_timeout"] = json!(remaining);
        self.id += 1;
        let request = json!({"id": self.id, "method": method, "params": params});
        let stdin = self
            .stdin
            .as_mut()
            .ok_or_else(|| Error::Transport("browser is closed".into()))?;
        writeln!(stdin, "{request}")
            .and_then(|_| stdin.flush())
            .map_err(|e| Error::Transport(format!("sending {method}: {e}")))?;
        let reply = self.receive(deadline, |v| v["id"].as_u64() == Some(self.id))?;
        if let Some(error) = reply.get("error") {
            return Err(Error::Command(
                error
                    .as_str()
                    .map(str::to_owned)
                    .unwrap_or_else(|| error.to_string()),
            ));
        }
        reply
            .get("result")
            .cloned()
            .ok_or_else(|| Error::Transport("reply has neither result nor error".into()))
    }

    pub fn finish(&mut self) -> Result<(), String> {
        // EOF goes through Bruster's normal shutdown path, including cache flush.
        self.stdin.take();
        let deadline = Instant::now() + Duration::from_secs(5);
        loop {
            match self.child.try_wait().map_err(|e| e.to_string())? {
                Some(status) => {
                    if !status.success() {
                        self.kill();
                        return Err(format!("browser exited with {status}; see stderr.log"));
                    }
                    self.finished = true;
                    return Ok(());
                }
                None if Instant::now() >= deadline => {
                    self.kill();
                    return Err("browser did not shut down within 5 seconds".into());
                }
                None => std::thread::sleep(Duration::from_millis(20)),
            }
        }
    }

    fn kill(&mut self) {
        #[cfg(unix)]
        unsafe {
            // The child owns a fresh process group, including native helpers.
            libc::kill(-(self.child.id() as i32), libc::SIGKILL);
        }
        #[cfg(windows)]
        {
            let _ = Command::new("taskkill")
                .args(["/PID", &self.child.id().to_string(), "/T", "/F"])
                .stdout(Stdio::null())
                .stderr(Stdio::null())
                .status();
        }
        let _ = self.child.kill();
        let _ = self.child.wait();
        self.finished = true;
    }
}

impl Drop for Browser {
    fn drop(&mut self) {
        if !self.finished {
            self.kill();
        }
    }
}
