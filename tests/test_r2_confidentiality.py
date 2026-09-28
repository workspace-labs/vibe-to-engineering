"""The R2 confidentiality/status slice's generated battery (release handoff, checklist B): a deterministic
set of adversarial --env name/value sets and orderings driven through the real CLI, asserting the Class II
invariant over the single emission choke point — no declared value appears in the saved evidence (header
included), the stdout echo, or the stderr summary/diagnostics — plus unit tests for the emission module
itself (safe fallback markers, the pre-parse value collection, the wrapper status namespace data).

The CLI battery runs against any candidate and fails against the pre-slice one on the leaked bytes:
  V2E_EVIDENCE=/path/to/preserved/skills/vibe-to-engineering/scripts/evidence.py \
      python3 -m unittest discover -s tests -p test_r2_confidentiality.py -v
The emission unit tests exercise the slice's new module; on a candidate that predates it they skip (the CLI
battery above is the fail-before proof), and they run for real on the repaired tree. Run from the
repository root:  python3 -m unittest discover -s tests -p test_r2_confidentiality.py -v
"""

import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock
from result_record import read

ROOT = Path(__file__).resolve().parents[1]
TOOL = Path(os.environ.get("V2E_EVIDENCE", ROOT / "skills" / "vibe-to-engineering" / "scripts" / "evidence.py"))
sys.path.insert(0, str(TOOL.parent))
import evidence  # noqa: E402
try:
    import emission  # noqa: E402 — the slice's new module; absent on candidates that predate it
except ImportError:
    emission = None

PY = os.path.realpath(sys.executable)

# The deterministic adversarial case table: (case name, [settings], values that must never appear,
# whether the scan covers the whole output or only the body below the header). --env names are shell
# names ([A-Za-z_][A-Za-z0-9_]*), so values embedded in other names are spelled without dashes; every
# value usually carries a unique tag. SUPERSEDED by the R2-F2/F6 corrective: the single-character case
# now scans ALL surfaces too; the retained scope column records the old fixture without exempting it.
# All cases must also retain a recoverable outcome, even when its words/digits are protected values.
CASES = (
    ("a value inside another name, chained",
     ["N7811=w1q7811", "w1q7811_X=w2q7811", "w2q7811_Y=w3q7811"],
     ["w1q7811", "w2q7811", "w3q7811"], "whole"),
    ("the same chain in the reverse argument order",
     ["w2q7811_Y=w3q7811", "w1q7811_X=w2q7811", "N7811=w1q7811"],
     ["w1q7811", "w2q7811", "w3q7811"], "whole"),
    ("a name that is its own value",
     ["SELF7812=SELF7812"], ["SELF7812"], "whole"),
    ("a value that is another setting's whole name",
     ["K7813=OTHER7813", "OTHER7813=v7813"], ["OTHER7813", "v7813"], "whole"),
    ("values at both ends of names",
     ["PRE7814=ab7814", "ab7814cd=cd7814", "Yab7814Z=xy7814"],
     ["ab7814", "cd7814", "xy7814"], "whole"),
    ("one value containing another",
     ["A7815=overlap7815", "B7815=overlap7815plus"], ["overlap7815plus", "overlap7815"], "whole"),
    ("an all-digit value inside a name",
     ["D7816=907816", "D907816X=v7816"], ["907816", "v7816"], "whole"),
    ("a value holding equals signs",
     ["E7817=a=b=7817", "K7817=v7817"], ["a=b=7817", "v7817"], "whole"),
    ("values colliding with the mask syntax",
     ["A7818=<masked", "B7818=masked", "C7818=<masked SECRET>"],
     ["<masked SECRET>", "<masked", "masked"], "whole"),
    ("values colliding with wrapper words",
     ["A7819=evidence", "B7819=secret values masked", "C7819=the check exited"],
     ["secret values masked", "the check exited", "evidence"], "whole"),
    ("a single-character value inside a name",
     ["S7820=z", "zS7820=v7820"], ["zS7820", "v7820", "z"], "body"),
    ("an empty value beside a secret one",
     ["EMPTY7821=", "K7821=v7821"], ["v7821"], "whole"),
)


