"""Decoded boolean values must keep the same confidentiality as their source scalars.

Pure, portable regressions: no runners, user registry, project files or subprocesses.
"""

import json
import os
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
TOOL = Path(os.environ.get("V2E_EVIDENCE", ROOT / "skills/vibe-to-engineering/scripts/evidence.py"))
sys.path.insert(0, str(TOOL.parent))
import evidence
import emission


class DecodedBooleans(unittest.TestCase):
    def result(self, label, source, printed):
        values, settings = evidence.classify(evidence.read_secret(label, source))
        text, _ = evidence.mask(printed, values)
        return emission.Context(file_values=values).scrub(text), values, settings

    def assert_protected(self, label, source, decoded):
        for printed in (str(decoded), json.dumps(decoded)):
            with self.subTest(printed=printed):
                text, values, _ = self.result(label, source, printed + "\n")
                self.assertIn(printed, dict(values), (label, source))
                self.assertNotIn(printed, text)

    def test_json_decoded_booleans_in_objects_and_lists(self):
        for boolean in (True, False):
            for document in ({"password": boolean}, {"credentials": {"value": boolean}},
                             {"codes": [boolean]}, [boolean]):
                with self.subTest(document=document):
                    source = json.dumps(document)
                    self.assert_protected("secrets.json", source, boolean)

    def test_toml_decoded_booleans_in_tables_and_arrays(self):
        for literal, boolean in (("true", True), ("false", False)):
            for source in ("password = %s\n", "[credentials]\nvalue = %s\n", "codes = [%s]\n",
                           "credentials = {value = %s}\n"):
                with self.subTest(source=source, literal=literal):
                    self.assert_protected("secrets.toml", source % literal, boolean)

    def test_yaml_implicit_booleans_in_mappings_flow_and_lists(self):
        for literal, boolean in (("true", True), ("false", False), ("yes", True), ("no", False),
                                 ("on", True), ("off", False)):
            for spelling in (literal, literal.capitalize(), literal.upper()):
                for source in ("password: %s\n", "{password: %s}\n", "codes: [%s]\n", "codes:\n- %s\n"):
                    with self.subTest(source=source, spelling=spelling):
                        self.assert_protected("secrets.yaml", source % spelling, boolean)

    def test_yaml_explicit_boolean_tags_and_aliases(self):
        for literal, boolean in (("yes", True), ("off", False)):
            for tag in ("!!bool", "!!b%6fol", "!<tag:yaml.org,2002:bool>", "!"):
                for source in ("password: %s '%s'\n", "{password: %s '%s'}\n",
                               "password: %s |-\n  %s\n", "password: %s\n  '%s'\n"):
                    with self.subTest(source=source, tag=tag, literal=literal):
                        self.assert_protected("secrets.yaml", source % (tag, literal), boolean)
            self.assert_protected("secrets.yaml", "%TAG !b! tag:yaml.org,2002:\n---\npassword: !b!bool '"
                                  + literal + "'\n", boolean)
            self.assert_protected("secrets.yaml", "ordinary: &flag " + literal + "\npassword: *flag\n", boolean)
            self.assert_protected("secrets.yaml", "password: !!bool\n  &flag '" + literal
                                  + "'\ncopy: *flag\n", boolean)

    def test_ordinary_boolean_settings_remain_readable(self):
        for label, source in (("secrets.json", '{"debug": true, "verbose": false}'),
                              ("secrets.toml", "debug=true\nverbose=false\n"),
                              ("secrets.yaml", "debug: yes\nverbose: off\n")):
            with self.subTest(label=label):
                printed = "True False true false\n"
                text, values, settings = self.result(label, source, printed)
                self.assertEqual(text, printed)
                self.assertEqual(values, [])
                self.assertEqual(settings, ["debug", "verbose"])

    def test_quoted_or_string_tagged_words_do_not_gain_boolean_readings(self):
        for label, source in (("secrets.json", '{"password": "true"}'),
                              ("secrets.toml", 'password="true"\n'),
                              ("secrets.yaml", "password: 'yes'\n"),
                              ("secrets.yaml", 'password: "off"\n'),
                              ("secrets.yaml", "password: !!str yes\n"),
                              ("secrets.yaml", "password: !!str\n  yes\n"),
                              ("secrets.yaml", "{password: !!str off}\n"),
                              ("secrets.yaml", "password: !custom yes\n"),
                              ("secrets.yaml", "password: |\n  yes\n")):
            with self.subTest(label=label, source=source):
                printed = "True False\n"
                text, values, _ = self.result(label, source, printed)
                self.assertEqual(text, printed)
                self.assertNotIn("True", dict(values))
                self.assertNotIn("False", dict(values))


if __name__ == "__main__":
    unittest.main()
