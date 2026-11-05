// Injected into every page before window.onload. Rust calls
// __bruster.run(id, method, params); the answer goes back over
// window.ipc.postMessage as {"id", "result"} or {"id", "error"}.
//
// Elements are addressed either by CSS selector ({selector: "#go"})
// or by a ref handed out by `snapshot` / `find` ({ref: "e3"}). Refs
// live until the next snapshot, find or navigation. Selectors reach
// into open shadow roots and same-origin iframes.
(() => {
  const SNAPSHOT_TAGS = 'a,button,input,textarea,select,summary,[role],[contenteditable],[onclick],[tabindex],[draggable=true],h1,h2,h3,h4,h5,h6,label,img[alt],p,li,td,th';
  // Text nodes inside these are already covered by the element's own name or
  // text, or are not content at all (script, style).
  const TEXT_OWNERS = 'p,li,td,th,h1,h2,h3,h4,h5,h6,a,button,label,summary,option,textarea,select,[onclick],[tabindex],[contenteditable],[draggable=true],[role=button],[role=link],[role=tab],[role=menuitem],[role=option],script,style,noscript,template';
  const TEXT_NODE = 3;
  const SHOW_ELEMENT_AND_TEXT = NodeFilter.SHOW_ELEMENT | NodeFilter.SHOW_TEXT;
  // Legacy keyCode/which for named keys; letters, digits and space are derived.
  const KEY_CODES = {
    Backspace: 8, Tab: 9, Enter: 13, Shift: 16, Control: 17, Alt: 18, Escape: 27, ' ': 32,
    PageUp: 33, PageDown: 34, End: 35, Home: 36, ArrowLeft: 37, ArrowUp: 38, ArrowRight: 39, ArrowDown: 40,
    Delete: 46, Meta: 91,
  };
  const F_KEY_BASE = 111;
  const NUMBER_CHARS = /[\d.eE+-]/;
  const SNAPSHOT_MAX = 1000;
  const NAME_MAX = 80;
  const TEXT_MAX = 200;
  const POLL_MS = 50;
  const DEFAULT_TIMEOUT_MS = 10000;
  const ACTION_TIMEOUT_MS = 5000;
  const IDLE_MS = 500;
  // navigate until=idle gives up waiting for a quiet network after this.
  const NAV_IDLE_CAP_MS = 10000;
  const PREFETCH_HOSTS_MAX = 8;
  const NET_MAX = 500;
  const BODY_MAX = 16384;
  const NET_BYTES = 2 * 1024 * 1024;
  const HEADER_MAX = 4096;
  const URL_MAX = 4096;
  const CAPTURE_MAX = 4;
  const CAPTURE_MS = 5000;
  const CONSOLE_MAX = 500;
  const LOG_MAX = 1000;
  const DIALOG_MAX = 100;
  const DIALOG_BYTES = 128 * 1024;

  const TAG_ROLE = {
    a: 'link', button: 'button', textarea: 'textbox', select: 'combobox', summary: 'button',
    h1: 'heading', h2: 'heading', h3: 'heading', h4: 'heading', h5: 'heading', h6: 'heading',
    img: 'img', label: 'label', p: 'text', li: 'listitem', td: 'cell', th: 'columnheader',
  };
  const INPUT_ROLE = {
    button: 'button', submit: 'button', reset: 'button', image: 'button',
    checkbox: 'checkbox', radio: 'radio', range: 'slider', number: 'spinbutton',
  };

  let refs = new Map();
  const WeakReference = globalThis.WeakRef;
  // Older engines can resolve a token by walking the live DOM. Neither path
  // owns detached elements or documents from navigated-away frames.
  const refTokens = new WeakMap();
  function refElement(ref) {
    const stored = refs.get(ref);
    if (!stored) return;
    if (WeakReference) return stored.deref();
    for (const el of nodesInRoots(document, NodeFilter.SHOW_ELEMENT)) {
      if (refTokens.get(el) === stored) return el;
    }
  }

  // Pages can replace JSON.stringify after injection; IPC must still work.
  const stringify = JSON.stringify.bind(JSON);
  const NativeError = Error;
  const nativeStackGetter = Object.getOwnPropertyDescriptor(new NativeError(), 'stack')?.get;
  // Do not retain an engine substring's potentially much larger backing string.
  // Call only on already-bounded diagnostic text, preserving UTF-16 code units.
  const compact = s => s.split('').join('');
  const documentQuery = Document.prototype.querySelector;
  const elementQuery = Element.prototype.querySelector;
  const fragmentQuery = DocumentFragment.prototype.querySelector;
  const documentId = `${performance.timeOrigin}:${Math.random()}`;
  let generation = 0;
  const post = (msg) => window.ipc.postMessage(stringify({ ...msg, document: documentId, generation }));
  const trunc = (s, n) => (s = (s || '').replace(/\s+/g, ' ').trim()).length > n ? s.slice(0, n) + '…' : s;
  const checkCancelled = signal => { if (signal?.aborted) throw new Error('request cancelled'); };
  function sleep(ms, signal) {
    checkCancelled(signal);
    return new Promise((resolve, reject) => {
      const timer = setTimeout(done, ms);
      function done() {
        clearTimeout(timer);
        signal?.removeEventListener('abort', done);
        if (signal?.aborted) reject(new Error('request cancelled'));
        else resolve();
      }
      signal?.addEventListener('abort', done, { once: true });
    });
  }

  // Subscribe only while a command is waiting. DOM mutations wake it promptly;
  // the timer still covers CSSOM edits, animations and newly attached roots.
  function changed(el, signal) {
    checkCancelled(signal);
    return new Promise((resolve, reject) => {
      const roots = new Set([document, el?.getRootNode()].filter(Boolean));
      const observer = new MutationObserver(done);
      const timer = setTimeout(done, POLL_MS);
      function done() {
        clearTimeout(timer);
        observer.disconnect();
        for (const root of roots) root.removeEventListener('load', done, true);
        signal?.removeEventListener('abort', done);
        if (signal?.aborted) reject(new Error('request cancelled'));
        else resolve();
      }
      for (const root of roots) {
        observer.observe(root, { subtree: true, childList: true, attributes: true, characterData: true });
        root.addEventListener('load', done, true);
      }
      signal?.addEventListener('abort', done, { once: true });
    });
  }
  // Format before serialization, with a shared output/item/depth budget. Avoid
  // application getters and toJSON: logging must not traverse the entire graph.
  function formatLog(args) {
    let out = '', items = 40;
    const seen = new WeakSet();
    const add = s => { out += s.slice(0, LOG_MAX - out.length); };
    function value(v, depth, quoted) {
      if (out.length >= LOG_MAX || --items < 0) return add('…');
      if (typeof v === 'string') return add(quoted ? stringify(v.slice(0, LOG_MAX - out.length)) : v);
      if (v === null || typeof v !== 'object') return add(typeof v === 'function' ? '[Function]' : String(v));
      if (v instanceof NativeError) {
        const field = key => {
          let obj = v;
          for (let i = 0; obj && i < 4; i++, obj = Object.getPrototypeOf(obj)) {
            const d = Object.getOwnPropertyDescriptor(obj, key);
            if (d) return d;
          }
        };
        const text = d => !d ? '' : 'value' in d ? (typeof d.value === 'string' ? d.value : '') : '[Getter]';
        const name = field('name'), message = field('message'), descriptor = field('stack');
        add(text(name)); add(': '); add(text(message));
        let stack = text(descriptor);
        // V8 keeps even an assigned stack string behind its native accessor.
        // Admit only that captured getter, with plain bounded error fields and
        // no prepareStackTrace hook that could run application code lazily.
        if (nativeStackGetter && descriptor?.get === nativeStackGetter
            && [name, message].every(d => d && 'value' in d && typeof d.value === 'string' && d.value.length <= LOG_MAX)) {
          let ctor = NativeError, safe = false;
          for (let i = 0; ctor && i < 4; i++, ctor = Object.getPrototypeOf(ctor)) {
            const hook = Object.getOwnPropertyDescriptor(ctor, 'prepareStackTrace');
            if (hook) { safe = 'value' in hook && hook.value === undefined; break; }
          }
          if (safe || !ctor) {
            const value = nativeStackGetter.call(v);
            stack = typeof value === 'string' ? value : '';
          }
        }
        if (stack) { add('\n'); add(stack); }
        return;
      }
      if (seen.has(v)) return add('[Circular]');
      if (depth >= 3) return add(Array.isArray(v) ? '[…]' : '{…}');
      seen.add(v);
      const array = Array.isArray(v);
      add(array ? '[' : '{');
      let n = 0;
      for (const k in v) {
        if (!Object.prototype.hasOwnProperty.call(v, k)) continue;
        if (n++ >= 20 || items <= 0 || out.length >= LOG_MAX) { add('…'); break; }
        if (n > 1) add(',');
        if (!array) { add(stringify(k.slice(0, LOG_MAX))); add(':'); }
        const d = Object.getOwnPropertyDescriptor(v, k);
        if (d && 'value' in d) value(d.value, depth + 1, true);
        else add('[Getter]');
      }
      add(array ? ']' : '}');
      seen.delete(v);
    }
    try {
      for (let i = 0; i < args.length && out.length < LOG_MAX && items > 0; i++) {
        if (i) add(' ');
        value(args[i], 0, false);
      }
    } catch { add('[unavailable]'); }
    return compact(out);
  }

  // Request log. Patched fetch/XHR give status, headers and a body prefix;
  // the page's own loads (img, script, css) come from the Performance API.
  // Cleared on navigation by virtue of living in the page.
  const net = [];
  let inflight = 0;
  let netBytes = 0, netEpoch = 0, captureBodies = true;
  const netStates = new WeakMap(), captures = new Set(), loggedXhrs = new Set(), loggedFetches = new Set();
  const activeEntry = entry => entry && netStates.get(entry)?.epoch === netEpoch;
  const bytesOf = v => typeof v === 'string' ? v.length * 2 : v && typeof v === 'object'
    ? Object.entries(v).reduce((n, [k, s]) => n + 32 + k.length * 2 + bytesOf(s), 0) : 0;
  function netField(entry, key, value) {
    if (!activeEntry(entry)) return;
    const delta = bytesOf(value) - bytesOf(entry[key]);
    if (netBytes + delta > NET_BYTES) { entry.truncated = true; return; }
    netBytes += delta;
    entry[key] = typeof value === 'string' ? compact(value) : value;
  }
  function admit(type, method, url) {
    if (net.length >= NET_MAX || netBytes + 256 > NET_BYTES) return null;
    const entry = { type, start: performance.now() };
    netStates.set(entry, { epoch: netEpoch });
    netBytes += 256; // scalar fields and bounded truncation/skipping markers
    net.push(entry);
    netField(entry, 'method', String(method).slice(0, 32));
    try {
      if (typeof url === 'string' && url.length > URL_MAX) {
        netField(entry, 'url', url.slice(0, URL_MAX));
        entry.truncated = true;
      } else { netField(entry, 'url', new URL(url, location.href).href.slice(0, URL_MAX)); }
    } catch {}
    return entry;
  }
  function headersOf(headers) {
    const out = Object.create(null);
    let left = Math.min(HEADER_MAX, Math.floor((NET_BYTES - netBytes) / 2));
    try {
      for (let [key, value] of headers) {
        if (typeof key !== 'string' || left < key.length + 16) break;
        key = compact(key.toLowerCase());
        if (typeof value !== 'string') {
          if (typeof value !== 'number' && typeof value !== 'boolean') continue;
          value = String(value);
        }
        const text = compact(value.slice(0, left - key.length - 16).trim());
        out[key] = out[key] === undefined ? text : out[key] + ', ' + text;
        left -= key.length + text.length + 16;
      }
    } catch {}
    return out;
  }
  function* requestHeaders(h) {
    if (!h) return;
    if (typeof h[Symbol.iterator] === 'function') { yield* h; return; }
    for (const key in h) {
      if (Object.prototype.hasOwnProperty.call(h, key)) yield [key, h[key]];
    }
  }
  function clearNetwork() {
    netEpoch++;
    for (const stop of captures) stop();
    for (const state of loggedXhrs) state.entry = null;
    loggedXhrs.clear();
    for (const state of loggedFetches) state.entry = null;
    loggedFetches.clear();
    net.length = 0;
    netBytes = 0;
    performance.clearResourceTimings();
  }

  async function captureBody(res, entry) {
    if (!activeEntry(entry)) return;
    const type = res.headers.get('content-type') || '';
    const limit = Math.min(BODY_MAX, Math.floor((NET_BYTES - netBytes) / 2));
    if (!captureBodies || !limit || captures.size >= CAPTURE_MAX || (type && !/^(text\/|application\/(json|[^;]+\+json|javascript|xml|[^;]+\+xml|x-www-form-urlencoded))/i.test(type))) {
      entry.body_skipped = true;
      return;
    }
    // Reserve the worst-case UTF-16 payload before cloning/starting a reader.
    netBytes += limit * 2;
    let reader, timer, stopped = false;
    const stop = () => {
      stopped = true;
      if (reader) reader.cancel().catch(() => {});
    };
    captures.add(stop);
    let text = '';
    try {
      const clone = res.clone();
      if (!clone.body) return;
      reader = clone.body.getReader();
      const decoder = new TextDecoder();
      timer = setTimeout(stop, CAPTURE_MS);
      while (!stopped && text.length < limit) {
        const { value, done } = await reader.read();
        if (done) {
          text += decoder.decode().slice(0, limit - text.length);
          break;
        }
        // A cached response can arrive as one enormous chunk. Bound decoding
        // as well as retained text, including UTF-8 split between these slices.
        for (let at = 0; at < value.length && text.length < limit; at += BODY_MAX) {
          const chunk = decoder.decode(value.subarray(at, at + BODY_MAX), { stream: true });
          text += chunk.slice(0, limit - text.length);
        }
      }
    } catch {
      if (activeEntry(entry)) entry.body_skipped = true;
    } finally {
      // Cancel only the cloned tee branch. Awaiting cancellation would wait
      // for the page's branch too, defeating the prefix bound on live streams.
      clearTimeout(timer);
      if (activeEntry(entry)) {
        netBytes -= limit * 2;
        netField(entry, 'body', text);
        if (stopped || text.length === limit) entry.body_truncated = true;
      }
      stop();
      // This private clone is discarded, so its reader need not be unlocked.
      // releaseLock() can allocate during GC while holding WebKit's stream
      // mutex, deadlocking the page: https://bugs.webkit.org/show_bug.cgi?id=326046
      // The cancelled reader and clone can be collected together instead.
      captures.delete(stop);
    }
  }

  const origFetch = window.fetch;
  window.fetch = async function (input, init) {
    // Indirection lets clear release metadata even if the page's original fetch
    // has not received headers yet. Never abort that original request.
    const state = { entry: admit('fetch', init?.method || input?.method || 'GET', typeof input === 'string' ? input : input?.url || input?.href) };
    if (state.entry) {
      loggedFetches.add(state);
      try { netField(state.entry, 'req_headers', headersOf(requestHeaders(init?.headers || input?.headers))); } catch {}
    }
    inflight++;
    try {
      const res = await origFetch.apply(this, arguments);
      const entry = state.entry;
      if (activeEntry(entry)) {
        entry.status = res.status;
        entry.ms = Math.round(performance.now() - entry.start);
        netField(entry, 'res_headers', headersOf(res.headers));
        captureBody(res, entry).catch(() => {});
      }
      return res;
    } catch (e) {
      const entry = state.entry;
      if (activeEntry(entry)) {
        netField(entry, 'error', formatLog([e]));
        entry.ms = Math.round(performance.now() - entry.start);
      }
      throw e;
    } finally {
      state.entry = null;
      loggedFetches.delete(state);
      inflight--;
      resourceDone();
    }
  };

  const xhrOpen = XMLHttpRequest.prototype.open;
  const xhrSend = XMLHttpRequest.prototype.send;
  const xhrStates = new WeakMap();
  XMLHttpRequest.prototype.open = function (method, url) {
    let state = xhrStates.get(this);
    if (!state) {
      state = { entry: null, pending: false };
      xhrStates.set(this, state);
      this.addEventListener('loadend', function () {
        if (state.pending) { state.pending = false; inflight--; resourceDone(); }
        const entry = state.entry;
        state.entry = null;
        loggedXhrs.delete(state);
        if (!activeEntry(entry)) return;
        entry.status = this.status;
        entry.ms = Math.round(performance.now() - entry.start);
        const headers = this.getAllResponseHeaders().slice(0, HEADER_MAX).split(/\r?\n/).filter(l => l.includes(':'))
          .map(l => { const i = l.indexOf(':'); return [l.slice(0, i), l.slice(i + 1).trim()]; });
        netField(entry, 'res_headers', headersOf(headers));
        if (captureBodies && (this.responseType === '' || this.responseType === 'text')) {
          const limit = Math.min(BODY_MAX, Math.floor((NET_BYTES - netBytes) / 2));
          netField(entry, 'body', this.responseText.slice(0, limit));
          if (this.responseText.length > limit) entry.body_truncated = true;
        } else { entry.body_skipped = true; }
      });
    }
    // Reopen can synchronously abort the old request. Let its loadend consume
    // the old state before assigning the next entry; an invalid open leaves it.
    const result = xhrOpen.apply(this, arguments);
    if (state.pending) { state.pending = false; inflight--; resourceDone(); }
    loggedXhrs.delete(state);
    state.entry = admit('xhr', method, url);
    if (state.entry) loggedXhrs.add(state);
    return result;
  };
  XMLHttpRequest.prototype.send = function () {
    const state = xhrStates.get(this), added = state && !state.pending;
    if (added) { state.pending = true; inflight++; }
    try { return xhrSend.apply(this, arguments); }
    catch (e) {
      if (added && state.pending) { state.pending = false; inflight--; resourceDone(); }
      throw e;
    }
  };

  // Console and page errors, readable through `console`.
  const consoleLog = [];
  const logConsole = (level, text) => {
    if (consoleLog.length < CONSOLE_MAX) consoleLog.push({ level, text: text.slice(0, LOG_MAX), ms: Math.round(performance.now()) });
  };
  for (const level of ['log', 'info', 'warn', 'error', 'debug']) {
    const orig = console[level];
    console[level] = function (...args) {
      if (consoleLog.length < CONSOLE_MAX) logConsole(level, formatLog(args));
      return orig.apply(this, args);
    };
  }
  window.addEventListener('error', (e) => {
    if (consoleLog.length < CONSOLE_MAX) logConsole('error', formatLog([e.message, e.filename || '', e.lineno || '']));
  });
  window.addEventListener('unhandledrejection', (e) => {
    if (consoleLog.length < CONSOLE_MAX) logConsole('error', formatLog(['Unhandled rejection:', e.reason]));
  });

  // Native alert/confirm/prompt would block the page and every later call.
  // Answer them here with the last `dialog` setting and tell the agent.
  let dialogAnswer = { accept: true, text: '' };
  const dialogs = [];
  let dialogBytes = 0;
  const onDialog = (type, message, def) => {
    if (dialogs.length < DIALOG_MAX && dialogBytes + LOG_MAX * 2 + 64 <= DIALOG_BYTES) {
      const d = { type, message: formatLog([message]), accept: dialogAnswer.accept };
      dialogBytes += d.message.length * 2 + 64;
      dialogs.push(d);
      post({ event: 'dialog', ...d });
    } else if (dialogs.length) {
      const last = dialogs[dialogs.length - 1];
      last.dropped = (last.dropped || 0) + 1;
    }
    if (type === 'prompt') return dialogAnswer.accept ? (dialogAnswer.text || def || '') : null;
    return type === 'confirm' ? dialogAnswer.accept : undefined;
  };
  window.alert = (m) => { onDialog('alert', m); };
  window.confirm = (m) => onDialog('confirm', m);
  window.prompt = (m, d) => onDialog('prompt', m, d);

  // target=_blank links are opened by Rust, not WebKit. On WebKitGTK, denying
  // the `create` signal of a link click leaves every later webview without
  // load events. Bubble phase on window, so page handlers run first.
  //
  // A link or form submit the page did not cancel means a load is about to
  // start. The reply of the current call carries that hint so Rust holds the
  // agent's next calls for the new page instead of running them in this one.
  let navExpected = false;
  // Listeners registered after ours can still cancel the default action.
  // Settle after synchronous event dispatch, before the action's async reply.
  // A confirmed hint must survive arbitrarily delayed native start callbacks.
  const hintNavigation = (e) => queueMicrotask(() => { if (!e.defaultPrevented) navExpected = true; });
  const leavesPage = (a) => /^https?:$/.test(a.protocol) && !a.hasAttribute('download')
    && !(a.hash && a.href.split('#')[0] === location.href.split('#')[0]);
  window.addEventListener('click', (e) => {
    const a = e.target && e.target.closest && e.target.closest('a[href]');
    if (!a || e.defaultPrevented) return;
    if (a.target === '_blank') {
      e.preventDefault();
      post({ open: a.href });
      return;
    }
    if ((!a.target || a.target === '_self') && leavesPage(a)) hintNavigation(e);
  });
  window.addEventListener('submit', (e) => {
    if (!e.defaultPrevented && e.target.method !== 'dialog' && (!e.target.target || e.target.target === '_self')) hintNavigation(e);
  });
  // A beforeunload prompt is a native dialog that would block the tab, and
  // the agent, for good. This runs before any page listener (registered
  // first) and stops them; the page leaves without asking.
  window.addEventListener('beforeunload', (e) => e.stopImmediatePropagation());

  // Page milestones for `navigate until`, top frame only. WebKit reports a
  // load as finished only once every subframe is done, including ad iframes
  // added after load, so the page's own load event is reported here.
  // idle: no fetch/xhr in flight and no resource finished for IDLE_MS.
  let lastResource = 0;
  let domReached = false, loadReached = false, idleReached = false;
  const bind = (next) => {
    generation = next;
    post({ bound: true });
    // Native commit and page IPC use different callback queues. Re-send any
    // milestone reached before Rust bound this document to its navigation.
    if (domReached) post({ dom: location.href });
    if (loadReached) post({ loaded: location.href });
    if (idleReached) post({ idle: location.href });
  };
  const resourceDone = () => { lastResource = Date.now(); };
  if (window.top === window) {
    // pushState history can change only state, not the URL. Native load
    // callbacks do not fire for these traversals, so acknowledge popstate.
    window.addEventListener('popstate', () => post({ history: location.href }));
    new PerformanceObserver(() => { lastResource = Date.now(); }).observe({ type: 'resource' });
    document.addEventListener('DOMContentLoaded', () => { domReached = true; post({ dom: location.href }); });
    window.addEventListener('load', () => {
      loadReached = true;
      post({ loaded: location.href });
      const start = Date.now();
      lastResource = start;
      const tick = () => {
        const quiet = !inflight && Date.now() - lastResource >= IDLE_MS;
        if (quiet || Date.now() - start >= NAV_IDLE_CAP_MS) {
          idleReached = true;
          return post({ idle: location.href });
        }
        setTimeout(tick, POLL_MS);
      };
      tick();
    });
  }

  const composedParent = (el) => el.assignedSlot || el.parentElement || el.getRootNode().host;
  const domParent = (el) => el.parentElement;
  const ariaHidden = (el) => el.getAttribute('aria-hidden') === 'true';
  const closedDetails = (el) => {
    const parent = composedParent(el);
    return parent?.tagName === 'DETAILS' && !parent.open
      && el !== [...parent.children].find(node => node.tagName === 'SUMMARY');
  };

  // Snapshot-local memoization: no retained nodes or stale state after a page
  // mutation. Iterative so deeply nested documents cannot exhaust the JS stack.
  function ancestorFlag(el, parentOf, test, cache) {
    const path = cache && [];
    let flag = false;
    for (let node = el; node; node = parentOf(node)) {
      const known = cache?.get(node);
      if (known !== undefined) { flag = known; break; }
      if (path) path.push(node);
      if (test(node)) { flag = true; break; }
    }
    if (path) for (const node of path) cache.set(node, flag);
    return flag;
  }

  function visible(el, detailsCache) {
    // Opacity-zero targets still receive pointer events. visibility:hidden does
    // not, unless a descendant explicitly overrides the inherited visibility.
    const hasVisibilityCheck = !!el.checkVisibility;
    // The native check covers both CSS visibility and the presence of a layout
    // box. Avoid two extra style/geometry queries for every snapshot element.
    if (hasVisibilityCheck) {
      if (!el.checkVisibility({ checkVisibilityCSS: true })) return false;
    } else if (getComputedStyle(el).visibility !== 'visible') return false;
    // Older WKWebView versions report layout boxes for closed details content.
    // Only the first summary (and its composed descendants) is rendered there.
    if (ancestorFlag(el, composedParent, closedDetails, detailsCache)) return false;
    return hasVisibilityCheck || el.getClientRects().length > 0;
  }
  const describe = (el) => `<${el.tagName.toLowerCase()}${el.id ? '#' + el.id : ''}>`;

  function connected(el) {
    if (!el || !el.isConnected) return false;
    // A node in a navigated-away frame can remain connected to its old Document.
    // Verify every frame in the chain still hosts that document in this page.
    let owner = el.ownerDocument;
    try {
      while (owner !== document) {
        const frame = owner.defaultView?.frameElement;
        if (!frame?.isConnected || frame.contentDocument !== owner) return false;
        owner = frame.ownerDocument;
      }
    } catch { return false; } // A frame may have navigated cross-origin.
    return true;
  }

  // querySelector stops at shadow roots and iframes. These walk through open
  // shadow roots and same-origin frames, in document order.
  //
  // TreeWalker, not querySelectorAll('*'): a NodeList pins every node of the
  // page, and a NodeList left over from a navigated-away page kept 13 MB per
  // 10k-node document alive until a full GC that never came (measured: 30
  // loads 627 MB settled vs 212 MB with a walker).
  function* elements(root) {
    const walker = (root.ownerDocument || root).createTreeWalker(root, NodeFilter.SHOW_ELEMENT);
    for (let el = walker.nextNode(); el; el = walker.nextNode()) yield el;
  }
  function* nodesInRoots(root, whatToShow) {
    const nested = [];
    const walker = (root.ownerDocument || root).createTreeWalker(root, whatToShow);
    for (let node = walker.nextNode(); node; node = walker.nextNode()) {
      if (node.nodeType !== TEXT_NODE) {
        const child = node.shadowRoot || node.contentDocument;
        if (child) nested.push(child);
      }
      yield node;
    }
    // Keep the existing order: this root first, then embedded roots depth-first.
    // Discover them during the same walk instead of scanning the whole page
    // before a selector's first match or a capped snapshot can return.
    for (const child of nested) yield* nodesInRoots(child, whatToShow);
  }
  // `matches` throws the same error as querySelector on a bad selector.
  function* matching(root, sel) {
    for (const el of nodesInRoots(root, NodeFilter.SHOW_ELEMENT)) if (el.matches(sel)) yield el;
  }
  function query(root, sel) {
    // Native lookup can stop at an indexed ID/class without visiting the page.
    // :scope (and its nesting alias &) in matches() is relative to each candidate;
    // escaped selectors may spell :scope too, so retain the walker for those.
    if (typeof sel === 'string' && !/\\|&|:scope\b|:host\b/i.test(sel)) {
      const select = root.nodeType === 9 ? documentQuery : root.nodeType === 11 ? fragmentQuery : elementQuery;
      const found = select.call(root, sel);
      if (found) return found;
      // This root was searched completely; embedded roots follow depth-first,
      // in the same order as nodesInRoots. No retained querySelectorAll list.
      for (const el of elements(root)) {
        const child = el.shadowRoot || el.contentDocument;
        if (child) {
          const found = query(child, sel);
          if (found) return found;
        }
      }
      return null;
    }
    for (const el of matching(root, sel)) return el;
    return null;
  }

  // Resolve {ref} or {selector} to one element, or null when the selector
  // matches nothing yet. Stale refs and missing params throw at once.
  function lookup(p) {
    if (p.ref) {
      const el = refElement(p.ref);
      if (!connected(el)) throw new Error(`stale or unknown ref '${p.ref}', take a new snapshot`);
      return el;
    }
    if (!p.selector) throw new Error('need params.selector or params.ref');
    return query(document, p.selector);
  }

  function find(p) {
    const el = lookup(p);
    if (!el) throw new Error(`no element matches '${p.selector}'`);
    return el;
  }

  // Why an element cannot be acted on right now, or null.
  function blocker(el, needEnabled) {
    if (!connected(el)) return 'detached';
    if (!visible(el)) return 'not visible';
    if (needEnabled && el.matches(':disabled')) return 'disabled';
    el.scrollIntoView({ block: 'center', inline: 'center' });
    const r = el.getBoundingClientRect();
    // No box, nothing can cover it (empty contenteditable, text without fonts).
    if (!r.width || !r.height) return null;
    const x = r.x + r.width / 2, y = r.y + r.height / 2;
    let hit = el.getRootNode().elementFromPoint(x, y);
    // Document hit testing retargets shadow descendants to their host. Descend
    // open roots before deciding whether a slotted control is covered.
    while (hit?.shadowRoot) {
      const inner = hit.shadowRoot.elementFromPoint(x, y);
      if (!inner || inner === hit) break;
      hit = inner;
    }
    if (!hit) return 'outside the viewport';
    for (let node = hit; node; node = composedParent(node)) if (node === el) return null;
    // An ancestor hit is not enough: pointer-events:none falls through to it.
    return `covered by ${describe(hit)}`;
  }

  // Waits until the target exists, is visible, enabled, in view and not
  // covered, like Playwright's actionability checks. `force` skips the
  // checks but still waits for the element to appear.
  async function actionable(p, needEnabled = true, signal) {
    const deadline = Date.now() + (p.timeout || ACTION_TIMEOUT_MS);
    for (;;) {
      checkCancelled(signal);
      const el = lookup(p);
      const why = el ? (p.force ? null : blocker(el, needEnabled)) : `no element matches '${p.selector}'`;
      if (!why) return el;
      if (Date.now() > deadline) throw new Error(el ? `${describe(el)} is ${why}` : why);
      await changed(el, signal);
    }
  }

  function roleOf(el) {
    const explicit = el.getAttribute('role');
    if (explicit) return explicit;
    const tag = el.tagName.toLowerCase();
    if (tag === 'input') return INPUT_ROLE[el.type] || 'textbox';
    if (tag === 'select') return el.multiple ? 'listbox' : 'combobox';
    if (el.isContentEditable) return 'textbox';
    return TAG_ROLE[tag] || 'generic';
  }

  function nameOf(el, readText) {
    const aria = el.getAttribute('aria-label');
    if (aria) return trunc(aria, NAME_MAX);
    const labelled = el.getAttribute('aria-labelledby');
    // ID references stay in the control's tree, even when it is slotted.
    if (labelled) return trunc(readText(el.getRootNode().getElementById(labelled)), NAME_MAX);
    if (el.labels && el.labels.length) return trunc(readText(el.labels[0]), NAME_MAX);
    // An image link is named by its alt. A value is only a name on button-like inputs.
    const img = el.tagName === 'A' && el.querySelector('img[alt]');
    const buttonValue = INPUT_ROLE[el.type] === 'button' && el.value;
    return trunc(el.alt || el.placeholder || el.title || readText(el) || (img && img.alt) || buttonValue, NAME_MAX);
  }

  const editable = (el) => el.isContentEditable || el.matches('input,textarea');
  const assertEditable = (el) => { if (!editable(el)) throw new Error(`${describe(el)} is not editable`); };

  // Right after a load starts, the document has a head but no body yet.
  // XML and JSON documents never get one: fall back to the root once parsed.
  async function body(signal) {
    const deadline = Date.now() + ACTION_TIMEOUT_MS;
    while (!document.body) {
      if (document.readyState !== 'loading') return document.documentElement;
      if (Date.now() > deadline) throw new Error('page has no body yet, still loading');
      await changed(undefined, signal);
    }
    return document.body;
  }

  // React and friends swallow plain `.value = x`; go through the prototype setter.
  // contenteditable has no value, its text is the content.
  function setValue(el, value) {
    if (el.isContentEditable) {
      el.textContent = value;
    } else {
      const proto = Object.getPrototypeOf(el);
      const desc = Object.getOwnPropertyDescriptor(proto, 'value');
      if (desc && desc.set) desc.set.call(el, value);
      else el.value = value;
    }
    el.dispatchEvent(new Event('input', { bubbles: true, composed: true }));
  }

  const valueOf = (el) => (el.isContentEditable ? el.textContent : el.value) || '';

  function mouse(el, type, x, y) {
    // Unlike click/over events, mouseenter neither bubbles nor crosses roots.
    const enter = type === 'mouseenter';
    el.dispatchEvent(new MouseEvent(type, { bubbles: !enter, cancelable: !enter, composed: !enter, view: window, clientX: x, clientY: y }));
  }

  // jQuery `event.which` and React `keyCode === 13` sites need the legacy codes.
  // ponytail: punctuation gets its char code, add a map if a site needs the exact legacy value.
  function keyCodeOf(k) {
    if (KEY_CODES[k]) return KEY_CODES[k];
    const f = /^F(\d+)$/.exec(k);
    if (f) return F_KEY_BASE + Number(f[1]);
    return k.length === 1 ? k.toUpperCase().charCodeAt(0) : 0;
  }

  function codeOf(k) {
    if (/^[a-z]$/i.test(k)) return 'Key' + k.toUpperCase();
    if (/^\d$/.test(k)) return 'Digit' + k;
    if (k === ' ') return 'Space';
    return k.length === 1 ? '' : k;
  }

  // "Control+Shift+k" -> KeyboardEvent init. Single characters pass through
  // untouched so typing "+" works.
  function keyInit(combo) {
    const parts = combo.length === 1 ? [combo] : combo.split('+');
    const k = parts.pop();
    const mods = new Set(parts.map((m) => m.toLowerCase()));
    const keyCode = keyCodeOf(k);
    return {
      key: k, code: codeOf(k), keyCode, which: keyCode,
      ctrlKey: mods.has('control') || mods.has('ctrl'), shiftKey: mods.has('shift') || /^[A-Z]$/.test(k),
      altKey: mods.has('alt'), metaKey: mods.has('meta') || mods.has('cmd'),
    };
  }

  function key(el, type, k) {
    return el.dispatchEvent(new KeyboardEvent(type, { ...keyInit(k), bubbles: true, cancelable: true, composed: true }));
  }

  // One keystroke. A printable key inserts its character into an editable
  // target; Enter submits the form. Neither happens on its own for synthetic events.
  function pressOn(el, k) {
    const notPrevented = key(el, 'keydown', k);
    if (notPrevented && k.length === 1 && editable(el)) setValue(el, valueOf(el) + k);
    key(el, 'keyup', k);
    if (k === 'Enter' && notPrevented && el.form) el.form.requestSubmit();
  }

  function clickOn(el, x, y) {
    el.focus();
    mouse(el, 'pointerdown', x, y);
    mouse(el, 'mousedown', x, y);
    mouse(el, 'pointerup', x, y);
    mouse(el, 'mouseup', x, y);
    mouse(el, 'click', x, y);
  }

  function center(el) {
    const r = el.getBoundingClientRect();
    return [r.x + r.width / 2, r.y + r.height / 2];
  }

  // Elements matching SNAPSHOT_TAGS plus bare text nodes (a <div>Saved!</div>
  // has no role but is what the agent needs to read), in document order,
  // through open shadow roots and same-origin frames.
  function* nodes(root) {
    for (const node of nodesInRoots(root, SHOW_ELEMENT_AND_TEXT)) {
      if (node.nodeType === TEXT_NODE) {
        const parent = node.parentElement;
        if (node.data.trim() && parent && !parent.closest(TEXT_OWNERS)) yield { el: parent, text: node.data };
      } else if (node.matches(SNAPSHOT_TAGS)) {
        yield { el: node };
      }
    }
  }

  // Flat list of visible, meaningful elements under root. Refs are reusable
  // in other methods. `match` filters, `max` caps, `boxes` adds rects.
  function collect(root, p, match) {
    refs = new Map();
    const max = p.max ?? SNAPSHOT_MAX;
    const out = [];
    const details = new WeakMap(), hidden = new WeakMap(), texts = new WeakMap();
    const readText = (el) => {
      if (!el) return '';
      let value = texts.get(el);
      if (value === undefined) { value = el.innerText || ''; texts.set(el, value); }
      return value;
    };
    let n = 0;
    let truncated = false;

    for (const { el, text } of nodes(root)) {
      if (!visible(el, details) || ancestorFlag(el, domParent, ariaHidden, hidden)) continue;

      const role = text ? 'text' : roleOf(el);
      const textRole = role === 'text' || role === 'listitem' || role === 'cell';
      const item = { ref: `e${n + 1}`, role };
      if (text) item.text = trunc(text, TEXT_MAX);
      else if (!textRole) item.name = nameOf(el, readText);
      const tag = el.tagName.toLowerCase();
      if (!text) {
        if (tag === 'a' && el.href) item.href = el.href;
        if ('value' in el && el.value && tag !== 'button') item.value = trunc(el.value, NAME_MAX);
        if (el.type === 'checkbox' || el.type === 'radio') item.checked = el.checked;
        if (el.matches(':disabled')) item.disabled = true;
        if (textRole) {
          item.text = trunc(readText(el), TEXT_MAX);
          if (!item.text) continue;
          // <li><a>Docs</a></li>: the link carries the text, listing the li
          // too would put a non-clickable twin first in the results.
          if (wrapsOne(el, readText)) continue;
        }
      }
      if (match && !match(item)) continue;
      if (p.boxes) {
        const r = el.getBoundingClientRect();
        item.box = { x: Math.round(r.x), y: Math.round(r.y), width: Math.round(r.width), height: Math.round(r.height) };
      }
      if (out.length >= max) { truncated = true; break; }

      n++;
      const stored = WeakReference ? new WeakReference(el) : {};
      if (!WeakReference) refTokens.set(el, stored);
      refs.set(item.ref, stored);
      out.push(item);
    }

    const result = { url: location.href, title: document.title, elements: out };
    if (truncated) result.truncated = true;
    prefetchHosts(out);
    return p.format === 'text' ? asText(result) : result;
  }

  // The agent's next navigate is likely one of these links: warm their DNS.
  function prefetchHosts(items) {
    const hosts = new Set();
    for (const e of items) {
      if (!e.href || !/^https?:/.test(e.href)) continue;
      const host = new URL(e.href).hostname;
      if (host !== location.hostname) hosts.add(host);
      if (hosts.size >= PREFETCH_HOSTS_MAX) break;
    }
    if (hosts.size) post({ prefetch: [...hosts] });
  }

  function wrapsOne(el, readText) {
    let only = null;
    for (const kid of elements(el)) {
      if (!kid.matches(SNAPSHOT_TAGS)) continue;
      if (only) return false;
      only = kid;
    }
    return !!only && readText(only).trim() === readText(el).trim();
  }

  // One line per element, about 40% fewer bytes than JSON and the form the
  // model reads anyway:  e7 link "Learn more" href=/help
  // Same-origin hrefs lose the origin; the url is on the first line.
  function asText(snap) {
    const lines = [snap.url, snap.title];
    for (const e of snap.elements) {
      let s = `${e.ref} ${e.role}`;
      if (e.name) s += ' ' + stringify(e.name);
      if (e.text) s += ' ' + stringify(e.text);
      if (e.href) s += ' href=' + (e.href.startsWith(location.origin) ? e.href.slice(location.origin.length) : e.href);
      if (e.value && !('checked' in e && e.value === 'on')) s += ' value=' + stringify(e.value);
      if ('checked' in e) s += ' checked=' + e.checked;
      if (e.disabled) s += ' disabled';
      if (e.box) s += ` box=${e.box.x},${e.box.y},${e.box.width},${e.box.height}`;
      lines.push(s);
    }
    if (snap.truncated) lines.push('(truncated, raise max or scope with selector)');
    return lines.join('\n');
  }

  const methods = {
    // Native WebView2 Source can lag behind a just-completed pushState action.
    url: () => location.href,
    // `eval` is compiled by Rust into a function so page CSP cannot refuse it;
    // see evalFn below. This just awaits it.
    __fn(fn) {
      return fn();
    },

    title() {
      return document.title;
    },

    text(p) {
      return trunc(find(p).innerText, p.max || Infinity);
    },

    html(p) {
      return find(p).outerHTML;
    },

    attr(p) {
      if (!p.name) throw new Error('attr: need params.name');
      return find(p).getAttribute(p.name);
    },

    count({ selector }) {
      let count = 0;
      for (const el of matching(document, selector)) count++;
      return count;
    },

    // Viewport-relative box, for screenshot clips.
    rect(p) {
      const r = find(p).getBoundingClientRect();
      return { x: Math.round(r.x), y: Math.round(r.y), width: Math.round(r.width), height: Math.round(r.height) };
    },

    network(p) {
      if (p.bodies !== undefined) {
        captureBodies = p.bodies !== false;
        if (!captureBodies) for (const stop of captures) stop();
      }
      const perf = performance.getEntriesByType('resource')
        .filter((e) => e.initiatorType !== 'fetch' && e.initiatorType !== 'xmlhttprequest')
        .map((e) => ({ type: e.initiatorType, url: e.name, ms: Math.round(e.duration) }));
      const out = net.map(({ start, req_headers, res_headers, body, ...e }, index) => ({ index, ...e })).concat(perf);
      if (p.clear) clearNetwork();
      return out;
    },

    // Headers and body prefix of one fetch/xhr entry, by index from `network`.
    network_request(p) {
      const e = net[p.index];
      if (!e) throw new Error(`no fetch/xhr entry ${p.index}`);
      const { start, ...rest } = e;
      return rest;
    },

    console(p) {
      const out = consoleLog.slice();
      if (p.clear) consoleLog.length = 0;
      return out;
    },

    dialog(p) {
      if (p.accept !== undefined || p.text !== undefined) dialogAnswer = { accept: p.accept !== false, text: compact((p.text || '').slice(0, LOG_MAX)) };
      const out = dialogs.slice();
      if (p.clear) { dialogs.length = 0; dialogBytes = 0; }
      return out;
    },

    async click(p, signal) {
      if (p.x !== undefined && p.y !== undefined && !p.selector && !p.ref) {
        const el = document.elementFromPoint(p.x, p.y);
        if (!el) throw new Error(`nothing at ${p.x},${p.y}`);
        clickOn(el, p.x, p.y);
        return null;
      }
      const el = await actionable(p, true, signal);
      clickOn(el, ...center(el));
      return null;
    },

    async hover(p, signal) {
      const el = await actionable(p, false, signal);
      const [x, y] = center(el);
      mouse(el, 'pointerover', x, y);
      mouse(el, 'mouseover', x, y);
      mouse(el, 'mouseenter', x, y);
      return null;
    },

    async fill(p, signal) {
      const el = await actionable(p, true, signal);
      assertEditable(el);
      el.focus();
      setValue(el, p.value);
      el.dispatchEvent(new Event('change', { bubbles: true }));
      return null;
    },

    // Types one character at a time so per-key handlers fire. Number inputs
    // sanitise on every write ("-1." becomes ""), so the typed text is kept
    // aside and letters are dropped, as a browser would.
    async type(p, signal) {
      const el = await actionable(p, true, signal);
      assertEditable(el);
      el.focus();
      const number = el.type === 'number';
      let typed = valueOf(el);
      for (const ch of p.text) {
        checkCancelled(signal);
        if (number && !NUMBER_CHARS.test(ch)) continue;
        key(el, 'keydown', ch);
        key(el, 'keypress', ch);
        typed += ch;
        setValue(el, typed);
        key(el, 'keyup', ch);
        if (p.delay) await sleep(p.delay, signal);
      }
      if (p.submit) pressOn(el, 'Enter');
      return null;
    },

    async press(p, signal) {
      const el = p.selector || p.ref ? await actionable(p, true, signal) : document.activeElement || document.body;
      pressOn(el, p.key);
      return null;
    },

    async select(p, signal) {
      const el = await actionable(p, true, signal);
      if (el.tagName !== 'SELECT') throw new Error(`${describe(el)} is not a select`);
      const wanted = [].concat(p.value);
      const options = [...el.options];
      const miss = wanted.find((w) => !options.some((o) => o.value === w || o.text === w));
      if (miss !== undefined) throw new Error(`no option matches '${miss}' in ${describe(el)}`);
      for (const o of options) o.selected = wanted.includes(o.value) || wanted.includes(o.text);
      el.dispatchEvent(new Event('input', { bubbles: true, composed: true }));
      el.dispatchEvent(new Event('change', { bubbles: true }));
      return [...el.selectedOptions].map((o) => o.value);
    },

    async check(p, signal) {
      const el = await actionable(p, true, signal);
      if (el.type !== 'checkbox' && el.type !== 'radio') throw new Error(`${describe(el)} is not a checkbox or radio, use click`);
      const want = p.checked !== false;
      if (el.checked !== want) el.click();
      return el.checked;
    },

    // One call for a whole form. Each field is a target plus `value`;
    // checkboxes take a boolean, selects a value or array.
    async fill_form(p, signal) {
      for (const f of p.fields) {
        checkCancelled(signal);
        const el = find(f);
        if (el.type === 'checkbox' || el.type === 'radio') await methods.check({ ...f, checked: !!f.value }, signal);
        else if (el.tagName === 'SELECT') await methods.select(f, signal);
        else await methods.fill(f, signal);
      }
      return null;
    },

    // HTML5 drag and drop with a shared DataTransfer, from one target to another.
    async drag(p, signal) {
      const from = await actionable(p.from || {}, true, signal);
      const to = await actionable(p.to || {}, false, signal);
      const dt = new DataTransfer();
      const ev = (el, type) => el.dispatchEvent(new DragEvent(type, { bubbles: true, cancelable: true, dataTransfer: dt }));
      mouse(from, 'pointerdown', ...center(from));
      mouse(from, 'mousedown', ...center(from));
      ev(from, 'dragstart');
      ev(to, 'dragenter');
      ev(to, 'dragover');
      ev(to, 'drop');
      ev(from, 'dragend');
      mouse(to, 'pointerup', ...center(to));
      mouse(to, 'mouseup', ...center(to));
      return null;
    },

    // Rust reads the files and passes them in as {name, type, data: base64}.
    // File inputs are often hidden, so no visibility check here.
    upload(p) {
      const el = find(p);
      if (el.tagName !== 'INPUT' || el.type !== 'file') throw new Error(`${describe(el)} is not a file input`);
      const dt = new DataTransfer();
      for (const f of p.files) {
        // Decode in blocks instead of materializing a second full binary string.
        const padding = f.data.endsWith('==') ? 2 : f.data.endsWith('=') ? 1 : 0;
        const bytes = new Uint8Array(f.data.length / 4 * 3 - padding);
        for (let at = 0, to = 0; at < f.data.length; at += 32768) {
          const block = atob(f.data.slice(at, at + 32768));
          for (let i = 0; i < block.length; i++) bytes[to++] = block.charCodeAt(i);
        }
        dt.items.add(new File([bytes], f.name, { type: f.type }));
      }
      el.files = dt.files;
      el.dispatchEvent(new Event('input', { bubbles: true, composed: true }));
      el.dispatchEvent(new Event('change', { bubbles: true }));
      return [...el.files].map((f) => f.name);
    },

    scroll(p) {
      if (p.selector || p.ref) find(p).scrollIntoView({ block: 'center' });
      else window.scrollBy(p.x || 0, p.y || 0);
      return { x: window.scrollX, y: window.scrollY };
    },

    // Waits until a condition holds: selector/ref state, text present or gone,
    // url substring, network idle, or just `time` ms.
    async wait_for(p, signal) {
      if (p.time) {
        await sleep(p.time, signal);
        return null;
      }
      if (!['url', 'text', 'textGone', 'idle', 'ref', 'selector'].some((k) => p[k] !== undefined)) {
        throw new Error('wait_for: need selector, ref, text, textGone, url, idle or time');
      }
      const timeout = p.timeout || DEFAULT_TIMEOUT_MS;
      const state = p.state || 'visible';
      const deadline = Date.now() + timeout;
      let idleSince = null;
      let target = null;
      const pageText = () => (document.body ? document.body.innerText : '');

      const check = () => {
        if (p.url !== undefined) return location.href.includes(p.url);
        if (p.text !== undefined) return pageText().includes(p.text);
        if (p.textGone !== undefined) return !pageText().includes(p.textGone);
        if (p.idle) {
          if (inflight) { idleSince = null; return false; }
          idleSince = idleSince || Date.now();
          return Date.now() - idleSince >= IDLE_MS;
        }
        const el = target = p.ref ? refElement(p.ref) : query(document, p.selector);
        const attached = connected(el);
        if (state === 'attached') return attached;
        if (state === 'hidden') return !attached || !visible(el);
        return attached && visible(el);
      };

      while (!check()) {
        checkCancelled(signal);
        if (Date.now() > deadline) throw new Error(`wait_for timed out after ${timeout}ms: ${stringify(p)}`);
        if (p.idle || p.url !== undefined) await sleep(POLL_MS, signal);
        else await changed(target, signal);
      }
      return null;
    },

    async snapshot(p, signal) {
      return collect(p.selector ? find(p) : await body(signal), p);
    },

    // Snapshot narrowed to elements whose name, text, value or href contains
    // `text` or matches `regex`. Hands out fresh refs like snapshot does.
    async find(p, signal) {
      const re = p.regex ? new RegExp(p.regex, 'i') : null;
      const needle = (p.text || '').toLowerCase();
      // Each field on its own, so ^...$ anchors work on a link with an href.
      const match = (item) => [item.name, item.text, item.value, item.href].filter(Boolean)
        .some((f) => (re ? re.test(f) : f.toLowerCase().includes(needle)));
      return collect(p.selector ? find(p) : await body(signal), p, match);
    },
  };

  const calls = new Map();
  function cancel(id, attempt) {
    const call = calls.get(id);
    if (call && (!attempt || attempt === call.attempt)) call.controller.abort();
  }
  async function run(id, method, params, attempt) {
    cancel(id, 0);
    const call = { attempt, controller: new AbortController() };
    calls.set(id, call);
    const signal = call.controller.signal;
    navExpected = false;
    try {
      const fn = methods[method];
      if (!fn) throw new Error(`unknown method '${method}'`);
      let abort;
      const stopped = new Promise((_, reject) => {
        abort = () => reject(new Error('request cancelled'));
        signal.addEventListener('abort', abort, { once: true });
      });
      let result;
      try {
        const operation = fn(params || {}, signal);
        params = null;
        result = await Promise.race([operation, stopped]);
      } finally { signal.removeEventListener('abort', abort); }
      checkCancelled(signal);
      if (result === undefined) result = null;
      const reply = navExpected ? { id, attempt, result, navigating: true } : { id, attempt, result };
      try {
        post(reply);
      } catch {
        post({ ...reply, result: String(result) }); // not JSON-safe (DOM node, cycle)
      }
    } catch (e) {
      if (!signal.aborted) post({ id, attempt, error: String((e && e.message) || e) });
    } finally {
      if (calls.get(id) === call) calls.delete(id);
    }
  }

  // Rust wraps the agent's expression in an async function and passes it
  // here, so the source is compiled as script, not through eval().
  const evalFn = (id, fn, attempt) => run(id, '__fn', fn, attempt);

  window.addEventListener('pagehide', () => {
    clearNetwork();
    refs.clear();
    for (const call of calls.values()) call.controller.abort();
  });

  window.__bruster = { run, evalFn, bind, cancel, document: documentId, get generation() { return generation; } };
  if (window.top === window) bind(0);
})();
