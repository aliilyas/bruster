//! Run the website's executable fixtures against Cargo's freshly built Bruster.
//! Python 3.10+ is required; local tests need no npm install or internet access.
//! Linux needs a display, like smoke.rs (`xvfb-run -a cargo test ...`).

use std::collections::BTreeSet;
use std::fs::{self, File};
use std::path::{Path, PathBuf};
use std::process::{Command, Stdio};
use std::sync::Mutex;
use std::time::{SystemTime, UNIX_EPOCH};

use serde_json::Value;

// Each fixture already launches an isolated browser. Keep groups sequential so
// `cargo test`'s worker count does not multiply native engine resource usage.
static LAB: Mutex<()> = Mutex::new(());

enum Selection<'a> {
    Cases(&'a [&'a str]),
    FullCore,
    Published(&'a [&'a str]),
}

fn configured_path(root: &Path, name: &str, default: &str) -> PathBuf {
    root.join(std::env::var_os(name).unwrap_or_else(|| default.into()))
}

fn read_json(path: &Path) -> Value {
    let bytes = fs::read(path).unwrap_or_else(|error| {
        panic!("Cannot read test-lab evidence {}: {error}", path.display())
    });
    serde_json::from_slice(&bytes)
        .unwrap_or_else(|error| panic!("Invalid test-lab JSON {}: {error}", path.display()))
}

fn run_lab(name: &str, selection: Selection<'_>) {
    let _serial = LAB.lock().unwrap_or_else(|poisoned| poisoned.into_inner());
    let root = Path::new(env!("CARGO_MANIFEST_DIR"));
    let output_root = configured_path(
        root,
        "BRUSTER_TEST_LAB_OUTPUT",
        "target/test-lab-results/cargo",
    );
    let stamp = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap()
        .as_nanos();
    let output = output_root.join(format!("{name}-{}-{stamp}", std::process::id()));
    fs::create_dir_all(&output).expect("create test-lab evidence directory");
    let site = output.join("site");
    let binary = std::env::var_os("BRUSTER_TEST_LAB_BINARY")
        .unwrap_or_else(|| env!("CARGO_BIN_EXE_bruster").into());
    let python = std::env::var_os("BRUSTER_TEST_PYTHON")
        .unwrap_or_else(|| if cfg!(windows) { "python" } else { "python3" }.into());
    let mut command = Command::new(&python);
    command
        .current_dir(root)
        .env("PYTHONUTF8", "1")
        .arg(root.join("scripts/test_lab.py"))
        .arg("run")
        .arg("--binary")
        .arg(binary)
        .args(["--transport", "both", "--suite", "core"])
        .arg("--site-dir")
        .arg(&site)
        .arg("--output")
        .arg(&output);

    let explicit_cases = match &selection {
        Selection::Cases(ids) | Selection::Published(ids) => Some(*ids),
        Selection::FullCore => None,
    };
    if let Some(ids) = explicit_cases {
        for id in ids {
            command.args(["--case", id]);
        }
    }
    if matches!(selection, Selection::Published(_)) {
        let url = std::env::var("BRUSTER_TEST_LAB_URL")
            .unwrap_or_else(|_| "https://aliilyas.github.io/bruster/test-lab/".into());
        command.args(["--url", &url]);
    } else if matches!(selection, Selection::FullCore) {
        let frameworks = configured_path(
            root,
            "BRUSTER_TEST_LAB_FRAMEWORKS",
            "target/test-lab-frameworks",
        );
        assert!(
            ["react.js", "vue.js", "svelte.js"]
                .iter()
                .all(|name| frameworks.join(name).is_file()),
            "Full test-lab coverage needs the pinned framework bundles. Run npm ci --prefix \
             tests/site/frameworks --ignore-scripts --no-audit --no-fund, then node \
             tests/site/frameworks/build.mjs target/test-lab-frameworks. \
             BRUSTER_TEST_LAB_FRAMEWORKS overrides the bundle directory."
        );
        command.arg("--frameworks").arg(frameworks);
    }

    let log_path = output.join("runner.log");
    let log = File::create(&log_path).unwrap();
    let status = command
        .stdin(Stdio::null())
        .stdout(log.try_clone().unwrap())
        .stderr(log)
        .status()
        .unwrap_or_else(|error| {
            panic!("Cannot launch {python:?}: {error}. Install Python 3.10+ or set BRUSTER_TEST_PYTHON.")
        });
    let log = fs::read_to_string(&log_path).unwrap_or_default();
    if !status.success() {
        // Early failures can be hundreds of lines away from the end of a full
        // run. Surface each failure while preserving the entire runner log.
        let mut details: Vec<_> = log
            .lines()
            .filter(|line| line.starts_with("FAIL ") || line.starts_with("ERROR "))
            .collect();
        if details.is_empty() {
            details = log.lines().rev().take(40).collect();
            details.reverse();
        }
        panic!(
            "Test lab {name} failed ({status}). Evidence: {}\n{}",
            output.display(),
            details.join("\n")
        );
    }

    // A successful process is insufficient: every requested case must appear
    // exactly once in each transport, and focused regression tests cannot skip.
    let report = read_json(&output.join("results.json"));
    assert_eq!(report["schemaVersion"], 1, "{}", output.display());
    assert!(
        report["finishedUtc"].is_string(),
        "incomplete test-lab report: {}",
        output.display()
    );
    let ids: Vec<String> = match explicit_cases {
        Some(ids) => ids.iter().map(|id| (*id).to_owned()).collect(),
        None => {
            let manifest = read_json(&site.join("manifest.json"));
            manifest["cases"]
                .as_array()
                .unwrap()
                .iter()
                .filter(|case| case["tier"] == "core")
                .map(|case| case["id"].as_str().unwrap().to_owned())
                .collect()
        }
    };
    let expected: BTreeSet<_> = ids
        .iter()
        .flat_map(|id| [format!("native/{id}"), format!("mcp/{id}")])
        .collect();
    assert!(!expected.is_empty(), "test-lab selection is empty");
    let mut observed = BTreeSet::new();
    for row in report["results"].as_array().unwrap() {
        let key = format!(
            "{}/{}",
            row["transport"].as_str().unwrap(),
            row["id"].as_str().unwrap()
        );
        assert!(observed.insert(key.clone()), "duplicate observation {key}");
        let status = row["status"].as_str().unwrap();
        if explicit_cases.is_some() {
            assert_eq!(
                status,
                "pass",
                "{key}: {}. Evidence: {}",
                row,
                output.display()
            );
        } else {
            assert!(
                matches!(status, "pass" | "probe-pass" | "probe-fail" | "skip"),
                "{key}: {row}"
            );
            if status == "skip" {
                assert!(
                    row["reason"]
                        .as_str()
                        .is_some_and(|reason| !reason.is_empty()),
                    "{key}: skip needs a reason"
                );
            }
        }
    }
    assert_eq!(
        observed,
        expected,
        "missing or unexpected lab observations; see {}",
        output.display()
    );
    println!(
        "Test lab {name}: {} observations; {}",
        observed.len(),
        output.join("index.html").display()
    );
}

