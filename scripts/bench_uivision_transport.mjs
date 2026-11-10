// Read evaluated values through Ui.Vision's public macro/log transport.
export function createEvaluator(runMacro) {
  let sequence = 0;

  async function read(source) {
    // When Ui.Vision evicts its log cursor it can return older echo lines too.
    // Correlate each response with its call instead of taking the first echo.
    const marker = `__BRUSTER_RESULT_${++sequence}__`;
    const script = `const value = uiv.evaluate(${JSON.stringify(source)});
      uiv.log(${JSON.stringify(marker)} + JSON.stringify(value));`;
    const output = await runMacro(script);
    const prefix = `[echo] ${marker}`;
    const lines = output.split('\n').filter(line => line.startsWith(prefix));
    if (lines.length !== 1) {
      throw new Error(`Ui.Vision result ${marker} missing or duplicated: ${output}`);
    }
    return JSON.parse(lines[0].slice(prefix.length));
  }

  return async function evaluate(expression) {
    const chunkSize = 12000;
    const source = `window.__brusterBenchmarkResult = JSON.stringify((${expression}));
      return {length: window.__brusterBenchmarkResult.length,
        chunk: window.__brusterBenchmarkResult.slice(0, ${chunkSize})};`;
    const first = await read(source);
    if (!Number.isSafeInteger(first?.length) || first.length < 0
        || typeof first.chunk !== 'string'
        || first.chunk.length !== Math.min(chunkSize, first.length)) {
      throw new Error('Invalid Ui.Vision extraction header');
    }
    let value = first.chunk;
    for (let start = chunkSize; start < first.length; start += chunkSize) {
      const chunk = await read(`return window.__brusterBenchmarkResult.slice(${start}, ${start + chunkSize});`);
      if (typeof chunk !== 'string' || chunk.length !== Math.min(chunkSize, first.length - start)) {
        throw new Error(`Incomplete Ui.Vision extraction chunk at ${start} of ${first.length}`);
      }
      value += chunk;
    }
    return JSON.parse(value);
  };
}
