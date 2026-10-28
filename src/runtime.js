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
  const CONSOLE_MAX = 500;
  const LOG_MAX = 1000;

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

  // Pages can replace JSON.stringify after injection; IPC must still work.
  const stringify = JSON.stringify.bind(JSON);
  const documentId = `${performance.timeOrigin}:${Math.random()}`;
  let generation = 0;
  const post = (msg) => window.ipc.postMessage(stringify({ ...msg, document: documentId, generation }));
  const trunc = (s, n) => (s = (s || '').replace(/\s+/g, ' ').trim()).length > n ? s.slice(0, n) + '…' : s;
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  const fmt = (v) => {
    if (typeof v === 'string') return v;
    if (v instanceof Error) {
      // WebKit stacks contain frames without the error's name/message.
      const message = String(v), stack = typeof v.stack === 'string' ? v.stack : '';
      return stack.includes(message) ? stack : message + (stack ? '\n' + stack : '');
    }
    try { return stringify(v); } catch { return String(v); }
  };

  // Request log. Patched fetch/XHR give status, headers and a body prefix;
  // the page's own loads (img, script, css) come from the Performance API.
  // Cleared on navigation by virtue of living in the page.
  const net = [];
  let inflight = 0;
  const logNet = (e) => { if (net.length < NET_MAX) net.push(e); };
  const headersOf = (h) => { try { return Object.fromEntries(new Headers(h)); } catch { return {}; } };

  const origFetch = window.fetch;
  window.fetch = async function (input, init) {
    const url = typeof input === 'string' ? input : input.url;
    const entry = {
      type: 'fetch', method: (init && init.method) || (input && input.method) || 'GET', url: new URL(url, location.href).href,
      start: performance.now(), req_headers: headersOf((init && init.headers) || (input && input.headers)),
    };
    logNet(entry);
    inflight++;
    try {
      const res = await origFetch.apply(this, arguments);
      entry.status = res.status;
      entry.ms = Math.round(performance.now() - entry.start);
      entry.res_headers = Object.fromEntries(res.headers);
      res.clone().text().then((t) => { entry.body = t.slice(0, BODY_MAX); }).catch(() => {});
      return res;
    } catch (e) {
      entry.error = String(e);
      entry.ms = Math.round(performance.now() - entry.start);
      throw e;
    } finally {
      inflight--;
      resourceDone();
    }
  };

  const xhrOpen = XMLHttpRequest.prototype.open;
  const xhrSend = XMLHttpRequest.prototype.send;
  XMLHttpRequest.prototype.open = function (method, url) {
    const entry = { type: 'xhr', method, url: new URL(url, location.href).href, start: performance.now() };
    logNet(entry);
    this.addEventListener('loadend', () => {
      entry.status = this.status;
      entry.ms = Math.round(performance.now() - entry.start);
      entry.res_headers = Object.fromEntries(this.getAllResponseHeaders().trim().split(/\r?\n/).filter(Boolean).map((l) => {
        const i = l.indexOf(':');
        return [l.slice(0, i), l.slice(i + 1).trim()];
      }));
      if (this.responseType === '' || this.responseType === 'text') entry.body = this.responseText.slice(0, BODY_MAX);
    });
    return xhrOpen.apply(this, arguments);
  };
  XMLHttpRequest.prototype.send = function () {
    inflight++;
    this.addEventListener('loadend', () => { inflight--; resourceDone(); }, { once: true });
    return xhrSend.apply(this, arguments);
  };

  // Console and page errors, readable through `console`.
  const consoleLog = [];
  const logConsole = (level, text) => {
    if (consoleLog.length < CONSOLE_MAX) consoleLog.push({ level, text: text.slice(0, LOG_MAX), ms: Math.round(performance.now()) });
  };
  for (const level of ['log', 'info', 'warn', 'error', 'debug']) {
    const orig = console[level];
    console[level] = function (...args) {
      logConsole(level, args.map(fmt).join(' '));
      return orig.apply(this, args);
    };
  }
  window.addEventListener('error', (e) => logConsole('error', e.message + (e.filename ? ` (${e.filename}:${e.lineno})` : '')));
  window.addEventListener('unhandledrejection', (e) => logConsole('error', 'Unhandled rejection: ' + fmt(e.reason)));

  // Native alert/confirm/prompt would block the page and every later call.
  // Answer them here with the last `dialog` setting and tell the agent.
  let dialogAnswer = { accept: true, text: '' };
  const dialogs = [];
  const onDialog = (type, message, def) => {
    const d = { type, message: String(message), accept: dialogAnswer.accept };
    dialogs.push(d);
    post({ event: 'dialog', ...d });
    if (type === 'prompt') return d.accept ? (dialogAnswer.text || def || '') : null;
    return type === 'confirm' ? d.accept : undefined;
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
  function visible(el) {
    // Opacity-zero targets still receive pointer events. visibility:hidden does
    // not, unless a descendant explicitly overrides the inherited visibility.
    if (getComputedStyle(el).visibility !== 'visible') return false;
    if (el.checkVisibility && !el.checkVisibility({ checkVisibilityCSS: true })) return false;
    // Older WKWebView versions report layout boxes for closed details content.
    // Only the first summary (and its composed descendants) is rendered there.
    for (let child = el, parent = composedParent(child); parent; child = parent, parent = composedParent(child)) {
      if (parent.tagName === 'DETAILS' && !parent.open
          && child !== [...parent.children].find(node => node.tagName === 'SUMMARY')) return false;
    }
    return el.getClientRects().length > 0;
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
  // ponytail: scans every element per query, fine at agent call rates.
  function* elements(root) {
    const walker = (root.ownerDocument || root).createTreeWalker(root, NodeFilter.SHOW_ELEMENT);
    for (let el = walker.nextNode(); el; el = walker.nextNode()) yield el;
  }
  function roots(root, out = []) {
    out.push(root);
    for (const el of elements(root)) {
      if (el.shadowRoot) roots(el.shadowRoot, out);
      else if (el.contentDocument) roots(el.contentDocument, out);
    }
    return out;
  }
  // `matches` throws the same error as querySelector on a bad selector.
  function* matching(root, sel) {
    for (const r of roots(root)) {
      for (const el of elements(r)) if (el.matches(sel)) yield el;
    }
  }
  const queryAll = (root, sel) => [...matching(root, sel)];
  function query(root, sel) {
    for (const el of matching(root, sel)) return el;
    return null;
  }

  // Resolve {ref} or {selector} to one element, or null when the selector
  // matches nothing yet. Stale refs and missing params throw at once.
  function lookup(p) {
    if (p.ref) {
      const el = refs.get(p.ref);
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
  async function actionable(p, needEnabled = true) {
    const deadline = Date.now() + (p.timeout || ACTION_TIMEOUT_MS);
    for (;;) {
      const el = lookup(p);
      const why = el ? (p.force ? null : blocker(el, needEnabled)) : `no element matches '${p.selector}'`;
      if (!why) return el;
      if (Date.now() > deadline) throw new Error(el ? `${describe(el)} is ${why}` : why);
      await sleep(POLL_MS);
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

  function nameOf(el) {
    const aria = el.getAttribute('aria-label');
    if (aria) return trunc(aria, NAME_MAX);
    const labelled = el.getAttribute('aria-labelledby');
    if (labelled) return trunc(el.ownerDocument.getElementById(labelled)?.innerText, NAME_MAX);
    if (el.labels && el.labels.length) return trunc(el.labels[0].innerText, NAME_MAX);
    // An image link is named by its alt. A value is only a name on button-like inputs.
    const img = el.tagName === 'A' && el.querySelector('img[alt]');
    const buttonValue = INPUT_ROLE[el.type] === 'button' && el.value;
    return trunc(el.alt || el.placeholder || el.title || el.innerText || (img && img.alt) || buttonValue, NAME_MAX);
  }

  const editable = (el) => el.isContentEditable || el.matches('input,textarea');
  const assertEditable = (el) => { if (!editable(el)) throw new Error(`${describe(el)} is not editable`); };

  // Right after a load starts, the document has a head but no body yet.
  // XML and JSON documents never get one: fall back to the root once parsed.
  async function body() {
    const deadline = Date.now() + ACTION_TIMEOUT_MS;
    while (!document.body) {
      if (document.readyState !== 'loading') return document.documentElement;
      if (Date.now() > deadline) throw new Error('page has no body yet, still loading');
      await sleep(POLL_MS);
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
    el.dispatchEvent(new Event('input', { bubbles: true }));
  }

  const valueOf = (el) => (el.isContentEditable ? el.textContent : el.value) || '';

  function mouse(el, type, x, y) {
    el.dispatchEvent(new MouseEvent(type, { bubbles: true, cancelable: true, view: window, clientX: x, clientY: y }));
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
    return el.dispatchEvent(new KeyboardEvent(type, { ...keyInit(k), bubbles: true, cancelable: true }));
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
    for (const r of roots(root)) {
      const walker = (r.ownerDocument || r).createTreeWalker(r, SHOW_ELEMENT_AND_TEXT);
      for (let node = walker.nextNode(); node; node = walker.nextNode()) {
        if (node.nodeType === TEXT_NODE) {
          const parent = node.parentElement;
          if (node.data.trim() && parent && !parent.closest(TEXT_OWNERS)) yield { el: parent, text: node.data };
        } else if (node.matches(SNAPSHOT_TAGS)) {
          yield { el: node };
        }
      }
    }
  }

  // Flat list of visible, meaningful elements under root. Refs are reusable
  // in other methods. `match` filters, `max` caps, `boxes` adds rects.
  function collect(root, p, match) {
    refs = new Map();
    const max = p.max ?? SNAPSHOT_MAX;
    const out = [];
    let n = 0;
    let truncated = false;

    for (const { el, text } of nodes(root)) {
      if (!visible(el) || el.closest('[aria-hidden="true"]')) continue;

      const item = text ? { ref: `e${n + 1}`, role: 'text', text: trunc(text, TEXT_MAX) } : { ref: `e${n + 1}`, role: roleOf(el), name: nameOf(el) };
      const tag = el.tagName.toLowerCase();
      if (!text) {
        if (tag === 'a' && el.href) item.href = el.href;
        if ('value' in el && el.value && tag !== 'button') item.value = trunc(el.value, NAME_MAX);
        if (el.type === 'checkbox' || el.type === 'radio') item.checked = el.checked;
        if (el.matches(':disabled')) item.disabled = true;
        if (item.role === 'text' || item.role === 'listitem' || item.role === 'cell') {
          item.text = trunc(el.innerText, TEXT_MAX);
          delete item.name;
          if (!item.text) continue;
          // <li><a>Docs</a></li>: the link carries the text, listing the li
          // too would put a non-clickable twin first in the results.
          if (wrapsOne(el)) continue;
        }
      }
      if (match && !match(item)) continue;
      if (p.boxes) {
        const r = el.getBoundingClientRect();
        item.box = { x: Math.round(r.x), y: Math.round(r.y), width: Math.round(r.width), height: Math.round(r.height) };
      }
      if (out.length >= max) { truncated = true; break; }

      n++;
      refs.set(item.ref, el);
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
      const host = new URL(e.href).host;
      if (host !== location.host) hosts.add(host);
      if (hosts.size >= PREFETCH_HOSTS_MAX) break;
    }
    if (hosts.size) post({ prefetch: [...hosts] });
  }

  function wrapsOne(el) {
    let only = null;
    for (const kid of elements(el)) {
      if (!kid.matches(SNAPSHOT_TAGS)) continue;
      if (only) return false;
      only = kid;
    }
    return !!only && only.innerText.trim() === el.innerText.trim();
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
      return queryAll(document, selector).length;
    },

    // Viewport-relative box, for screenshot clips.
    rect(p) {
      const r = find(p).getBoundingClientRect();
      return { x: Math.round(r.x), y: Math.round(r.y), width: Math.round(r.width), height: Math.round(r.height) };
    },

    network(p) {
      const perf = performance.getEntriesByType('resource')
        .filter((e) => e.initiatorType !== 'fetch' && e.initiatorType !== 'xmlhttprequest')
        .map((e) => ({ type: e.initiatorType, url: e.name, ms: Math.round(e.duration) }));
      const out = net.map(({ start, req_headers, res_headers, body, ...e }, index) => ({ index, ...e })).concat(perf);
      if (p.clear) { net.length = 0; performance.clearResourceTimings(); }
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
      if (p.accept !== undefined || p.text !== undefined) dialogAnswer = { accept: p.accept !== false, text: p.text || '' };
      const out = dialogs.slice();
      if (p.clear) dialogs.length = 0;
      return out;
    },

    async click(p) {
      if (p.x !== undefined && p.y !== undefined && !p.selector && !p.ref) {
        const el = document.elementFromPoint(p.x, p.y);
        if (!el) throw new Error(`nothing at ${p.x},${p.y}`);
        clickOn(el, p.x, p.y);
        return null;
      }
      const el = await actionable(p);
      clickOn(el, ...center(el));
      return null;
    },

    async hover(p) {
      const el = await actionable(p, false);
      const [x, y] = center(el);
      mouse(el, 'pointerover', x, y);
      mouse(el, 'mouseover', x, y);
      mouse(el, 'mouseenter', x, y);
      return null;
    },

    async fill(p) {
      const el = await actionable(p);
      assertEditable(el);
      el.focus();
      setValue(el, p.value);
      el.dispatchEvent(new Event('change', { bubbles: true }));
      return null;
    },

    // Types one character at a time so per-key handlers fire. Number inputs
    // sanitise on every write ("-1." becomes ""), so the typed text is kept
    // aside and letters are dropped, as a browser would.
    async type(p) {
      const el = await actionable(p);
      assertEditable(el);
      el.focus();
      const number = el.type === 'number';
      let typed = valueOf(el);
      for (const ch of p.text) {
        if (number && !NUMBER_CHARS.test(ch)) continue;
        key(el, 'keydown', ch);
        key(el, 'keypress', ch);
        typed += ch;
        setValue(el, typed);
        key(el, 'keyup', ch);
        if (p.delay) await sleep(p.delay);
      }
      if (p.submit) pressOn(el, 'Enter');
      return null;
    },

    async press(p) {
      const el = p.selector || p.ref ? await actionable(p) : document.activeElement || document.body;
      pressOn(el, p.key);
      return null;
    },

    async select(p) {
      const el = await actionable(p);
      if (el.tagName !== 'SELECT') throw new Error(`${describe(el)} is not a select`);
      const wanted = [].concat(p.value);
      const options = [...el.options];
      const miss = wanted.find((w) => !options.some((o) => o.value === w || o.text === w));
      if (miss !== undefined) throw new Error(`no option matches '${miss}' in ${describe(el)}`);
      for (const o of options) o.selected = wanted.includes(o.value) || wanted.includes(o.text);
      el.dispatchEvent(new Event('input', { bubbles: true }));
      el.dispatchEvent(new Event('change', { bubbles: true }));
      return [...el.selectedOptions].map((o) => o.value);
    },

    async check(p) {
      const el = await actionable(p);
      if (el.type !== 'checkbox' && el.type !== 'radio') throw new Error(`${describe(el)} is not a checkbox or radio, use click`);
      const want = p.checked !== false;
      if (el.checked !== want) el.click();
      return el.checked;
    },

    // One call for a whole form. Each field is a target plus `value`;
    // checkboxes take a boolean, selects a value or array.
    async fill_form(p) {
      for (const f of p.fields) {
        const el = find(f);
        if (el.type === 'checkbox' || el.type === 'radio') await methods.check({ ...f, checked: !!f.value });
        else if (el.tagName === 'SELECT') await methods.select(f);
        else await methods.fill(f);
      }
      return null;
    },

    // HTML5 drag and drop with a shared DataTransfer, from one target to another.
    async drag(p) {
      const from = await actionable(p.from || {});
      const to = await actionable(p.to || {}, false);
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
        const bytes = Uint8Array.from(atob(f.data), (c) => c.charCodeAt(0));
        dt.items.add(new File([bytes], f.name, { type: f.type }));
      }
      el.files = dt.files;
      el.dispatchEvent(new Event('input', { bubbles: true }));
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
    async wait_for(p) {
      if (p.time) {
        await sleep(p.time);
        return null;
      }
      if (!['url', 'text', 'textGone', 'idle', 'ref', 'selector'].some((k) => p[k] !== undefined)) {
        throw new Error('wait_for: need selector, ref, text, textGone, url, idle or time');
      }
      const timeout = p.timeout || DEFAULT_TIMEOUT_MS;
      const state = p.state || 'visible';
      const deadline = Date.now() + timeout;
      let idleSince = null;
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
        const el = p.ref ? refs.get(p.ref) : query(document, p.selector);
        const attached = connected(el);
        if (state === 'attached') return attached;
        if (state === 'hidden') return !attached || !visible(el);
        return attached && visible(el);
      };

      while (!check()) {
        if (Date.now() > deadline) throw new Error(`wait_for timed out after ${timeout}ms: ${stringify(p)}`);
        await sleep(POLL_MS);
      }
      return null;
    },

    async snapshot(p) {
      return collect(p.selector ? find(p) : await body(), p);
    },

    // Snapshot narrowed to elements whose name, text, value or href contains
    // `text` or matches `regex`. Hands out fresh refs like snapshot does.
    async find(p) {
      const re = p.regex ? new RegExp(p.regex, 'i') : null;
      const needle = (p.text || '').toLowerCase();
      // Each field on its own, so ^...$ anchors work on a link with an href.
      const match = (item) => [item.name, item.text, item.value, item.href].filter(Boolean)
        .some((f) => (re ? re.test(f) : f.toLowerCase().includes(needle)));
      return collect(p.selector ? find(p) : await body(), p, match);
    },
  };

  async function run(id, method, params, attempt) {
    navExpected = false;
    try {
      const fn = methods[method];
      if (!fn) throw new Error(`unknown method '${method}'`);
      let result = await fn(params || {});
      if (result === undefined) result = null;
      const reply = navExpected ? { id, attempt, result, navigating: true } : { id, attempt, result };
      try {
        post(reply);
      } catch {
        post({ ...reply, result: String(result) }); // not JSON-safe (DOM node, cycle)
      }
    } catch (e) {
      post({ id, attempt, error: String((e && e.message) || e) });
    }
  }

  // Rust wraps the agent's expression in an async function and passes it
  // here, so the source is compiled as script, not through eval().
  const evalFn = (id, fn, attempt) => run(id, '__fn', fn, attempt);

  window.__bruster = { run, evalFn, bind, document: documentId, get generation() { return generation; } };
  if (window.top === window) bind(0);
})();
