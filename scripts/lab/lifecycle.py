"""Navigation, asynchronous behavior, HTTP contracts, storage, and diagnostics."""
from .cases import case, command, evaluate, check


def populate():
    waits()
    navigation()
    network()
    storage()
    diagnostics()
    stress()


def waits():
    for state in ('attached', 'visible'):
        case('wait-insert-' + state, 'Wait for an explicitly released ' + state + ' element', 'Waiting','<div id="mount"></div>',
             [command('wait_for',{'selector':'#late','state':state,'timeout':4000},send='wait'),
              evaluate("mount.innerHTML='<button id=late>Ready</button>'"),{'await':'wait'},
              command('click',{'selector':'#late'}),check("document.activeElement.id",'late')])
    case('wait-hidden-attached', 'Attached and visible are distinct states', 'Waiting','<button id="target" hidden>Target</button>',
         [command('wait_for',{'selector':'#target','state':'attached','timeout':200}),
          command('wait_for',{'selector':'#target','state':'visible','timeout':4000},send='wait'),
          evaluate('target.hidden=false'),{'await':'wait'},check('target.hidden',False)])
    case('wait-disappear', 'Hidden wait resolves after element removal', 'Waiting','<button id="target">Target</button>',
         [command('wait_for',{'selector':'#target','state':'hidden','timeout':4000},send='wait'),evaluate('target.remove()'),{'await':'wait'},command('count',{'selector':'#target'},expect=0)])
    case('wait-detached-ref', 'A detached reference must not satisfy attached', 'Waiting','<button id="target">Target</button>',
         [command('snapshot',{'format':'json'},capture={'ref':'result.elements[0].ref'}),evaluate('target.remove()'),
          command('wait_for',{'ref':'{{ref}}','state':'attached','timeout':150},error='')],contract='probe')
    case('wait-text', 'Text present and text gone follow explicit page transitions', 'Waiting','<p id="out"></p>',
         [command('wait_for',{'text':'Ready','timeout':4000},send='wait'),evaluate("out.textContent='Ready'"),{'await':'wait'},
          command('wait_for',{'textGone':'Ready','timeout':4000},send='gone'),evaluate("out.textContent=''"),{'await':'gone'},check('out.textContent','')])
    case('wait-timeout', 'A missing condition times out and leaves the session usable', 'Waiting','<p id="out">Healthy</p>',
         [command('wait_for',{'selector':'#missing','timeout':150},error='timed out'),command('text',{'selector':'#out'},expect='Healthy')])
    case('wait-zero-time', 'Explicit zero-duration wait completes immediately', 'Waiting','<p>Zero time</p>',
         [command('wait_for',{'time':0},expect=None)],contract='probe')
    for name, scheduling in [('promise',"Promise.resolve().then(change)"),('microtask','queueMicrotask(change)'),
                             ('timer','setTimeout(change,20)'),('animation','requestAnimationFrame(change)'),
                             ('observer',"new MutationObserver(change).observe(marker,{attributes:true});marker.dataset.trigger='yes'")]:
        case('async-' + name, 'Wait for a ' + name + ' DOM update', 'Async JavaScript','<button id="start">Start</button><div id="marker"></div><p id="out"></p>',
             [command('click',{'selector':'#start'}),command('wait_for',{'text':'Finished','timeout':5000}),check('out.textContent','Finished')],
             setup="const change=()=>out.textContent='Finished';start.onclick=()=>{"+scheduling+'}')
    case('request-late-reply', 'Expired running promise produces only one reply', 'Timeouts','<p>Promise fixture</p>',
         [command('eval',{'expression':'new Promise(resolve=>window.release=resolve)','request_timeout':150},error='timed out'),
          evaluate('release(42)'),check('21*2',42),{'assertNoDuplicateReplies':True}])
    case('request-zero', 'A zero-deadline operation never executes', 'Timeouts','<p>Zero deadline</p>',
         [command('eval',{'expression':'window.unexpected=true','request_timeout':0},error='timed out'),check('window.unexpected===undefined')])
    case('request-queued-expiry', 'Operation expiring behind navigation never runs afterward', 'Timeouts','<a id="link" href="../__lab/hang">Slow destination</a>',
         [command('click',{'selector':'#link'}),command('eval',{'expression':'window.expired=true','request_timeout':150},error='timed out'),
          command('navigate',{'url':'{{site}}support/other.html','timeout':5000}),check('window.expired===undefined')],requires=['server'])


