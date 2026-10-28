(() => {
  'use strict';

  document.documentElement.classList.add('js');
  const toggle = document.querySelector('.nav-toggle');
  const nav = document.querySelector('#site-nav');
  if (toggle && nav) {
    toggle.hidden = false;
    const closeMenu = () => {
      toggle.setAttribute('aria-expanded', 'false');
      nav.classList.remove('is-open');
    };
    toggle.addEventListener('click', () => {
      const open = toggle.getAttribute('aria-expanded') !== 'true';
      toggle.setAttribute('aria-expanded', String(open));
      nav.classList.toggle('is-open', open);
    });
    nav.addEventListener('click', (event) => {
      if (event.target.closest('a')) closeMenu();
    });
    document.addEventListener('keydown', (event) => {
      if (event.key === 'Escape' && toggle.getAttribute('aria-expanded') === 'true') {
        closeMenu();
        toggle.focus();
      }
    });
  }

  const status = document.querySelector('#copy-status');
  document.querySelectorAll('[data-copy]').forEach((button) => {
    const code = document.getElementById(button.dataset.copy);
    if (!code || !navigator.clipboard) return;
    button.hidden = false;
    button.addEventListener('click', async () => {
      status.textContent = '';
      try {
        await navigator.clipboard.writeText(code.textContent.trim());
        button.textContent = 'Copied';
        status.textContent = 'Code copied to clipboard.';
      } catch {
        const range = document.createRange();
        range.selectNodeContents(code);
        const selection = window.getSelection();
        selection.removeAllRanges();
        selection.addRange(range);
        status.textContent = 'Clipboard unavailable. Code selected; use your keyboard to copy.';
        button.textContent = 'Selected';
      }
      window.setTimeout(() => { button.textContent = 'Copy'; }, 2000);
    });
  });

  document.querySelectorAll('[data-tabs]').forEach((group) => {
    const tablist = group.querySelector('[role="tablist"]');
    const tabs = Array.from(group.querySelectorAll('[role="tab"]'));
    const panels = Array.from(group.querySelectorAll('[data-tab-panel]'));
    if (!tablist || !tabs.length || tabs.length !== panels.length) return;
    tablist.hidden = false;
    panels.forEach((panel) => {
      panel.setAttribute('role', 'tabpanel');
      panel.setAttribute('aria-labelledby', panel.dataset.tabPanel);
      panel.tabIndex = 0;
    });
    const activate = (tab, focus = false) => {
      tabs.forEach((item) => {
        const selected = item === tab;
        item.setAttribute('aria-selected', String(selected));
        item.tabIndex = selected ? 0 : -1;
        document.getElementById(item.getAttribute('aria-controls')).hidden = !selected;
      });
      if (focus) tab.focus();
    };
    tabs.forEach((tab, index) => {
      tab.addEventListener('click', () => activate(tab));
      tab.addEventListener('keydown', (event) => {
        let next;
        if (event.key === 'ArrowRight') next = (index + 1) % tabs.length;
        if (event.key === 'ArrowLeft') next = (index - 1 + tabs.length) % tabs.length;
        if (event.key === 'Home') next = 0;
        if (event.key === 'End') next = tabs.length - 1;
        if (next !== undefined) {
          event.preventDefault();
          activate(tabs[next], true);
        }
      });
    });
    activate(tabs[0]);
  });

  // Old homepage bookmarks still have useful, visible links without JavaScript.
  // With JavaScript, take the visitor straight to the corresponding documentation.
  const followLegacyLink = () => {
    const target = document.getElementById(location.hash.slice(1));
    if (target && target.matches('.legacy-links a') && target.origin === location.origin) {
      location.replace(target.href);
    }
  };
  followLegacyLink();
  window.addEventListener('hashchange', followLegacyLink);
})();
