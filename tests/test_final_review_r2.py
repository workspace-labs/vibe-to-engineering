"""Regression tests for the R2 corrective — slice A2 (R2-F5, runner identity; owner decision 5.2 and release
decision 3.3) and the confidentiality/status slice (R2-F2, R2-F3, R2-F4, R2-F6; owner decision 5.3 and the
release handoff's checklist B). The F2/F3/F4/F6 classes land with their slice below the F5 class.

  F5  validation must not give an untrusted candidate execution privileges, and a path or symlink swap must
      not change the launched executable. The pre-A2 candidate probed the resolved runner on every run — a
      compiled fake answered the probe and its payload executed during routine validation — and then launched
      the original command NAME, so a binary replaced after the probe ran as a different program. The repair
      is per-user enrollment at ~/.vibe-to-engineering/runners.json: enrollment (--enroll-runner) discloses
      the resolved path, size and SHA-256 and runs the one profile probe only after the human types the
      approval word — an approval is never reused for different bytes; a routine run validates hash-only and
      never executes the candidate; and the bytes launched are the enrolled bytes — pin path for a location
      the user can write neither the file nor the folder of (launched at the enrolled path), pin copy launched
      from a private copy written from the very bytes just hashed. Unenrolled, malformed, unsupported or
      changed identities refuse before the check runs (exit 2, no evidence); a changed runner names manual
      re-enrollment as the remedy, and nothing is ever enrolled or re-enrolled automatically.

The F5 class fails against the pre-A2 candidate; the Emission (F2/F3), RecordedPaths (F4) and WrapperStatus
(F6) classes fail against the post-A2, pre-this-slice candidate — run any preserved candidate with
  V2E_EVIDENCE=/path/to/preserved/skills/vibe-to-engineering/scripts/evidence.py \
      python3 -m unittest discover -s tests -p test_final_review_r2.py -v
—and all pass after the repairs. Tests that demonstrate a mechanism enroll conditionally, so against a
candidate without enrollment (the historical R2 snapshot) they fail on the behavior itself (the untrusted
execution, the leaked bytes, the substituted program), not merely on the missing API. Run from the
repository root:

  python3 -m unittest discover -s tests -p test_final_review_r2.py -v
"""

import contextlib
import hashlib
import importlib.util
import io
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
TOOL = Path(os.environ.get("V2E_EVIDENCE", ROOT / "skills" / "vibe-to-engineering" / "scripts" / "evidence.py"))
sys.path.insert(0, str(TOOL.parent))
import evidence  # noqa: E402
import childenv  # noqa: E402


def scratch_base(home):
    """The scratch base a run with `home` as HOME uses: per-user now (~/.vibe-to-engineering/runs, A3),
    never the constant /tmp."""
    return os.path.join(str(home), ".vibe-to-engineering", "runs")

# A compiled lookalike for the node kind: answers the profile probe, otherwise prints its baked line and —
# with MARKER — writes a marker at a baked absolute path, so a test can tell exactly which bytes executed.
FAKE = (r'#include <stdio.h>' + "\n" + r'#include <string.h>' + "\n"
        r'int main(int argc, char **argv) {' + "\n"
        r'    if (argc > 1 && strcmp(argv[1], "--version") == 0) { printf("v20.20.2\n"); return 0; }' + "\n"
        r'#ifdef MARKER' + "\n"
        r'    FILE *m = fopen(MARKER, "w"); if (m) { fputs("ran", m); fclose(m); }' + "\n"
        r'#endif' + "\n"
        r'    printf("%s\n", LINE);' + "\n"
        r'    return 0;' + "\n" + r'}' + "\n")

# A candidate that answers its profile only while it stands at its original path: a private copy of it cannot
# answer, so it can take neither pin mode and enrollment must refuse it.
ROOTED = (r'#include <stdio.h>' + "\n" + r'#include <string.h>' + "\n" + r'#include <mach-o/dyld.h>' + "\n"
          r'int main(int argc, char **argv) {' + "\n"
          r'    char path[4096]; unsigned int size = sizeof(path);' + "\n"
          r'    if (_NSGetExecutablePath(path, &size) != 0) return 1;' + "\n"
          r'    if (argc > 1 && strcmp(argv[1], "--version") == 0 && strstr(path, ORIG)) {'
          r' printf("v20.20.2\n"); return 0; }' + "\n"
          r'    printf("not-the-profile\n");' + "\n"
          r'    return 0;' + "\n" + r'}' + "\n")


