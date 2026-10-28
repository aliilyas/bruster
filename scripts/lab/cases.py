"""Executable fixture specifications. Expectations are independent of Bruster internals.

Every parameter expansion produces its own URL, trace, assertions, and result.
Probes describe deliberate capability questions; a failing probe is never a pass.
"""
from copy import deepcopy


CASES = []


def command(method, params=None, *, expect=..., verify=None, error=None, capture=None, **extra):
    step = {'method': method, 'params': params or {}}
    if expect is not ...:
        step['expect'] = expect
    if verify is not None:
        step['verify'] = verify
    if error is not None:
        step['error'] = error
    if capture:
        step['capture'] = capture
    return dict(step, **extra)


def evaluate(expression, expect=..., **kwargs):
    return command('eval', {'expression': expression}, expect=expect, **kwargs)


def check(expression, expected=True, label=None):
    # MCP renders scalar strings verbatim, so "0" and 0 have the same wire text.
    # A structured observation retains the actual DOM value's JSON type without
    # using the expected value to guess how a response should be decoded.
    return evaluate('({value: (' + expression + ')})', {'value': expected},
                    **({'label': label} if label else {}))


def case(id, title, category, html, steps, *, css='', setup='', description='',
         contract='required', requires=(), tier='core', scripts=(), document=None,
         launch=(), viewport=(960, 640)):
    item = dict(id=id, title=title, category=category, html=html, css=css, setup=setup,
                description=description or title, steps=deepcopy(steps), contract=contract,
                requires=list(requires), tier=tier, scripts=list(scripts),
                launch=list(launch), viewport=list(viewport))
    if document is not None:
        item['document'] = document
    CASES.append(item)
    return item


BUTTONS = '<button id="a" onclick="__lab.state.a++">Save</button><button id="b" onclick="__lab.state.b++">Save</button>'
COUNTERS = '__lab.state = {a:0,b:0};'
SNAPSHOT_REFS = command('snapshot', {'format': 'json'},
    capture={'a': "result.elements.filter(e=>e.role==='button')[0].ref",
             'b': "result.elements.filter(e=>e.role==='button')[1].ref"},
    verify="result.elements.filter(e=>e.role==='button').length === 2")


def identity_cases():
    for suffix, title, mutation, target, expected, error in [
        ('duplicate', 'Same-name controls retain exact identity', '', 'b', [0, 1], None),
        ('moved', 'Moving the same node preserves its reference', "document.body.append(a)", 'a', [1, 0], None),
        ('renamed', 'Renaming the same node preserves its reference', "a.textContent='Renamed'", 'a', [1, 0], None),
        ('clone', 'An identical clone cannot inherit a detached reference', 'a.replaceWith(a.cloneNode(true))', 'a', [0, 0], 'stale or unknown ref'),
        ('removed', 'Removing one duplicate cannot redirect its reference', 'a.remove()', 'a', [0, 0], 'stale or unknown ref'),
        ('replaced', 'Replacing and reversing duplicates invalidates old references',
         "const x=a.cloneNode(true), y=b.cloneNode(true); a.remove(); b.remove(); document.body.append(y,x)", 'b', [0, 0], 'stale or unknown ref'),
    ]:
        steps = [SNAPSHOT_REFS]
        if mutation:
            steps.append(evaluate(mutation))
        steps += [command('click', {'ref': '{{' + target + '}}', 'timeout': 200}, error=error),
                  check('[__lab.state.a,__lab.state.b]', expected)]
        if error:
            steps += [command('click', {'selector': '#b'}), check('__lab.state.b', 1)]
        case('ref-' + suffix, title, 'References', BUTTONS, steps, setup=COUNTERS)
    case('ref-find-refresh', 'Find installs the reference mapping used by the next action', 'References',
         '<button id="a" onclick="__lab.state.a++">Alpha</button><button id="b" onclick="__lab.state.b++">Beta</button>',
         [command('snapshot', {'format': 'json'}),
          command('find', {'text': 'Beta', 'format': 'json'}, capture={'ref': 'result.elements[0].ref'},
                  verify="result.elements.length===1 && result.elements[0].name==='Beta'"),
          command('click', {'ref': '{{ref}}'}), check('[__lab.state.a,__lab.state.b]', [0, 1])], setup=COUNTERS)
    case('ref-unknown', 'Unknown reference fails and a valid selector still works', 'References', BUTTONS,
         [command('click', {'ref': 'e99999'}, error='stale or unknown ref'),
          check('[__lab.state.a,__lab.state.b]', [0, 0]), command('click', {'selector': '#a'}),
          check('__lab.state.a', 1)], setup=COUNTERS)
    for selector, id in [('[data-key="special"]', 'attribute'), ('#odd\\:id', 'escaped'),
                         ('section > button:nth-child(2)', 'combinator'), ('button[data-key="special"]', 'compound')]:
        case('selector-' + id, 'Target by ' + id + ' selector', 'Selectors',
             '<section><button onclick="__lab.state.a++">Decoy</button><button id="odd:id" data-key="special" onclick="__lab.state.b++">Target</button></section>',
             [command('click', {'selector': selector}), check('[__lab.state.a,__lab.state.b]', [0, 1])], setup=COUNTERS)
    case('selector-invalid', 'Invalid CSS selector reports an error without damaging the page', 'Selectors', BUTTONS,
         [command('count', {'selector': '###'}, error='selector'), command('count', {'selector': 'button'}, expect=2),
          check('[__lab.state.a,__lab.state.b]', [0, 0])], setup=COUNTERS)


