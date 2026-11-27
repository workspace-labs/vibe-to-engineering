"""Exercise the matrix adapter with tiny, local reader APIs and their real return conventions."""
import os
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest import mock

import test_literal_matrix as matrix


@unittest.skipUnless(sys.platform == 'darwin', 'the reader matrix adapter is native macOS')
class ReaderReportedErrors(unittest.TestCase):
    def test_only_completed_reads_can_count_as_coverage(self):
        node = os.environ.get('V2E_NODE') or shutil.which('node')
        self.assertTrue(node, 'the native reader control needs Node')
        with tempfile.TemporaryDirectory(prefix='v2e-reader-api-') as directory:
            root = Path(directory)
            shutil.copyfile(matrix.ROOT / 'tests/reader_matrix_harness.js', root / 'harness.js')
            fixture = root / 'sample.env'
            fixture.write_text('A=abc\n')
            adapter = matrix.DifferentialMatrix()
            adapter.tmp = root
            adapter.masked = {'sample': {'A': {'abc'}}}
            entry = root / 'reader.js'
            adapter.entries = {'node-v24.21.0': node, 'dotenv-18.0.4': str(entry), 'dotenv-0.5.0': str(entry)}
            cases = [
                ('config', 'return {parsed:{}}', None),
                ('config', 'process.env.A="abc"; return {parsed:{A:"abc"}}', 'abc'),
                ('config', 'return {error:new Error("unavailable")}', False),
                ('config', 'throw new Error("unavailable")', False),
                ('load', 'return false', False),
                ('load', 'return {error:new Error("unavailable")}', False),
                ('parse', 'return {A:"abc",error:"ordinary variable"}', 'abc'),
                ('parse', 'return new Error("unavailable")', False),
            ]
            with mock.patch.object(matrix, 'MATRIX_DIR', root):
                for api, body, expected in cases:
                    versions = ('18.0.4', '0.5.0') if api == 'load' else ('18.0.4',)
                    for version in versions:
                        with self.subTest(api=api, body=body, version=version):
                            entry.write_text('module.exports={' + api + '(){' + body + '}}')
                            if expected is False:
                                with self.assertRaisesRegex(AssertionError, 'NOT VERIFIED'):
                                    adapter.assert_covered('test reader', 'sample', adapter.read_dotenv(version, fixture))
                            else:
                                values = adapter.read_dotenv(version, fixture)
                                self.assertEqual(values, {'A': expected, 'B': None, 'C': None})
                                adapter.assert_covered('test reader', 'sample', values)
