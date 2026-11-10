// Real Ui.Vision extension + stdio MCP bridge. Playwright only provisions and
// closes the isolated browser; timed operations use the extension's MCP tools.
import { createRequire } from 'node:module';
import { pathToFileURL } from 'node:url';
import { createInterface } from 'node:readline';
import { createServer } from 'node:net';
import { writeFile } from 'node:fs/promises';
import path from 'node:path';

const [executablePath, dependencies] = process.argv.slice(2);
const require = createRequire(path.join(dependencies, 'package.json'));
const { chromium } = require('playwright-core');
const { Client } = await import(pathToFileURL(require.resolve('@modelcontextprotocol/sdk/client/index.js')));
const { StdioClientTransport } = await import(pathToFileURL(require.resolve('@modelcontextprotocol/sdk/client/stdio.js')));
// Each round owns a bridge port. The default port can be held by another
// application or an ephemeral browser connection from an earlier round.
const probe = createServer();
await new Promise((resolve, reject) => {
  probe.once('error', reject);
  probe.listen(0, '127.0.0.1', resolve);
});
const bridgePort = probe.address().port;
await new Promise(resolve => probe.close(resolve));
const transport = new StdioClientTransport({
  command: process.execPath,
  args: [path.join(dependencies, 'node_modules/uivision-mcp-bridge/uivision-mcp-bridge.js'),
    '--port', String(bridgePort)],
  env: process.env, stderr: 'pipe',
});
transport.stderr.on('data', data => process.stderr.write(data));
const client = new Client({ name: 'bruster-benchmark', version: '1.0.0' });
const emit = data => process.stdout.write(JSON.stringify(data) + '\n');
const text = response => (response.content || []).filter(c => c.type === 'text').map(c => c.text).join('\n');
let context;

async function call(name, args = {}) {
  const response = await client.callTool({ name, arguments: args }, undefined, { timeout: 60000 });
  if (response.isError) throw new Error(text(response));
  return response;
}

async function macro(script) {
  // Ui.Vision caps its log transport at 40,000 characters. Keep its normal
  // post-run response, and retrieve large values in bounded public tool calls.
  const response = await call('run_macro', { script, log_limit: 40000 });
  const match = text(response).match(/^\[echo\] __BRUSTER_RESULT__(.*)$/m);
  if (!match) throw new Error(`Ui.Vision result missing or truncated: ${text(response)}`);
  return JSON.parse(match[1]);
}

async function evaluate(expression) {
  const chunkSize = 12000;
  const source = `window.__brusterBenchmarkResult = JSON.stringify((${expression}));
    return {length: window.__brusterBenchmarkResult.length,
      chunk: window.__brusterBenchmarkResult.slice(0, ${chunkSize})};`;
  const first = await macro(`const value = uiv.evaluate(${JSON.stringify(source)});
    uiv.log('__BRUSTER_RESULT__' + JSON.stringify(value));`);
  let value = first.chunk;
  for (let start = chunkSize; start < first.length; start += chunkSize) {
    const read = `return window.__brusterBenchmarkResult.slice(${start}, ${start + chunkSize});`;
    value += await macro(`uiv.log('__BRUSTER_RESULT__' + JSON.stringify(uiv.evaluate(${JSON.stringify(read)})));`);
  }
  if (value.length !== first.length) throw new Error('Incomplete Ui.Vision extraction transport');
  return JSON.parse(value);
}

async function navigate(url) {
  // This is Ui.Vision's documented navigate-and-inspect MCP tool.
  await call('browser_snapshot', { url });
  return await evaluate('({url: location.href})');
}

async function close() {
  try {
    await context?.close();
  } finally {
    await client.close();
  }
}

