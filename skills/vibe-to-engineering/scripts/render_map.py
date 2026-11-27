#!/usr/bin/python3 -I
"""Render the approved migration plan's line map using the append-only ledger."""

import sys

sys.dont_write_bytecode = True

import argparse
import base64
import contextlib
import html
import io
import json
import os
import re
import stat
import tempfile
import unicodedata
import uuid
from html.parser import HTMLParser
from pathlib import Path
from textwrap import wrap
from typing import NamedTuple

if os.name == "posix":
    import fcntl

sys.path.insert(0, str(Path(__file__).resolve().parent))  # support isolated Python (-I)
import render_pdf
from private_names import load_name_map
from mapledger import phase_states
from checkpoint import STATE_DIR, check_state_folder, resolve_project
from gitrun import Fail, git, is_link
from platformgate import PlatformRefusal, require_supported_platform

PLAN = "Engineering-Migration-Plan.html"
LEDGER = "ledger.md"
MAP_DATA = "migration-map.json"
MAP_HTML = "Migration-Map.html"
MAP_PDF = "Migration-Map.pdf"
PHASE_HEADING = re.compile(r"Phase ([1-9]\d*)\s*—\s*(.+)\Z")
PLAN_VERSION = re.compile(r"Plan version\s+(\S+)\Z")
SAFE_VERSION = re.compile(r"[A-Za-z0-9._-]+")
APPROVED_MAP_TEMP = re.compile(r"\.v2e-approved-[0-9a-f]{32}\.tmp")
NEW_FILE_EVIDENCE = re.compile(r"exact|not yet exact: .+")
OLD_RANGE = re.compile(r"(part of )?([0-9]+)[-–]([0-9]+)")
OLD_LINE_GROUP = re.compile(
    rf"(?P<source>.+?): (?P<ranges>{OLD_RANGE.pattern}(?:, {OLD_RANGE.pattern})*)(?:; |\Z)"
)


class PlanEntries(HTMLParser):
    """Read version labels, phase headings and evidence from the plan form."""

    def __init__(self, plan):
        super().__init__(convert_charrefs=True)
        self.phases, self.paths = [], set()
        self.versions, self.new_files = set(), {}
        self.kind, self.pieces, self.badge = None, [], False
        self.path_cell = False
        self.has_new_files_table = self.in_new_files = False
        self.new_file_row = None
        self.feed(plan)
        self.close()

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        classes = (attrs.get("class") or "").split()
        if tag == "table" and attrs.get("id") == "new-files":
            if self.has_new_files_table:
                raise Fail("plan repeats the new-files table")
            self.has_new_files_table = self.in_new_files = True
        if tag == "tr" and self.in_new_files:
            self.new_file_row = []
        if tag == "td":
            self.path_cell = "path" in classes
        if (tag == "h3" or (tag == "td" and (self.path_cell or self.new_file_row is not None))
                or (tag in ("span", "p") and self.kind is None and "hidden" not in attrs)):
            self.kind, self.pieces = tag, []
        if self.kind == "h3" and tag == "span" and "badge" in classes:
            self.badge = True

    def handle_endtag(self, tag):
        if tag == "tr" and self.in_new_files:
            self.finish_new_file_row()
        if tag == "table":
            self.in_new_files = False
        if tag == "span":
            self.badge = False
        if tag != self.kind:
            return
        entry = "".join(self.pieces).strip()
        if tag == "td":
            if self.path_cell:
                self.paths.add(entry)
            if self.new_file_row is not None:
                self.new_file_row.append(entry)
        elif tag == "h3":
            match = PHASE_HEADING.fullmatch(entry)
            if match:
                self.phases.append((int(match[1]), match[2]))
        else:
            match = PLAN_VERSION.fullmatch(entry)
            if match:
                self.versions.add(match[1])
        self.kind = None

    def handle_data(self, text):
        if self.kind and not self.badge:
            self.pieces.append(text)

    def finish_new_file_row(self):
        row, self.new_file_row = self.new_file_row, None
        if not row:
            return  # The heading row uses th, not td.
        if len(row) != 5:
            raise Fail("each plan new-files row must have a path and four evidence cells")
        path = relative_path(row[0])
        if path in self.new_files:
            raise Fail("plan lists the new file more than once: %s" % path)
        evidence = " ".join(row[-1].split())
        if not NEW_FILE_EVIDENCE.fullmatch(evidence):
            raise Fail("invalid plan evidence for new file: %s" % path)
        self.new_files[path] = (row[1], evidence == "exact")


def regular_file(path, missing_ok=False):
    """Use lstat so even a dangling link is distinguishable from a missing file."""
    try:
        info = path.lstat()
    except FileNotFoundError:
        if missing_ok:
            return None
        raise
    if is_link(str(path)) or not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
        raise Fail("%s is linked or is not a regular file" % path)
    return info


@contextlib.contextmanager
def project_directory_fd(project, parts):
    """Hold the checked directory for relative file operations on macOS."""
    flags = os.O_RDONLY | os.O_DIRECTORY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
    directory = os.open(project.anchor, flags)
    try:
        for piece in (*project.parts[1:], *parts):
            child = os.open(piece, flags, dir_fd=directory)
            os.close(directory)
            directory = child
        yield directory
    finally:
        os.close(directory)


