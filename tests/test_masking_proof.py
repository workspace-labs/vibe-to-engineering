"""A masking exam must fail if the child exits without ever printing its input."""
import sys
import unittest
from unittest import mock

import test_evidence


class MaskingProof(unittest.TestCase):
    def test_failed_child_and_missing_masked_output_fail_each_masking_fixture(self):
        for program, reason in (("raise SystemExit(7)", "'exit': 7"),
                                ("print('masking fixture read the input')", "Regex didn't match")):
            with self.subTest(program=program):
                case = test_evidence.Evidence("test_every_value_a_secret_file_holds_is_masked_however_it_is_written")
                actual = case.run_tool

                def substitute(out, *command, **settings):
                    return actual(out, sys.executable, "-c", program, **settings)

                result = unittest.TestResult()
                with mock.patch.object(case, "run_tool", side_effect=substitute):
                    case.run(result)
                self.assertEqual(result.errors, [])
                self.assertEqual(result.skipped, [])
                self.assertEqual(len(result.failures), 5)
                for _, failure in result.failures:
                    self.assertIn(reason, failure)
