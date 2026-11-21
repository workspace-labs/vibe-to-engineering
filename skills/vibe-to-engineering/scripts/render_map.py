#!/usr/bin/env python3
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
from html.parser import HTMLParser
from pathlib import Path
from textwrap import wrap

import render_pdf
from checkpoint import STATE_DIR, check_state_folder, resolve_project
from gitrun import Fail, git, is_link
from platformgate import PlatformRefusal, require_supported_platform

PLAN = "Engineering-Migration-Plan.html"
LEDGER = "ledger.md"
MAP_DATA = "migration-map.json"
MAP_HTML = "Migration-Map.html"
MAP_PDF = "Migration-Map.pdf"
PHASE_HEADING = re.compile(r"Phase ([1-9]\d*)\s*—\s*(.+)\Z")
PHASE_EVENT = re.compile(r"PHASE ([1-9]\d*) (STARTED|COMPLETE|FAILED)\Z")
PHASE_RESTORE = re.compile(r"(?:r[1-9]\d*-)?\d{2,}-phase-([1-9]\d*)\Z")
BASELINE_RESTORE = re.compile(r"(?:r[1-9]\d*-)?00-baseline(?:-checked)?\Z")
EVENT_STATE = {"STARTED": "Now", "COMPLETE": "Done", "FAILED": "Failed"}


class PlanEntries(HTMLParser):
    """Read visible phase headings and whole path cells from the plan form."""

    def __init__(self, plan):
        super().__init__(convert_charrefs=True)
        self.phases, self.paths = [], set()
        self.kind, self.pieces, self.badge = None, [], False
        self.feed(plan)
        self.close()

    def handle_starttag(self, tag, attrs):
        classes = (dict(attrs).get("class") or "").split()
        if (tag == "td" and "path" in classes) or tag == "h3":
            self.kind, self.pieces = tag, []
        if self.kind == "h3" and tag == "span" and "badge" in classes:
            self.badge = True

    def handle_endtag(self, tag):
        if tag == "span":
            self.badge = False
        if tag != self.kind:
            return
        entry = "".join(self.pieces).strip()
        if tag == "td":
            self.paths.add(entry)
        else:
            match = PHASE_HEADING.fullmatch(entry)
            if match:
                self.phases.append((int(match[1]), match[2]))
        self.kind = None

    def handle_data(self, text):
        if self.kind and not self.badge:
            self.pieces.append(text)


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
def project_file(project, parts):
    """Open a regular, unlinked file under project without following any link on macOS."""
    path = project.joinpath(*parts)
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
    with contextlib.ExitStack() as opened:
        if os.open in os.supports_dir_fd:
            # Open each component against its verified parent, including the resolved project root.
            directory_flags = flags | os.O_DIRECTORY
            directory = os.open(project.anchor, directory_flags)
            opened.callback(os.close, directory)
            for piece in (*project.parts[1:], *parts[:-1]):
                directory = os.open(piece, directory_flags, dir_fd=directory)
                opened.callback(os.close, directory)
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


def validate_map(data, plan):
    if type(data["schema"]) is not int or data["schema"] != 1:
        raise Fail("unsupported migration map schema")
    required_text(data["project"], "project name")
    version = required_text(data["plan_version"], "plan version")
    if re.search(r"\s", version):
        raise Fail("plan version must be a single value")
    known_parts, sources = set(), set()
    for source in required_rows(data["sources"], "sources"):
        path = relative_path(source["path"])
        if path in sources:
            raise Fail("source path is listed more than once: %s" % path)
        sources.add(path)
        total = required_count(source["lines"], "source lines")
        parts = required_rows(source["parts"], "source parts")
        for part in parts:
            part_id = required_text(part["id"], "part id")
            if part_id in known_parts:
                raise Fail("part id is listed more than once: %s" % part_id)
            known_parts.add(part_id)
            required_text(part["label"], "part label")
            required_count(part["from"], "range start")
            required_count(part["to"], "range end", minimum=part["from"])
        parts.sort(key=lambda part: part["from"])
        next_line = 1
        for part in parts:
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
            if path in file_paths:
                raise Fail("mapped file path is listed more than once: %s" % path)
            file_paths.add(path)
            low = required_count(file["lines_low"], "estimated lower line count", minimum=0)
            required_count(file["lines_high"], "estimated upper line count", minimum=low)
            for origin in required_rows(file["from"], "file origins"):
                part = required_text(origin["part"], "file origin part")
                if part not in known_parts:
                    raise Fail("mapped file names an unknown part: %s" % part)
                if type(origin["exact"]) is not bool:
                    raise Fail("part exactness must be true or false")
                used_parts.add(part)
    if used_parts != known_parts:
        raise Fail("source part is unused: %s" % sorted(known_parts - used_parts)[0])


