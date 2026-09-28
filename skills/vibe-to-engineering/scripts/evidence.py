#!/usr/bin/env python3
"""Run one check and keep its output as evidence, with every secret value masked.

    python3 evidence.py --project <project> --out <project>/.vibe-to-engineering/evidence/<step>/<name>.txt \\
        [--with-path /abs/dir]… [--env NAME=VALUE]… -- <command> [<argument>…]          (Windows: py -3 evidence.py …)
    python3 evidence.py --enroll-runner <runner> [--with-path /abs/dir]…      enroll this user's runner (A2)

Standard library only. The command runs in the project folder with a constructed environment — nothing is
inherited: PATH is the system folders plus each --with-path folder (validated: absolute, existing, a real
directory, its name never holding the PATH separator — one folder enters PATH as exactly one entry — the
validated entries retained from construction, so the header records exactly what the child received, never a
mutable original argument resolved again after the run), HOME and TMPDIR are one fresh private folder made for the run (removed when
the run ends, and nothing else is — the object at its path is matched by identity before anything is deleted), the
locale and timezone are fixed — plus each --env setting, how a check is
pointed at throwaway data: NAME=VALUE, the name a shell's name, never one the constructed environment or the
prohibited set holds (the shells', runtimes', linkers', dotenv, package-manager, git and proxy configuration
channels), never given twice, never only whitespace and '=' (it could not be masked); the header records the
declared names, never their values, and no diagnostic shows one, even inside another argument. The check's runner
is resolved under the launch's own working directory and must be enrolled for this user (A2, R2-F5): enrollment
lives at ~/.vibe-to-engineering/runners.json and is a deliberate human act — python3 evidence.py --enroll-runner
<runner> shows the resolved executable's path, size and SHA-256 and, only after the human types the approval
word, runs the one disclosed profile probe and records the identity — and a routine run never executes a
candidate to validate it: the resolved path must be the enrolled one and the bytes there must hash to the
enrolled SHA-256, or the check is refused before anything runs. The bytes launched are the enrolled bytes: a
runner whose entire resolved path is proven root-owned, without group/other write permissions or ACLs,
launches at its enrolled path (pin path, rechecked each run). Any other enrolled runner (pin copy) launches
from a private copy written from the very bytes just hashed, inside the run's scratch root — a replaced
binary or a retargeted link between validation
and launch cannot substitute another program. A changed binary refuses and names manual re-enrollment as the
remedy; there is no automatic enrollment and no automatic re-enrollment, and a script under a runner's name is
never enrolled and never runs at all. Enrollment is not protection against an attacker who controls the user's
account. The one
constructed
mapping governs the secret-value analysis and the launch alike. Its output, standard output and error together,
is printed and saved with secret
values masked. The values come from the project's secret files (.env and its variants, key, credential and certificate
files — read here for masking, never shown), each read whole by the one reader its name calls for (the readers are in
secretformats.py): a key file (every line, every piece of a line, each armored body joined); JSON (and any secret file
that is one JSON document); YAML (mappings, lists, plain, quoted, block and flow values, anchors, tags — resolved
through the document's %TAG handles — and aliases);
TOML (tables, every string form, arrays, inline tables); Java .properties (escapes, continued lines); INI (a [section]
before the first option, continued values); .env (literal assignments only — the v0.1 boundary, envliteral.py:
[export ]NAME=VALUE with the probed quoting and character subset, no references, interpolation or expansion; anything
else refuses before launch) — a data-format extension before a .env name,
so .env.yaml is YAML, and a YAML file whose reader stops at a line holding a {{ or {% template marker is read as text; a
file that is one JSON document is read as JSON too — and any other
file (a document, source code, a log, a file with no extension whose first option comes before any [section]) line by
line, by its NAME=VALUE pairs and by the words and members of its lines, masked as written, not decoded. A value is
masked in every form it may be printed in: as written; decoded as each standard reader of its format reads it (JSON,
PyYAML, tomllib, configparser filling in %(name)s, Java from UTF-8 and ISO-8859-1; a .env value is the one decode
every claimed reader agrees on);
stripped, line by line, around and with its ${NAME} references filled in, as the number or the date a reader makes of
it; each value named inside it (NAME=VALUE in a list, a URL's password=…, a connection string's Password=…); and each
part a check may print alone (its first word, its members, a URL's password, its query values, percent-decoded). A
setting's name with nothing after it (API_KEY=) holds no value; a would-be name that is not a name (a base64 or base32
token) is a value, never a name. A mask shows the name the file gave the value — for a value found inside another
value, or a part of one, the name of that value, never the text before its '=' or ':'; for a list's member, the list's
name — or the file's own name when that name holds text from any secret file; the summary of settings follows the same
rule — and a name that itself holds a masked value (a declared --env value inside another declared name) falls
back to a value-free marker, so a mask's label never carries a secret (R2-F2). A value under a name that says secret (key, token, password…) is always masked; under any other name, a number or
a yes/no word is a setting, left readable and named in the summary — never a list's member, and never a number found
inside another value unless it was given with '=' to a setting's name (PORT=8000 in a list). Anything shaped like a
private key, an access token or a password is masked wherever it appears, and so is anything printed after a name that
says secret and '=' or ':'. Every match is found in the output as the check printed it before any is replaced, so masking
one value never hides another from these rules. A secret file that is a
link is read through the link; a folder that cannot be listed, or a linked folder, stops the run before the check,
because secret files inside it would not be found — and so does a secret file this tool cannot read completely (binary,
an encoding without a byte order mark, or anything its reader does not understand, such as a quote never closed) or
that holds a value only the program reading it can make out (a YAML tag PyYAML decodes to bytes, however it is
written); a .env file outside the literal boundary — a reference, expansion or interpolation anywhere in a value ('$'
or a backtick, inside quotes too), an unquoted byte outside the probed set (braces included: bash expands {a,b}, so
both are refused), whitespace inside an unquoted value or at a quoted value's edge, a duplicate name, spaces around
'=', a quote never closed or text after it, a line break inside quotes, a control character but a literal tab inside
quotes, consecutive backslashes inside single quotes, a carriage return, a byte order mark, a bare line — because every claimed reader must read admitted bytes
literally, or the file refuses; or a .env.vault file, whose values are encrypted and the key that would
read them (DOTENV_KEY) may never enter a check's environment), because its values could not be masked. A .env file
inside the boundary has no environment-dependent readings at all: the decode is the same for every claimed reader.
A value --env declares is sensitive from admission and masked wherever the check prints it, under its
declared name.
The evidence file is replaced whole, and it must lie inside the project's .vibe-to-engineering/evidence/ folder.

Exit status — the wrapper's own namespace (owner decision 5.3), never the check's: 0 the check ran and its
evidence was successfully produced — the check's own outcome is reported as data (its exit code, or the signal
that ended it, number and name; a signal is never collapsed into an ordinary exit code), and 0 does not say the
check passed: judge the check by its recorded outcome, never by this status alone; 1 the wrapper itself failed
— the validated launch could not be started, or the evidence could not be written; 2 a pre-launch refusal:
usage, a refused --env or --with-path setting, a refused evidence path, a refused enrollment (the approval word
not given, the candidate not a supported enrolled-able binary), a check whose runner is not in the supported
set, is not enrolled for this user, resolves to a different executable than enrolled, or no longer matches its
enrolled bytes (references/supported-checks.md — an unvalidated check never runs), or secret files that could
not be gathered or read completely — always before anything runs: exit 2 means the check never ran and this
attempt produced no check evidence; 3 a post-launch integrity failure — the check DID run (its outcome is
reported and stands), only the scratch root could not be confirmed and safely removed. A failure after the
launch is never reported as a refusal. Every byte the wrapper emits — the evidence including its header, the
stdout echo, the stderr summary, mask labels, diagnostics and parser errors — holds no declared --env value:
the maskable values are collected from the raw arguments before any parsing or validation (two-phase
admission), a mask's label falls back to a value-free marker when the name itself holds a masked value, and
the final generated text passes the redaction context once more before it is printed or saved.
"""

