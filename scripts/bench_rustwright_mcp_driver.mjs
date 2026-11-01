// Official native Rustwright MCP server, launched from its npm binary package.
// The MCP client and server (plus all response snapshots) are measured together.
import { createRequire } from 'node:module';
import { pathToFileURL } from 'node:url';
import { createInterface } from 'node:readline';
import { writeFile } from 'node:fs/promises';
import path from 'node:path';

const [executablePath, dependencies] = process.argv.slice(2);
const require = createRequire(path.join(dependencies, 'package.json'));
const { Client } = await import(pathToFileURL(require.resolve('@modelcontextprotocol/sdk/client/index.js')));
const { StdioClientTransport } = await import(pathToFileURL(require.resolve('@modelcontextprotocol/sdk/client/stdio.js')));
const platforms = require('rustwright-mcp/platforms.json');
const platform = platforms[`${process.platform}-${process.arch}`];
if (!platform) throw new Error('Rustwright MCP has no native package for this platform');
const transport = new StdioClientTransport({
  command: require.resolve(`${platform.package}/bin/${platform.binary}`),
  env: { ...process.env, RUSTWRIGHT_CHROMIUM: executablePath,
    RUSTWRIGHT_MCP_MAX_RESPONSE_BYTES: '0', RUSTWRIGHT_MCP_MAX_RESPONSE_LINES: '0' },
  stderr: 'pipe',
});
transport.stderr.on('data', data => process.stderr.write(data));
const client = new Client({ name: 'bruster-benchmark', version: '1.0.0' });
const emit = data => process.stdout.write(JSON.stringify(data) + '\n');
const text = response => (response.content || []).filter(c => c.type === 'text').map(c => c.text).join('\n');

async function call(name, args = {}) {
  const response = await client.callTool({ name, arguments: args }, undefined, { timeout: 60000 });
  if (response.isError) throw new Error(text(response));
  return response;
}

async function evaluate(expression) {
  const response = text(await call('browser_evaluate', { function: `() => (${expression})` }));
  // The published server returns a JSON value followed by its normal snapshot.
  return JSON.parse(response.split(/\r?\n\r?\n### /, 1)[0]);
}

async function navigate(url) {
  await call('browser_navigate', { url });
  return await evaluate(`new Promise(resolve => {
    const done = () => resolve({url: location.href});
    if (document.readyState === 'complete') done();
    else addEventListener('load', done, {once: true});
  })`);
}

try {
  await client.connect(transport);
  const { tools } = await client.listTools();
  for (const name of ['browser_navigate', 'browser_resize', 'browser_evaluate', 'browser_snapshot', 'browser_take_screenshot', 'browser_close']) {
    if (!tools.some(tool => tool.name === name)) throw new Error(`Required MCP tool missing: ${name}`);
  }
  await call('browser_resize', { width: 1280, height: 800 });
  emit({ event: 'ready', tool: 'rustwright-mcp' });
  const lines = createInterface({ input: process.stdin, crlfDelay: Infinity });
  for await (const line of lines) {
    const { id, method, params = {} } = JSON.parse(line);
    try {
      let result;
      switch (method) {
        case 'navigate': result = await navigate(params.url); break;
        case 'eval': result = await evaluate(params.expression); break;
        case 'snapshot': result = text(await call('browser_snapshot')); break;
        case 'screenshot': {
          const response = await call('browser_take_screenshot', { type: 'png', fullPage: false });
          const image = response.content.find(c => c.type === 'image');
          if (!image || image.mimeType !== 'image/png') throw new Error('Rustwright MCP did not return a PNG screenshot');
          await writeFile(params.path, Buffer.from(image.data, 'base64'));
          result = { path: params.path };
          break;
        }
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