class RunnerIdentity(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="v2e-r2-")).resolve()
        self.count = 0

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def fresh_home(self, name):
        home = self.tmp / ("home-%s" % re.sub(r"\W+", "-", name))
        home.mkdir()
        return home

    def project(self, name, files=None):
        self.count += 1
        project = self.tmp / (re.sub(r"\W+", "-", name) + "-%d" % self.count)
        (project / ".vibe-to-engineering" / "evidence").mkdir(parents=True)
        for file, content in (files if files is not None else {".env": "SECRET_KEY=hunter2-not-real\n"}).items():
            (project / file).write_text(content)
        (project / "check.py").write_text("from pathlib import Path\nPath('check-ran').write_text('ran')\n")
        return project

    def run_tool(self, project, command, home, with_path=(), out="check.txt"):
        """A routine run of the tool over `project` with `home` as the user's HOME: (exit code, what it
        printed, the evidence text or None, its report, whether the python check ran)."""
        out = project / ".vibe-to-engineering" / "evidence" / out
        settings = [part for folder in with_path for part in ("--with-path", str(folder))]
        done = subprocess.run([sys.executable, str(TOOL), "--project", str(project), "--out", str(out)] + settings
                              + ["--"] + list(command), stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                              env=dict(os.environ, HOME=str(home)))
        return (done.returncode, done.stdout.decode("utf-8", "replace"),
                out.read_text(encoding="utf-8") if out.exists() else None,
                done.stderr.decode("utf-8", "replace"), (project / "check-ran").exists())

    def enroll_cli(self, program, home, approve=b"enroll\n", with_path=()):
        done = subprocess.run([sys.executable, str(TOOL), "--enroll-runner", str(program)]
                              + [part for folder in with_path for part in ("--with-path", str(folder))],
                              input=approve, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                              env=dict(os.environ, HOME=str(home)))
        return (done.returncode, done.stdout.decode("utf-8", "replace"), done.stderr.decode("utf-8", "replace"))

    def enroll_api(self, program, home, ask=None, with_path=()):
        """Enrollment through the module API, when the candidate under test has it (None when it does not)."""
        enroll = getattr(evidence, "enroll_runner", None)
        if enroll is None:
            return None
        with mock.patch.dict(os.environ, {"HOME": str(home)}):
            with open(os.devnull, "w") as quiet:
                enroll(str(program), with_path, ask=ask or (lambda prompt: evidence.APPROVAL), out=quiet)
        return True

    def registry(self, home):
        path = home / ".vibe-to-engineering" / "runners.json"
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None

    def compile(self, dest, defines=(), source=FAKE):
        cc = shutil.which("cc")
        if not cc:
            self.skipTest("NOT VERIFIED: no C compiler to build a binary lookalike")
        c = self.tmp / ("source-%s.c" % dest.name)
        c.write_text(source)
        subprocess.run([cc] + list(defines) + [str(c), "-o", str(dest)], check=True)
        return dest

    def in_process(self, argv, home, inject):
        """The tool inside this process with inject(tool) wrapping one of its steps — to mutate the world at
        the exact moment between identity validation and launch."""
        spec = importlib.util.spec_from_file_location("evidence_r2_under_test", str(TOOL))
        tool = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(tool)
        inject(tool)
        out, err = io.StringIO(), io.StringIO()
        with mock.patch.dict(os.environ, {"HOME": str(home)}), contextlib.redirect_stdout(out), \
                contextlib.redirect_stderr(err):
            code = tool.main(argv)
        return code, out.getvalue(), err.getvalue()

    # ---------------------------------------------------- routine validation never executes an untrusted candidate

    def test_an_unenrolled_candidate_is_not_executed_by_routine_validation(self):
        home = self.fresh_home("unenrolled")
        with self.subTest("a real runner with no enrollment"):
            project = self.project("real python")
            code, _, saved, report, ran = self.run_tool(project, [sys.executable, "-B", "check.py"], home)
            self.assertEqual(code, 2, report)
            self.assertFalse(ran)                       # nothing ran
            self.assertIsNone(saved)                    # no evidence
            self.assertIn("enrolled", report)
            self.assertIn("--enroll-runner", report)    # the remedy is named
        with self.subTest("a compiled untrusted candidate is never executed — not even to validate it"):
            # R2-F5, first mechanism: the pre-A2 gate's own profile probe executed the candidate — this fake
            # answers the probe perfectly, and proves its execution with a marker at an absolute path
            tools = self.tmp / "untrusted-tools"
            tools.mkdir()
            project = self.project("compiled fake")
            marker = project / "untrusted-executed-7751"
            self.compile(tools / "node", ("-DLINE=\"untrusted-ran-7751\"",
                                          "-DMARKER=\"%s\"" % str(marker).replace("\\", "\\\\")))
            code, _, saved, report, _ = self.run_tool(project, ["node", "--version"], home, with_path=[tools])
            self.assertEqual(code, 2, report)
            self.assertIsNone(saved)
            self.assertFalse(marker.exists())           # its payload never ran: routine validation is hash-only
            self.assertIn("enrolled", report)

    # ---------------------------------------------------- enrollment: disclosure, approval, one disclosed probe

    def test_enrollment_discloses_the_identity_and_needs_the_approval_word(self):
        home = self.fresh_home("approval")
        for name, approve in (("no answer (EOF)", b""), ("a plain yes is not the approval word", b"yes\n")):
            with self.subTest(name):
                code, shown, report = self.enroll_cli("sh", home, approve=approve)
                self.assertEqual(code, 2, report)
                self.assertIsNone(self.registry(home))           # nothing was written
                self.assertIn("sha256:", shown)                  # the identity was disclosed first
                self.assertIn(os.path.realpath("/bin/sh"), shown)
                self.assertIn("not approved", report)
        with self.subTest("the approval word enrolls exactly the disclosed identity"):
            code, shown, report = self.enroll_cli("sh", home)
            self.assertEqual(code, 0, report)
            registry = self.registry(home)
            self.assertIsNotNone(registry)
            entry = registry["runners"]["sh"]
            self.assertEqual(entry["path"], os.path.realpath("/bin/sh"))
            self.assertRegex(entry["sha256"], r"[0-9a-f]{64}\Z")
            self.assertIn(entry["sha256"], shown)                # approved identity == recorded identity
            self.assertGreater(entry["size"], 0)
            self.assertIn(entry["pin"], ("path", "copy"))
            folder = home / ".vibe-to-engineering"
            self.assertEqual(stat.S_IMODE(folder.stat().st_mode), 0o700)
            self.assertEqual(stat.S_IMODE((folder / "runners.json").stat().st_mode), 0o600)

    def test_an_approval_is_never_reused_for_different_bytes(self):
        if getattr(evidence, "enroll_runner", None) is None:
            self.fail("A2 enrollment mechanism is absent from this candidate")
        tools = self.tmp / "swap-tools"
        tools.mkdir()
        self.compile(tools / "node", ("-DLINE=\"first-bytes-7752\"",))
        with self.subTest("the bytes change between disclosure and approval"):
            home = self.fresh_home("swapped approval")
            other = self.tmp / "other-bytes"
            self.compile(other, ("-DLINE=\"other-bytes-7752\"",))

            def swapping_ask(prompt):
                shutil.copyfile(str(other), str(tools / "node"))   # different bytes after the disclosure
                return evidence.APPROVAL

            refused = None
            try:
                self.enroll_api(tools / "node", home, ask=swapping_ask)
            except evidence.Fail as error:
                refused = str(error)
            self.assertIsNotNone(refused, "enrollment approved different bytes than the disclosed ones")
            self.assertIn("never reused", refused)
            self.assertIsNone(self.registry(home))                 # the different bytes were not enrolled
        with self.subTest("the same bytes enroll (the positive control)"):
            home = self.fresh_home("control")
            self.assertTrue(self.enroll_api(tools / "node", home))
            self.assertIsNotNone(self.registry(home))

    # ---------------------------------------------------- the launched bytes are the enrolled bytes

    def test_a_successful_check_launches_bytes_whose_hash_equals_its_enrollment_record(self):
        node = shutil.which("node")
        if not node:
            if os.environ.get("V2E_REQUIRE_NODE"):
                self.fail("NOT VERIFIED: V2E_REQUIRE_NODE is set but no node is on the PATH")
            self.skipTest("NOT VERIFIED: no node on the PATH, so the launched-bytes proof did not run")
        home = self.fresh_home("launched bytes")
        self.assertTrue(self.enroll_api(node, home), "A2 enrollment mechanism is absent from this candidate")
        entry = self.registry(home)["runners"]["node"]
        project = self.project("node hash")
        script = ("const c=require('crypto'),f=require('fs');"
                  "console.log(c.createHash('sha256').update(f.readFileSync(process.execPath)).digest('hex'));"
                  "console.log(process.execPath)")
        code, printed, saved, report, _ = self.run_tool(project, ["node", "-e", script], home,
                                                        with_path=[os.path.dirname(entry["path"])])
        self.assertEqual(code, 0, report)
        lines = saved.rstrip().splitlines()
        self.assertEqual(lines[-2], entry["sha256"])     # the launched bytes hash to the enrollment record
        launched = lines[-1]
        if entry["pin"] == "copy":
            self.assertIn("/%s" % childenv.SCRATCH_PREFIX, launched)   # launched the private copy…
            self.assertTrue(launched.startswith(scratch_base(home)))   # …inside the run's scratch root
        else:
            self.assertEqual(launched, entry["path"])                  # launched at the enrolled path
        self.assertIn("  runner node %s sha256:%s mode:%s" % (entry["path"], entry["sha256"], entry["pin"]),
                      saved)                               # the header attests the enrolled identity launched

    # ---------------------------------------------------- swaps cannot substitute another program

    def test_a_replaced_binary_is_refused_and_names_manual_reenrollment(self):
        tools = self.tmp / "replaced-tools"
        tools.mkdir()
        self.compile(tools / "node", ("-DLINE=\"original-A-ran-7753\"",))
        home = self.fresh_home("replaced")
        self.enroll_api(tools / "node", home)            # None on the pre-A2 candidate: it fails on behavior
        project = self.project("replaced binary")
        marker = project / "substitute-ran-7753"
        self.compile(tools / "node", ("-DLINE=\"substitute-B-ran-7753\"",
                                      "-DMARKER=\"%s\"" % str(marker).replace("\\", "\\\\")))
        before = self.registry(home)
        code, _, saved, report, _ = self.run_tool(project, ["node", "run"], home, with_path=[tools])
        self.assertEqual(code, 2, report)
        self.assertFalse(marker.exists())                # R2-F5, second mechanism: the substitute never ran
        self.assertIsNone(saved)
        self.assertIn("no longer matches", report)
        self.assertIn("re-enroll", report)               # the remedy is manual re-enrollment…
        self.assertIn("--enroll-runner", report)
        self.assertEqual(self.registry(home), before)    # …never an automatic re-enrollment
        enrolled = getattr(evidence, "enroll_runner", None)
        if enrolled is not None:
            with self.subTest("manual re-enrollment is the working remedy"):
                self.assertTrue(self.enroll_api(tools / "node", home))
                code, printed, saved, report, _ = self.run_tool(project, ["node", "run"], home,
                                                                with_path=[tools])
                self.assertEqual(code, 0, report)
                self.assertIn("substitute-B-ran-7753", printed)   # the human approved these bytes

    def test_a_retargeted_symlink_cannot_substitute_another_program(self):
        tools = self.tmp / "link-tools"
        tools.mkdir()
        original = self.tmp / "original"
        original.mkdir()
        self.compile(original / "node", ("-DLINE=\"linked-A-ran-7754\"",))
        os.symlink(str(original / "node"), str(tools / "node"))
        home = self.fresh_home("retargeted")
        self.enroll_api(tools / "node", home)            # enrolled through the link: the resolved identity
        project = self.project("retargeted link")
        marker = project / "substitute-ran-7754"
        substitute = self.tmp / "substitute"
        substitute.mkdir()
        self.compile(substitute / "node", ("-DLINE=\"substitute-C-ran-7754\"",
                                           "-DMARKER=\"%s\"" % str(marker).replace("\\", "\\\\")))
        os.unlink(str(tools / "node"))
        os.symlink(str(substitute / "node"), str(tools / "node"))   # the link now resolves elsewhere
        code, _, saved, report, _ = self.run_tool(project, ["node", "run"], home, with_path=[tools])
        self.assertEqual(code, 2, report)
        self.assertFalse(marker.exists())                # the substitute never ran
        self.assertIsNone(saved)
        self.assertIn("enrolled", report)
        self.assertIn("re-enroll", report)
        with self.subTest("the enrolled identity still validates when the link points back"):
            os.unlink(str(tools / "node"))
            os.symlink(str(original / "node"), str(tools / "node"))
            code, printed, saved, report, _ = self.run_tool(project, ["node", "run"], home, with_path=[tools])
            if getattr(evidence, "enroll_runner", None) is not None:
                self.assertEqual(code, 0, report)
                self.assertIn("linked-A-ran-7754", printed)

    def test_a_swap_between_validation_and_launch_cannot_substitute(self):
        # The state-transition point R2-F5 names: the world changes AFTER the gate validates and BEFORE the
        # launch. pin copy launches the private copy made from the hashed bytes; pin path launches the
        # resolved enrolled path — neither consults the name or the original location again.
        with self.subTest("pin copy: the enrolled binary is replaced after validation"):
            tools = self.tmp / "midrun-copy-tools"
            tools.mkdir()
            self.compile(tools / "node", ("-DLINE=\"enrolled-A-ran-7755\"",))
            home = self.fresh_home("midrun copy")
            self.enroll_api(tools / "node", home)
            project = self.project("midrun copy")
            marker = project / "substitute-ran-7755"

            def swap_copy(tool):
                real = tool.secret_values   # called after identity validation, before the launch

                def swapping(project, environ):
                    self.compile(tools / "node", ("-DLINE=\"substitute-B-ran-7755\"",
                                                  "-DMARKER=\"%s\"" % str(marker).replace("\\", "\\\\")))
                    return real(project, environ)
                tool.secret_values = swapping

            out = project / ".vibe-to-engineering" / "evidence" / "check.txt"
            code, printed, report = self.in_process(
                ["--project", str(project), "--out", str(out), "--with-path", str(tools), "--", "node", "run"],
                home, swap_copy)
            self.assertEqual(code, 0, report)
            self.assertIn("enrolled-A-ran-7755", printed)   # the enrolled bytes launched…
            self.assertNotIn("substitute-B-ran-7755", printed)
            self.assertFalse(marker.exists())               # …never the replacement
        with self.subTest("pin path: the link is retargeted after validation"):
            tools = self.tmp / "midrun-path-tools"
            tools.mkdir()
            os.symlink("/bin/sh", str(tools / "node"))       # resolves to sh: a pin-path enrolled identity
            home = self.fresh_home("midrun path")
            self.enroll_api(tools / "node", home)
            project = self.project("midrun path")
            marker = project / "substitute-ran-7756"

            def swap_path(tool):
                real = tool.secret_values

                def swapping(project, environ):
                    substitute = self.tmp / "midrun-substitute"
                    self.compile(substitute, ("-DLINE=\"substitute-D-ran-7756\"",
                                              "-DMARKER=\"%s\"" % str(marker).replace("\\", "\\\\")))
                    os.unlink(str(tools / "node"))
                    os.symlink(str(substitute), str(tools / "node"))
                    return real(project, environ)
                tool.secret_values = swapping

            out = project / ".vibe-to-engineering" / "evidence" / "check.txt"
            code, printed, report = self.in_process(
                ["--project", str(project), "--out", str(out), "--with-path", str(tools), "--",
                 "node", "-c", "printf path-pin-launched-7756"], home, swap_path)
            self.assertEqual(code, 0, report)
            self.assertIn("path-pin-launched-7756", printed)   # the enrolled sh launched…
            self.assertNotIn("substitute-D-ran-7756", printed)
            self.assertFalse(marker.exists())                  # …never the retargeted program

    # ---------------------------------------------------- malformed and unsupported identities refuse

    def test_a_malformed_registry_refuses_before_the_check_runs(self):
        home = self.fresh_home("malformed")
        folder = home / ".vibe-to-engineering"
        folder.mkdir()
        registry = folder / "runners.json"
        resolved = os.path.realpath("/bin/sh")
        digest = hashlib.sha256(Path(resolved).read_bytes()).hexdigest()
        valid = {"path": resolved, "sha256": digest, "size": os.path.getsize(resolved), "pin": "path"}

        def document(entry):
            return json.dumps({"version": 1, "runners": {"sh": entry}})

        project = self.project("malformed registry")
        for name, text in (
                ("not json at all", "{oops"),
                ("not an object", "[]"),
                ("the wrong version", json.dumps({"version": 2, "runners": {"sh": valid}})),
                ("an entry that is not an object", document("oops")),
                ("a missing hash", document({key: value for key, value in valid.items() if key != "sha256"})),
                ("a bad hash", document(dict(valid, sha256="XYZ"))),
                ("a negative size", document(dict(valid, size=-1))),
                ("an unknown pin mode", document(dict(valid, pin="unknown"))),
                ("a relative path", document(dict(valid, path="bin/sh")))):
            with self.subTest(name):
                registry.write_text(text)
                code, _, saved, report, ran = self.run_tool(project, ["sh", "-c", "printf never-7761"], home)
                self.assertEqual(code, 2, report)
                self.assertFalse(ran)
                self.assertIsNone(saved)
                self.assertIn("malformed", report)
                self.assertIn("--enroll-runner", report)   # the remedy is named, never automatic repair
        with self.subTest("a valid registry without the runner is an unenrolled refusal"):
            registry.write_text(json.dumps({"version": 1, "runners": {}}))
            code, _, saved, report, ran = self.run_tool(project, ["sh", "-c", "printf never-7762"], home)
            self.assertEqual(code, 2, report)
            self.assertFalse(ran)
            self.assertIsNone(saved)
            self.assertIn("not enrolled", report)
        with self.subTest("the same valid entry lets the check run (the positive control)"):
            registry.write_text(document(valid))
            code, printed, saved, report, _ = self.run_tool(project, ["sh", "-c", "printf runs-7763"], home)
            self.assertEqual(code, 0, report)
            self.assertIn("runs-7763", printed)

    def test_a_script_under_a_runners_name_is_never_enrolled(self):
        # the R1 binary gate stands at enrollment: a lookalike script is refused without ever being executed
        tools = self.tmp / "script-tools"
        tools.mkdir()
        script = tools / "node"
        marker = self.tmp / "script-executed-7764"
        script.write_text("#!/bin/sh\n: > '%s'\necho v20.20.2\n" % marker)
        script.chmod(0o755)
        home = self.fresh_home("script")
        code, shown, report = self.enroll_cli("node", home, with_path=[tools])
        self.assertEqual(code, 2, report)
        self.assertIsNone(self.registry(home))
        self.assertFalse(marker.exists())                # never executed — not even to be probed
        self.assertIn("binary", report)

    def test_a_candidate_with_neither_pin_mode_is_refused(self):
        # not in a location the pin-path rule covers (the folder is the user's own), and a private copy of it
        # cannot answer the profile — so it cannot be launched as the enrolled bytes, and enrollment refuses
        tools = self.tmp / "rooted-tools"
        tools.mkdir()
        self.compile(tools / "node", ("-DORIG=\"%s\"" % str(tools).replace("\\", "\\\\"),), source=ROOTED)
        home = self.fresh_home("rooted")
        code, shown, report = self.enroll_cli("node", home, with_path=[tools])
        self.assertEqual(code, 2, report)
        self.assertIsNone(self.registry(home))
        self.assertIn("enrollment is refused", report)


