//! Observe main-frame provisional starts, which Wry only reports at commit.
//! Forward the rest of WKNavigationDelegate to Wry (policy, loads, downloads).

use std::cell::RefCell;

use objc2::rc::Retained;
use objc2::runtime::{AnyObject, NSObject, NSObjectProtocol, ProtocolObject, Sel};
use objc2::{define_class, msg_send, DeclaredClass, MainThreadOnly, Message};
use objc2_foundation::{NSError, NSString, NSURLRequest, NSURL};
use objc2_web_kit::{WKNavigation, WKNavigationDelegate, WKWebView};
use wry::WebViewExtMacOS;

use crate::{emit, fail, json, trace_navigation, EventLoopProxy, Shared, TabId, UserEvent};

pub struct ObserverState {
    original: Retained<ProtocolObject<dyn WKNavigationDelegate>>,
    pending: Shared,
    tab: TabId,
    proxy: EventLoopProxy<UserEvent>,
    active: RefCell<Option<Retained<WKNavigation>>>,
    explicit: RefCell<Option<(u64, Retained<WKNavigation>)>>,
}

define_class!(
    #[unsafe(super(NSObject))]
    #[thread_kind = MainThreadOnly]
    #[ivars = ObserverState]
    pub struct NavigationObserver;

    unsafe impl NSObjectProtocol for NavigationObserver {
        #[unsafe(method(respondsToSelector:))]
        fn responds_to_selector(&self, selector: Sel) -> bool {
            let own: bool = unsafe { msg_send![super(self), respondsToSelector: selector] };
            own || self.ivars().original.respondsToSelector(selector)
        }
    }

    impl NavigationObserver {
        #[unsafe(method(forwardingTargetForSelector:))]
        fn forwarding_target(&self, _selector: Sel) -> *mut AnyObject {
            // The original delegate stays retained for this observer's lifetime.
            Retained::as_ptr(&self.ivars().original) as *mut AnyObject
        }
    }

    unsafe impl WKNavigationDelegate for NavigationObserver {
        #[unsafe(method(webView:didStartProvisionalNavigation:))]
        fn provisional_start(&self, webview: &WKWebView, navigation: Option<&WKNavigation>) {
            let state = self.ivars();
            let mut p = state.pending.borrow_mut();
            if !p.warming {
                if let Some((id, _)) = p.navigate {
                    if state.explicit.borrow().as_ref().is_some_and(|(expected, n)| {
                        *expected == id && !navigation.is_some_and(|current| std::ptr::eq(current, &**n))
                    }) {
                        return;
                    }
                }
                *state.active.borrow_mut() = navigation.map(|n| n.retain());
                // Also cover page-initiated navigation without an action reply.
                p.provisional_start();
                let url = unsafe { webview.URL() }.and_then(|u| u.absoluteString()).map(|u| u.to_string()).unwrap_or_default();
                trace_navigation("provisional start", state.tab, &p, &url);
            }
        }

        #[unsafe(method(webView:didCommitNavigation:))]
        fn committed(&self, webview: &WKWebView, navigation: Option<&WKNavigation>) {
            if self.is_current_load(navigation) {
                unsafe { self.ivars().original.webView_didCommitNavigation(webview, navigation) };
            }
        }

        #[unsafe(method(webView:didFinishNavigation:))]
        fn finished(&self, webview: &WKWebView, navigation: Option<&WKNavigation>) {
            if self.is_current_load(navigation) {
                unsafe { self.ivars().original.webView_didFinishNavigation(webview, navigation) };
            }
        }

        #[unsafe(method(webView:didFailProvisionalNavigation:withError:))]
        fn provisional_failed(&self, _webview: &WKWebView, navigation: Option<&WKNavigation>, error: &NSError) {
            self.failed(navigation, error);
        }

        #[unsafe(method(webView:didFailNavigation:withError:))]
        fn navigation_failed(&self, _webview: &WKWebView, navigation: Option<&WKNavigation>, error: &NSError) {
            self.failed(navigation, error);
        }
    }
);

