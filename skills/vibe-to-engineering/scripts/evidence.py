#!/usr/bin/env python3
"""Run one check and keep its output as evidence, with every secret value masked.

    python3 evidence.py --project <project> --out <project>/.vibe-to-engineering/evidence/<step>/<name>.txt \\
        [--env NAME=VALUE]… -- <command> [<argument>…]          (Windows: py -3 evidence.py …)

Standard library only. The command runs in the project folder, with each --env setting added to its environment — how a
check is pointed at throwaway data. Its output, standard output and error together, is printed and saved with secret
values masked. The values come from the project's secret files (.env and its variants, key, credential and certificate
files — read here for masking, never shown), each read whole by the one reader its name calls for (the readers are in
secretformats.py): a key file (every line, every piece of a line, each armored body joined); JSON (and any secret file
that is one JSON document); YAML (mappings, lists, plain, quoted, block and flow values, anchors, tags and aliases);
TOML (tables, every string form, arrays, inline tables); Java .properties (escapes, continued lines); INI (a [section]
before the first option, continued values); .env (NAME=VALUE, a name starting with a digit, export, quoted over several
lines, an inline comment, ${NAME} references, a bare line or base64 token) — a data-format extension before a .env name,
so .env.yaml is YAML, and a YAML file whose reader stops at a line holding a {{ or {% template marker is read as text; a
file that is one JSON document is read as JSON too — and any other
file (a document, source code, a log, a file with no extension whose first option comes before any [section]) line by
line, by its NAME=VALUE pairs and by the words and members of its lines, masked as written, not decoded. A value is
masked in every form it may be printed in: as written; decoded as each standard reader of its format reads it (JSON,
PyYAML, tomllib, configparser filling in %(name)s, Java from UTF-8 and ISO-8859-1, python-dotenv, Node, a shell);
stripped, line by line, around and with its ${NAME} references filled in, as the number or the date a reader makes of
it; each value named inside it (NAME=VALUE in a list, a URL's password=…, a connection string's Password=…); and each
part a check may print alone (its first word, its members, a URL's password, its query values, percent-decoded). A
setting's name with nothing after it (API_KEY=) holds no value; a would-be name that is not a name (a base64 or base32
token) is a value, never a name. A mask shows the name the file gave the value — for a value found inside another
value, or a part of one, the name of that value, never the text before its '=' or ':'; for a list's member, the list's
name — or the file's own name when that name holds text from any secret file; the summary of settings follows the same
rule. A value under a name that says secret (key, token, password…) is always masked; under any other name, a number or
a yes/no word is a setting, left readable and named in the summary — never a list's member, and never a number found
inside another value unless it was given with '=' to a setting's name (PORT=8000 in a list). Anything shaped like a
private key, an access token or a password is masked wherever it appears, and so is anything printed after a name that
says secret and '=' or ':'. Every match is found in the output as the check printed it before any is replaced, so masking
one value never hides another from these rules. A secret file that is a
link is read through the link; a folder that cannot be listed, or a linked folder, stops the run before the check,
because secret files inside it would not be found — and so does a secret file this tool cannot read completely (binary,
an encoding without a byte order mark, or anything its reader does not understand, such as a quote never closed),
because its values could not be masked. The evidence file is replaced whole, and it must lie inside the project's
.vibe-to-engineering/evidence/ folder.

Exit codes: the command's own; 1 when it could not run; 2 usage, a refused evidence path, or secret files that
could not be gathered or read completely.
"""

import argparse
import codecs
import fnmatch
import os
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # the modules beside this file
from checkpoint import STATE_DIR, resolve_project  # noqa: E402
from gitrun import Fail, configure_output, is_link, write_lf  # noqa: E402
from secretformats import (Unreadable, commented, dotenv_values, ini_values, json_values, key_values,  # noqa: E402
                           properties_values, text_values, toml_values, values_in, yaml_values)
