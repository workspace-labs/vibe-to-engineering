"""The readers behind evidence.py: each turns the text of one secret file into (name, value) pairs — every value in
every form a check may print it in, under the name the file gives it — or raises Unreadable, naming the line and what
it could not read, never the file's text; evidence.py then stops the run before the check, because the file's values
could not be masked. Standard library only.

The formats read: a key file; .env; JSON; YAML and TOML (the subsets their readers name); INI; Java .properties; and a
file in no format this tool reads — a document, source code, a log — line by line, by the NAME=VALUE pairs on its lines
and by each word and member of a line, masked as written, not decoded. That last one is a known limit: a value that
stands in such a file only as a part cut out of a word, or encoded by the program that reads it, is not masked when a
check prints it alone.

A line's would-be name decides what it is: a name as people write one with nothing after its '=' or ':' is an empty
setting and holds no value; a would-be name that is not written as a name is (a base64 token, cjMt…Nw==) makes the
line a bare token, whatever follows it — its values are named after the file, and the token is never a name. The forms
of each value, and the standard readings of each format, come from secretforms.py.
"""

import bisect
import codecs
import json
import re
from urllib.parse import unquote

from envliteral import NotLiteral, assignments
from secretforms import (BARE, LIST, SECRET_NAME, SETTING, forms, interpolated, latin1, listed,  # noqa
                         qualified, token_like, trimmed)

# A name given a value, anywhere on a line: NAME=VALUE, export NAME=VALUE, name: value, "name": "value", 'name' = …
NAME = re.compile(r"""(?<![\w.-])(?:export\s+)?(["']?)([A-Za-z_][\w.-]*)\1\s*[=:]\s*""")
QUOTED = re.compile(r'"((?:[^"\\]|\\.)*)"|\'([^\']*)\'')
BLOCK = re.compile(r"[|>][+\-1-9]{0,2}")  # a YAML block value: the more indented lines that follow hold it
ARMOR = re.compile(r"-----(?:BEGIN|END) [A-Z0-9 ]+-----")  # the lines around a key or a certificate: not values
# A line's would-be name, before its '=' or ':' — a name, or a base64 token that only looks like one; a comment
WOULD_BE = re.compile(r"""[ \t]*(?:export[ \t]+)?([^\s=:#'"]+)[ \t]*[=:]""")
COMMENT = re.compile(r"(?m)(?:^[ \t]*[#;!]|[ \t]#)(.*)$")
SPACES = re.compile(r"[ \t]*")
COMMENT_END = re.compile(r"[ \t]*(?:#[^\n]*)?(?:\n|$)")  # the rest of a line after a value: spaces, a comment
# .env: [export ]NAME= or NAME: (2FA_SECRET, DB_PASSWORD[0], API_KEY! too — anything python-dotenv takes for a name —
# and a quoted name, as python-dotenv reads 'A=B'=value), any space
# but a line break around them as python-dotenv takes it; the quote closing a value quoted with ", ' or `; an escape
DOTENV = re.compile(r"""[^\S\n]*(?:export[^\S\n]+)?(?:'([^'\n]+)'|"([^"\n]+)"|([^\s=:#'"]+))[^\S\n]*[=:]""")
DOTENV_CLOSE = {'"': re.compile(r'(?:[^"\\]|\\.)*"', re.S), "'": re.compile(r"(?:[^'\\]|\\[\\']|\\(?![\\']))*'"),
                "`": re.compile(r"[^`]*`")}
DOTENV_ESCAPE = re.compile(r"""\\(?:U(?:000[0-9a-fA-F]|0010)[0-9a-fA-F]{4}|u[0-9a-fA-F]{4}|x[0-9a-fA-F]{2}|[0-7]{1,3}"""
                           r"""|[\\'"abfnrtv])""")   # each one decodes as Python decodes it, never failing
# a reference to another value, not after a backslash: ${NAME}, ${NAME<op>word} for each of a shell's :- - := = :+ +
# :? ?, and $NAME — or to one of a shell's special parameters ($1, $#, $$, $?, $!, $@, $*, $-, braced or not) — and
# ${#NAME}, the length of a value (group 5)
REFERENCE = re.compile(r"(?<!\\)\$(?:\{(?!#(?:\w+|[#?@*])\})(\w+|[#?$!@*-])(?:(:?[-=+?]|##?|%%?)([^}]*))?\}"
                       r"|([A-Za-z_]\w*|[0-9#?$!@*-])|\{#(\w+|[#?@*])\})")
REFERENCE_TEXT = re.compile(r"(?<!\\)\$(?:\{[^}]*\}|[A-Za-z_]\w*|[0-9#?$!@*-])")   # the same, to split a value around
INNERMOST = re.compile(r"(?<!\\)\$(?:\{(?!#(?:\w+|[#?@*])\})(\w+|[#?$!@*-])(?:(:?[-=+?]|##?|%%?)([^}$]*))?\}"
                       r"|([A-Za-z_]\w*|[0-9#?$!@*-])|\{#(\w+|[#?@*])\})")
# Java .properties: a key up to the first = : or space not escaped, the separator, an escape
PROPERTIES_KEY = re.compile(r"(?:[^\\=: \t\f]|\\.)*")
PROPERTIES_SEPARATOR = re.compile(r"[ \t\f]*[=:]?[ \t\f]*")
PROPERTIES_ESCAPE = re.compile(r"\\(u.{0,4}|.)")
# YAML: a plain key and its colon, a block value's header, anchors and tags, the close of a quoted value, a flow
# value's words, the space and comments between flow members, and what may follow a value on its line
YAML_KEY = re.compile(r"""(?![-?:](?:[ \t]|$))([^\s,\[\]{}#&*!|>'"%@`].*?)[ \t]*:(?:[ \t]+|$)""")
YAML_HEADER = re.compile(r"[|>](?:([1-9])[+-]?|[+-]([1-9])?)?(?:[ \t]+#.*|[ \t]*)$")
YAML_PREFIX = re.compile(r"(?:(?:!<[^>\s]*>|[&!][^\s,\[\]{}]*)[ \t]*)+")
ANCHOR = re.compile(r"&([^\s,\[\]{}]+)")
YAML_CLOSE = {'"': re.compile(r'(?:[^"\\]|\\.)*"', re.S), "'": re.compile(r"(?:[^']|'')*'(?!')")}
YAML_ESCAPES = {"0": "\0", "a": "\a", "b": "\b", "t": "\t", "\t": "\t", "n": "\n", "v": "\v", "f": "\f", "r": "\r",
                "e": "\x1b", " ": " ", '"': '"', "/": "/", "\\": "\\", "N": "\x85", "_": "\xa0", "L": "\u2028",
                "P": "\u2029"}
