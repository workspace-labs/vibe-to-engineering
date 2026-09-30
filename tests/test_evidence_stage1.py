"""Tests for the NEW-5 stage-1 launch path of scripts/evidence.py: a check runs with the constructed
environment childenv builds — nothing of the parent's environment is inherited; the one constructed mapping
governs the secret-value analysis and the launch alike; the evidence header records declared --env names
(never their values) and each --with-path folder; and the run's scratch root is retained when the run ends,
however the run ends (A3 — nothing is ever deleted). Slice 3 adds the precedence semantics over that mapping: a reading a declared value
wins is masked as the winner, never refused; a recognized .env.vault is always refused. (The third piece — npm
dotenv v0.4–1.2's $NAME interpolation computed from the known inputs — is superseded by the v0.1 literal .env
boundary, A1: interpolation refuses before launch; see the supersession comment on the last test.)

Run from the repository root:  python3 -m unittest discover -s tests -p test_evidence_stage1.py -v
"""

import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = Path(os.environ.get("V2E_EVIDENCE", ROOT / "skills" / "vibe-to-engineering" / "scripts" / "evidence.py"))
sys.path.insert(0, str(ROOT / "skills" / "vibe-to-engineering" / "scripts"))
import childenv  # noqa: E402
import enrolled  # noqa: E402 — the isolated HOME with the suite's runners enrolled (A2)


def scratch_base():
    """The scratch base the tool under test uses: inside the suite's isolated enrolled HOME — the base is
    per-user now (~/.vibe-to-engineering/runs, A3), never /tmp, which the OS reaps on its own schedule."""
    base = Path(str(enrolled.enrolled_home())) / ".vibe-to-engineering" / "runs"
    base.mkdir(parents=True, exist_ok=True)
    return base
SYNTHESIZED = ["HOME", "LANG", "LC_ALL", "PATH", "TMPDIR", "TZ"] + sorted(childenv.PINNED)


