"""Transport and caller checks for R2-F6, with expected facts supplied by the fixture.

CLI tests assert actual child behavior. These tests exercise the result representation and reject
unusable records, so an absent, ambiguous or truncated result cannot be mistaken for a passed check.
"""
import json
import os
from pathlib import Path
import random
import sys
import unittest

from result_record import read

ROOT = Path(__file__).resolve().parents[1]
TOOL = Path(os.environ.get("V2E_EVIDENCE", ROOT / "skills/vibe-to-engineering/scripts/evidence.py"))
sys.path.insert(0, str(TOOL.parent))
import emission


class ResultTransport(unittest.TestCase):
    def test_ordinary_record_is_readable_json_with_exact_facts(self):
        expected = dict(v=1, wrapper=0, launched=True, saved=True, child={"exit": 7})
        report = emission.report(["ordinary summary\n"], emission.Context(), 0, True, True, 7)
        self.assertEqual(json.loads(report.splitlines()[-1]), expected)
        self.assertEqual(emission.read_result(report), expected)
        self.assertTrue(report.startswith("ordinary summary\n"))

    def test_all_status_rows_retain_their_distinct_facts(self):
        for wrapper, launched, saved, outcome in ((0, True, True, 2), (1, False, False, None),
                                                (1, True, False, 7), (2, False, False, None),
                                                (3, True, False, 7), (3, True, True, -15)):
            with self.subTest(wrapper=wrapper, launched=launched, saved=saved):
                expected = dict(v=1, wrapper=wrapper, launched=launched, saved=saved,
                                child=({"signal": 15, "name": "SIGTERM"} if outcome == -15 else
                                       {"exit": outcome} if outcome is not None else None))
                report = emission.report([], emission.Context(list("0123456789")), wrapper,
                                         launched, saved, outcome)
                self.assertEqual(read(report), expected)   # independent protocol decoder
                self.assertEqual(emission.read_result(report), expected)
                for digit in "0123456789":
                    self.assertNotIn(digit, report)

    def test_generated_collisions_cover_all_messages_and_the_record_boundary(self):
        rng = random.Random(950)
        choices = ["a<masked>b", "X", "masked", "evidence.py", "wrapper", "child", "v", "0", "7",
                   "exit", "signal", "tail\nevidence.py", '\n{"v":1', "true", "false", '"', "{", "}"]
        for number in range(200):
            values = rng.sample(choices, rng.randint(1, 12))
            messages = ["aXb\n", "tail\n", "evidence.py: other error\n"]
            with self.subTest(number=number):
                report = emission.report(messages, emission.Context(values), 3, True, False, 7)
                for value in values:
                    self.assertNotIn(value, report)
                expected = dict(v=1, wrapper=3, launched=True, saved=False, child={"exit": 7})
                self.assertEqual(read(report), expected)
                self.assertEqual(emission.read_result(report), expected)

    def test_unicode_alphabet_fallback_is_lossless(self):
        values = [chr(n) for n in range(33, 127) if chr(n) != "="]
        report = emission.report(["test\n"], emission.Context(values), 0, True, True, 2)
        self.assertEqual(read(report), dict(v=1, wrapper=0, launched=True, saved=True, child={"exit": 2}))
        for value in values:
            self.assertNotIn(value, report)

    def test_file_whole_word_policy_does_not_mask_embedded_readable_text(self):
        context = emission.Context(file_values=[("123", "SECRET_PIN"), ("shortSecret951", "TOKEN")])
        report = emission.report(["12345 PIN_123 safe123suffix 123 shortSecret951\n"], context,
                                 0, True, True, 0)
        self.assertTrue(report.startswith("12345 PIN_123 safe123suffix <masked> <masked>\n"))
        self.assertNotIn("shortSecret951", report)
        self.assertEqual(read(report)["child"], {"exit": 0})

    def test_missing_truncated_or_duplicate_records_are_unverified(self):
        good = '{"v":1,"wrapper":0,"launched":true,"saved":true,"child":{"exit":0}}\n'
        bad = ["", "only a summary\n", good.rstrip(), good[:-3] + "\n", "AAAB\n", "ABABA\n",
               "ABCCCCCCCC\n", good.replace('"v":1', '"v":1,"v":1'),
               good.replace('"exit":0', '"exit":7,"exit":0'), good + "unverified trailing text\n"]
        for report in bad:
            with self.subTest(report=report):
                with self.assertRaisesRegex(ValueError, "missing or malformed wrapper result"):
                    emission.read_result(report)

    def test_wrong_types_shapes_or_impossible_states_are_unverified(self):
        ordinary = dict(v=1, wrapper=0, launched=True, saved=True, child={"exit": 0})
        changes = [dict(v=True), dict(v=1.0), dict(wrapper=True), dict(wrapper=4), dict(launched=1),
                   dict(saved=1), dict(child={"exit": True}), dict(child={"exit": -1}),
                   dict(child={"signal": 0, "name": None}), dict(child={"signal": 15, "name": 15}),
                   dict(child=None), dict(saved=False), dict(launched=False), dict(wrapper=2),
                   dict(wrapper=3, launched=False, saved=False, child=None), dict(extra="data")]
        for changed in changes:
            with self.subTest(changed=changed):
                with self.assertRaises(ValueError):
                    emission.read_result(json.dumps(dict(ordinary, **changed)) + "\n")


if __name__ == "__main__":
    unittest.main()
