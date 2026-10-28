"""Reject overlapping measurements, including frozen binaries and idle controllers."""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import bench_compare as compare
import bench_performance as performance


@unittest.skipUnless(sys.platform == 'linux', 'process accounting uses /proc')
class Concurrency(unittest.TestCase):
    def process(self, name):
        child = subprocess.Popen([sys.executable, '-c', """
import ctypes, sys
assert ctypes.CDLL(None).prctl(15, sys.argv[1].encode(), 0, 0, 0) == 0
print('ready', flush=True)
sys.stdin.read()
""", name], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
        self.addCleanup(self.close, child)
        self.assertEqual(child.stdout.readline().strip(), 'ready')
        return child

    @staticmethod
    def close(child):
        if not child.stdin.closed:
            child.stdin.close()
        child.wait(timeout=5)
        child.stdout.close()

    def test_live_helpers_and_truncated_build_names_are_detected_and_excludable(self):
        names = ('baseline-bruster', 'candidate-bruster', 'WebKitWebProcess',
                 'WebKitNetworkProcess', 'chrome', 'headless_shell', 'agent-browser', 'node', 'rustc')
        children = [self.process(name) for name in names]
        pids = {p.pid for p in children}
        found = {row['pid'] for row in compare.background_work()}
        self.assertTrue(pids <= found)
        self.assertFalse(pids & {row['pid'] for row in compare.background_work(pids)})
        # Exited, unreaped processes have no resident workload.
        for child in children:
            child.stdin.close()
            os.waitid(os.P_PID, child.pid, os.WEXITED | os.WNOWAIT)
        self.assertFalse(pids & {row['pid'] for row in compare.background_work()})

    def test_controller_is_detected_between_browser_sessions(self):
        with tempfile.TemporaryDirectory() as directory:
            for name in ('site_compare.py', 'site_campaign.py'):
                with self.subTest(name=name):
                    script = Path(directory) / name
                    script.write_text("import sys\nprint('ready', flush=True)\nsys.stdin.read()\n")
                    child = subprocess.Popen([sys.executable, str(script)], stdin=subprocess.PIPE,
                                             stdout=subprocess.PIPE, text=True)
                    try:
                        self.assertEqual(child.stdout.readline().strip(), 'ready')
                        self.assertIn(child.pid, {row['pid'] for row in compare.background_work()})
                    finally:
                        self.close(child)

    def test_preexisting_competition_rejects_launch_and_preserves_paired_failure(self):
        child = self.process('candidate-bruster')
        args = SimpleNamespace(baseline=Path(sys.executable))
        with patch.object(compare, 'ProcessClient') as launch:
            with self.assertRaisesRegex(RuntimeError, 'Concurrent browser/build workload'):
                compare.measure(args, None, 'bruster', 1)
            row = performance.measure(args, None, 'baseline', 1)
            launch.assert_not_called()
        self.assertIn(child.pid, {r['pid'] for r in row['competing_before']})
        self.assertIn('Concurrent browser/build workload', row['error'])
        self.assertEqual(row['forced_cleanup'], [])
        self.assertIsNone(child.poll())  # A competing process is never ours to clean up.
        self.assertEqual(json.loads(json.dumps(row)), row)


if __name__ == '__main__':
    unittest.main()