FLOW_WORD = r"(?:[^\s,\[\]{}:#]|:(?![\s,\[\]{}]|$)|(?<=\S)#)+"
FLOW_WORDS = re.compile(r"%s(?:[ \t]+%s)*" % (FLOW_WORD, FLOW_WORD))
FLOW_SPACE = re.compile(r"(?:[ \t\n]+(?:#[^\n]*)?)*")
FLOW_BREAK = re.compile(r"[ \t]*\n(?:[ \t]*\n)*[ \t]*")
AFTER_VALUE = re.compile(r"(?:[ \t]+#.*)?[ \t]*")
DOCUMENT_MARK = re.compile(r"(?:---|\.\.\.)(?:[ \t]|$)")
# A tag, as PyYAML resolves it: each document's handles (! and !!, then those its %TAG directives name), a node's tag
# — verbatim !<…>, or a handle and a suffix — and one written flush against what follows it, which PyYAML reads on
TAG_HANDLES = {"!": "!", "!!": "tag:yaml.org,2002:"}
TAG_DIRECTIVE = re.compile(r"%TAG +(!(?:[0-9A-Za-z_-]*!)?) +([0-9A-Za-z;/?:@&=+$,_.!~*'()\[\]%-]+)(?: +(?:#.*)?)?")
TAG = re.compile(r"!<[^>\s]*>|![^\s,\[\]{}]*")
TAG_LAST = re.compile(r"(?:!<[^>\s]*>|![^\s,\[\]{}]*)$")
# What of a YAML line is not its data: a quoted value (to the line's end when it goes on) and a comment; a template's
# marker in what is left is template syntax, which PyYAML cannot read either
YAML_NOT_DATA = re.compile(r"\"(?:[^\"\\]|\\.)*(?:\"|$)|'(?:[^']|'')*(?:'|$)|(?:^|(?<=[ \t]))#.*")
TEMPLATE = re.compile(r"\{\{|\{%")
# TOML: a bare key, a value that is not a string (as written), the four strings (opener, close, escapes), a comment
TOML_KEY = re.compile(r"[A-Za-z0-9_-]+")
TOML_SCALAR = re.compile(r"\d{4}-\d{2}-\d{2}(?:[Tt ]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:[Zz]|[+-]\d{2}:\d{2})?)?"
                         r"|\d{2}:\d{2}:\d{2}(?:\.\d+)?|true|false|[+-]?(?:inf|nan)|[+-]?0x[0-9A-Fa-f_]+"
                         r"|[+-]?0o[0-7_]+|[+-]?0b[01_]+|[+-]?[0-9_]+(?:\.[0-9_]+)?(?:[eE][+-]?[0-9_]+)?")
TOML_STRINGS = (('"""', re.compile(r'(?:[^"\\]|\\.|"(?!""))*"""', re.S), True),
                ("'''", re.compile(r"(?:[^']|'(?!''))*'''"), False),
                ('"', re.compile(r'(?:[^"\\\n]|\\[^\n])*"'), True), ("'", re.compile(r"[^'\n]*'"), False))
TOML_ESCAPES = {"b": "\b", "t": "\t", "n": "\n", "f": "\f", "r": "\r", '"': '"', "\\": "\\", "e": "\x1b"}
TOML_SPACE = re.compile(r"(?:[ \t\n]|#[^\n]*)*")
LINE_BREAK = re.compile(r"[ \t]*\n\s*")  # after a TOML line-ending backslash: the break and the space that follows
INI_OPTION = re.compile(r"(.*?)\s*[=:]\s*(.*)$")
TELLING = re.compile(r"\w|\S.{2,}\S", re.S)  # a piece worth masking: a word or four characters, never a lone -


class Unreadable(Exception):
    """What a reader could not understand in a secret file, and where (`line`, 0 when it names no line) — never the
    file's text. `final` when the file may not be read another way instead (evidence.py's template reading)."""
    line, final = 0, False


def unreadable(text, at, what):
    """Unreadable naming the line of text that holds offset `at`."""
    error = Unreadable("line %d: %s" % (text.count("\n", 0, at) + 1, what))
    error.line = text.count("\n", 0, at) + 1
    return error


def decoded(raw):
    """A quoted value as a JSON reader decodes it (\\uXXXX, \\n, \\"), or "" when it is not JSON."""
    try:
        return json.loads('"%s"' % raw, strict=False)
    except ValueError:
        return ""


def values_in(text, label):
    """(name, sign, value) for every value the text gives a name, its sign '=' or ':' — each in every form it may be
    printed: a quoted value whole, decoded and line by line; an unquoted value whole, without an inline comment, up to
    a separator (',' ';' '}', and a URL's '&' or '?'), its first word; a YAML block value (`|`, `>`) whole and line by
    line — and, named after the file (`label`, sign None), every line that gives no name a value: a key file's own
    lines, a bare token. Comment lines and the lines around a key are not values. The line scan behind text_values,
    for a file in no format this tool reads, behind the values named inside another value (evidence.py's inner), and
    behind the values named inside a comment (commented)."""
    found, lines, i = [], text.splitlines(), 0
    while i < len(lines):
        line, i = lines[i], i + 1
        if not re.search(r"\w", line) or line.lstrip().startswith("#") or ARMOR.fullmatch(line.strip()):
            continue
        matches = list(NAME.finditer(line))
        if not matches:
            bare = line.strip()
            found += [(label, None, value) for value in dict.fromkeys([bare, bare.lstrip("-").strip()]) if value]
            continue
        for match in matches:
            rest = line[match.end():]
            quoted = QUOTED.match(rest)
            if rest[:1] in ('"', "'") and not quoted:  # a quoted value that goes on over the following lines
                joined, j = rest, i
                while j < len(lines) and not quoted:
                    joined += "\n" + lines[j]
                    j += 1
                    quoted = QUOTED.match(joined) if rest[0] in lines[j - 1] else None  # only a quote can close it
                if quoted:
                    i = j
            if quoted:
                raw = quoted.group(1) if quoted.group(1) is not None else quoted.group(2)
                candidates = [raw, re.sub(r"\\(.)", r"\1", raw), decoded(raw),
                              yaml_quoted(raw, quoted.group(1) is not None) or ""] + raw.split("\n")
            elif BLOCK.fullmatch(rest.strip()):
                block, own = [], len(line) - len(line.lstrip())
                while i < len(lines) and (not lines[i].strip() or lines[i][:own + 1].isspace()):   # more indented
                    block.append(lines[i].strip())
                    i += 1
                candidates = block + ["\n".join(block).strip(), " ".join(part for part in block if part)]
            else:
                rest = rest.strip()
                candidates = [rest, re.split(r"\s+#", rest)[0].strip(), re.split(r"[,;}]", rest)[0].strip(),
                              re.split(r"[&;?]", rest)[0].strip(), rest.split()[0] if rest.split() else ""]
            sign = "=" if "=" in match.group() else ":"
            found += [(match.group(2), sign, value) for value in dict.fromkeys(candidates) if value]
    return found


