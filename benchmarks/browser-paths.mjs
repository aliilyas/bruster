// Resolve the browsers supplied by the just-installed latest Playwright release.
import { accessSync, constants } from 'node:fs';
import { createRequire } from 'node:module';
import path from 'node:path';

const require = createRequire(path.resolve(process.argv[2], 'package.json'));
const { registry } = require('playwright-core/lib/coreBundle').registry;
for (const [variable, browser] of [['BENCH_CHROME', 'chromium'], ['BENCH_SHELL', 'chromium-headless-shell']]) {
  const executable = registry.findExecutable(browser).executablePath();
  accessSync(executable, constants.X_OK);
  console.log(`${variable}=${executable}`);
}