def navigation():
    case('navigation-hash', 'Hash navigation keeps the document and updates URL', 'Navigation','<a id="link" href="#section">Section</a><p id="section">Section content</p>',
         [evaluate('window.marker=42'),command('click',{'selector':'#link'}),command('url',verify="result.endsWith('#section')"),check('window.marker',42)])
    case('navigation-history-state', 'Same-URL history restores the correct state object', 'Navigation','<p>History</p>',
         [evaluate("history.pushState({step:1},'',location.href);history.pushState({step:2},'',location.href)"),
          command('back'),check('history.state.step',1),command('forward'),check('history.state.step',2)])
    case('navigation-pushstate', 'PushState and back expose the correct URL and document', 'Navigation','<button id="go">Next</button>',
         [command('click',{'selector':'#go'}),command('url',verify="result.includes('route=next')"),command('back'),command('url',verify="!result.includes('route=next')")],
         setup="go.onclick=()=>history.pushState({},'', '?route=next')")
    case('navigation-same-url', 'Repeated same-URL navigation loads a fresh document', 'Navigation','<p>Reload me</p>',
         [evaluate('window.marker=42'),command('navigate',{'url':'{{caseUrl}}','timeout':5000}),check('window.marker===undefined')])
    case('navigation-cancelled', 'Canceled link navigation does not stall later calls', 'Navigation','<a id="link" href="../support/other.html">Stay</a>',
         [command('click',{'selector':'#link'}),command('url',verify="result.includes('navigation-cancelled')"),check('__lab.state.cancelled',True)],
         setup='link.onclick=e=>{e.preventDefault();__lab.state.cancelled=true}')
    case('navigation-reload', 'Reload discards document-local mutations', 'Navigation','<p>Reload</p>',
         [evaluate('window.marker=42'),command('reload'),check('window.marker===undefined')])
    case('navigation-redirect', 'HTTP redirects return the final URL', 'Navigation','<p>Redirect</p>',
         [command('navigate',{'url':'{{site}}__lab/redirect?count=3','timeout':5000}),command('url',verify="result.endsWith('/support/other.html')"),command('title',expect='Other fixture')],requires=['server'])
    case('navigation-dom', 'DOM navigation completes before a controlled slow image', 'Navigation','<p>Load milestones</p>',
         [command('navigate',{'url':'{{site}}__lab/slow-page','until':'dom','timeout':5000}),check('window.imageFinished',False),
          {'server':'release','gate':'image'},command('wait_for',{'text':'Image finished','timeout':5000})],requires=['server'])
    case('navigation-load', 'Load navigation waits for a gated subresource', 'Navigation','<p>Load milestones</p>',
         [command('navigate',{'url':'{{site}}__lab/slow-page','until':'load','timeout':5000},send='nav'),
          {'server':'wait','gate':'image'}, {'server':'release','gate':'image'}, {'await':'nav'},check('window.imageFinished',True)],requires=['server'])
    case('navigation-failure-recovery', 'A connection failure is followed by successful navigation', 'Navigation','<p>Failure recovery</p>',
         [command('navigate',{'url':'{{closedOrigin}}/','timeout':1000},error=''),command('navigate',{'url':'{{site}}support/other.html','timeout':5000}),command('title',expect='Other fixture')],requires=['server'])
    case('tab-new-current', 'New tab is ready without changing the current tab', 'Tabs','<p>Original tab</p>',
         [command('new_tab',{'url':'{{site}}support/other.html'},capture={'tab':'result.tab'}),command('title',verify="result.includes('tab-new-current')"),
          command('title',{'tab':'{{tab}}'},expect='Other fixture'),command('close_tab',{'tab':'{{tab}}'})])
    case('tab-switch', 'Switching tabs changes the default command target', 'Tabs','<p>Original tab</p>',
         [command('new_tab',{'url':'{{site}}support/other.html'},capture={'tab':'result.tab'}),command('switch_tab',{'tab':'{{tab}}'}),
          command('title',expect='Other fixture'),command('close_tab',{'tab':'{{tab}}'}),command('title',verify="result.includes('tab-switch')")])
    case('tab-close-pending', 'Closing a tab answers its pending work', 'Tabs','<p>Original tab</p>',
         [command('new_tab',{'url':'{{site}}support/other.html'},capture={'tab':'result.tab'}),
          command('wait_for',{'tab':'{{tab}}','selector':'#never','timeout':5000},send='wait'),command('close_tab',{'tab':'{{tab}}'}),
          {'await':'wait','error':'tab closed'},command('title',verify="result.includes('tab-close-pending')")])
    case('tab-last', 'Closing the last tab fails without closing the session', 'Tabs','<p>Last tab</p>',
         [command('close_tab',error='last tab'),command('tabs',verify='result.length===1'),command('title',verify="result.includes('tab-last')")])
    case('tab-blank-link', 'A blank-target link creates exactly one tab', 'Tabs','<a id="link" href="../support/other.html" target="_blank">Open</a>',
         [command('click',{'selector':'#link'}),command('tabs',verify='result.length===2',capture={'tab':'result.find(t=>!t.current).tab'}),
          command('wait_for',{'tab':'{{tab}}','text':'Other page','timeout':5000}),command('close_tab',{'tab':'{{tab}}'})])
    case('tab-first-init', 'Init script executes before the first page script in a new tab', 'Tabs','<p>Init</p>',
         [command('new_tab',{'url':'{{site}}support/init.html'},capture={'tab':'result.tab'}),command('title',{'tab':'{{tab}}'},expect='seeded'),command('close_tab',{'tab':'{{tab}}'})],launch=['--init-script','{{initScript}}'])
    case('launch-user-agent', 'Configured user agent reaches initial and subsequent tabs', 'Launch options','<p>User agent</p>',
         [check('navigator.userAgent','bruster-test-lab'),command('new_tab',{'url':'{{site}}support/other.html'},capture={'tab':'result.tab'}),
          command('eval',{'tab':'{{tab}}','expression':'navigator.userAgent'},expect='bruster-test-lab'),command('close_tab',{'tab':'{{tab}}'})],launch=['--user-agent','bruster-test-lab'])