import argparse
import codecs
import ctypes
import errno
import fnmatch
import hashlib
import json
import os
import re
import stat
import subprocess
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # the modules beside this file
from checkpoint import STATE_DIR, resolve_project  # noqa: E402
import childenv  # noqa: E402 — the constructed environment every check runs with (NEW-5 stage 1)
import emission  # noqa: E402 — the governed emission path and the wrapper status namespace (R2 slice)
from gitrun import Fail, configure_output, is_link, write_lf  # noqa: E402
from secretformats import (Unreadable, commented, dotenv_values, ini_values, json_values, key_values,  # noqa: E402
                           properties_values, text_values, toml_values, values_in, yaml_values)
from secretforms import BARE, LIST, SECRET_NAME, SETTING, parts, worth  # noqa: E402
from watched import SECRET_FILES, UNWATCHED_FOLDERS  # noqa: E402 — one list of secret files

BOMS = ((codecs.BOM_UTF8, "utf-8-sig"), (codecs.BOM_UTF32_LE, "utf-32"), (codecs.BOM_UTF32_BE, "utf-32"),
        (codecs.BOM_UTF16_LE, "utf-16"), (codecs.BOM_UTF16_BE, "utf-16"))  # UTF-32 first: its mark begins like UTF-16's
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


def read_secret(label, text, written=None, environ=None):
    """(name, value) for every value a secret file holds, from the one reader its lower-cased name calls for: a key
    file; the data formats, before the .env names — YAML (a file whose reader stops at a line holding a {{ or {% template
    marker is a Helm or Go template, read as text), TOML, Java .properties, INI (a [section] before the first option,
    as configparser needs); a .env file; a file with no extension as INI when a [section] comes first and it reads as
    INI, else as text; a *.json file as JSON; anything else as text. A .env.vault file is never read: its values are
    encrypted, and the key that would decrypt them (DOTENV_KEY) may never enter a check's environment, so its values
    cannot be masked. A file whose text is one JSON document is also read as JSON (and only as JSON when its own
    reader cannot read it — never a .env file, which a shell sources as it is: its refusal stands). A data format's
    comments add the secrets kept in them (commented). Then every value named inside a value and every part of a value
    (inner), and each value's stripped form — never a text with nothing in it, or only a setting's name and its '='
    (worth). `written`, the file as written, carriage returns and a byte order mark and all, goes to the .env reader
    for the boundary's byte-order-mark and carriage-return refusals (a shell sourcing the file reads both);
    `environ` is no longer consulted by it — under the literal boundary no .env reading depends on the
    environment. Unreadable when the reader cannot read it all."""
    name, pairs = label.lower(), None
    if name == ".env.vault":
        raise Unreadable("a .env.vault file: its values are encrypted, and the key that would read them "
                         "(DOTENV_KEY) may never enter a check's environment")
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
    reader, own, shell = text_values, label, False   # own: the file's name, for a reader that names every value after
    if called(KEY_FILES):                           # the file; shell: a .env file, which a shell may source
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
        reader, own, shell = (lambda text, label: dotenv_values(text, label, written, environ)), None, True
    if document is not None and (is_json or reader is text_values):
        pairs = inner(document)
    else:
        try:
            pairs = inner(resolved(reader(text, label) + (commented(text, label) if own is None else []))
                          + (document or []), own)
        except Unreadable as error:
            line = text.split("\n")[error.line - 1] if error.line and not error.final else ""
            if document is not None and not shell:   # a shell sources a .env file as it is, JSON or not: its
                pairs = inner(document)   # refusal stands; another file its own reader cannot read, one JSON document
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
    """A secret file's text: decoded by its byte order mark (UTF-8, UTF-16, UTF-32), otherwise as UTF-8 — the mark
    kept as a leading U+FEFF, for the one reading that takes the file as written (a shell sourcing a .env file reads the
    mark's bytes as part of its first word). A file that is not text this tool can read — bytes that are not UTF-8, or a
    NUL character, as in UTF-16 without a mark or a binary key container — stops the run: its values could not be
    masked."""
    data = Path(path).read_bytes()
    encoding = next((encoding for mark, encoding in BOMS if data.startswith(mark)), "utf-8")
    try:
        text = data.decode(encoding)
    except UnicodeDecodeError:
        text = "\0"
    if "\0" in text:
        raise Fail("%s is not text this tool can read (binary, or an encoding without a byte order mark), so its "
                   "values cannot be masked — keep it outside the project for the migration" % path)
    return ("\ufeff" if encoding != "utf-8" else "") + text


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


