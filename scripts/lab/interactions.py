"""Hit testing, event traces, composed trees, graphics, and framework fixtures."""
from .cases import case, command, evaluate, check


def populate():
    hit_testing()
    events_and_files()
    composed_trees()
    rendering()
    frameworks_and_workflows()


def hit_testing():
    target = '<button id="target" onclick="__lab.state.clicks++">Target</button><button id="neighbor" onclick="__lab.state.neighbor++">Neighbor</button>'
    setup = '__lab.state={clicks:0,neighbor:0};'
    for id, css, error in [
        ('display-none', '#target{display:none}', ''),
        ('hidden', '#target{visibility:hidden}', ''),
        ('ancestor-hidden', 'section{display:none}', ''),
        ('outside', '#target{position:absolute;left:-9999px}', 'outside the viewport'),
        ('pointer-none', '#target{pointer-events:none}', 'covered'),
    ]:
        case('hit-' + id, 'Reject unreachable target: ' + id, 'Hit testing', '<section>'+target+'</section>',
             [command('click', {'selector':'#target','timeout':150}, error=error),
              check('[__lab.state.clicks,__lab.state.neighbor]', [0,0])], css=css, setup=setup)
    for id, css in [('opacity-zero', '#target{opacity:0}'),
                    ('transformed', '#target{transform:translate(100px,80px) scale(1.4)}'),
                    ('below-fold', '#target{margin-top:1800px}'),
                    ('contents', 'section{display:contents}'),
                    ('rtl', 'body{direction:rtl}'),
                    ('vertical', 'section{writing-mode:vertical-rl}')]:
        case('hit-' + id, 'Activate target with ' + id, 'Hit testing', '<section>'+target+'</section>',
             [command('click', {'selector':'#target'}), check('[__lab.state.clicks,__lab.state.neighbor]', [1,0])], css=css, setup=setup)
    for layout in ('flex', 'grid', 'table', 'inline-block', 'flow-root'):
        case('layout-' + layout, 'Target identity in ' + layout + ' layout', 'CSS layout', '<section>'+target+'</section>',
             [command('click', {'selector':'#neighbor'}), check('[__lab.state.clicks,__lab.state.neighbor]', [0,1]),
              command('rect', {'selector':'#neighbor'}, verify='result.width>0 && result.height>0')],
             css=f'section{{display:{layout};gap:16px}}', setup=setup)
    for id, css in [('float', '#target{float:right}'), ('columns', 'section{columns:2}'),
                    ('logical', '#target{margin-inline-start:80px;padding-block:20px}'),
                    ('custom-property', ':root{--gap:40px}#target{margin-left:var(--gap)}'),
                    ('content-visibility', 'section{content-visibility:auto;contain-intrinsic-size:200px}')]:
        case('layout-' + id, 'Target identity with ' + id, 'CSS layout', '<section>'+target+'</section>',
             [command('click', {'selector':'#target'}), check('[__lab.state.clicks,__lab.state.neighbor]', [1,0])], css=css, setup=setup)
    overlay = target + '<div id="overlay"></div>'
    overlay_css = '#overlay{position:fixed;inset:0;background:transparent;z-index:10}'
    case('hit-overlay', 'Transparent pointer-active overlay blocks the target', 'Hit testing', overlay,
         [command('click', {'selector':'#target','timeout':150}, error='covered'),
          check('[__lab.state.clicks,__lab.state.neighbor]', [0,0]), evaluate('overlay.remove()'),
          command('click', {'selector':'#target'}), check('__lab.state.clicks', 1)], css=overlay_css, setup=setup)
    case('hit-overlay-pass-through', 'Pointer-inactive overlay allows the target click', 'Hit testing', overlay,
         [command('click', {'selector':'#target'}), check('__lab.state.clicks', 1)], css=overlay_css+'#overlay{pointer-events:none}', setup=setup)
    case('hit-force', 'Force explicitly bypasses an overlay', 'Hit testing', overlay,
         [command('click', {'selector':'#target','force':True}), check('[__lab.state.clicks,__lab.state.neighbor]', [1,0])], css=overlay_css, setup=setup)
    case('hit-overlay-release', 'Waiting click completes once an overlay is released', 'Hit testing', overlay,
         [command('click', {'selector':'#target','timeout':4000}, send='pending'),
          evaluate('overlay.remove()'), {'await':'pending'}, check('__lab.state.clicks', 1)], css=overlay_css, setup=setup)
    case('hit-nested-scroll', 'Nested containers scroll to the intended target', 'Hit testing',
         '<div id="outer"><div class="spacer"></div><div id="inner"><div class="spacer"></div>'+target+'</div></div>',
         [command('click', {'selector':'#target'}), check('__lab.state.clicks', 1),
          check('outer.scrollTop>0 && inner.scrollTop>0')],
         css='#outer,#inner{height:180px;overflow:auto;border:1px solid} .spacer{height:1000px}', setup=setup)
    case('hit-hidden-override', 'CSS can override the hidden attribute rendering', 'Hit testing',
         target.replace('id="target"', 'id="target" hidden'),
         [command('click', {'selector':'#target'}), check('__lab.state.clicks', 1)], css='#target{display:inline-block}', setup=setup)
    case('hit-details', 'Opening details reveals its control', 'Hit testing',
         '<details><summary id="summary">Expand</summary>'+target+'</details>',
         [command('click', {'selector':'#target','timeout':150}, error=''), command('click', {'selector':'#summary'}),
          command('click', {'selector':'#target'}), check('__lab.state.clicks', 1)], setup=setup)
    case('hit-inert', 'Inert background rejects interactive actions', 'Hit testing', '<section inert>'+target+'</section>',
         [command('click', {'selector':'#target','timeout':150}, error=''), check('__lab.state.clicks', 0)], setup=setup, contract='probe')
    case('hit-coordinate', 'A coordinate click on an icon bubbles to its button once', 'Hit testing',
         '<button id="target" onclick="__lab.state.clicks++"><span id="icon">Icon</span></button>',
         [command('rect', {'selector':'#icon'}, capture={'x':'result.x+result.width/2','y':'result.y+result.height/2'}),
          command('click', {'x':'{{x}}','y':'{{y}}'}), check('__lab.state.clicks', 1),
          check("__lab.events.filter(e=>e.type==='click')[0].target", 'icon')], setup=setup)
    case('hit-svg-stroke', 'SVG stroke remains interactive with zero geometric height', 'Hit testing',
         '<svg width="400" height="100"><line id="line" x1="20" y1="50" x2="380" y2="50" stroke="red" stroke-width="12" onclick="__lab.state.clicks++"/></svg>',
         [command('click', {'selector':'#line'}), check('__lab.state.clicks', 1)], setup=setup, contract='probe')