def network():
    for form, expr, contract in [('string',"'../__lab/echo'",'required'),('request',"new Request('../__lab/echo')",'required'),('url',"new URL('../__lab/echo',location.href)",'probe')]:
        case('fetch-' + form, 'Fetch accepts a ' + form + ' input', 'Network','<p>Fetch fixture</p>',
             [command('network',{'clear':True}),evaluate(f"(await fetch({expr})).json()",verify="result.method==='GET'"),
              command('network',verify="result.some(e=>e.type==='fetch' && e.status===200)")],requires=['server'],contract=contract)
    for status in (200,204,404,500):
        case(f'fetch-status-{status}', f'HTTP {status} remains a response rather than a transport error', 'Network','<p>HTTP status</p>',
             [evaluate(f"(await fetch('../__lab/status?code={status}')).status",expect=status),
              command('network',verify=f"result.some(e=>e.type==='fetch'&&e.status==={status})")],requires=['server'])
    case('fetch-headers', 'Request headers reach the server and response headers remain inspectable', 'Network','<p>Headers</p>',
         [command('network',{'clear':True}),evaluate("(await fetch('../__lab/echo',{headers:{'X-Lab':'fixture'}})).json()",verify="result.headers['x-lab']==='fixture'"),
          command('network',capture={'index':"result.find(e=>e.type==='fetch').index"}),command('network_request',{'index':'{{index}}'},verify="result.req_headers['x-lab']==='fixture' && result.res_headers['x-lab-response']==='fixture'")],requires=['server'])
    case('fetch-post', 'POST body and method reach the HTTP fixture exactly', 'Network','<p>POST</p>',
         [evaluate("(await fetch('../__lab/echo',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text:'héllo'})})).json()",
                   verify="result.method==='POST' && JSON.parse(result.body).text==='héllo'")],requires=['server'])
    for response_type in ('text','json','arraybuffer'):
        case('xhr-' + response_type, 'XHR ' + response_type + ' response is preserved by instrumentation', 'Network','<p>XHR</p>',
             [evaluate("await new Promise((resolve,reject)=>{const x=new XMLHttpRequest();x.open('GET','../__lab/echo');x.responseType="+repr(response_type)+";x.onload=()=>resolve(x.status);x.onerror=reject;x.send()})",expect=200),
              command('network',verify="result.some(e=>e.type==='xhr'&&e.status===200)")],requires=['server'])
    case('fetch-abort', 'Aborted fetch records failure and permits later requests', 'Network','<p>Abort</p>',
         [evaluate("await new Promise(resolve=>{const c=new AbortController();fetch('../__lab/hang',{signal:c.signal}).then(()=>resolve('unexpected'),e=>resolve(e.name));c.abort()})",expect='AbortError'),
          evaluate("(await fetch('../__lab/echo')).status",expect=200)],requires=['server'])
    for size in (16383,16384,16385):
        case(f'network-body-{size}', f'ASCII response body prefix at {size} characters', 'Network','<p>Body prefix</p>',
             [command('network',{'clear':True}),evaluate(f"await (await fetch('../__lab/body?size={size}')).text()",verify=f'result.length==={size}'),
              command('network',capture={'index':"result.find(e=>e.type==='fetch').index"}),
              command('network_request',{'index':'{{index}}'},verify=f"typeof result.body==='string' && result.body.length==={min(size,16384)}")],requires=['server'])
    case('network-clear', 'Clearing request logs resets entries and indexes', 'Network','<p>Clear logs</p>',
         [evaluate("await (await fetch('../__lab/echo')).text()"),command('network',{'clear':True}),command('network',expect=[]),
          command('network_request',{'index':0},error='no fetch/xhr entry')],requires=['server'])
    case('network-idle-gate', 'Network idle cannot complete while a gated request is pending', 'Network','<button id="start">Start request</button>',
         [command('click',{'selector':'#start'}),{'server':'wait','gate':'fetch'},command('wait_for',{'idle':True,'timeout':150},error='timed out'),
          {'server':'release','gate':'fetch'},command('wait_for',{'idle':True,'timeout':5000}),check('__lab.state.finished',True)],
         setup="start.onclick=()=>fetch('../__lab/gate?name=fetch').then(r=>r.text()).then(()=>__lab.state.finished=true)",requires=['server'])
    case('network-cors', 'A second origin supports explicitly permitted CORS', 'Network','<p>CORS</p>',
         [evaluate("(await fetch(__lab.server.otherOrigin+__lab.sitePath+'__lab/echo?cors=1')).json()",verify="result.method==='GET'")],requires=['server'])
    case('network-cors-denied', 'A denied cross-origin request fails without breaking same-origin requests', 'Network','<p>CORS denied</p>',
         [evaluate("await fetch(__lab.server.otherOrigin+__lab.sitePath+'__lab/echo')",error=''),evaluate("(await fetch('../__lab/echo')).status",expect=200)],requires=['server'])