def snapshot_cases():
    for tag, role in [('h1', 'heading'), ('h2', 'heading'), ('h3', 'heading'), ('h4', 'heading'),
                      ('h5', 'heading'), ('h6', 'heading'), ('button', 'button'), ('textarea', 'textbox')]:
        html = '<textarea aria-label="Target">Initial</textarea>' if tag=='textarea' else f'<{tag}>Target</{tag}>'
        value = " && e.value==='Initial'" if tag=='textarea' else ''
        case('snapshot-role-' + tag, f'{tag} has the documented snapshot role', 'Snapshots', html,
             [command('snapshot', {'format': 'json'}, verify=f"result.elements.some(e=>e.role==='{role}' && e.name==='Target'{value})")])
    names = [
        ('label-for', '<label for="field">Account name</label><input id="field">', 'Account name', 'required'),
        ('label-wrap', '<label>Account name<input id="field"></label>', 'Account name', 'required'),
        ('placeholder', '<input id="field" placeholder="Account name">', 'Account name', 'required'),
        ('title', '<input id="field" title="Account name">', 'Account name', 'required'),
        ('aria-label', '<input id="field" aria-label="Account name">', 'Account name', 'required'),
        ('labelledby', '<span id="name">Account name</span><input id="field" aria-labelledby="name">', 'Account name', 'required'),
        ('labelledby-list', '<span id="first">Account</span><span id="last">name</span><input id="field" aria-labelledby="first last">', 'Account name', 'probe'),
        ('empty-label-fallback', '<label for="field"></label><input id="field" title="Account name">', 'Account name', 'probe'),
        ('name-precedence', '<span id="name">Account name</span><input id="field" aria-label="Other" aria-labelledby="name">', 'Account name', 'probe'),
    ]
    for id, html, name, contract in names:
        case('snapshot-' + id, 'Accessible name: ' + id, 'Snapshots', html,
             [command('snapshot', {'format': 'json'}, verify=f"result.elements.some(e=>e.role==='textbox' && e.name==={name!r})")], contract=contract)
    for id, html, wanted in [
        ('nested-text', '<p>Alpha <span>beta <strong>gamma</strong></span> delta</p>', 'Alpha beta gamma delta'),
        ('bare-text', '<div><div>Saved successfully</div></div>', 'Saved successfully'),
        ('unicode', '<p>héllo 日本語 🎉 مرحبا é</p>', 'héllo 日本語 🎉 مرحبا é'),
        ('whitespace', '<p> Alpha\n  beta\t gamma </p>', 'Alpha beta gamma'),
    ]:
        case('snapshot-' + id, 'Preserve ' + id, 'Snapshots', html,
             [command('snapshot', {'format': 'json'}, verify=f"result.elements.some(e=>e.text==={wanted!r})")])
    case('snapshot-wrapper-dedup', 'A link-only list item is represented once', 'Snapshots',
         '<ul><li><a href="#target">Only link</a></li></ul>',
         [command('find', {'text': 'Only link', 'format': 'json'},
                  verify="result.elements.length===1 && result.elements[0].role==='link'")])
    case('snapshot-scope', 'Scoped snapshots exclude neighboring content', 'Snapshots',
         '<section id="scope"><div><div><button>Inside</button></div></div></section><button>Outside</button>',
         [command('snapshot', {'selector': '#scope', 'format': 'json'},
                  verify="result.elements.length===1 && result.elements[0].name==='Inside'")])
    case('snapshot-image-link', 'Image alt supplies the image-only link name', 'Snapshots',
         '<a href="#target"><img src="../assets/pattern.svg" alt="Open chart"></a>',
         [command('snapshot', {'format': 'json'}, verify="result.elements.some(e=>e.role==='link' && e.name==='Open chart')")])
    case('snapshot-aria-hidden', 'ARIA-hidden controls are omitted but remain DOM-addressable', 'Snapshots',
         '<div aria-hidden="true"><button id="hidden" onclick="__lab.state.clicked=true">Secret</button></div><button>Visible</button>',
         [command('snapshot', {'format': 'json'}, verify="!result.elements.some(e=>e.name==='Secret')"),
          command('click', {'selector': '#hidden'}), check('__lab.state.clicked', True)])
    for size in (0, 1, 999, 1000, 1001):
        case(f'snapshot-count-{size}', f'Snapshot default limit with {size} controls', 'Boundaries', '',
             [command('snapshot', {'format': 'json'},
                      verify=f"result.elements.length==={min(size,1000)} && Boolean(result.truncated)==={str(size>1000).lower()}")],
             setup=f"for(let i=0;i<{size};i++){{const b=document.createElement('button');b.textContent='Item '+i;document.body.append(b)}}")
    for maximum in (0, 1, 3):
        case(f'snapshot-max-{maximum}', f'Explicit snapshot max={maximum}', 'Boundaries', '<button>A</button><button>B</button>',
             [command('snapshot', {'max': maximum, 'format': 'json'},
                      verify=f"result.elements.length==={min(maximum,2)} && Boolean(result.truncated)==={str(maximum<2).lower()}")])
    for tag, field, limit in [('button', 'name', 80), ('p', 'text', 200)]:
        for size in (limit-1, limit, limit+1):
            expected = 'x' * min(size, limit) + ('…' if size > limit else '')
            case(f'snapshot-{field}-{size}', f'{field} truncation at {size} characters', 'Boundaries', f'<{tag}>{"x"*size}</{tag}>',
                 [command('snapshot', {'format': 'json'}, verify=f"result.elements[0].{field}==={expected!r}")])
    case('snapshot-text-format', 'Text snapshots escape names and preserve link destinations', 'Snapshots',
         '<a href="?value=1#part">A &quot;quoted&quot; link</a>',
         [command('snapshot', {'format': 'text'},
                  verify=r'''typeof result==='string' && result.includes('A \\"quoted\\" link') && result.includes('?value=1#part')''')])
    case('find-anchored', 'Find regex anchors match an individual name field', 'Selectors',
         '<a href="#long-destination">Exact</a><button>Not Exact</button>',
         [command('find', {'regex': '^Exact$', 'format': 'json'}, verify="result.elements.length===1 && result.elements[0].name==='Exact'")])
    case('find-invalid-regex', 'Invalid regular expression is bounded and recoverable', 'Selectors', '<button>Valid</button>',
         [command('find', {'regex': '('}, error=''), command('count', {'selector': 'button'}, expect=1)])
    case('attributes-properties', 'Attribute reads distinguish DOM attributes from live values', 'Extraction',
         '<input id="field" value="original" data-empty="">',
         [command('fill', {'selector': '#field', 'value': 'changed'}),
          command('attr', {'selector': '#field', 'name': 'value'}, expect='original'),
          command('attr', {'selector': '#field', 'name': 'data-empty'}, expect=''),
          command('attr', {'selector': '#field', 'name': 'absent'}, expect=None), check('field.value', 'changed'),
          command('html', {'selector': '#field'}, verify="result.startsWith('<input') && result.includes('value=\"original\"')")])