def commented(text, label):
    """(the file's name, value) for each value given a name inside a comment ('#', and a comment line's ';' or '!') —
    an old password kept after it (# previous: …), a setting put out of use (#API_KEY=…) — when it reads as a secret
    rather than as prose: one word of six characters or more holding a digit, not a number or a date. Named after the
    file (`label`): a comment names nothing."""
    return [(label, value) for comment in COMMENT.finditer(text)
            for _, sign, value in values_in(comment.group(1), label)
            if sign and re.fullmatch(r"\S{6,}", value) and re.search(r"[0-9]", value)
            and not re.fullmatch(r"[0-9][0-9._:/-]*", value)]


def fold(parts):
    """Lines joined as YAML folds them: one space between two lines, a line break for each blank line between."""
    out, blank = [], 0
    for part in parts:
        if part:
            out += [("\n" * blank or " ") * bool(out), part]
        blank = 0 if part else blank + 1
    return "".join(out)


def hex_escape(raw, i, widths):
    """(the character, the escape's length) for the \\x, \\u or \\U escape at raw[i] when widths names its letter and
    its digits are hexadecimal, else None."""
    width = widths.get(raw[i + 1:i + 2], 0)
    digits = raw[i + 2:i + 2 + width]
    if width and re.fullmatch(r"[0-9a-fA-F]{%d}" % width, digits) and int(digits, 16) <= 0x10FFFF:
        return chr(int(digits, 16)), 2 + width
    return None


def key_values(text, label):
    """A key file's values, each named after the file: every line that is not a key's armor (-----BEGIN …-----,
    -----END …-----), each piece of such a line between spaces, and each armored body joined, on one line and on its
    lines."""
    found, bodies = [], []
    for line in (line.strip() for line in text.split("\n")):
        if ARMOR.fullmatch(line):
            bodies.append([] if line.startswith("-----BEGIN") else None)   # None: the body before it is closed
        elif line:
            found += [line] + line.split()
            if bodies and bodies[-1] is not None:
                bodies[-1].append(line)
    return [(label + BARE, value) for value in found + [part for body in bodies if body
                                                        for part in ("".join(body), "\n".join(body))]]


def bare(line, label, always=True):
    """A line that gives no name a value, named after the file (`label`): stripped, without a leading '-', and — in a
    .env file — cut at an inline comment. A line that starts NAME= or NAME: is judged by its would-be name: a name as
    people write one with nothing after its sign but spaces or a comment is an empty setting and holds no value
    (API_KEY=, password:); a would-be name that is not written as a name — a base64 token, cjMt…Nw== — or that holds no
    secret word and is followed by '=' padding makes the line a bare token whatever follows it (token_like), and the
    token, the token with its padding, and the line without a comment glued on ('#') or after a space ('#', ';') are
    values too. The token is never a name."""
    line = line.strip()
    found = [line, line.lstrip("-").strip()] + ([re.split(r"[ \t]#", line)[0].strip()] if always else [])
    would = WOULD_BE.match(found[1])
    if would and not token_like(would.group(1), found[1][would.end():]):
        if not re.split(r"(?:^|[ \t])[#;]", found[1][would.end():].strip(" \t="))[0].strip():
            return []
    elif would:
        token, rest = would.group(1), found[1][would.end(1):]
        found += [token, token + re.match(r"[ \t]*(=*)", rest).group(1), re.split(r"#|[ \t];", found[1])[0].strip()]
    return [(label + BARE, value) for value in dict.fromkeys(found) if value]


def filled(form, values):
    """form with each reference in it filled in as a shell sourcing the file fills it, the innermost first (so that
    ${A:-${B#p}} and ${A#$P} read as the shell reads them): ${NAME} and $NAME with the value `values` gives NAME, else
    nothing; ${NAME:-word} (and := :?) with the word when NAME is unset or empty, ${NAME-word} (and = ?) when it is
    unset — := and = also give NAME the word from then on, as the shell does; ${NAME:+word} with the word when NAME is
    set and not empty, ${NAME+word} when it is set, else nothing; ${NAME#pattern} ## % %% with the value trimmed as the
    shell trims it; ${#NAME} with the length of its value, in characters; and a special parameter as $# and $? as 0,
    the others as nothing. The other readers' filling (python-dotenv's, Node's), from the file's own values; the shell's
    own reading, which refuses what the file does not decide, is secretforms.evaluate."""
    def one(ref):
        if ref.group(5) is not None:   # ${#NAME}: how long its value is
            length = ref.group(5)
            value = values.get(length) if re.match(r"[A-Za-z_]", length) else "0" if length in ("#", "?") else ""
            return str(len(value or ""))
        name, operator, word = ref.group(1) or ref.group(4), ref.group(2) or "", ref.group(3) or ""
        if not re.match(r"[A-Za-z_]", name):
            return "0" if name in ("#", "?") else ""
        value = values.get(name)
        if operator[:1] in ("#", "%"):
            return trimmed(value or "", operator, word)
        if "+" in operator:
            return word if value is not None and (value or ":" not in operator) else ""
        if operator and (value is None or (not value and ":" in operator)):
            if "=" in operator:
                values[name] = word
            return word
        return value or ""
    for _ in range(10):   # innermost first: a reference whose word holds no other reference, then again
        done = INNERMOST.sub(one, form)
        if done == form:
            break
        form = done
    return form


