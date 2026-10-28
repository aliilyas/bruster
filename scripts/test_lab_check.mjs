// Validate generated JavaScript and every local script/style asset before publishing.
import { readFile, readdir, stat } from 'node:fs/promises';
import path from 'node:path';
import vm from 'node:vm';

const directory = path.resolve(process.argv[2] || 'target/test-lab');
const manifest = JSON.parse(await readFile(path.join(directory, 'manifest.json'), 'utf8'));
let count = 0;
async function walk(root) {
  for (const name of await readdir(root)) {
    const file = path.join(root, name);
    if ((await stat(file)).isDirectory()) { await walk(file); continue; }
    if (name.endsWith('.js')) new vm.Script(await readFile(file, 'utf8'), { filename: file });
    if (!name.endsWith('.html')) continue;
    const content = await readFile(file, 'utf8');
    for (const match of content.matchAll(/<script\b([^>]*)>([\s\S]*?)<\/script>/gi)) {
      const src = match[1].match(/\bsrc="([^"]+)"/i);
      if (src) await stat(path.resolve(path.dirname(file), src[1]));
      else new vm.Script(match[2], { filename: file });
    }
    for (const match of content.matchAll(/<link\b[^>]*href="([^"]+)"/gi)) {
      await stat(path.resolve(path.dirname(file), match[1]));
    }
    count++;
  }
}
await walk(directory);
for (const item of manifest.cases) {
  await stat(path.join(directory, item.url));
  new vm.Script(`async function fixture(){${item.setup}\n}`, { filename: item.id });
  for (const step of item.steps) {
    if (step.method === 'eval' && !Object.hasOwn(step, 'error')) {
      try {
        new vm.Script(`async function expression(){return (\n${step.params.expression}\n)}`, { filename: item.id });
      } catch {
        new vm.Script(`async function statements(){\n${step.params.expression}\n}`, { filename: item.id });
      }
    }
    if (step.verify) new vm.Script(`async function verify(result){return (${step.verify})}`, { filename: item.id });
    for (const expression of Object.values(step.capture || {})) {
      new vm.Script(`async function capture(result){return (${expression})}`, { filename: item.id });
    }
  }
}
console.log(`Validated ${manifest.cases.length} case routes, ${count} HTML pages, and their JavaScript/assets`);