def storage():
    case('cookie-set-read', 'Native cookie setting is visible in the page and other tabs', 'Storage','<p>Cookies</p>',
         [command('set_cookie',{'name':'lab_cookie','value':'fixture','path':'{{sitePath}}'}),check("document.cookie.includes('lab_cookie=fixture')"),
          command('new_tab',{'url':'{{site}}support/other.html'},capture={'tab':'result.tab'}),
          command('eval',{'tab':'{{tab}}','expression':"document.cookie.includes('lab_cookie=fixture')"},expect=True),command('close_tab',{'tab':'{{tab}}'})])
    case('cookie-server', 'Server-set cookies reach the native cookie API', 'Storage','<p>Server cookies</p>',
         [evaluate("await fetch('../__lab/cookie')"),command('cookies',verify="result.some(c=>c.name==='lab_server'&&c.value==='fixture')")],requires=['server'])
    case('cookie-paths', 'Same-named cookies on distinct paths remain distinguishable', 'Storage','<p>Cookie paths</p>',
         [command('set_cookie',{'name':'lab_path','value':'root','path':'/'}),command('set_cookie',{'name':'lab_path','value':'site','path':'{{sitePath}}'}),
          command('cookies',verify="result.filter(c=>c.name==='lab_path').length===2")])
    case('storage-tabs', 'Local storage is shared while new-tab session storage is independent', 'Storage','<p>Tab storage</p>',
         [evaluate("localStorage.setItem('lab_local','shared');sessionStorage.setItem('lab_session','private')"),
          command('new_tab',{'url':'{{site}}support/other.html'},capture={'tab':'result.tab'}),
          command('eval',{'tab':'{{tab}}','expression':"[localStorage.getItem('lab_local'),sessionStorage.getItem('lab_session')]"},expect=['shared',None]),command('close_tab',{'tab':'{{tab}}'})])
    case('storage-port-origin', 'Different ports isolate local storage', 'Storage','<p>Port origins</p>',
         [evaluate("localStorage.setItem('lab_origin','private')"),command('new_tab',{'url':'{{otherSite}}support/other.html'},capture={'tab':'result.tab'}),
          command('eval',{'tab':'{{tab}}','expression':"localStorage.getItem('lab_origin')"},expect=None),command('close_tab',{'tab':'{{tab}}'})],requires=['server'])
    case('profile-persistence', 'Named profile preserves local storage across process restart', 'Profiles','<p>Persistent profile</p>',
         [evaluate("localStorage.setItem('lab_persist','kept')"),{'restart':True},command('navigate',{'url':'{{caseUrl}}'}),check("localStorage.getItem('lab_persist')",'kept')],launch=['--profile','{{profile}}'])
    case('session-isolation', 'Profile-free process restart discards local storage', 'Profiles','<p>Session isolation</p>',
         [evaluate("localStorage.setItem('lab_persist','discarded')"),{'restart':True},command('navigate',{'url':'{{caseUrl}}'}),check("localStorage.getItem('lab_persist')",None)])
    case('indexeddb', 'IndexedDB writes are readable after their transaction commits', 'Storage','<p>IndexedDB</p>',
         [evaluate("await new Promise((resolve,reject)=>{const r=indexedDB.open('lab-fixture',1);r.onupgradeneeded=()=>r.result.createObjectStore('items');r.onerror=()=>reject(r.error);r.onsuccess=()=>{const db=r.result;const tx=db.transaction('items','readwrite');tx.objectStore('items').put({value:'stored'},'key');tx.oncomplete=()=>{db.close();resolve(true)}}})",expect=True),
          evaluate("await new Promise((resolve,reject)=>{const r=indexedDB.open('lab-fixture',1);r.onsuccess=()=>{const db=r.result;const read=db.transaction('items').objectStore('items').get('key');read.onsuccess=()=>{db.close();resolve(read.result)}};r.onerror=()=>reject(r.error)})",expect={'value':'stored'})])
    case('worker-message', 'Dedicated worker communication survives page instrumentation', 'Workers','<p>Worker</p>',
         [evaluate("await new Promise((resolve,reject)=>{const w=new Worker('../support/worker.js');w.onmessage=e=>{w.terminate();resolve(e.data)};w.onerror=reject;w.postMessage(21)})",expect=42)])
    case('service-worker', 'Service worker registration is scoped and explicitly removable', 'Workers','<p>Service worker</p>',
         [evaluate("const r=await navigator.serviceWorker.register('../support/sw.js');await __lab.until(()=>r.active);return r.scope.endsWith('/support/')",expect=True),
          evaluate("const registrations=await navigator.serviceWorker.getRegistrations();const ours=registrations.filter(r=>r.scope.endsWith('/test-lab/support/'));return (await Promise.all(ours.map(r=>r.unregister()))).every(Boolean)",expect=True)],
         requires=[{'expression':"'serviceWorker' in navigator",'reason':'Service workers unavailable in this engine/context'}])