def events_and_files():
    case('event-click-order', 'Click produces one activation and ordered mouse events', 'Events', '<button id="target">Click</button>',
         [command('click', {'selector':'#target'}),
          check("__lab.events.filter(e=>e.target==='target'&&['mousedown','mouseup','click'].includes(e.type)).map(e=>e.type)", ['mousedown','mouseup','click']),
          check("__lab.events.filter(e=>e.type==='click').every(e=>e.trusted===false)")])
    case('event-propagation', 'Capture, target, and bubble listeners fire in order', 'Events', '<section id="container"><button id="target">Click</button></section>',
         [command('click', {'selector':'#target'}), check('__lab.state.order', ['capture','target','bubble'])],
         setup="__lab.state.order=[];container.addEventListener('click',()=>__lab.state.order.push('capture'),true);target.onclick=()=>__lab.state.order.push('target');container.addEventListener('click',()=>__lab.state.order.push('bubble'));")
    case('event-stop-propagation', 'Stopped propagation does not activate the parent', 'Events', '<section id="container"><button id="target">Click</button></section>',
         [command('click', {'selector':'#target'}), check('__lab.state.parent', 0)],
         setup="__lab.state.parent=0;container.onclick=()=>__lab.state.parent++;target.onclick=e=>e.stopPropagation()")
    for key, expected in [('Control+k', ['k',True,False,False,False]), ('Shift+A',['A',False,True,False,False]),
                          ('Alt+x',['x',False,False,True,False]), ('Meta+k',['k',False,False,False,True])]:
        case('key-' + key.lower().replace('+','-'), 'Keyboard modifiers: ' + key, 'Keyboard', '<input id="field">',
             [command('press', {'selector':'#field','key':key}), check('__lab.state.key', expected)],
             setup='field.onkeydown=e=>{__lab.state.key=[e.key,e.ctrlKey,e.shiftKey,e.altKey,e.metaKey];e.preventDefault()}')
    case('key-cancelled-press', 'Canceled printable press does not insert text', 'Keyboard', '<input id="field" value="start">',
         [command('press', {'selector':'#field','key':'x'}), check('field.value','start')], setup='field.onkeydown=e=>e.preventDefault()')
    case('key-cancelled-type', 'Canceled keydown should suppress typed insertion', 'Keyboard', '<input id="field" value="start">',
         [command('type', {'selector':'#field','text':'x'}), check('field.value','start')], setup='field.onkeydown=e=>e.preventDefault()', contract='probe')
    case('key-caret', 'Typing with a middle caret follows native editing semantics', 'Keyboard', '<input id="field" value="ac">',
         [evaluate('field.focus();field.setSelectionRange(1,1)'), command('type', {'selector':'#field','text':'b'}), check('field.value','abc')], contract='probe')
    case('key-backspace', 'Backspace removes the preceding character', 'Keyboard', '<input id="field" value="abc">',
         [evaluate('field.focus();field.setSelectionRange(3,3)'), command('press', {'key':'Backspace'}), check('field.value','ab')], contract='probe')
    case('hover-js', 'Synthetic hover opens a JavaScript menu', 'Events', '<button id="target">Hover</button><div id="menu" hidden>Menu</div>',
         [command('hover', {'selector':'#target'}), check('menu.hidden',False)], setup='target.onmouseenter=()=>menu.hidden=false')
    case('hover-css', 'Synthetic hover leaves native hover state unchanged', 'Events', '<button id="target">Hover</button>',
         [evaluate("__lab.state.before=target.matches(':hover')"), command('hover', {'selector':'#target'}), check("target.matches(':hover')===__lab.state.before")],
         description='Bruster dispatches DOM hover events; it does not move the OS pointer or emulate CSS :hover.')
    drag = '<div id="source" draggable="true">Source</div><div id="dest">Destination</div>'
    setup = "__lab.state.drops=0;source.ondragstart=e=>e.dataTransfer.setData('text/plain','payload 🎉');dest.ondragover=e=>e.preventDefault();dest.ondrop=e=>{__lab.state.drops++;__lab.state.payload=e.dataTransfer.getData('text/plain')}"
    case('drag-html5', 'HTML5 drag transfers one exact payload', 'Drag and drop', drag,
         [command('drag', {'from':{'selector':'#source'},'to':{'selector':'#dest'}}), check('__lab.state.drops',1), check('__lab.state.payload','payload 🎉'),
          check("__lab.events.filter(e=>['dragstart','dragenter','dragover','drop','dragend'].includes(e.type)).map(e=>e.type)", ['dragstart','dragenter','dragover','drop','dragend'])],
         css='#source,#dest{display:inline-block;margin:30px;padding:30px;border:2px solid}', setup=setup)
    case('drag-cancelled', 'Canceling dragstart should prevent the drop', 'Drag and drop', drag,
         [command('drag', {'from':{'selector':'#source'},'to':{'selector':'#dest'}}), check('__lab.state.drops',0)],
         setup=setup+';source.ondragstart=e=>e.preventDefault()', contract='probe')
    case('drag-pointer-slider', 'Pointer-driven dragging changes actual slider position', 'Drag and drop', drag,
         [command('drag', {'from':{'selector':'#source'},'to':{'selector':'#dest'}}), check('__lab.state.moved',True)],
         setup="__lab.state.moved=false;source.onpointerdown=e=>source.setPointerCapture(e.pointerId);source.onpointermove=e=>{if(e.buttons===1)__lab.state.moved=true}", contract='probe',
         description='Capability probe for native pointer capture and movement; Bruster currently promises HTML5 drag events.')
    for id, html, paths, names, sizes in [
        ('single','<input id="file" type="file">',['{{textFile}}'],['sample.txt'],[6]),
        ('multiple','<input id="file" type="file" multiple>',['{{textFile}}','{{binaryFile}}'],['sample.txt','bytes.bin'],[6,256]),
        ('hidden','<input id="file" type="file" hidden>',['{{textFile}}'],['sample.txt'],[6]),
        ('empty-file','<input id="file" type="file">',['{{emptyFile}}'],['empty.txt'],[0]),
        ('unicode-name','<input id="file" type="file">',['{{unicodeFile}}'],['résumé-日本.txt'],[6]),
    ]:
        case('upload-' + id, 'Upload ' + id, 'Uploads', html,
             [command('upload', {'selector':'#file','paths':paths}, expect=names),
              check('[...file.files].map(f=>f.size)',sizes),
              check("__lab.events.filter(e=>['input','change'].includes(e.type)).map(e=>e.type)",['input','change']),
              check('await file.files[0].text()', '' if id=='empty-file' else 'hello\n')])
    case('upload-binary', 'Uploaded binary contents are byte-for-byte intact', 'Uploads','<input id="file" type="file">',
         [command('upload', {'selector':'#file','paths':['{{binaryFile}}']}),
          check('Array.from(new Uint8Array(await file.files[0].arrayBuffer()))', list(range(256)))])
    case('upload-clear', 'Upload replaces and clears the file list', 'Uploads','<input id="file" type="file" multiple>',
         [command('upload', {'selector':'#file','paths':['{{textFile}}','{{binaryFile}}']}),
          command('upload', {'selector':'#file','paths':['{{emptyFile}}']}, expect=['empty.txt']),
          command('upload', {'selector':'#file','paths':[]}, expect=[]), check('file.files.length',0)])
    case('upload-missing', 'Missing files report errors without losing the previous upload', 'Uploads','<input id="file" type="file">',
         [command('upload', {'selector':'#file','paths':['{{textFile}}']}),
          command('upload', {'selector':'#file','paths':['{{missingFile}}']}, error='upload'), check('file.files[0].name','sample.txt')])


