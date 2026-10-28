/* Catalog content is rendered with textContent, including imported test reports. */
(async () => {
  const $ = id => document.getElementById(id);
  const make = (tag, text, className) => {
    const node = document.createElement(tag);
    if (text !== undefined) node.textContent = text;
    if (className) node.className = className;
    return node;
  };
  let manifest;
  try {
    const response = await fetch('manifest.json');
    if (!response.ok) throw new Error(`Manifest HTTP ${response.status}`);
    manifest = await response.json();
  } catch (error) {
    $('cases').textContent = `Unable to load the fixture catalog: ${error.message}`;
    return;
  }
  const cases = manifest.cases;
  const counts = new Map();
  for (const item of cases) counts.set(item.category, (counts.get(item.category) || 0) + 1);
  let category = '', results = new Map();
  $('case-count').textContent = cases.length;
  $('category-count').textContent = counts.size;
  $('probe-count').textContent = cases.filter(item => item.contract === 'probe').length;
  $('revision').textContent = manifest.provenance.sourceSha256.slice(0, 8);
  $('provenance').textContent = `Commit ${manifest.provenance.commit} · Fixture SHA-256 ${manifest.provenance.sourceSha256}`;
  for (const [name, count] of [['', cases.length], ...counts]) {
    const button = make('button', undefined, 'category');
    button.type = 'button';
    button.append(make('span', name || 'All fixtures'), make('span', count));
    button.dataset.category = name;
    button.setAttribute('aria-pressed', String(!name));
    button.onclick = () => { category = name; render(); };
    $('categories').append(button);
  }
  function render() {
    const query = $('search').value.trim().toLowerCase();
    const selected = cases.filter(item => {
      const server = item.requires.includes('server');
      return (!category || item.category === category)
        && (!$('contract').value || item.contract === $('contract').value)
        && (!$('tier').value || item.tier === $('tier').value)
        && (!$('environment').value || server === ($('environment').value === 'server'))
        && (!query || `${item.id} ${item.title} ${item.description} ${item.category} ${item.steps.map(s => s.method || '').join(' ')}`.toLowerCase().includes(query));
    });
    $('cases').replaceChildren();
    $('inventory-title').textContent = category || 'All fixtures';
    $('showing').textContent = `${selected.length} of ${cases.length} cases`;
    for (const button of $('categories').children) button.setAttribute('aria-pressed', String(button.dataset.category === category));
    if (!selected.length) $('cases').append(make('p', 'No fixtures match these filters.', 'empty'));
    for (const item of selected) {
      const card = make('article', undefined, 'case');
      const heading = make('h3');
      const link = make('a', item.title);
      link.href = '#' + item.id;
      heading.append(link);
      card.append(make('div', item.id, 'case-id'), heading, make('p', `${item.steps.length} steps · ${item.category}`));
      const badges = make('div', undefined, 'badges');
      badges.append(make('span', item.contract === 'probe' ? 'Compatibility probe' : 'Required behavior', 'badge ' + item.contract));
      if (item.requires.includes('server')) badges.append(make('span', 'Local HTTP server', 'badge'));
      if (item.tier === 'stress') badges.append(make('span', 'Stress', 'badge'));
      for (const result of results.get(item.id) || []) badges.append(make('span', `${result.transport}: ${result.status}`, 'badge status-' + result.status));
      const actions = make('div', undefined, 'case-actions');
      const fixture = make('a', 'Open clean fixture ↗');
      fixture.href = item.url; fixture.target = '_blank'; fixture.rel = 'noopener';
      const details = make('a', 'Steps & assertions'); details.href = '#' + item.id;
      actions.append(details, fixture); card.append(badges, actions); $('cases').append(card);
    }
  }
  function detail() {
    const item = cases.find(item => '#' + item.id === location.hash);
    const node = $('detail'); node.replaceChildren(); node.hidden = !item;
    if (!item) return;
    const header = make('div', undefined, 'heading');
    const title = make('h2', item.title); title.id = 'detail-title';
    const close = make('button', 'Close'); close.onclick = () => { history.replaceState(null, '', location.pathname + location.search); node.hidden = true; };
    header.append(title, close); node.append(header, make('p', item.id, 'case-id'), make('p', item.description));
    const fixture = make('a', 'Open standalone fixture ↗'); fixture.href = item.url; fixture.target = '_blank'; fixture.rel = 'noopener'; node.append(fixture);
    node.append(make('h3', 'Execution contract'), make('p', `${item.contract} · ${item.tier} suite · viewport ${item.viewport.join(' × ')}`));
    if (item.requires.length) node.append(make('pre', JSON.stringify(item.requires, null, 2)));
    const options = [item.tier === 'stress' ? '--suite stress' : '',
      item.requires.some(value => typeof value === 'string' && value.startsWith('framework:')) ? '--frameworks target/test-lab-frameworks' : ''].filter(Boolean).join(' ');
    node.append(make('h3', 'Reproduce with Bruster'), make('pre', `python3 scripts/test_lab.py run --binary target/release/bruster --case ${item.id} --transport both${options ? ' ' + options : ''}`));
    node.append(make('h3', 'Commands, state assertions, and expected errors'), make('pre', JSON.stringify(item.steps, null, 2)));
    node.append(make('h3', 'Fixture HTML'), make('pre', item.html || '(Created by fixture setup)'));
    if (item.css) node.append(make('h3', 'Fixture CSS'), make('pre', item.css));
    if (item.setup) node.append(make('h3', 'Fixture setup'), make('pre', item.setup));
    if (results.has(item.id)) node.append(make('h3', 'Imported observations'), make('pre', JSON.stringify(results.get(item.id), null, 2)));
    node.scrollIntoView({ block: 'start' });
  }
  for (const id of ['search', 'contract', 'environment', 'tier']) $(id).addEventListener('input', render);
  window.addEventListener('hashchange', detail);
  $('report-file').addEventListener('change', async event => {
    const file = event.target.files[0];
    if (!file) return;
    try {
      const report = JSON.parse(await file.text());
      if (report.schemaVersion !== 1 || !Array.isArray(report.results)) throw new Error('Unsupported report schema');
      if (report.provenance?.sourceSha256 !== manifest.provenance.sourceSha256) throw new Error('Fixture revision mismatch; open the matching site build');
      const imported = new Map(), seen = new Set();
      for (const result of report.results) {
        if (!cases.some(item => item.id === result.id)) throw new Error(`Unknown case ${result.id}`);
        if (!['native', 'mcp'].includes(result.transport)
          || !['pass', 'fail', 'probe-pass', 'probe-fail', 'skip', 'error'].includes(result.status)) throw new Error('Invalid observation status or transport');
        const key = `${result.id}:${result.transport}`;
        if (seen.has(key)) throw new Error(`Duplicate observation ${key}`);
        seen.add(key);
        const entries = imported.get(result.id) || []; entries.push(result); imported.set(result.id, entries);
      }
      results = imported;
      $('report-status').textContent = `Imported ${report.results.length} observations from ${report.platform}.`;
      render(); detail();
    } catch (error) { $('report-status').textContent = `Import failed: ${error.message}`; }
  });
  render(); detail();
})();