class ConfidentialityBattery(unittest.TestCase):
    """Every generated case through the real wrapper: the check runs (wrapper 0), all of its declared
    values reach it (the child prints them from its own environment), and none of them survives in any
    emitted byte — evidence header and body, stdout echo, stderr summary."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="v2e-r2b-")).resolve()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def enroll(self, home):
        enroll = getattr(evidence, "enroll_runner", None)
        if enroll is None:
            return None   # the historical R2 candidate gates by probing: the run still demonstrates the leak
        with mock.patch.dict(os.environ, {"HOME": str(home)}):
            with open(os.devnull, "w") as quiet:
                enroll(PY, ask=lambda prompt: evidence.APPROVAL, out=quiet)
        return True

    def test_no_declared_value_survives_any_emission(self):
        for index, (name, settings, values, scope) in enumerate(CASES):
            with self.subTest(name):
                home = self.tmp / ("home-%d" % index)
                home.mkdir()
                self.enroll(home)
                project = self.tmp / ("project-%d" % index)
                (project / ".vibe-to-engineering" / "evidence").mkdir(parents=True)
                declared = [setting.split("=", 1)[0] for setting in settings]
                (project / "check.py").write_text(
                    "from pathlib import Path\nPath('check-ran').write_text('ran')\n"
                    "import os\nprint(%s)\n" % ", ".join("os.environ[%r]" % name for name in declared))
                out = project / ".vibe-to-engineering" / "evidence" / "check.txt"
                done = subprocess.run([sys.executable, str(TOOL), "--project", str(project), "--out", str(out)]
                                      + [part for setting in settings for part in ("--env", setting)]
                                      + ["--", sys.executable, "-B", "check.py"],
                                      stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                      env=dict(os.environ, HOME=str(home)))
                printed = done.stdout.decode("utf-8", "replace")
                report = done.stderr.decode("utf-8", "replace")
                saved = out.read_text(encoding="utf-8") if out.exists() else None
                self.assertEqual(done.returncode, 0, report)   # the check ran; its outcome is data
                self.assertTrue((project / "check-ran").exists())
                self.assertIsNotNone(saved)
                self.assertEqual(saved, printed)
                for text in (printed, saved, report):
                    for value in values:
                        self.assertNotIn(value, text)   # the Class II invariant, checked first
                self.assertEqual(read(report), dict(v=1, wrapper=0, launched=True, saved=True,
                                                     child={"exit": 0}))
                if not any(word in "the check exited 0" for word in values):
                    self.assertIn("the check exited 0", report)   # safe human-readable control, in addition
                                                                    # to the unconditional outcome above


class EmissionModule(unittest.TestCase):
    """The emission choke point itself: the pre-parse maskable-value collection, the scrub's safe fallback
    markers, and the child-outcome data. Skipped (not failed) on a candidate that predates the module."""

    def setUp(self):
        if emission is None:
            self.skipTest("this candidate predates the emission module — the CLI battery is the proof")

    def test_collect_gathers_every_env_value_before_parsing(self):
        argv = ["--project", "p", "--env", "A=v1q-7831", "--env=B=v2q-7831", "--with-path", "/somewhere-7831",
                "--env", "DUP=x-7831", "--env", "DUP=y-7831", "--out", "o", "--", "python3", "-c", "print(1)"]
        self.assertEqual(sorted(emission.collect(argv)), sorted(["v1q-7831", "v2q-7831", "x-7831", "y-7831"]))

    def test_collect_stops_at_the_command_boundary_and_never_reads_the_parent(self):
        with mock.patch.dict(os.environ, {"PARENT_SECRET7832": "leak-7832"}):
            argv = ["--env", "A=v-7832", "positional-start", "--env", "B=after-7832"]
            self.assertEqual(emission.collect(argv), ["v-7832"])   # a positional starts the command…
            argv = ["--env", "A=v-7832", "--", "--env", "B=after-7832"]
            self.assertEqual(emission.collect(argv), ["v-7832"])   # …and so does '--'
            self.assertNotIn("leak-7832", emission.collect(argv))  # the parent's environment is never read

    def test_collect_skips_values_that_could_not_be_masked(self):
        argv = ["--env", "EMPTY=", "--env", "PAD= \t=", "--env", "KEPT=v-7833"]
        self.assertEqual(emission.collect(argv), ["v-7833"])

    def test_scrub_replaces_longest_first_and_never_reintroduces_a_value(self):
        text = "one ab-7834 here, one ab-7834-plus there, ab-7834 again"
        cleaned = emission.scrub(text, ["ab-7834", "ab-7834-plus"])
        self.assertNotIn("ab-7834", cleaned)
        self.assertEqual(cleaned.count("<masked>"), 3)
        for value in ("masked", "<masked", "ask", "m"):   # a value inside the ordinary marker itself
            cleaned = emission.scrub("the word %s stands here-7834" % value, [value])
            self.assertNotIn(value, cleaned)               # the fallback marker never reintroduces it
            self.assertNotIn("<masked>", cleaned)          # …because the ordinary marker was unsafe

    def test_fallback_marker_avoids_every_all_one_character_value(self):
        values = ["*", "**", "***", "%", "%%"]             # block the first punctuation candidates
        marker = emission.fallback(values)
        for value in values:
            self.assertNotIn(value, marker)
        self.assertEqual(emission.fallback(["ordinary-7835"]), "<masked>")

    def test_child_outcome_is_accurate_data(self):
        self.assertEqual(emission.child_outcome(0), "exited 0")
        self.assertEqual(emission.child_outcome(2), "exited 2")
        self.assertEqual(emission.child_outcome(-15), "terminated by signal 15 (SIGTERM)")
        self.assertEqual(emission.child_outcome(-9), "terminated by signal 9 (SIGKILL)")
        self.assertIn("signal 45", emission.child_outcome(-45))   # an unusual signal still accurate

    def test_the_wrapper_status_namespace_is_the_approved_one(self):
        self.assertEqual((emission.RAN, emission.OPERATIONAL, emission.REFUSED, emission.INTEGRITY),
                         (0, 1, 2, 3))

    def test_a_mask_label_is_value_free_or_falls_back(self):
        values = [("r2SecretName7719", "A"), ("other-7719", "r2SecretName7719_X"), ("1234", "PIN")]
        everywhere = frozenset(("r2SecretName7719", "other-7719", "1234"))
        label = evidence.safe_label("r2SecretName7719_X", values, everywhere)
        self.assertNotIn("r2SecretName7719", label)        # a name holding a declared value falls back
        self.assertEqual(evidence.safe_label("PIN", values, everywhere), "<masked PIN>")   # a clean name
        self.assertEqual(evidence.safe_label("A", values, everywhere), "<masked A>")

    def test_a_label_keeps_attribution_when_a_short_value_is_not_a_whole_word_inside_it(self):
        # a short or all-digit file value masks only as a whole word: glued inside a name it is not masked,
        # so the name may still attribute the mask
        values = [("123", "FILE7836"), ("v-7836", "PIN_123")]
        label = evidence.safe_label("PIN_123", values, frozenset())
        self.assertEqual(label, "<masked PIN_123>")
        label = evidence.safe_label("PIN 123", values, frozenset())   # …but a whole-word hit falls back
        self.assertNotIn("123", label)


if __name__ == "__main__":
    unittest.main()