from secretforms import BARE, LIST, SECRET_NAME, parts, worth  # noqa: E402
from watched import SECRET_FILES, UNWATCHED_FOLDERS  # noqa: E402 — one list of secret files

BOMS = ((codecs.BOM_UTF8, "utf-8-sig"), (codecs.BOM_UTF32_LE, "utf-32"), (codecs.BOM_UTF32_BE, "utf-32"),
        (codecs.BOM_UTF16_LE, "utf-16"), (codecs.BOM_UTF16_BE, "utf-16"))  # UTF-32 first: its mark begins like UTF-16's
SETTING = re.compile(r"(?i)[0-9][0-9._-]*|true|false|yes|no|on|off|null|none")  # a number or a yes/no word
LARGEST_SECRET_FILE = 1 << 20  # a secret file bigger than this is not a secret file
SHAPES = (  # secret values recognized wherever they appear
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----", re.S),
    re.compile(r"\b(?:sk|pk|rk)_(?:live|test)_[A-Za-z0-9]{8,}"),                  # Stripe
    re.compile(r"\bsk-[A-Za-z0-9_-]{16,}"),                                        # OpenAI, Anthropic and others
    re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,})"),  # GitHub
    re.compile(r"\bxox[abprs]-[A-Za-z0-9-]{10,}"),                                 # Slack
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),                                           # AWS access key id
    re.compile(r"\bAIza[0-9A-Za-z_-]{35}"),                                        # Google API key
    re.compile(r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}"),  # a JSON web token
)
# A value given to a name that says it is secret: API_KEY=…, "password": "…", token: …
WORD = re.compile(r"[\w-]")   # a character that joins a word, for the whole-word rule
NAMED = re.compile(r"""(?i)\b([A-Za-z0-9_.-]*(?:key|secret|token|passw(?:or)?d|pwd|credential|private|salt|pin)"""
                   r"""[A-Za-z0-9_.-]*)(["']?\s*[:=]\s*["']?)(?!<masked)([^\s"',;]+)""")

# Which reader a secret file goes to, by its lower-cased name (JSON also by its text: see read_secret). A data-format
# extension is looked at before the .env names, so .env.yaml is YAML, .env.json JSON and .env.local still .env.
KEY_FILES = ("*.pem", "*.key", "id_rsa*", "id_ecdsa*", "id_ed25519*", "*.p12", "*.pfx", "*.keystore", "*.jks")
YAML_FILES, TOML_FILES, INI_FILES = ("*.yaml", "*.yml"), ("*.toml",), ("*.ini", "*.cfg", "*.conf")
PROPERTIES_FILES, DOTENV_FILES = ("*.properties",), (".env", ".env.*", "*.env")
SECTION_FIRST = re.compile(r"(?:[ \t]*(?:[#;].*)?\n)*[ \t]*\[")  # INI: blank and comment lines, then a [section]


def named(outer, name, how, part, label):
    """The name a value found inside another value (under `outer`) is masked under: always the name of the value it
    was found in, never the text before its '=' or ':' — that text may be part of a password (monkey:Banana77,
    pinwheelKey=Orbit6620), and a mask's name, or the summary of settings, would show it. A part of a value (how
    "part") follows its value's name. Under a name that says nothing secret, a number or a yes/no word found inside a
    value is a setting, as the owner's rule reads a number there (PORT=8000 in a compose file's environment list, the
    port in http://localhost:8000) — unless the name it was given inside says secret (DB_PIN=4821), or it is a URL's
    password (how "password"): then it is named "secret in …" and stays masked. For a key file or a file read as text,
    everything takes the file's name (`label`)."""
    if label:
        return "secret in " + label if how == "password" and not SECRET_NAME.search(label) and SETTING.fullmatch(
            part) else label
    if how == "part" or SECRET_NAME.search(outer) or not SETTING.fullmatch(part):
        return outer
    return "secret in " + outer if how == "password" or (name and SECRET_NAME.search(name)) else outer