def dotenv_values(text, label, written=None, environ=None):
    """(name, value) for every value in a .env file — but only a file inside the v0.1 literal boundary
    (envliteral.py; release decision A1, owner-approved 2026-09-27) is read at all. The boundary is a positive
    grammar, proven against every claimed reader by the 2026-09-27 reader-compatibility experiment and re-proven
    by the in-suite differential matrix: blank lines, '#' comments and literal [export ]NAME=VALUE assignments —
    no references, interpolation or expansion anywhere. Anything else is Unreadable and stops the run before the
    check (exit 2, nothing runs, no evidence), because the file's values could not be guaranteed masked. The
    masked set for an admitted line is the line's single unanimous decode across the claimed readers — plus, for
    a quoted-empty line, the two-character form ('' or "") dotenv 15.0.0 alone reads — each in every form a
    check may print it in (forms). `written`, the file as written, decides the byte-order-mark and
    carriage-return refusals (a shell sourcing the file reads both). `environ` keeps the call's shape and is no
    longer consulted: under the boundary no reading depends on the environment."""
    try:
        parsed = assignments(text, written)
    except NotLiteral as error:
        at = sum(len(line) + 1 for line in text.split("\n")[:error.line - 1]) if error.line else 0
        raise unreadable(text, at, error.reason)
    found = []
    for name, value, quoted_empty in parsed:
        if value:
            found += [(name, form) for form in forms(value)]
        if quoted_empty:
            found.append((name, quoted_empty))   # dotenv 15.0.0 alone reads ''/"" literally
    return found


def json_values(text, label):
    """(name, value) for every value in a file that is one JSON document — a string decoded and as written, a number
    as written and as JSON writes it, true and false; a list's members under the list's name, the top level under the
    file's name, and every member of an object under its own key (qualified by the object's when that says secret and
    the key does not), a repeated key too. ValueError for any other text."""
    document = json.loads(text, object_pairs_hook=lambda pairs: ("{", pairs), parse_int=lambda raw: ("#", raw),
                          parse_float=lambda raw: ("#", raw), parse_constant=lambda raw: ("#", raw))
    found, names, pending = [], {}, [(label, document)]
    while pending:
        name, value = pending.pop()
        if isinstance(value, tuple) and value[0] == "{":   # a key under an object named secret keeps saying so
            around = None if name.replace(LIST, "") == label else name
            pending += [(qualified(around, key), member) for key, member in value[1]]
        elif isinstance(value, tuple):
            found += [(name, form) for form in forms(value[1], json.dumps(json.loads(value[1])))]
        elif isinstance(value, list):
            pending += [(listed(name), member) for member in value]
        elif isinstance(value, bool):
            found.append((name, json.dumps(value)))
        elif isinstance(value, str):
            found += [(name, form) for form in forms(value)]
            names.setdefault(value, []).append(name)
    for token in re.finditer(r'"((?:[^"\\]|\\.)*)"', text):   # each string as written, beside its decoded value
        for name in dict.fromkeys(names.get(json.loads(token.group(0)), ())):
            found += [(name, form) for form in forms(token.group(1))]
    return found


def yaml_quoted(raw, double):
    """A quoted YAML value: '' read as ' (single), its escapes decoded (double), each line break folded to one space
    and each blank line to a line break, the spaces around a line break trimmed. None for an escape YAML lacks."""
    out, i, kept = [], 0, 0
    while i < len(raw):
        char = raw[i]
        if char == "\n" or (double and char == "\\" and raw[i + 1:i + 2] == "\n"):
            while char == "\n" and len(out) > kept and out[-1] in " \t":
                out.pop()
            i, breaks = i + 1 + (char == "\\"), 0
            while raw.startswith("\n", SPACES.match(raw, i).end()):
                i, breaks = SPACES.match(raw, i).end() + 1, breaks + 1
            i = SPACES.match(raw, i).end()
            out.append("\n" * breaks or " " * (char == "\n"))
            kept = len(out)
        elif double and char == "\\":
            escape = hex_escape(raw, i, {"x": 2, "u": 4, "U": 8}) or (YAML_ESCAPES.get(raw[i + 1:i + 2]), 2)
            if escape[0] is None:
                return None
            out.append(escape[0])
            i, kept = i + escape[1], len(out)
        else:
            out.append(char)
            i += 1 + (char == "'" and not double)      # '' is one ' in a single-quoted value
    return "".join(out)


def yaml_binary(prefix, handles):
    """True when a tag among a node's anchors and tags (`prefix`) is one PyYAML turns into bytes or a Python object
    rather than text — tag:yaml.org,2002:binary, or python/… under it — however it is written: !!binary, through a
    handle a %TAG directive names (!e!binary, or !binary for the ! handle), verbatim (!<tag:yaml.org,2002:binary>), or
    with %-escaped letters (!!bin%61ry). A handle the document does not name resolves to nothing: PyYAML stops there."""
    for tag in TAG.findall(prefix):
        if tag.startswith("!<") and tag.endswith(">"):
            full = unquote(tag[2:-1])
        else:
            second = tag.find("!", 1)
            handle, suffix = (tag[:second + 1], tag[second + 1:]) if second > 0 else ("!", tag[1:])
            full = handles[handle] + unquote(suffix) if handle in handles else ""
        if full == "tag:yaml.org,2002:binary" or full.startswith("tag:yaml.org,2002:python/"):
            return True
    return False


def yaml_values(text, label):
    """yaml_document_values() — and when that cannot read the file, its Unreadable marked final, so that the file is
    never read as a template's text instead (evidence.py), unless the line it stopped at holds a template's marker ({{
    or {%) in its data, not in a quoted value or a comment: template syntax, which PyYAML cannot read either. Final
    even then when a tag anywhere in the file may be one PyYAML decodes (yaml_decodes): the text reading decodes
    none."""
    try:
        return yaml_document_values(text, label)
    except Unreadable as error:
        line = text.split("\n")[error.line - 1] if error.line else ""
        if not TEMPLATE.search(YAML_NOT_DATA.sub("", line)) or yaml_decodes(text):
            error.final = True
        raise


def yaml_decodes(text):
    """True when a tag anywhere in a YAML file's data (not in a quoted value or a comment) may be one PyYAML decodes to
    bytes or a Python object (yaml_binary) — with the ! and !! handles, or with any a %TAG directive in the file names
    — or when such a directive cannot be read."""
    declared = [dict(TAG_HANDLES)]
    for line in text.split("\n"):
        if re.match(r"%TAG(?:[ \t]|$)", line):
            directive = TAG_DIRECTIVE.fullmatch(line.rstrip())
            if not directive:
                return True
            declared.append({directive.group(1): unquote(directive.group(2))})
    data = " ".join(YAML_NOT_DATA.sub("", line) for line in text.split("\n"))
    return any(yaml_binary(data, handles) for handles in declared)


