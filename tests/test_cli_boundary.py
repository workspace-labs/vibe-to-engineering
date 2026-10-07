"""Malformed CLI inputs fail plainly before unsafe work (final check, 2026-10-07)."""

import os
import subprocess
import sys
from pathlib import Path

from support import Fixture, ROOT, STATE, TOOL, identities, write


RENDERER = Path(os.environ.get("V2E_RENDER_PDF", ROOT / "skills" / "vibe-to-engineering" /
                              "scripts" / "render_pdf.py"))


class CliBoundaries(Fixture):
    def setUp(self):
        super().setUp()
        temporary = self.tmp / "temp"
        temporary.mkdir()
        self.env.update({"TMPDIR": str(temporary), "PYTHONDONTWRITEBYTECODE": "1"})

    def run_script(self, script, *args, env=None):
        return subprocess.run([sys.executable, "-I", "-B", str(script), *map(str, args)],
                              cwd=str(self.tmp), env=dict(self.env, **(env or {})),
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=15)

    def assert_plain_error(self, done, tool):
        shown = (done.stdout + done.stderr).decode("utf-8", "replace")
        self.assertEqual(done.returncode, 1, shown)
        self.assertIn(tool + ": error:", shown)
        self.assertNotIn("Traceback (most recent call last)", shown)

    def project(self, name="project"):
        project = self.tmp / name
        write(project / "app.py", b'print("synthetic fixture")\n')
        return project

    def unknown_home(self):
        return "~v2e-no-such-user-" + self.tmp.name + "/project"

    def test_checkpoint_unknown_home_is_a_plain_error_with_no_state(self):
        before = identities(self.tmp)
        done = self.run_script(TOOL, "--project", self.unknown_home(), "tree", "--current")
        self.assert_plain_error(done, "checkpoint.py")
        self.assertEqual(identities(self.tmp), before)

    def test_checkpoint_symlink_loop_is_a_plain_error_and_is_not_changed(self):
        loop = self.tmp / "loop"
        loop.symlink_to("loop")
        before = identities(self.tmp)
        done = self.run_script(TOOL, "--project", loop, "tree", "--current")
        self.assert_plain_error(done, "checkpoint.py")
        self.assertEqual(os.readlink(loop), "loop")
        self.assertEqual(identities(self.tmp), before)

    def test_newline_checkpoint_labels_are_refused_before_any_project_write(self):
        for number, label in enumerate(("baseline\n", "a" * 64 + "\n", "baseline\r\n")):
            with self.subTest(label=repr(label)):
                project = self.project("project-" + str(number))
                before = identities(project)
                done = self.run_script(TOOL, "--project", project, "create", label)
                self.assert_plain_error(done, "checkpoint.py")
                self.assertIn(b"invalid label", done.stderr)
                self.assertEqual(identities(project), before)
                self.assertFalse((project / STATE).exists())

    def test_a_valid_maximum_length_label_still_creates_and_verifies(self):
        project = self.project()
        label = "a" * 64
        made = self.run_script(TOOL, "--project", project, "create", label)
        self.assertEqual(made.returncode, 0, made.stderr.decode())
        verified = self.run_script(TOOL, "--project", project, "verify", label)
        self.assertEqual(verified.returncode, 0, verified.stderr.decode())
        self.assertIn(b"byte for byte", verified.stdout)

    def test_renderer_unknown_home_is_a_plain_error_and_keeps_existing_pdf(self):
        pdf = self.tmp / "plan.pdf"
        pdf.write_bytes(b"%PDF-synthetic-existing")
        before = pdf.stat()
        done = self.run_script(RENDERER, self.unknown_home() + ".html", pdf)
        self.assert_plain_error(done, "render_pdf.py")
        self.assertEqual(pdf.read_bytes(), b"%PDF-synthetic-existing")
        self.assertEqual((pdf.stat().st_ino, pdf.stat().st_mtime_ns),
                         (before.st_ino, before.st_mtime_ns))

    def test_renderer_invalid_utf8_is_a_plain_error_and_keeps_existing_pdf(self):
        html, pdf = self.tmp / "plan.html", self.tmp / "plan.pdf"
        html.write_bytes(b"<!DOCTYPE html>\n<html>\xff</html>\n")
        pdf.write_bytes(b"%PDF-synthetic-existing")
        before = pdf.stat()
        done = self.run_script(RENDERER, html, pdf)
        self.assert_plain_error(done, "render_pdf.py")
        self.assertEqual(pdf.read_bytes(), b"%PDF-synthetic-existing")
        self.assertEqual((pdf.stat().st_ino, pdf.stat().st_mtime_ns),
                         (before.st_ino, before.st_mtime_ns))

    def assert_renderer_same_file_refused(self, html, pdf):
        marker, browser = self.tmp / "browser-launched", self.tmp / "browser"
        browser.write_text('#!/bin/sh\nprintf "%s" launched > "$V2E_BROWSER_MARKER"\n'
                           'for arg in "$@"; do case "$arg" in --print-to-pdf=*) '
                           'printf "%s" "%PDF-1.4 synthetic" > "${arg#--print-to-pdf=}";; esac; done\n')
        browser.chmod(0o755)
        before = identities(self.tmp)
        done = self.run_script(RENDERER, html, pdf,
                               env={"V2E_BROWSER": str(browser), "V2E_BROWSER_MARKER": str(marker)})
        shown = (done.stdout + done.stderr).decode("utf-8", "replace")
        self.assertEqual(done.returncode, 2, shown)
        self.assertIn("plan and PDF must be different files", shown)
        self.assertNotIn("Traceback (most recent call last)", shown)
        self.assertEqual(identities(self.tmp), before)
        self.assertFalse(marker.exists(), "the browser launched before the same-file refusal")

    def test_renderer_refuses_identical_and_normalized_input_output_paths(self):
        for name in ("same", "normalized"):
            with self.subTest(path=name):
                html = self.tmp / name / "plan.html"
                write(html, b'<!DOCTYPE html>\n<html><body>Synthetic plan</body></html>\n')
                pdf = html if name == "same" else str(html.parent) + "/./plan.html"
                self.assert_renderer_same_file_refused(html, pdf)

    def test_renderer_refuses_symlink_aliases_of_the_input(self):
        for side in ("input", "output"):
            with self.subTest(symlink=side):
                html = self.tmp / side / "plan.html"
                write(html, b'<!DOCTYPE html>\n<html><body>Synthetic plan</body></html>\n')
                alias = html.parent / "alias"
                alias.symlink_to("plan.html")
                self.assert_renderer_same_file_refused(alias if side == "input" else html,
                                                       html if side == "input" else alias)

    def test_renderer_refuses_hard_link_aliases_of_the_input(self):
        html, pdf = self.tmp / "plan.html", self.tmp / "plan.pdf"
        write(html, b'<!DOCTYPE html>\n<html><body>Synthetic plan</body></html>\n')
        os.link(html, pdf)
        self.assert_renderer_same_file_refused(html, pdf)

    def test_renderer_browser_launch_failure_is_plain_and_leaves_no_pdf_or_profile(self):
        html, pdf = self.tmp / "plan.html", self.tmp / "plan.pdf"
        html.write_text("<!DOCTYPE html>\n<html><head><title>Fixture</title></head>"
                        "<body>Fixture</body></html>\n")
        browser = self.tmp / "not-executable-browser"
        browser.write_text("synthetic non-executable placeholder\n")
        browser.chmod(0o600)
        done = self.run_script(RENDERER, html, pdf, env={"V2E_BROWSER": str(browser)})
        self.assert_plain_error(done, "render_pdf.py")
        self.assertFalse(pdf.exists())
        self.assertEqual(list((self.tmp / "temp").glob("v2e-browser-*")), [])
