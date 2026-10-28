"""Execute manifest cases, preserve first-attempt evidence, and grade actual state."""
import base64
import fnmatch
import hashlib
import html
import json
import platform
import re
import socket
import struct
import sys
import tempfile
import time
import traceback
import zlib
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

from .build import provenance
from .client import Client, BrowserError, CommandError, evidence


class SkipCase(Exception):
    pass


def substitute(value, variables):
    if isinstance(value, list):
        return [substitute(v,variables) for v in value]
    if isinstance(value, dict):
        return {k:substitute(v,variables) for k,v in value.items()}
    if not isinstance(value,str):
        return value
    pattern = r'\{\{([A-Za-z][A-Za-z0-9]*)\}\}'
    full = re.fullmatch(pattern,value)
    if full:
        return variables[full[1]]
    return re.sub(pattern,lambda match:str(variables[match[1]]),value)


def same_json(actual, expected):
    # Python's True == 1 must not turn an incorrect JSON boolean into a pass.
    return json.dumps(actual,sort_keys=True,ensure_ascii=True)==json.dumps(expected,sort_keys=True,ensure_ascii=True)


def png_pixels(data):
    """Decode non-interlaced 8-bit RGB/RGBA/grayscale native PNGs using stdlib."""
    if data[:8] != b'\x89PNG\r\n\x1a\n':
        raise AssertionError('Screenshot is not PNG')
    offset, compressed = 8, bytearray()
    width = height = depth = color = interlace = None
    ended = False
    while offset+12 <= len(data):
        size, = struct.unpack('>I',data[offset:offset+4])
        kind = data[offset+4:offset+8]
        chunk = data[offset+8:offset+8+size]
        if len(chunk)!=size or offset+12+size>len(data):
            raise AssertionError('Truncated PNG chunk')
        checksum, = struct.unpack('>I',data[offset+8+size:offset+12+size])
        if zlib.crc32(kind+chunk)&0xffffffff != checksum:
            raise AssertionError('PNG checksum mismatch')
        if kind==b'IHDR':
            width,height,depth,color,compression,filter_method,interlace = struct.unpack('>IIBBBBB',chunk)
        elif kind==b'IDAT':
            compressed.extend(chunk)
        offset += size+12
        if kind==b'IEND':
            ended = True
            break
    if not ended:
        raise AssertionError('PNG has no end chunk')
    channels = {0:1,2:3,4:2,6:4}.get(color)
    if not width or not height or depth!=8 or interlace!=0 or channels is None:
        raise AssertionError(f'Unsupported native PNG format: {width}×{height}, depth={depth}, color={color}, interlace={interlace}')
    if width*height>40_000_000:
        raise AssertionError('PNG exceeds the test decoder pixel budget')
    raw = zlib.decompress(compressed)
    stride = width*channels
    if len(raw)!=(stride+1)*height:
        raise AssertionError('PNG decompressed size mismatch')
    rows, previous = [],bytearray(stride)
    for y in range(height):
        start = y*(stride+1)
        filter_type, row = raw[start],bytearray(raw[start+1:start+1+stride])
        if filter_type not in range(5):
            raise AssertionError('Invalid PNG scanline filter')
        if filter_type:
            for x in range(stride):
                a = row[x-channels] if x>=channels else 0
                b = previous[x]
                c = previous[x-channels] if x>=channels else 0
                if filter_type==1:
                    predictor = a
                elif filter_type==2:
                    predictor = b
                elif filter_type==3:
                    predictor = (a+b)//2
                else:
                    p = a+b-c
                    distances = (abs(p-a),abs(p-b),abs(p-c))
                    predictor = (a,b,c)[distances.index(min(distances))]
                row[x] = (row[x]+predictor)&255
        rows.append(row)
        previous = row

    def pixel(x,y):
        if not 0<=x<width or not 0<=y<height:
            raise AssertionError(f'Pixel {x},{y} outside screenshot {width}×{height}')
        values = rows[y][x*channels:(x+1)*channels]
        return list(values[:3]) if color in (2,6) else [values[0]]*3
    return width,height,pixel