def yaml_document_values(text, label):
    """(name, value) for every value in a YAML file, in the subset this reader understands: comments, document markers
    and directives (%TAG naming a document's tag handles); mappings with plain or quoted keys; lists ('- ', nested, and
    at their key's own column); plain values over several lines; quoted values with their escapes; block values (| and
    >, with an indentation digit, chomping and a comment on the header); flow lists and mappings over several lines;
    anchors, tags and aliases. A value is named after its nearest key. Anything else — an explicit '? ' key, a tab in
    the indentation, a quote or bracket never closed, a plain value holding ': ', a line it cannot place, a tag that
    PyYAML turns into bytes or a Python object (yaml_binary) or that it reads on into what follows it — is
    Unreadable."""
    if re.search("[\x85\u2028\u2029]", text):
        raise Unreadable("a line break this reader does not read")
    lines, found, frames = text.split("\n"), [], []    # frames: [column, "map" or "seq", name, value still to come]
    anchors, pending = {}, []   # an anchor's forms; the anchors whose value is still to come: (anchor, mark, column)
    handles, declared = dict(TAG_HANDLES), {}   # this document's tag handles; those named for the next one
    starts = [line.start() for line in re.finditer(r"(?m)^", text)]

    def row_of(at):
        row = bisect.bisect_right(starts, at) - 1
        return row, starts[row] + len(lines[row])

    def quoted(at, end):
        """(offset after, value, forms) for the quoted value at `at`; end, when given, keeps it on one line."""
        close = YAML_CLOSE[text[at]].match(text, at + 1, len(text) if end is None else end)
        if not close:
            raise unreadable(text, at, "a quoted value that is never closed")
        raw = text[at + 1:close.end() - 1]
        value = yaml_quoted(raw, text[at] == '"')
        if value is None:
            raise unreadable(text, at, "an escape this reader does not read")
        return close.end(), value, forms(value, raw)

    def tagged(prefix, at):
        """Refuses the node at `at` when a tag in its prefix is one PyYAML reads as bytes or a Python object, or is
        written flush against what follows it (PyYAML reads that on as part of the tag) — for good: such a value is
        never read as a template's text instead."""
        binary = prefix is not None and yaml_binary(prefix.group(), handles)
        if binary or (prefix and TAG_LAST.search(prefix.group()) and text[prefix.end():prefix.end() + 1] not in (
                "", "\n")):
            error = unreadable(text, at, "a binary value" if binary else "a tag this reader does not read")
            error.final = True
            raise error

    def flow(at, name):
        """Reads the [ ] or { } at `at`, over several lines when it goes on; returns the offset after it."""
        closing, at = "]" if text[at] == "[" else "}", at + 1
        while True:
            at = FLOW_SPACE.match(text, at).end()
            if text.startswith(closing, at):
                return at + 1
            if at >= len(text):
                raise unreadable(text, at, "a [ or { that is never closed")
            if re.match(r"\?(?:\s|$)", text[at:at + 2]):
                raise unreadable(text, at, "an explicit '? ' key")
            at, value, member = flow_node(at, name)
            after, owner = SPACES.match(text, at).end(), listed(name) if closing == "]" else name
            if text.startswith(":", after):   # the value was a key, naming the value after it
                if value is None:
                    raise unreadable(text, at, "a key this reader does not read")
                owner = qualified(name if name.replace(LIST, "") != label else None, value)   # under a secret name
                at, member = FLOW_SPACE.match(text, after + 1).end(), []
                if text[at:at + 1] not in (",", closing, ""):
                    at, _, member = flow_node(at, owner)
            found.extend((owner, form) for form in member)
            at = FLOW_SPACE.match(text, at).end()
            if text.startswith(",", at):
                at += 1
            elif not text.startswith(closing, at):
                raise unreadable(text, at, "a [ or { %s" % ("that is never closed" if at >= len(text) else
                                                            "this reader does not read"))

    def flow_node(at, name):
        """(offset after, the scalar's value or None, its forms) for one member of a [ ] or { }; an anchor on it
        keeps what it holds, for the aliases to it."""
        prefix, mark = YAML_PREFIX.match(text, at), len(found)
        read = flow_member(at, name, prefix)
        for anchor in ANCHOR.findall(prefix.group()) if prefix else ():
            anchors[anchor] = read[2] + [form for _, form in found[mark:]]
        return read

    def flow_member(at, name, prefix):
        tagged(prefix, at)
        at = FLOW_SPACE.match(text, prefix.end()).end() if prefix else at
        char = text[at:at + 1]
        if prefix and char in (",", "]", "}", ""):
            return at, None, []
        if char in ("[", "{"):
            return flow(at, name), None, []
        if char == "*":   # an alias: the values of the node its anchor is on, under this name
            alias = re.compile(r"\*([^\s,\[\]{}]*)").match(text, at)
            return alias.end(), None, list(anchors.get(alias.group(1), ()))
        if char in ('"', "'"):
            return quoted(at, None)
        if not char or char in "#,[]{}|>%@`" or re.match(r"[-?:](?:[\s,\[\]{}]|$)", text[at:at + 2]):
            raise unreadable(text, at, "a value this reader does not read")
        parts = []
        while True:   # a plain value, going on over the following lines until a flow sign
            words = FLOW_WORDS.match(text, at)
            parts.append(words.group())
            at, gap = words.end(), FLOW_BREAK.match(text, words.end())
            if not gap or not FLOW_WORDS.match(text, gap.end()):
                break
            parts.extend([""] * (gap.group().count("\n") - 1))
            at = gap.end()
        value = fold(parts)
        return at, value, forms(value, "\n".join(part for part in parts if part), *parts)

    def block(row, digit, name, parent):
        """A block value (| or >) on the lines after row; returns the next row to read."""
        size, body, row = max(parent, 0) + int(digit) if digit else None, [], row + 1
        while row < len(lines):
            line, spaces = lines[row], len(lines[row]) - len(lines[row].lstrip(" "))
            if line.strip() and (spaces <= parent or (spaces == 0 and DOCUMENT_MARK.match(line))):
                break
            if line.strip() and size is not None and spaces < size and digit:
                raise unreadable(text, starts[row], "a block value less indented than its header says")
            size = spaces if size is None and line.strip() else size
            body.append(line[min(spaces, size):] if line.strip() else "")
            row += 1
        while body and not body[-1].strip():
            body.pop()
        literal, stripped = "\n".join(body), [part.strip() for part in body]
        folded, joined = fold(stripped), " ".join(part for part in stripped if part)
        found.extend((name, form) for form in forms(literal, literal + "\n", folded, folded + "\n", joined))
        return row

    def plain(row, piece, name, parent):
        """A plain value and the more indented lines that go on with it; returns the next row to read."""
        parts = []
        while True:
            value, cut = re.split(r"[ \t]#", piece, 1)[0].rstrip(), re.search(r"[ \t]#", piece)
            if re.search(r":(?:[ \t]|$)", value):
                raise unreadable(text, starts[row], "a plain value holding ': '")
            parts.append(value)
            nxt = next((nxt for nxt in range(row + 1, len(lines)) if lines[nxt].strip()), len(lines))
            line = lines[nxt] if nxt < len(lines) else ""
            spaces, piece = len(line) - len(line.lstrip(" ")), line.strip()
            if cut or not piece or spaces <= parent or piece.startswith("#") or (
                    not spaces and DOCUMENT_MARK.match(line)):
                break
            parts.extend([""] * (nxt - row - 1))
            row = nxt
        joined = fold(parts)
        found.extend((name, form) for form in forms(joined, "\n".join(part for part in parts if part), *parts))
        return row + 1

    def node(at, name, parent):
        """Reads the value at offset `at`: returns the next row to read, and True when the value is still to come,
        on the more indented lines that follow. An anchor on it keeps what it holds, for the aliases to it — for a
        value still to come, from the lines under it (closed in the loop below)."""
        prefix, mark = YAML_PREFIX.match(text, at, row_of(at)[1]), len(found)
        row, waiting = read_node(at, name, parent, prefix)
        for anchor in ANCHOR.findall(prefix.group()) if prefix else ():
            if waiting:
                pending.append((anchor, mark, parent))
            else:
                anchors[anchor] = [form for _, form in found[mark:]]
        return row, waiting

    def read_node(at, name, parent, prefix):
        row, end = row_of(at)
        tagged(prefix, at)
        at = prefix.end() if prefix else at
        rest = text[at:end]
        if not rest or rest.startswith("#"):
            return row + 1, True
        if rest[0] == "*":   # an alias: the values of the node its anchor is on, under this name
            alias = re.fullmatch(r"\*([^\s,\[\]{}]+)(?:[ \t]+#.*)?[ \t]*", rest)
            if not alias:
                raise unreadable(text, at, "an alias this reader does not read")
            found.extend((name, form) for form in anchors.get(alias.group(1), ()))
            return row + 1, False
        if rest[0] in "[{\"'":
            after, _, member = quoted(at, None) if rest[0] in "\"'" else (flow(at, name), None, [])
            found.extend((name, form) for form in member)
            row, end = row_of(after)
            if not AFTER_VALUE.fullmatch(text, after, end):
                raise unreadable(text, after, "text after a value")
            return row + 1, False
        if rest[0] in "|>":
            header = YAML_HEADER.match(rest)
            if not header:
                raise unreadable(text, at, "a block value header this reader does not read")
            return block(row, header.group(1) or header.group(2), name, parent), False
        if rest[0] in "%@`,]}" or re.match(r"[-?](?:[ \t]|$)", rest):
            raise unreadable(text, at, "a value this reader does not read")
        return plain(row, rest, name, parent), False

    def key_at(at, end):
        """(the key, the offset of its value) when the line at `at` is a mapping's key: value, else None."""
        if text[at] in "\"'":
            after, value, _ = quoted(at, end) if YAML_CLOSE[text[at]].match(text, at + 1, end) else (at, None, None)
            colon = re.compile(r"[ \t]*:[ \t]*").match(text, after, end) if value is not None else None
            return (value, colon.end()) if colon else None
        match = YAML_KEY.match(text, at, end)
        return (match.group(1), match.end()) if match and not re.search(r"[ \t]#", match.group(1)) else None

    def pair(frame, key):   # a key under a mapping named secret keeps saying so (qualified)
        index = next(at for at, open_frame in enumerate(frames) if open_frame is frame)
        parent = next((above[2] for above in reversed(frames[:index])
                       if above[2] and above[2].replace(LIST, "") != label), None)   # never the file's own name
        frame[2] = qualified(parent, key[0])
        row, frame[3] = node(key[1], frame[2], frame[0])
        return row

    def item(row, column, at):
        """A list entry: '- ' and its value, on this line or on the more indented lines that follow."""
        dash = re.compile(r"-([ \t]*)").match(text, at)
        if "\t" in dash.group(1):
            raise unreadable(text, at, "a tab after '-'")
        frames[-1][3] = True
        if dash.end() == row_of(at)[1] or text[dash.end()] == "#":
            return row + 1
        return place(row, column + dash.end() - at, dash.end())

    def place(row, column, at):
        """Places the text at offset `at`, column `column` of row, among the open mappings and lists; returns the
        next row to read."""
        dash = re.match(r"-(?:[ \t]|$)", text[at:at + 2])
        if re.match(r"\?(?:[ \t]|$)", text[at:at + 2]):
            raise unreadable(text, at, "an explicit '? ' key")
        key = None if dash else key_at(at, row_of(at)[1])
        while frames and (frames[-1][0] > column or (frames[-1][0] == column and frames[-1][1] == "seq" and not dash)):
            frames.pop()
        top = frames[-1] if frames else None
        if top and top[0] == column:   # the mapping's next key, or the list's next entry
            if top[1] == "map" and key:
                return pair(top, key)
            if top[1] == "map" and not (dash and top[3]):
                raise unreadable(text, at, "a line this reader cannot place")
            if top[1] == "map":   # a list at its key's own column
                top[3] = False
                frames.append([column, "seq", listed(top[2]), False])
            return item(row, column, at)
        if top and not top[3]:
            raise unreadable(text, at, "a line this reader cannot place")
        name, parent = (top[2], top[0]) if top else (label, -1)
        if top:
            top[3] = False
        if dash or key:
            frames.append([column, "seq" if dash else "map", listed(name) if dash else name, False])
            return item(row, column, at) if dash else pair(frames[-1], key)
        row, waiting = node(at, name, parent)
        if top and waiting:
            top[3] = True
        return row

    def close(column, entry=False):
        """Closes each anchor whose value was still to come once a line stands at or left of the column of the key
        it was given under (a list's entry may stand at its key's own column), or the document ends (-1)."""
        for anchor, mark, parent in list(pending):
            if column < parent or (column == parent and not entry):
                anchors[anchor] = [form for _, form in found[mark:]]
                pending.remove((anchor, mark, parent))

    row, directives = 0, True
    while row < len(lines):
        line, column = lines[row], len(lines[row]) - len(lines[row].lstrip(" "))
        if not line.strip() or line.strip().startswith("#"):
            row += 1
        elif line[column] == "\t":
            raise unreadable(text, starts[row] + column, "a tab in the indentation")
        elif column == 0 and DOCUMENT_MARK.match(line):
            if not re.fullmatch(r"(?:---|\.\.\.)(?:[ \t]+#.*)?[ \t]*", line):
                raise unreadable(text, starts[row], "a value on a document marker's line")
            del frames[:]
            close(-1)
            if line.startswith("---"):   # a document starts: the directives before it name its tag handles
                handles.clear()
                handles.update(TAG_HANDLES)
                handles.update(declared)
                declared.clear()
            row, directives = row + 1, line.startswith("...")
        elif column == 0 and line.startswith("%"):
            if not directives:
                raise unreadable(text, starts[row], "a directive inside a document")
            if re.match(r"%TAG(?:[ \t]|$)", line):
                directive = TAG_DIRECTIVE.fullmatch(line.rstrip())
                if not directive:
                    raise unreadable(text, starts[row], "a tag directive this reader does not read")
                declared[directive.group(1)] = unquote(directive.group(2))
            row += 1
        else:
            close(column, re.match(r"-(?:[ \t]|$)", line[column:]) is not None)
            row, directives = place(row, column, starts[row] + column), False
    return found


