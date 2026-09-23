"""Tests for the plan template and the PDF renderer.

The render test fills every placeholder of the real template with sample text, so it always tracks the
current template. It is skipped when no Chrome-family browser is installed; the refusal tests never
need one.

Run from the repository root:  python3 -m unittest discover -s tests -v
"""

import http.server
import importlib.util
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "vibe-to-engineering"
SCRIPT = Path(os.environ.get("V2E_RENDER_PDF", SKILL / "scripts" / "render_pdf.py"))  # seam: test another copy
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

    def test_refuses_a_plan_with_a_script_or_an_event_handler(self):
        for extra in ('<script>document.title = "x"</script>', '<img src="data:," onload="alert(1)">'):
            with self.subTest(extra=extra):
                code, output, pdf = self.render(filled_template().replace("</body>", extra + "</body>"))
                self.assertEqual(code, 1, output)
                self.assertIn("static", output)
                self.assertFalse(pdf.exists())

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
        self.assertEqual(code, 0, output)
        self.assertTrue(pdf.read_bytes().startswith(b"%PDF-"), "no PDF, so the absence of requests proves nothing")
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


if __name__ == "__main__":
    unittest.main()