def composed_trees():
    case('shadow-open', 'Selectors and refs reach open shadow roots', 'Composed trees','<div id="host"></div>',
         [command('snapshot', {'format':'json'}, capture={'ref':"result.elements.find(e=>e.name==='Inside').ref"}),
          command('click', {'ref':'{{ref}}'}), check('__lab.state.clicks',1), command('count',{'selector':'#inside'},expect=1)],
         setup="__lab.state.clicks=0;host.attachShadow({mode:'open'}).innerHTML='<button id=inside onclick=\"window.__lab.state.clicks++\">Inside</button>'")
    case('shadow-scope', 'Host-scoped snapshot includes its own shadow root', 'Composed trees','<div id="host"></div><button>Outside</button>',
         [command('snapshot', {'selector':'#host','format':'json'}, verify="result.elements.some(e=>e.name==='Inside') && !result.elements.some(e=>e.name==='Outside')")],
         setup="host.attachShadow({mode:'open'}).innerHTML='<button>Inside</button>'", contract='probe')
    for depth in (1,5,20):
        case(f'shadow-depth-{depth}', f'Traverse {depth} nested open shadow roots', 'Composed trees','<div id="host"></div>',
             [command('click',{'selector':'#deep'}),check('__lab.state.clicked',True)],
             setup=f"let h=host;for(let i=0;i<{depth};i++){{const r=h.attachShadow({{mode:'open'}});r.innerHTML='<div></div>';h=r.firstChild}}h.innerHTML='<button id=deep onclick=\"window.__lab.state.clicked=true\">Deep</button>'")
    case('shadow-closed', 'Closed shadow contents stay outside selector traversal', 'Composed trees','<div id="host"></div><button id="outside">Outside</button>',
         [command('count',{'selector':'#closed'},expect=0),command('click',{'selector':'#outside'})],
         setup="host.attachShadow({mode:'closed'}).innerHTML='<button id=closed>Closed</button>'")
    case('shadow-slots', 'Slotted controls remain actionable without duplicate discovery', 'Composed trees','<div id="host"><button id="slotted" onclick="__lab.state.clicked=true">Slotted</button></div>',
         [command('count',{'selector':'#slotted'},expect=1),command('click',{'selector':'#slotted'}),check('__lab.state.clicked',True)],
         setup="host.attachShadow({mode:'open'}).innerHTML='<section><slot></slot></section>'")
    frame = '<iframe id="frame" title="Fixture frame" src="../support/frame.html"></iframe>'
    ready = evaluate("await new Promise(resolve=>{if(frame.contentDocument?.readyState==='complete'&&frame.contentDocument.getElementById('inside'))resolve();else frame.addEventListener('load',resolve,{once:true})})")
    case('frame-same-origin', 'Same-origin frame controls work through selector and reference', 'Composed trees',frame,
         [ready,command('count',{'selector':'#inside'},expect=1),command('click',{'selector':'#inside'}),
          check('frame.contentWindow.clicks',1),command('snapshot',{'format':'json'},capture={'ref':"result.elements.find(e=>e.name==='Frame button').ref"}),
          command('click',{'ref':'{{ref}}'}),check('frame.contentWindow.clicks',2)])
    case('frame-replaced-ref', 'Frame replacement invalidates child references', 'Composed trees',frame,
         [ready,command('snapshot',{'format':'json'},capture={'ref':"result.elements.find(e=>e.name==='Frame button').ref"}),
          evaluate("await new Promise(resolve=>{frame.onload=resolve;frame.src='../support/frame.html?second'})"),
          command('click',{'ref':'{{ref}}','timeout':150},error='stale or unknown ref'),check('frame.contentWindow.clicks',0)])
    case('frame-offset-rect', 'Frame descendant rectangles use the top-level viewport', 'Composed trees',frame,
         [ready,command('rect',{'selector':'#inside'},verify="Math.abs(result.x-(frame.getBoundingClientRect().x+frame.clientLeft+frame.contentDocument.getElementById('inside').getBoundingClientRect().x))<=1")],
         css='#frame{margin:120px;border:4px solid;width:400px;height:250px}', contract='probe')
    case('frame-cross-origin', 'Cross-origin child is inaccessible while parent remains usable', 'Composed trees','<iframe id="frame" title="Cross-origin frame"></iframe><button id="parentButton">Parent</button>',
         [command('count',{'selector':'#inside'},expect=0),command('click',{'selector':'#parentButton'}),check('frame.contentDocument',None)],
         setup="await new Promise(resolve=>{frame.onload=resolve;frame.src=__lab.server.otherOrigin+__lab.sitePath+'support/frame.html'})", requires=['server'])
    case('frame-sandbox', 'Opaque sandbox frame does not leak into traversal', 'Composed trees',
         '<iframe sandbox="allow-scripts" title="Sandbox" srcdoc="<button id=opaque>Opaque</button>"></iframe>',
         [command('count',{'selector':'#opaque'},expect=0)])