def toml_string(text, at):
    """(offset after, decoded value, raw text) for the TOML string at `at`, or None when none starts there."""
    for opener, close, escapes in TOML_STRINGS:
        if text.startswith(opener, at):
            start = at + len(opener) + (len(opener) == 3 and text.startswith("\n", at + 3))  # a first break is dropped
            match = close.match(text, start)
            if not match:
                raise unreadable(text, at, "a string that is never closed")
            extra = len(re.compile(opener[0] + "*").match(text, match.end()).group()) if len(opener) == 3 else 0
            if extra > 2:
                raise unreadable(text, at, "a string this reader does not read")
            raw = text[start:match.end() - len(opener) + extra]
            return match.end() + extra, toml_unescape(text, at, raw) if escapes else raw, raw
    return None


def toml_unescape(text, at, raw):
    """A basic TOML string's escapes decoded (\\b \\t \\n \\f \\r \\" \\\\ \\e \\uXXXX \\UXXXXXXXX, and a line-ending
    backslash, which drops the break and the space after it); any other escape is Unreadable."""
    out, i, slash = [], 0, raw.find("\\")
    while slash >= 0:
        out.append(raw[i:slash])
        escape = hex_escape(raw, slash, {"u": 4, "U": 8}) or (TOML_ESCAPES.get(raw[slash + 1:slash + 2]), 2)
        gap = LINE_BREAK.match(raw, slash + 1)
        if escape[0] is None and not gap:
            raise unreadable(text, at, "an escape this reader does not read")
        out.append(escape[0] if escape[0] is not None else "")
        i = slash + escape[1] if escape[0] is not None else gap.end()
        slash = raw.find("\\", i)
    return "".join(out) + raw[i:]


