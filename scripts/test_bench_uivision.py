"""Exercise the real extension/bridge with its default port already occupied."""
import json
import os
import shutil
import socket
import threading
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path

from bench_audit import Fixtures
from bench_compare import EXTRACT, ProcessClient, validate_extract


@unittest.skipUnless(os.environ.get('BRUSTER_TEST_UIVISION') == '1',
                     'requires installed Ui.Vision, BENCH_DEPS and BENCH_CHROME')
class UiVisionIsolation(unittest.TestCase):
    def test_repeated_rounds_with_default_port_occupied(self):
        driver = Path(__file__).with_name('bench_uivision_driver.mjs')
        command = [shutil.which('node'), str(driver), os.environ['BENCH_CHROME'],
                   os.environ['BENCH_DEPS']]
        with socket.socket() as occupied, ThreadingHTTPServer(('127.0.0.1', 0), Fixtures) as server:
            occupied.bind(('127.0.0.1', 50888))
            occupied.listen()
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                for round_ in range(5):
                    with self.subTest(round=round_):
                        client = ProcessClient(command, True)
                        try:
                            port = client.ready['bridge_port']
                            self.assertNotEqual(port, 50888)
                            client.navigate(f'http://127.0.0.1:{server.server_port}/tiny')
                            _, title, _ = client.call('eval', {'expression': 'document.title'})
                            self.assertEqual(title, 'bench')
                            if round_ == 0:
                                # Match the real workload's repeated, multi-chunk
                                # object and JSON-string extraction in one session.
                                for sample in range(5):
                                    client.navigate(f'http://127.0.0.1:{server.server_port}/large?sample={sample}')
                                    _, value, _ = client.call('eval', {'expression': EXTRACT})
                                    validate_extract(value, 2000, 'large')
                                    _, encoded, _ = client.call('eval', {'expression': f'JSON.stringify({EXTRACT})'})
                                    self.assertEqual(json.loads(encoded), value)
                        finally:
                            client.close()
                        self.assertIsNone(client.close_error)
                        self.assertEqual(client.proc.returncode, 0)
                        with socket.socket() as probe:
                            probe.settimeout(1)
                            self.assertNotEqual(probe.connect_ex(('127.0.0.1', port)), 0,
                                                'bridge still listening after shutdown')
            finally:
                server.shutdown()
                thread.join(timeout=5)


if __name__ == '__main__':
    unittest.main()
