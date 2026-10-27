// Persistent JSON-lines adapters for the public Playwright/Puppeteer APIs.
// Their Node process and imports are included in startup and memory accounting.
import { createRequire } from 'node:module';
import { pathToFileURL } from 'node:url';
import { createInterface } from 'node:readline';
import { stat } from 'node:fs/promises';
import path from 'node:path';

const [tool, executablePath, dependencies] = process.argv.slice(2);
const require = createRequire(path.join(dependencies, 'package.json'));
const options = { executablePath, headless: true, args: ['--no-sandbox'] };
let browser, page;
if (tool.startsWith('playwright')) {
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
} else {
  throw new Error(`Unknown tool: ${tool}`);
}

function emit(obj) {
  process.stdout.write(JSON.stringify(obj) + '\n');
}
emit({ event: 'ready', tool, browserVersion: await browser.version() });
const lines = createInterface({ input: process.stdin, crlfDelay: Infinity });
for await (const line of lines) {
  const request = JSON.parse(line);
  const { id, method, params = {} } = request;
  try {
    let result;
    switch (method) {
      case 'navigate': {
        const response = await page.goto(params.url, { waitUntil: 'load', timeout: 60000 });
        if (!response || response.status() !== 200) throw new Error('Navigation did not return HTTP 200');
        result = { url: page.url() };
        break;
      }
      case 'eval':
        result = await page.evaluate(params.expression);
        break;
      case 'snapshot':
        result = tool.startsWith('playwright')
          ? await page.locator('body').ariaSnapshot()
          : await page.accessibility.snapshot({ interestingOnly: true });
        break;
      case 'screenshot':
        await page.screenshot({ path: params.path, type: 'png', fullPage: false });
        result = { path: params.path, bytes: (await stat(params.path)).size };
        break;
      case 'close':
        await browser.close();
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
await browser.close();