@contextlib.contextmanager
def project_file(project, parts):
    """Open a regular, unlinked file under project without following any link on macOS."""
    path = project.joinpath(*parts)
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
    with contextlib.ExitStack() as opened:
        if os.open in os.supports_dir_fd:
            directory = opened.enter_context(project_directory_fd(project, parts[:-1]))
            fd = os.open(parts[-1], flags, dir_fd=directory)
            opened.callback(os.close, fd)
        else:
            # Also used when exercising the pure validation path on unsupported platforms.
            for parent in path.parents:
                if parent == project:
                    break
                if is_link(str(parent)) or not stat.S_ISDIR(parent.lstat().st_mode):
                    raise Fail("%s is not a regular directory" % parent)
            before = regular_file(path)
            fd = os.open(path, flags | getattr(os, "O_BINARY", 0))
            opened.callback(os.close, fd)
            if not os.path.samestat(before, os.fstat(fd)):
                raise Fail("%s changed while being opened" % path)
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
            raise Fail("%s is linked or is not a regular file" % path)
        with open(fd, "rb", closefd=False) as source:
            yield source


def state_paths(project):
    check_state_folder(project)
    state = project / STATE_DIR
    for name in (PLAN, LEDGER, MAP_DATA, MAP_HTML, MAP_PDF):
        regular_file(state / name, missing_ok=name in (MAP_HTML, MAP_PDF))
    return state


def approved_map_name(version):
    if not isinstance(version, str) or not SAFE_VERSION.fullmatch(version):
        raise Fail("unsafe or missing approved plan version")
    return "approved-map-v%s.json" % version


@contextlib.contextmanager
def approved_map_state(project, state):
    """Recover interrupted copies while keeping other refreshes out of publication."""
    open_state = (project_directory_fd(project, (STATE_DIR,)) if os.open in os.supports_dir_fd
                  else contextlib.nullcontext())
    with open_state as directory:
        if directory is not None:
            fcntl.flock(directory, fcntl.LOCK_EX)
        for name in os.listdir(state if directory is None else directory):
            if not APPROVED_MAP_TEMP.fullmatch(name):
                continue
            entry = state / name if directory is None else name
            with contextlib.suppress(FileNotFoundError):
                info = os.lstat(entry, dir_fd=directory)
                if stat.S_ISREG(info.st_mode) and (directory is not None or not is_link(str(entry))):
                    os.unlink(entry, dir_fd=directory)
        yield


def read_approved_map(project, version):
    """Read the saved approval as data, using the same safe opener as the plan."""
    name = approved_map_name(version)
    try:
        regular_file(project / STATE_DIR / name)
        with project_file(project, (STATE_DIR, name)) as source:
            saved = json.load(source)
    except (OSError, ValueError, Fail) as error:
        raise Fail("approved map copy %s is missing or unreadable: %s" % (name, error)) from error
    if not isinstance(saved, dict) or saved.get("plan_version") != version:
        raise Fail("approved map copy %s has an invalid version" % name)
    return saved


def create_approved_map(project, state, name, body):
    """Publish a fully written copy without replacing a previous approval."""
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
    with contextlib.ExitStack() as opened:
        directory = None
        if os.open in os.supports_dir_fd:
            directory = opened.enter_context(project_directory_fd(project, (STATE_DIR,)))
            state = Path()
        target = state / name
        temporary = state / (".v2e-approved-%s.tmp" % uuid.uuid4().hex)
        fd = os.open(temporary, flags, 0o600, dir_fd=directory)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as destination:
                destination.write(body + "\n")
                destination.flush()
                os.fsync(destination.fileno())
            if directory is None:
                os.link(temporary, target)
            else:
                os.link(temporary, target, src_dir_fd=directory, dst_dir_fd=directory, follow_symlinks=False)
        finally:
            os.unlink(temporary, dir_fd=directory)


def record_approved_map(project, data):
    version = data["plan_version"]
    name = approved_map_name(version)
    body = json.dumps(data, sort_keys=True)
    try:
        create_approved_map(project, state_paths(project), name, body)
    except FileExistsError:
        if json.dumps(read_approved_map(project, version), sort_keys=True) != body:
            raise Fail("map data differs from its approved copy %s" % name)


def relative_path(value):
    value = required_text(value, "file path")
    pieces = value.split("/")
    if (any(piece.casefold() in ("", ".", "..", ".git") for piece in pieces)
            or "\\" in value or re.match(r"^[A-Za-z]:", value)):
        raise Fail("map file paths must be relative to the project")
    if pieces[0].casefold() == STATE_DIR and not (len(pieces) > 2 and pieces[1] == "checks"):
        raise Fail("only planned checks may be mapped inside the state folder")
    return value


def required_text(value, name):
    if not isinstance(value, str) or not value.strip() or any(not ch.isprintable() for ch in value):
        raise Fail("%s must be nonempty printable text" % name)
    return value


def required_count(value, name, minimum=1):
    if type(value) is not int or value < minimum:
        raise Fail("%s must be an integer of at least %d" % (name, minimum))
    return value


