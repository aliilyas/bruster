//! Requested window mode, separate from WebView cookies and caches.
use std::path::{Path, PathBuf};

use serde::{Deserialize, Serialize};
use tao::window::Window;

#[derive(Clone, Copy, Debug, Default, Deserialize, Serialize, PartialEq)]
#[serde(rename_all = "lowercase")]
pub enum State {
    #[default]
    Normal,
    Maximized,
    Minimized,
}

impl State {
    pub fn command(method: &str) -> Option<Self> {
        match method {
            "maximize" => Some(Self::Maximized),
            "minimize" => Some(Self::Minimized),
            _ => None,
        }
    }

    pub fn apply(self, window: &Window) {
        // Hide rather than iconify: there should be no native window on screen.
        window.set_minimized(false);
        window.set_visible(self != Self::Minimized);
        window.set_maximized(self == Self::Maximized);
    }
}

pub struct Store {
    path: Option<PathBuf>,
    pub state: State,
    pub dark: bool,
}

#[derive(Default, Deserialize, Serialize)]
#[serde(default)]
struct Preferences {
    state: State,
    dark: bool,
}

#[derive(Deserialize)]
#[serde(untagged)]
enum Saved {
    Preferences(Preferences),
    Legacy(State),
}

fn state_root() -> Option<PathBuf> {
    #[cfg(target_os = "windows")]
    {
        std::env::var_os("LOCALAPPDATA").map(PathBuf::from)
    }
    #[cfg(target_os = "macos")]
    {
        std::env::var_os("HOME").map(|h| PathBuf::from(h).join("Library/Application Support"))
    }
    #[cfg(not(any(target_os = "windows", target_os = "macos")))]
    {
        std::env::var_os("XDG_STATE_HOME")
            .filter(|p| Path::new(p).is_absolute())
            .map(PathBuf::from)
            .or_else(|| std::env::var_os("HOME").map(|h| PathBuf::from(h).join(".local/state")))
    }
}

impl Store {
    pub fn load(profile: Option<&Path>) -> Self {
        // Profile metadata is namespaced alongside (not inside) WebView data.
        let path = profile
            .map(|p| {
                // Normalize trailing separators, relative aliases and symlinks so
                // a profile always selects the same sibling metadata file.
                let _ = std::fs::create_dir_all(p);
                let profile = std::fs::canonicalize(p).unwrap_or_else(|_| p.to_path_buf());
                let mut name = profile.as_os_str().to_os_string();
                name.push(".bruster-window.json");
                PathBuf::from(name)
            })
            .or_else(|| state_root().map(|p| p.join("bruster/window.json")));
        Self::from_path(path)
    }

    fn from_path(path: Option<PathBuf>) -> Self {
        let saved = path
            .as_ref()
            .and_then(|p| std::fs::read(p).ok())
            .and_then(|b| serde_json::from_slice::<Saved>(&b).ok());
        let prefs = match saved {
            Some(Saved::Preferences(prefs)) => prefs,
            Some(Saved::Legacy(state)) => Preferences { state, dark: false },
            None => Preferences::default(),
        };
        Self {
            path,
            state: prefs.state,
            dark: prefs.dark,
        }
    }

    pub fn save(&mut self, state: State) -> std::io::Result<()> {
        self.save_preferences(state, self.dark)
    }

    pub fn save_dark(&mut self, dark: bool) -> std::io::Result<()> {
        self.save_preferences(self.state, dark)
    }

    fn save_preferences(&mut self, state: State, dark: bool) -> std::io::Result<()> {
        let path = self
            .path
            .as_ref()
            .ok_or_else(|| std::io::Error::other("no persistent state directory available"))?;
        if let Some(parent) = path.parent() {
            std::fs::create_dir_all(parent)?;
        }
        let temp = path.with_extension(format!("{}.tmp", std::process::id()));
        std::fs::write(&temp, serde_json::to_vec(&Preferences { state, dark })?)?;
        std::fs::rename(temp, path)?;
        self.state = state;
        self.dark = dark;
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn commands_and_persistence() {
        let path =
            std::env::temp_dir().join(format!("bruster-state-test-{}.json", std::process::id()));
        let mut store = Store::from_path(Some(path.clone()));
        for (command, state) in [
            ("maximize", State::Maximized),
            ("minimize", State::Minimized),
        ] {
            assert_eq!(State::command(command), Some(state));
            store.save(state).unwrap();
            assert_eq!(Store::from_path(Some(path.clone())).state, state);
        }
        assert_eq!(State::command("close"), None);
        store.save_dark(true).unwrap();
        assert!(Store::from_path(Some(path.clone())).dark);
        store.save(State::Maximized).unwrap();
        assert!(Store::from_path(Some(path.clone())).dark);
        store.save_dark(false).unwrap();
        assert!(!Store::from_path(Some(path.clone())).dark);
        assert_eq!(Store::from_path(Some(path.clone())).state, State::Maximized);
        std::fs::write(&path, "\"minimized\"").unwrap();
        let legacy = Store::from_path(Some(path.clone()));
        assert_eq!(legacy.state, State::Minimized);
        assert!(!legacy.dark);
        std::fs::write(&path, "invalid").unwrap();
        assert_eq!(Store::from_path(Some(path.clone())).state, State::Normal);
        std::fs::remove_file(path).unwrap();
    }

    #[test]
    fn profiles_have_independent_metadata_outside_webview_data() {
        let root =
            std::env::temp_dir().join(format!("bruster-profile-state-test-{}", std::process::id()));
        let first = root.join("first");
        let second = root.join("second");
        Store::load(Some(&first)).save(State::Minimized).unwrap();
        Store::load(Some(&second)).save(State::Maximized).unwrap();
        assert_eq!(Store::load(Some(&first.join("."))).state, State::Minimized);
        assert_eq!(Store::load(Some(&second)).state, State::Maximized);
        assert_eq!(std::fs::read_dir(&first).unwrap().count(), 0);
        std::fs::remove_dir_all(root).unwrap();
    }
}
