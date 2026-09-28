"""The v0.1 literal .env boundary (release decision A1, owner-approved 2026-09-27): which .env files may reach a
check at all, and what each admitted line means. Standard library only.

The boundary replaces reader modeling with a positive grammar: a recognized .env file is admitted only when every
claimed reader reads every line the same way, proven by the reader-compatibility experiment of 2026-09-27 (107
readers — bash 3.2 as /bin/sh, Node --env-file v20.7.0, v20.20.2, v22.0.0, v22.16.0, v24.21.0, v26.10.0, all 99
stable npm dotenv releases, python-dotenv 1.2.3 — over 83 fixtures, the evidence bundle beside the project's
handoff) and re-proven by the in-suite differential matrix (tests/test_literal_matrix.py) over the claimed range.
Anything else refuses before launch (exit 2, nothing runs, no evidence) — the guiding rule: every claimed reader
reads admitted bytes literally, or the file refuses.

The grammar, exactly as approved:

File: UTF-8, LF-only (a carriage return anywhere refuses), no byte order mark.
Line: blank (spaces and tabs only) · a comment ('#', after optional leading spaces or tabs) · one assignment.
Assignment: optional leading spaces · an optional single 'export ' prefix · NAME immediately '=' — a NAME is
[A-Za-z_][A-Za-z0-9_]*, no spaces around the '=', each name assigned at most once per file — then one VALUE:
  empty        A=   A=''   A=""
  unquoted     one or more characters only from A-Z a-z 0-9 and  ! % * + , - . / : = ? @ [ ] ^ _  — with '~'
               additionally allowed except at the value's start or immediately after a ':' — then optional
               trailing spaces or tabs (every claimed reader strips them; proven by fixture 05)
  single-quoted  '…' on one line: no ''', no '$' or backtick, no consecutive backslashes, no control character
               except a literal tab, no
               leading or trailing Unicode whitespace (including U+FEFF) inside the quotes; nothing after the closing quote
  double-quoted  "…" on one line: also no '\\'; the same otherwise

A1 corrective note (2026-09-28): single-quoted backslash pairs refuse because python-dotenv collapses them;
Unicode Cc controls except TAB and Unicode whitespace/U+FEFF at quoted edges refuse.

Refused (each grounded in the experiment's demonstrated divergence or execution): a '$' or backtick anywhere in a
value (interpolation, command substitution — even inside single quotes, dotenv 0.3–1.2), an unquoted '#' (cut vs
keep), spaces around '=', interior whitespace or any other byte in an unquoted value, '{' or '}' unquoted (bash
brace expansion — Codex's reproduced case: export A=x{a,b} reads xb under bash; the combination, never the isolated
character, is the operator), '~' at a value's start or after ':' (bash expands through the account database),
a duplicate name (dotenv 0.1.1 first-wins), a quote never closed or text after it, a line break inside quotes,
whitespace at a quoted value's edge (dotenv 0.2.5–6.2.0 trim inside quotes), a control character other than a
literal tab inside quotes (kept out for output-channel hygiene; stricter than the evidence requires), CRLF (bash
keeps the '\\r'), a BOM, a bare line, and anything else not matching the above.

Deliberately stricter than the evidence, recorded: a non-ASCII character is admitted only inside quotes (the
unquoted set is the probed ASCII set, although the UTF-8 probe read café unanimously); a tab before a name (only
spaces were probed); whitespace after a closing quote (unprobed); control bytes inside quotes beyond the tab
(probed unanimous-literal, refused anyway for output-channel hygiene). Comment text is unrestricted: no claimed
reader in range reads it (dotenv 0.1.1–0.2.0, which read a comment's text before an '=', are outside the claimed
range).

The claimed npm dotenv range is 0.4.0–18.0.4: 0.1.1–0.2.0 truncate a value at its second '=', and 0.1.1–0.3.0
strip quote characters anywhere in a value — both diverge from every other claimed reader on legitimate literal
values. Recorded limitation inside the range: 0.5.0 fails with empty environment state when .env.<NODE_ENV> is
absent (its load() applies values only when both .env and the env-specific file load, so nothing is applied)
and decodes normally in its two-file setup; a fail-closed read, never a wrong one.
"""

import re
import unicodedata

NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
ASSIGNMENT = re.compile(r"^ *(?:export )?([A-Za-z_][A-Za-z0-9_]*)=(.*)$")   # no spaces around '=', one 'export '
UNQUOTED = re.compile(r"^([A-Za-z0-9!%*+,./:=?@\[\]^_~-]*?)([ \t]*)$")   # the probed set; braces were removed