def required_rows(value, name):
    if not isinstance(value, list):
        raise Fail("%s must be a list" % name)
    return value


class SourceRange(NamedTuple):
    source: str
    start: int
    end: int
    exact: bool

    def overlaps(self, other):
        return self.source == other.source and self.start <= other.end and other.start <= self.end


def parse_old_lines(cell, sources, path):
    ranges = []
    position = 0
    while True:
        group = OLD_LINE_GROUP.match(cell, position)
        if not group:
            raise Fail("invalid old-lines format for %s" % path)
        source = group["source"]
        if source not in sources:
            raise Fail("old-lines cell names unlisted source %s for %s" % (source, path))
        for match in OLD_RANGE.finditer(group["ranges"]):
            start, end = int(match[2]), int(match[3])
            if not 1 <= start <= end <= sources[source]:
                raise Fail("old-lines range %s is outside source %s for %s" % (match[0], source, path))
            ranges.append(SourceRange(source, start, end, match[1] is None))
        position = group.end()
        if position == len(cell):
            return ranges


def merge_ranges(ranges):
    merged = []
    for item in sorted(ranges):
        if merged and merged[-1].source == item.source and item.start <= merged[-1].end + 1:
            previous = merged[-1]
            merged[-1] = previous._replace(end=max(previous.end, item.end))
        else:
            merged.append(item)
    return merged


def check_old_lines(path, cell, exact, sources, links):
    ranges = parse_old_lines(cell, sources, path)
    if exact:
        if any(not item.exact for item in ranges):
            raise Fail("exact evidence cannot use part of old-lines ranges for %s" % path)
        if merge_ranges(ranges) != merge_ranges(links):
            raise Fail("exact old-lines ranges differ from linked parts for %s" % path)
        return

    for link in links:
        if link.exact:
            if not any(item.exact and item.source == link.source and item.start <= link.start <= link.end <= item.end
                       for item in ranges):
                raise Fail("exact link needs a containing plain old-lines range for %s" % path)
        elif not any(not item.exact and link.overlaps(item) for item in ranges):
            raise Fail("inexact link needs an overlapping part of old-lines range for %s" % path)
    if any(not any(item.overlaps(link) for link in links) for item in ranges):
        raise Fail("old-lines range has no linked part for %s" % path)


def validate_map(data, plan):
    if type(data["schema"]) is not int or data["schema"] != 1:
        raise Fail("unsupported migration map schema")
    required_text(data["project"], "project name")
    version = required_text(data["plan_version"], "plan version")
    if not SAFE_VERSION.fullmatch(version):
        raise Fail("unsafe plan version: use only letters, digits, ., _, and -")
    if plan.versions != {version}:
        raise Fail("visible plan version does not match map plan_version")
    if not plan.has_new_files_table:
        raise Fail("plan is missing its new-files table")
    known_parts, sources = {}, {}
    for source in required_rows(data["sources"], "sources"):
        path = relative_path(source["path"])
        if path not in plan.paths:
            raise Fail("source path is absent from the plan: %s" % path)
        if path in sources:
            raise Fail("source path is listed more than once: %s" % path)
        total = required_count(source["lines"], "source lines")
        sources[path] = total
        parts = required_rows(source["parts"], "source parts")
        for part in parts:
            part_id = required_text(part["id"], "part id")
            if part_id in known_parts:
                raise Fail("part id is listed more than once: %s" % part_id)
            required_text(part["label"], "part label")
            start = required_count(part["from"], "range start")
            end = required_count(part["to"], "range end", minimum=start)
            known_parts[part_id] = (path, start, end)
        next_line = 1
        for part in sorted(parts, key=lambda part: part["from"]):
            if part["from"] != next_line or part["to"] > total:
                raise Fail("source parts overlap or leave a gap: %s" % path)
            next_line = part["to"] + 1
        if next_line != total + 1:
            raise Fail("source parts do not cover all lines: %s" % path)

    phases = required_rows(data["phases"], "phases")
    headings = [(required_count(phase["number"], "phase number"), required_text(phase["title"], "phase title"))
                for phase in phases]
    if not headings or headings != plan.phases or len({n for n, _ in headings}) != len(headings):
        raise Fail("map phase numbers and titles differ from the plan headings")
    used_parts, file_paths = set(), set()
    for phase in phases:
        for file in required_rows(phase["files"], "phase files"):
            path = relative_path(file["path"])
            if path not in plan.paths:
                raise Fail("mapped file path is absent from the plan: %s" % path)
            if path not in plan.new_files:
                raise Fail("mapped file is missing a plan evidence row: %s" % path)
            if path in file_paths:
                raise Fail("mapped file path is listed more than once: %s" % path)
            file_paths.add(path)
            low = required_count(file["lines_low"], "estimated lower line count", minimum=0)
            required_count(file["lines_high"], "estimated upper line count", minimum=low)
            origins = required_rows(file["from"], "file origins")
            old_lines, exact = plan.new_files[path]
            no_source = old_lines == "none"
            if no_source and (origins or not exact):
                raise Fail("new file with old lines marked none must have no source links and exact evidence: %s" % path)
            if not no_source and not origins:
                raise Fail("new file with old lines must have a source link: %s" % path)
            links = []
            for origin in origins:
                part = required_text(origin["part"], "file origin part")
                if part not in known_parts:
                    raise Fail("mapped file names an unknown part: %s" % part)
                if type(origin["exact"]) is not bool:
                    raise Fail("part exactness must be true or false")
                links.append(SourceRange(*known_parts[part], origin["exact"]))
                used_parts.add(part)
            if all(link.exact for link in links) != exact:
                raise Fail("mapped link exactness does not match plan evidence for %s" % path)
            if not no_source:
                check_old_lines(path, old_lines, exact, sources, links)
    missing_files = plan.new_files.keys() - file_paths
    if missing_files:
        raise Fail("planned new file is missing from the map: %s" % sorted(missing_files)[0])
    if used_parts != known_parts.keys():
        raise Fail("source part is unused: %s" % sorted(known_parts.keys() - used_parts)[0])


