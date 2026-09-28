"""The environment-dependent readings of Node's .env loaders. Standard library only.

STATUS (2026-09-28, the v0.1 literal .env boundary, A1): nothing calls this module any more — the .env reader
(secretformats.dotenv_values) admits only literal files (envliteral.py) and refuses every form these models
covered, interpolation included. The module is retained unmodified as the provenance record of the rounds
that built it (the loader-profile survey behind the registry's Node version bounds, and old npm dotenv's
interpolation model); no capability is claimed from it. Its physical removal is a separate owner decision.

The loaders, each ported from its own source: Node's own (--env-file; process.loadEnvFile() and util.parseEnv() from
v20.12) from v20.7, when it began to keep an inherited value — to v21.6 a line at a time (line_keys), v20.12 to v22.0 a
regular expression taken from npm dotenv, searched for anywhere (regex_keys), then its own parser: to v23.11 in five
forms (parser_keys), v24's since v22.16 (parser_keys_v24) — and npm dotenv from v0.1.1, when it began to keep one: since
v15 with that expression from a line's start (v15's without its `…` alternative), before that line by line
(regex_keys), and at first the text before a line's first '=' (split_keys); and v18's opt-in fast parser (fast_keys).
Every key any of them reads counts (node_keys): which Node, or which dotenv, runs the check is not known here.

Under the constructed environment (NEW-5 stage 1) these readings no longer stop the run: a loader that keeps the
environment's value over the file's keeps a value this tool built — the mapping is known exactly, so the reading is
computed from it, and a declared --env value that wins is masked as the winner (evidence.py). Old npm dotenv's
interpolation (v0.4–1.2: a value starting with '$' is replaced whole by what the name the rest of it forms resolves
to, from the file's keys so far, then the process's environment) is likewise computed from those known inputs
(old_npm_interpolated) — never guessed.
"""

import bisect
import re

SPACE = "\t\v\f \u00a0\u1680\u2000-\u200a\u2028\u2029\u202f\u205f\u3000\ufeff"   # JavaScript's \s, less \n and \r
BREAK = "\n\r\u2028\u2029"   # where JavaScript's ^ and $ may meet, and its . may not
# npm dotenv's LINE, after the white space it starts with: Node v20.12 to v22.0 took it into C++ (std::regex: \s is
# ASCII's) without its ^ and $. A key never starts inside a word (see regex_keys), so none is looked for there
LINE = (r"(?:export{s}+)?(?<![\w.-])([\w.-]+)(?:{s}*={s}*?|:{s}+?)({s}*'(?:\\'|[^'])*'|{s}*\"(?:\\\"|[^\"])*\"|{s}*`"
        r"(?:\\`|[^`])*`|[^#\r\n]+)?{s}*(?:#{dot}*)?")
NODE_LINE = re.compile(LINE.format(s=r"[ \t\n\v\f\r]", dot="."), re.ASCII)
NPM_LINE = re.compile(LINE.format(s="[%s\n\r]" % SPACE, dot="[^%s]" % BREAK) + "(?=[%s]|\\Z)" % BREAK, re.ASCII)
# npm dotenv v15 read no `…` value: a key inside one, on a later line, is a key to it
NPM15_LINE = re.compile(LINE.replace(r"{s}*`(?:\\`|[^`])*`|", "").format(s="[%s\n\r]" % SPACE, dot="[^%s]" % BREAK)
                        + "(?=[%s]|\\Z)" % BREAK, re.ASCII)
SOLID = {NODE_LINE: re.compile(r"[^ \t\n\v\f\r]"), NPM_LINE: re.compile("[^%s\n\r]" % SPACE),
         NPM15_LINE: re.compile("[^%s\n\r]" % SPACE)}
LINE_END = re.compile("[%s]" % BREAK)
NPM_OLD = re.compile(r"(?:^|(?<=\n))[%s]*([\w.-]+)[%s]*=" % (SPACE, SPACE), re.ASCII)   # before v15: line by line


def regex_keys(text):
    """(offset, key) for each key the regular expressions read in text, each of its line breaks a \\n as these loaders
    make them: Node v20.12 to v22.0's LINE from anywhere its last match ended, npm dotenv's from a line's start (a line
    ends at \\n, \\r, U+2028 or U+2029) — v16 on, and v15's, with no `…` value — each after the white space it may
    start with; and npm dotenv's before v15. Each place a match may start is tried once, as the first character after
    white space: trying it again from within that space finds the same, and a match never ends inside a word — so a
    key is never looked for from there either."""
    found = []
    for pattern, anywhere in ((NODE_LINE, True), (NPM_LINE, False), (NPM15_LINE, False)):
        solid = SOLID[pattern].search(text)
        while solid:
            match = pattern.match(text, solid.start())
            found += [(match.start(1), match.group(1))] if match else []
            at = match.end() if match else solid.start() + 1
            if not anywhere:   # npm dotenv tries again from the next line's start
                end = LINE_END.search(text, match.end() if match else solid.start())
                at = end.end() if end else len(text) + 1
            solid = SOLID[pattern].search(text, at) if at <= len(text) else None
    return found + [(match.start(1), match.group(1)) for match in NPM_OLD.finditer(text)]


