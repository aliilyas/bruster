// Persistent controller for the real Cypress spec runner. Each protocol request
// is a separate Cypress test so expected navigation failures can be followed by
// a recovery test. The runner, proxy, task IPC and browser all remain in scope.
import { spawn } from 'node:child_process';
import { createServer } from 'node:http';
import { createInterface } from 'node:readline';
import { copyFile, writeFile } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const [executablePath, dependencies, commandCount, baseUrl] = process.argv.slice(2);
process.env.CYPRESS_CACHE_FOLDER = path.join(dependencies, 'cypress-cache');
process.env.BRUSTER_CYPRESS_BASE_URL = baseUrl;
const here = path.dirname(fileURLToPath(import.meta.url));
const project = process.env.HOME;
await writeFile(path.join(project, 'package.json'), '{"private":true}\n');
for (const name of ['bench_cypress.config.cjs', 'bench_cypress.cy.js']) {
  await copyFile(path.join(here, name), path.join(project, name));
}
const queue = [];
let pending, closing, active, ready = false;
const emit = value => process.stdout.write(JSON.stringify(value) + '\n');
const send = (response, value) => {
  response.writeHead(200, { 'Content-Type': 'application/json' });
  response.end(JSON.stringify(value));
};
const lines = createInterface({ input: process.stdin, crlfDelay: Infinity });
lines.on('line', line => {
  const request = JSON.parse(line);
  if (pending) {
    active = request;
    send(pending, request);
    pending = undefined;
  } else queue.push(request);
});
const server = createServer(async (request, response) => {
  try {
    const chunks = [];
    for await (const chunk of request) chunks.push(chunk);
    const data = JSON.parse(Buffer.concat(chunks).toString() || 'null');
    switch (request.url) {
      case '/ready':
        if (!ready) emit({ event: 'ready', tool: 'cypress' });
        ready = true;
        break;
      case '/next':
        // Cypress can reload its runner when establishing the AUT origin.
        // Redeliver an unacknowledged command rather than losing it on reload.
        if (active || queue.length) send(response, active ||= queue.shift());
        else pending = response;
        return;
      case '/result':
        if (data.id !== active?.id) throw new Error('Cypress command/result mismatch');
        active = undefined;
        emit(data);
        break;
      case '/close': closing = data.id; break;
      default: throw new Error(`Unknown Cypress controller endpoint: ${request.url}`);
    }
    send(response, null);
  } catch (error) {
    response.writeHead(500);
    response.end(String(error.stack || error));
  }
});
await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
process.env.BRUSTER_CYPRESS_ENDPOINT = `http://127.0.0.1:${server.address().port}`;
try {
  const runner = spawn(process.execPath, [path.join(dependencies, 'node_modules/cypress/bin/cypress'),
    'run', '--project', project, '--browser', executablePath, '--headless', '--quiet',
    '--config-file', path.join(project, 'bench_cypress.config.cjs'),
    '--expose', `benchmarkCommands=${Number(commandCount)}`,
  ], { stdio: ['ignore', 'pipe', 'pipe'] });
  runner.stdout.pipe(process.stderr);
  runner.stderr.pipe(process.stderr);
  const code = await new Promise((resolve, reject) => {
    runner.once('error', reject);
    runner.once('exit', resolve);
  });
  if (!closing || code !== 0) {
    throw new Error(`Cypress stopped before a clean close (exit ${code})`);
  }
  emit({ id: closing, result: null });
} finally {
  lines.close();
  process.stdin.destroy();
  server.closeAllConnections();
  await new Promise(resolve => server.close(resolve));
}