def phase_identity(phase):
    return phase["title"], {file["path"] for file in phase["files"]}


def check_completed_phases(project, phases, progress, current_version, *, earlier):
    """Tie every displayed completion to the phase approved at that event."""
    archived = {}
    for phase in phases:
        number = phase["number"]
        if progress.states[number] != "Done":
            continue
        version = progress.completions[number]
        completed_earlier = version != current_version
        if completed_earlier != earlier:
            continue
        try:
            if version not in archived:
                archived[version] = read_approved_map(project, version)
            matches = [item for item in archived[version]["phases"]
                       if type(item["number"]) is int and item["number"] == number]
            if len(matches) != 1 or phase_identity(matches[0]) != phase_identity(phase):
                raise Fail("title or file paths differ from the approved map for v%s" % version)
        except (Fail, KeyError, TypeError) as error:
            raise Fail("Phase %s cannot carry completion: %s" % (number, error)) from error


def actual_lines(project, relative):
    try:
        with project_file(project, relative.split("/")) as source:
            # Universal newlines count CRLF once, handle CR, and include a final unterminated line.
            with io.TextIOWrapper(source, encoding="latin-1", newline=None) as lines:
                return str(sum(1 for _ in lines))
    except (OSError, Fail):
        return "missing"


def theme_css():
    theme = Path.home() / STATE_DIR / "map-theme.css"
    if not os.path.lexists(theme):
        return ""
    regular_file(theme)
    css = theme.read_text(encoding="utf-8")
    if "<" in css:
        raise Fail("map theme contains a less-than sign")
    problem = render_pdf.css_problem(css)
    if problem:
        raise Fail("map theme: %s" % problem)
    return css


