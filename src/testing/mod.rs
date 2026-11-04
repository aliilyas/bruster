//! User-facing `.bru` tests, executed through the existing JSON-lines API.
mod client;
mod parser;

use std::fs;
use std::path::{Component, Path, PathBuf};
use std::time::{Duration, Instant, SystemTime, UNIX_EPOCH};

use serde_json::{json, Value};
use url::Url;

use client::{Browser, Error};
use parser::{Assertion, Step, Suite, Test};

const HELP: &str = r#"Usage: bruster test FILE.bru [FILE.bru ...] [options]

Options:
  --base-url URL    Override each file's base_url (HTTP or HTTPS)
  --timeout MS      Override each file's step deadline (default 5000)
  --output DIR      Report parent directory (default bruster-results)
  --visible         Show browser windows (off-screen by default)
  --viewport WxH    Initial viewport (default 1280x800)
  --help, -h        Show this help

One command per line; double-quoted strings use JSON escapes. # starts a comment.
Files contain test "name" ... end blocks and an optional before_each ... end.
Top-level base_url "URL" and timeout MS apply to every test in that file.

Actions:
  navigate "URL or relative path"
  click "selector"                 hover "selector"
  fill "selector" "value"          type "selector" "text"
  press "key"                      press "selector" "key"
  select "selector" "value"        check "selector" / uncheck "selector"
  upload "selector" "file"         screenshot "filename.png"
  eval "JavaScript"                reload / back / forward

Assertions (retried until the step deadline):
  expect visible|hidden|attached "selector"
  expect text "selector" "exact text"
  expect contains "selector" "substring"
  expect title "exact title"       expect url "URL or relative path"
  expect url_contains "substring"  expect count "selector" NUMBER
  expect attr "selector" "name" "value"
  expect js "expression returning true"

Each test gets a fresh browser/profile. Failure stops that test; others continue.
Reports, stderr, and failure screenshots go in a unique run directory.
Exit codes: 0 = all passed, 1 = test/browser failure, 2 = invalid input/report I/O.
"#;

struct Options {
    files: Vec<PathBuf>,
    base_url: Option<Url>,
    timeout: Option<u64>,
    output: PathBuf,
    visible: bool,
    viewport: String,
}

impl Options {
    fn parse(args: &[String]) -> Result<Self, String> {
        let mut options = Self {
            files: Vec::new(),
            base_url: None,
            timeout: None,
            output: "bruster-results".into(),
            visible: false,
            viewport: "1280x800".into(),
        };
        let mut args = args.iter();
        while let Some(arg) = args.next() {
            match arg.as_str() {
                "--base-url" | "--timeout" | "--output" | "--viewport" => {
                    let value = args
                        .next()
                        .ok_or_else(|| format!("{arg} requires a value"))?;
                    match arg.as_str() {
                        "--base-url" => options.base_url = Some(http_url(value)?),
                        "--timeout" => options.timeout = Some(parser::timeout(value)?),
                        "--output" => options.output = value.into(),
                        _ => {
                            let (w, h) = crate::parse_viewport(value)
                                .ok_or("--viewport requires WIDTHxHEIGHT")?;
                            if w == 0
                                || h == 0
                                || w > crate::MAX_VIEWPORT_SIDE
                                || h > crate::MAX_VIEWPORT_SIDE
                            {
                                return Err(
                                    "viewport dimensions must be between 1 and 16000".into()
                                );
                            }
                            options.viewport = value.clone();
                        }
                    }
                }
                "--visible" => options.visible = true,
                "--" => {
                    options.files.extend(args.map(PathBuf::from));
                    break;
                }
                _ if arg.starts_with('-') => return Err(format!("unknown option: {arg}")),
                _ => options.files.push(arg.into()),
            }
        }
        if options.files.is_empty() {
            return Err("provide at least one .bru file; see bruster test --help".into());
        }
        Ok(options)
    }
}

fn http_url(value: &str) -> Result<Url, String> {
    let url = Url::parse(value).map_err(|e| format!("invalid URL {value:?}: {e}"))?;
    if !matches!(url.scheme(), "http" | "https") || url.host_str().is_none() {
        return Err(format!("expected an HTTP(S) URL, got {value:?}"));
    }
    Ok(url)
}

fn resolve_url(value: &str, base: Option<&Url>) -> Result<String, String> {
    let url = if let Some(base) = base {
        base.join(value)
            .map_err(|e| format!("invalid URL {value:?}: {e}"))?
    } else {
        http_url(value)?
    };
    Ok(http_url(url.as_str())?.into())
}

fn screenshot_path(value: &str) -> Result<&Path, String> {
    let path = Path::new(value);
    if value.is_empty() || !path.components().all(|c| matches!(c, Component::Normal(_))) {
        return Err(
            "screenshot path must be relative to the test's artifact directory, without . or .."
                .into(),
        );
    }
    // Keep paths portable even when the suite is validated on another OS.
    if value.contains(['\\', ':']) {
        return Err("screenshot paths use forward slashes and must be relative".into());
    }
    Ok(path)
}