def inner(pairs, label=None):
    """pairs, then every value given a name inside one of their values, as written and decoded (the line scan,
    values_in: a list entry NAME=VALUE, a URL's password=…, a connection string's Password=…, each piece also cut at
    '&', ';' and '?'), then each part of every value a check may print alone (parts: its first word, its text up to a
    ',' ';' or '}', its members, a URL's password and query values, percent-decoded) — each named by named(). For a key
    file or a file read as text (`label`), a part is a word of four signs or more, or of two or three that is not only
    letters, and never a number or a yes/no word alone: in a document or a log those are its prose, not its secrets. A
    part is never a name holding a secret word (worth): in a list of field names it names a field."""
    found = list(pairs)
    for outer, value in dict.fromkeys(pairs):
        if re.search(r"[=:]", value):
            found += [(named(outer, name, sign, part, label), part)
                      for name, sign, part in values_in(value, label or outer)]
    for outer, value in dict.fromkeys(found):
        found += [(named(outer, name, how, part, label), part) for name, part, how in parts(value)
                  if worth(part) and (re.search(r"\w", part) or len(part) > 3) and (not label or (
                      len(part) > 3 or (len(part) > 1 and not part.isalpha())) and not SETTING.fullmatch(part))]
    return found


def member(name, value):
    """The name a value is masked under, once a reader has marked it a list's member (LIST) or a line that gives no
    name a value (BARE): the list's name or the file's — or, for a number or a yes/no word, "secret in" it. Neither has
    a name of its own that could make it a setting: a list of recovery codes or PINs under a name that says nothing
    secret, or a bare 482193 in a .env file, stays masked."""
    if not name.endswith((LIST, BARE)):
        return name
    name = name[:-len(LIST)]   # LIST and BARE are as long as each other
    return "secret in " + name if SETTING.fullmatch(value) and not SECRET_NAME.search(name) else name


def read_secret(label, text):
    """(name, value) for every value a secret file holds, from the one reader its lower-cased name calls for: a key
    file; the data formats, before the .env names — YAML (a file whose reader stops at a line holding a {{ or {% template
    marker is a Helm or Go template, read as text), TOML, Java .properties, INI (a [section] before the first option,
    as configparser needs); a .env file; a file with no extension as INI when a [section] comes first and it reads as
    INI, else as text; a *.json file as JSON; anything else as text. A file whose text is one JSON document is also
    read as JSON (and only as JSON when its own reader cannot read it). A data format's comments add the secrets kept
    in them (commented). Then every value named inside a value and every part of a value (inner), and each value's
    stripped form — never a text with nothing in it, or only a setting's name and its '=' (worth). Unreadable when
    the reader cannot read it all."""
    name, pairs = label.lower(), None
    plain, is_json = not os.path.splitext(name)[1], fnmatch.fnmatchcase(name, "*.json")

    def called(patterns):
        return any(fnmatch.fnmatchcase(name, pattern) for pattern in patterns)

    def resolved(found):
        return [(member(key, value), value) for key, value in found]
    try:
        document = resolved(json_values(text, label)) if text.strip()[:1] in ("{", "[") or is_json else None
    except ValueError:
        if is_json and text.strip():
            raise Unreadable("it is not one JSON document")
        document = None
    reader, own = text_values, label   # own: the file's name, for a reader that names every value after the file
    if called(KEY_FILES):
        reader = key_values
    elif called(YAML_FILES):
        reader, own = yaml_values, None
    elif called(TOML_FILES) or called(PROPERTIES_FILES):
        reader, own = toml_values if called(TOML_FILES) else properties_values, None
    elif called(INI_FILES):
        reader, own = ini_values, None
    elif plain and not called(DOTENV_FILES):
        reader, own = (ini_values, None) if SECTION_FIRST.match(text) else (text_values, label)
    elif called(DOTENV_FILES):
        reader, own = dotenv_values, None
    if document is not None and (is_json or reader is text_values):
        pairs = inner(document)
    else:
        try:
            pairs = inner(resolved(reader(text, label) + (commented(text, label) if own is None else []))
                          + (document or []), own)
        except Unreadable as error:
            line = text.split("\n")[error.line - 1] if error.line else ""
            if document is not None:
                pairs = inner(document)   # one JSON document in a file its own reader cannot read
            elif (reader is yaml_values and re.search(r"\{\{|\{%", line)) or (reader is ini_values and plain):
                pairs = inner(resolved(text_values(text, label)), label)   # a template, or no extension, not INI
            else:
                raise
    return [(key, value) for key, value in pairs + [(key, value.strip()) for key, value in pairs
                                                    if value.strip() != value] if worth(value)]