def toml_key(text, at):
    """(offset after, its parts) for a TOML key: bare, quoted, or dotted from both."""
    parts = []
    while True:
        at = SPACES.match(text, at).end()
        string = None if text.startswith(('"""', "'''"), at) else toml_string(text, at)
        match = None if string else TOML_KEY.match(text, at)
        if not string and not match:
            raise unreadable(text, at, "a key this reader does not read")
        at, name = string[:2] if string else (match.end(), match.group())
        at, parts = SPACES.match(text, at).end(), parts + [name]
        if not text.startswith(".", at):
            return at, parts
        at += 1


def toml_name(parent, parts):
    """The name a value under the dotted key `parts` is masked under, inside `parent` (a table, an inline table, or
    None): its last part — qualified by what is around it when that says secret and the part does not."""
    name = parent
    for part in parts:
        name = qualified(name, part) if name is not None else part
    return name


def toml_value(text, at, name, found):
    """Reads the TOML value at `at` into found, named after its key; returns the offset after it."""
    string = toml_string(text, at)
    if string:
        found += [(name, form) for form in forms(string[1], string[2])]
        return string[0]
    if text[at:at + 1] in ("[", "{"):
        closing, at = "]" if text[at] == "[" else "}", TOML_SPACE.match(text, at + 1).end()
        while not text.startswith(closing, at):
            if closing == "]":
                at = toml_value(text, at, listed(name), found)
            else:
                at, key = toml_key(text, at)
                if not text.startswith("=", at):
                    raise unreadable(text, at, "an inline table this reader does not read")
                at = toml_value(text, SPACES.match(text, at + 1).end(), toml_name(name, key), found)
            at = TOML_SPACE.match(text, at).end()
            if text.startswith(",", at):
                at = TOML_SPACE.match(text, at + 1).end()
            elif not text.startswith(closing, at):
                raise unreadable(text, at, "an array or inline table %s" % (
                    "that is never closed" if at >= len(text) else "this reader does not read"))
        return at + 1
    match = TOML_SCALAR.match(text, at)
    if not match:
        raise unreadable(text, at, "a value this reader does not read")
    found += [(name, form) for form in forms(match.group())]
    return match.end()


def toml_values(text, label):
    """(name, value) for every value in a TOML file, in the subset this reader understands: comments, table headers
    ([a.b] and [[a.b]]), key = value with bare, quoted and dotted keys; basic, literal and multi-line strings (decoded,
    as written, line by line), numbers, booleans and dates as written, arrays over several lines and inline tables.
    A value is named after its key. Anything else is Unreadable."""
    found, at, table = [], 0, None
    while True:
        at = TOML_SPACE.match(text, at).end()
        if at >= len(text):
            return found
        if text.startswith("[", at):
            double = text.startswith("[[", at)
            at, parts = toml_key(text, at + 1 + double)
            table = toml_name(None, parts)
            if not text.startswith("]]" if double else "]", at):
                raise unreadable(text, at, "a table header this reader does not read")
            at += 1 + double
        else:
            at, parts = toml_key(text, at)
            if not text.startswith("=", at):
                raise unreadable(text, at, "a line this reader does not read")
            at = toml_value(text, SPACES.match(text, at + 1).end(), toml_name(table, parts), found)
        end = COMMENT_END.match(text, at)
        if not end:
            raise unreadable(text, at, "text after a value")
        at = end.end()


