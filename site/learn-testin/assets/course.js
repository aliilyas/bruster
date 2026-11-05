(() => {
  'use strict';
  const status = document.getElementById('copy-status');
  document.querySelectorAll('[data-copy]').forEach((button) => {
    const code = document.getElementById(button.dataset.copy);
    if (!code) return;
    button.hidden = false;
    button.addEventListener('click', async () => {
      try {
        await navigator.clipboard.writeText(code.textContent);
        button.textContent = 'Copied';
        status.textContent = 'Test copied. Paste it into your plain-text file.';
      } catch {
        const range = document.createRange();
        range.selectNodeContents(code);
        const selection = window.getSelection();
        selection.removeAllRanges();
        selection.addRange(range);
        button.textContent = 'Selected';
        status.textContent = 'Text selected. Press Ctrl+C on Windows or Linux, or Command+C on Mac, to copy it.';
      }
    });
  });
})();
