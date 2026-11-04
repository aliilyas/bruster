//! Exercise the public test CLI, including real assertions and failure evidence.
mod common;

use std::fs;
use std::path::PathBuf;
use std::process::{Command, ExitStatus, Stdio};
use std::time::{Duration, Instant, SystemTime, UNIX_EPOCH};

use serde_json::Value;

struct Fixture(PathBuf);

impl Fixture {
    fn new(source: &str) -> Self {
        let stamp = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap()
            .as_nanos();
        let path = std::env::temp_dir().join(format!("bruster-dsl-{}-{stamp}", std::process::id()));
        fs::create_dir(&path).unwrap();
        fs::write(path.join("suite.bru"), source).unwrap();
        Self(path)
    }

    fn command(&self) -> Command {
        let mut command = Command::new(env!("CARGO_BIN_EXE_bruster"));
        command
            .arg("test")
            .arg(self.0.join("suite.bru"))
            .arg("--output")
            .arg(self.0.join("results"))
            .stdin(Stdio::null())
            .stdout(fs::File::create(self.0.join("stdout.log")).unwrap())
            .stderr(fs::File::create(self.0.join("stderr.log")).unwrap());
        command
    }

    fn run(&self, command: &mut Command) -> ExitStatus {
        let mut child = command.spawn().unwrap();
        let start = Instant::now();
        loop {
            if let Some(status) = child.try_wait().unwrap() {
                return status;
            }
            if start.elapsed() > Duration::from_secs(90) {
                let _ = child.kill();
                let _ = child.wait();
                panic!("DSL runner hung; evidence: {}", self.0.display());
            }
            std::thread::sleep(Duration::from_millis(50));
        }
    }

    fn report(&self) -> Value {
        let runs: Vec<_> = fs::read_dir(self.0.join("results"))
            .unwrap()
            .map(|e| e.unwrap().path())
            .collect();
        assert_eq!(runs.len(), 1);
        serde_json::from_slice(&fs::read(runs[0].join("results.json")).unwrap()).unwrap()
    }
}

impl Drop for Fixture {
    fn drop(&mut self) {
        if !std::thread::panicking() {
            common::remove_profile_dir(&self.0);
        }
    }
}

#[test]
fn runs_real_flows_retries_observations_and_isolates_tests() {
    let fixture = Fixture::new(
        r##"base_url "https://override-me.invalid/"
timeout 15000
before_each
  navigate "/"
end

test "greeting and delayed content"
  expect title "smoke"
  expect visible "#name"
  fill "#name" "日本 # Ada"
  click "#go"
  expect text "#out" "hi 日本 # Ada"
  expect contains "#out" "Ada"
  eval "localStorage.setItem('dsl-isolation', 'dirty')"
  eval "void fetch('/slow').then(() => { const p = document.createElement('p'); p.id = 'delayed'; p.textContent = 'ready'; document.body.append(p); })"
  expect text "#delayed" "ready"
  expect count "#delayed" 1
  screenshot "screens/greeting.png"
end

test "fresh browser and form state"
  expect js "localStorage.getItem('dsl-isolation') === null"
  expect text "#out" ""
  navigate "/form"
  fill "#q" "a quoted \"value\""
  press "#q" "Enter"
  expect text "#out" "submitted:a quoted \"value\""
  check "#c"
  expect js "document.querySelector('#c').checked === true"
  uncheck "#c"
  select "#s" "b"
  expect js "!document.querySelector('#c').checked && document.querySelector('#s').value === 'b'"
  expect attr "#q" "data-k" "v"
  expect url "/form"
  expect url_contains "/form"
  expect hidden "#missing"
  expect attached "#q"
end

test "upload relative to the suite"
  navigate "/extra"
  upload "#up" "sample.txt"
  expect text "#out" "files:sample.txt:6:text/plain"
end
"##,
    );
    fs::write(fixture.0.join("sample.txt"), "hello\n").unwrap();
    let status = fixture.run(fixture.command().arg("--base-url").arg(common::serve()));
    let report = fixture.report();
    assert!(status.success(), "{report:#}");
    assert_eq!(report["passed"], 3);
    assert_eq!(report["failed"], 0);
    let artifacts = PathBuf::from(report["tests"][0]["artifacts"].as_str().unwrap());
    let image = fs::read(artifacts.join("screens/greeting.png")).unwrap();
    assert_eq!(&image[..8], b"\x89PNG\r\n\x1a\n");
    assert!(!artifacts.join("failure.png").exists());
}

#[test]
fn failures_report_actual_state_capture_evidence_and_continue() {
    let fixture = Fixture::new(
        r##"before_each
  navigate "/"
end
test "wrong text"
  fill "#name" "Ada"
  click "#go"
  expect text "#out" "wrong"
  eval "document.title = 'must not execute'"
end
test "unresolved promise"
  eval "new Promise(() => {})"
end
test "continues after failures"
  expect title "smoke"
end
"##,
    );
    let status = fixture.run(fixture.command().arg("--base-url").arg(common::serve()));
    assert_eq!(status.code(), Some(1));
    let report = fixture.report();
    assert_eq!(report["passed"], 1, "{report:#}");
    assert_eq!(report["failed"], 2, "{report:#}");
    let failed = &report["tests"][0];
    let error = failed["error"].as_str().unwrap();
    assert!(error.contains("suite.bru:7:"), "{error}");
    assert!(error.contains("hi Ada"), "{error}");
    assert_eq!(failed["steps"].as_array().unwrap().len(), 4);
    let artifacts = PathBuf::from(failed["artifacts"].as_str().unwrap());
    assert_eq!(
        &fs::read(artifacts.join("failure.png")).unwrap()[..8],
        b"\x89PNG\r\n\x1a\n"
    );
    let snapshot: Value =
        serde_json::from_slice(&fs::read(artifacts.join("snapshot.json")).unwrap()).unwrap();
    assert_eq!(snapshot["title"], "smoke");
    assert!(snapshot.to_string().contains("hi Ada"));
    assert!(artifacts.join("console.json").is_file());
    assert_eq!(report["tests"][2]["status"], "pass");
}

#[test]
fn validates_all_files_and_help_without_starting_a_browser() {
    let fixture = Fixture::new("test \"valid\"\n navigate \"https://example.com\"\nend\n");
    fs::write(
        fixture.0.join("bad.bru"),
        "test \"invalid\"\n clik \"#go\"\nend\n",
    )
    .unwrap();
    let mut command = fixture.command();
    command
        .arg(fixture.0.join("bad.bru"))
        .env_remove("DISPLAY")
        .env_remove("WAYLAND_DISPLAY")
        .env("BRUSTER_NO_XVFB", "1");
    assert_eq!(fixture.run(&mut command).code(), Some(2));
    let stderr = fs::read_to_string(fixture.0.join("stderr.log")).unwrap();
    assert!(stderr.contains("bad.bru:2: unknown command"), "{stderr}");
    assert!(!fixture.0.join("results").exists());

    let mut command = fixture.command();
    command
        .arg("--help")
        .env_remove("DISPLAY")
        .env_remove("WAYLAND_DISPLAY")
        .env("BRUSTER_NO_XVFB", "1");
    assert!(fixture.run(&mut command).success());
    assert!(fs::read_to_string(fixture.0.join("stdout.log"))
        .unwrap()
        .contains("Usage: bruster test"));
    assert!(!fixture.0.join("results").exists());
}