class Emission(unittest.TestCase):
    """R2-F2 and R2-F3 — Class II (confidentiality): every byte the wrapper emits after receiving the inputs —
    saved evidence including its header, the stdout echo, the stderr summary, mask labels, diagnostics and
    parser errors — holds no declared --env value; names and generated text are data. And confidentiality
    holds before admission finishes: the maskable values are collected from every supplied wrapper setting
    first (two-phase admission), so a failure on an early argument never exposes a value supplied later.

    Every test runs the real CLI against an isolated HOME and fails against the pre-slice candidate on the
    leaked or unredacted bytes themselves — run it with
      V2E_EVIDENCE=/path/to/preserved/skills/vibe-to-engineering/scripts/evidence.py \
          python3 -m unittest discover -s tests -p test_final_review_r2.py -v
    """

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="v2e-r2e-")).resolve()
        self.count = 0

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def fresh_home(self, name):
        home = self.tmp / ("home-%s" % re.sub(r"\W+", "-", name))
        home.mkdir()
        return home

    def enroll(self, home):
        """Enroll the real test interpreter when the candidate has enrollment (A2); None when it does not
        (the historical R2 candidate gates by probing, so the run below still demonstrates the behavior)."""
        enroll = getattr(evidence, "enroll_runner", None)
        if enroll is None:
            return None
        with mock.patch.dict(os.environ, {"HOME": str(home)}):
            with open(os.devnull, "w") as quiet:
                enroll(os.path.realpath(sys.executable), ask=lambda prompt: evidence.APPROVAL, out=quiet)
        return True

    def project(self, name, body, files=None):
        self.count += 1
        project = self.tmp / (re.sub(r"\W+", "-", name) + "-%d" % self.count)
        (project / ".vibe-to-engineering" / "evidence").mkdir(parents=True)
        for file, content in (files or {}).items():
            (project / file).write_text(content)
        (project / "check.py").write_text("from pathlib import Path\nPath('check-ran').write_text('ran')\n"
                                          + body)
        return project

    def run_tool(self, project, command, home, env=(), with_path=(), out="check.txt"):
        """A routine run: (exit code, stdout, the evidence text or None, stderr, whether the check ran)."""
        out = project / ".vibe-to-engineering" / "evidence" / out
        settings = [part for setting in env for part in ("--env", setting)]
        settings += [part for folder in with_path for part in ("--with-path", str(folder))]
        done = subprocess.run([sys.executable, str(TOOL), "--project", str(project), "--out", str(out)]
                              + settings + ["--"] + list(command), stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE, env=dict(os.environ, HOME=str(home)))
        return (done.returncode, done.stdout.decode("utf-8", "replace"),
                out.read_text(encoding="utf-8") if out.exists() else None,
                done.stderr.decode("utf-8", "replace"), (project / "check-ran").exists())

    def run_raw(self, home, argv):
        done = subprocess.run([sys.executable, str(TOOL)] + list(argv), stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE, env=dict(os.environ, HOME=str(home)))
        return done.returncode, done.stdout.decode("utf-8", "replace"), done.stderr.decode("utf-8", "replace")

    def registry_bytes(self, home):
        path = home / ".vibe-to-engineering" / "runners.json"
        return path.read_bytes() if path.exists() else None

    # ---------------------------------------------------- R2-F2: no declared value in generated text

    def test_a_declared_value_never_appears_inside_a_mask_label(self):
        # the original R2-F2 counterexample: the second value's mask label spelled the first value out
        home = self.fresh_home("label")
        self.enroll(home)
        project = self.project("mask label", "import os\nprint(os.environ['r2SecretName7719_X'])\n")
        code, printed, saved, report, ran = self.run_tool(
            project, [sys.executable, "-B", "check.py"], home,
            env=["A=r2SecretName7719", "r2SecretName7719_X=other-7719"])
        self.assertEqual(code, 0, report)
        self.assertTrue(ran)
        self.assertIsNotNone(saved)
        self.assertEqual(saved, printed)
        for text in (printed, saved, report):
            self.assertNotIn("r2SecretName7719", text)   # not even inside another value's mask label
            self.assertNotIn("other-7719", text)
        self.assertIn("<masked>", printed)               # the value-free fallback label

    def test_mutual_and_overlapping_name_value_relationships(self):
        home = self.fresh_home("mutual")
        self.enroll(home)
        project = self.project("mutual", "import os\nprint(os.environ['beta7781_A'])\n")
        code, printed, saved, report, ran = self.run_tool(
            project, [sys.executable, "-B", "check.py"], home,
            env=["A7781=beta7781", "beta7781_A=gamma7781", "G7781=beta7781_A"])
        self.assertEqual(code, 0, report)
        self.assertTrue(ran)
        for text in (printed, saved, report):
            for value in ("beta7781", "gamma7781", "beta7781_A"):   # a value that is also a name, one inside
                self.assertNotIn(value, text)                       # a name, one holding another value

    def test_short_numeric_and_single_character_values_in_and_around_labels(self):
        home = self.fresh_home("short")
        self.enroll(home)
        project = self.project("short values", "import os\nprint(os.environ['D7_D'], os.environ['N'])\n")
        code, printed, saved, report, ran = self.run_tool(
            project, [sys.executable, "-B", "check.py"], home,
            env=["D7=7", "D7_D=v7782", "N=1234"])
        self.assertEqual(code, 0, report)
        self.assertTrue(ran)
        self.assertNotIn("<masked D7_D>", printed)       # the old label itself spelled a declared value
        for text in (printed, saved, report):
            self.assertNotIn("v7782", text)
            self.assertNotIn("1234", text)
        body = printed.split("\n\n", 1)[1]               # below the header: no stray digit of the values
        self.assertNotIn("7", body)
        self.assertIn("<masked N>", body)                # a clean name still attributes its mask

    def test_a_value_colliding_with_the_mask_syntax_or_wrapper_words(self):
        for name, value in (("the mask word itself", "masked"), ("the mask marker's opening", "<masked"),
                            ("a wrapper word", "evidence")):
            with self.subTest(name):
                home = self.fresh_home(name)
                self.enroll(home)
                project = self.project(name, "print('say %s aloud-7783')\n" % value)
                code, printed, saved, report, ran = self.run_tool(
                    project, [sys.executable, "-B", "check.py"], home, env=["A=%s" % value])
                self.assertEqual(code, 0, report)
                self.assertTrue(ran)
                for text in (printed, saved, report):
                    self.assertNotIn(value, text)        # not even inside the mask markers or the summary

    def test_the_summary_of_settings_holds_no_declared_value(self):
        home = self.fresh_home("summary")
        self.enroll(home)
        project = self.project("summary", "print('ordinary output-7784')\n",
                               files={".env": "PORT=8000\n"})
        code, printed, saved, report, ran = self.run_tool(
            project, [sys.executable, "-B", "check.py"], home, env=["A7784=PORT"])
        self.assertEqual(code, 0, report)
        self.assertTrue(ran)
        self.assertIn("settings left readable: ", report)   # the summary still reports settings…
        self.assertNotIn("PORT", report)                    # …but a declared value inside a name is masked

    def test_the_leak_is_closed_in_every_argument_order_and_spelling(self):
        for name, env in (("the second value declared first", ["r2SecretName7719_X=other-7719",
                                                               "A=r2SecretName7719"]),
                          ("the --env= spelling", ["A=r2SecretName7719", "r2SecretName7719_X=other-7719"])):
            with self.subTest(name):
                home = self.fresh_home(name)
                self.enroll(home)
                project = self.project(name, "import os\nprint(os.environ['r2SecretName7719_X'])\n")
                if name == "the --env= spelling":
                    out = project / ".vibe-to-engineering" / "evidence" / "check.txt"
                    code, printed, report = self.run_raw(
                        home, ["--project", str(project), "--out", str(out)]
                              + ["--env=%s" % setting for setting in env]
                              + ["--", sys.executable, "-B", "check.py"])
                    saved = out.read_text(encoding="utf-8") if out.exists() else None
                else:
                    code, printed, saved, report, _ = self.run_tool(
                        project, [sys.executable, "-B", "check.py"], home, env=env)
                self.assertEqual(code, 0, report)
                for text in (printed, saved, report):
                    self.assertNotIn("r2SecretName7719", text)
                    self.assertNotIn("other-7719", text)

    # ---------------------------------------------------- R2-F3: confidentiality before admission finishes

    def refused_confidentially(self, name, env, command=None, blame=None):
        """The shared early-refusal contract for this slice: exit 2, the check never ran, no evidence, the
        registry untouched, no traceback — and no declared value in stdout or stderr, however the settings
        embed one in another argument's name."""
        home = self.fresh_home(name)
        self.enroll(home)
        before = self.registry_bytes(home)
        project = self.project(name, "print('never runs-7785')\n")
        code, printed, saved, report, ran = self.run_tool(
            project, command or [sys.executable, "-B", "check.py"], home, env=env)
        self.assertEqual(code, 2, report)
        self.assertFalse(ran)                            # the check never ran
        self.assertIsNone(saved)                         # no check evidence
        self.assertEqual(self.registry_bytes(home), before)   # the real registry was never touched
        self.assertNotIn("Traceback", report)
        if blame is not None:
            self.assertIn(blame, report)
        values = [setting.split("=", 1)[1] for setting in env if "=" in setting]
        for text in (printed, report):
            for value in values:
                if value.strip():
                    self.assertNotIn(value, text)        # no declared value, even inside another name
        return report

    def test_the_original_r2_f3_counterexample(self):
        self.refused_confidentially(
            "duplicate name", ["A=r2SecretName7719", "r2SecretName7719_X=x-7786", "r2SecretName7719_X=y-7786"],
            blame="given twice")

    def test_a_failure_on_an_early_argument_exposes_no_later_value(self):
        # the duplicate is reported before the later --env is ever validated — its value is still redacted
        report = self.refused_confidentially(
            "later value", ["r2SecretName7719_X=x-7787", "r2SecretName7719_X=y-7787", "A=r2SecretName7719"],
            blame="given twice")
        self.assertNotIn("r2SecretName7719", report)

    def test_prohibited_and_held_name_refusals_stay_confidential(self):
        self.refused_confidentially("prohibited name holding a value", ["A7788=GIT_", "GIT_CONFIG=x-7788"])
        self.refused_confidentially("held name holding a value", ["A7789=PA", "PATH=x-7789"])

    def test_malformed_settings_and_argument_orders_stay_confidential(self):
        for name, env in (("a malformed name holding a value", ["A7790=se7790", "se7790 NOT-A-NAME=x-7790"]),
                          ("an unmaskable value after a secret", ["A7791=s7791e", "PAD7791= = ="]),
                          ("the --env= spelling, duplicate", ["A=r2SecretName7719", "r2SecretName7719_X=x-7792",
                                                              "r2SecretName7719_X=y-7792"])):
            with self.subTest(name):
                if name == "the --env= spelling, duplicate":
                    home = self.fresh_home(name)
                    self.enroll(home)
                    project = self.project(name, "print('never runs-7792b')\n")
                    out = project / ".vibe-to-engineering" / "evidence" / "check.txt"
                    code, printed, report = self.run_raw(
                        home, ["--project", str(project), "--out", str(out)]
                              + ["--env=%s" % setting for setting in env]
                              + ["--", sys.executable, "-B", "check.py"])
                    self.assertEqual(code, 2, report)
                    self.assertFalse(out.exists())
                    self.assertNotIn("r2SecretName7719", report + printed)
                    self.assertNotIn("Traceback", report)
                else:
                    self.refused_confidentially(name, env)

    def test_parser_errors_are_redacted_and_never_run_the_check(self):
        home = self.fresh_home("parser")
        self.enroll(home)
        project = self.project("parser", "print('never runs-7793')\n")
        out = project / ".vibe-to-engineering" / "evidence" / "check.txt"
        with self.subTest("an unknown argument echoing a declared value"):
            code, printed, report = self.run_raw(
                home, ["--project", str(project), "--out", str(out),
                       "--env", "A7793=secret7793value", "--bogus-secret7793value",
                       "--", sys.executable, "-B", "check.py"])
            self.assertEqual(code, 2, report)
            self.assertFalse((project / "check-ran").exists())
            self.assertFalse(out.exists())
            self.assertNotIn("secret7793value", report + printed)
            self.assertNotIn("Traceback", report)
        with self.subTest("a missing --out names no declared value"):
            code, printed, report = self.run_raw(
                home, ["--project", str(project), "--env", "A7794=secret7794value",
                       "--", sys.executable, "-B", "check.py"])
            self.assertEqual(code, 2, report)
            self.assertNotIn("secret7794value", report + printed)
        with self.subTest("a missing command and an --env without its setting"):
            code, printed, report = self.run_raw(home, ["--project", str(project), "--out", str(out), "--env"])
            self.assertEqual(code, 2, report)
            self.assertNotIn("Traceback", report)


