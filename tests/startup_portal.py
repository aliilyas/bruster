#!/usr/bin/env python3
"""Linux startup regression: python3 tests/startup_portal.py /path/to/bruster.

Run under Xvfb. Needs dbus-run-session, python3-dbus and python3-gi; the script
creates a private bus so it never replaces the user's desktop portal.
"""
import json
import os
import signal
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path


def check(binary):
    import dbus
    import dbus.service
    from dbus.mainloop.glib import DBusGMainLoop
    from gi.repository import GLib

    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
    from bench_compare import ProcessClient, isolated_environment
    from lab.client import Client

    DBusGMainLoop(set_as_default=True)
    bus = dbus.SessionBus()
    name = dbus.service.BusName('org.freedesktop.portal.Desktop', bus, do_not_queue=True)
    calls = []
    stalled = False

    class Portal(dbus.service.Object):
        @dbus.service.method('org.freedesktop.DBus.Properties', in_signature='s', out_signature='a{sv}',
                             async_callbacks=('reply', 'error'))
        def GetAll(self, interface, reply, error):
            calls.append(str(interface))
            if not stalled:
                reply({})

        @dbus.service.method('org.freedesktop.portal.Settings', in_signature='ss', out_signature='v',
                             async_callbacks=('reply', 'error'))
        def Read(self, namespace, key, reply, error):
            calls.append('org.freedesktop.portal.Settings')
            if not stalled:
                reply(dbus.UInt32(0, variant_level=2))

    portal = Portal(name, '/org/freedesktop/portal/desktop')
    loop = GLib.MainLoop()
    thread = threading.Thread(target=loop.run, daemon=True)
    thread.start()
    try:
        # Positive controls prove the fixture is reachable, including both ways
        # to request desktop integration. The portal answers immediately here.
        for flags, use_bus in [(['--hidden', '--visible'], False), (['--hidden'], True)]:
            calls.clear()
            os.environ.pop('BRUSTER_USE_SESSION_BUS', None)
            if use_bus:
                os.environ['BRUSTER_USE_SESSION_BUS'] = '1'
            client = ProcessClient([binary, *flags], chromium=False)
            try:
                assert {'org.freedesktop.portal.Inhibit', 'org.freedesktop.portal.Settings'} <= set(calls), calls
            finally:
                client.close()
            assert client.close_error is None, client.close_error

        # Withhold replies completely: old builds stall for ~25 + 5 seconds.
        os.environ.pop('BRUSTER_USE_SESSION_BUS', None)
        stalled = True
        calls.clear()
        client = ProcessClient([binary, '--hidden'], chromium=False)
        try:
            assert client.startup_ms < 10_000, client.startup_ms
            client.call('new_tab')  # Tao also queried the theme for each new tab.
            assert not calls, calls
            print(f'PASS: hidden ready in {client.startup_ms:.1f} ms; new tab bypasses stalled portal')
        finally:
            client.close()
        assert client.close_error is None, client.close_error

        # Animation fixtures request visible windows, but the lab still isolates
        # desktop integration. Exercise both transports against the stalled bus.
        for transport in ('native','mcp'):
            with tempfile.TemporaryDirectory(prefix='bruster-portal-lab-') as temp:
                client = Client(binary,transport,Path(temp),launch=('--visible',))
                try:
                    startup_ms = (time.monotonic()-client.started)*1000
                    assert startup_ms < 10_000, startup_ms
                    client.call('new_tab')
                    assert not calls, calls
                    print(f'PASS: visible {transport} lab ready in {startup_ms:.1f} ms; new tab bypasses stalled portal')
                finally:
                    error = client.close()
                assert error is None, error

        # MCP implies hidden mode; exercise real JSON-RPC startup and a browser
        # command, not just initialize (which the stdin thread answers itself).
        with tempfile.TemporaryDirectory(prefix='bruster-portal-mcp-') as temp:
            requests = [
                {'jsonrpc': '2.0', 'id': 1, 'method': 'initialize', 'params': {}},
                {'jsonrpc': '2.0', 'id': 2, 'method': 'tools/call', 'params': {'name': 'new_tab', 'arguments': {}}},
            ]
            proc = subprocess.Popen([binary, '--mcp'], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE, env=isolated_environment(temp, False),
                                    start_new_session=True, text=True)
            try:
                out, err = proc.communicate(''.join(json.dumps(r) + '\n' for r in requests), timeout=10)
            finally:
                if proc.poll() is None:
                    os.killpg(proc.pid, signal.SIGKILL)
                    proc.communicate()
            assert proc.returncode == 0, err
            replies = {r.get('id'): r for line in out.splitlines() if (r := json.loads(line)).get('id')}
            assert replies[1]['result']['serverInfo']['name'] == 'bruster', replies
            assert 'error' not in replies[2] and not replies[2]['result'].get('isError'), replies
            assert not calls, calls
            print('PASS: MCP startup and new tab bypass stalled portal')
    finally:
        loop.quit()
        thread.join(timeout=2)
        portal.remove_from_connection()
        del portal, name
        bus.close()


if __name__ == '__main__':
    binary = str(Path(sys.argv[1]).resolve(strict=True))
    if sys.argv[2:] == ['--private-bus']:
        check(binary)
    else:
        subprocess.run(['dbus-run-session', '--', sys.executable, __file__, binary, '--private-bus'], check=True)
