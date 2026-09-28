"""A1-F03/F04: failure observations and executable artifact provenance, with synthetic fixtures only."""
import hashlib
import io
import json
import shutil
import subprocess
import tarfile
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import test_literal_matrix as matrix
import reader_matrix_prepare as prepare


class ReaderFailures(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='v2e-reader-fail-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.path = self.root / 'simple.env'
        self.path.write_text('A=abc\n')
        self.reader = matrix.DifferentialMatrix()
        self.reader.tmp = self.root
        self.reader.entries = {'node-v24.21.0': '/usr/bin/false', 'dotenv-18.0.4': 'unused',
                               'python-dotenv-1.2.3': str(self.root)}

    def test_nonzero_node_is_not_an_empty_success(self):
        for required in ('', '1'):
            with self.subTest(required=required), mock.patch.dict(matrix.os.environ, {'V2E_REQUIRE_MATRIX': required}):
                with self.assertRaisesRegex(AssertionError, 'NOT VERIFIED'):
                    self.reader.read_node('/usr/bin/false', self.path)

    def test_malformed_or_wrong_shape_output_is_not_coverage(self):
        for payload in (b'', b'not-json', b'{}', b'[]', b'{"A":3,"B":null,"C":null}'):
            for adapter in ('node', 'python'):
                with self.subTest(payload=payload, adapter=adapter):
                    with mock.patch.object(matrix.subprocess, 'run', return_value=
                                           subprocess.CompletedProcess([], 0, payload, b'')):
                        with self.assertRaisesRegex(AssertionError, 'NOT VERIFIED'):
                            if adapter == 'node':
                                self.reader.read_node('node', self.path)
                            else:
                                self.reader.read_pydotenv(self.path)

    def test_missing_dotenv_result_is_not_coverage(self):
        with mock.patch.object(matrix.subprocess, 'run', return_value=
                               subprocess.CompletedProcess([], 0, b'', b'')):
            with self.assertRaisesRegex(AssertionError, 'NOT VERIFIED'):
                self.reader.read_dotenv('18.0.4', self.path)

    def test_harness_exception_even_with_partial_data_is_not_verified(self):
        def failed_harness(cmd, **kwargs):
            result = Path(cmd[-2])
            result.write_text(json.dumps({'failed': True, 'env': {'A': 'abc', 'B': None, 'C': None}}))
            return subprocess.CompletedProcess(cmd, 0, b'', b'')
        with mock.patch.object(matrix.subprocess, 'run', side_effect=failed_harness):
            with self.assertRaisesRegex(AssertionError, 'NOT VERIFIED'):
                self.reader.read_dotenv('18.0.4', self.path)

    def test_shell_source_failure_is_not_coverage(self):
        with mock.patch.object(matrix.subprocess, 'run', return_value=
                               subprocess.CompletedProcess([], 0, b'YWJj\n\n\n', b'SRC=1\n')):
            with self.assertRaisesRegex(AssertionError, 'NOT VERIFIED'):
                self.reader.read_bash(self.path)

    def test_nonempty_smoke_control_cannot_silently_disappear(self):
        self.reader.masked = {'simple': {'A': {'abc'}}}
        with self.assertRaisesRegex(AssertionError, 'NOT VERIFIED'):
            self.reader.assert_covered('reader', 'simple', {'A': None, 'B': None, 'C': None})

    def test_successful_empty_values_remain_valid(self):
        values = {'A': '', 'B': None, 'C': None}
        with mock.patch.object(matrix.subprocess, 'run', return_value=
                               subprocess.CompletedProcess([], 0, json.dumps(values).encode(), b'')):
            self.assertEqual(self.reader.read_node('node', self.path), values)


class ArtifactIdentity(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='v2e-artifact-identity-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.name = 'dotenv-18.0.4'
        self.dest = self.root / 'extract' / self.name
        self.files = {'package/package.json': b'{"main":"main.js"}',
                      'package/main.js': b'module.exports=require("./reader");\n',
                      'package/reader.js': b'module.exports={config(){return {};}};\n'}
        archive = self.root / 'artifacts' / 'dotenv.tgz'
        archive.parent.mkdir()
        with tarfile.open(archive, 'w:gz') as stream:
            for name, content in self.files.items():
                info = tarfile.TarInfo(name)
                info.size, info.mode = len(content), 0o644
                stream.addfile(info, io.BytesIO(content))
                path = self.dest / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(content)
        self.provenance = {self.name: {'file': archive.name, 'sha256': hashlib.sha256(archive.read_bytes()).hexdigest()}}
        self.entry = self.dest / 'package/main.js'
        (self.root / 'manifest.json').write_text(json.dumps({'entries': {self.name: str(self.entry)}}))
        shutil.copyfile(matrix.ROOT / 'tests/reader_matrix_harness.js', self.root / 'harness.js')
        for patch in (mock.patch.object(matrix, 'MATRIX_DIR', self.root),
                      mock.patch.object(matrix, 'PROVENANCE', self.provenance),
                      mock.patch.object(matrix.shutil, 'which', return_value='/trusted/node'),
                      mock.patch.object(matrix.subprocess, 'run', return_value=
                                        subprocess.CompletedProcess([], 0, b'v20.20.2\n', b''))):
            patch.start()
            self.addCleanup(patch.stop)

    def missing(self):
        return matrix.DifferentialMatrix.what_is_missing()

    def test_untouched_offline_artifacts_are_accepted(self):
        self.assertEqual(self.missing(), [])

    def test_entry_and_imported_module_tampering_is_refused(self):
        for rel in ('package/main.js', 'package/reader.js'):
            path = self.dest / rel
            with self.subTest(file=rel):
                original = path.read_bytes()
                path.write_bytes(b'module.exports={};')
                self.assertTrue(self.missing(), 'an unchanged archive must not authorize modified code')
                path.write_bytes(original)

    def test_redirected_manifest_is_refused(self):
        other = self.root / 'substitute.js'
        other.write_text('module.exports={config(){return {};}};')
        (self.root / 'manifest.json').write_text(json.dumps({'entries': {self.name: str(other)}}))
        self.assertTrue(self.missing(), 'a substituted manifest target was accepted')

    def test_modified_harness_is_refused(self):
        (self.root / 'harness.js').write_text('process.exit(0);')
        self.assertTrue(self.missing(), 'the actual harness must match the repository harness')

    def test_extra_importable_file_is_refused(self):
        (self.dest / 'package/reader.json').write_text('{}')
        self.assertTrue(self.missing(), 'the extracted tree must match the archive, including extra files')

    def test_prepare_does_not_reuse_tampered_extraction(self):
        self.entry.write_text('module.exports={};')
        with mock.patch.object(prepare, 'TARGET', str(self.root)), \
             mock.patch.object(prepare, 'PROVENANCE', {'artifacts': self.provenance}):
            with self.assertRaises((ValueError, SystemExit)):
                prepare.main()


if __name__ == '__main__':
    unittest.main()
