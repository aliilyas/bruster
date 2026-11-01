"""Native npm runtimes must not disappear from installed-file accounting."""
import json
import struct
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from bench_footprint import inventory, libraries, package_files


class NativePackages(unittest.TestCase):
    def test_counts_installed_optional_platform_binary_and_its_dependencies(self):
        with tempfile.TemporaryDirectory() as directory:
            deps = Path(directory)
            modules = deps / 'node_modules'
            manifests = {
                'server': {'optionalDependencies': {'@native/linux-x64': '1', '@native/darwin-arm64': '1'}},
                '@native/linux-x64': {'dependencies': {'runtime': '1'}},
                'runtime': {},
            }
            for name, manifest in manifests.items():
                root = modules / name
                root.mkdir(parents=True)
                (root / 'package.json').write_text(json.dumps(manifest))
            binary = modules / '@native/linux-x64/server'
            binary.write_bytes(b'native server payload')
            library = modules / 'runtime/runtime.so'
            library.write_bytes(b'linked runtime payload')
            paths = package_files(deps, 'server')
            self.assertIn(binary, paths)
            self.assertIn(library, paths)
            self.assertEqual(len(paths), 5)  # Three manifests and both payloads; other OS is absent.

    def test_missing_required_dependency_rejects_incomplete_inventory(self):
        with tempfile.TemporaryDirectory() as directory:
            deps = Path(directory)
            root = deps / 'node_modules/server'
            root.mkdir(parents=True)
            (root / 'package.json').write_text(json.dumps({'dependencies': {'required-runtime': '1'}}))
            with self.assertRaisesRegex(RuntimeError, 'Missing dependency: required-runtime'):
                package_files(deps, 'server')

    def test_foreign_prebuilds_count_toward_disk_without_using_host_libraries(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            paths = []
            for target, machine in [('android-x64', 62), ('linux-arm64', 183), ('linux-x64', 62)]:
                binary = root / 'prebuilds' / target / 'runtime.so'
                binary.parent.mkdir(parents=True)
                binary.write_bytes(b'\x7fELF\x02\x01' + bytes(12) + struct.pack('<H', machine))
                paths.append(binary)
            with patch('bench_footprint.platform.machine', return_value='x86_64'), \
                    patch('bench_footprint.subprocess.run', return_value=SimpleNamespace(
                        returncode=1, stdout='not a dynamic executable', stderr='')) as ldd:
                self.assertEqual(libraries(set(paths)), set())
                self.assertEqual(ldd.call_count, 1)
                self.assertEqual(ldd.call_args.args[0], ['ldd', str(paths[2])])
            self.assertEqual(len(inventory(set(paths))), 3)


if __name__ == '__main__':
    unittest.main()