def finder(text, char):
    """next(at, end): where `char` next stands in text[at:end], or -1 — from its places, found once (searching the text
    on from each key in turn would take as long squared on a long line of short keys)."""
    places = [match.start() for match in re.finditer(re.escape(char), text)]

    def next_one(at, end):
        k = bisect.bisect_left(places, at)
        return places[k] if k < len(places) and places[k] < end else -1
    return next_one


def line_keys(written):
    """(offset, key) for each key Node v20.7 to v21.6 read in the file as written, a line (to each \\n) at a time: the
    text before its first '=', white space ("C" locale) taken off, 'export ' and all — unless it is empty or starts
    with #, or its value starts with a quote that line never has again."""
    found, at = [], 0
    for line in written.split("\n"):
        key, _, value = line.partition("=")
        key = key.strip(" \t\n\v\f\r") if "=" in line else ""
        if key and key[0] != "#" and not (value[:1] in ("'", '"', "`") and value.find(value[0], 1) < 0):
            found.append((at, key))
        at += len(line) + 1
    return found


# Node's own parser from v20.13 to v23.11 changed from release to release (the round-9 handoff's r9-node-variants,
# compiled from each release's source): A v20.13 to v20.16, v22.1 to v22.5; B v20.17, v20.18, v22.6 to v23.3 — a value's
# spaces taken off before its quote is looked for; D v20.19.0 to v20.19.4, v22.13 to v23.8 — and the text kept where no
# line break follows a value; C v20.19.5 to v20.20 — a line with no '=' skipped, each line break passed, nothing read
# after the last value; E v22.15, v23.9 to v23.11 — as D, tabs and line breaks trimmed too, a key with no value kept
VARIANTS = "ABCDE"


def parser_keys(text, variant):
    """(offset, key) for each key Node's own parser reads in text, each carriage return taken out, as `variant` (above)
    reads it — its ParseContent step by step: a key is the text to the next '=', trimmed, one 'export ' taken off; a
    line that starts with # or is blank is skipped when a line break follows it; a quoted value runs to the same quote,
    on any line; one never closed, and an unquoted one, to its line's end. Where no line break follows a value, A and B
    move the text a character back (a string view's remove_prefix(npos)); D and E read it again, C reads no more; and
    A to D's trim_spaces takes a text of spaces only to the character before it (the same npos; measured, v20.20.2)."""
    space, nl, eq = " \t\n" if variant == "E" else " ", finder(text, "\n"), finder(text, "=")

    def view(i, j):
        return (i, j) if 0 <= i < j else None

    def trim(i, j):   # trim_spaces(text[i:j]), or None for an empty result
        if i >= j:
            return None
        start = i
        while start < j and text[start] in space:
            start += 1
        if variant == "E" or text[i] == " ":   # E trims whatever it starts with; A to D only a space
            i = start if start < j or variant == "E" else i - 1
        stop = j
        while stop > max(i, 0) and text[stop - 1] in space:
            stop -= 1
        return view(i, stop if variant == "E" or text[j - 1] == " " else j)
    found, content = [], trim(0, len(text))
    while content:
        i, j = content
        newline = nl(i, j)
        if text[i] in "\n#" and newline >= 0:
            content = view(newline + 1, j)
            continue
        equal = eq(i, j)
        if equal < 0:   # no key after it (C passes one line at a time, finding none: not run, it takes as long squared)
            break
        key, content = trim(i, equal), view(equal + 1, j)
        if variant == "E" and (content is None or text[equal + 1] == "\n"):   # a key with no value: kept as it is
            found.append((i, text[key[0]:key[1]] if key else ""))
            continue
        content = trim(*content) if content and variant != "A" else content
        if not key:
            break
        name = text[key[0]:key[1]]
        name = name[7:] if name.startswith("export ") else name
        if not content:
            found.append((key[0], name))
            break
        i, j = content
        close = text.find(text[i], i + 1, j) if text[i] in "'\"`" else i
        newline = nl(i if close < 0 else close + (close > i), j)
        found += [(key[0], name)] if close >= 0 or newline >= 0 else []   # a quote never closed, the last line: none
        if newline >= 0:
            content = view(newline + (variant == "C"), j)
        elif close >= 0 and variant == "C":
            content = None
        elif i < close and variant in "AB":
            content = view(i - 1, j)
    return found