def form_cases():
    for kind, values in {
        'text': ['', 'replacement', ' héllo 日本語 🎉 مرحبا '], 'search': ['query'],
        'tel': ['+1 555 0100'], 'password': ['p@ss-秘密'], 'email': ['qa@example.test', 'invalid'],
        'url': ['https://example.test/a?q=1', 'invalid'], 'number': ['0', '-12', '1.5', '1e3'],
        'range': ['0', '50', '100'], 'date': ['2024-02-29'], 'month': ['2026-10'],
        'week': ['2026-W44'], 'time': ['13:45'], 'datetime-local': ['2026-10-28T13:45'],
        'color': ['#336699'],
    }.items():
        for n, value in enumerate(values):
            html = f'<label for="field">Value</label><input id="field" type="{kind}" min="0" max="100"><input id="neighbor" value="untouched">'
            if kind not in ('range',):
                html = html.replace(' min="0" max="100"', '')
            case(f'input-{kind}-{n+1}', f'Fill {kind}: {value!r}', 'Inputs', html,
                 [command('fill', {'selector': '#field', 'value': value}, expect=None),
                  check('field.value', value), check('neighbor.value', 'untouched'),
                  check("__lab.events.filter(e=>e.target==='field'&&e.type==='input').length", 1),
                  check("__lab.events.filter(e=>e.target==='field'&&e.type==='change').length", 1)],
                 requires=[{'expression': f"field.type==='{kind}'", 'reason': f'Native input type {kind} is not supported by this engine'}])
    for id, html, value in [
        ('textarea', '<textarea id="field">old</textarea>', 'line one\nline two\tend'),
        ('contenteditable', '<div id="field" contenteditable>old <b>markup</b></div>', 'new content'),
        ('empty-contenteditable', '<div id="field" contenteditable></div>', 'héllo 🎉'),
        ('plaintext', '<div id="field" contenteditable="plaintext-only">old</div>', 'new content'),
    ]:
        case('fill-' + id, 'Replace ' + id + ' contents', 'Inputs', html,
             [command('fill', {'selector': '#field', 'value': value}),
              check("field.isContentEditable ? field.textContent : field.value", value)],
             requires=([{'expression': 'field.isContentEditable', 'reason': 'plaintext-only contenteditable unsupported'}] if id=='plaintext' else []))
    for value, id in [('abc', 'ascii'), ('a🎉b', 'emoji'), ('é', 'combining'), ('', 'empty'), ('+', 'plus')]:
        case('type-' + id, 'Type ' + id + ' text with per-character events', 'Keyboard', '<input id="field" value="start:">',
             [command('type', {'selector': '#field', 'text': value}), check('field.value', 'start:' + value),
              check("__lab.events.filter(e=>e.target==='field'&&e.type==='input').length", len(value))])
    for disabled, html in [('control', '<input id="field" disabled value="unchanged">'),
                           ('fieldset', '<fieldset disabled><input id="field" value="unchanged"></fieldset>')]:
        case('fill-disabled-' + disabled, 'Reject a disabled ' + disabled, 'Inputs', html,
             [command('fill', {'selector': '#field', 'value': 'bad', 'timeout': 150}, error='disabled'),
              check('field.value', 'unchanged'), check("__lab.events.filter(e=>e.type==='input').length", 0)])
    case('fieldset-legend', 'First legend control remains enabled in a disabled fieldset', 'Inputs',
         '<fieldset disabled><legend><input id="field"></legend><input id="other"></fieldset>',
         [command('fill', {'selector': '#field', 'value': 'allowed'}), check('field.value', 'allowed'), check('other.value', '')])
    case('readonly', 'Readonly input should resist editing', 'Inputs', '<input id="field" readonly value="original">',
         [command('fill', {'selector': '#field', 'value': 'changed', 'timeout': 150}, error=''), check('field.value', 'original')], contract='probe')
    case('fill-wrong-target', 'A noneditable paragraph rejects fill', 'Inputs', '<p id="field">unchanged</p>',
         [command('fill', {'selector': '#field', 'value': 'bad'}, error='not editable'), check('field.textContent', 'unchanged')])
    case('fill-form-partial', 'A form batch stops at its first failed field', 'Forms',
         '<input id="first"><p id="wrong">text</p><input id="last">',
         [command('fill_form', {'fields': [{'selector':'#first','value':'saved'}, {'selector':'#wrong','value':'bad'}, {'selector':'#last','value':'later'}]}, error='not editable'),
          check('[first.value,last.value]', ['saved', ''])])
    form = '<form id="form"><input id="field" name="q" required><input name="token" type="hidden" value="fixture"><button id="submit">Submit</button><button id="reset" type="reset">Reset</button></form>'
    setup = "__lab.state.submits=0; form.addEventListener('submit',e=>{e.preventDefault();__lab.state.submits++;__lab.state.values=Object.fromEntries(new FormData(form))})"
    case('form-invalid', 'Required validation prevents submission', 'Forms', form,
         [command('click', {'selector': '#submit'}), check('__lab.state.submits', 0), check('field.validity.valueMissing', True)], setup=setup)
    case('form-enter', 'Enter submits valid form once, including hidden fields', 'Forms', form,
         [command('type', {'selector': '#field', 'text': 'value', 'submit': True}), check('__lab.state.submits', 1),
          check('__lab.state.values', {'q': 'value', 'token': 'fixture'}), command('title', verify="result.includes('form-enter')")], setup=setup)
    case('form-reset', 'Reset restores initial value and checked state', 'Forms',
         '<form><input id="field" value="default"><input id="box" type="checkbox" checked><button id="reset" type="reset">Reset</button></form>',
         [command('fill', {'selector': '#field', 'value': 'changed'}), command('check', {'selector': '#box', 'checked': False}),
          command('click', {'selector': '#reset'}), check('[field.value,box.checked]', ['default', True])])
    case('form-associated', 'An external form-associated input participates in submission', 'Forms',
         '<form id="form"><button id="submit">Submit</button></form><input id="field" form="form" name="q">',
         [command('fill', {'selector': '#field', 'value': 'external'}), command('click', {'selector': '#submit'}),
          check('__lab.state.values', {'q':'external'})], setup=setup)


