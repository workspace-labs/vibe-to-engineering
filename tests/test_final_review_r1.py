"""Regression tests for the NEW-5 stage-1 final review's R1 corrective (2026-09-27): eight findings, each with a
test that fails against the reviewed candidate and passes only after the underlying correction — plus the nearby
variants, not only the reviewer's reproductions.

  F1  retention matches the scratch root by identity (device, inode), never by the path alone — a check can
      move its root away or put a foreign folder, link or file in its place, and nothing the run did not make
      is ever touched; A3 takes the last step: nothing is ever deleted at all, the root is retained
  F2  every admitted --env value is masked wherever the check prints it — short, numeric, single-character,
      embedded — and a value of only whitespace and '=' is refused at admission (it could not be masked)
  F3  no diagnostic shows a declared value, even inside another argument (a --with-path folder, the --out path)
  F4  a --with-path folder never holds the PATH separator: one folder enters PATH as exactly one entry
  F5  the supported-runner gate resolves the executable under the launch's own working directory and probes the
      resolved runner against its profile — a file's name alone proves nothing
  F6  an integrity failure after the run (the scratch root not confirmable as retained at its recorded path)
      is exit 3, never exit 2: exit 2 always means nothing ran and no evidence exists
  F7  shell readings the file does not decide are computed from the constructed environment (held, or
      determinably empty); refusal stands only for what stays indeterminate ($1 $# $? $@ $*, the shell's own
      variables, the ones it sets at startup, ~name, ~+ ~-). SUPERSEDED by the v0.1 literal .env boundary (A1,
      2026-09-27): a '$' anywhere in a value refuses before launch, so the F7 cases are now refusal tests —
      against the R1-reviewed candidate they still fail (the candidate computes where the boundary refuses)

Run from the repository root:  python3 -m unittest discover -s tests -p test_final_review_r1.py -v
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

ROOT = Path(__file__).resolve().parents[1]
TOOL = Path(os.environ.get("V2E_EVIDENCE", ROOT / "skills" / "vibe-to-engineering" / "scripts" / "evidence.py"))
sys.path.insert(0, str(TOOL.parent))
import childenv  # noqa: E402
import enrolled  # noqa: E402 — the isolated HOME with the suite's runners enrolled (A2)
from gitrun import Fail  # noqa: E402


def scratch_base():
    """The scratch base the tool under test uses: inside the suite's isolated enrolled HOME — the base is
    per-user now (~/.vibe-to-engineering/runs, A3), never /tmp, which the OS reaps on its own schedule."""
    base = Path(str(enrolled.enrolled_home())) / ".vibe-to-engineering" / "runs"
    base.mkdir(parents=True, exist_ok=True)
    return base


class FinalReviewR1(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="v2e-r1-")).resolve()
        self.count = 0

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def scratch_roots(self):
        return {name for name in os.listdir(str(scratch_base())) if name.startswith(childenv.SCRATCH_PREFIX)}

    def run_tool(self, name, body, env=(), with_path=(), parent=None, files=None, command=None, cwd=None):
        """The tool over a project holding `files` (default: one .env), its check marking that it ran, then running
        `body` — (exit code, what it printed, the evidence text or None, its report, whether the check ran,
        the project). `command` replaces the default python check; `cwd` runs the tool from another folder."""
        self.count += 1
        project = self.tmp / (re.sub(r"\W+", "-", name) + "-%d" % self.count)
        (project / ".vibe-to-engineering").mkdir(parents=True)
        for file, content in (files if files is not None else {".env": "SECRET_KEY=hunter2-not-real\n"}).items():
            path = project / file
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content)
        (project / "check.py").write_text("from pathlib import Path\nPath('check-ran').write_text('ran')\n"
                                          + body + "\n")
        out = project / ".vibe-to-engineering" / "evidence" / "check.txt"
        settings = [part for setting in env for part in ("--env", setting)]
        settings += [part for folder in with_path for part in ("--with-path", folder)]
        done = subprocess.run([sys.executable, str(TOOL), "--project", str(project), "--out", str(out)] + settings
                              + ["--"] + list(command or (sys.executable, "-B", "check.py")),
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=cwd,
                              env=enrolled.environ(dict(os.environ, **(parent or {}))))
        return (done.returncode, done.stdout.decode("utf-8", "replace"),
                out.read_text(encoding="utf-8") if out.exists() else None,
                done.stderr.decode("utf-8", "replace"), (project / "check-ran").exists(), project)

    # ------------------------------------------------------------------ F1 + F6: retention ownership, exit codes

    MOVER = ("import os\nfrom pathlib import Path\nroot = Path(os.environ['HOME']).parent\n"
             "root.rename(Path('moved-scratch'))\n")

    def test_retention_never_touches_a_folder_that_took_the_roots_place(self):
        # the reviewer's reproduction: the check moves its scratch root away and a foreign folder takes the path;
        # the reviewed candidate deleted the foreign folder. Under retention nothing is ever deleted: the foreign
        # folder is left standing at that path, and the run ends in an integrity failure, exit 3
        before = self.scratch_roots()
        code, printed, saved, report, ran, project = self.run_tool(
            "folder in its place", self.MOVER + "Path('foreign').rename(root)\nprint('done-5519')",
            files={".env": "SECRET_KEY=hunter2-not-real\n", "foreign/data.txt": "precious-r1-6601"})
        left = self.scratch_roots() - before                 # whatever stands at the path now
        self.assertEqual(code, 3, report)                    # an integrity failure after the run — never 2
        self.assertTrue(ran)                                 # the check DID run
        self.assertIn("done-5519", printed)
        self.assertIsNotNone(saved)                          # the evidence exists
        self.assertIn("integrity failure", report)
        self.assertIn("check ran", report)
        self.assertEqual(len(left), 1)                       # the stranger at the path, left for the human
        standing = scratch_base() / left.pop()
        self.assertEqual((standing / "data.txt").read_text(), "precious-r1-6601")   # untouched
        shutil.rmtree(str(standing))

    def test_retention_never_follows_a_link_at_the_roots_place(self):
        before = self.scratch_roots()
        code, printed, saved, report, ran, project = self.run_tool(
            "a link in its place", self.MOVER + "root.symlink_to(Path('foreign').resolve(), "
            "target_is_directory=True)\nprint('done-5520')",
            files={".env": "SECRET_KEY=hunter2-not-real\n", "foreign/data.txt": "precious-r1-6602"})
        for name in self.scratch_roots() - before:   # the link itself, left standing, removed by the test
            os.unlink(str(scratch_base() / name))
        self.assertEqual(code, 3, report)
        self.assertTrue(ran)
        self.assertEqual((project / "foreign" / "data.txt").read_text(), "precious-r1-6602")

    def test_retention_reports_a_root_simply_moved_or_removed(self):
        code, printed, saved, report, ran, project = self.run_tool(
            "root moved away", self.MOVER + "print('done-5521')")
        self.assertEqual(code, 3, report)
        self.assertTrue(ran)
        self.assertIsNotNone(saved)
        self.assertTrue((project / "moved-scratch" / "home").is_dir())   # wherever it went is the check's doing
        code, printed, saved, report, ran, project = self.run_tool(
            "root deleted", "import os, shutil\nshutil.rmtree(Path(os.environ['HOME']).parent)\nprint('done-5522')")
        self.assertEqual(code, 3, report)
        self.assertTrue(ran)

    def test_retention_unit_level_identity(self):
        # unit level: the object at a registered path is matched by identity — another folder there is refused
        # and left exactly as found; a root standing as the run made it is confirmed and retained, never deleted
        with mock.patch.dict(os.environ, {"HOME": str(self.tmp)}):   # in-process roots stay in the test dir
            root = childenv.scratch_root()
            moved = self.tmp / "moved"
            os.rename(str(root), str(moved))
            replacement = Path(root)
            replacement.mkdir()
            (replacement / "data.txt").write_text("precious-r1-6603")
            with self.assertRaises(Fail):
                childenv.retain(root)
            self.assertEqual((replacement / "data.txt").read_text(), "precious-r1-6603")
            childenv._ROOTS.pop(str(root), None)   # the test moved it: unregister rather than leave a stale entry
            shutil.rmtree(str(moved))
            shutil.rmtree(str(replacement))        # the test's own stand-in, removed by the test
            root = childenv.scratch_root()         # a root standing as made is confirmed and retained …
            (root / "home" / "kept.txt").write_text("run data-r1-6604")
            self.assertEqual(childenv.retain(root), str(root))
            self.assertTrue(root.exists())         # … never deleted, contents and all
            self.assertEqual((root / "home" / "kept.txt").read_text(), "run data-r1-6604")

    # ------------------------------------------------------------------ F2: every admitted value stays secret

    def test_short_numeric_and_embedded_declared_values_are_masked_wherever_they_appear(self):
        # the reviewer's reproductions: CRED=abc and CRED=48213377 printed embedded reached the evidence raw
        for name, value in (("short", "abc"), ("numeric", "48213377"), ("one character", "q"),
                            ("a short word", "s3c")):
            with self.subTest(name):
                code, printed, saved, report, ran, _ = self.run_tool(
                    name, "import os; print('prefix' + os.environ['CRED'] + 'suffix')", env=["CRED=" + value])
                self.assertEqual(code, 0, report)
                self.assertTrue(ran)
                self.assertIn("prefix<masked CRED>suffix", printed)
                self.assertIn("prefix<masked CRED>suffix", saved)   # the evidence file holds the mask too
                if len(value) > 2:   # a one- or two-character value could sit inside a path; the mask is the proof
                    for text in (printed, saved, report):
                        self.assertNotIn(value, text)

    def test_a_declared_value_of_only_whitespace_or_equals_is_refused_at_admission(self):
        for name, setting in (("equals", "PAD==="), ("spaces", "PAD=  "), ("mixed", "PAD= \t=\t"),
                              ("tab", "PAD=\t")):
            with self.subTest(name):
                code, printed, saved, report, ran, _ = self.run_tool(name, "print('never')", env=[setting])
                self.assertEqual(code, 2, report)
                self.assertFalse(ran)
                self.assertIsNone(saved)
                self.assertIn("PAD", report)                 # the name …
                self.assertNotIn(" \t", report.split("PAD", 1)[-1])   # … never the value

    def test_an_empty_declared_value_is_admitted_and_masks_nothing(self):
        code, printed, saved, report, ran, _ = self.run_tool(
            "empty value", "import os; print('EMPTY' in os.environ, repr(os.environ['EMPTY']))", env=["EMPTY="])
        self.assertEqual(code, 0, report)
        self.assertTrue(ran)
        self.assertIn("True ''", printed)

    # ------------------------------------------------------------------ F3: no diagnostic shows a declared value

    def test_no_diagnostic_shows_a_declared_value_even_inside_another_argument(self):
        # the reviewer's reproduction: a --with-path refusal echoed the folder, declared value inside it and all
        secret = "s3cr3t-d1r-9922"
        cases = ({"with_path": ["/tmp/%s/nope" % secret]},              # not an existing directory
                 {"with_path": ["relative-%s" % secret]},               # not absolute
                 {"with_path": ["/tmp/%s" % secret + ":" + secret]},)   # the PATH separator, value inside
        for flags in cases:
            with self.subTest(flags=flags):
                code, printed, saved, report, ran, _ = self.run_tool(
                    "redacted %s" % sorted(flags), "print('never')", env=["TOKEN=%s" % secret], **flags)
                self.assertEqual(code, 2, report)
                self.assertFalse(ran)
                self.assertIsNone(saved)
                self.assertNotIn(secret, report)
                self.assertNotIn(secret, printed)

    # ------------------------------------------------------------------ F4: one --with-path folder, one entry

    def test_with_path_never_enters_path_as_more_than_one_entry(self):
        # the reviewer's reproduction: a real directory whose name holds ':' entered PATH as two entries, the
        # second never validated
        joined = self.tmp / ("a:%s" % (self.tmp / "tools"))
        joined.mkdir(parents=True)
        (self.tmp / "tools").mkdir(exist_ok=True)
        code, _, saved, report, ran, _ = self.run_tool("a colon in the name", "print('never')",
                                                       with_path=[str(joined)])
        self.assertEqual(code, 2, report)
        self.assertFalse(ran)
        self.assertIsNone(saved)
        link = self.tmp / "a-link"
        os.symlink(str(joined), str(link))       # resolving to such a name is refused too
        code, _, saved, report, ran, _ = self.run_tool("a link to one", "print('never')", with_path=[str(link)])
        self.assertEqual(code, 2, report)
        self.assertFalse(ran)
        tools = self.tmp / "plain tools"         # an ordinary folder still lands as exactly one entry
        tools.mkdir()
        code, printed, saved, report, ran, _ = self.run_tool(
            "an ordinary folder", "import os; print(os.environ['PATH'])", with_path=[str(tools)])
        self.assertEqual(code, 0, report)
        self.assertIn("/usr/bin:/bin:/usr/sbin:/sbin:%s\n" % os.path.realpath(str(tools)), printed)

    # ------------------------------------------------------------------ F5: the gate validates what will launch
    # (A2, 2026-09-28: the mechanism these tests first pinned down moved — a routine run no longer probes the
    # resolved runner at all, because per-run probing itself executed untrusted candidates (R2-F5). Validation
    # is now enrollment identity plus the enrolled SHA-256, and the profile check stands at enrollment only.
    # The invariants below are unchanged: a lookalike is refused before anything runs, never executed even to
    # validate it; the version bounds are enforced; the launch's own working directory governs resolution.)

    def fake(self, folder, name, body):
        tool = folder / name
        tool.write_text("#!/bin/sh\n" + body + "\n")
        tool.chmod(0o755)
        return tool

    def test_a_lookalike_runner_is_refused_before_anything_runs(self):
        # the reviewer's reproduction: a shell script named 'node' in a --with-path folder passed the gate on its
        # name and ran. Now an unenrolled identity is refused before anything runs — nothing executes it, not
        # even to validate it — and a script under a runner's name can never become enrolled (the binary gate
        # stands at enrollment, proven in tests/test_final_review_r2.py). (Only a runner absent from the system
        # folders can be impersonated this way: --with-path folders come after them, so a lookalike 'sh' or
        # 'python3' never shadows the real one — that ordering stands.)
        folder = self.tmp / "tools"
        folder.mkdir()
        self.fake(folder, "node", ": > probe-mark\necho synthetic-not-node")
        code, printed, saved, report, ran, project = self.run_tool(
            "fake node", "", command=["node", "--version"], with_path=[str(folder)])
        self.assertEqual(code, 2, report)
        self.assertIsNone(saved)
        self.assertFalse((project / "probe-mark").exists())   # never executed — not even to validate it
        self.assertIn("enrolled", report)
        with self.subTest("a perfect version answer under another name is still refused by name"):
            self.fake(folder, "node2", "echo v20.20.2")
            code, _, saved, report, _, _ = self.run_tool("misnamed", "", command=["node2", "--version"],
                                                         with_path=[str(folder)])
            self.assertEqual(code, 2, report)
            self.assertIsNone(saved)
        with self.subTest("an enrolled real runner still runs"):
            code, printed, saved, report, ran, _ = self.run_tool("a real shell", "", command=["sh", "-c",
                                                                                              "printf ok-6630"])
            self.assertEqual(code, 0, report)
            self.assertIn("ok-6630", printed)

    def test_a_binary_outside_the_supported_profile_or_version_bounds_is_never_enrolled(self):
        # R1 pinned the profile check on the per-run probe: a compiled lookalike passed the binary check, so the
        # probe ran it and its answer had to match. A2 removes the per-run probe (it executed untrusted
        # candidates — R2-F5); the check now stands at enrollment: a candidate answering outside the registry's
        # version bounds, or answering garbage, is refused and never enters the registry, and the one disclosed
        # probe runs only with the human's approval, from inside a scratch root, never the project.
        cc = shutil.which("cc")
        if not cc:
            self.skipTest("no C compiler to build a binary lookalike")
        folder = self.tmp / "tools"
        folder.mkdir()
        home = self.tmp / "home"
        home.mkdir()
        registry = home / ".vibe-to-engineering" / "runners.json"
        source = self.tmp / "fake.c"
        source.write_text('#include <stdio.h>\nint main(void) {\n'
                          '    FILE *mark = fopen("binary-probe-ran-6631", "w");\n'
                          '    if (mark) { fputs("ran", mark); fclose(mark); }\n'
                          '    printf("%s\\n", ANSWER);\n    return 0;\n}\n')
        for name, answer, message in (("too new", "v27.0.0", "bounds"), ("garbage", "synthetic", "profile")):
            with self.subTest(name):
                subprocess.run([cc, "-DANSWER=\"%s\"" % answer, str(source), "-o", str(folder / "node")],
                               check=True)
                done = subprocess.run([sys.executable, str(TOOL), "--enroll-runner", "node",
                                       "--with-path", str(folder)], input=b"enroll\n",
                                      stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                      env=dict(os.environ, HOME=str(home)))
                report = done.stderr.decode("utf-8", "replace")
                self.assertEqual(done.returncode, 2, report)
                self.assertIn(message, report)
                self.assertFalse(registry.exists())      # never entered the registry
        with self.subTest("a candidate answering its profile can be enrolled"):
            subprocess.run([cc, "-DANSWER=\"v20.20.2\"", str(source), "-o", str(folder / "node")], check=True)
            done = subprocess.run([sys.executable, str(TOOL), "--enroll-runner", "node",
                                   "--with-path", str(folder)], input=b"enroll\n",
                                  stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                  env=dict(os.environ, HOME=str(home)))
            report = done.stderr.decode("utf-8", "replace")
            self.assertEqual(done.returncode, 0, report)
            self.assertTrue(registry.exists())

    def test_the_gate_judges_the_executable_under_the_launchs_own_working_directory(self):
        # the reviewer's reproduction: run from a folder holding a link to the real python3, with the project
        # holding a lookalike ./python3 — the reviewed candidate validated the link and launched the lookalike
        elsewhere = self.tmp / "elsewhere"
        elsewhere.mkdir()
        os.symlink(sys.executable, str(elsewhere / "python3"))   # a real python3 by that name where the TOOL runs
        project = self.tmp / "relative-runner-project"
        (project / ".vibe-to-engineering" / "evidence").mkdir(parents=True)
        (project / ".env").write_text("SECRET_KEY=hunter2-not-real\n")
        (project / "check.py").write_text("from pathlib import Path\nPath('check-ran').write_text('ran')\n")
        fake = project / "python3"                               # the lookalike the launch would actually run
        fake.write_text("#!/bin/sh\n: > project-fake-ran-6621\necho synthetic\n")
        fake.chmod(0o755)
        out = project / ".vibe-to-engineering" / "evidence" / "check.txt"
        done = subprocess.run([sys.executable, str(TOOL), "--project", str(project), "--out", str(out),
                               "--", "./python3", "-B", "check.py"], stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                              cwd=str(elsewhere), env=enrolled.environ())
        report = done.stderr.decode("utf-8", "replace")
        self.assertEqual(done.returncode, 2, report)       # judged under the project: the lookalike, refused
        self.assertFalse(out.exists())
        self.assertFalse((project / "project-fake-ran-6621").exists())
        self.assertFalse((project / "check-ran").exists())

    # ------------------------------------------------------------------ F6: exit 2 means nothing ran

    def test_a_pre_launch_refusal_still_means_nothing_ran(self):
        before = self.scratch_roots()
        for name, flags in (("a prohibited name", {"env": ["GIT_DIR=/x-6623"]}),
                            ("an unreadable secret file", {"files": {".env": "SECRET='never closed\n"}}),
                            ("an unsupported runner", {"command": ["foreign-6623"]})):
            with self.subTest(name):
                code, printed, saved, report, ran, _ = self.run_tool(name, "print('never')", **flags)
                self.assertEqual(code, 2, report)
                self.assertFalse(ran)
                self.assertIsNone(saved)
        left = self.scratch_roots() - before   # A3: a refusal PAST construction retains its root, never
        self.assertEqual(len(left), 2)         # deletes it — the unreadable secret file and the unsupported
        for name in left:                      # runner cases; the prohibited name stops before a root exists
            self.assertTrue((scratch_base() / name).is_dir())

    # --------------- F7: shell readings over the known mapping — superseded by the A1 literal boundary (refusal)

    def test_a_shell_reading_the_file_does_not_decide_is_refused_by_the_boundary(self):
        # SUPERSEDED (A1 literal boundary, 2026-09-27): this was
        # test_a_shell_reading_the_file_does_not_decide_is_computed_from_the_constructed_environment — the
        # R1-F7 mechanism, where DB_PASSWORD=$FEED was computed from the constructed mapping (a declared value
        # winning, masked; undeclared determinably empty). The boundary refuses any '$' in a value before
        # launch, so there is no reading to compute: both the declared and the undeclared case stop the run,
        # and the declared value appears nowhere
        sourced = ("import subprocess; print(subprocess.run(['/bin/sh', '-c', '. ./.env; printf \"%s\" "
                   "\"$DB_PASSWORD\"'], stdout=subprocess.PIPE).stdout.decode(), end='')")
        for name, kw in (("declared feed", {"env": ["FEED=declared-feed-9924"],
                                            "files": {".env": "DB_PASSWORD=$FEED\n"}}),
                         ("nothing holds it", {"files": {".env": "DB_PASSWORD=${FEED:-}\n"}})):
            with self.subTest(name):
                code, printed, saved, report, ran, _ = self.run_tool(name, sourced, **kw)
                self.assertEqual(code, 2, report)
                self.assertFalse(ran)
                self.assertIsNone(saved)
                self.assertNotIn("declared-feed-9924", printed + report)

    def test_genuinely_indeterminate_readings_still_refuse(self):
        if not os.path.exists("/bin/sh"):
            self.skipTest("a shell's reading needs a POSIX shell (not Windows)")
        sourced = ("import subprocess; print(subprocess.run(['/bin/sh', '-c', '. ./.env; printf \"%s\" "
                   "\"$DB_PASSWORD\"'], stdout=subprocess.PIPE).stdout.decode(), end='')")
        for name, source in (("the shell works out", "DB_PASSWORD=$RANDOM\n"),
                             ("the shell sets at startup", "DB_PASSWORD=$PWD\n"),
                             ("another startup one", "DB_PASSWORD=$HOSTNAME\n"),
                             ("a positional parameter", "DB_PASSWORD=$1\n"),
                             ("the user database decides", "DB_PASSWORD=~root/x-6625\n")):
            with self.subTest(name):
                code, printed, saved, report, ran, _ = self.run_tool(name, sourced, files={".env": source})
                self.assertEqual(code, 2, report)
                self.assertFalse(ran)
                self.assertIsNone(saved)

    def test_the_reader_alone_without_the_mapping_still_refuses(self):
        # unit level: a reference the file does not decide refuses with or without the constructed mapping.
        # SUPERSEDED in part (A1 literal boundary, 2026-09-27): the second half used to compute the reading
        # from the mapping; the boundary refuses any '$' in a value, so `environ` is no longer consulted at
        # all — both calls refuse now
        sys.path.insert(0, str(TOOL.parent))
        import secretformats
        text = "DB_PASSWORD=$FEED\n"
        with self.assertRaises(Exception):
            secretformats.dotenv_values(text, ".env", text)
        with self.assertRaises(Exception):
            secretformats.dotenv_values(text, ".env", text, {"FEED": "known-6626"})


if __name__ == "__main__":
    unittest.main()