def ledger_headings(ledger):
    fence = None
    for line in ledger.splitlines():
        start = re.match(r"^ {0,3}(`{3,}|~{3,})(.*)", line)
        if start:
            mark, rest = start.groups()
            if fence is None:
                fence = mark
            elif mark.startswith(fence) and not rest.strip():
                fence = None
            continue
        heading = re.match(r"^ {0,3}##[ \t]+(.+?)\s*$", line)
        if not fence and heading:
            fields = heading[1].split(" — ", 2)
            if len(fields) == 3:
                yield fields[1], fields[2]
            elif len(fields) == 1:
                yield fields[0], ""


def phase_states(ledger, version, numbers):
    events = list(ledger_headings(ledger))
    approval = "PLAN APPROVED v" + version
    last = next((i for i in range(len(events) - 1, -1, -1) if events[i][0] == approval), None)
    if last is None:
        raise Fail("ledger has no %s heading" % approval)
    states = dict.fromkeys(numbers, "Waiting")
    stopped = restored = False
    plan_only = events[last][1] == "PLAN ONLY"
    for event, _ in events[last + 1:]:
        phase = PHASE_EVENT.fullmatch(event)
        if phase:
            number = int(phase[1])
            if number not in states:
                raise Fail("ledger event names a phase absent from the plan: %s" % number)
            states[number] = EVENT_STATE[phase[2]]
            plan_only = False
            restored = False
        elif event == "MIGRATION STOPPED":
            stopped = True
        elif event == "RESTORED" or event.startswith("RESTORED "):
            label = event[len("RESTORED "):]
            saved_phase = PHASE_RESTORE.fullmatch(label)
            if BASELINE_RESTORE.fullmatch(label):
                cutoff = 0
            elif saved_phase:
                cutoff = int(saved_phase[1])
            else:
                raise Fail("unknown restore label: %s" % label)
            for number in states:
                if number > cutoff:
                    states[number] = "Waiting"
            plan_only = False
            restored = True
    return states, stopped, plan_only, restored


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
DIAGRAM_BUDGET = 805
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
.sheet-header { margin-bottom: 18px; }
h1, h2, h3, p { margin: 0; }
h1 { font-size: 29px; line-height: 34px; margin: 0 0 7px; }
.subtitle { color: var(--muted); overflow-wrap: anywhere; }
.summary { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12px; margin-top: 15px; }
.fact { border-top: 2px solid var(--edge); padding-top: 5px; overflow-wrap: anywhere; }
.fact span, .gate, .source-range, .counts { font-size: 12px; color: var(--muted); }
.fact strong { display: block; margin-top: 2px; }
.stopped { margin-top: 12px; padding: 4px 10px; border-left: 3px solid var(--ink); background: var(--failed); }
.column-labels { display: grid; grid-template-columns: 262px auto; border-bottom: 1px solid var(--edge); padding-bottom: 6px; }
.column-labels h2 { font-size: 13px; }
.diagram { position: relative; margin-top: 11px; }
.connectors { position: absolute; inset: 0; width: 100%; height: 100%; }
.source, .phase { position: absolute; }
.source { left: 0; width: 198px; }
.source h3 { font: 600 12px/16px ui-monospace, monospace; }
.source-name, .source-label, .phase-title, .file-path { overflow-wrap: anywhere; }
.source-label { position: absolute; left: 0; width: 143px; padding-left: 8px;
                font: 12px/16px ui-monospace, monospace; }
.source-label.even { border-left: 3px solid var(--segment-even); }
.source-label.odd { border-left: 3px solid var(--segment-odd); }
.segment { position: absolute; right: 0; width: 41px; background: var(--segment-odd); }
.segment.even { background: var(--segment-even); }
.phase { left: 262px; right: 0; border: 1px solid var(--edge); border-radius: 5px; background: var(--paper); }
.phase.now { border-color: var(--ink); }
.phase-head { padding: 6px 9px; display: grid; grid-template-columns: 26px minmax(0, 1fr) auto; gap: 7px; align-items: start; }
.phase h3 { font: 700 13px/16px ui-monospace, monospace; }
.phase-mark, .pill { line-height: 19px; text-align: center; background: var(--wash); border-radius: 10px; }
.phase-mark { border: 1px solid var(--edge); width: 22px; font-size: 11px; font-weight: 700; }
.pill { padding: 0 7px; font-size: 11px; font-weight: 700; }
.done .pill { background: var(--done); }
.now .pill { background: var(--now); }
.failed .pill { background: var(--failed); }
.gate { line-height: 15px; margin-top: 1px; }
.file { position: absolute; left: 0; right: 0; display: grid; grid-template-columns: minmax(0, 1fr) 107px; gap: 7px;
        align-items: center; padding: 2px 9px; border-top: 1px solid var(--edge); background: var(--wash); }