def named_safely(triples):
    """(name, value) for every (name, value, file) with a value — never one made only of '=' (a base64 token's
    padding), which would mask every '=' — and every name that holds a value from any secret file, or no name,
    replaced by its file's name ("secret file" when that holds one), still saying secret when the name did (a PIN
    stays masked): any value of two characters or more anywhere in the name (QXZ in backupQXZkey), a one-character
    value as a whole word of it — and a name shaped like a secret itself (a token used as a key, api_key=… as an
    option), or holding a control character (a key decoded from \\u0000). A mask never shows secret text as its name,
    nor does the summary of settings left readable."""
    triples = [(name, value, label) for name, value, label in triples if re.sub(r"[\s=]+", "", value)]
    values = {value for _, value, _ in triples if len(value) >= 4}
    short, names = {value for _, value, _ in triples if len(value) < 4}, {}
    mixed = {value for value in short if len(value) > 1}

    def holds(name):
        if name not in names:
            names[name] = not name.strip() or re.search(r"[\x00-\x1f\x7f]", name) is not None or any(
                shape.search(name) for shape in SHAPES) or NAMED.search(name) is not None or any(
                word in short for word in re.split(r"[\W_]+", name)) or any(value in name for value in mixed) or (
                any(name[a:b] in values for a in range(len(name)) for b in range(a + 4, len(name) + 1))
                if len(name) * len(name) < 2 * len(values) else any(value in name for value in values))
        return names[name]

    def safe(name, label):
        label = "secret file" if holds(label) else label
        return label if SECRET_NAME.search(label) or not SECRET_NAME.search(name) else "secret in " + label
    return [(safe(name, label) if holds(name) else name, value) for name, value, label in triples]


def secret_text(path):
    """A secret file's text: decoded by its byte order mark (UTF-8, UTF-16, UTF-32), otherwise as UTF-8. A file that
    is not text this tool can read — bytes that are not UTF-8, or a NUL character, as in UTF-16 without a mark or a
    binary key container — stops the run: its values could not be masked."""
    data = Path(path).read_bytes()
    encoding = next((encoding for mark, encoding in BOMS if data.startswith(mark)), "utf-8")
    try:
        text = data.decode(encoding)
    except UnicodeDecodeError:
        text = "\0"
    if "\0" in text:
        raise Fail("%s is not text this tool can read (binary, or an encoding without a byte order mark), so its "
                   "values cannot be masked — keep it outside the project for the migration" % path)
    return text


def secret_files(project):
    """Every secret file in the project, outside dependency, build-output and cache folders — through a link to a
    plain file too. A folder that cannot be listed, or that is a link, stops the run: a secret file inside it would
    not be found, and its values would reach the evidence unmasked."""
    def unreadable(error):
        raise Fail("cannot list the folder %s to find secret files (%s)" % (error.filename, error.strerror or error))
    found = []
    for folder, dirs, names in os.walk(str(project), onerror=unreadable):
        kept = []
        for name in dirs:
            path = os.path.join(folder, name)
            if name in UNWATCHED_FOLDERS or name in (".git", STATE_DIR):
                continue
            if is_link(path):
                raise Fail("%s is a link to a folder — secret files inside it would not be found; run the check "
                           "with that folder in place, or add it to the plan as out of scope" % path)
            kept.append(name)
        dirs[:] = kept
        for name in names:
            if any(fnmatch.fnmatchcase(name.lower(), pattern) for pattern in SECRET_FILES):
                found.append(os.path.join(folder, name))
    return found