fn prepare(suite: &mut Suite, path: &Path, options: &Options) -> Result<(), String> {
    let base = match &options.base_url {
        Some(base) => Some(base.clone()),
        None => suite
            .base_url
            .as_deref()
            .map(http_url)
            .transpose()
            .map_err(|e| format!("{}: base_url: {e}", path.display()))?,
    };
    for step in suite
        .before_each
        .iter_mut()
        .chain(suite.tests.iter_mut().flat_map(|t| &mut t.steps))
    {
        let result: Result<(), String> = (|| {
            if step.method == "navigate" {
                step.params["url"] = json!(resolve_url(
                    step.params["url"].as_str().unwrap(),
                    base.as_ref()
                )?);
            }
            if step.method == "url" {
                if let Some(Assertion::Equals(value)) = &mut step.assertion {
                    *value = json!(resolve_url(value.as_str().unwrap(), base.as_ref())?);
                }
            }
            if step.method == "upload" {
                let file = path
                    .parent()
                    .unwrap_or(Path::new("."))
                    .join(step.params["paths"][0].as_str().unwrap());
                step.params["paths"][0] = json!(file);
            }
            if step.method == "screenshot" {
                screenshot_path(step.params["path"].as_str().unwrap())?;
            }
            Ok(())
        })();
        result.map_err(|e| format!("{}:{line}: {e}", path.display(), line = step.line))?;
    }
    Ok(())
}

pub fn run(args: &[String]) -> i32 {
    if args.iter().any(|arg| arg == "--help" || arg == "-h") {
        print!("{HELP}");
        return 0;
    }
    match execute(args) {
        Ok(code) => code,
        Err(error) => {
            eprintln!("bruster test: {error}");
            2
        }
    }
}

fn execute(args: &[String]) -> Result<i32, String> {
    let options = Options::parse(args)?;
    // Parse and validate every file before starting browsers or creating reports.
    let mut suites = Vec::new();
    for path in &options.files {
        let source = fs::read_to_string(path).map_err(|e| format!("{}: {e}", path.display()))?;
        let mut suite = parser::parse(&source).map_err(|e| format!("{}:{e}", path.display()))?;
        prepare(&mut suite, path, &options)?;
        suites.push((path, suite));
    }
    // Re-exec the runner once under Xvfb, rather than one wrapper per test.
    crate::ensure_display(&std::env::args().skip(1).collect::<Vec<_>>());
    fs::create_dir_all(&options.output).map_err(|e| e.to_string())?;
    let root = fs::canonicalize(&options.output).map_err(|e| e.to_string())?;
    let stamp = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map_err(|e| e.to_string())?
        .as_nanos();
    let output = root.join(format!("{stamp}-{}", std::process::id()));
    fs::create_dir(&output).map_err(|e| e.to_string())?;
    println!("Artifacts: {}", output.display());
    let mut results = Vec::new();
    let mut failed = 0;
    for (path, suite) in &suites {
        let timeout = Duration::from_millis(options.timeout.or(suite.timeout).unwrap_or(5000));
        for test in &suite.tests {
            let directory = output.join(format!("test-{:03}", results.len() + 1));
            fs::create_dir(&directory).map_err(|e| e.to_string())?;
            let result = run_test(path, suite, test, &directory, &options, timeout);
            if result["status"] == "pass" {
                println!("PASS {} ({})", test.name, path.display());
            } else {
                failed += 1;
                println!(
                    "FAIL {} ({})\n  {}",
                    test.name,
                    path.display(),
                    result["error"].as_str().unwrap_or("unknown failure")
                );
                println!("  artifacts: {}", directory.display());
            }
            results.push(result);
        }
    }
    let passed = results.len() - failed;
    let report = json!({"schema_version": 1, "passed": passed, "failed": failed, "tests": results});
    fs::write(
        output.join("results.json"),
        serde_json::to_vec_pretty(&report).map_err(|e| e.to_string())?,
    )
    .map_err(|e| e.to_string())?;
    println!("\n{passed} passed, {failed} failed");
    Ok(if failed == 0 { 0 } else { 1 })
}