def grade_image(result, spec, dpr, path):
    if not isinstance(result,dict) or 'png_base64' not in result:
        raise AssertionError(f'Missing screenshot payload: {result}')
    data = base64.b64decode(result['png_base64'],validate=True)
    path.write_bytes(data)
    width,height,pixel = png_pixels(data)
    for dimension,actual in [('Width',width),('Height',height)]:
        if 'min'+dimension in spec and actual<spec['min'+dimension]*dpr:
            raise AssertionError(f'PNG {dimension} {actual} is below expected minimum')
        if 'css'+dimension in spec and abs(actual-spec['css'+dimension]*dpr)>1:
            raise AssertionError(f'PNG {dimension} {actual} differs from CSS extent × DPR')
    for x,y,wanted in spec.get('samples',[]):
        actual = pixel(round(x*dpr),round(y*dpr))
        if any(abs(a-b)>8 for a,b in zip(actual,wanted)):
            raise AssertionError(f'Pixel at CSS {x},{y}: expected {wanted}, got {actual}')
    return {'width':width,'height':height,'sha256':hashlib.sha256(data).hexdigest()}


class CaseRunner:
    def __init__(self, binary, site, manifest, output, server=None):
        self.binary, self.site, self.manifest = Path(binary).resolve(),site,manifest
        self.output, self.server = Path(output).resolve(),server

    def requirement(self, requirement, client=None):
        if isinstance(requirement,dict):
            if client and client.call('eval',{'expression':requirement['expression']}) is not True:
                raise SkipCase(requirement['reason'])
            return
        reasons = {'server':self.server is not None, 'linux':sys.platform.startswith('linux'),
                   'windows':sys.platform=='win32','clip':sys.platform!='win32'}
        if requirement.startswith('framework:'):
            present = f'frameworks/{requirement.split(":",1)[1]}.js' in self.manifest['frameworks']
        elif requirement in reasons:
            present = reasons[requirement]
        else:
            raise ValueError(f'Unknown fixture requirement {requirement}')
        if not present:
            raise SkipCase('Missing prerequisite: '+requirement)

    def run_case(self, item, transport):
        started = time.monotonic()
        result = {'id':item['id'],'title':item['title'],'category':item['category'],
                  'contract':item['contract'],'transport':transport,'status':'error','steps':[]}
        directory = self.output/transport/item['id']
        directory.mkdir(parents=True,exist_ok=True)
        client, clients = None,[]
        phase = 'setup'
        preferred_temp = '/tmp/opencode' if Path('/tmp/opencode').is_dir() else None
        temporary = tempfile.TemporaryDirectory(prefix='bruster-lab-',dir=preferred_temp)
        scratch = Path(temporary.name)
        try:
            for requirement in item['requires']:
                self.requirement(requirement)
            if self.server:
                self.server.reset()
            files = {'textFile':('sample.txt',b'hello\n'),'binaryFile':('bytes.bin',bytes(range(256))),
                     'emptyFile':('empty.txt',b''),'unicodeFile':('résumé-日本.txt',b'hello\n'),
                     'initScript':('init.js',b'window.__labInit="seeded";')}
            variables = {'site':self.site,'sitePath':urlsplit(self.site).path,
                         'caseUrl':self.site+item['url'],'profile':str(scratch/'profile'),
                         'missingFile':str(scratch/'does-not-exist.txt')}
            if self.server:
                variables['otherSite'] = self.server.other_url
                with socket.socket() as closed:
                    closed.bind(('127.0.0.1',0))
                    variables['closedOrigin'] = f'http://127.0.0.1:{closed.getsockname()[1]}'
            for name,(filename,contents) in files.items():
                (scratch/filename).write_bytes(contents)
                variables[name] = str(scratch/filename)
            launch = substitute(item['launch'],variables)

            def start():
                try:
                    browser = Client(self.binary,transport,scratch,launch,item['viewport'])
                except BrowserError as error:
                    (directory/'stderr.log').write_text('\n'.join(getattr(error,'stderr',[])),encoding='utf-8')
                    (directory/'startup-transcript.json').write_text(json.dumps(getattr(error,'records',[]),indent=2),encoding='utf-8')
                    raise
                clients.append(browser)
                return browser

            client = start()
            client.call('navigate',{'url':variables['caseUrl']})
            client.call('eval',{'expression':"(async()=>{await __lab.until(()=>__lab.ready||__lab.error);if(__lab.error)throw new Error(__lab.error);return true})()"})
            result['browser'] = client.call('eval',{'expression':"({userAgent:navigator.userAgent,platform:navigator.platform,dpr:devicePixelRatio,width:innerWidth,height:innerHeight})"})
            for requirement in item['requires']:
                if isinstance(requirement,dict):
                    self.requirement(requirement,client)
            phase = 'execution'
            pending = {}
            for index,raw_step in enumerate(item['steps']):
                step = substitute(raw_step,variables)
                observation = {'index':index+1,'step':step}
                result['steps'].append(observation)
                if 'server' in step:
                    self.server.control(step['server'],step['gate'])
                    continue
                if 'restart' in step:
                    error = client.close()
                    if error:
                        raise RuntimeError('Restart shutdown failed: '+error)
                    client = start()
                    continue
                if 'assertNoDuplicateReplies' in step:
                    if client.duplicates:
                        raise AssertionError(f'Duplicate response IDs: {client.duplicates}')
                    continue
                if 'send' in step:
                    pending[step['send']] = (client.send(step['method'],step['params']),step)
                    continue
                if 'await' in step:
                    id, original = pending.pop(step['await'])
                    step = dict(original,**step)
                    action = lambda:client.receive(id)
                else:
                    action = lambda:client.call(step['method'],step['params'])
                value = None
                try:
                    value = action()
                except CommandError as error:
                    observation['error'] = str(error)
                    if 'error' not in step or step['error'].lower() not in str(error).lower():
                        raise AssertionError(f'Unexpected command error: {error}') from error
                else:
                    observation['result'] = evidence(value)
                    if 'error' in step:
                        raise AssertionError(f'Expected error containing {step["error"]!r}, got success: {value!r}')
                    if 'expect' in step and not same_json(value,step['expect']):
                        raise AssertionError(f'Expected {step["expect"]!r}, got {value!r}')
                if 'verify' in step:
                    expression = '(async (result) => ('+step['verify']+'))('+json.dumps(value,ensure_ascii=True)+')'
                    verified = client.call('eval',{'expression':expression})
                    if verified is not True:
                        raise AssertionError(f'Assertion was {verified!r}: {step["verify"]}; result={evidence(value)!r}')
                if 'capture' in step:
                    fields = ','.join(json.dumps(name)+':('+expr+')' for name,expr in step['capture'].items())
                    captured = client.call('eval',{'expression':'(async (result) => ({'+fields+'}))('+json.dumps(value,ensure_ascii=True)+')'})
                    if not isinstance(captured,dict) or set(captured)!=set(step['capture']):
                        raise AssertionError(f'Capture did not resolve: {step["capture"]}; got {captured}')
                    variables.update(captured)
                if 'image' in step:
                    observation['image'] = grade_image(value,step['image'],result['browser']['dpr'],directory/f'step-{index+1}.png')
            if client.duplicates:
                raise AssertionError(f'Duplicate response IDs: {client.duplicates}')
            result['status'] = 'pass' if item['contract']=='required' else 'probe-pass'
        except SkipCase as error:
            result.update(status='skip',reason=str(error))
        except AssertionError as error:
            status = ('probe-fail' if item['contract']=='probe' else 'fail') if phase=='execution' else 'error'
            result.update(status=status,error=str(error))
        except BrowserError as error:
            result.update(status='error',error=str(error))
        except Exception as error:
            result.update(status='error',error=f'{type(error).__name__}: {error}',traceback=traceback.format_exc())
        finally:
            if client and result['status'] in ('fail','probe-fail','error'):
                if self.server:
                    http = {'requests':self.server.requests,'responses':self.server.responses}
                    try:
                        (directory/'http.json').write_text(json.dumps(http,ensure_ascii=True,indent=2),encoding='utf-8')
                    except OSError as error:
                        result.setdefault('evidenceErrors',{})['http'] = str(error)
                for name,method,params in [('state','eval',{'expression':"window.__lab ? ({id:__lab.id,ready:__lab.ready,error:__lab.error,state:__lab.state,events:__lab.events}) : null",'request_timeout':1500}),
                                           ('snapshot','snapshot',{'format':'json','max':100,'request_timeout':1500}),
                                           ('console','console',{'request_timeout':1500}),('network','network',{'request_timeout':1500})]:
                    try:
                        value = client.call(method,params,timeout=3)
                        (directory/(name+'.json')).write_text(json.dumps(value,ensure_ascii=True,indent=2),encoding='utf-8')
                    except Exception as error:
                        result.setdefault('evidenceErrors',{})[name] = str(error)
                try:
                    shot = client.call('screenshot',timeout=4)
                    (directory/'failure.png').write_bytes(base64.b64decode(shot['png_base64'],validate=True))
                except Exception as error:
                    result.setdefault('evidenceErrors',{})['screenshot'] = str(error)
            if client:
                error = client.close()
                if error:
                    result['shutdownError'] = error
                    result['status'] = 'error'
            duplicates = [id for browser in clients for id in browser.duplicates]
            if duplicates:
                result.update(status='error',error=f'Duplicate response IDs: {duplicates}')
            if clients:
                with (directory/'transcript.jsonl').open('w',encoding='utf-8') as stream:
                    for n,browser in enumerate(clients):
                        for record in browser.records:
                            stream.write(json.dumps(dict(record,process=n),ensure_ascii=True)+'\n')
                (directory/'stderr.log').write_text('\n'.join(line for browser in clients for line in browser.errors),encoding='utf-8')
            result['durationMs'] = round((time.monotonic()-started)*1000,2)
            result['artifacts'] = directory.relative_to(self.output).as_posix()
            # WebView2 may retain profile handles briefly after controller shutdown.
            for attempt in range(20):
                try:
                    temporary.cleanup()
                    break
                except OSError:
                    if attempt==19:
                        result['cleanupError'] = str(scratch)
                        result['status'] = 'error'
                    else:
                        time.sleep(.1)
            (directory/'result.json').write_text(json.dumps(result,ensure_ascii=True,indent=2)+'\n',encoding='utf-8')
        return result


