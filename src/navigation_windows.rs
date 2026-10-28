//! WebView2 can start a replacement before completing the retiring load.
//! Wry's load callbacks omit NavigationId, so observe the native events here.
//! Wait for each API call's start before submitting a replacement: otherwise
//! an older queued start can be mistaken for the newest command, even with IDs.

use webview2_com::{
    take_pwstr, ContentLoadingEventHandler, NavigationCompletedEventHandler,
    NavigationStartingEventHandler, SourceChangedEventHandler,
};
use windows::core::{BOOL, PWSTR};
use wry::WebViewExtWindows;

use crate::{
    emit, fail, json, page_load, trace_navigation, EventLoopProxy, PageLoadEvent, Pending, Shared,
    TabId, UserEvent,
};

pub struct Navigation {
    generation: u64,
    method: String,
    url: Option<String>,
}

impl Navigation {
    fn start(self, wv: &wry::WebView, pending: &Shared) -> wry::Result<()> {
        pending.borrow_mut().native_start = Some(self.generation);
        let result = match self.method.as_str() {
            "navigate" => wv.load_url(self.url.as_deref().unwrap()),
            "reload" => wv.reload(),
            "back" => wv.go_back(),
            "forward" => wv.go_forward(),
            _ => unreachable!("not a native navigation"),
        };
        if result.is_err() {
            pending.borrow_mut().native_start = None;
        }
        result
    }
}

pub fn navigate(
    wv: &wry::WebView,
    pending: &Shared,
    method: &str,
    url: Option<&str>,
) -> wry::Result<()> {
    let mut p = pending.borrow_mut();
    let next = Navigation {
        generation: p.generation,
        method: method.into(),
        url: url.map(str::to_owned),
    };
    if p.native_start.is_some() {
        // Supersession already answered the previous waiter. Only the latest
        // command needs a native call after the outstanding start is observed.
        p.native_next = Some(next);
        return Ok(());
    }
    p.native_next = None;
    drop(p);
    next.start(wv, pending)
}

pub fn resume(wv: &wry::WebView, tab: TabId, pending: &Shared, proxy: &EventLoopProxy<UserEvent>) {
    let next = pending.borrow_mut().windows_next();
    if let Some(next) = next {
        if let Err(error) = next.start(wv, pending) {
            let mut p = pending.borrow_mut();
            if let Some((id, _)) = p.navigate.take() {
                fail(id, error);
            }
            p.awaiting_start = false;
            let _ = proxy.send_event(p.flush_event(tab));
        }
    }
}

impl Pending {
    fn windows_next(&mut self) -> Option<Navigation> {
        if self.native_start.is_some() {
            return None;
        }
        self.native_next
            .take()
            .filter(|next| next.generation == self.generation && self.awaiting_start)
    }

    /// Returns false when a superseded/timed-out native call must be cancelled.
    fn windows_start(&mut self, id: u64, url: &str, redirected: bool) -> bool {
        if redirected || self.native_id == Some(id) {
            // Redirects retain their NavigationId, including a late redirect
            // from a retiring load after its replacement has started.
            return self.windows_current(id);
        }
        self.native_id = Some(id);
        let explicit = self.native_start.take();
        if self.warming && url == "about:blank" {
            return true;
        }
        // The real load can start before about:blank's completion. Its later
        // completion must neither clear this load nor consume its waiter.
        self.warming = false;
        if let Some(generation) = explicit {
            self.native_generation = generation;
            if generation != self.generation || !self.awaiting_start {
                return false;
            }
        }
        self.provisional_start();
        true
    }

    fn windows_current(&self, id: u64) -> bool {
        self.native_id == Some(id)
            && (self.warming || (!self.awaiting_start && self.native_generation == self.generation))
    }
}