def parser_keys_v24(text):
    """(offset, key) for each key Node v24's parser reads in text, each carriage return taken out: a key is the text
    before an '=' on its own line, spaces, tabs and line breaks taken off it (after one 'export ' too, which is taken
    off); a line that starts with # or is blank, or has no '=', is skipped; a quoted value runs to the same quote on any
    line after, one never closed to its line's end. The text after each line has its spaces, tabs and line breaks
    taken off first, as after a key with no value; a key with no value keeps its 'export '."""
    found, space, nl, eq = [], " \t\n", finder(text, "\n"), finder(text, "=")
    i, end = len(text) - len(text.lstrip(space)), len(text.rstrip(space))

    def trimmed(at):
        while at < end and text[at] in space:
            at += 1
        return at
    while i < end:
        if text[i] in "\n#":
            if nl(i, end) < 0:
                break
            i = nl(i, end) + 1
            continue
        stop = min([at for at in (eq(i, end), nl(i, end)) if at >= 0] or [-1])
        if stop < 0:
            break
        if text[stop] == "\n":
            i = trimmed(stop + 1)
            continue
        start, key, i = i, text[i:stop].strip(space), stop + 1
        if i >= end or text[i] == "\n":
            found.append((start, key))
            continue
        i = trimmed(i)
        if not key:
            continue
        found.append((start, key[7:].strip(space) if key.startswith("export ") else key))
        if i >= end:
            break
        quoted = text[i] in "'\"`"
        close = text.find(text[i], i + 1, end) if quoted else -1
        newline = nl(close if close >= 0 else i, end)
        if newline < 0:
            break
        i = newline + 1 if close >= 0 else trimmed(newline + 1)
    return found


JS_SPACE = "\t\n\v\f\r       　﻿" + "".join(map(chr, range(0x2000, 0x200b)))
KEY_CHAR = set("0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz_.-")


def fast_keys(text, variant):
    """(offset, key) for each key npm dotenv's opt-in fast parser reads (parse(src, {fast: true}); DOTENV_CONFIG_FAST in
    the environment turns it on), each line break a \\n, as `variant` reads it: "0" v18.0.0 and v18.0.1 (only a space, a
    tab, a \\n or a byte order mark skipped between keys, none crossing a line before a value's quote), "2" v18.0.2 (any
    white space, a quote found across lines), "3" v18.0.3 on (and a line with no separator after 'export' read again
    from its own end) — its scanner step by step: a key is a run of [A-Za-z0-9_.-] after an 'export ' or not, then '='
    or ': '; a quoted value ends at its quote, the text after it read on as the next key's (v18.0.0), or only at a
    quote a line's end or # follows (v18.0.2 on); an unquoted one at its line's end."""
    n, found, i = len(text), [], 0
    skip, blank, ends = (" \t\n﻿", " \t", "\n") if variant == "0" else (JS_SPACE, JS_SPACE, "\n  ")
    nl, sharp = finder(text, "\n"), finder(text, "#")

    def line_end(at):
        while at < n and text[at] not in ends:
            at += 1
        return at
    while i < n:
        while i < n and text[i] in skip:
            i += 1
        if i >= n:
            break
        if text[i] == "#":
            i = line_end(i)
            continue
        export_end = -1
        if text.startswith("export", i) and i + 6 < n and text[i + 6] in blank:
            after = i + 7
            while after < n and text[after] in blank:
                after += 1
            if variant == "0":
                i = after
            elif after < n and text[after] in KEY_CHAR:   # else 'export' is the key itself
                export_end, i = i + 6, after
        start = i
        while i < n and text[i] in KEY_CHAR:
            i += 1
        key_end = i
        while start < i < n and text[i] in blank:
            i += 1
        separator = text[i:i + 1]
        if start == key_end or not (separator == "=" or separator == ":" and i + 1 < n and text[i + 1] in blank
                                    and (variant == "0" or i == key_end)):
            i = line_end(start if start == key_end else export_end if variant == "3" and export_end >= 0 else
                         key_end if variant != "0" else i)
            continue
        found.append((start, text[start:key_end]))
        i += 1 if separator == "=" or variant == "0" else 2
        quote = i
        while quote < n and text[quote] in (blank if variant == "0" else JS_SPACE):
            quote += 1
        close = -1
        if quote < n and text[quote] in "'\"`" and variant == "0":
            j = quote + 1
            while j < n and text[j] != text[quote]:
                j += 2 if text[j] == "\\" and j + 1 < n and text[j + 1] in (text[quote], "\\") else 1
            if j < n:
                close, i = j, j + 1
                while i < n and text[i] in blank:
                    i += 1
                i = line_end(i) if i < n and text[i] == "#" else i
            else:
                i = quote
        elif quote < n and text[quote] in "'\"`":
            j = text.find(text[quote], quote + 1)
            while j >= 0:
                end = j + 1
                while end < n and text[end] not in ends and text[end] in JS_SPACE:
                    end += 1
                if end == n or text[end] in ends or text[end] == "#":
                    close, i = j, end
                if text[j - 1] != "\\":
                    break
                j = text.find(text[quote], j + 1)
            i = line_end(i) if close >= 0 and i < n and text[i] == "#" else i
        if close < 0:   # unquoted, or a quote never closed: to the line's end, a # there to the end of its line
            line = nl(i, n) if nl(i, n) >= 0 else n
            hashed = sharp(i, line) if variant != "0" else -1
            i = line if hashed < 0 else line_end(hashed)
    return found