class Stage1(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="v2e-stage1-")).resolve()
        self.count = 0

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def scratch_roots(self):
        return {name for name in os.listdir(str(scratch_base())) if name.startswith(childenv.SCRATCH_PREFIX)}

    def run_tool(self, name, body, env=(), with_path=(), parent=None, files=()):
        """The tool run the way an agent runs it, over a project holding `files` (default: one .env), its check
        marking that it ran, then running `body`. `parent`: names added to the environment the tool itself runs
        in — which a check must never inherit."""
        self.count += 1
        project = self.tmp / (re.sub(r"\W+", "-", name) + "-%d" % self.count)
        (project / ".vibe-to-engineering").mkdir(parents=True)
        for file, content in (files if files else {".env": "SECRET_KEY=hunter2-not-real\n"}).items():
            (project / file).write_text(content)
        (project / "check.py").write_text("from pathlib import Path\nPath('check-ran').write_text('ran')\n"
                                          + body + "\n")
        out = project / ".vibe-to-engineering" / "evidence" / "check.txt"
        settings = [part for setting in env for part in ("--env", setting)]
        settings += [part for folder in with_path for part in ("--with-path", folder)]
        done = subprocess.run([sys.executable, str(TOOL), "--project", str(project), "--out", str(out)] + settings
                              + ["--", sys.executable, "-B", "check.py"], stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE,
                              env=enrolled.environ(dict(os.environ, **(parent or {}))))
        return (done.returncode, done.stdout.decode("utf-8", "replace"),
                out.read_text(encoding="utf-8") if out.exists() else None,
                done.stderr.decode("utf-8", "replace"), (project / "check-ran").exists())

    def test_a_check_inherits_nothing_but_the_constructed_environment(self):
        parent = {"STAGE1_MARKER": "parent-secret-7731", "BASH_FUNC_evil%%": "() { echo pwned; }",
                  "http_proxy": "http://127.0.0.1:9", "TMPDIR": str(self.tmp)}
        # (the parent's HOME lever is gone with A2: the wrapper legitimately reads its own per-user runner
        # registry from HOME — run_tool points it at the isolated enrolled home; the child's HOME independence
        # is proven by the full-environment print below, and TMPDIR stays hostile)
        code, printed, saved, report, ran = self.run_tool(
            "constructed environment", "import os; print(sorted(os.environ)); print(os.environ['PATH']); "
            "print(os.environ['HOME']); print(os.environ['TMPDIR'])", parent=parent)
        self.assertEqual(code, 0, report)
        self.assertTrue(ran)
        names = re.search(r"\[('[^]]*')\]", printed).group(0)
        self.assertEqual(sorted(re.findall(r"'(\w+)'", names)), SYNTHESIZED)
        self.assertIn("/usr/bin:/bin:/usr/sbin:/sbin\n", printed)
        home = re.search(r"^\S*home$", printed, re.M).group(0)
        tmpdir = re.search(r"^\S*tmp$", printed, re.M).group(0)
        self.assertEqual(home, os.path.join(os.path.dirname(tmpdir.rstrip("tmp")), "home"))
        self.assertTrue(tmpdir.startswith(os.path.join(str(scratch_base()), childenv.SCRATCH_PREFIX)))
        for text in (printed, saved, report):
            self.assertNotIn("parent-secret-7731", text)
            self.assertNotIn("STAGE1_MARKER", text)
            self.assertNotIn("BASH_FUNC", text)
            self.assertNotIn("http_proxy", text)

    def test_declared_names_are_added_and_the_header_records_names_only(self):
        code, printed, saved, report, ran = self.run_tool(
            "declared names", "import os; print('DB_PATH' in os.environ)", env=["DB_PATH=/throwaway-5521.db"])
        self.assertEqual(code, 0, report)
        self.assertTrue(ran)
        self.assertIn("True", printed)                       # the declared name reached the check
        self.assertIn("  with DB_PATH\n", printed)           # the header records the name …
        for text in (printed, saved, report):
            self.assertNotIn("/throwaway-5521.db", text)     # … never the value (D4 rule 4)

    def test_a_refused_env_setting_or_with_path_runs_nothing_and_leaves_nothing(self):
        before = self.scratch_roots()
        cases = ({"env": ["BASH_ENV=/x-5561"]}, {"env": ["PATH=/x-5561"]}, {"env": ["A=1", "A=2"]},
                 {"env": ["NOT A NAME=v-5561"]}, {"with_path": ["relative/dir"]},
                 {"with_path": [str(self.tmp / "missing")]})
        for flags in cases:
            with self.subTest(flags=flags):
                code, printed, saved, report, ran = self.run_tool("refused %s" % sorted(flags), "print('ran')",
                                                                  **flags)
                self.assertEqual(code, 2, report)
                self.assertFalse(ran)
                self.assertIsNone(saved)
                self.assertNotIn("-5561", report)            # a refusal never shows the value — every
                # canary above carries "-5561"; the non-hex '-' can never be spelled by a random hex
                # root name or a mktemp suffix in the report's paths (L3)
        self.assertEqual(self.scratch_roots(), before)       # a refusal before construction leaves nothing

    def test_with_path_adds_a_real_folder_and_is_recorded_in_the_header(self):
        tools = self.tmp / "extra tools"
        tools.mkdir()
        code, printed, saved, report, ran = self.run_tool(
            "with path", "import os; print(os.environ['PATH'])", with_path=[str(tools)])
        self.assertEqual(code, 0, report)
        self.assertIn("/usr/bin:/bin:/usr/sbin:/sbin:%s\n" % tools, printed)
        self.assertIn("  path %s\n" % tools, printed)        # D2: recorded in the evidence header
        self.assertEqual(saved, printed)

    def test_the_scratch_root_is_retained_when_the_run_ends_however_it_ends(self):
        before = self.scratch_roots()
        code, _, saved, report, ran = self.run_tool("a successful run", "print('ok')")
        self.assertEqual(code, 0, report)
        self.assertTrue(ran)
        self.assertIn("scratch root is retained at", report)         # A3: reported on stderr, never deleted
        self.assertIn("\n  scratch ", saved)                         # and recorded in the evidence header
        self.assertIn("may hold sensitive output", saved)
        code, _, saved, report, ran = self.run_tool(   # a refusal after construction (an unreadable secret file)
            "a refused run", "print('never')", files={".env": "SECRET='never closed\n"})
        self.assertEqual(code, 2, report)
        self.assertFalse(ran)
        self.assertIsNone(saved)
        left = self.scratch_roots() - before
        self.assertEqual(len(left), 2)                 # both runs' roots retained, however each run ended
        for name in left:
            root = scratch_base() / name
            self.assertTrue((root / "home").is_dir() and (root / "tmp").is_dir())   # the scratch files survive
            self.assertEqual(stat.S_IMODE(root.stat().st_mode), 0o700)

    def test_the_analysis_runs_over_the_constructed_mapping(self):
        # a secret file that sets HOME collides with a name the constructed environment always holds — slice 3:
        # the collision is determinable from the one mapping, so the run proceeds and the file's reading is
        # masked; refusal is for readings that cannot be derived from the approved inputs (D4 rule 5)
        code, printed, saved, report, ran = self.run_tool(
            "analysis over the mapping", "print(open('.env').read().split('=', 1)[1].strip())",
            files={".env": "HOME=/elsewhere-9981\n"})
        self.assertEqual(code, 0, report)
        self.assertTrue(ran)
        for text in (printed, saved, report):
            self.assertNotIn("elsewhere-9981", text)

    def test_a_declared_value_that_wins_a_reading_is_masked_as_the_winner(self):
        # D4 rules 4–5: the admitted --env names join the precedence analysis — python-dotenv's load_dotenv() and
        # Node's loaders keep the environment's value over the file's, so the declared value wins determinably:
        # masked as the winner, never refused, never shown; the file's own value is masked too
        code, printed, saved, report, ran = self.run_tool(
            "declared winner", "import os; print('uses', os.environ['DB_PASSWORD'])",
            env=["DB_PASSWORD=declared-winner-4471"], files={".env": "DB_PASSWORD=file-secret-9917\n"})
        self.assertEqual(code, 0, report)
        self.assertTrue(ran)
        self.assertIn("uses <masked DB_PASSWORD>", printed)
        for text in (printed, saved, report):
            self.assertNotIn("declared-winner-4471", text)
            self.assertNotIn("file-secret-9917", text)

    def test_a_vault_file_is_always_refused(self):
        # the Codex-required reader obligation (§6): a recognized .env.vault is never read — its values are
        # encrypted, and the key that would read them (DOTENV_KEY) may never enter a check's environment, so the
        # plaintext is never determinable; the run stops before the check, naming the file, never its text
        code, printed, saved, report, ran = self.run_tool(
            "a vault file", "print('never')",
            files={".env.vault": '{"vault": "ciphertext-7713"}', ".env": "SECRET_KEY=hunter2-not-real\n"})
        self.assertEqual(code, 2, report)
        self.assertFalse(ran)
        self.assertIsNone(saved)
        self.assertIn(".env.vault", report)
        self.assertNotIn("ciphertext-7713", printed + report)

    def test_old_npm_dotenv_interpolation_is_refused_by_the_boundary(self):
        # SUPERSEDED (A1 literal boundary, 2026-09-27): this was
        # test_old_npm_dotenv_interpolation_is_computed_from_known_inputs — npm dotenv v0.4–1.2's $NAME
        # interpolation computed from the known constructed inputs, unit-level against the ported model and end
        # to end with a declared winner. The boundary refuses interpolation outright: a '$' anywhere in a value —
        # single quotes included, where dotenv 0.3–1.2 interpolate (reader-compat matrix rows 19–21) — stops the
        # run before the check, so the model is no longer wired into the .env reader and these cases are refusal
        # proofs (the declared value never appears in a refusal either)
        for source in ("DB_PASSWORD='$SECRET'\n", "DB_PASSWORD=$SECRET\n", 'DB_PASSWORD="$SECRET"\n'):
            with self.subTest(source=source.strip()):
                code, printed, saved, report, ran = self.run_tool(
                    "interpolation refused", "print('never')", env=["SECRET=declared-5517"],
                    files={".env": source})
                self.assertEqual(code, 2, report)
                self.assertFalse(ran)
                self.assertIsNone(saved)
                self.assertIn(".env", report)
                self.assertNotIn("declared-5517", printed + report)


if __name__ == "__main__":
    unittest.main()