def select_check_cases():
    html = '<select id="choices"><option value="a">Alpha</option><option value="b">Beta</option><option value="c">Gamma</option></select>'
    for id, value, expected in [('value', 'b', ['b']), ('text', 'Beta', ['b']), ('case', 'c', ['c'])]:
        case('select-' + id, 'Select by ' + id, 'Selects', html,
             [command('select', {'selector': '#choices', 'value': value}, expect=expected),
              check('[...choices.selectedOptions].map(o=>o.value)', expected),
              check("__lab.events.filter(e=>e.type==='change').length", 1)])
    case('select-multi', 'Multiselect accepts a mixture of values and text', 'Selects', html.replace('<select ', '<select multiple '),
         [command('select', {'selector':'#choices','value':['a','Gamma']}, expect=['a','c']),
          check('[...choices.selectedOptions].map(o=>o.value)', ['a','c'])])
    case('select-invalid-multi', 'Missing multiselect option leaves state and events untouched', 'Selects',
         html.replace('<select ', '<select multiple ').replace('value="a"', 'value="a" selected'),
         [command('select', {'selector':'#choices','value':['b','missing']}, error='no option matches'),
          check('[...choices.selectedOptions].map(o=>o.value)', ['a']),
          check("__lab.events.filter(e=>['input','change'].includes(e.type)).length", 0),
          command('select', {'selector':'#choices','value':['b']}, expect=['b'])])
    case('select-clear', 'Empty array clears a multiselect', 'Selects', html.replace('<select ', '<select multiple '),
         [command('select', {'selector':'#choices','value':['a','b']}), command('select', {'selector':'#choices','value':[]}, expect=[]),
          check('choices.selectedOptions.length', 0)])
    for id, options, value, expected in [
        ('label-override', '<option value="a">Initial</option><option value="b" label="Visible label">Source text</option>', 'Visible label', ['b']),
        ('nbsp', '<option value="a">Initial</option><option value="b">Alpha\u00a0Beta</option>', 'Alpha Beta', ['b']),
        ('zero-width', '<option value="a">Initial</option><option value="b">Zero\u200bWidth</option>', 'ZeroWidth', ['b']),
    ]:
        case('select-' + id, 'Option naming compatibility: ' + id, 'Selects', '<select id="choices">'+options+'</select>',
             [command('select', {'selector':'#choices','value':value}, expect=expected),
              check('[...choices.selectedOptions].map(o=>o.value)', expected)], contract='probe')
    case('select-case-sensitive', 'Option values remain case-sensitive', 'Selects',
         '<select id="choices"><option value="US">Upper</option><option value="us">Lower</option></select>',
         [command('select', {'selector':'#choices','value':'us'}, expect=['us']), check('choices.value', 'us')])
    case('select-empty-value', 'Empty-string option values are selectable', 'Selects',
         '<select id="choices"><option value="a">Alpha</option><option value="">Placeholder</option></select>',
         [command('select', {'selector':'#choices','value':''}, expect=['']), check('choices.value', '')])
    case('checkbox-idempotent', 'Check and uncheck are idempotent', 'Checkboxes', '<input id="box" type="checkbox">',
         [command('check', {'selector':'#box'}, expect=True), command('check', {'selector':'#box'}, expect=True),
          check("__lab.events.filter(e=>e.type==='change').length", 1),
          command('check', {'selector':'#box','checked':False}, expect=False), command('check', {'selector':'#box','checked':False}, expect=False),
          check("__lab.events.filter(e=>e.type==='change').length", 2)])
    case('radio-group', 'Radio selection only changes its own group', 'Checkboxes',
         '<input id="a" name="g" type="radio" checked><input id="b" name="g" type="radio"><input id="other" name="h" type="radio" checked>',
         [command('check', {'selector':'#b'}, expect=True), check('[a.checked,b.checked,other.checked]', [False,True,True])])
    case('checkbox-cancelled', 'Canceled checkbox activation reports actual state', 'Checkboxes', '<input id="box" type="checkbox">',
         [command('check', {'selector':'#box'}, expect=False), check('box.checked', False)], setup="box.onclick=e=>e.preventDefault()")
    case('checkbox-hidden-label', 'Visible label activates its hidden native checkbox', 'Checkboxes',
         '<label id="label" for="box">Accept</label><input id="box" type="checkbox" style="display:none">',
         [command('click', {'selector':'#label'}), check('box.checked', True)])
    case('checkbox-aria-click', 'Clicking a custom ARIA checkbox changes application state', 'Checkboxes',
         '<div id="box" role="checkbox" tabindex="0" aria-checked="false" onclick="this.setAttribute(\'aria-checked\',String(this.getAttribute(\'aria-checked\')!==\'true\'))">Custom</div>',
         [command('click', {'selector':'#box'}), command('attr', {'selector':'#box','name':'aria-checked'}, expect='true'),
          command('check', {'selector':'#box','timeout':200}, error='not a checkbox')])


def all_cases():
    if not CASES:
        identity_cases()
        snapshot_cases()
        form_cases()
        select_check_cases()
        # Imported lazily so the small definition helpers can be shared.
        from . import interactions, lifecycle
        interactions.populate()
        lifecycle.populate()
    return CASES