# Coordinates are CSS pixels. The SVG uses the exact same dimensions and row centres as the HTML.
DIAGRAM_WIDTH = 710
SOURCE_END = 198
PHASE_START = 262
DIAGRAM_BUDGET = 815
STOP_NOTICE_HEIGHT = 40
PHASE_GAP = 5
SOURCE_GAP = 6
MIN_BAR_SPACE = 32
# Columns of 12px monospace text in the source, phase header and file row.
SOURCE_COLUMNS = 27
LABEL_COLUMNS = 20
FOLDER_COLUMNS = 36
NAME_COLUMNS = 43
ROW_COLUMNS = 58
CSS = """
:root {
  --ink: #27282b; --muted: #555962; --edge: #bfc1c7; --paper: #fff;
  --wash: #f4f4f5; --segment-odd: #dedee2; --segment-even: #bfc2c9;
  --done: #e5eee8; --now: #e3e9ee; --failed: #f6e7e6;
}
@page { size: A4; margin: 0; }
* { box-sizing: border-box; }
html, body { margin: 0; print-color-adjust: exact; -webkit-print-color-adjust: exact; }
body { color: var(--ink); background: var(--paper); font: 14px/1.35 system-ui, sans-serif; }
.sheet { min-height: 1119px; padding: 30px 0 23px; display: flex; flex-direction: column; break-after: page; }
.sheet:last-child { break-after: auto; }
.frame { width: 710px; margin: 0 auto; }
.sheet-header { margin-bottom: 12px; }
h1, h2, h3, p { margin: 0; }
h1 { font-size: 29px; line-height: 34px; margin: 0 0 7px; }
.subtitle { color: var(--muted); overflow-wrap: anywhere; }
.summary { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12px; margin-top: 12px; }
.fact { border-top: 2px solid var(--edge); padding-top: 5px; overflow-wrap: anywhere; }
.fact span, .gate, .source-range, .counts { font-size: 12px; color: var(--muted); }
.fact strong { display: block; margin-top: 2px; }
.stopped { margin-top: 12px; padding: 4px 10px; border-left: 3px solid var(--ink); background: var(--failed); }
.column-labels { display: grid; grid-template-columns: 262px auto; border-bottom: 1px solid var(--edge); padding-bottom: 6px; }
.column-labels h2 { font-size: 13px; }
.diagram { position: relative; margin-top: 8px; }
.connectors { position: absolute; inset: 0; width: 100%; height: 100%; }
.source, .phase { position: absolute; }
.source { left: 0; width: 198px; }
.source h3 { font: 600 12px/16px ui-monospace, monospace; }
.source-name, .source-label, .phase-folder, .file-path, .file-folder, .file-evidence { white-space: pre; }
.phase-title { overflow-wrap: anywhere; }
.source-range { line-height: 16px; }
.source-range[title] { font-family: ui-monospace, monospace; white-space: pre; }
.source-label { position: absolute; left: 0; width: 156px; padding-left: 8px;
                font: 12px/16px ui-monospace, monospace; }
.source-label.even { border-left: 3px solid var(--segment-even); }
.source-label.odd { border-left: 3px solid var(--segment-odd); }
.segment { position: absolute; right: 0; width: 41px; background: var(--segment-odd); }
.segment.even { background: var(--segment-even); }
.phase { left: 262px; right: 0; border: 1px solid var(--edge); border-radius: 5px; background: var(--paper); }
.phase.now { border-color: var(--ink); }
.phase-head { padding: 2px 9px; display: grid; grid-template-columns: 26px minmax(0, 1fr) auto;
              column-gap: 7px; align-items: start; }
.phase h3 { font: 700 13px/16px ui-monospace, monospace; }
.phase-mark, .pill { line-height: 19px; text-align: center; background: var(--wash); border-radius: 10px; }
.phase-mark { line-height: 17px; border: 1px solid var(--edge); width: 22px; font-size: 11px; font-weight: 700; }
.pill { padding: 0 7px; font-size: 11px; font-weight: 700; }
.done .pill { background: var(--done); }
.now .pill { background: var(--now); }
.failed .pill { background: var(--failed); }
.phase-meta { grid-column: 1 / -1; display: grid; grid-template-columns: minmax(0, 1fr) auto;
              column-gap: 7px; align-items: end; }
.gate { grid-column: 2; line-height: 15px; }
.file { position: absolute; left: 0; right: 0; display: grid; grid-template-columns: minmax(0, 1fr) 107px; gap: 7px;
        row-gap: 0; align-items: start; align-content: start; padding: 0 9px;
        border-top: 1px solid var(--edge); background: var(--wash); }
.file:last-child { border-radius: 0 0 4px 4px; }
.file-path { font: 600 12px/16px ui-monospace, monospace; }
.phase-folder, .file-folder, .file-evidence { color: var(--muted); font: 12px/15px ui-monospace, monospace; }
.wide, .file-folder, .file-evidence { grid-column: 1 / -1; }
.counts { grid-column: 2; text-align: right; line-height: 15px; white-space: nowrap; }
.empty { color: var(--muted); }
.legend { display: flex; flex-wrap: wrap; gap: 10px 18px; color: var(--muted); font-size: 12px; padding: 8px 0; }
.line-key { display: inline-block; width: 24px; border-top: 2px solid var(--muted); vertical-align: middle; margin-right: 5px; }
.line-key.dashed { border-top-style: dashed; }
footer { margin-top: auto; }
.footer-row { display: flex; justify-content: space-between; border-top: 1px solid var(--edge); padding-top: 7px;
              font-size: 12px; color: var(--muted); }
"""


def escaped(value):
    return html.escape(str(value)).replace("{", "&#123;").replace("}", "&#125;")


def wrapped(value, width):
    # Reserve two columns for wide characters. HTML breaks stay in sync with connector geometry.
    if any(unicodedata.east_asian_width(character) in ("W", "F") for character in value):
        width //= 2
    lines = wrap(value, width=width, break_on_hyphens=False, replace_whitespace=False, drop_whitespace=False)
    return "<br>".join(escaped(line) for line in lines), len(lines)


def text_columns(value):
    return sum(2 if unicodedata.east_asian_width(ch) in ("W", "F") else 1
               for ch in value if not unicodedata.combining(ch))


def packed_lines(pieces, columns):
    lines, line = [], ""
    for piece in pieces:
        if line and text_columns(line + piece) > columns:
            lines.append(line)
            line = ""
        line += piece
    return lines + [line] if line else lines


def path_lines(path, columns):
    return packed_lines(re.findall(r"[^/]+/?", path), columns)


def display_lines(lines):
    return "<br>".join(escaped(line) for line in lines)


def old_range(part):
    return f'{part["from"]}–{part["to"]}'


def range_lines(links, origins):
    groups = {}
    for link in links:
        source, part = origins[link["part"]]
        prefix = "" if link["exact"] else "part of "
        groups.setdefault(source["path"], (source["lines"], []))[1].append(prefix + old_range(part))
    lines = []
    for source, (total, ranges) in groups.items():
        pieces = [item + ", " for item in ranges[:-1]] + ranges[-1:]
        if len(groups) > 1:
            pieces = re.findall(r"[^/]+/?", source) + [f" ({total:,} lines): "] + pieces
        lines.extend(packed_lines(pieces, ROW_COLUMNS))
    return lines


class MapRow(NamedTuple):
    content: str
    height: int
    links: list


class MapCard(NamedTuple):
    number: int
    state: str
    heading: str
    heading_height: int
    rows: list
    fragment: int = 1

    @property
    def height(self):
        return 2 + self.heading_height + sum(row.height for row in self.rows)


