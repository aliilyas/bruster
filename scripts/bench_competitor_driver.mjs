// Persistent JSON-lines adapters for public browser SDKs.
// Their Node process and imports are included in startup and memory accounting.
import { createRequire } from 'node:module';
import { pathToFileURL } from 'node:url';
import { createInterface } from 'node:readline';
import { readFile, stat, writeFile } from 'node:fs/promises';
import path from 'node:path';

const [tool, executablePath, dependencies] = process.argv.slice(2);
const require = createRequire(path.join(dependencies, 'package.json'));
const options = { executablePath, headless: true, args: ['--no-sandbox'] };
let browser, page, stagehand, viewportSocket;
if (tool === 'playwright' || tool === 'playwright-shell') {
  const loaded = await import(pathToFileURL(require.resolve('playwright-core')));
  const { chromium } = loaded.default || loaded;
  browser = await chromium.launch(options);
  page = await browser.newPage({ viewport: { width: 1280, height: 800 }, deviceScaleFactor: 1 });
} else if (tool === 'puppeteer') {
  const { default: puppeteer } = await import(pathToFileURL(require.resolve('puppeteer-core')));
  browser = await puppeteer.launch({ ...options, defaultViewport: { width: 1280, height: 800, deviceScaleFactor: 1 } });
  // Reuse the initial blank tab, so both tools have exactly one page.
  [page] = await browser.pages();
  if (!page) page = await browser.newPage();
} else if (tool === 'stagehand') {
  // v4 exports ESM only. Resolve its public import entry, not a private API.
  const root = path.join(dependencies, 'node_modules/@browserbasehq/stagehand');
  const manifest = JSON.parse(await readFile(path.join(root, 'package.json'), 'utf8'));
  const { localBrowser, Stagehand } = await import(pathToFileURL(path.join(root, manifest.exports['.'].import)));
  browser = await localBrowser.launch({ ...options, viewport: { width: 1280, height: 800 }, deviceScaleFactor: 1 });
  try {
    stagehand = await Stagehand.create({ browser });
    [page] = await browser.context.pages();
    if (!page) page = await browser.context.newPage();
    await page.setViewportSize(1280, 800, { deviceScaleFactor: 1 });
  } catch (error) {
    await closeBrowser();
    throw error;
  }
} else if (tool === 'rustwright') {
  const { chromium } = require('rustwright');
  browser = await chromium.launch({ ...options, userDataDir: path.join(process.env.HOME, 'chrome-profile') });
  try {
    page = await browser.newPage();
    // The experimental Node API has no viewport setter. Use its public CDP
    // endpoint only for initial viewport provisioning; all measured operations
    // below go through Rustwright. Chromium ties overrides to the CDP session,
    // so the idle setup connection stays alive and is counted in memory.
    viewportSocket = await rustwrightViewport(browser.wsEndpoint());
  } catch (error) {
    await closeBrowser();
    throw error;
  }
} else if (tool === 'biloba') {
  const root = path.join(dependencies, 'node_modules/biloba');
  const manifest = JSON.parse(await readFile(path.join(root, 'package.json'), 'utf8'));
  const { connect } = await import(pathToFileURL(path.join(root, manifest.exports['.'].import)));
  browser = await connect({ chromePath: executablePath, mode: 'headless', autoInstall: false,
    chromeSandbox: false, windowSize: { width: 1280, height: 800 } });
  try {
    page = await browser.openSession();
    await page.setDeviceMetrics({ width: 1280, height: 800, deviceScaleFactor: 1, mobile: false });
  } catch (error) {
    await closeBrowser();
    throw error;
  }
} else {
  throw new Error(`Unknown tool: ${tool}`);
}

async function rustwrightViewport(endpoint) {
  const socket = new WebSocket(endpoint);
  let nextId = 0;
  const pending = new Map();
  socket.addEventListener('message', event => {
    const message = JSON.parse(event.data);
    const resolve = pending.get(message.id);
    if (resolve) { pending.delete(message.id); resolve(message); }
  });
  const request = async (method, params = {}, sessionId) => {
    const id = ++nextId;
    let timer;
    try {
      const response = await Promise.race([
        new Promise(resolve => { pending.set(id, resolve); socket.send(JSON.stringify({ id, method, params, sessionId })); }),
        new Promise((_, reject) => { timer = setTimeout(() => reject(new Error(`Viewport setup timed out: ${method}`)), 30000); }),
      ]);
      if (response.error) throw new Error(JSON.stringify(response.error));
      return response.result;
    } finally { clearTimeout(timer); pending.delete(id); }
  };
  try {
    await new Promise((resolve, reject) => {
      socket.addEventListener('open', resolve, { once: true });
      socket.addEventListener('error', reject, { once: true });
    });
    const { targetInfos } = await request('Target.getTargets');
    const targets = targetInfos.filter(target => target.type === 'page');
    if (!targets.length) throw new Error('Rustwright did not create a page');
    for (const { targetId } of targets) {
      const { sessionId } = await request('Target.attachToTarget', { targetId, flatten: true });
      await request('Emulation.setDeviceMetricsOverride', { width: 1280, height: 800, deviceScaleFactor: 1, mobile: false }, sessionId);
    }
    return socket;
  } catch (error) {
    socket.close();
    throw error;
  }
}

function emit(obj) {
  process.stdout.write(JSON.stringify(obj) + '\n');
}

async function closeBrowser() {
  // Stagehand.close() detaches the SDK; the separately launched browser is
  // still owned by this adapter and must be closed even if detaching fails.
  try {
    await stagehand?.close();
  } finally {
    try {
      await browser.close();
    } finally {
      viewportSocket?.close();
    }
  }
}
emit({ event: 'ready', tool });
const lines = createInterface({ input: process.stdin, crlfDelay: Infinity });
for await (const line of lines) {
  const request = JSON.parse(line);
  const { id, method, params = {} } = request;
  try {
    let result;
    switch (method) {
      case 'navigate': {
        if (tool === 'biloba') {
          await page.navigateWithStatus(params.url, 200, { timeoutMs: 60000 });
          result = { url: await page.url() };
          break;
        }
        const response = await page.goto(params.url, { waitUntil: 'load', timeout: 60000 });
        const status = tool === 'rustwright' ? response?.status : response?.status();
        if (status !== 200) throw new Error(`Navigation did not return HTTP 200: ${JSON.stringify(response)}`);
        result = { url: tool === 'rustwright' ? await page.evaluate('location.href') : await page.url() };
        break;
      }
      case 'eval':
        result = await page.evaluate(params.expression);
        break;
      case 'snapshot':
        if (tool === 'rustwright') throw new Error('Rustwright Node SDK has no native snapshot API');
        result = tool === 'biloba' ? await page.accessibilityOutline() : tool === 'stagehand' ? await page.snapshot() : tool.startsWith('playwright')
          ? await page.locator('body').ariaSnapshot()
          : await page.accessibility.snapshot({ interestingOnly: true });
        break;
      case 'screenshot':
        if (tool === 'biloba') await writeFile(params.path, await page.captureScreenshot({ viewport: true }));
        else await page.screenshot({ path: params.path, type: 'png', fullPage: false });
        result = { path: params.path, bytes: (await stat(params.path)).size };
        break;
      case 'close':
        await closeBrowser();
        emit({ id, result: null });
        process.exit(0);
        break;
      default:
        throw new Error(`Unknown method: ${method}`);
    }
    emit({ id, result });
  } catch (error) {
    emit({ id, error: String(error.stack || error) });
  }
}
await closeBrowser();