def ini_values(text, label):
    """(name, value) for every value in an INI file: [section] headers, comment lines (# or ;), key = value or
    key: value, and more indented lines going on with the value before them. Each value as written, without one pair
    of surrounding quotes, with %% read as %, without an inline comment, the text around each %(name)s, as configparser
    reads it with each %(name)s filled in from its section and [DEFAULT] (interpolated), and line by line. A key that
    is not written as a name (a base64 token, cjMt…MQ== ; rotated) makes its line a bare token, all it holds named after
    the file (bare); a key with nothing after it is an empty setting. An option before any [section] (configparser
    refuses it too), or anything else, is Unreadable."""
    found, entries, sections, name, lines, level, section, token = [], [], {}, None, [], 0, None, False
    for number, line in enumerate(text.split("\n") + ["[end]"], 1):
        stripped = line.strip()
        if stripped.startswith(("#", ";")) or (not stripped and name is None):
            continue
        if not stripped or (name is not None and line[:level + 1].isspace()):
            lines.append(stripped)
            continue
        if name is not None:
            entries.append((section, label + BARE if token else name, "\n".join(lines).rstrip("\n")))
            sections.setdefault(section, {})[name.lower()] = entries[-1][2]
        name, level, option = None, len(line) - len(line.lstrip()), INI_OPTION.match(stripped)
        header = re.match(r"\[(.+)\]", stripped)
        if header:
            section = header.group(1)
            continue
        if not option or not option.group(1):
            raise Unreadable("line %d: a line this reader does not read" % number)
        if section is None:
            raise Unreadable("line %d: an option before any [section]" % number)
        token = token_like(option.group(1), option.group(2))
        found += bare(stripped, label) if token else []   # a base64 token, never a name
        name, lines = option.group(1), [option.group(2).strip("=") and option.group(2)]
    for section, name, value in entries:
        unquoted = value[1:-1] if len(value) > 1 and value[0] == value[-1] and value[0] in "\"'" else value
        defaults = sections.get("DEFAULT", {})
        # a [DEFAULT] option is an option of every section too, and configparser fills its references in each one
        places = [sections.get(section, {})] + ([own for other, own in sections.items() if other != "DEFAULT"]
                                                if section == "DEFAULT" else [])
        around = section if section != "DEFAULT" else next(   # a [DEFAULT] option is read in every section too
            (other for other in sections if other != "DEFAULT" and qualified(other, "x") != "x"), section)
        name = name if name.endswith(BARE) else qualified(around, name)   # an option of a secret section says so
        found += [(name, form) for form in forms(
            value, unquoted, value.replace("%%", "%"), unquoted.replace("%%", "%"),
            re.split(r"[ \t][;#]", value)[0].strip(), *[interpolated(written, own, defaults) for own in places
                                                        for written in (value, unquoted)],
            *re.split(r"%\([^)]*\)s", unquoted.replace("%%", "%")))]
    return found


def properties_unescape(raw, number):
    """A .properties key or value as Java reads it: \\uXXXX (a surrogate pair joined into its character), \\t \\n \\r
    \\f, and a backslash before any other character is that character. A \\u escape without four hexadecimal digits
    is Unreadable, naming the line."""
    def one(escape):
        body = escape.group(1)
        if body[0] == "u" and not re.fullmatch(r"u[0-9a-fA-F]{4}", body):
            raise Unreadable("line %d: a \\u escape without four hexadecimal digits" % number)
        return chr(int(body[1:], 16)) if body[0] == "u" else {"t": "\t", "n": "\n", "r": "\r", "f": "\f"}.get(
            body, body)
    text = PROPERTIES_ESCAPE.sub(one, raw)
    try:
        return text.encode("utf-16", "surrogatepass").decode("utf-16")
    except UnicodeDecodeError:   # a lone surrogate stays as it is
        return text


def properties_values(text, label):
    """(name, value) for every value in a Java .properties file: blank lines, comment lines (# or !), and key = value,
    key: value or key value — the key ending at the first '=', ':' or space not escaped — where a line ending in an odd
    number of backslashes goes on on the next line, that line's leading space dropped. Each value decoded as Java reads
    it (properties_unescape) from UTF-8 text and, as Properties.load(InputStream) does, from ISO-8859-1 (latin1); as
    written; without one pair of surrounding quotes; and line by line — named after its decoded key. A line that is only
    a key is a bare value, and a key that is not written as a name (a base64 token) makes its line a bare token (bare),
    both named after the file. A line it cannot read (a \\u escape without four hexadecimal digits) is Unreadable."""
    found, lines, row = [], text.split("\n"), 0
    while row < len(lines):
        number, pieces, row = row + 1, [lines[row].lstrip(" \t\f")], row + 1
        if not pieces[0] or pieces[0][0] in "#!":
            continue
        while (len(pieces[-1]) - len(pieces[-1].rstrip("\\"))) % 2:   # an odd number of backslashes: it goes on
            pieces[-1] = pieces[-1][:-1]
            if row == len(lines):
                break
            pieces, row = pieces + [lines[row].lstrip(" \t\f")], row + 1
        logical = "".join(pieces)
        key = PROPERTIES_KEY.match(logical)
        start = PROPERTIES_SEPARATOR.match(logical, key.end()).end()
        raw, name = logical[start:], properties_unescape(key.group(), number)
        value = properties_unescape(raw, number)
        texts = [value, raw, value[1:-1] if len(value) > 1 and value[0] == value[-1] and value[0] in "\"'" else None,
                 properties_unescape(latin1(raw), number)] + ([pieces[0][start:]] + pieces[1:]
                                                              if start <= len(pieces[0]) else [raw])
        if key.end() == len(logical):   # a key alone, no value: a bare value
            found += bare(logical, label) + [(label + BARE, form) for form in forms(
                name, properties_unescape(latin1(key.group()), number))]
        elif token_like(name, raw):     # a base64 token, never a name
            found += bare(logical, label) + [(label + BARE, form) for form in forms(*texts)]
        else:
            found += [(name, form) for form in forms(*texts)]
    return found


def text_values(text, label):
    """The values of a file in no format this tool reads — a document, source code, a log, a backup, a file with no
    extension whose first option comes before any [section], a YAML template — masked as written, not decoded, line by
    line and by the NAME=VALUE pairs on its lines: every line, stripped (a bare token also as its token, bare), and
    every value values_in finds, all named after the file; evidence.py adds each part of each (its words and members).
    A value standing in such a file neither as a line, nor after a name, nor as a member between spaces, commas,
    semicolons, brackets or quotes — a part cut out of a word — is not masked when printed alone."""
    return [pair for line in text.split("\n") for pair in bare(line, label, always=False)] + [
        (label, value) for _, _, value in values_in(text, label)]