impl NavigationObserver {
    fn is_current_load(&self, navigation: Option<&WKNavigation>) -> bool {
        let p = self.ivars().pending.borrow();
        // The initial blank still has to finish when a real navigate is queued.
        if p.warming {
            return true;
        }
        !p.awaiting_start
            && p.native_generation == p.generation
            && navigation.is_some_and(|current| {
                self.ivars()
                    .active
                    .borrow()
                    .as_ref()
                    .is_some_and(|n| std::ptr::eq(current, &**n))
            })
    }

    fn is_current_failure(&self, navigation: Option<&WKNavigation>) -> bool {
        let state = self.ivars();
        let p = state.pending.borrow();
        let Some(navigation) = navigation else {
            return false;
        };
        if p.warming
            || p.hinted.is_some()
            || !state
                .active
                .borrow()
                .as_ref()
                .is_some_and(|n| std::ptr::eq(navigation, &**n))
        {
            return false;
        }
        if let Some((id, _)) = p.navigate {
            // A delayed start from an older click may arrive while this ID is
            // already pending. Match the token returned by the native API.
            return state
                .explicit
                .borrow()
                .as_ref()
                .is_none_or(|(expected, n)| *expected == id && std::ptr::eq(navigation, &**n));
        }
        true
    }

    fn failed(&self, navigation: Option<&WKNavigation>, error: &NSError) {
        let state = self.ivars();
        if !self.is_current_failure(navigation) {
            trace_navigation(
                "stale native failure",
                state.tab,
                &state.pending.borrow(),
                &error.localizedDescription().to_string(),
            );
            return;
        }
        let mut p = state.pending.borrow_mut();
        *state.active.borrow_mut() = None;
        p.loading = false;
        p.awaiting_start = false;
        p.hinted = None;
        let why = error.localizedDescription().to_string();
        let url = p.navigate_url.take().unwrap_or_default();
        if let Some((id, _)) = p.navigate.take() {
            fail(id, format!("navigate {url}: load failed: {why}"));
        }
        emit(json!({ "event": "load_failed", "tab": state.tab, "url": url, "error": why }));
        // A cancelled download can leave the old document usable. If another
        // navigation starts before dispatch, its requests must stay queued.
        let _ = state.proxy.send_event(p.flush_event(state.tab));
    }

    pub fn navigate(
        &self,
        webview: &wry::WebView,
        id: u64,
        method: &str,
        url: Option<&str>,
    ) -> wry::Result<()> {
        let webview = webview.webview();
        let navigation = unsafe {
            match method {
                "navigate" => {
                    let url = NSURL::URLWithString(&NSString::from_str(url.unwrap())).ok_or_else(
                        || wry::Error::Io(std::io::Error::other("invalid navigation URL")),
                    )?;
                    webview.loadRequest(&NSURLRequest::requestWithURL(&url))
                }
                "reload" => webview.reload(),
                "back" => webview.goBack(),
                "forward" => webview.goForward(),
                _ => unreachable!("not a native navigation"),
            }
        };
        *self.ivars().explicit.borrow_mut() = navigation.map(|n| (id, n));
        Ok(())
    }
}

pub fn observe(
    webview: &wry::WebView,
    tab: TabId,
    pending: Shared,
    proxy: EventLoopProxy<UserEvent>,
) -> Retained<NavigationObserver> {
    let webview = webview.webview();
    let original = unsafe { webview.navigationDelegate() }.expect("Wry navigation delegate");
    let observer = NavigationObserver::alloc(webview.mtm()).set_ivars(ObserverState {
        original,
        pending,
        tab,
        proxy,
        active: RefCell::new(None),
        explicit: RefCell::new(None),
    });
    let observer: Retained<NavigationObserver> = unsafe { msg_send![super(observer), init] };
    unsafe { webview.setNavigationDelegate(Some(ProtocolObject::from_ref(&*observer))) };
    observer
}