def diagnostics():
    for id, expression, expected in [('number','42',42),('string',"'héllo 🎉'",'héllo 🎉'),('boolean','false',False),
                                     ('null','null',None),('undefined','undefined',None),('array','[1,true,null]',[1,True,None]),
                                     ('object','({nested:{value:3}})',{'nested':{'value':3}}),('promise',"Promise.resolve('resolved')",'resolved')]:
        case('eval-' + id, 'JavaScript return serialization: ' + id, 'Evaluation','<p>Evaluation</p>',[evaluate(expression,expect=expected)])
    for id, expression in [('throw',"throw new Error('lab failure')"),('syntax','const = ;'),('rejection',"Promise.reject(new Error('lab failure'))")]:
        case('eval-' + id, 'Recover after JavaScript ' + id, 'Evaluation','<p>Recovery</p>',
             [evaluate(expression,error=''),evaluate('21*2',expect=42)])
    case('eval-cyclic', 'Cyclic result uses a JSON-safe fallback', 'Evaluation','<p>Cycle</p>',
         [evaluate('const a={};a.self=a;return a',expect='[object Object]'),evaluate('42',expect=42)])
    case('eval-page-monkeypatch', 'Replacing page JSON.stringify cannot corrupt replies', 'Evaluation','<p id="out">Healthy</p>',
         [evaluate("JSON.stringify=()=> 'broken';document.querySelector=()=>null"),command('text',{'selector':'#out'},expect='Healthy'),evaluate('42',expect=42)])
    for level in ('log','info','warn','error','debug'):
        case('console-' + level, 'Console captures level ' + level, 'Console','<p>Console</p>',
             [command('console',{'clear':True}),evaluate(f"console.{level}('lab-message',{{value:3}})"),
              command('console',verify=f"result.some(e=>e.level==='{level}'&&e.text.includes('lab-message')&&e.text.includes('value'))"),
              command('console',{'clear':True}),command('console',expect=[])])
    for size in (999,1000,1001):
        case(f'console-length-{size}', f'Console entry truncation at {size} characters', 'Boundaries','<p>Console limits</p>',
             [command('console',{'clear':True}),evaluate(f"console.log('x'.repeat({size}))"),command('console',verify=f'result.length===1 && result[0].text.length==={min(size,1000)}')])
    case('console-unhandled', 'Unhandled promise rejection reaches console diagnostics', 'Console','<button id="start">Reject</button>',
         [command('console',{'clear':True}),command('click',{'selector':'#start'}),
          evaluate("await __lab.until(()=>__lab.state.rejected===true)"),command('console',verify="result.some(e=>e.level==='error'&&e.text.includes('fixture rejection'))")],
         setup="window.addEventListener('unhandledrejection',()=>__lab.state.rejected=true);start.onclick=()=>{Promise.reject(new Error('fixture rejection'))}")
    for accept in (True,False):
        case('dialog-confirm-' + str(accept).lower(), 'Confirm returns ' + str(accept).lower(), 'Dialogs','<button id="start">Confirm</button>',
             [command('dialog',{'accept':accept,'clear':True}),command('click',{'selector':'#start'}),check('__lab.state.answer',accept),
              command('dialog',verify="result.length===1 && result[0].type==='confirm'")],setup="start.onclick=()=>__lab.state.answer=confirm('Continue?')")
    for id, params, expected, contract in [('text',{'accept':True,'text':'custom'},'custom','required'),
                                          ('cancel',{'accept':False},None,'required'),
                                          ('empty',{'accept':True,'text':''},'','probe')]:
        case('dialog-prompt-' + id, 'Prompt response: ' + id, 'Dialogs','<button id="start">Prompt</button>',
             [command('dialog',dict(params,clear=True)),command('click',{'selector':'#start'}),check('__lab.state.answer',expected)],
             setup="start.onclick=()=>__lab.state.answer=prompt('Name','default')",contract=contract)
    case('dialog-alert', 'Alert emits a record and subsequent code runs', 'Dialogs','<button id="start">Alert</button>',
         [command('click',{'selector':'#start'}),check('__lab.state.after',True),command('dialog',{'clear':True},verify="result.length===1&&result[0].type==='alert'"),command('dialog',expect=[])],
         setup="start.onclick=()=>{alert('Hello');__lab.state.after=true}")
    case('beforeunload', 'Beforeunload cannot block navigation', 'Dialogs','<a id="leave" href="../support/other.html">Leave</a>',
         [command('click',{'selector':'#leave'}),command('wait_for',{'text':'Other page','timeout':5000}),command('title',expect='Other fixture')],
         setup="window.addEventListener('beforeunload',e=>{e.preventDefault();e.returnValue='Stay?'})")


