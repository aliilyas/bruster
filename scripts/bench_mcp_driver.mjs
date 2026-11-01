// The official MCP server is a separate child: startup, transport, automatic
// snapshots and both Node processes are part of the measurement.
import { createRequire } from 'node:module';
import { pathToFileURL } from 'node:url';
import { createInterface } from 'node:readline';
import { writeFile } from 'node:fs/promises';
import path from 'node:path';

const [executablePath, dependencies] = process.argv.slice(2);
const require = createRequire(path.join(dependencies, 'package.json'));
const { Client } = await import(pathToFileURL(require.resolve('@modelcontextprotocol/sdk/client/index.js')));
const { StdioClientTransport } = await import(pathToFileURL(require.resolve('@modelcontextprotocol/sdk/client/stdio.js')));
const config = path.join(process.env.HOME, 'playwright-mcp.json');
await writeFile(config, JSON.stringify({
  browser: {
    browserName: 'chromium', isolated: true,
    launchOptions: { executablePath, headless: true, args: ['--no-sandbox'] },
    contextOptions: { viewport: { width: 1280, height: 800 }, deviceScaleFactor: 1 },
  },
  timeouts: { action: 60000, navigation: 60000 },
}));
const transport = new StdioClientTransport({
  command: process.execPath,
  args: [path.join(dependencies, 'node_modules/@playwright/mcp/cli.js'),
    '--config', config, '--output-dir', path.join(process.env.HOME, 'mcp-output'),
    '--allow-unrestricted-file-access'],
  env: process.env, stderr: 'pipe',
});
transport.stderr?.on('data', data => process.stderr.write(data));
const client = new Client({ name: 'bruster-benchmark', version: '1.0.0' });

function emit(obj) {
  process.stdout.write(JSON.stringify(obj) + '\n');
}

async function call(name, args = {}) {
  const response = await client.callTool({ name, arguments: args }, undefined, { timeout: 60000 });
  const text = (response.content || []).filter(c => c.type === 'text').map(c => c.text).join('\n');
  if (response.isError) throw new Error(text);
  return text;
}

async function evaluate(expression) {
  const text = await call('browser_evaluate', { function: `() => (${expression})` });
  const result = text.match(/(?:^|\r?\n)### Result\r?\n([\s\S]*?)(?=\r?\n### |$)/);
  if (!result) throw new Error(`MCP evaluation result missing: ${text}`);
  return JSON.parse(result[1]);
}

async function navigate(url) {
  await call('browser_navigate', { url });
  // MCP's navigation may stop at DOMContentLoaded. Keep its normal tool path
  // and response snapshots, then explicitly await the common load boundary.
  return await evaluate(`new Promise(resolve => {
    const done = () => resolve({url: location.href});
    if (document.readyState === 'complete') done();
    else addEventListener('load', done, {once: true});
  })`);
}

try {
  await client.connect(transport);
  const { tools } = await client.listTools();
  for (const name of ['browser_navigate', 'browser_evaluate', 'browser_snapshot', 'browser_take_screenshot', 'browser_close']) {
    if (!tools.some(tool => tool.name === name)) throw new Error(`Required MCP tool missing: ${name}`);
  }
  await navigate('about:blank');
  emit({ event: 'ready', tool: 'playwright-mcp' });
  const lines = createInterface({ input: process.stdin, crlfDelay: Infinity });
  for await (const line of lines) {
    const { id, method, params = {} } = JSON.parse(line);
    try {
      let result;
      switch (method) {
        case 'navigate': result = await navigate(params.url); break;
        case 'eval': result = await evaluate(params.expression); break;
        case 'snapshot': result = await call('browser_snapshot'); break;
        case 'screenshot':
          await call('browser_take_screenshot', { filename: params.path, type: 'png', fullPage: false, scale: 'css' });
          result = { path: params.path };
          break;
        case 'close':
          await call('browser_close');
          await client.close();
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
  await client.close();
}
