"""Bounded stdio client for both public Bruster transports."""
import base64
import contextlib
import hashlib
import json
import os
import queue
import signal
import subprocess
import sys
import threading
import time


class BrowserError(RuntimeError):
    pass


class CommandError(BrowserError):
    """An error response from Bruster, distinct from transport/process failure."""


def evidence(value):
    """Retain readable wire evidence without duplicating entire PNG payloads."""
    if isinstance(value, dict):
        return {k: ({'base64Length': len(v), 'sha256': hashlib.sha256(v.encode()).hexdigest()}
                    if k in ('png_base64', 'data') and isinstance(v, str) and len(v) > 4096
                    else evidence(v)) for k, v in value.items()}
    if isinstance(value, list):
        return [evidence(v) for v in value]
    if isinstance(value, str) and len(value) > 32000:
        return {'prefix': value[:2000], 'length': len(value), 'sha256': hashlib.sha256(value.encode()).hexdigest()}
    return value


class Client:
    def __init__(self, binary, transport, directory, launch=(), viewport=(960, 640)):
        self.transport = transport
        self.records, self.errors, self.events = [], [], []
        self.duplicates, self.seen = [], set()
        self.queue, self.pending, self.methods = queue.Queue(), {}, {}
        self.sequence = 0
        self.started = time.monotonic()
        env = os.environ.copy()
        for key in ('XDG_CONFIG_HOME', 'XDG_CACHE_HOME', 'XDG_DATA_HOME', 'XDG_STATE_HOME'):
            env[key] = str(directory / key.lower())
        if sys.platform == 'darwin':
            env['HOME'] = str(directory / 'home')
            (directory / 'home').mkdir(exist_ok=True)
        elif sys.platform == 'win32':
            for key in ('LOCALAPPDATA', 'APPDATA'):
                env[key] = str(directory / key.lower())
                (directory / key.lower()).mkdir(exist_ok=True)
        command = [str(binary), '--hidden', '--viewport', f'{viewport[0]}x{viewport[1]}', *launch]
        if transport == 'mcp':
            command.append('--mcp')
        self.process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                        stderr=subprocess.PIPE, env=env, start_new_session=os.name != 'nt')
        self.reader = threading.Thread(target=self._read, daemon=True)
        self.err_reader = threading.Thread(target=self._stderr, daemon=True)
        self.reader.start()
        self.err_reader.start()
        try:
            if transport == 'mcp':
                id = self._send({'method': 'initialize', 'params': {'protocolVersion':'2025-06-18',
                    'capabilities':{}, 'clientInfo':{'name':'bruster-test-lab','version':'1'}}})
                initialized = self._receive(id, 30)
                if initialized.get('result',{}).get('protocolVersion') != '2025-06-18':
                    raise BrowserError(f'Invalid MCP initialization response: {initialized}')
                self._write({'jsonrpc':'2.0','method':'notifications/initialized'})
                # Native startup might predate initialization, suppressing the ready event.
                self.call('tabs')
            else:
                deadline = time.monotonic() + 30
                while True:
                    if time.monotonic() >= deadline:
                        raise TimeoutError('Bruster did not emit ready within 30s')
                    message = self._next(max(0.1, deadline-time.monotonic()))
                    if message.get('event') == 'ready':
                        break
        except Exception as error:
            self.close()
            failure = BrowserError(f'Bruster startup failed (exit {self.process.returncode}): {error}; '+ '\n'.join(self.errors[-12:]))
            failure.records, failure.stderr = self.records, self.errors
            raise failure from error

    def _record(self, direction, value):
        self.records.append({'ms':round((time.monotonic()-self.started)*1000,3),
                             'direction':direction, 'message':evidence(value)})

    def _read(self):
        try:
            for line in self.process.stdout:
                try:
                    value = json.loads(line)
                    if not isinstance(value, dict):
                        raise ValueError('Protocol message is not an object')
                except (ValueError, UnicodeDecodeError) as error:
                    self.queue.put(BrowserError(f'Invalid protocol line: {line[:200]!r}: {error}'))
                    continue
                self._record('receive', value)
                if 'id' in value:
                    if value['id'] in self.seen:
                        self.duplicates.append(value['id'])
                    self.seen.add(value['id'])
                if 'event' in value:
                    self.events.append(value)
                elif value.get('method') == 'notifications/message':
                    self.events.append(value.get('params', {}).get('data'))
                self.queue.put(value)
        finally:
            self.queue.put(BrowserError('Bruster stdout closed'))

    def _stderr(self):
        for line in self.process.stderr:
            self.errors.append(line.decode('utf-8', errors='replace').rstrip())

    def _write(self, value):
        self._record('send', value)
        self.process.stdin.write((json.dumps(value, ensure_ascii=True)+'\n').encode())
        self.process.stdin.flush()

    def _send(self, value):
        self.sequence += 1
        value = dict(value, id=self.sequence)
        if self.transport == 'mcp':
            value['jsonrpc'] = '2.0'
        self._write(value)
        return self.sequence

    def _next(self, timeout):
        try:
            value = self.queue.get(timeout=timeout)
        except queue.Empty as error:
            raise TimeoutError(f'Bruster did not reply within {timeout:.1f}s') from error
        if isinstance(value, Exception):
            raise value
        return value

    def _receive(self, id, timeout):
        deadline = time.monotonic()+timeout
        while id not in self.pending:
            if time.monotonic() >= deadline:
                raise TimeoutError(f'No reply for request {id}')
            value = self._next(deadline-time.monotonic())
            if 'id' in value:
                self.pending[value['id']] = value
        return self.pending.pop(id)

    def send(self, method, params=None):
        params = dict(params or {})
        if method in ('snapshot', 'find'):
            params.setdefault('format','json')
        if method in ('navigate','new_tab'):
            params.setdefault('timeout',30000)
        if method in ('eval','wait_for','snapshot','find','click','fill','type','press','select','check','hover','drag'):
            params.setdefault('request_timeout',20000)
        if self.transport == 'mcp':
            id = self._send({'method':'tools/call','params':{'name':method,'arguments':params}})
        else:
            value = {'method':method,'params':params}
            if 'tab' in params:
                value['tab'] = params.pop('tab')
            id = self._send(value)
        self.methods[id] = method
        return id

    def receive(self, id, timeout=35):
        value = self._receive(id,timeout)
        if 'error' in value:
            raise CommandError(str(value['error']))
        result = value.get('result')
        if self.transport == 'native':
            return result
        if result.get('isError'):
            raise CommandError('\n'.join(part.get('text','') for part in result.get('content',[])))
        parts = result.get('content',[])
        if len(parts) != 1:
            raise BrowserError(f'Expected one MCP content block: {result}')
        if parts[0]['type'] == 'image':
            if parts[0].get('mimeType') != 'image/png':
                raise BrowserError('Expected MCP PNG image')
            base64.b64decode(parts[0]['data'],validate=True)
            return {'png_base64':parts[0]['data']}
        text = parts[0]['text']
        method = self.methods[id]
        if method in ('title','url','text','html'):
            return text
        if method == 'attr':
            return None if text == 'null' else text
        try:
            return json.loads(text)
        except ValueError:
            return text

    def call(self, method, params=None, timeout=35):
        return self.receive(self.send(method,params),timeout)

    def close(self):
        error = None
        if self.process.poll() is None:
            try:
                self.call('close',timeout=5)
                self.process.wait(timeout=10)
            except (OSError, TimeoutError, BrowserError, subprocess.TimeoutExpired) as exc:
                error = str(exc)
                if os.name == 'nt':
                    subprocess.run(['taskkill','/PID',str(self.process.pid),'/T','/F'],capture_output=True)
                    if self.process.poll() is None:
                        self.process.kill()
                else:
                    try:
                        os.killpg(self.process.pid,signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                self.process.wait(timeout=5)
        self.reader.join(timeout=2)
        self.err_reader.join(timeout=2)
        if self.process.returncode:
            error = error or f'Bruster exited with status {self.process.returncode}'
        for stream in (self.process.stdin,self.process.stdout,self.process.stderr):
            with contextlib.suppress(OSError):
                stream.close()
        return error