def secret_values(project, environ):
    """(name, value) for every value the project's secret files hold, each file read whole by the one reader its name
    calls for (read_secret): key files, .env, JSON, YAML, TOML, Java .properties, INI, and any other file line by
    line, as written — `environ`, the check's whole constructed environment (no .env reading consults it under the
    literal boundary). A secret file that
    cannot be read, is not text this tool can read, or that its reader cannot understand completely stops the run
    before the check, naming the file and the line, never its text: its values could not be masked."""
    found = []
    for path in secret_files(project):
        try:
            if not os.path.isfile(path):  # a link to nothing, or to a folder: no values to mask
                continue
            if os.path.getsize(path) > LARGEST_SECRET_FILE:
                raise Fail("%s is larger than a secret file (%d bytes) — its values cannot be masked" % (path, os.path.getsize(path)))
            written = secret_text(path)   # as written: a byte order mark kept, for the shell's reading alone
        except OSError as error:
            raise Fail("cannot read %s to mask its values (%s)" % (path, error.strerror or error))
        text = written[1:] if written.startswith("\ufeff") else written
        try:
            pairs = read_secret(os.path.basename(path), text.replace("\r\n", "\n").replace("\r", "\n"), written,
                                environ)
            if re.search(r"\r(?!\n)", text):   # a lone carriage return: also as Node reads it, which drops it
                try:
                    pairs += read_secret(os.path.basename(path), text.replace("\r\n", "\n").replace("\r", ""),
                                         environ=environ)
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


def safe_label(name, values, everywhere):
    """The mask label for a value masked under `name`: '<masked NAME>' — unless that label would itself be
    masked, because names are data and the Class II invariant covers every emitted byte, labels included
    (R2-F2): a name holding a declared --env value (masked wherever it appears), or holding any masked
    value where the output would mask it (a value of four characters or more, not all digits, anywhere; a
    shorter or all-digit one only as a whole word), or a name itself shaped like a secret, gets a
    value-free fallback marker instead — emission.fallback, which by construction holds none of the
    masked values, so the final form never reintroduces a secret after the child's output was masked."""
    candidate = "<masked %s>" % name
    for value, _ in values:
        if not value:
            continue
        if value in everywhere or len(value) >= 4 and not value.isdigit():
            if value in candidate:
                return emission.fallback([secret for secret, _ in values])
        elif re.search(r"(?<![\w-])%s(?![\w-])" % re.escape(value), candidate):
            return emission.fallback([secret for secret, _ in values])
    if any(shape.search(candidate) for shape in SHAPES):
        return emission.fallback([secret for secret, _ in values])
    return candidate


def mask(text, values, everywhere=frozenset()):
    """text with every secret value replaced, and how many were. Values are matched as they always were, longest first:
    a value under four characters, or all digits, only where it stands as a whole word — a PIN of 1234 is not the
    inside of 12345 — and every other value wherever it appears; a value masked already counts as the edge of a word,
    as its mask did (48213377 glued to a masked token is masked too). A declared --env value is the exception (D4
    rule 4, final-review R1): it is sensitive from admission, so it is masked wherever it appears — `everywhere` —
    even inside a longer word, however short or plain it is (childenv refuses a value of nothing but whitespace and
    '=', which could not be masked at all). Then anything shaped like a secret, and a value
    given to a name that says secret — each looked for both in the text as the check printed it, so that a masked piece
    of a name never hides DB_PASSWORD=… from the net, and in that text with the values found blanked out, so that a
    value masked right before a token or a name never hides it either. Every match is found before anything is
    replaced; matches that overlap are masked as one. A mask's label is safe_label's: the value's own name when
    that name holds no masked value itself, else a value-free fallback — the label can never carry a secret
    into the masked text (R2-F2)."""
    covered, spans = bytearray(len(text)), []

    def word_at(at):   # a character that joins a word; a masked one, or none, is the edge of a word
        return 0 <= at < len(text) and not covered[at] and WORD.match(text, at) is not None
    for value, name in values:
        label, size = safe_label(name, values, everywhere), len(value)
        whole = value not in everywhere and (len(value) < 4 or value.isdigit())
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