def write_reports(output, report):
    output = Path(output)
    report['summary'] = dict(Counter(row['status'] for row in report['results']))
    temporary = output/'.results.json.tmp'
    temporary.write_text(json.dumps(report,ensure_ascii=True,indent=2)+'\n',encoding='utf-8')
    temporary.replace(output/'results.json')
    rows = []
    for row in report['results']:
        reason = row.get('error',row.get('reason',''))
        rows.append('<tr><td><a href="'+html.escape(row['artifacts'],quote=True)+'/result.json">'+html.escape(row['id'])+'</a></td><td>'+html.escape(row['transport'])+'</td><td>'+html.escape(row['status'])+'</td><td>'+str(row['durationMs'])+'</td><td>'+html.escape(reason)+'</td></tr>')
    page = '<!doctype html><meta charset="utf-8"><title>Bruster Test Lab results</title><style>body{font:14px/1.6 system-ui;max-width:1400px;margin:30px auto;padding:20px}table{border-collapse:collapse;width:100%}td,th{padding:8px;border:1px solid #ccc;text-align:left}td:last-child{overflow-wrap:anywhere;max-width:600px}code{overflow-wrap:anywhere}</style><h1>Bruster Test Lab results</h1><p>'+html.escape(report['platform'])+'</p><p>'+html.escape(str(report['summary']))+'</p><p>Fixture revision: <code>'+html.escape(report['provenance']['sourceSha256'])+'</code></p><p><a href="results.json">Machine-readable report</a></p><table><tr><th>Case</th><th>Transport</th><th>Status</th><th>ms</th><th>Observation</th></tr>'+''.join(rows)+'</table>'
    (output/'index.html').write_text(page,encoding='utf-8')