def split_keys(written):
    """(offset, key) for each key npm dotenv v0.1.1 to v0.2.0 read in the file as written: its lines (to each \\n, the
    file's white space trimmed off first), blank ones dropped, each the text before its first '=', trimmed — until a
    line with no '=', where the reading stops (its value's trim() throws, and ends the loop)."""
    found, at = [], len(written) - len(written.lstrip(JS_SPACE))
    for line in written.strip(JS_SPACE).split("\n"):
        if line.strip(JS_SPACE):
            if "=" not in line:
                break
            found.append((at, line.split("=", 1)[0].strip(JS_SPACE)))
        at += len(line) + 1
    return found


def node_keys(text, written):
    """(offset in text, key) for each key any loader above reads: `text`, the file with each line break a \\n;
    `written`, as it is written — Node's own parsers take its carriage returns out, v20.7 to v21.6 keep them."""
    plain, lone, removed = written.replace("\r", ""), [], 0   # lone: where a lone \r stood in plain, a \n in text
    for match in re.finditer(r"\r\n?", written):
        lone += [match.start() - removed] if match.group() == "\r" else []
        removed += 1
    pairs = [match.start() for match in re.finditer("\r\n", written)]   # each one a single \n in text
    return regex_keys(text) + [pair for variant in "023" for pair in fast_keys(text, variant)] + [
        (at + bisect.bisect_right(lone, at), key) for at, key in parser_keys_v24(plain) + [
        pair for variant in VARIANTS for pair in parser_keys(plain, variant)]] + [
        (at - bisect.bisect_left(pairs, at), key) for at, key in line_keys(written) + split_keys(written)]


# npm dotenv v0.4–1.2 (each release's own lib/main.js: 0.4.0, 0.5.0, 0.5.1, 1.0.0, 1.1.0, 1.2.0 — all identical here;
# 2.0.0 dropped it): after a line is read by its pattern below, the value — a double-quoted one's \n expanded first,
# then one leading and one trailing quote removed and the rest trimmed — when it starts with '$' is replaced whole by
# the value of the name the rest of it forms, looked up in the file's keys so far (each already resolved) and then in
# the process's environment, the first of them not empty, else empty; and '\$' anywhere this leaves at the start is
# unescaped to '$'
OLD_LINE = re.compile(r"[%s]*([A-Za-z0-9_.-]+)[%s]*=[%s]*(.*?)[%s]*$" % ((SPACE,) * 4), re.ASCII)
OLD_QUOTE = re.compile(r"^['\"]|['\"]$")   # one quote at each end, removed however they pair


def old_npm_interpolated(text, environ):
    """(key, value) for each value npm dotenv v0.4–1.2's interpolation resolves in a .env file, `text` with each line
    break a \\n: every value theirs that starts with '$', resolved from the file's own keys so far and the check's
    constructed environment alone (their `obj[name] || process.env[name] || ''` — an empty file value falls through to
    the environment, an unknown name to empty). Both sources are known exactly here, so the reading is computed, never
    guessed: what cannot be derived from them does not exist under the constructed environment."""
    values, found = {}, []
    for line in text.split("\n"):
        match = OLD_LINE.match(line)
        if not match:
            continue
        key, value = match.group(1), match.group(2)
        if value and value[0] == '"' and value[-1] == '"':
            value = value.replace("\\n", "\n")
        value = OLD_QUOTE.sub("", value).strip(SPACE)
        interpolated = value.startswith("$")
        if interpolated:
            value = values.get(value[1:]) or environ.get(value[1:]) or ""
        if value.startswith("\\$"):
            value = value[1:]
        values[key] = value
        if interpolated and value:
            found.append((key, value))
    return found