# The supported-check gate (NEW-5 stage 1, D6): a check launches only under a runner in the supported set — the
# registry of record is references/supported-checks.md, and this table implements exactly that set
# (tests/test_check_registry.py proves they agree). An unvalidated check is unsupported and refused before
# execution; a quarantined runner re-enters only through the same revalidation gate.
SUPPORTED = (("python", re.compile(r"python3(?:\.\d+)?\Z")),
             ("sh", re.compile(r"sh\Z")),
             ("node", re.compile(r"node\Z")))

# The profile each enrolled runner answered at enrollment (A2, R2-F5 — owner decision 5.2 and release decision
# 3.3): a file's name proves nothing — any folder on the check's PATH can hold anything under a runner's name.
# The one fixed, benign invocation runs ONLY at enrollment, disclosed to and approved by the human, under the
# constructed environment from inside that enrollment's own scratch root, so a lookalike's side effects land
# there and are removed with it; its answer is never shown (it could be anything) and must match the profile,
# version-bounded where the registry bounds it. A routine run never executes a candidate to validate it:
# validation is the enrolled path plus the enrolled SHA-256 alone.
NODE_MIN, NODE_MAX = (20, 7), (26, 10)   # the registry's version-bounded loader profiles (nodekeys.py)
PROBES = {"python": (("-I", "-c", "import sys; print(sys.version_info[0])"), re.compile(r"3\Z")),
          "sh": (("-c", "echo ${BASH_VERSION:-none}"), re.compile(r"3\.2\.\d+[^\n]*")),
          "node": (("--version",), None)}   # the version's bounds are checked below, not by the pattern
# Before any enrollment probe runs, the candidate must be a real executable binary of the platform — the
# supported profiles were revalidated against binaries, and a text script under a runner's name is refused
# without being executed at all: probing runs the suspect file, and even a benign fixed invocation would let a
# lookalike script act with the user's privileges (final-review R1). Mach-O (64-bit, 32-bit, fat, fat-64) on
# macOS, ELF on Linux; on any other platform this static check cannot be made, and the gate refuses rather than
# enroll blind — support is not claimed there anyway.
BINARY_MAGIC = {"darwin": (b"\xcf\xfa\xed\xfe", b"\xce\xfa\xed\xfe", b"\xca\xfe\xba\xbe", b"\xca\xfe\xba\xbf"),
                "linux": (b"\x7fELF")}.get(sys.platform)

# Runner enrollment (A2): the per-user registry at ~/.vibe-to-engineering/runners.json is the only source of
# launchable runner identities. A runner enters it solely through --enroll-runner — a deliberate human act that
# discloses the resolved path, size and SHA-256, waits for the typed approval word, then runs the one disclosed
# probe and records the identity. There is no automatic enrollment and no automatic re-enrollment: a changed or
# moved runner refuses and names manual re-enrollment as the remedy. Enrollment is not protection against an
# attacker who controls the user's account; within that boundary the launched bytes always equal the enrolled
# bytes, by each entry's pin mode: "path" only after proving the entire root-owned path chain cannot be
# replaced by non-root, including every ancestor and any ACLs, on each run; "copy" for any other runner
# (the launched copy is written from the very bytes just hashed, inside the run's private scratch
# root, so nothing replaced or retargeted after validation can be launched). A candidate with neither pin
# mode is refused.
ENROLL_REGISTRY = "~/.vibe-to-engineering/runners.json"
APPROVAL = "enroll"                        # the exact word that approves an enrollment disclosure
PINS = ("path", "copy")


def no_acl(fd):
    """Prove absence of a macOS extended ACL on an open object. Darwin's acl_get_fd returns NULL/ENOENT
    for no ACL (filesec_get_property); with a valid fd this is not a pathname-existence test. Any ACL,
    other error or unverified platform prevents path pinning. No candidate is executed to inspect metadata."""
    if sys.platform != "darwin":
        return False
    try:
        libc = ctypes.CDLL(None, use_errno=True)
        libc.acl_get_fd.argtypes, libc.acl_get_fd.restype = [ctypes.c_int], ctypes.c_void_p
        libc.acl_free.argtypes, libc.acl_free.restype = [ctypes.c_void_p], ctypes.c_int
    except (AttributeError, OSError):
        return False
    ctypes.set_errno(0)
    acl = libc.acl_get_fd(fd)
    if acl:
        libc.acl_free(acl)
        return False
    return ctypes.get_errno() == errno.ENOENT