def rendering():
    for width in (480,960):
        case(f'responsive-{width}', f'Responsive breakpoint at viewport {width}', 'Rendering','<div id="box">Responsive</div>',
             [command('resize',{'width':width,'height':640}),
              evaluate("await new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)))"),
              check('innerWidth',width),check('getComputedStyle(box).color','rgb(255, 0, 0)' if width<600 else 'rgb(0, 0, 255)')],
             css='#box{color:blue}@media(max-width:599px){#box{color:red}}')
    case('container-query', 'Container queries respond to their container width', 'Rendering', '<section id="container"><span id="child">Content</span></section>',
         [check('getComputedStyle(child).color','rgb(255, 0, 0)'),evaluate("container.style.width='400px';await new Promise(r=>requestAnimationFrame(r))"),
          check('getComputedStyle(child).color','rgb(0, 0, 255)')],
         css='#container{container-type:inline-size;width:200px}#child{color:blue}@container(max-width:250px){#child{color:red}}',
         requires=[{'expression':"CSS.supports('container-type','inline-size')",'reason':'Container queries unsupported'}])
    case('screenshot-quadrants', 'Screenshot pixels contain the current viewport content', 'Screenshots','<div id="red"></div><div id="green"></div><div id="blue"></div><div id="white"></div>',
         [command('screenshot', image={'samples':[[50,50,[255,0,0]],[250,50,[0,128,0]],[50,250,[0,0,255]],[250,250,[255,255,255]]],'minWidth':400,'minHeight':400})],
         css='body{margin:0;display:grid;grid-template-columns:200px 200px}body>div{width:200px;height:200px}#red{background:red}#green{background:green}#blue{background:blue}#white{background:white}')
    case('screenshot-canvas-update', 'Native capture reflects a canvas update', 'Screenshots','<canvas id="canvas" width="300" height="300"></canvas>',
         [evaluate("canvas.getContext('2d').fillStyle='red';canvas.getContext('2d').fillRect(0,0,300,300);await new Promise(r=>requestAnimationFrame(r))"),
          command('screenshot', image={'samples':[[80,80,[255,0,0]]]}),
          evaluate("canvas.getContext('2d').fillStyle='blue';canvas.getContext('2d').fillRect(0,0,300,300);await new Promise(r=>requestAnimationFrame(r))"),
          command('screenshot', image={'samples':[[80,80,[0,0,255]]]})], css='body{margin:0}')
    case('screenshot-clip', 'A clip contains the intended element pixels', 'Screenshots','<div id="box"></div>',
         [command('rect',{'selector':'#box'},capture={'clip':'result'}),command('screenshot',{'clip':'{{clip}}'},image={'cssWidth':100,'cssHeight':80,'samples':[[30,30,[255,0,0]]]})],
         css='#box{width:100px;height:80px;background:red}',requires=['clip'])
    case('screenshot-clip-windows', 'Windows explicitly rejects screenshot clipping', 'Screenshots','<p>Clip support</p>',
         [command('screenshot',{'clip':{'x':0,'y':0,'width':100,'height':100}},error='not supported')],requires=['windows'])
    case('screenshot-full-restore', 'Full-page capture includes the lower page and restores viewport', 'Screenshots','<div id="tall"></div>',
         [evaluate('[innerWidth,innerHeight]',capture={'size':'result'}),command('screenshot',{'full':True},image={'minHeight':1200}),
          evaluate('await __lab.until(()=>innerHeight===640);return [innerWidth,innerHeight]',expect=[960,640])],
         css='#tall{height:1400px;background:linear-gradient(red,blue)}',requires=['linux'])
    case('image-decoded', 'Image readiness includes successful decoding', 'Rendering','<img id="image" src="../assets/pattern.svg" alt="Fixture pattern">',
         [evaluate('await image.decode();return image.naturalWidth',expect=160),command('screenshot',image={'minWidth':100})])
    case('image-broken', 'Broken image has zero natural width and useful alt text', 'Rendering','<img id="image" src="../assets/intentionally-missing.png" alt="Unavailable illustration">',
         [check('image.complete && image.naturalWidth===0'),command('snapshot',{'format':'json'},verify="result.elements.some(e=>e.name==='Unavailable illustration')")])
    case('render-mathml', 'MathML remains visible and surrounding controls work', 'Rendering',
         '<math><mfrac><mn>1</mn><mn>2</mn></mfrac></math><button id="target" onclick="__lab.state.clicked=true">Continue</button>',
         [command('screenshot',image={'minWidth':100}),command('click',{'selector':'#target'}),check('__lab.state.clicked',True)])
    case('render-media', 'Media elements expose stable poster and playback state', 'Rendering',
         '<video id="video" controls poster="../assets/pattern.svg" width="320"></video><audio id="audio" controls></audio>',
         [check('video.paused && audio.paused'),command('screenshot',image={'minWidth':320})],
         requires=[{'expression':"typeof HTMLMediaElement==='function' && video instanceof HTMLMediaElement && audio instanceof HTMLMediaElement",
                    'reason':'Native media elements unavailable in this engine/runtime'}])
    case('color-scheme', 'Dark and light set the documented page color scheme', 'Rendering','<input id="field">',
         [command('dark'),check('getComputedStyle(document.documentElement).colorScheme','dark'),
          command('light'),check('getComputedStyle(document.documentElement).colorScheme','light')])
    for width,height in [(0,640),(960,0),(16001,1)]:
        case(f'resize-invalid-{width}-{height}', f'Reject viewport {width}×{height}', 'Boundaries','<p>Viewport</p>',
             [command('resize',{'width':width,'height':height},error='between'),command('resize',{'width':960,'height':640},expect={'width':960,'height':640})])


