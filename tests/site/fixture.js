/* Instrumentation only: the external Bruster runner performs and grades actions. */
(() => {
  const site = new URL('../', location.href);
  const lab = window.__lab = {
    id: '', ready: false, error: null, state: {}, events: [],
    server: window.__labServer, sitePath: site.pathname,
    async until(predicate, timeout = 5000) {
      const deadline = performance.now() + timeout;
      while (!predicate()) {
        if (performance.now() > deadline) throw new Error('Fixture readiness timed out');
        await new Promise(resolve => setTimeout(resolve, 20));
      }
      return true;
    },
  };
  for (const type of ['focus','blur','focusin','focusout','pointerdown','pointerup','pointermove',
    'mousedown','mouseup','click','mouseover','mouseenter','keydown','keypress','keyup',
    'beforeinput','input','change','submit','reset','dragstart','dragenter','dragover','drop','dragend']) {
    document.addEventListener(type, event => {
      if (lab.events.length >= 5000) return;
      const entry = {
        sequence: lab.events.length, type, target: event.target.id || event.target.nodeName,
        trusted: event.isTrusted, bubbles: event.bubbles, cancelled: event.defaultPrevented,
        key: event.key, code: event.code, keyCode: event.keyCode,
        button: event.button, buttons: event.buttons, pointerId: event.pointerId,
        x: event.clientX, y: event.clientY,
        value: 'value' in event.target ? event.target.value : undefined,
      };
      lab.events.push(entry);
      queueMicrotask(() => { entry.cancelled = event.defaultPrevented; });
    }, true);
  }
})();