fn run_test(
    path: &Path,
    suite: &Suite,
    test: &Test,
    directory: &Path,
    options: &Options,
    timeout: Duration,
) -> Value {
    let started = Instant::now();
    let mut result = json!({"name": test.name, "file": path, "line": test.line,
        "status": "pass", "artifacts": directory, "steps": []});
    let mut error = None;
    match Browser::start(directory, options.visible, &options.viewport) {
        Err(e) => error = Some(format!("{}:{}: {e}", path.display(), test.line)),
        Ok(mut browser) => {
            for step in suite.before_each.iter().chain(&test.steps) {
                let began = Instant::now();
                let outcome = run_step(&mut browser, step, directory, timeout);
                result["steps"].as_array_mut().unwrap().push(json!({
                    "line": step.line, "command": step.source,
                    "status": if outcome.is_ok() { "pass" } else { "fail" },
                    "duration_ms": began.elapsed().as_millis() as u64,
                }));
                if let Err(e) = outcome {
                    error = Some(format!(
                        "{}:{}: {}\n  {e}",
                        path.display(),
                        step.line,
                        step.source
                    ));
                    result["evidence_errors"] = capture_failure(&mut browser, directory);
                    break;
                }
            }
            if let Err(e) = browser.finish() {
                error = Some(match error {
                    Some(original) => format!("{original}\n  shutdown: {e}"),
                    None => e,
                });
            }
        }
    }
    // The profile isolates tests; diagnostics, rather than browser caches, are retained.
    let _ = fs::remove_dir_all(directory.join("profile"));
    let _ = fs::remove_file(directory.join("profile.bruster-window.json"));
    if let Some(error) = error {
        result["status"] = json!("fail");
        result["error"] = json!(error);
    }
    result["duration_ms"] = json!(started.elapsed().as_millis() as u64);
    result
}

fn run_step(
    browser: &mut Browser,
    step: &Step,
    directory: &Path,
    timeout: Duration,
) -> Result<(), String> {
    let deadline = Instant::now() + timeout;
    let mut params = step.params.clone();
    if step.method == "screenshot" {
        let path = directory.join(screenshot_path(params["path"].as_str().unwrap())?);
        fs::create_dir_all(path.parent().unwrap()).map_err(|e| e.to_string())?;
        params["path"] = json!(path);
    }
    let Some(assertion) = &step.assertion else {
        return browser
            .call(step.method, params, deadline)
            .map(|_| ())
            .map_err(|e| e.to_string());
    };
    let mut last = "no result".to_owned();
    loop {
        match browser.call(step.method, params.clone(), deadline) {
            Ok(value) => {
                let matches = match assertion {
                    Assertion::Equals(expected) => value == *expected,
                    Assertion::Contains(text) => value.as_str().is_some_and(|v| v.contains(text)),
                };
                if matches {
                    return Ok(());
                }
                last = format!("observed {value}");
            }
            Err(Error::Command(error)) => last = format!("browser error: {error}"),
            Err(Error::Transport(error)) => return Err(format!("{error}; last {last}")),
        }
        let remaining = deadline.saturating_duration_since(Instant::now());
        if remaining.is_zero() {
            break;
        }
        std::thread::sleep(remaining.min(Duration::from_millis(50)));
        if Instant::now() >= deadline {
            break;
        }
    }
    Err(format!(
        "assertion timed out after {}ms; last {last}",
        timeout.as_millis()
    ))
}

fn capture_failure(browser: &mut Browser, directory: &Path) -> Value {
    let mut errors = Vec::new();
    for (method, filename, params) in [
        (
            "screenshot",
            "failure.png",
            json!({"path": directory.join("failure.png")}),
        ),
        ("snapshot", "snapshot.json", json!({"format": "json"})),
        ("console", "console.json", json!({})),
    ] {
        let outcome = browser
            .call(method, params, Instant::now() + Duration::from_secs(2))
            .map_err(|e| e.to_string())
            .and_then(|value| {
                if method == "screenshot" {
                    return Ok(());
                }
                fs::write(
                    directory.join(filename),
                    serde_json::to_vec_pretty(&value).map_err(|e| e.to_string())?,
                )
                .map_err(|e| e.to_string())
            });
        if let Err(error) = outcome {
            errors.push(format!("{method}: {error}"));
        }
    }
    json!(errors)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn relative_urls_follow_url_semantics() {
        let base = http_url("https://example.com/app/").unwrap();
        assert_eq!(
            resolve_url("../login?next=%2F#form", Some(&base)).unwrap(),
            "https://example.com/login?next=%2F#form"
        );
        assert_eq!(
            resolve_url("/login", Some(&base)).unwrap(),
            "https://example.com/login"
        );
        assert!(resolve_url("/login", None).is_err());
        assert!(resolve_url("file:///tmp/test.html", Some(&base)).is_err());
        assert!(http_url("data:text/html,hi").is_err());
    }

    #[test]
    fn artifact_paths_are_relative_and_portable() {
        for path in [
            "",
            "../escape.png",
            "/tmp/a.png",
            "nested/../escape.png",
            "C:\\out.png",
            "..\\escape.png",
        ] {
            assert!(screenshot_path(path).is_err(), "{path}");
        }
        assert!(screenshot_path("screens/日本.png").is_ok());
    }
}
