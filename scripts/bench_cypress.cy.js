// Cypress executes every browser operation here, in its application iframe.
// Suppressed test failures are sent back as protocol errors, never successes.
let active, response, stopped = false;
Cypress.on('fail', error => {
  if (!active) throw error;
  response = { id: active.id, error: String(error.stack || error) };
  return false;
});
before(() => {
  cy.viewport(1280, 800);
  cy.window();
  cy.task('benchmark:ready', null, { log: false });
});
afterEach(() => {
  if (!active) return;
  cy.task('benchmark:result', response, { log: false }).then(() => { active = undefined; });
});
for (let i = 0; i < Cypress.expose('benchmarkCommands'); i++) {
  it(`controller command ${i}`, function () {
    if (stopped) this.skip();
    cy.task('benchmark:next', null, { log: false }).then(request => {
      active = request;
      response = { id: request.id, result: null };
      const params = request.params || {};
      switch (request.method) {
        case 'navigate':
          return cy.visit(params.url, { retryOnNetworkFailure: false, retryOnStatusCodeFailure: false })
            .then(win => { response.result = { url: win.location.href }; });
        case 'eval':
          return cy.window().then(win => {
            // Run in the AUT window, not Cypress's runner document.
            return Cypress.Promise.resolve().then(() => win.eval(params.expression))
              .then(result => { response.result = result; })
              .catch(error => { response = { id: request.id, error: String(error.stack || error) }; });
          });
        case 'screenshot':
          return cy.screenshot(`benchmark-${request.id}`, {
            capture: 'viewport', overwrite: true, disableTimersAndAnimations: false,
          }).then(() => { response.result = { path: params.path }; });
        case 'close': stopped = true; return;
        default: throw new Error(`Unsupported Cypress operation: ${request.method}`);
      }
    });
  });
}