def file_layout(file, shared, actual, origins):
    path = file["path"]
    folder, slash, basename = path.rpartition("/")
    folders = path_lines(folder + slash, ROW_COLUMNS) if not shared else []
    wide = text_columns(basename) > NAME_COLUMNS
    names = packed_lines(basename, ROW_COLUMNS) if wide else [basename]
    evidence = range_lines(file["from"], origins)
    low, high = file["lines_low"], file["lines_high"]
    counts = f"~{low:,}" if low == high else f"{low:,}–{high:,}"
    count_height = 15
    if actual is not None:
        counts += "<br>Actual: " + ("missing" if actual == "missing" else f"{int(actual):,}")
        count_height *= 2
    name_height = 16 * len(names)
    height = 1 + 15 * (len(folders) + len(evidence))
    height += name_height + count_height if wide else max(name_height, count_height)
    content = (
        (f'<span class="file-folder">{display_lines(folders)}</span>' if folders else "")
        + f'<span class="file-path{" wide" if wide else ""}" title="{escaped(path)}">{display_lines(names)}</span>'
        + f'<span class="counts">{counts}</span>'
        + (f'<span class="file-evidence">{display_lines(evidence)}</span>' if evidence else "")
    )
    return MapRow(content, height, file["from"])


def phase_layout(phase, state, actual, origins):
    number = phase["number"]
    title, title_lines = wrapped(phase["title"], 42)
    parents = {file["path"].rpartition("/")[0] for file in phase["files"]}
    shared = next(iter(parents)) if len(parents) == 1 else ""
    folders = path_lines(shared + "/", FOLDER_COLUMNS) if shared else []
    wide = any(text_columns(line) > FOLDER_COLUMNS for line in folders)
    if wide:
        folders = path_lines(shared + "/", ROW_COLUMNS)
    folder_html = (f'<span class="phase-folder{" wide" if wide else ""}">{display_lines(folders)}</span>'
                   if folders else "")
    mark = {"Done": "✓", "Failed": "!"}.get(state, str(number))
    heading = (f'<div class="phase-head"><span class="phase-mark">{mark}</span>'
               f'<h3 class="phase-title">{title}</h3><span class="pill">{state}</span>'
               f'<div class="phase-meta">{folder_html}<p class="gate">then stop for your approval</p></div></div>')
    meta_lines = len(folders) + 1 if wide else max(1, len(folders))
    heading_height = 4 + max(19, 16 * title_lines) + 15 * meta_lines
    rows = [file_layout(file, shared, actual[file["path"]] if state == "Done" else None, origins)
            for file in phase["files"]]
    return MapCard(number, state, heading, heading_height, rows)


def source_headings(sources, destinations, origins, budget):
    headings = {}
    for source in sources:
        path = source["path"]
        name = path_lines(path, SOURCE_COLUMNS)
        content = (f'<h3 class="source-name">{display_lines(name)}</h3>'
                   f'<p class="source-range">{source["lines"]:,} lines today</p>')
        headings[path] = (16 * (len(name) + 1) + 2, content)
    gap_space = SOURCE_GAP * (len(sources) - 1)
    if sum(height for height, _ in headings.values()) + gap_space + MIN_BAR_SPACE <= budget:
        return headings, SOURCE_GAP

    # Reserve one line first for sources referenced alone. Mixed-source rows also name their sources and totals.
    solo = set()
    for _, links in destinations:
        paths = {origins[link["part"]][0]["path"] for link in links}
        if len(paths) == 1:
            solo.update(paths)
    capacity = (budget - MIN_BAR_SPACE) // 16
    compact = {}
    for source in sorted(sources, key=lambda source: source["path"] not in solo)[:capacity]:
        path = source["path"]
        count = f'{source["lines"]:,} lines'
        caption = f'{path.rsplit("/", 1)[-1]} · {count}'
        if text_columns(caption) > SOURCE_COLUMNS:
            caption = count + " today"
        compact[path] = (16, f'<p class="source-range" title="{escaped(path)}">{escaped(caption)}</p>')
    return compact, 0


def source_layout(sources, destinations, origins, phase_height, budget):
    used = {link["part"] for _, links in destinations for link in links}
    visible = [source for source in sources if any(part["id"] in used for part in source["parts"])]
    height = max(phase_height, 60)
    if not visible:
        return '<p class="source empty">No source ranges.</p>', {}, height

    # Source headings can use spare space on the sheet. Only phase cards select the pages.
    headings, gap = source_headings(visible, destinations, origins, budget)
    reserved = sum(height for height, _ in headings.values()) + gap * (len(visible) - 1)
    height = max(height, reserved + MIN_BAR_SPACE)
    scale = (height - reserved) / sum(source["lines"] for source in visible)
    drawings, anchors, top = [], {}, 0
    for source in visible:
        bar_top, heading = headings.get(source["path"], (0, ""))
        bar_height = source["lines"] * scale
        drawings.append(f'<div class="source" style="top:{top:.4f}px">{heading}')
        for index, part in enumerate(sorted(source["parts"], key=lambda part: part["from"])):
            if part["id"] not in used:
                continue
            part_height = (part["to"] - part["from"] + 1) * scale
            part_top = bar_top + (part["from"] - 1) * scale
            anchors[part["id"]] = top + part_top + part_height / 2
            tint = "even" if index % 2 == 0 else "odd"
            drawings.append(f'<div class="segment {tint}" style="top:{part_top:.4f}px;height:{part_height:.4f}px"></div>')
            title = packed_lines(re.findall(r"\S+\s*", part["label"]), LABEL_COLUMNS)
            label_height = 16 * (len(title) + 1)
            if label_height + 2 <= part_height and all(text_columns(line) <= LABEL_COLUMNS for line in title):
                label_top = part_top + (part_height - label_height) / 2
                drawings.append(f'<div class="source-label {tint}" style="top:{label_top:.4f}px">'
                                f'<b>{display_lines(title)}</b><br>'
                                f'<span class="source-range">{old_range(part)}</span></div>')
        drawings.append("</div>")
        top += bar_top + bar_height + gap
    return "".join(drawings), anchors, height