pub fn observe(
    wv: &wry::WebView,
    tab: TabId,
    pending: Shared,
    proxy: EventLoopProxy<UserEvent>,
) -> wry::Result<()> {
    let webview = wv.webview();
    let mut token = 0;
    let start_pending = pending.clone();
    let start_proxy = proxy.clone();
    unsafe {
        webview.add_NavigationStarting(
            &NavigationStartingEventHandler::create(Box::new(move |_, args| {
                if let Some(args) = args {
                    let mut id = 0;
                    let mut url = PWSTR::null();
                    let mut redirected = BOOL::default();
                    args.NavigationId(&mut id)?;
                    args.Uri(&mut url)?;
                    args.IsRedirected(&mut redirected)?;
                    let url = take_pwstr(url);
                    let mut p = start_pending.borrow_mut();
                    if !p.windows_start(id, &url, redirected.as_bool()) {
                        args.SetCancel(true)?;
                    }
                    trace_navigation("provisional start", tab, &p, &url);
                    let _ = start_proxy.send_event(UserEvent::StartNavigation(tab));
                }
                Ok(())
            })),
            &mut token,
        )
    }?;

    // Same-document history/fragment changes have no NavigationStarting.
    // Release their API-call slot here, before the next queued navigation.
    let source_pending = pending.clone();
    let source_proxy = proxy.clone();
    unsafe {
        webview.add_SourceChanged(
            &SourceChangedEventHandler::create(Box::new(move |_, args| {
                if let Some(args) = args {
                    let mut new_document = BOOL::default();
                    args.IsNewDocument(&mut new_document)?;
                    if !new_document.as_bool() {
                        source_pending.borrow_mut().native_start = None;
                        let _ = source_proxy.send_event(UserEvent::StartNavigation(tab));
                    }
                }
                Ok(())
            })),
            &mut token,
        )?;
    }

    let commit_pending = pending.clone();
    let commit_proxy = proxy.clone();
    unsafe {
        webview.add_ContentLoading(
            &ContentLoadingEventHandler::create(Box::new(move |view, args| {
                if let (Some(view), Some(args)) = (view, args) {
                    let mut id = 0;
                    args.NavigationId(&mut id)?;
                    let mut p = commit_pending.borrow_mut();
                    if p.windows_current(id) {
                        let mut url = PWSTR::null();
                        view.Source(&mut url)?;
                        page_load(
                            &mut p,
                            PageLoadEvent::Started,
                            tab,
                            &take_pwstr(url),
                            &commit_proxy,
                        );
                    }
                }
                Ok(())
            })),
            &mut token,
        )
    }?;

    unsafe {
        webview.add_NavigationCompleted(
            &NavigationCompletedEventHandler::create(Box::new(move |view, args| {
                if let (Some(view), Some(args)) = (view, args) {
                    let mut id = 0;
                    args.NavigationId(&mut id)?;
                    let mut p = pending.borrow_mut();
                    if !p.windows_current(id) {
                        return Ok(());
                    }
                    let mut url = PWSTR::null();
                    view.Source(&mut url)?;
                    let url = take_pwstr(url);
                    let mut success = BOOL::default();
                    args.IsSuccess(&mut success)?;
                    if p.warming || success.as_bool() {
                        page_load(&mut p, PageLoadEvent::Finished, tab, &url, &proxy);
                    } else {
                        let url = p.navigate_url.clone().unwrap_or(url);
                        let mut status = Default::default();
                        args.WebErrorStatus(&mut status)?;
                        let why = format!("load failed: {status:?}");
                        p.loading = false;
                        p.hinted = None;
                        if let Some((id, _)) = p.navigate.take() {
                            fail(id, format!("navigate {url}: {why}"));
                        }
                        emit(
                            json!({ "event": "load_failed", "tab": tab, "url": url, "error": why }),
                        );
                        let _ = proxy.send_event(p.flush_event(tab));
                    }
                }
                Ok(())
            })),
            &mut token,
        )
    }?;
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn queued_start_keeps_its_original_command_generation() {
        let mut p = Pending::default();
        p.begin_navigation();
        p.native_start = Some(p.generation);
        // Two replacements are accepted before the first native start arrives.
        // Even a reused public request ID and identical URL cannot identify it.
        for _ in 0..2 {
            p.begin_navigation();
            p.navigate = Some((7, false));
            p.navigation_token = p.generation;
            p.native_next = Some(Navigation {
                generation: p.generation,
                method: "navigate".into(),
                url: Some("https://example.com/".into()),
            });
        }
        assert!(p.windows_next().is_none());
        assert!(!p.windows_start(10, "https://example.com/", false));
        assert!(!p.windows_current(10)); // Its cancellation cannot answer request 7.
        assert!(p.awaiting_start);
        assert_eq!(p.navigate, Some((7, false)));
        let next = p.windows_next().unwrap();
        assert_eq!(next.generation, p.generation);
        assert!(p.native_next.is_none());
        p.native_start = Some(next.generation);
        assert!(!p.windows_start(10, "https://example.com/redirect", true));
        assert_eq!(p.native_start, Some(next.generation));
        assert!(p.windows_start(11, "https://example.com/", false));
        assert!(!p.windows_current(10));
        assert!(p.windows_current(11));
    }

    #[test]
    fn timed_out_native_calls_are_cancelled_and_deferred_calls_are_dropped() {
        let mut p = Pending::default();
        p.begin_navigation();
        p.native_start = Some(p.generation);
        p.awaiting_start = false; // The timeout fired before the native start.
        assert!(!p.windows_start(10, "https://example.com/", false));
        p.native_next = Some(Navigation {
            generation: p.generation,
            method: "reload".into(),
            url: None,
        });
        assert!(p.windows_next().is_none());
        assert!(p.native_next.is_none());
        p.begin_navigation();
        p.native_start = Some(p.generation);
        assert!(p.windows_start(11, "https://example.com/", false));
    }

    #[test]
    fn replacement_starts_before_warmup_finishes() {
        let mut p = Pending {
            warming: true,
            ..Default::default()
        };
        p.windows_start(10, "about:blank", false);
        p.begin_navigation();
        p.windows_start(11, "https://example.com/", false);
        assert!(!p.windows_current(10));
        assert!(p.windows_current(11));
        let generation = p.generation;
        p.windows_start(11, "https://example.com/redirected", true);
        p.windows_start(10, "https://example.com/stale", true);
        assert!(p.windows_current(11));
        assert_eq!(p.generation, generation);
        p.begin_navigation();
        assert!(!p.windows_current(11));
        p.windows_start(12, "https://example.com/redirected", false);
        assert!(!p.windows_current(11));
        assert!(p.windows_current(12));
    }
}