.file:last-child { border-radius: 0 0 4px 4px; }
.file-path { font: 600 12px/16px ui-monospace, monospace; }
.counts { text-align: right; line-height: 15px; overflow-wrap: anywhere; }
.empty { color: var(--muted); }
.legend { display: flex; flex-wrap: wrap; gap: 10px 18px; color: var(--muted); font-size: 12px; padding: 12px 0; }
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


def phase_layout(phases, states, actual):
    cards, destinations, top = [], [], 0
    for phase in phases:
        number = phase["number"]
        state = states[number]
        title, title_lines = wrapped(phase["title"], 42)
        position = max(43, 30 + 16 * title_lines)
        files = []
        for file in phase["files"]:
            path, path_lines = wrapped(file["path"], 40)
            height = max(32, 7 + 16 * path_lines, 37 if state == "Done" else 0)
            planned = "%s–%s" % (file["lines_low"], file["lines_high"])
            count = "<br>Actual: " + actual[file["path"]] if state == "Done" else ""
            files.append(f'<div class="file" style="top:{position}px;height:{height}px">'
                         f'<span class="file-path">{path}</span><span class="counts">{planned}{count}</span></div>')
            destinations.append((top + position + height / 2, file["from"]))
            position += height
        mark = {"Done": "✓", "Failed": "!"}.get(state, str(number))
        cards.append(f'<article id="phase-{number}" class="phase {state.lower()}" '
                     f'style="top:{top}px;height:{position + 1}px"><div class="phase-head">'
                     f'<span class="phase-mark">{mark}</span><div><h3 class="phase-title">{title}</h3>'
                     f'<p class="gate">then stop for your approval</p></div><span class="pill">{state}</span></div>'
                     + "".join(files) + "</article>")
        top += position + 11
    return "".join(cards), destinations, top - 10


def source_layout(sources, destinations, phase_height):
    used = {link["part"] for _, links in destinations for link in links}
    visible = [source for source in sources if any(part["id"] in used for part in source["parts"])]
    if not visible:
        return '<p class="empty">No source ranges mapped to these phases.</p>', {}, 0
    # One scale across sources on this page, with separate labels that keep even short ranges legible.
    total = sum(source["lines"] for source in visible)
    available = max(100, min(610, phase_height - 55 * len(visible)))
    drawings, anchors, top = [], {}, 0
    for source in visible:
        name, name_lines = wrapped(source["path"], 25)
        bar_top = 18 + 16 * name_lines
        bar_height = (source["lines"] / total) * available
        drawings.append(f'<div class="source" style="top:{top}px"><h3 class="source-name">{name}</h3>'
                        f'<p class="source-range">{source["lines"]} lines today</p>')
        label_top = bar_top
        for index, part in enumerate(source["parts"]):
            part_height = ((part["to"] - part["from"] + 1) / source["lines"]) * bar_height
            part_top = bar_top + ((part["from"] - 1) / source["lines"]) * bar_height
            anchors[part["id"]] = top + part_top + part_height / 2
            tint = "even" if index % 2 == 0 else "odd"
            title, title_lines = wrapped(part["label"], 18)
            label_height = 16 * (title_lines + 1)
            label_top = max(label_top, min(part_top + (part_height - label_height) / 2,
                                           bar_top + bar_height - label_height))
            drawings.append(f'<div class="segment {tint}" style="top:{part_top:.4f}px;height:{part_height:.4f}px"></div>'
                            f'<div class="source-label {tint}" style="top:{label_top:.4f}px"><b>{title}</b><br>'
                            f'<span class="source-range">{part["from"]}–{part["to"]}</span></div>')
            label_top += label_height + 3
        drawings.append("</div>")
        top += max(bar_top + bar_height, label_top) + 16
    return "".join(drawings), anchors, int(top + 0.999)


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


def diagram(sources, phases, states, actual):
    cards, destinations, phase_height = phase_layout(phases, states, actual)
    drawings, anchors, source_height = source_layout(sources, destinations, phase_height)
    height = max(phase_height, source_height, 60)
    image = connector_image(destinations, anchors, height)
    return height, f'<div class="diagram" style="height:{height}px">{image}{drawings}{cards}</div>'


def diagrams(data, states, actual):
    pages, current = [], []
    for phase in data["phases"]:
        candidate = diagram(data["sources"], current + [phase], states, actual)
        if candidate[0] > DIAGRAM_BUDGET and current:
            pages.append(diagram(data["sources"], current, states, actual))
            current = []
        current.append(phase)
    pages.append(diagram(data["sources"], current, states, actual))
    return pages