class NotLiteral(ValueError):
    """A .env file outside the literal boundary: `line` (1-based; 0 when the file as a whole is meant) and the
    construct that is refused — never the file's text. evidence.py stops the run before the check for it."""

    def __init__(self, line, reason):
        super().__init__(reason if not line else "line %d: %s" % (line, reason))
        self.line, self.reason = line, reason


def quoted(line, rest, mark):
    """The decode of a quoted value: rest must be exactly mark…mark on this line — nothing after the closing quote
    (unprobed) — with no interpolator ('$' or backtick, refused even here: dotenv 0.3–1.2 interpolate inside single
    quotes), no mark inside, no '\\' in a double-quoted one (bash keeps it, dotenv decodes it), no control
    character (Unicode Cc) but a literal tab, no consecutive single-quoted backslashes, and no whitespace at its edges (dotenv 0.2.5–6.2.0 trim inside quotes). Returns
    (value, the quoted-empty form for dotenv 15.0.0 or None): 15.0.0 alone reads ''/\"\" literally, so the masked
    set covers those two-character forms for an empty quoted value."""
    if not rest.endswith(mark) or len(rest) < 2:
        raise NotLiteral(line, "text after a closing quote" if rest.count(mark) > 1 else
                         "a quoted value that is never closed on its line")
    content = rest[1:-1]
    if mark in content:
        raise NotLiteral(line, "a quoted value holding its own quote (adjacent or escaped quotes read differently "
                               "across readers)")
    if "$" in content or "`" in content:
        raise NotLiteral(line, "a '$' or backtick in a value — no references, interpolation or expansion")
    if mark == '"' and "\\" in content:
        raise NotLiteral(line, "a backslash in a double-quoted value (readers disagree on every escape)")
    if mark == "'" and "\\\\" in content:
        raise NotLiteral(line, "consecutive backslashes in a single-quoted value (python-dotenv decodes them)")
    if any(unicodedata.category(char) == "Cc" and char != "\t" for char in content):
        raise NotLiteral(line, "a control character in a quoted value (only a literal tab is admitted)")
    if content and any(char.isspace() or char == "\ufeff" for char in (content[0], content[-1])):
        raise NotLiteral(line, "whitespace at a quoted value's edge (dotenv 0.2.5–6.2.0 trim inside quotes)")
    return content, (mark * 2 if not content else None)


def assignments(text, written=None):
    """[(name, value, quoted-empty form or None)] for a .env file inside the literal boundary, in file order;
    NotLiteral otherwise. `written`, the file as written (carriage returns and a byte order mark included), is
    checked when given — a shell sourcing the file reads both, so either refuses the file. `value` is the single
    unanimous decode of the line across the claimed readers; the masked set for the line is that decode plus, for
    a quoted-empty line, the two-character form dotenv 15.0.0 reads."""
    as_written = text if written is None else written
    if as_written.startswith("\ufeff"):
        raise NotLiteral(0, "a byte order mark, which a shell sourcing the file reads as part of its first word")
    if "\r" in as_written:
        raise NotLiteral(0, "a carriage return — the boundary is LF-only (bash keeps a '\\r' in the value)")
    found, seen = [], set()
    for number, line in enumerate(text.split("\n"), 1):
        if not line.strip(" \t"):
            continue   # blank
        if line.lstrip(" \t").startswith("#"):
            continue   # a comment: no claimed reader in range reads its text
        match = ASSIGNMENT.match(line)
        if not match:
            raise NotLiteral(number, "not a literal assignment (a line is blank, a '#' comment, or "
                                     "[export ]NAME=VALUE — a shell's name, no spaces around '=', a single "
                                     "'export ' prefix)")
        name, rest = match.groups()
        if name in seen:
            raise NotLiteral(number, "the name is assigned twice (dotenv 0.1.1 takes the first, every other "
                                     "reader the last)")
        seen.add(name)
        if rest[:1] in ("'", '"'):
            value, empty_form = quoted(number, rest, rest[0])
        else:
            unquoted = UNQUOTED.match(rest)
            if not unquoted:
                raise NotLiteral(number, "a byte outside the literal unquoted set (whitespace inside a value, "
                                         "'#', a quote, a backslash, '{', '}', or a control character)")
            value = unquoted.group(1)
            if "$" in value or "`" in value:   # unreachable through the set — stated for the reader of the diff
                raise NotLiteral(number, "a '$' or backtick in a value — no references, interpolation or "
                                         "expansion")
            if value.startswith("~") or ":~" in value:
                raise NotLiteral(number, "a '~' at a value's start or after a ':' (bash expands it through the "
                                         "account database)")
            value, empty_form = value, None
        found.append((name, value, empty_form))
    return found
