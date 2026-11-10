import assert from 'node:assert/strict';
import test from 'node:test';
import vm from 'node:vm';
import { createEvaluator } from './bench_uivision_transport.mjs';

function transport({ truncate = false } = {}) {
  const page = vm.createContext({ window: {} });
  const history = [];
  return async script => {
    vm.runInNewContext(script, { uiv: {
      evaluate(source) {
        const result = vm.runInContext(`(function() { ${source} })()`, page);
        return truncate && typeof result === 'string' ? result.slice(0, -1) : result;
      },
      log(value) { history.push(`[echo] ${value}`); },
    } });
    // Simulate losing the upstream log cursor: previous results precede the
    // current result, within the same otherwise-successful macro response.
    return `JS script finished without errors.\n--- log ---\n${history.slice(-3).join('\n')}`;
  };
}

test('selects this call when the log also contains previous results', async () => {
  const evaluate = createEvaluator(transport());
  assert.equal(await evaluate('"previous"'), 'previous');
  assert.equal(await evaluate('"current"'), 'current');
});

test('reassembles object and JSON-string results through retained chunk logs', async () => {
  const evaluate = createEvaluator(transport());
  const value = { text: '雪😀\\"\n'.repeat(10000), items: [null, true, 42] };
  const expression = JSON.stringify(value);
  assert.deepEqual(await evaluate(expression), value);
  assert.equal(await evaluate(`JSON.stringify(${expression})`), expression);
});

test('rejects a truncated chunk instead of returning partial data', async () => {
  const evaluate = createEvaluator(transport({ truncate: true }));
  await assert.rejects(evaluate('"x".repeat(30000)'), /Incomplete Ui.Vision extraction chunk/);
});

test('rejects stale-only, malformed and duplicated results', async () => {
  await assert.rejects(createEvaluator(async () => '[echo] __BRUSTER_RESULT_0__42')('42'), /missing or duplicated/);
  const run = transport();
  await assert.rejects(createEvaluator(async script => {
    const output = await run(script);
    return `${output}\n${output}`;
  })('42'), /missing or duplicated/);
  await assert.rejects(createEvaluator(async () => '[echo] __BRUSTER_RESULT_1__{"length":-1,"chunk":""}')('42'),
    /Invalid Ui.Vision extraction header/);
});
