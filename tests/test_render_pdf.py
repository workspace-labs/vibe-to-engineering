"""Tests for the plan template and the PDF renderer.

The render test fills every placeholder of the real template with sample text, so it always tracks the
current template. It is skipped when no Chrome-family browser is installed; the refusal tests never
need one.

Run from the repository root:  python3 -m unittest discover -s tests -v
"""

import contextlib
import http.server
import importlib.util
import io
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "vibe-to-engineering"
SCRIPT = Path(os.environ.get("V2E_RENDER_PDF", SKILL / "scripts" / "render_pdf.py"))  # seam: test another copy
sys.path.insert(0, str(SCRIPT.parent))  # sibling modules for isolated renderer discovery
TEMPLATE = SKILL / "assets" / "plan-template.html"
SECTIONS = ("summary", "overview", "findings", "target", "phases", "verification", "unchanged", "risks", "approval")


def filled_template():
    return re.sub(r"\{\{([A-Z0-9_]+)\}\}", lambda m: "Sample " + m.group(1).lower().replace("_", " "),
                  TEMPLATE.read_text(encoding="utf-8"))


def installed_browser():
    spec = importlib.util.spec_from_file_location("render_pdf", str(SCRIPT))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.find_browser()


class Renderer(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="v2e-pdf-")).resolve()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def render(self, html_text, env=None):
        html = self.tmp / "plan.html"
        html.write_text(html_text, encoding="utf-8")
        pdf = self.tmp / "plan.pdf"
        done = subprocess.run([sys.executable, str(SCRIPT), str(html), str(pdf)], env=env,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return done.returncode, done.stdout.decode() + done.stderr.decode(), pdf

    def test_the_template_has_every_plan_section_and_loads_nothing_from_the_network(self):
        text = TEMPLATE.read_text(encoding="utf-8")
        for section in SECTIONS:
            self.assertIn('id="%s"' % section, text)
        for words in ("CURRENT", "MIGRATION", "TARGET", "AWAITING HUMAN APPROVAL"):
            self.assertIn(words, text)
        self.assertNotRegex(text, r"(?i)(src\s*=\s*[\"']?\s*(https?:)?//|url\(\s*[\"']?\s*(https?:)?//|@import)")

    def test_refuses_a_plan_with_unfilled_placeholders(self):
        code, output, pdf = self.render(TEMPLATE.read_text(encoding="utf-8"))
        self.assertEqual(code, 1, output)
        self.assertIn("unfilled placeholders", output)
        self.assertRegex(output, r"\{\{[A-Z_]+\}\}")
        self.assertFalse(pdf.exists())

    def test_refuses_a_plan_that_loads_from_the_network(self):
        text = filled_template().replace("</head>", '<link rel="stylesheet" href="https://example.com/x.css"></head>')
        code, output, _ = self.render(text)
        self.assertEqual(code, 1, output)
        self.assertIn("self-contained", output)

    def test_names_the_missing_browser_it_was_told_to_use(self):
        env = dict(os.environ, V2E_BROWSER=str(self.tmp / "no-such-browser"))
        code, output, _ = self.render(filled_template(), env=env)
        self.assertEqual(code, 3, output)
        self.assertIn("V2E_BROWSER", output)

    def checked(self, extra):
        """Exit code and output for the template plus `extra`, stopped before any browser starts:
        1 means the plan was refused, 3 that it passed every check (only the missing browser stopped it)."""
        env = dict(os.environ, V2E_BROWSER=str(self.tmp / "no-such-browser"))
        code, output, pdf = self.render(filled_template().replace("</body>", extra + "</body>"), env=env)
        self.assertFalse(pdf.exists())
        return code, output

    def test_refuses_nested_documents_local_files_and_encoded_active_content(self):
        local = self.tmp / "local-secret.txt"
        local.write_text("LOCAL-FILE-CONTENT")
        cases = {
            "an entity-encoded script in a nested document":
                '<iframe srcdoc="&#60;script&#62;document.write(\'SCRIPT-EXECUTED\')&#60;/script&#62;"></iframe>',
            "a local file in a frame": '<iframe src="%s"></iframe>' % local.as_uri(),
            "a local file in an object": '<object data="%s"></object>' % local.as_uri(),
            "an embedded file": '<embed src="local-secret.txt">',
            "a relative image": '<img src="local-secret.txt">',
            "a local image": '<img src="%s">' % local.as_uri(),
            "a local image candidate": '<img srcset="local-secret.txt 1x">',
            "an entity-encoded network address": '<img src="http&#58;//127.0.0.1:9/x.png">',
            "an entity-encoded script address": '<img src="javascript&#58;alert(1)">',
            "a stylesheet file": '<link rel="stylesheet" href="plan.css">',
            "a local file in CSS": '<div style="background: url(local-secret.txt)"></div>',
            "an entity-encoded url() in a style attribute": '<div style="background: u&#114;l(local-secret.txt)"></div>',
            "a CSS escape": '<style>div { background: u\\72 l(local-secret.txt) }</style>',
            "a CSS image-set": '<style>div { background: image-set("local-secret.txt" 1x) }</style>',
            "a refresh to a local file": '<meta http-equiv="refresh" content="0; url=%s">' % local.as_uri(),
            "a base address": '<base href="%s">' % self.tmp.as_uri(),
            "an SVG image": '<svg><image href="%s"/></svg>' % local.as_uri(),
            "markup another parser reads differently": '<!-- x --!><iframe src="%s"></iframe> -->' % local.as_uri(),
        }
        for name, extra in cases.items():
            with self.subTest(name):
                code, output = self.checked(extra)
                self.assertEqual(code, 1, output)
                self.assertIn("self-contained", output)

    def test_accepts_code_that_is_quoted_as_text(self):
        quoted = ('<p>Evidence: <code>&lt;script src="app.js"&gt;</code>, <code>&lt;iframe srcdoc="x"&gt;</code>, '
                  '<code>onclick="save()"</code>, <code>url(logo.png)</code>, file:///etc/hosts and '
                  '<code>javascript:void(0)</code>.</p>')
        code, output = self.checked(quoted)
        self.assertEqual(code, 3, output)

    def test_refuses_a_plan_with_a_script_or_an_event_handler(self):
        for extra in ('<script>document.title = "x"</script>', '<img src="data:," onload="alert(1)">'):
            with self.subTest(extra=extra):
                code, output, pdf = self.render(filled_template().replace("</body>", extra + "</body>"))
                self.assertEqual(code, 1, output)
                self.assertIn("static", output)
                self.assertFalse(pdf.exists())

    def test_refuses_an_element_that_is_not_on_the_list_even_a_harmless_one(self):   # FIX-FIRST item 9
        code, output = self.checked("<p><a>no attribute, so only the element list can refuse it</a></p>")
        self.assertEqual(code, 1, output)
        self.assertIn("while it prints: <a>.", output)

    def test_refuses_a_meta_tag_that_other_markup_hides_from_the_checks(self):
        local = self.tmp / "local-secret.txt"
        local.write_text("LOCAL-FILE-CONTENT")
        for extra in ('<!-- x --!><meta content="0; url=%s" x=">" http-equiv="refresh"> -->' % local.as_uri(),
                      '<meta name="viewport" content="width=device-width" http-equiv="refresh">'):
            with self.subTest(extra=extra):
                code, output = self.checked(extra)
                self.assertEqual(code, 1, output)
                self.assertIn("<meta> other than the template's", output)

    def test_refuses_a_plan_with_anything_but_spaces_before_the_doctype(self):
        for name, lead in (("a non-breaking space", " "), ("a vertical tab", "\x0b"), ("an em space", " "),
                           ("a comment", "<!-- x -->"), ("text", "x")):
            with self.subTest(name):
                env = dict(os.environ, V2E_BROWSER=str(self.tmp / "no-such-browser"))
                code, output, pdf = self.render(lead + filled_template(), env=env)
                self.assertEqual(code, 1, output)
                self.assertIn("must begin with <!DOCTYPE html>", output)
                self.assertFalse(pdf.exists())
        code, output, pdf = self.render(filled_template().replace("<!DOCTYPE html>", "", 1),
                                        env=dict(os.environ, V2E_BROWSER=str(self.tmp / "no-such-browser")))
        self.assertEqual(code, 1, output)
        self.assertIn("it has no doctype", output)

    @unittest.skipIf(os.name == "nt", "the stand-in browser is a shell script")
    def test_refuses_the_print_when_the_browser_reports_the_policy_ignored(self):
        browser = self.tmp / "browser"
        browser.write_text('#!/bin/sh\nfor arg in "$@"; do case "$arg" in --print-to-pdf=*) printf "%%s" "%%PDF-1.4 stand-in" '
                           '> "${arg#--print-to-pdf=}";; esac; done\n'
                           'echo "[0924/000000.000000:INFO:CONSOLE:1] \\"The Content Security Policy \'default-src '
                           "'none'\\' was delivered via a <meta> element outside the document's <head>, which is "
                           'disallowed. The policy has been ignored.\\", source: file:///plan.html (1)" >&2\n')
        os.chmod(browser, 0o755)
        code, output, pdf = self.render(filled_template(), env=dict(os.environ, V2E_BROWSER=str(browser)))
        self.assertEqual(code, 1, output)
        self.assertIn("The policy has been ignored", output)
        self.assertFalse(pdf.exists(), "a PDF printed without the policy was kept")

    @unittest.skipIf(installed_browser() is None or not shutil.which("pdftotext"),
                     "needs a Chrome-family browser and pdftotext")
    def test_the_browser_runs_no_script_and_loads_no_local_file_whatever_markup_gets_past_the_checks(self):
        svg = self.tmp / "local.svg"
        svg.write_text('<svg xmlns="http://www.w3.org/2000/svg" width="500" height="100">'
                       '<text x="10" y="60" font-size="28">LOCAL-FILE-LOADED</text></svg>')
        inline = ("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='500' height='100'%3E"
                  "%3Ctext x='10' y='60' font-size='28'%3EINLINE-IMAGE-SHOWN%3C/text%3E%3C/svg%3E")
        cases = {   # the independent review's inputs (2026-09-24): Python's parser and the browser read them apart
            "an event handler behind a comment only the browser closes":
                '<!-- hidden --!><img/src="data:,"/onerror="document.body.append(\'EVENT-SCRIPT-EXECUTED\')"> -->',
            "a local image behind that comment": '<!-- hidden --!><img src="%s"> -->' % svg.as_uri(),
            "a style only the browser keeps open":
                '<style/>div{width:500px;height:100px;background-image:url(%s)}</style><div></div>' % svg.as_uri(),
            "a local image in a style behind that comment":
                '<!-- hidden --!><style>div{width:500px;height:100px;background-image:url(%s)}</style><div></div> -->'
                % svg.as_uri(),
        }
        for name, extra in cases.items():
            with self.subTest(name):   # the policy stops it in the browser, and the browser's report stops the print
                code, output, pdf = self.render(filled_template().replace("</body>", extra + "</body>"))
                self.assertEqual(code, 1, output)
                self.assertIn("violates the following Content Security Policy directive", output)
                self.assertFalse(pdf.exists(), "a PDF was kept although the browser reported the plan")
        for name, lead in (("nothing", ""), ("a byte order mark and spaces", "﻿ \t\n")):
            with self.subTest("an image written into the plan, with %s before the doctype" % name):
                plan = lead + filled_template().replace("</body>", '<p><img alt="" src="%s"></p></body>' % inline)
                code, output, pdf = self.render(plan)
                self.assertEqual(code, 0, output)
                text = subprocess.run(["pdftotext", str(pdf), "-"], stdout=subprocess.PIPE).stdout.decode()
                self.assertIn("AWAITING HUMAN APPROVAL", text)        # the plan printed...
                self.assertIn("INLINE-IMAGE-SHOWN", text)             # ...with the image written into it

    @unittest.skipIf(installed_browser() is None, "no Chrome-family browser installed")
    def test_nothing_is_fetched_while_rendering(self):
        requests = []

        class Beacon(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                requests.append(self.path)
                self.send_response(404)
                self.end_headers()

            def log_message(self, *args):
                pass

        server = http.server.HTTPServer(("127.0.0.1", 0), Beacon)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        try:
            port = server.server_address[1]
            sneaky = '<img srcset="http://localhost:%d/beacon.png 1x"></body>' % port  # slips past the text check
            code, output, pdf = self.render(filled_template().replace("</body>", sneaky))
        finally:
            server.shutdown()
            server.server_close()
        self.assertEqual(code, 1, output)   # the policy stopped the image, and the browser's report stopped the print
        self.assertIn("violates the following Content Security Policy directive", output)
        self.assertFalse(pdf.exists())
        self.assertEqual(requests, [], "the renderer reached the network")

    @unittest.skipIf(installed_browser() is None, "no Chrome-family browser installed")
    def test_renders_the_template_with_a_landscape_overview_page(self):
        code, output, pdf = self.render(filled_template())
        self.assertEqual(code, 0, output)
        self.assertTrue(pdf.read_bytes().startswith(b"%PDF-"))
        if shutil.which("pdftotext"):
            text = subprocess.run(["pdftotext", "-layout", str(pdf), "-"], stdout=subprocess.PIPE).stdout.decode()
            for words in ("CURRENT", "MIGRATION", "TARGET", "AWAITING HUMAN APPROVAL", "Sample project name"):
                self.assertIn(words, text)
        if shutil.which("pdfinfo"):
            info = subprocess.run(["pdfinfo", "-f", "1", "-l", "2", str(pdf)], stdout=subprocess.PIPE).stdout.decode()
            sizes = re.findall(r"Page\s+(\d+) size:\s+([\d.]+) x ([\d.]+)", info)
            portrait, landscape = sizes[0], sizes[1]
            self.assertLess(float(portrait[1]), float(portrait[2]), "page 1 should be portrait")
            self.assertGreater(float(landscape[1]), float(landscape[2]), "page 2 should be landscape")


class RendererOutputSafety(unittest.TestCase):
    """Destination and failure handling, using only disposable files and a mocked browser."""

    def setUp(self):
        self.folder = tempfile.TemporaryDirectory(prefix="v2e-render-safety-")
        self.addCleanup(self.folder.cleanup)
        self.tmp = Path(self.folder.name).resolve()
        self.html = self.tmp / "plan.html"
        self.html.write_text("<!DOCTYPE html><html><body><p>Fixture plan</p></body></html>", encoding="utf-8")
        self.pdf = self.tmp / "plan.pdf"
        self.previous = b"previous PDF must survive a failed render"
        self.pdf.write_bytes(self.previous)
        spec = importlib.util.spec_from_file_location("renderer_under_test", str(SCRIPT))
        self.renderer = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.renderer)

    def invoke(self, browser_run, output=None):
        out, error = io.StringIO(), io.StringIO()
        with mock.patch.object(self.renderer, "require_supported_platform"), \
                mock.patch.object(self.renderer, "find_browser", return_value="/fixture/browser"), \
                mock.patch.object(self.renderer.subprocess, "run", side_effect=browser_run) as launch, \
                mock.patch.object(self.renderer, "page_count", return_value=1), \
                contextlib.redirect_stdout(out), contextlib.redirect_stderr(error):
            code = self.renderer.main(["render_pdf.py", str(self.html), str(output or self.pdf)])
        return code, out.getvalue() + error.getvalue(), launch

    @staticmethod
    def print_pdf(command, **kwargs):
        target = Path(next(arg.split("=", 1)[1] for arg in command if arg.startswith("--print-to-pdf=")))
        target.write_bytes(b"%PDF-1.4\nfixture replacement\n")
        return subprocess.CompletedProcess(command, 0, b"", b"")

    def test_refuses_input_as_output_without_touching_the_plan(self):
        previous = self.html.read_bytes()
        code, output, launch = self.invoke(self.print_pdf, self.html)
        self.assertEqual(code, 1, output)
        self.assertEqual(self.html.read_bytes(), previous)
        launch.assert_not_called()

    def test_refuses_symlink_destinations_and_symlinked_parent_directories(self):
        link = self.tmp / "linked.pdf"
        link.symlink_to(self.pdf)
        outside = self.tmp / "outside"
        outside.mkdir()
        escaped_pdf = outside / "plan.pdf"
        escaped_pdf.write_bytes(self.previous)
        parent_link = self.tmp / "linked-parent"
        parent_link.symlink_to(outside, target_is_directory=True)
        for output in (link, parent_link / "plan.pdf"):
            with self.subTest(output=output):
                code, diagnostic, launch = self.invoke(self.print_pdf, output)
                self.assertEqual(code, 1, diagnostic)
                self.assertEqual(self.pdf.read_bytes(), self.previous)
                self.assertEqual(escaped_pdf.read_bytes(), self.previous)
                launch.assert_not_called()
        self.assertTrue(link.is_symlink())
        self.assertTrue(parent_link.is_symlink())

    @unittest.skipUnless(sys.platform == "darwin", "native macOS /tmp alias")
    def test_accepts_the_native_macos_tmp_alias(self):
        with tempfile.TemporaryDirectory(prefix="v2e-render-alias-", dir="/tmp") as folder:
            pdf = Path(folder) / "plan.pdf"  # deliberately preserve the system alias
            code, output, _ = self.invoke(self.print_pdf, pdf)
            self.assertEqual(code, 0, output)
            self.assertEqual(pdf.read_bytes(), b"%PDF-1.4\nfixture replacement\n")
            self.assertEqual(sorted(path.name for path in Path(folder).iterdir()), ["plan.pdf"])

    @unittest.skipUnless(sys.platform == "darwin", "native macOS /var/folders alias")
    def test_accepts_the_native_macos_var_folders_alias(self):
        if not self.tmp.is_relative_to("/private/var/folders"):
            self.skipTest("the native temporary fixture is not under /var/folders")
        pdf = Path("/var") / self.tmp.relative_to("/private/var") / "aliased.pdf"
        code, output, _ = self.invoke(self.print_pdf, pdf)
        self.assertEqual(code, 0, output)
        self.assertEqual(pdf.read_bytes(), b"%PDF-1.4\nfixture replacement\n")

    def test_refuses_a_directory_destination_without_a_traceback(self):
        directory = self.tmp / "directory.pdf"
        directory.mkdir()
        code, output, launch = self.invoke(self.print_pdf, directory)
        self.assertEqual(code, 1, output)
        self.assertNotIn("Traceback", output)
        self.assertTrue(directory.is_dir())
        launch.assert_not_called()

    def test_nonzero_browser_exit_cannot_replace_an_existing_pdf(self):
        def fail_after_print(command, **kwargs):
            done = self.print_pdf(command, **kwargs)
            done.returncode = 7
            return done

        code, output, _ = self.invoke(fail_after_print)
        self.assertEqual(code, 1, output)
        self.assertEqual(self.pdf.read_bytes(), self.previous)
        self.assertEqual(sorted(path.name for path in self.tmp.iterdir()), ["plan.html", "plan.pdf"])

    def test_browser_timeout_preserves_an_existing_pdf_and_removes_partial_output(self):
        def timeout_after_print(command, **kwargs):
            self.print_pdf(command, **kwargs)
            raise subprocess.TimeoutExpired(command, 180)

        code, output, _ = self.invoke(timeout_after_print)
        self.assertEqual(code, 1, output)
        self.assertEqual(self.pdf.read_bytes(), self.previous)
        self.assertEqual(sorted(path.name for path in self.tmp.iterdir()), ["plan.html", "plan.pdf"])

    def test_browser_launch_error_preserves_the_pdf_without_a_traceback(self):
        code, output, _ = self.invoke(PermissionError("fixture browser cannot execute"))
        self.assertEqual(code, 1, output)
        self.assertNotIn("Traceback", output)
        self.assertIn("cannot execute", output)
        self.assertEqual(self.pdf.read_bytes(), self.previous)

    def test_missing_or_invalid_new_pdf_preserves_an_existing_pdf(self):
        def invalid_pdf(command, **kwargs):
            done = self.print_pdf(command, **kwargs)
            target = Path(next(arg.split("=", 1)[1] for arg in command if arg.startswith("--print-to-pdf=")))
            target.write_bytes(b"not a PDF")
            return done

        for render in (invalid_pdf, lambda command, **kwargs: subprocess.CompletedProcess(command, 0, b"", b"")):
            with self.subTest(render=render):
                code, output, _ = self.invoke(render)
                self.assertEqual(code, 1, output)
                self.assertEqual(self.pdf.read_bytes(), self.previous)
                self.assertEqual(sorted(path.name for path in self.tmp.iterdir()), ["plan.html", "plan.pdf"])

    def test_replace_failure_preserves_an_existing_pdf_without_a_traceback(self):
        with mock.patch.object(self.renderer.os, "replace", side_effect=PermissionError("fixture replace denied")):
            code, output, _ = self.invoke(self.print_pdf)
        self.assertEqual(code, 1, output)
        self.assertIn("replace denied", output)
        self.assertNotIn("Traceback", output)
        self.assertEqual(self.pdf.read_bytes(), self.previous)
        self.assertEqual(sorted(path.name for path in self.tmp.iterdir()), ["plan.html", "plan.pdf"])

    def test_policy_refusal_preserves_an_existing_pdf(self):
        def report_policy(command, **kwargs):
            done = self.print_pdf(command, **kwargs)
            done.stderr = b"Content Security Policy was ignored"
            return done

        code, output, _ = self.invoke(report_policy)
        self.assertEqual(code, 1, output)
        self.assertEqual(self.pdf.read_bytes(), self.previous)

    def test_success_replaces_the_pdf_only_after_rendering_to_a_temporary_path(self):
        def print_while_original_survives(command, **kwargs):
            self.assertEqual(self.pdf.read_bytes(), self.previous)
            target = Path(next(arg.split("=", 1)[1] for arg in command if arg.startswith("--print-to-pdf=")))
            self.assertNotEqual(target, self.pdf)
            self.assertTrue(target.is_relative_to(self.pdf.parent))
            return self.print_pdf(command, **kwargs)

        with mock.patch.object(self.renderer.os, "replace", wraps=os.replace) as replace:
            code, output, _ = self.invoke(print_while_original_survives)
        self.assertEqual(code, 0, output)
        self.assertEqual(self.pdf.read_bytes(), b"%PDF-1.4\nfixture replacement\n")
        replace.assert_called_once()
        self.assertEqual(Path(replace.call_args.args[1]), self.pdf)
        self.assertEqual(sorted(path.name for path in self.tmp.iterdir()), ["plan.html", "plan.pdf"])

    def test_nonexecutable_browser_override_is_not_selected(self):
        browser = self.tmp / "browser"
        browser.write_text("fixture, not executable", encoding="utf-8")
        browser.chmod(0o644)
        with mock.patch.dict(os.environ, {"V2E_BROWSER": str(browser)}):
            self.assertIsNone(self.renderer.find_browser())


if __name__ == "__main__":
    unittest.main()