def frameworks_and_workflows():
    for framework in ('react','vue','svelte'):
        case('framework-' + framework, f'{framework} controlled input survives a rerender', 'Frameworks','<div id="app"></div>',
             [command('fill',{'selector':'#field','value':'héllo controlled'}),
              command('click',{'selector':'#rerender'}),
              evaluate("await __lab.until(()=>document.getElementById('model').textContent==='héllo controlled')"),
              check("document.getElementById('field').value",'héllo controlled'),
              command('click',{'selector':'#submit'}),check('__lab.state.submitted','héllo controlled')],
             scripts=[f'frameworks/{framework}.js'],requires=['framework:'+framework],
             setup="await __lab.until(()=>document.getElementById('field'))")
    case('workflow-search', 'Search selects the correct item despite duplicate names', 'Workflows',
         '<input id="query" aria-label="Search"><button id="search">Search</button><div id="results"></div>',
         [command('fill',{'selector':'#query','value':'blue'}),command('click',{'selector':'#search'}),
          command('wait_for',{'selector':'#item-2'}),command('click',{'selector':'#item-2'}),check('__lab.state.selected',2)],
         setup="search.onclick=()=>{results.innerHTML='<button id=item-1>Blue backpack $70</button><button id=item-2>Blue backpack $50</button>';results.onclick=e=>{if(e.target.id.startsWith('item-'))__lab.state.selected=Number(e.target.id.slice(5))}}")
    case('workflow-decoy-login', 'Visible login fields receive values while hidden decoys stay untouched', 'Workflows',
         '<input name="email" hidden value="decoy"><form id="login"><label>Email<input id="email" name="email"></label><label>Password<input id="password" name="password" type="password"></label><button id="submit">Sign in</button></form>',
         [command('snapshot',{'format':'json'},capture={'emailRef':"result.elements.find(e=>e.role==='textbox'&&e.name==='Email').ref"}),
          command('fill',{'ref':'{{emailRef}}','value':'qa@example.test'}),command('fill',{'selector':'#password','value':'fixture-only'}),
          command('click',{'selector':'#submit'}),check('__lab.state.values',{'email':'qa@example.test','password':'fixture-only'}),
          check("document.querySelector('input[hidden]').value",'decoy'),check('__lab.state.submits',1)],
         setup="__lab.state.submits=0;login.onsubmit=e=>{e.preventDefault();__lab.state.submits++;__lab.state.values=Object.fromEntries(new FormData(login))}")
    case('workflow-modal-cancel', 'Canceling a modal edit preserves the record', 'Workflows',
         '<button id="edit">Edit record</button><dialog id="modal"><input id="field"><button id="cancel">Cancel</button><button id="save">Save</button></dialog>',
         [command('click',{'selector':'#edit'}),command('fill',{'selector':'#field','value':'changed'}),command('click',{'selector':'#cancel'}),check('__lab.state.record','original'),
          command('click',{'selector':'#edit'}),check('field.value','original'),command('fill',{'selector':'#field','value':'saved'}),command('click',{'selector':'#save'}),check('__lab.state.record','saved')],
         setup="__lab.state.record='original';edit.onclick=()=>{field.value=__lab.state.record;modal.showModal()};cancel.onclick=()=>modal.close();save.onclick=()=>{__lab.state.record=field.value;modal.close()}")
    case('workflow-virtualized', 'Recycled DOM nodes are rediscovered after virtual scrolling', 'Workflows',
         '<button id="next">Next records</button><div id="rows"></div>',
         [command('snapshot',{'format':'json'}),command('click',{'selector':'#next'}),command('find',{'text':'Record 12','format':'json'},capture={'ref':'result.elements[0].ref'}),
          command('click',{'ref':'{{ref}}'}),check('__lab.state.selected',12)],
         setup="const render=n=>{rows.innerHTML=Array.from({length:5},(_,i)=>'<button data-record='+ (n+i) +'>Record '+(n+i)+'</button>').join('')};render(0);next.onclick=()=>render(10);rows.onclick=e=>{if(e.target.dataset.record)__lab.state.selected=Number(e.target.dataset.record)}")
