//! Observe main-frame provisional starts, which Wry only reports at commit.
//! Forward the rest of WKNavigationDelegate to Wry (policy, loads, downloads).

use std::cell::RefCell;

use objc2::rc::Retained;
use objc2::runtime::{AnyObject, NSObject, NSObjectProtocol, ProtocolObject, Sel};
use objc2::{define_class, msg_send, DeclaredClass, MainThreadOnly, Message};
use objc2_foundation::NSError;
use objc2_web_kit::{WKNavigation, WKNavigationDelegate, WKWebView};
use wry::WebViewExtMacOS;

use crate::{emit, fail, json, trace_navigation, EventLoopProxy, Shared, TabId, UserEvent};

struct Active {
    navigation: Retained<WKNavigation>,
    request: Option<u64>,
}

pub struct ObserverState {
    original: Retained<ProtocolObject<dyn WKNavigationDelegate>>,
    pending: Shared,
    tab: TabId,
    proxy: EventLoopProxy<UserEvent>,
    active: RefCell<Option<Active>>,
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
                *state.active.borrow_mut() = navigation.map(|n| Active {
                    navigation: n.retain(),
                    request: p.navigate.map(|(id, _)| id),
                });
                // Also cover page-initiated navigation without an action reply.
                p.loading = true;
                p.hinted = None;
                let url = unsafe { webview.URL() }.and_then(|u| u.absoluteString()).map(|u| u.to_string()).unwrap_or_default();
                trace_navigation("provisional start", state.tab, &p, &url);
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
    fn failed(&self, navigation: Option<&WKNavigation>, error: &NSError) {
        let state = self.ivars();
        let mut active = state.active.borrow_mut();
        let Some(current) = active.as_ref() else {
            return;
        };
        if !navigation.is_some_and(|n| std::ptr::eq(n, &*current.navigation)) {
            return; // A newer native navigation has already started.
        }
        let mut p = state.pending.borrow_mut();
        if current.request != p.navigate.map(|(id, _)| id) {
            return; // An explicit navigate superseded this load before starting.
        }
        *active = None;
        p.loading = false;
        p.hinted = None;
        let why = error.localizedDescription().to_string();
        let url = p.navigate_url.take().unwrap_or_default();
        if let Some((id, _)) = p.navigate.take() {
            fail(id, format!("navigate {url}: load failed: {why}"));
        }
        emit(json!({ "event": "load_failed", "tab": state.tab, "url": url, "error": why }));
        // A cancelled download can leave the old document usable. If another
        // navigation starts before dispatch, its requests must stay queued.
        let _ = state.proxy.send_event(UserEvent::FlushIfIdle(state.tab));
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
    });
    let observer: Retained<NavigationObserver> = unsafe { msg_send![super(observer), init] };
    unsafe { webview.setNavigationDelegate(Some(ProtocolObject::from_ref(&*observer))) };
    observer
}