def secret_values(project):
    """(name, value) for every value the project's secret files hold, each file read whole by the one reader its name
    calls for (read_secret): key files, .env, JSON, YAML, TOML, Java .properties, INI, and any other file line by
    line, as written. A secret file that cannot be read, is not text this tool can read, or that its reader cannot
    understand completely stops the run before the check, naming the file and the line, never its text: its values
    could not be masked."""
    found = []
    for path in secret_files(project):
        try:
            if not os.path.isfile(path):  # a link to nothing, or to a folder: no values to mask
                continue
            if os.path.getsize(path) > LARGEST_SECRET_FILE:
                raise Fail("%s is larger than a secret file (%d bytes) — its values cannot be masked" % (path, os.path.getsize(path)))
            text = secret_text(path)
        except OSError as error:
            raise Fail("cannot read %s to mask its values (%s)" % (path, error.strerror or error))
        try:
            pairs = read_secret(os.path.basename(path), text.replace("\r\n", "\n").replace("\r", "\n"))
            if re.search(r"\r(?!\n)", text):   # a lone carriage return: also as Node reads it, which drops it
                try:
                    pairs += read_secret(os.path.basename(path), text.replace("\r\n", "\n").replace("\r", ""))
                except Unreadable:
                    pass   # read already, as a line break: every value this reading has is masked
        except Unreadable as error:
            raise Fail("%s: %s — its values cannot be masked; keep it outside the project for the migration"
                       % (path, error))
        except Exception:  # any other failure to read it stops the run too, without showing the file's text
            raise Fail("%s: it is not written in a form this tool reads — its values cannot be masked; keep it "
                       "outside the project for the migration" % path)
        found += [(member(name, value), value, os.path.basename(path)) for name, value in pairs]   # no mark left
    return named_safely(found)


def classify(values):
    """The values to mask, longest first, and the names of settings left readable: a number or a yes/no word under
    a name that does not say secret."""
    masked, settings = {}, []
    for name, value in values:
        if not SECRET_NAME.search(name) and SETTING.fullmatch(value):
            settings.append(name)
        else:
            masked.setdefault(value, name)
    return sorted(masked.items(), key=lambda item: -len(item[0])), sorted(dict.fromkeys(settings))


def mask(text, values):
    """text with every secret value replaced, and how many were. Values are matched as they always were, longest first:
    a value under four characters, or all digits, only where it stands as a whole word — a PIN of 1234 is not the
    inside of 12345 — and every other value wherever it appears; a value masked already counts as the edge of a word,
    as its mask did (48213377 glued to a masked token is masked too). Then anything shaped like a secret, and a value
    given to a name that says secret — each looked for both in the text as the check printed it, so that a masked piece
    of a name never hides DB_PASSWORD=… from the net, and in that text with the values found blanked out, so that a
    value masked right before a token or a name never hides it either. Every match is found before anything is
    replaced; matches that overlap are masked as one."""
    covered, spans = bytearray(len(text)), []

    def word_at(at):   # a character that joins a word; a masked one, or none, is the edge of a word
        return 0 <= at < len(text) and not covered[at] and WORD.match(text, at) is not None
    for value, name in values:
        label, size, whole = "<masked %s>" % name, len(value), len(value) < 4 or value.isdigit()
        at = text.find(value)
        while at >= 0:
            end = at + size
            if not whole or (not any(covered[at:end]) and not word_at(at - 1) and not word_at(end)):
                spans.append((at, end, label))
                covered[at:end] = b"\x01" * size
                at = text.find(value, end)
            else:
                at = text.find(value, at + 1)
    pieces, done = [], 0
    for run in re.finditer(rb"\x01+", bytes(covered)):   # the text with every value found blanked out
        pieces += [text[done:run.start()], "\x01" * (run.end() - run.start())]
        done = run.end()
    view = "".join(pieces) + text[done:]
    for source in (text, view) if view != text else (text,):
        for shape in SHAPES:
            spans += [(found.start(), found.end(), "<masked>") for found in shape.finditer(source)]
        spans += [(found.start(3), found.end(3), "<masked>") for found in NAMED.finditer(source)]
    out, done, merged = [], 0, []
    for start, end, label in sorted(spans, key=lambda span: (span[0], -span[1])):   # a value's own mask first
        if merged and start < merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end, label])
    for start, end, label in merged:
        out += [text[done:start], label]
        done = end
    return "".join(out) + text[done:], len(merged)


