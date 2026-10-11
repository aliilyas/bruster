// Drives bruster through the official MCP TypeScript SDK, the client library
// behind Claude Desktop, Cursor and VS Code. Usage: node ts_sdk.mjs <bruster> [args...]
import { Client } from '@modelcontextprotocol/sdk/client/index.js';
import { StdioClientTransport } from '@modelcontextprotocol/sdk/client/stdio.js';

const [command, ...args] = process.argv.slice(2);
const client = new Client({ name: 'bruster-integration', version: '0' }, { capabilities: {} });
await client.connect(new StdioClientTransport({ command, args, stderr: 'ignore' }));

const assert = (cond, msg) => { if (!cond) { console.error('FAIL', msg); process.exit(1); } };
const text = (r) => r.content.find((c) => c.type === 'text')?.text;

const { tools } = await client.listTools();
assert(tools.length > 30, `only ${tools.length} tools`);
assert(tools.every((t) => t.inputSchema?.type === 'object'), 'tool without object schema');

const nav = await client.callTool({ name: 'navigate', arguments: { url: 'https://example.com/' } });
assert(text(nav).includes('example.com'), `navigate: ${text(nav)}`);

const snap = await client.callTool({ name: 'snapshot', arguments: {} });
assert(text(snap).includes('Example Domain'), 'snapshot missing title');

const shot = await client.callTool({ name: 'screenshot', arguments: {} });
assert(shot.content[0].type === 'image' && shot.content[0].mimeType === 'image/png', 'screenshot not an image');

const bad = await client.callTool({ name: 'click', arguments: { selector: '#nope', timeout: 200 } });
assert(bad.isError === true, 'missing element must be isError');

await client.callTool({ name: 'close', arguments: {} }).catch(() => {});
console.log('PASS ts-sdk', tools.length, 'tools');
process.exit(0);
