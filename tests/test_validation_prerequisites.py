"""Validation boundary and reader preparation contracts using ordinary disposable inputs."""
import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
import zipfile
from unittest import mock

import reader_matrix_prepare as prepare
import run_validation as validation


class ValidationContracts(unittest.TestCase):
    def test_worker_sees_only_required_inputs_and_its_own_tool_path(self):
        with tempfile.TemporaryDirectory(prefix='v2e-worker-env-') as directory:
            root = Path(directory)
            fixture = root / 'source'
            scripts = fixture / 'skills' / 'vibe-to-engineering' / 'scripts'
            scripts.mkdir(parents=True)
            (scripts / 'childenv.py').write_text('SCRATCH_BASE = "/tmp"\n')
            (fixture / 'LICENSE').write_text('Synthetic validation fixture.\n')
            tests = fixture / 'tests'
            tests.mkdir()
            # Let the normal harness prepare, copy and launch a small worker. Its source
            # represents an untouched checkout even inside a harness that redirected its own copy.
            (tests / 'run_validation.py').write_text(
                'import json, os, sys\nfrom pathlib import Path\n'
                'assert "--worker" in sys.argv\n'
                'output = Path(sys.argv[sys.argv.index("--output") + 1])\n'
                'keys = ["V2E_PARENT_ONLY", "PARENT_ONLY", "PATH", "HOME", "GIT_CONFIG_GLOBAL"]\n'
                '(output / "worker.json").write_text(json.dumps({key: os.getenv(key) for key in keys}))\n')
            extra = root / 'unused-parent-tools'
            extra.mkdir()
            argv = ['run_validation.py', '--scope', 'portable', '--output', str(root / 'output')]
            with mock.patch.dict(os.environ, {'PARENT_ONLY': 'ordinary-parent-marker', 'V2E_PARENT_ONLY': '1',
                                               'PATH': str(extra)}), mock.patch.object(sys, 'argv', argv), \
                    mock.patch.object(validation, 'ROOT', fixture), contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(validation.main(), 0)
            values = json.loads((root / 'output' / 'worker.json').read_text())
            self.assertIsNone(values['PARENT_ONLY'])
            self.assertIsNone(values['V2E_PARENT_ONLY'])
            self.assertNotIn(str(extra), values['PATH'].split(os.pathsep))
            self.assertEqual(Path(values['GIT_CONFIG_GLOBAL']).parent, Path(values['HOME']))

    def test_native_recipe_and_identity_cover_the_actual_prerequisites(self):
        import re
        for doc in ('README.md', 'TEST-EVIDENCE.md'):
            blocks = re.findall(r'```[^\n]*\n(.*?)```', (validation.ROOT / doc).read_text(encoding='utf-8'), re.S)
            self.assertTrue(any('--scope macos' in block and all(name in block for name in
                                ('V2E_BROWSER', 'V2E_NODE', 'V2E_READER_MATRIX_DIR')) for block in blocks), doc)
        import validation_prerequisites as prerequisites
        with tempfile.TemporaryDirectory(prefix='v2e-identity-') as directory:
            root = Path(directory)
            (root / 'home').mkdir()
            (root / 'temp').mkdir()
            env = prerequisites.worker_environment(root, False, os.environ)
            env.update(V2E_NODE=sys.executable, V2E_BROWSER=sys.executable)
            folder = root / 'readers'
            folder.mkdir()
            harness = (validation.ROOT / 'tests/reader_matrix_harness.js').read_bytes()
            (folder / 'harness.js').write_bytes(harness)
            (folder / 'manifest.json').write_text('{"entries":{}}')
            env['V2E_READER_MATRIX_DIR'] = str(folder)
            revision = 'a1' * 20
            with mock.patch.object(prerequisites, 'ARCHIVE_REVISION', revision):
                identity, problems = prerequisites.validation_identity(validation.ROOT, env, True)
            self.assertEqual(identity['source']['revision'], revision)
            self.assertEqual(identity['python']['executable'], sys.executable)
            self.assertTrue(identity['host']['platform'])
            for name in ('node', 'browser'):
                self.assertTrue(identity[name]['version'].startswith('Python '))
                self.assertEqual(identity[name]['sha256'], prerequisites.file_digest(sys.executable))
            self.assertEqual(identity['readers']['harness_sha256'], hashlib.sha256(harness).hexdigest())
            self.assertTrue(any('v20.20.2' in problem for problem in problems))

    def test_preparation_owns_fresh_output_and_refuses_existing_names(self):
        with tempfile.TemporaryDirectory(prefix='v2e-prepare-owner-') as directory:
            root = Path(directory).resolve()
            target, retained = root / 'prepared', root / 'retained'
            retained.mkdir()
            name, wheel = 'python-dotenv-1.2.3', retained / 'example.whl'
            with zipfile.ZipFile(wheel, 'w') as archive:
                archive.writestr('dotenv/__init__.py', '# synthetic reader metadata\n')
            pins = {'artifacts': {name: {'file': wheel.name, 'sha256': hashlib.sha256(wheel.read_bytes()).hexdigest()}}}
            with mock.patch.object(prepare, 'reader_prerequisites', return_value=(None, [])), \
                    mock.patch.object(prepare, 'PROVENANCE', pins), mock.patch.object(prepare, 'COMPAT', str(retained)), \
                    mock.patch.object(prepare.urllib.request, 'urlopen', side_effect=AssertionError('unexpected network')), \
                    contextlib.redirect_stdout(io.StringIO()):
                with mock.patch.object(prepare, 'TARGET', str(target)):
                    prepare.main()
                self.assertEqual((target / 'harness.js').read_bytes(),
                                 (validation.ROOT / 'tests/reader_matrix_harness.js').read_bytes())
                self.assertEqual(set(json.loads((target / 'manifest.json').read_text())['entries']), {name})
                outside = root / 'prior-record'
                outside.write_bytes(b'prior record')
                existing = root / 'existing'
                existing.mkdir()
                (existing / 'harness.js').write_bytes(b'original harness name')
                with mock.patch.object(prepare, 'TARGET', str(existing)):
                    with self.assertRaisesRegex(SystemExit, 'new reader target'):
                        prepare.main()
                self.assertEqual(list(existing.iterdir()), [existing / 'harness.js'])
                self.assertEqual((existing / 'harness.js').read_bytes(), b'original harness name')
                self.assertEqual(outside.read_bytes(), b'prior record')