def summary(data, states, stopped, plan_only, restored):
    current = next((n for n, state in states.items() if state in ("Now", "Failed")), None)
    waiting = next((n for n, state in states.items() if state == "Waiting"), None)
    if stopped:
        status, gate = "Stopped", "Migration stopped"
    elif current and states[current] == "Failed":
        status, gate = "Failed", "Owner decision"
    elif current:
        status, gate = "In progress", "Owner approval"
    elif plan_only:
        status, gate = "Plan only", "Disposable copy required"
    elif restored and waiting:
        status, gate = "Restored", "Phase %s retry approval" % waiting
    elif waiting:
        status, gate = "Waiting", "Phase %s approval" % waiting if waiting != data["phases"][0]["number"] else "Prepare baseline"
    else:
        status, gate = "Phases complete", "Final review"
    count = sum(len(phase["files"]) for phase in data["phases"] if states[phase["number"]] == "Done")
    total = sum(len(phase["files"]) for phase in data["phases"])
    facts = (("Status", status), ("Current phase", "Phase %s" % current if current else "—"),
             ("New files done", "%s of %s" % (count, total)), ("Next stop", gate))
    return '<div class="summary">' + "".join(f'<div class="fact"><span>{label}</span><strong>{value}</strong></div>'
                                                for label, value in facts) + "</div>"


def map_html(data, states, stopped, plan_only, restored, actual, theme):
    pages = diagrams(data, states, actual)
    header = ('<header class="sheet-header"><h1>Migration Map</h1><p class="subtitle">'
              f'{escaped(data["project"])} · Plan v{escaped(data["plan_version"])}</p>'
              + summary(data, states, stopped, plan_only, restored)
              + ('<p class="stopped"><strong>Stopped</strong></p>' if stopped else '') + '</header>')
    names = '<div class="column-labels"><h2>Source files</h2><h2>Migration phases</h2></div>'
    legend = ('<div class="legend"><span><i class="line-key"></i>Exact source range</span>'
              '<span><i class="line-key dashed"></i>Source range not yet exact</span>'
              '<span>Planned lines are estimates</span></div>')
    sheets, print_sizes = [], []
    for index, (height, content) in enumerate(pages, 1):
        size_class = ""
        if height > DIAGRAM_BUDGET:
            # Preserve a single oversized phase as one longer sheet, without slicing its rows or reducing text.
            size_class = f" long-{index}"
            print_sizes.append(f'@page extended-{index} {{ size: 210mm {height + 314}px; }} '
                               f'.long-{index} {{ page: extended-{index}; min-height: {height + 311}px; }}')
        sheets.append(f'<section class="sheet{size_class}"><main class="frame">'
                      f'{header}{names}{content}{legend}</main><footer class="frame">'
                      f'<div class="footer-row"><span>Migration Map</span><span>Page {index} of {len(pages)}</span></div>'
                      '</footer></section>')
    return ('<!DOCTYPE html>\n<html lang="en"><head><meta charset="utf-8"><title>Migration Map</title><style>'
            + CSS + "\n" + "\n".join(print_sizes) + "\n" + theme + "\n</style></head><body>\n"
            + "\n".join(sheets) + "\n</body></html>\n")


def render_project(project):
    state = state_paths(project)
    inputs = {}
    for name in (PLAN, LEDGER, MAP_DATA):
        with project_file(project, (STATE_DIR, name)) as source:
            inputs[name] = source.read()
    try:
        data = json.loads(inputs[MAP_DATA].decode("utf-8"))
        plan = PlanEntries(inputs[PLAN].decode("utf-8"))
        validate_map(data, plan)
        fingerprint = git(["hash-object", "--no-filters", "--stdin"], cwd=project,
                          stdin=inputs[PLAN]).stdout.decode("ascii").strip()
        if data["plan_fingerprint"] != fingerprint:
            raise Fail("plan fingerprint does not match the current plan HTML")
    except (KeyError, TypeError) as error:
        raise Fail("invalid migration-map.json structure: %s" % error) from error
    states, stopped, plan_only, restored = phase_states(
        inputs[LEDGER].decode("utf-8"), data["plan_version"], (phase["number"] for phase in data["phases"]),
    )
    theme = theme_css()
    actual = {file["path"]: actual_lines(project, file["path"])
              for phase in data["phases"] if states[phase["number"]] == "Done" for file in phase["files"]}
    document = map_html(data, states, stopped, plan_only, restored, actual, theme)
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
    try:
        require_supported_platform()
        parser = argparse.ArgumentParser(description=__doc__)
        parser.add_argument("--project", required=True)
        options = parser.parse_args(argv[1:])
        return render_project(resolve_project(options.project))
    except (Fail, PlatformRefusal, OSError, UnicodeError, ValueError, OverflowError) as error:
        print("render_map.py: error: %s" % error, file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
