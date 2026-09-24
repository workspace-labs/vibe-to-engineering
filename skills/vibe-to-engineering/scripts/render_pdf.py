#!/usr/bin/env python3
"""Render Engineering-Migration-Plan.html to a PDF with a Chrome-family browser.

    python3 render_pdf.py <plan.html> <plan.pdf>        (Windows: py -3 render_pdf.py …)

Standard library only. It uses a Chrome, Chromium, Edge or Brave browser that is
already installed, or one downloaded by Playwright; set V2E_BROWSER to a browser's
full path to choose one. Where browsers are looked for is the only
platform-specific part, in browser_candidates(). It refuses a plan with unfilled
placeholders, scripts, external resources, nested documents or local files — reading
the markup decoded, as the browser does — and blocks every network lookup while
printing. It prints a temporary copy that starts with a content security policy, so
the browser itself runs no script and loads nothing but images written into the plan,
whatever markup got past the checks.

Exit codes: 0 written; 1 refused or failed; 2 usage; 3 no browser found.
"""

import glob
import os
import re
import shutil
import subprocess
import sys
import tempfile
from html.parser import HTMLParser
from pathlib import Path

PLACEHOLDER = re.compile(r"\{\{[^{}]*\}\}|\{\{")
REMOTE = (  # anything the browser would fetch from the network; the plan must be self-contained
    re.compile(r"""\bsrc\s*=\s*["']?\s*(?:https?:)?//""", re.I),
    re.compile(r"""<link\b[^>]*\bhref\s*=\s*["']?\s*(?:https?:)?//""", re.I),
    re.compile(r"""url\(\s*["']?\s*(?:https?:)?//""", re.I),
    re.compile(r"""@import\b""", re.I),
)
# A plan is static. (Turning scripts off in the browser also stops it printing, so they are refused here.)
SCRIPT = re.compile(r"""<script\b|<[^>]*\son[a-z]+\s*=""", re.I)

# The markup a plan may use: the template's, plus plain text markup. Anything else — frames, objects, embeds, links
# to other files, a <base>, forms, media, SVG — could run code or bring another document or file into the PDF.
ELEMENTS = {"html", "head", "meta", "title", "style", "body", "section", "article", "header", "footer", "main", "div",
            "span", "p", "h1", "h2", "h3", "h4", "h5", "h6", "ul", "ol", "li", "dl", "dt", "dd", "table", "caption",
            "colgroup", "col", "thead", "tbody", "tfoot", "tr", "th", "td", "pre", "code", "b", "strong", "i", "em",
            "u", "s", "small", "sub", "sup", "br", "hr", "blockquote", "figure", "figcaption", "abbr", "mark", "kbd",
            "samp", "var", "img"}
ATTRIBUTES = {"class", "id", "style", "lang", "dir", "title", "colspan", "rowspan", "span"}
ELEMENT_ATTRIBUTES = {"meta": {"charset", "name", "content"}, "img": {"src", "srcset", "alt", "width", "height"}}
# The same kinds of markup, looked for in the raw text too: odd markup that Python's parser reads differently from
# the browser's (a comment closed with "--!>", for example) cannot hide them.
NESTED = re.compile(r"""<\s*(script|iframe|frame|frameset|object|embed|applet|portal|fencedframe|base|link|svg|math)\b"""
                    r"""|<[^>]*[\s"'/](srcdoc|http-equiv)\s*=""", re.I)
CSS_LOADS = re.compile(r"""(?<![\w-])(?:image-set|-webkit-image-set|image|element|cross-fade|src)\s*\(|@import""", re.I)
CSS_URL = re.compile(r"""(?<![\w-])url\s*\(\s*["']?\s*([^"')\s]*)""", re.I)
# A <meta> can send the page to another address (a refresh), which no content policy stops. Every <meta> starts with
# these five characters in the raw text, so only the template's two lines are allowed, whatever parser reads the rest.
META = re.compile(r"<meta\b", re.I)
META_ALLOWED = re.compile(r"""<meta\s+(?:charset\s*=\s*["']?utf-8["']?|name\s*=\s*["']?viewport["']?\s+"""
                          r"""content\s*=\s*"[^"<>]*")\s*/?>""", re.I)
# Put in front of the plan before it prints, so the browser enforces what the checks look for: no script or event
# handler runs, and nothing loads — no local file, no network address — except images and fonts written into the plan.
POLICY = ('<meta charset="utf-8"><meta http-equiv="Content-Security-Policy" content="default-src \'none\'; '
          "style-src 'unsafe-inline'; img-src data:; font-src data:; base-uri 'none'; form-action 'none'\">")
