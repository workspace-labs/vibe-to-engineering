"""Reader prerequisites must not mislabel a host or fetch unusable artifacts."""
import subprocess
import unittest
from unittest import mock

import reader_platform as readers
import reader_matrix_prepare as prepare


class ReaderPlatformTests(unittest.TestCase):
    def test_unsupported_hosts_refuse_before_any_probe(self):
        for system, architecture in [('win32', 'AMD64'), ('linux', 'aarch64'), ('darwin', 'x86_64')]:
            with self.subTest(system=system, architecture=architecture), \
                 mock.patch.object(readers.sys, 'platform', system), \
                 mock.patch.object(readers.platform, 'machine', return_value=architecture), \
                 mock.patch.object(readers.subprocess, 'run') as run, \
                 mock.patch.object(readers.shutil, 'which') as which:
                node, problems = readers.reader_prerequisites()
                self.assertIsNone(node)
                self.assertIn('requires macOS arm64', problems[0])
                run.assert_not_called()
                which.assert_not_called()

    def native_probe(self, shell_output=b'GNU bash, version 3.2.57(1)-release\n',
                     node_output=b'v20.20.2\n', shell_code=0, node_code=0):
        responses = [subprocess.CompletedProcess([], shell_code, shell_output, b''),
                     subprocess.CompletedProcess([], node_code, node_output, b'')]
        with mock.patch.object(readers.sys, 'platform', 'darwin'), \
             mock.patch.object(readers.platform, 'machine', return_value='arm64'), \
             mock.patch.object(readers.shutil, 'which', return_value='/trusted/node'), \
             mock.patch.object(readers.subprocess, 'run', side_effect=responses) as run:
            result = readers.reader_prerequisites()
            for call in run.call_args_list:
                self.assertNotIn('NODE_OPTIONS', call.kwargs['env'])
                self.assertNotIn('BASH_ENV', call.kwargs['env'])
            return result

    def test_claimed_native_reader_versions_are_accepted(self):
        self.assertEqual(self.native_probe(), ('/trusted/node', []))

    def test_other_shell_or_version_is_not_bash_32_coverage(self):
        for output, code in [(b'GNU bash, version 5.2.0\n', 0), (b'', 2), (b'not bash', 0)]:
            with self.subTest(output=output, code=code):
                _, problems = self.native_probe(shell_output=output, shell_code=code)
                self.assertTrue(any('bash 3.2' in problem for problem in problems))

    def test_wrong_node_version_or_failed_probe_is_not_coverage(self):
        for output, code in [(b'v24.19.0\n', 0), (b'v20.20.2\n', 1)]:
            with self.subTest(output=output, code=code):
                _, problems = self.native_probe(node_output=output, node_code=code)
                self.assertTrue(any('v20.20.2' in problem for problem in problems))

    def test_preparation_refuses_before_artifact_access(self):
        with mock.patch.object(prepare, 'reader_prerequisites', return_value=(None, ['unsupported host'])), \
             mock.patch.object(prepare, 'artifact') as artifact, \
             mock.patch.object(prepare.os, 'makedirs') as mkdir:
            with self.assertRaisesRegex(SystemExit, 'no reader artifacts were written or downloaded'):
                prepare.main()
            artifact.assert_not_called()
            mkdir.assert_not_called()


if __name__ == '__main__':
    unittest.main()