def location_pin(resolved):
    """Prove a root-owned, non-replaceable chain from / to the runner, on every use of pin path. A read-only
    user-owned object is not immutable: its owner can chmod it, and a writable ancestor can replace it.
    Reject links, group/other write bits and ACLs even when os.access is denied by a temporary sandbox.
    System runners that cannot be relocated can use this proof; all other locations require pin copy."""
    runner = Path(resolved)
    if not runner.is_absolute() or os.geteuid() == 0:
        return None
    # Root first: once checked, a parent cannot be exchanged by an unprivileged writer while checking its child.
    for component in list(reversed(runner.parents)) + [runner]:
        try:
            fd = os.open(str(component), os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
            try:
                info = os.fstat(fd)
                right_type = stat.S_ISREG(info.st_mode) if component == runner else stat.S_ISDIR(info.st_mode)
                if not right_type or info.st_uid != 0 or info.st_mode & 0o022 \
                        or os.access(str(component), os.W_OK) or not no_acl(fd):
                    return None
            finally:
                os.close(fd)
        except OSError:
            return None
    return "path"


def registry_path():
    """The per-user runner registry, resolved fresh from the calling user's home each time (tests isolate it
    with their own HOME; the tool never reads another account's)."""
    return os.path.expanduser(ENROLL_REGISTRY)


def load_registry():
    """The enrolled-runner registry, or a refusal: missing (nothing is enrolled — the remedy is the enrollment
    command), unreadable, not JSON, or not the documented shape. A malformed registry never silently passes:
    every refusal here stops the run before anything executes."""
    path = registry_path()
    try:
        raw = Path(path).read_text(encoding="utf-8")
    except FileNotFoundError:
        raise Fail("no runners are enrolled for this user (%s does not exist) — enrollment is a deliberate "
                   "human act: python3 evidence.py --enroll-runner <runner>; the check is refused before "
                   "execution" % path)
    except UnicodeError:
        raw = ""   # malformed encoding follows the same refusal as malformed JSON; never echo raw bytes
    except OSError as error:
        raise Fail("cannot read the runner registry %s (%s) — the check is refused before execution"
                   % (path, error.strerror or error))
    try:
        registry = json.loads(raw)
    except ValueError:
        registry = None
    if not isinstance(registry, dict) or type(registry.get("version")) is not int or registry["version"] != 1 \
            or not isinstance(registry.get("runners"), dict):
        raise Fail("the runner registry %s is malformed — repair it or re-enroll the runner manually "
                   "(python3 evidence.py --enroll-runner <runner>); the check is refused before execution" % path)
    return registry


def registry_entry(registry, kind):
    """The registry's entry for one runner kind, every field the launch relies on validated: an absolute
    enrolled path, a lowercase hex SHA-256, a non-negative size and a known pin mode. Anything else — or no
    entry at all — refuses before anything runs, naming manual (re-)enrollment as the remedy."""
    entry = registry["runners"].get(kind)
    if entry is None:
        raise Fail("the %s runner is not enrolled for this user — enrollment is a deliberate human act: "
                   "python3 evidence.py --enroll-runner %s; the check is refused before execution"
                   % (kind, kind))
    if not (isinstance(entry, dict) and isinstance(entry.get("path"), str)
            and os.path.isabs(entry["path"]) and isinstance(entry.get("sha256"), str)
            and re.fullmatch(r"[0-9a-f]{64}", entry["sha256"]) is not None
            and isinstance(entry.get("size"), int) and not isinstance(entry.get("size"), bool)
            and entry["size"] >= 0 and entry.get("pin") in PINS):
        raise Fail("the runner registry's %s entry is malformed — repair %s or re-enroll manually "
                   "(python3 evidence.py --enroll-runner %s); the check is refused before execution"
                   % (kind, registry_path(), kind))
    return entry


def hashed(resolved, into=None):
    """(SHA-256 hexdigest, size) of a runner's bytes, read once from one open file description — O_NOFOLLOW, so
    a link swapped onto the last component after resolution refuses instead of hashing a substitute. With
    `into` (a fresh path inside the run's private scratch root) the same reading also writes the launch copy,
    so the bytes hashed are the bytes copied."""
    try:
        fd = os.open(resolved, os.O_RDONLY | os.O_NOFOLLOW)
    except OSError as error:
        raise Fail("cannot open the runner %s (%s) — the check is refused before execution"
                   % (resolved, error.strerror or error))
    digest, size = hashlib.sha256(), 0
    try:
        stream = open(into, "wb") if into is not None else None
        try:
            while True:
                chunk = os.read(fd, 1 << 20)
                if not chunk:
                    break
                digest.update(chunk)
                size += len(chunk)
                if stream is not None:
                    stream.write(chunk)
        finally:
            if stream is not None:
                stream.close()
    finally:
        os.close(fd)
    return digest.hexdigest(), size


def probe(resolved, kind, env, scratch):
    """The one disclosed enrollment probe (final-review R1's profile check, moved to enrollment by A2): the
    fixed invocation under the constructed environment, from inside the scratch root, its answer checked but
    never shown. A candidate that cannot be launched, does not answer in time, answers anything else, or fails
    (for node, a version outside the revalidated bounds) is not the runner the set revalidated."""
    args, pattern = PROBES[kind]
    try:
        done = subprocess.run([resolved] + list(args), env=env, cwd=str(scratch / "tmp"),
                              stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                              timeout=15)
        answer = done.stdout.decode("utf-8", "replace").strip()
        ok = done.returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        answer, ok = "", False
    if ok and kind == "node":
        match = re.fullmatch(r"v(\d+)\.(\d+)\.\d+", answer)
        ok = match is not None
        if ok and not NODE_MIN <= (int(match.group(1)), int(match.group(2))) <= NODE_MAX:
            raise Fail("%s: node v%s.%s is outside the revalidated loader-profile bounds (v%d.%d–v%d.%d) — "
                       "enrollment is refused" % ((resolved, match.group(1), match.group(2))
                                                  + NODE_MIN + NODE_MAX))
    elif ok:
        ok = pattern.fullmatch(answer) is not None
    if not ok:
        raise Fail("%s: the candidate does not answer as its supported profile (%s) — a file's name alone "
                   "proves nothing; enrollment is refused" % (resolved, kind))
    return answer


def enrolled_identity(resolved, kind, scratch):
    """(launch path, registry entry) for a routine run — hash-only validation, never an execution (A2): the
    resolved executable must be the enrolled path and its bytes must hash to the enrolled SHA-256. For pin path
    the enrolled path itself launches (a system-protected location: non-root cannot replace those bytes between
    this hash and the launch); for pin copy the launch is a private copy written from the same reading that was
    hashed, so a binary replaced or a link retargeted at any moment — before or after this validation — cannot
    put another program in the launch. A changed or moved identity refuses, naming manual re-enrollment."""
    entry = registry_entry(load_registry(), kind)
    if entry["path"] != resolved:
        raise Fail("%s: the command resolves here, but the enrolled %s runner is %s — a moved or retargeted "
                   "runner is never re-enrolled automatically: if this change is intended, re-enroll manually "
                   "(python3 evidence.py --enroll-runner %s); the check is refused before execution"
                   % (resolved, kind, entry["path"], kind))
    if entry["pin"] == "copy":
        folder = scratch / "runner"
        folder.mkdir(exist_ok=True)
        os.chmod(str(folder), 0o700)
        copy = folder / ("%s-%s" % (kind, entry["sha256"][:16]))
        digest, size = hashed(resolved, into=str(copy))
        if size != entry["size"] or digest != entry["sha256"]:
            raise Fail("%s: the %s runner no longer matches its enrolled bytes (enrolled sha256 %s…, found "
                       "%s…) — never re-enrolled automatically: if the change is intended, re-enroll manually "
                       "(python3 evidence.py --enroll-runner %s); the check is refused before execution"
                       % (resolved, kind, entry["sha256"][:12], digest[:12], kind))
        os.chmod(str(copy), 0o500)
        return str(copy), entry
    if location_pin(resolved) != "path":
        raise Fail("%s: the enrolled path is no longer provably protected through every ancestor — re-enroll "
                   "manually (python3 evidence.py --enroll-runner %s); the check is refused before execution"
                   % (resolved, kind))
    digest, size = hashed(resolved)
    if size != entry["size"] or digest != entry["sha256"]:
        raise Fail("%s: the %s runner no longer matches its enrolled bytes (enrolled sha256 %s…, found %s…) — "
                   "never re-enrolled automatically: if the change is intended, re-enroll manually "
                   "(python3 evidence.py --enroll-runner %s); the check is refused before execution"
                   % (resolved, kind, entry["sha256"][:12], digest[:12], kind))
    return resolved, entry


def resolve_candidate(program, path):
    """(resolved path, runner kind) for an enrollment candidate: an absolute path when it holds a '/', else
    found on the given PATH — an existing executable file, links resolved, kind by the resolved final name.
    The binary-magic gate stands at enrollment: a script under a runner's name is refused without ever being
    executed."""
    if "/" in program or os.sep in program:
        if not os.path.isabs(program):
            raise Fail("%s: enroll by an absolute path, or by a name found on the PATH" % program)
        candidate = program
        resolved = os.path.realpath(candidate) if os.path.isfile(candidate) and os.access(
            candidate, os.X_OK) else None
    else:
        resolved = next((os.path.realpath(os.path.join(folder, program)) for folder in path.split(os.pathsep)
                         if os.path.isfile(os.path.join(folder, program))
                         and os.access(os.path.join(folder, program), os.X_OK)), None)
    if resolved is None:
        raise Fail("%s: not an existing executable file — nothing to enroll" % program)
    kind = next((kind for kind, pattern in SUPPORTED if pattern.fullmatch(os.path.basename(resolved))), None)
    if kind is None:
        raise Fail("%s: this runner is not in the supported set (references/supported-checks.md) — an "
                   "unvalidated runner is never enrolled" % resolved)
    if BINARY_MAGIC is None:
        raise Fail("%s: this platform's executable format is not one the gate verifies — enrollment is refused"
                   % resolved)
    try:
        with open(resolved, "rb") as stream:
            magic = stream.read(4)
    except OSError:
        magic = b""
    if magic not in BINARY_MAGIC:
        raise Fail("%s: not a real executable binary of this platform — a script under a runner's name is "
                   "never enrolled and never even probed" % resolved)
    return resolved, kind


def enroll_runner(program, with_path=(), ask=None, out=None):
    """Enroll one runner into the per-user registry — the only way a runner enters it. The candidate's resolved
    path, size and SHA-256 are disclosed, and only the typed approval word (APPROVAL) allows the one disclosed
    probe to run and the identity to be recorded; the bytes are hashed again after approval, so an approval is
    never reused for different bytes, including the reading that writes a probe copy. The pin mode is the
    location's: 'path' only with a proven root-owned path chain,
    else 'copy' once a private copy is shown to answer the profile (a candidate with neither is refused).
    Re-enrolling a kind replaces its entry — manually, with the same disclosure and approval."""
    ask = ask or input
    out = out or sys.stdout
    extras = [childenv.with_path(raw) for raw in with_path]
    resolved, kind = resolve_candidate(program, ":".join([childenv.PATH_FOLDERS] + extras))
    digest, size = hashed(resolved)
    pin = location_pin(resolved)
    try:
        existing = registry_entry(load_registry(), kind)
    except Fail:
        existing = None
    args, _ = PROBES[kind]
    print("vibe-to-engineering runner enrollment — the identity disclosed before anything runs:", file=out)
    print("  runner:  %s" % kind, file=out)
    print("  path:    %s (resolved)" % resolved, file=out)
    print("  size:    %d bytes" % size, file=out)
    print("  sha256:  %s" % digest, file=out)
    print("  pin:     %s" % ("path — protected file and every ancestor, launched at its enrolled path" if pin
                             else "to be verified: launched from a private copy of the hashed bytes (pin copy) "
                                  "or refused"), file=out)
    print("  probe:   %s %s — the one invocation enrollment will run; routine runs never execute the runner to "
          "validate it" % (resolved, " ".join(args)), file=out)
    if existing is not None:
        print("  replaces: the enrolled %s (sha256 %s…) — manual re-enrollment, never automatic"
              % (kind, existing["sha256"][:12]), file=out)
    try:
        answer = ask("type '%s' to approve exactly this identity and run the disclosed probe: " % APPROVAL)
    except EOFError:
        answer = ""
    if answer.strip() != APPROVAL:
        raise Fail("enrollment not approved — nothing ran and nothing was written")
    if pin == "path" and location_pin(resolved) != "path":
        raise Fail("the candidate's path protection changed after disclosure — re-enroll manually "
                   "(python3 evidence.py --enroll-runner %s); enrollment is refused" % kind)
    again, size2 = hashed(resolved)
    if again != digest or size2 != size:
        raise Fail("the candidate changed between disclosure and approval — an approval is never reused for "
                   "different bytes; enrollment is refused")
    scratch = childenv.scratch_root()
    try:
        env = childenv.profile(scratch, extras)
        if pin is None:   # pin copy, if a private copy of the approved bytes answers the profile
            folder = scratch / "runner"
            folder.mkdir()
            copy = folder / ("candidate-%s" % digest[:16])
            copied, copied_size = hashed(resolved, into=str(copy))
            if copied != digest or copied_size != size:
                raise Fail("the candidate changed while preparing its approved probe — an approval is never "
                           "reused for different bytes; enrollment is refused")
            os.chmod(str(copy), 0o500)
            probe(str(copy), kind, env, scratch)
            pin = "copy"
        else:
            probe(resolved, kind, env, scratch)
    finally:
        childenv.cleanup(scratch)
    record = {"path": resolved, "sha256": digest, "size": size, "pin": pin,
              "probe": "%s %s" % (resolved, " ".join(args)),
              "enrolled": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    path = registry_path()
    folder = os.path.dirname(path)
    os.makedirs(folder, exist_ok=True)
    os.chmod(folder, 0o700)
    registry = {"version": 1, "runners": {}}
    if os.path.exists(path):
        registry = load_registry()   # a malformed registry is never silently replaced: it fails here instead
    registry["runners"][kind] = record
    fd, temp = tempfile.mkstemp(prefix="runners-", suffix=".tmp", dir=folder)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(json.dumps(registry, indent=2, sort_keys=True) + "\n")
        os.chmod(temp, 0o600)
        os.replace(temp, path)
    except BaseException:
        try:
            os.unlink(temp)
        except OSError:
            pass
        raise
    print("enrolled %s: %s (sha256 %s, pin %s)" % (kind, resolved, digest, pin), file=out)


def supported_runner(command, path, cwd):
    """The check's runner kind when its executable is in the supported set, else None. The executable is the path
    named when it holds a '/', resolved under the launch's own working directory (the check runs with cwd=project,
    so a relative path is judged where it will actually run, never against this process's folder), else found on
    the check's own constructed PATH — an existing, executable file either way, links resolved, and judged by its
    resolved final name, never by the name it was called."""
    program = command[0]
    if "/" in program or os.sep in program:
        candidate = program if os.path.isabs(program) else os.path.join(str(cwd), program)
        resolved = os.path.realpath(candidate) if os.path.isfile(candidate) and os.access(
            candidate, os.X_OK) else None
    else:
        resolved = next((os.path.realpath(os.path.join(folder, program)) for folder in path.split(os.pathsep)
                         if os.path.isfile(os.path.join(folder, program))
                         and os.access(os.path.join(folder, program), os.X_OK)), None)
    if resolved is None:
        return None, None
    name = os.path.basename(resolved)
    return resolved, next((kind for kind, pattern in SUPPORTED if pattern.fullmatch(name)), None)


Parser = emission.Parser   # grammar-aware early collection and complete parser/help emissions (R2-F3)


def main(argv=None):
    configure_output()
    parser = Parser(prog="evidence.py", description="Run one check and keep its output as evidence, "
                                                   "with secret values masked.")
    parser.add_argument("--project", default=".", help="the project folder (default: the current folder)")
    parser.add_argument("--out", help="the evidence file, inside .vibe-to-engineering/evidence/")
    parser.add_argument("--env", action="append", default=[], metavar="NAME=VALUE",
                        help="declare a value for the check's constructed environment (repeatable)")
    parser.add_argument("--with-path", action="append", default=[], metavar="/abs/dir",
                        help="add a folder to the check's PATH (repeatable)")
    parser.add_argument("--enroll-runner", metavar="RUNNER",
                        help="enroll a runner for this user (shows its resolved path and SHA-256, asks for "
                             "approval, runs the one disclosed probe) — the only way a runner enters the registry")
    parser.add_argument("command", nargs=argparse.REMAINDER, help="-- then the check's command and arguments")
    try:
        args = parser.parse_args(argv)
    except SystemExit as quit_:   # argparse already reported — usage, redacted: nothing ran (usage is 2)
        return quit_.code if isinstance(quit_.code, int) else emission.REFUSED
    context, messages = parser.context, []

    def note(message):
        messages.append("evidence.py: error: %s\n" % message)

    def finish(status, launched=False, saved=False, returncode=None):
        sys.stderr.write(emission.report(messages, context, status, launched, saved, returncode))
        return status

    command = args.command[1:] if args.command[:1] == ["--"] else args.command
    if args.enroll_runner:
        if command or args.out or args.env or args.project != ".":
            parser.error("--enroll-runner stands alone: no check, --out, --env or --project with it")
        try:
            enroll_runner(args.enroll_runner, args.with_path)
        except Fail as error:
            sys.stderr.write(context.scrub("evidence.py: error: %s\n" % error))
            return emission.REFUSED
        except OSError as error:
            sys.stderr.write(context.scrub("evidence.py: error: cannot enroll %s (%s)\n"
                                           % (args.enroll_runner, error.strerror or error)))
            return emission.OPERATIONAL
        return 0   # enrollment is its own command form: 0 enrolled, never a check's status
    if not args.out:
        parser.error("give the evidence file with --out")
    if not command:
        parser.error("give the check after --")
    try:
        admitted = childenv.declared(args.env)   # phase two: early context already protects ALL raw settings
    except Fail as error:
        note(str(error))
        return finish(emission.REFUSED)
    secrets = [value for value in admitted.values() if value]
    context = emission.Context(secrets)
    try:
        project = resolve_project(args.project)
        out = evidence_path(project, args.out)
        env, scratch, paths = childenv.construct(args.with_path, args.env)   # retain F4's validated mapping
    except Fail as error:
        note(str(error))
        return finish(emission.REFUSED)
    except (OSError, ValueError, RuntimeError) as error:
        note("cannot prepare the run (%s)" % type(error).__name__)
        return finish(emission.OPERATIONAL)
    result, launched, saved, returncode = emission.REFUSED, False, False, None
    try:
        try:
            resolved, runner = supported_runner(command, env["PATH"], project)   # D6: an unvalidated check
            if runner is None:                                                   # never runs — judged under the
                raise Fail("%s: this runner is not in the supported set (references/supported-checks.md) — "
                           "an unvalidated check is refused before execution" % command[0])   # launch's own cwd
            launch, enrolled = enrolled_identity(resolved, runner, scratch)   # A2: hash-only validation, and
            # every declared value is sensitive from admission (D4 rule 4): masked wherever the check prints it,
            # under its declared name — so a check pointed at throwaway data prints the masked declared value
            declared = [(value, name) for name, value in admitted.items() if value]
            values, settings = classify(secret_values(project, env))
            context = emission.Context(secrets, values)   # known file values govern ALL subsequent output
            seen = {value for value, _ in declared}   # the declared name wins the attribution of a shared value
            values = declared + [(value, name) for value, name in values if value not in seen]
            values.sort(key=lambda item: -len(item[0]))
            try:
                done = subprocess.run(command, executable=launch, cwd=str(project), env=env,
                                      stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
                launched = True                 # the enrolled bytes launch — never a fresh lookup (A2, R2-F5)
                returncode = done.returncode      # retain facts before masking/writing can fail (R2-F6)
            except OSError as error:
                note("cannot run %s (%s)" % (command[0], error.strerror or error))
                result = emission.OPERATIONAL   # the validated launch itself failed: a wrapper failure
            else:
                outcome = emission.child_outcome(done.returncode)   # the child's own result, as data (5.3)
                header = "$ %s\n%s%s  runner %s\n" % (   # declared --env names, never their values; each
                    " ".join(command), "".join("  with %s\n" % name for name in admitted),
                    "".join("  path %s\n" % folder for folder in paths),   # --with-path entry the child
                    "%s %s sha256:%s mode:%s — the enrolled identity launched"   # actually received,
                    % (runner, enrolled["path"], enrolled["sha256"], enrolled["pin"]))   # retained (R2-F4)
                text, masked = mask(header + "\n" + done.stdout.decode("utf-8", "replace"), values,
                                    frozenset(secrets))   # a declared value is masked wherever it appears (R1)
                text = context.scrub(text if text.endswith("\n") else text + "\n")   # newline included
                try:
                    write_lf(out, text)
                    saved = True
                except OSError as error:
                    note("cannot write %s (%s) — the check ran (%s) but its evidence was not saved"
                         % (str(out), error.strerror or error, outcome))
                    result = emission.OPERATIONAL   # the check ran; the wrapper failed to keep the evidence
                else:
                    sys.stdout.write(text)   # exactly the saved, governed bytes — no later print suffix
                    messages.append("evidence.py: the check %s; evidence saved to %s (%d secret %s masked%s)\n"
                                    % (outcome, str(out), masked, "value" if masked == 1 else "values",
                                       "; settings left readable: " + ", ".join(settings) if settings else ""))
                    result = emission.RAN    # ran + evidence, never a claim that the check passed
        except Fail as error:
            note(str(error))
            result = emission.INTEGRITY if launched else emission.REFUSED
        except (OSError, ValueError, RuntimeError) as error:
            note("wrapper operation failed (%s)" % type(error).__name__)
            result = emission.OPERATIONAL
    finally:
        try:
            childenv.cleanup(scratch)   # the run's own scratch root, and nothing else — matched by identity
        except Fail as error:
            messages.append("evidence.py: integrity failure after the run: %s\n" % error)
            if launched or saved:
                result = emission.INTEGRITY
    return finish(result, launched, saved, returncode)   # one stderr emission, through cleanup and result


if __name__ == "__main__":
    sys.exit(main())
