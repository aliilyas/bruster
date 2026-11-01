const { copyFile } = require('node:fs/promises');

module.exports = {
  viewportWidth: 1280,
  viewportHeight: 800,
  video: false,
  screenshotOnRunFailure: false,
  numTestsKeptInMemory: 0,
  retries: 0,
  pageLoadTimeout: 60000,
  taskTimeout: 90000,
  e2e: {
    baseUrl: process.env.BRUSTER_CYPRESS_BASE_URL,
    specPattern: 'bench_cypress.cy.js',
    supportFile: false,
    testIsolation: false,
    setupNodeEvents(on) {
      let active;
      async function call(method, data = null) {
        const response = await fetch(`${process.env.BRUSTER_CYPRESS_ENDPOINT}/${method}`, {
          method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data),
        });
        if (!response.ok) throw new Error(await response.text());
        return response.json();
      }
      on('task', {
        'benchmark:ready': () => call('ready'),
        'benchmark:next': async () => (active = await call('next')),
        'benchmark:result': result => call(active.method === 'close' ? 'close' : 'result', result),
      });
      on('before:browser:launch', (browser, options) => {
        if (browser.family !== 'chromium') throw new Error('Benchmark requires full Chrome');
        // Leave room for the runner around the 1280x800 application iframe;
        // Cypress otherwise clips viewport screenshots to its 720px window.
        options.args.push('--no-sandbox', '--force-device-scale-factor=1', '--window-size=1600,1200');
        return options;
      });
      on('after:screenshot', async details => {
        if (active?.method !== 'screenshot') throw new Error('Unexpected Cypress screenshot');
        // Cypress owns screenshot naming; include the final copy to the
        // controller-requested path in the measured command round trip.
        await copyFile(details.path, active.params.path);
      });
    },
  },
};