DOCTYPE = re.compile(r"﻿?\s*<!doctype[^>]*>", re.I)


def address_kind(address):
    """"inline" for data carried in the plan itself, "network" for an http(s) address (the browser's network block
    stops those), "local" for anything else — a file, a relative path, another scheme."""
    address = address.strip().lower()
    if address.startswith("data:"):
        return "inline"
    return "network" if address.startswith(("http:", "https:")) else "local"


def css_problem(css):
    """What in this CSS could load something while the plan prints, or None."""
    css = re.sub(r"/\*.*?\*/", " ", css, flags=re.S)
    if "\\" in css:
        return "a CSS escape (\\), which can spell url( or @import in disguise"
    found = CSS_LOADS.search(css)
    if found:
        return "CSS " + found.group(0)
    for match in CSS_URL.finditer(css):
        if address_kind(match.group(1)) != "inline":
            return "CSS url(%s)" % match.group(1)[:60]
    return None


class Markup(HTMLParser):
    """Collects what in a plan could run code, or bring in another document or a file, while it prints. Attribute
    values arrive decoded (&#58; is ':'), as the browser reads them."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.problems, self.css, self.in_style = [], [], False

    def handle_starttag(self, tag, attrs):
        if tag not in ELEMENTS:
            self.problems.append("<%s>" % tag)
        self.in_style = tag == "style"
        for name, value in attrs:
            value = value or ""
            if name not in ATTRIBUTES and name not in ELEMENT_ATTRIBUTES.get(tag, ()):
                self.problems.append('%s="…" on <%s>' % (name, tag))
            elif name == "style":
                self.css.append(value)
            elif name in ("src", "srcset"):
                addresses = [value] if name == "src" else [part.split()[0] for part in value.split(",") if part.split()]
                for address in addresses:  # a network address in srcset is left to the browser's network block
                    if address_kind(address) == "local" or (name == "src" and address_kind(address) == "network"):
                        self.problems.append('%s="%s"' % (name, address[:60]))

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        self.in_style = False

    def handle_endtag(self, tag):
        self.in_style = False

    def handle_data(self, data):
        if self.in_style:
            self.css.append(data)


def static_problems(text):
    """Everything in the plan that could run code, or bring in another document or a file, while it prints."""
    problems = ["<%s>" % match.group(1).lower() if match.group(1) else '%s="…"' % match.group(2).lower()
                for match in NESTED.finditer(text)]
    markup = Markup()
    markup.feed(text)
    markup.close()
    problems += markup.problems + [problem for problem in map(css_problem, markup.css) if problem]
    problems += ["<meta> other than the template's charset and viewport lines"
                 for meta in META.finditer(text) if not META_ALLOWED.match(text, meta.start())]
    return list(dict.fromkeys(problems))


def with_policy(text):
    """The plan with POLICY in front of everything it holds — after a leading doctype, so the page keeps its layout."""
    lead = DOCTYPE.match(text)
    return text[:lead.end()] + POLICY + text[lead.end():] if lead else POLICY + text


def browser_candidates():
    """Where Chrome-family browsers usually live on this operating system."""
    home = Path.home()
    names = ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser", "microsoft-edge",
             "microsoft-edge-stable", "brave-browser", "chrome", "msedge", "chrome-headless-shell")
    found = [shutil.which(name) for name in names]
    if sys.platform == "darwin":
        for root in (Path("/Applications"), home / "Applications"):
            for app in ("Google Chrome", "Chromium", "Microsoft Edge", "Brave Browser", "Google Chrome for Testing"):
                found.append(root / (app + ".app") / "Contents" / "MacOS" / app)
        playwright = home / "Library" / "Caches" / "ms-playwright"
    elif os.name == "nt":
        for variable in ("PROGRAMFILES", "PROGRAMFILES(X86)", "LOCALAPPDATA"):
            base = os.environ.get(variable)
            if base:
                found += [Path(base, "Google", "Chrome", "Application", "chrome.exe"),
                          Path(base, "Microsoft", "Edge", "Application", "msedge.exe"),
                          Path(base, "Chromium", "Application", "chrome.exe"),
                          Path(base, "BraveSoftware", "Brave-Browser", "Application", "brave.exe")]
        playwright = Path(os.environ.get("LOCALAPPDATA", str(home))) / "ms-playwright"
    else:
        found.append(Path("/snap/bin/chromium"))
        playwright = home / ".cache" / "ms-playwright"
    for pattern in ("chromium_headless_shell-*/*/chrome-headless-shell", "chromium_headless_shell-*/*/chrome-headless-shell.exe",
                    "chromium-*/chrome-*/chrome", "chromium-*/chrome-*/chrome.exe",
                    "chromium-*/chrome-*/*.app/Contents/MacOS/*"):
        found += sorted(glob.glob(str(playwright / pattern)), reverse=True)
    return [str(path) for path in found if path]


def find_browser():
    chosen = os.environ.get("V2E_BROWSER")
    if chosen:
        return chosen if Path(chosen).is_file() else None
    for candidate in browser_candidates():
        if Path(candidate).is_file() and os.access(candidate, os.X_OK):
            return candidate
    return None


def page_count(pdf):
    """Pages in the PDF, from pdfinfo when it is installed, else by counting page objects."""
    if shutil.which("pdfinfo"):
        info = subprocess.run(["pdfinfo", str(pdf)], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        match = re.search(rb"^Pages:\s+(\d+)", info.stdout, re.M)
        if match:
            return int(match.group(1))
    count = len(re.findall(rb"/Type\s*/Page(?![a-zA-Z])", pdf.read_bytes()))
    return count or None


def main(argv):
    if len(argv) != 3:
        print("usage: render_pdf.py <plan.html> <plan.pdf>", file=sys.stderr)
        return 2
    html, pdf = Path(argv[1]).expanduser().resolve(), Path(argv[2]).expanduser().resolve()
    if not html.is_file():
        print("render_pdf.py: error: plan not found: %s" % html, file=sys.stderr)
        return 2
    text = html.read_text(encoding="utf-8")
    left = sorted(set(PLACEHOLDER.findall(text)))
    if left:
        print("render_pdf.py: error: the plan still has unfilled placeholders: %s. Fill them, or write text "
              "that really contains two braces as &#123;&#123;." % ", ".join(left[:10]), file=sys.stderr)
        return 1
    if SCRIPT.search(text):
        print("render_pdf.py: error: the plan contains a script or an event handler; a plan is static — "
              "remove them.", file=sys.stderr)
        return 1
    if any(rule.search(text) for rule in REMOTE):
        print("render_pdf.py: error: the plan loads something from the network; keep it self-contained "
              "(no external scripts, stylesheets, fonts or images).", file=sys.stderr)
        return 1
    problems = static_problems(text)
    if problems:
        print("render_pdf.py: error: the plan holds something that could run code, or bring in another document or a "
              "file, while it prints: %s. A plan is static and self-contained — remove it; text that shows code is "
              "written with &lt; and &gt;." % ", ".join(problems[:10]), file=sys.stderr)
        return 1
    browser = find_browser()
    if browser is None:
        where = "V2E_BROWSER=%s does not exist" % os.environ["V2E_BROWSER"] if os.environ.get("V2E_BROWSER") \
            else "no Chrome, Chromium, Edge or Brave browser was found"
        print("render_pdf.py: error: %s. The plan is still readable in any browser: %s. To make the PDF, install "
              "one of those browsers or set V2E_BROWSER to one's full path." % (where, html), file=sys.stderr)
        return 3
    if pdf.exists():
        pdf.unlink()  # never let an old PDF pass for the new one
    work = Path(tempfile.mkdtemp(prefix="v2e-browser-"))
    try:
        page = work / "plan.html"
        page.write_bytes(with_policy(text).encode("utf-8"))
        command = [browser, "--headless", "--disable-gpu", "--no-first-run", "--no-default-browser-check",
                   "--disable-extensions", "--user-data-dir=" + str(work / "profile"), "--no-pdf-header-footer",
                   "--print-to-pdf-no-header",
                   "--host-resolver-rules=MAP * ~NOTFOUND",  # no host name resolves: nothing is fetched
                   "--print-to-pdf=" + str(pdf), page.as_uri()]
        done = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=180)
    except subprocess.TimeoutExpired:
        print("render_pdf.py: error: %s did not finish within 3 minutes" % browser, file=sys.stderr)
        return 1
    finally:
        shutil.rmtree(str(work), ignore_errors=True)
    if not pdf.is_file() or not pdf.read_bytes().startswith(b"%PDF-"):
        detail = done.stderr.decode("utf-8", "replace").strip().splitlines()[-3:]
        print("render_pdf.py: error: %s did not produce a PDF. %s" % (browser, " ".join(detail)), file=sys.stderr)
        return 1
    pages = page_count(pdf)
    print("wrote %s (%s pages, %d KB) with %s" % (pdf, pages if pages else "?", pdf.stat().st_size // 1024, browser))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