def run(binary, site, manifest, output, *, transport='both', suite='core', patterns=(), server=None, strict_probes=False):
    output = Path(output)
    if (output/'results.json').exists():
        raise ValueError('A report already exists at this output path; choose a fresh directory')
    output.mkdir(parents=True,exist_ok=True)
    cases = [item for item in manifest['cases'] if (suite=='all' or item['tier']==suite)
             and (not patterns or any(fnmatch.fnmatchcase(item['id'],p) for p in patterns))]
    if not cases:
        raise ValueError('No cases matched the requested suite/filter')
    report = {'schemaVersion':1,'provenance':manifest['provenance'],'runnerProvenance':provenance(),
              'platform':platform.platform(),
              'startedUtc':datetime.now(timezone.utc).isoformat(),'site':site,
              'binarySha256':hashlib.sha256(Path(binary).read_bytes()).hexdigest(),
              'results':[]}
    runner = CaseRunner(binary,site,manifest,output,server)
    transports = ['native','mcp'] if transport=='both' else [transport]
    for mode in transports:
        for item in cases:
            result = runner.run_case(item,mode)
            report['results'].append(result)
            print(f'{result["status"].upper():11} {mode:6} {item["id"]} {result.get("error",result.get("reason",""))[:180]}',flush=True)
            write_reports(output,report)
    report['finishedUtc'] = datetime.now(timezone.utc).isoformat()
    write_reports(output,report)
    print(json.dumps(report['summary'],sort_keys=True),flush=True)
    print(f'Report: {output.resolve()/"index.html"}',flush=True)
    failing = {'fail','error'} | ({'probe-fail'} if strict_probes else set())
    if all(row['status']=='skip' for row in report['results']):
        return 2
    return int(any(row['status'] in failing for row in report['results']))