def connector_image(destinations, anchors, height):
    paths = []
    for target, links in destinations:
        for origin in links:
            start = anchors[origin["part"]]
            pattern = '' if origin["exact"] else ' stroke-dasharray="4 3"'
            paths.append(f'<path d="M{SOURCE_END - 1} {start:.2f} C225 {start:.2f} 235 {target:.2f} '
                         f'{PHASE_START + 1} {target:.2f}" fill="none" stroke="rgb(85,89,98)" '
                         f'stroke-width="1.35"{pattern}/>')
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {DIAGRAM_WIDTH} {height}">'
           + "".join(paths) + "</svg>")
    encoded = base64.b64encode(svg.encode("ascii")).decode("ascii")
    return f'<img class="connectors" src="data:image/svg+xml;base64,{encoded}" alt="">'


def diagram(sources, cards, origins, budget):
    drawings, destinations, top = [], [], 0
    for card in cards:
        suffix = f"-part-{card.fragment}" if card.fragment > 1 else ""
        drawings.append(f'<article id="phase-{card.number}{suffix}" class="phase {card.state.lower()}" '
                        f'style="top:{top}px;height:{card.height}px">{card.heading}')
        position = card.heading_height
        for row in card.rows:
            drawings.append(f'<div class="file" style="top:{position}px;height:{row.height}px">'
                            f'{row.content}</div>')
            destinations.append((top + 1 + position + row.height / 2, row.links))
            position += row.height
        drawings.append("</article>")
        top += card.height + PHASE_GAP
    parts, anchors, height = source_layout(sources, destinations, origins, top - PHASE_GAP, budget)
    image = connector_image(destinations, anchors, height)
    return f'<div class="diagram" style="height:{height}px">{image}{parts}{"".join(drawings)}</div>'


def card_fragments(card, budget):
    rows, height, fragment = [], 2 + card.heading_height, 1
    for row in card.rows:
        if rows and height + row.height > budget:
            yield card._replace(rows=rows, fragment=fragment)
            rows, height, fragment = [], 2 + card.heading_height, fragment + 1
        rows.append(row)
        height += row.height
    yield card._replace(rows=rows, fragment=fragment)


def diagrams(data, states, actual, budget):
    sources = data["sources"]
    origins = {part["id"]: (source, part) for source in sources for part in source["parts"]}
    pages, current, used_height = [], [], 0
    for phase in data["phases"]:
        card = phase_layout(phase, states[phase["number"]], actual, origins)
        if current and used_height + PHASE_GAP + card.height > budget:
            pages.append(diagram(sources, current, origins, budget))
            current, used_height = [], 0
        if card.height > budget:
            fragments = list(card_fragments(card, budget))
            pages.extend(diagram(sources, [fragment], origins, budget) for fragment in fragments[:-1])
            card = fragments[-1]
        used_height += (PHASE_GAP if current else 0) + card.height
        current.append(card)
    pages.append(diagram(sources, current, origins, budget))
    return pages


def summary(data, progress):
    states = progress.states
    current = next((n for n, state in states.items() if state in ("Now", "Failed")), None)
    waiting = next((n for n, state in states.items() if state == "Waiting"), None)
    if progress.outcome:
        status, gate = progress.outcome, "None"
    elif progress.stopped:
        status, gate = "Stopped", "Migration stopped"
    elif current and states[current] == "Failed":
        status, gate = "Failed", "Owner decision"
    elif current:
        status, gate = "In progress", "Owner approval"
    elif progress.plan_only:
        status, gate = "Plan only", "Disposable copy required"
    elif progress.restored and waiting:
        status, gate = "Restored", "Phase %s retry approval" % waiting
    elif waiting:
        status = "Waiting"
        gate = ("Phase %s approval" % waiting
                if progress.started or waiting != data["phases"][0]["number"] else "Prepare baseline")
    else:
        status, gate = "Phases complete", "Final review"
    count = sum(len(phase["files"]) for phase in data["phases"] if states[phase["number"]] == "Done")
    total = sum(len(phase["files"]) for phase in data["phases"])
    facts = (("Status", status), ("Current phase", "Phase %s" % current if current and not progress.outcome else "—"),
             ("New files done", "%s of %s" % (count, total)), ("Next stop", gate))
    return '<div class="summary">' + "".join(f'<div class="fact"><span>{label}</span><strong>{value}</strong></div>'
                                                for label, value in facts) + "</div>"