macro_rules! lab_cases {
    ($name:ident, $($id:literal),+ $(,)?) => {
        #[test]
        fn $name() {
            run_lab(stringify!($name), Selection::Cases(&[$($id),+]));
        }
    };
}

lab_cases!(
    references_and_snapshots,
    "ref-duplicate",
    "ref-clone",
    "ref-find-refresh",
    "snapshot-label-for",
    "snapshot-unicode"
);
lab_cases!(
    form_state_and_atomic_failures,
    "input-number-1",
    "type-emoji",
    "fill-disabled-fieldset",
    "form-enter",
    "select-invalid-multi",
    "checkbox-idempotent"
);
lab_cases!(
    css_actionability_and_events,
    "layout-grid",
    "hit-display-none",
    "hit-overlay",
    "hit-coordinate",
    "event-propagation",
    "key-cancelled-press"
);
lab_cases!(
    shadow_frames_and_uploads,
    "shadow-open",
    "shadow-slots",
    "frame-same-origin",
    "upload-binary"
);
lab_cases!(
    javascript_waits_and_deadlines,
    "async-microtask",
    "wait-insert-visible",
    "wait-timeout",
    "request-late-reply",
    "request-zero"
);
lab_cases!(
    navigation_and_tabs,
    "navigation-history-state",
    "navigation-redirect",
    "navigation-dom",
    "tab-close-pending"
);
lab_cases!(
    http_and_storage,
    "fetch-headers",
    "network-idle-gate",
    "network-cors-denied",
    "cookie-server",
    "storage-port-origin"
);
lab_cases!(
    rendering_and_application_workflows,
    "screenshot-quadrants",
    "screenshot-canvas-update",
    "workflow-decoy-login",
    "workflow-modal-cancel"
);

#[test]
#[ignore = "complete core suite; build pinned framework bundles first (see tests/site/README.md)"]
fn full_test_lab() {
    run_lab("full_test_lab", Selection::FullCore);
}

#[test]
#[ignore = "uses the published GitHub Pages site and requires internet access"]
fn published_test_lab() {
    run_lab(
        "published_test_lab",
        Selection::Published(&[
            "ref-duplicate",
            "ref-clone",
            "snapshot-unicode",
            "input-number-1",
            "select-invalid-multi",
            "hit-overlay",
            "shadow-open",
            "frame-same-origin",
            "screenshot-quadrants",
            "workflow-decoy-login",
            "framework-react",
            "framework-vue",
            "framework-svelte",
        ]),
    );
}
