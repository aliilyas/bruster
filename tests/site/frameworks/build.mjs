import { build } from 'esbuild';
import { compile } from 'svelte/compiler';
import { mkdir, readFile, writeFile, readdir } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import path from 'node:path';

const source = path.dirname(fileURLToPath(import.meta.url));
const output = process.argv[2] ? path.resolve(process.argv[2]) : path.resolve(source, '../../../target/test-lab-frameworks');
await mkdir(output, { recursive: true });
await build({
  absWorkingDir: source,
  entryPoints: ['react.js', 'vue.js', 'svelte.js'],
  outdir: output,
  bundle: true,
  minify: true,
  format: 'iife',
  platform: 'browser',
  target: 'es2020',
  legalComments: 'external',
  define: { 'process.env.NODE_ENV': '"production"', __VUE_OPTIONS_API__: 'true', __VUE_PROD_DEVTOOLS__: 'false', __VUE_PROD_HYDRATION_MISMATCH_DETAILS__: 'false' },
  plugins: [{
    name: 'svelte-fixture',
    setup(builder) {
      builder.onLoad({ filter: /\.svelte$/ }, async args => ({
        contents: compile(await readFile(args.path, 'utf8'), { filename: args.path, generate: 'client', dev: false }).js.code,
        resolveDir: path.dirname(args.path),
        loader: 'js',
      }));
    },
  }],
});
const versions = {}, licenses = [];
for (const name of ['react', 'react-dom', 'svelte', 'vue']) {
  const directory = path.join(source, 'node_modules', name);
  versions[name] = JSON.parse(await readFile(path.join(directory, 'package.json'), 'utf8')).version;
  const license = (await readdir(directory)).find(file => /^license(?:\.md|\.txt)?$/i.test(file));
  if (!license) throw new Error(`Missing ${name} license`);
  licenses.push(`${name} ${versions[name]}\n${await readFile(path.join(directory, license), 'utf8')}`);
}
await writeFile(path.join(output, 'versions.json'), JSON.stringify(versions, null, 2) + '\n');
await writeFile(path.join(output, 'LICENSES.txt'), licenses.join('\n\n'));
console.log(`Built pinned framework fixtures in ${output}`);
