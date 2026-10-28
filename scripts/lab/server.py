"""Loopback fixture server with two real origins and bounded controllable HTTP gates."""
import contextlib
import json
import mimetypes
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlsplit


PREFIX = '/bruster/test-lab/'


class FixtureServer:
    def __init__(self, directory, port=0, *, static_gates=None):
        self.directory = Path(directory).resolve()
        self.static_gates = dict(static_gates or {})
        self.gates, self.arrivals = {}, {}
        self.lock = threading.Lock()
        self.requests, self.responses = [], []
        self.servers, self.threads = [], []
        owner = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *_):
                pass

            def do_HEAD(self):
                self.handle_request(head=True)

            def do_GET(self):
                self.handle_request()

            def do_POST(self):
                self.handle_request()

            def do_OPTIONS(self):
                self.respond(204,b'',{'Access-Control-Allow-Origin':'*','Access-Control-Allow-Headers':'Content-Type,X-Lab','Access-Control-Allow-Methods':'GET,POST,OPTIONS'})

            def respond(self, status, body=b'', headers=None, head=False):
                if isinstance(body,str):
                    body = body.encode('utf-8')
                owner.responses.append({'method':self.command,'path':self.path,'status':status,
                                        'contentType':(headers or {}).get('Content-Type'),'bytes':len(body)})
                self.send_response(status)
                for key,value in (headers or {}).items():
                    self.send_header(key,value)
                self.send_header('Content-Length',str(len(body)))
                self.send_header('Connection','close')
                self.end_headers()
                if not head and body:
                    with contextlib.suppress(BrokenPipeError,ConnectionResetError):
                        self.wfile.write(body)

            def handle_request(self, head=False):
                parsed = urlsplit(self.path)
                path = unquote(parsed.path)
                query = parse_qs(parsed.query)
                if path in ('/','/bruster/','/bruster/test-lab'):
                    return self.respond(302,b'',{'Location':PREFIX},head)
                if not path.startswith(PREFIX):
                    return self.respond(404,b'Not found',head=head)
                relative = path[len(PREFIX):] or 'index.html'
                if relative == 'server-config.js':
                    return self.respond(200,'window.__labServer='+json.dumps({'otherOrigin':owner.other_origin,'origin':owner.origin})+';',
                                        {'Content-Type':'text/javascript','Cache-Control':'no-store'},head)
                if relative.startswith('__lab/'):
                    return self.api(relative[6:],query,head)
                file = (owner.directory/relative).resolve()
                if not file.is_relative_to(owner.directory) or not file.is_file():
                    return self.respond(404,b'Not found',head=head)
                if relative in owner.static_gates:
                    arrival, gate = owner.gate(owner.static_gates[relative])
                    arrival.set()
                    gate.wait(15)
                content_type = {'js':'text/javascript','svg':'image/svg+xml'}.get(file.suffix[1:]) or mimetypes.guess_type(file.name)[0] or 'application/octet-stream'
                return self.respond(200,file.read_bytes(),{'Content-Type':content_type,'Cache-Control':'no-store'},head)

            def api(self, route, query, head):
                try:
                    length = min(int(self.headers.get('Content-Length','0')),1_000_000)
                except ValueError:
                    return self.respond(400,b'Invalid length')
                body = self.rfile.read(length).decode('utf-8',errors='replace') if length else ''
                record = {'method':self.command,'path':self.path,'headers':{k.lower():v for k,v in self.headers.items()},'body':body}
                owner.requests.append(record)
                headers = {'Content-Type':'application/json','Cache-Control':'no-store','X-Lab-Response':'fixture'}
                if query.get('cors') == ['1']:
                    headers['Access-Control-Allow-Origin'] = '*'
                if route == 'echo':
                    return self.respond(200,json.dumps(record),headers,head)
                if route == 'status':
                    try:
                        status = int(query.get('code',['200'])[0])
                    except ValueError:
                        status = 400
                    if status not in (200,204,400,404,500):
                        status = 400
                    return self.respond(status,b'' if status==204 else json.dumps({'status':status}),headers,head)
                if route == 'body':
                    try:
                        size = max(0,min(int(query.get('size',['0'])[0]),100000))
                    except ValueError:
                        return self.respond(400,b'Invalid size')
                    return self.respond(200,'x'*size,{'Content-Type':'text/plain'},head)
                if route == 'cookie':
                    headers['Set-Cookie'] = 'lab_server=fixture; Path=/bruster/test-lab/; Max-Age=3600; SameSite=Lax'
                    return self.respond(200,'{}',headers,head)
                if route == 'redirect':
                    try:
                        count = max(0,min(int(query.get('count',['0'])[0]),10))
                    except ValueError:
                        return self.respond(400,b'Invalid redirect count')
                    return self.respond(302,b'',{'Location': PREFIX+('__lab/redirect?count='+str(count-1) if count else 'support/other.html')},head)
                if route == 'slow-page':
                    html = '<!doctype html><title>Slow fixture</title><script>window.imageFinished=false</script><p id="out">Waiting for image</p><img src="image" onload="imageFinished=true;out.textContent=\'Image finished\'">'
                    return self.respond(200,html,{'Content-Type':'text/html'},head)
                if route in ('gate','image','hang'):
                    name = query.get('name',[route])[0]
                    arrival, gate = owner.gate(name)
                    arrival.set()
                    # All connections have a finite lifetime, including intentionally slow routes.
                    gate.wait(15)
                    if route == 'image':
                        return self.respond(200,(owner.directory/'assets/pattern.svg').read_bytes(),{'Content-Type':'image/svg+xml'},head)
                    return self.respond(200,'released',{'Content-Type':'text/plain'},head)
                return self.respond(404,b'Unknown fixture endpoint',head=head)

        for requested in (port,0):
            server = ThreadingHTTPServer(('127.0.0.1',requested),Handler)
            server.daemon_threads = True
            self.servers.append(server)
        self.origin, self.other_origin = [f'http://127.0.0.1:{s.server_port}' for s in self.servers]
        self.url, self.other_url = self.origin+PREFIX,self.other_origin+PREFIX

    def gate(self, name):
        with self.lock:
            return self.arrivals.setdefault(name,threading.Event()),self.gates.setdefault(name,threading.Event())

    def reset(self):
        with self.lock:
            for gate in self.gates.values():
                gate.set()
            self.gates.clear()
            self.arrivals.clear()
            self.requests.clear()
            self.responses.clear()

    def control(self, operation, name):
        arrival, gate = self.gate(name)
        if operation == 'release':
            gate.set()
        elif operation == 'wait':
            if not arrival.wait(8):
                raise TimeoutError(f'HTTP gate {name!r} was never requested')
        else:
            raise ValueError(f'Unknown server operation {operation}')

    def __enter__(self):
        for server in self.servers:
            thread = threading.Thread(target=server.serve_forever,daemon=True)
            thread.start()
            self.threads.append(thread)
        return self

    def __exit__(self, *_):
        self.reset()
        for server in self.servers:
            server.shutdown()
            server.server_close()
        for thread in self.threads:
            thread.join(timeout=2)