def evidence_path(project, raw):
    """The evidence file, refused unless — every link and '..' resolved — it lies inside
    <project>/.vibe-to-engineering/evidence/, so the output can only land there."""
    if not (project / STATE_DIR).is_dir():
        raise Fail("%s is not there yet: evidence is kept only after the plan exists" % (project / STATE_DIR))
    folder = project / STATE_DIR / "evidence"
    out = Path(os.path.realpath(os.path.abspath(os.path.expanduser(raw))))
    if folder not in out.parents:
        raise Fail("the evidence file must be inside %s, not %s" % (folder, out))
    return out


def main(argv=None):
    configure_output()
    parser = argparse.ArgumentParser(prog="evidence.py", description="Run one check and keep its output as evidence, "
                                                                     "with secret values masked.")
    parser.add_argument("--project", default=".", help="the project folder (default: the current folder)")
    parser.add_argument("--out", required=True, help="the evidence file, inside .vibe-to-engineering/evidence/")
    parser.add_argument("--env", action="append", default=[], metavar="NAME=VALUE",
                        help="add to the check's environment (repeatable)")
    parser.add_argument("command", nargs=argparse.REMAINDER, help="-- then the check's command and arguments")
    args = parser.parse_args(argv)
    command = args.command[1:] if args.command[:1] == ["--"] else args.command
    if not command or any("=" not in setting for setting in args.env):
        parser.error("give the check after --, and every --env as NAME=VALUE")
    try:
        project = resolve_project(args.project)
        out = evidence_path(project, args.out)
        values, settings = classify(secret_values(project))
    except Fail as error:
        print("evidence.py: error: %s" % error, file=sys.stderr)
        return 2
    env = dict(os.environ, **dict(setting.split("=", 1) for setting in args.env))
    try:
        done = subprocess.run(command, cwd=str(project), env=env, stdin=subprocess.DEVNULL,
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    except OSError as error:
        print("evidence.py: error: cannot run %s (%s)" % (command[0], error.strerror or error), file=sys.stderr)
        return 1
    header = "$ %s\n%s" % (" ".join(command), "".join("  with %s\n" % setting for setting in args.env))
    text, masked = mask(header + "\n" + done.stdout.decode("utf-8", "replace"), values)
    try:
        write_lf(out, text)
    except OSError as error:
        print("evidence.py: error: cannot write %s (%s)" % (out, error.strerror or error), file=sys.stderr)
        return 1
    print(text, end="" if text.endswith("\n") else "\n")
    code = done.returncode if done.returncode >= 0 else 1   # a check stopped by a signal failed
    print("evidence.py: exit code %d; saved to %s (%d secret %s masked%s)"
          % (done.returncode, out, masked, "value" if masked == 1 else "values",
             "; settings left readable: " + ", ".join(settings) if settings else ""), file=sys.stderr)
    return code


if __name__ == "__main__":
    sys.exit(main())