class RecordedPaths(unittest.TestCase):
    """R2-F4 — Class I (identity): the evidence header records the validated --with-path entries the child
    actually received, retained from construction — never a mutable original argument resolved again after
    the run. A check that retargets or removes its symlink cannot make the header attest to a different
    folder, and cannot make an already-run check look like a pre-launch refusal."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="v2e-r2p-")).resolve()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def enroll(self, home):
        enroll = getattr(evidence, "enroll_runner", None)
        if enroll is None:
            return None
        with mock.patch.dict(os.environ, {"HOME": str(home)}):
            with open(os.devnull, "w") as quiet:
                enroll(os.path.realpath(sys.executable), ask=lambda prompt: evidence.APPROVAL, out=quiet)
        return True

    def run_tool(self, project, command, home, with_path=(), out="check.txt"):
        out = project / ".vibe-to-engineering" / "evidence" / out
        settings = [part for folder in with_path for part in ("--with-path", str(folder))]
        done = subprocess.run([sys.executable, str(TOOL), "--project", str(project), "--out", str(out)]
                              + settings + ["--"] + list(command), stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE, env=dict(os.environ, HOME=str(home)))
        return (done.returncode, done.stdout.decode("utf-8", "replace"),
                out.read_text(encoding="utf-8") if out.exists() else None,
                done.stderr.decode("utf-8", "replace"), (project / "check-ran").exists())

    def link_setup(self, name, body):
        one, two = self.tmp / ("one-%s" % name), self.tmp / ("two-%s" % name)
        one.mkdir()
        two.mkdir()
        link = self.tmp / ("link-%s" % name)
        os.symlink(str(one), str(link))
        home = self.tmp / ("home-%s" % name)
        home.mkdir()
        self.enroll(home)
        project = self.tmp / ("project-%s" % name)
        (project / ".vibe-to-engineering" / "evidence").mkdir(parents=True)
        (project / "check.py").write_text("from pathlib import Path\nPath('check-ran').write_text('ran')\n"
                                          + body)
        return one, two, link, home, project

    def test_the_header_records_the_path_the_child_actually_received(self):
        # the original R2-F4 counterexample: the check retargets its symlink; the old header resolved the
        # flag again after the run and attested to the OTHER folder than the child's PATH held
        one, two, link, home, project = self.link_setup(
            "retargeted", "import os\nprint('CHILD-PATH=' + os.environ['PATH'])\n"
                          "os.unlink(%r)\nos.symlink(%r, %r)\n"
                          % (str(self.tmp / "link-retargeted"), str(self.tmp / "two-retargeted"),
                             str(self.tmp / "link-retargeted")))
        code, printed, saved, report, ran = self.run_tool(project, [sys.executable, "-B", "check.py"], home,
                                                          with_path=[link])
        self.assertEqual(code, 0, report)
        self.assertTrue(ran)
        self.assertIsNotNone(saved)
        self.assertIn("CHILD-PATH=/usr/bin:/bin:/usr/sbin:/sbin:%s\n" % one, saved)   # what the child got
        self.assertIn("  path %s\n" % one, saved)      # the header attests to the same validated entry…
        self.assertNotIn("  path %s" % two, saved)     # …never to the retargeted one

    def test_a_removed_link_keeps_the_run_and_its_evidence(self):
        # removing the link made the old header's re-resolution fail AFTER the check ran — a post-launch
        # refusal (exit 2) that threw the run's evidence away (also R2-F6's second counterexample)
        one, two, link, home, project = self.link_setup(
            "removed", "import os\nprint('CHILD-PATH=' + os.environ['PATH'])\n"
                       "os.unlink(%r)\n" % str(self.tmp / "link-removed"))
        code, printed, saved, report, ran = self.run_tool(project, [sys.executable, "-B", "check.py"], home,
                                                          with_path=[link])
        self.assertEqual(code, 0, report)              # the check ran and its evidence was produced
        self.assertTrue(ran)
        self.assertIsNotNone(saved)                    # no evidence is lost to a late re-resolution
        self.assertIn("  path %s\n" % one, saved)
        self.assertIn("CHILD-PATH=/usr/bin:/bin:/usr/sbin:/sbin:%s\n" % one, saved)


class WrapperStatus(unittest.TestCase):
    """R2-F6 — Class III (status semantics), owner decision 5.3: the wrapper's exit status is its own
    namespace — 0 the check ran and the required evidence was produced, 1 a wrapper operational failure,
    2 a pre-launch refusal (nothing ran, no new check evidence), 3 a post-launch integrity failure (the
    check ran). The child's own result — its exit code, or the signal that ended it — is recorded as data
    and never collides with the wrapper's control meanings: wrapper 0 does NOT say the check passed."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="v2e-r2s-")).resolve()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def enroll(self, home):
        enroll = getattr(evidence, "enroll_runner", None)
        if enroll is None:
            return None
        with mock.patch.dict(os.environ, {"HOME": str(home)}):
            with open(os.devnull, "w") as quiet:
                enroll(os.path.realpath(sys.executable), ask=lambda prompt: evidence.APPROVAL, out=quiet)
        return True

    def run_tool(self, project, command, home, out="check.txt"):
        out = project / ".vibe-to-engineering" / "evidence" / out
        done = subprocess.run([sys.executable, str(TOOL), "--project", str(project), "--out", str(out)]
                              + ["--"] + list(command), stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                              env=dict(os.environ, HOME=str(home)))
        return (done.returncode, done.stdout.decode("utf-8", "replace"),
                out.read_text(encoding="utf-8") if out.exists() else None,
                done.stderr.decode("utf-8", "replace"), (project / "check-ran").exists())

    def project(self, name, body):
        project = self.tmp / re.sub(r"\W+", "-", name)
        (project / ".vibe-to-engineering" / "evidence").mkdir(parents=True)
        (project / "check.py").write_text("from pathlib import Path\nPath('check-ran').write_text('ran')\n"
                                          + body)
        home = self.tmp / ("home-%s" % re.sub(r"\W+", "-", name))
        home.mkdir()
        self.enroll(home)
        return project, home

    def test_the_original_r2_f6_counterexample(self):
        # a supported check calling sys.exit(2) RAN and produced evidence — the old wrapper returned 2,
        # the pre-launch refusal code, for a run that was not a refusal at all
        project, home = self.project("exit two", "import sys\nprint('ran to completion-7795')\nsys.exit(2)\n")
        code, printed, saved, report, ran = self.run_tool(project, [sys.executable, "-B", "check.py"], home)
        self.assertEqual(code, 0, report)              # the check ran and the evidence was produced
        self.assertTrue(ran)
        self.assertIsNotNone(saved)
        self.assertIn("ran to completion-7795", saved)
        self.assertIn("the check exited 2", report)    # the child's own outcome, recorded as data

    def test_a_signaled_check_is_recorded_as_a_signal_never_an_ordinary_exit(self):
        project, home = self.project("signaled", "import os, signal\nprint('before the signal-7796', flush=True)\n"
                                                 "os.kill(os.getpid(), signal.SIGTERM)\n")
        code, printed, saved, report, ran = self.run_tool(project, [sys.executable, "-B", "check.py"], home)
        self.assertEqual(code, 0, report)              # it ran; its output up to the signal is evidence
        self.assertTrue(ran)
        self.assertIsNotNone(saved)
        self.assertIn("before the signal-7796", saved)
        self.assertIn("terminated by signal 15 (SIGTERM)", report)   # never collapsed into 'exit 1'
        self.assertNotIn("exit code -15", report)

    def test_a_failed_check_never_counts_as_passed_because_the_wrapper_is_zero(self):
        # the caller's contract: the wrapper's 0 attests 'ran + evidence'; the RECORDED OUTCOME judges
        for outcome in (1, 2, 3, 7):
            with self.subTest("the check exits %d" % outcome):
                project, home = self.project("exit %d" % outcome,
                                             "import sys\nprint('done-7797')\nsys.exit(%d)\n" % outcome)
                code, printed, saved, report, ran = self.run_tool(project, [sys.executable, "-B", "check.py"],
                                                                  home)
                self.assertEqual(code, 0, report)
                self.assertTrue(ran)
                self.assertIsNotNone(saved)
                self.assertIn("the check exited %d" % outcome, report)   # the failure stays on the record
        with self.subTest("a passing check reads as one"):
            project, home = self.project("exit zero", "print('all good-7798')\n")
            code, printed, saved, report, ran = self.run_tool(project, [sys.executable, "-B", "check.py"],
                                                              home)
            self.assertEqual(code, 0, report)
            self.assertIn("the check exited 0", report)


if __name__ == "__main__":
    unittest.main()