def stress():
    for count in (5000,10000):
        case(f'stress-dom-{count}', f'Extract and interact with {count} controls', 'Stress','',
             [command('snapshot',{'max':count+1,'format':'json'},verify=f'result.elements.length==={count} && !result.truncated'),
              command('click',{'selector':f'#item-{count-1}'}),check('__lab.state.selected',count-1)],
             setup=f"for(let i=0;i<{count};i++){{const b=document.createElement('button');b.id='item-'+i;b.textContent='Record '+i;b.onclick=()=>__lab.state.selected=i;document.body.append(b)}}",tier='stress')
    case('stress-console-count', 'Console collection stays bounded after 501 messages', 'Stress','<p>Console</p>',
         [command('console',{'clear':True}),evaluate('for(let i=0;i<501;i++)console.log(i)'),command('console',verify='result.length===500')],tier='stress')
    case('stress-large-result', 'A large Unicode result survives protocol framing', 'Stress','<p>Large reply</p>',
         [evaluate("'日本語🎉'.repeat(20000)",verify='result.length===100000'),evaluate('42',expect=42)],tier='stress')
    case('stress-tab-cycles', 'Repeated tab creation and closure returns to one tab', 'Stress','<p>Tab cycles</p>',
         sum(([command('new_tab',{'url':'{{site}}support/other.html'},capture={'tab':'result.tab'}),command('close_tab',{'tab':'{{tab}}'})] for _ in range(12)),[])
         + [command('tabs',verify='result.length===1')],tier='stress')