def map_html(data, progress, actual, theme):
    stopped = progress.stopped and not progress.outcome
    budget = DIAGRAM_BUDGET - (STOP_NOTICE_HEIGHT if stopped else 0)
    pages = diagrams(data, progress.states, actual, budget)
    header = ('<header class="sheet-header"><h1>Migration Map</h1><p class="subtitle">'
              f'{escaped(data["project"])} · Plan v{escaped(data["plan_version"])}</p>'
              + summary(data, progress)
              + ('<p class="stopped"><strong>Stopped</strong></p>'
                 if stopped else '') + '</header>')
    names = '<div class="column-labels"><h2>Source files</h2><h2>Migration phases</h2></div>'
    legend = ('<div class="legend"><span><i class="line-key"></i>Exact source range</span>'
              '<span><i class="line-key dashed"></i>Source range not yet exact</span>'
              '<span>Planned lines are estimates</span></div>')
    sheets = []
    for index, content in enumerate(pages, 1):
        sheets.append(f'<section class="sheet"><main class="frame">'
                      f'{header}{names}{content}{legend}</main><footer class="frame">'
                      f'<div class="footer-row"><span>Migration Map</span><span>Page {index} of {len(pages)}</span></div>'
                      '</footer></section>')
    return ('<!DOCTYPE html>\n<html lang="en"><head><meta charset="utf-8"><title>Migration Map</title><style>'
            + CSS + "\n" + theme + "\n</style></head><body>\n"
            + "\n".join(sheets) + "\n</body></html>\n")


def render_project(project, names=None):
    state = state_paths(project)
    inputs = {}
    for name in (PLAN, LEDGER, MAP_DATA):
        with project_file(project, (STATE_DIR, name)) as source:
            inputs[name] = source.read()
    try:
        data = json.loads(inputs[MAP_DATA].decode("utf-8"))
        if names:
            names.check_html(inputs[PLAN].decode("utf-8"))
            names.check_values(data)
            names.check_text(inputs[LEDGER].decode("utf-8"))
        plan = PlanEntries(inputs[PLAN].decode("utf-8"))
        validate_map(data, plan)
        fingerprint = git(["hash-object", "--no-filters", "--stdin"], cwd=project,
                          stdin=inputs[PLAN]).stdout.decode("ascii").strip()
        if data["plan_fingerprint"] != fingerprint:
            raise Fail("plan fingerprint does not match the current plan HTML")
    except (KeyError, TypeError) as error:
        raise Fail("invalid migration-map.json structure: %s" % error) from error
    progress = phase_states(
        inputs[LEDGER].decode("utf-8"), data["plan_version"], fingerprint,
        (phase["number"] for phase in data["phases"]),
    )
    if not progress.started:
        for source in data["sources"]:
            path = source["path"]
            measured = actual_lines(project, names.disk_path(project, path) if names else path)
            if measured != str(source["lines"]):
                raise Fail("source line count differs from the map for %s (measured: %s)" % (path, measured))
    phases, version = data["phases"], data["plan_version"]
    with approved_map_state(project, state):
        check_completed_phases(project, phases, progress, version, earlier=True)
        record_approved_map(project, data)
        check_completed_phases(project, phases, progress, version, earlier=False)
    theme = theme_css()
    actual = {file["path"]: actual_lines(project, names.disk_path(project, file["path"]) if names else file["path"])
              for phase in data["phases"] if progress.states[phase["number"]] == "Done" for file in phase["files"]}
    document = map_html(data, progress, actual, theme)
    if names:
        names.check_html(document)
    problems = render_pdf.static_problems(document)
    if render_pdf.PLACEHOLDER.search(document) or problems:
        raise Fail("map is not static and self-contained: %s" % (", ".join(problems) or "unfilled placeholder"))
    with tempfile.TemporaryDirectory(prefix=".v2e-map-", dir=state) as scratch:
        draft_html, draft_pdf = Path(scratch) / MAP_HTML, Path(scratch) / MAP_PDF
        draft_html.write_text(document, encoding="utf-8")
        code = render_pdf.main(["render_pdf.py", str(draft_html), str(draft_pdf)])
        if code:
            return code
        state_paths(project)
        os.replace(draft_pdf, state / MAP_PDF)
        os.replace(draft_html, state / MAP_HTML)
    print("wrote %s and %s" % (state / MAP_HTML, state / MAP_PDF))
    return 0


def main(argv):
    confidential = False
    try:
        require_supported_platform()
        parser = argparse.ArgumentParser(description=__doc__)
        parser.add_argument("--project", required=True)
        parser.add_argument("--name-map", help="absolute path to the owner-held confidential name map")
        options = parser.parse_args(argv[1:])
        confidential = options.name_map is not None
        project = resolve_project(options.project)
        names = load_name_map(options.name_map, project)
        if names:
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                code = render_project(project, names)
            print("Confidential map written." if code == 0 else "Confidential map printing failed.")
            return code
        return render_project(project)
    except (Fail, PlatformRefusal, OSError, UnicodeError, ValueError, OverflowError) as error:
        if confidential:
            error = "confidential map refused; check the name map, plan and ledger"
        print("render_map.py: error: %s" % error, file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
