//! WebView2 can start a replacement before completing the retiring load.
//! Wry's load callbacks omit NavigationId, so observe the native events here.

use webview2_com::{
    take_pwstr, ContentLoadingEventHandler, NavigationCompletedEventHandler,
    NavigationStartingEventHandler,
};
use windows::core::{BOOL, PWSTR};
use wry::WebViewExtWindows;

use crate::{
    emit, fail, json, page_load, trace_navigation, EventLoopProxy, PageLoadEvent, Pending, Shared,
    TabId, UserEvent,
};

impl Pending {
    fn windows_start(&mut self, id: u64, url: &str) {
        if self.native_id == Some(id) {
            return; // HTTP redirects keep their NavigationId.
        }
        self.native_id = Some(id);
        if self.warming && url == "about:blank" {
            return;
        }
        // The real load can start before about:blank's completion. Its later
        // completion must neither clear this load nor consume its waiter.
        self.warming = false;
        self.provisional_start();
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
    unsafe {
        webview.add_NavigationStarting(
            &NavigationStartingEventHandler::create(Box::new(move |_, args| {
                if let Some(args) = args {
                    let mut id = 0;
                    let mut url = PWSTR::null();
                    args.NavigationId(&mut id)?;
                    args.Uri(&mut url)?;
                    let url = take_pwstr(url);
                    let mut p = start_pending.borrow_mut();
                    p.windows_start(id, &url);
                    trace_navigation("provisional start", tab, &p, &url);
                }
                Ok(())
            })),
            &mut token,
        )
    }?;

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
    fn replacement_starts_before_warmup_finishes() {
        let mut p = Pending {
            warming: true,
            ..Default::default()
        };
        p.windows_start(10, "about:blank");
        p.begin_navigation();
        p.windows_start(11, "https://example.com/");
        assert!(!p.windows_current(10));
        assert!(p.windows_current(11));
        let generation = p.generation;
        p.windows_start(11, "https://example.com/redirected");
        assert_eq!(p.generation, generation);
        p.begin_navigation();
        assert!(!p.windows_current(11));
        p.windows_start(12, "https://example.com/redirected");
        assert!(!p.windows_current(11));
        assert!(p.windows_current(12));
    }
}