try {
  await client.connect(transport);
  const before = text(await call('bridge_status'));
  // Also reject relay mode if another process took the chosen port between
  // the probe and bridge startup, even when that bridge has no browser yet.
  if (/relay mode/i.test(before) || !before.includes('NOT connected')) {
    throw new Error(`Ui.Vision bridge is not isolated: ${before}`);
  }
  const extension = path.join(dependencies, 'uivision-extension');
  context = await chromium.launchPersistentContext(path.join(process.env.HOME, 'chrome-profile'), {
    executablePath, headless: true, viewport: { width: 1280, height: 800 }, deviceScaleFactor: 1,
    args: ['--no-sandbox', `--disable-extensions-except=${extension}`, `--load-extension=${extension}`],
  });
  const origin = 'chrome-extension://gcbalfbdmfieckjlnblleoemohcganoc/';
  const blank = context.pages()[0];
  const panel = await context.newPage();
  await panel.goto(`${origin}sidepanel.html`);
  // The first panel initializes and persists defaults asynchronously. Writing
  // storage before that finishes can lose the custom port. Use the normal
  // settings controls after initialization, then reload the panel from storage.
  await panel.getByText('Files', { exact: true }).waitFor();
  const settings = await context.newPage();
  await settings.goto(`${origin}options.html`);
  await settings.getByRole('link', { name: 'AI ✨', exact: true }).click();
  const enabled = settings.locator('.ai-settings-item')
    .filter({ hasText: 'MCP bridge (Claude Code' }).getByRole('switch');
  if (await enabled.getAttribute('aria-checked') !== 'true') await enabled.click();
  await settings.getByText('Bridge port:', { exact: true }).locator('..')
    .getByRole('spinbutton').fill(String(bridgePort));
  await settings.waitForFunction(async port => {
    const { config = {} } = await chrome.storage.local.get('config');
    return config.mcpBridgeEnabled && Number(config.mcpBridgePort) === port;
  }, bridgePort);
  await settings.close();
  await panel.reload();
  const deadline = Date.now() + 30000;
  while (true) {
    const status = text(await call('bridge_status'));
    if (status.includes('1 browser connection:')) break;
    if (Date.now() > deadline) {
      const settings = await panel.evaluate(async () => {
        const { config = {} } = await chrome.storage.local.get('config');
        const active = window.store?.getState()?.config || {};
        return { storedPort: config.mcpBridgePort, storedEnabled: config.mcpBridgeEnabled,
          activePort: active.mcpBridgePort, activeEnabled: active.mcpBridgeEnabled };
      });
      throw new Error(`Ui.Vision panel did not connect on port ${bridgePort}: ${JSON.stringify(settings)}; ${status}`);
    }
    await new Promise(resolve => setTimeout(resolve, 200));
  }
  // The numeric suffix counts connections, so the panel reload can advance it.
  // The isolated bridge has exactly one browser; select that Chrome instance.
  await call('select_browser', { target: 'chrome' });
  await call('get_authoring_guide');
  for (const page of context.pages()) {
    if (page !== blank && page !== panel) await page.close();
  }
  emit({ event: 'ready', tool: 'uivision', bridge_port: bridgePort });
  const lines = createInterface({ input: process.stdin, crlfDelay: Infinity });
  for await (const line of lines) {
    const { id, method, params = {} } = JSON.parse(line);
    try {
      let result;
      switch (method) {
        case 'navigate': result = await navigate(params.url); break;
        case 'eval': result = await evaluate(params.expression); break;
        case 'snapshot': result = text(await call('browser_snapshot', { max_chars: 60000 })); break;
        case 'screenshot': {
          const response = await call('screenshot', { scope: 'browser' });
          const image = response.content.find(c => c.type === 'image');
          if (!image || image.mimeType !== 'image/png') throw new Error('Ui.Vision did not return a PNG screenshot');
          await writeFile(params.path, Buffer.from(image.data, 'base64'));
          result = { path: params.path };
          break;
        }
        case 'close':
          await close();
          emit({ id, result: null });
          process.exit(0);
          break;
        default: throw new Error(`Unknown method: ${method}`);
      }
      emit({ id, result });
    } catch (error) {
      emit({ id, error: String(error.stack || error) });
    }
  }
} finally {
  await close();
}
