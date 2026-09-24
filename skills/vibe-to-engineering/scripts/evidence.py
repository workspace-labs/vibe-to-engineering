#!/usr/bin/env python3
"""Run one check and keep its output as evidence, with every secret value masked.

    python3 evidence.py --project <project> --out <project>/.vibe-to-engineering/evidence/<step>/<name>.txt \\
        [--env NAME=VALUE]… -- <command> [<argument>…]          (Windows: py -3 evidence.py …)

Standard library only. The command runs in the project folder, with each --env setting added to its environment —
how a check is pointed at throwaway data. Its output, standard output and error together, is printed and saved with
secret values masked. The values come from the project's secret files (.env and its variants, key, credential and
certificate files — read here for masking, never shown): every NAME=VALUE, NAME: VALUE or "name": "value" they hold,
with and without an inline comment, quoted and unquoted. A value under a name that says secret (key, token,
password…) is always masked; under any other name, a number or a yes/no word is a setting, left readable and named
in the summary. Anything shaped like a private key, an access token or a password is masked wherever it appears. A
secret file that is a link is read through the link; a folder that cannot be listed, or a linked folder, stops the
run before the check, because secret files inside it would not be found. The evidence file is replaced whole, and it
must lie inside the project's .vibe-to-engineering/evidence/ folder.

Exit codes: the command's own; 1 when it could not run; 2 usage, a refused evidence path, or secret files that
could not be gathered.
"""

import argparse
import fnmatch
import os
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # the modules beside this file
from checkpoint import STATE_DIR, resolve_project  # noqa: E402
from gitrun import Fail, configure_output, is_link, write_lf  # noqa: E402
from watched import SECRET_FILES, UNWATCHED_FOLDERS  # noqa: E402 — one list of secret files

# A name given a value, anywhere on a line: NAME=VALUE, export NAME=VALUE, name: value, "name": "value", 'name' = …
NAME = re.compile(r"""(?<![\w.-])(?:export\s+)?(["']?)([A-Za-z_][\w.-]*)\1\s*[=:]\s*""")
QUOTED = re.compile(r'"((?:[^"\\]|\\.)*)"|\'([^\']*)\'')
SECRET_NAME = re.compile(r"(?i)key|secret|token|passw(?:or)?d|pwd|credential|private|salt|(?<![a-z])pin(?![a-z])")
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
NAMED = re.compile(r"""(?i)\b([A-Za-z0-9_.-]*(?:key|secret|token|passw(?:or)?d|pwd|credential|private|salt|pin)"""
                   r"""[A-Za-z0-9_.-]*)(["']?\s*[:=]\s*["']?)(?!<masked)([^\s"',;]+)""")


def values_on(line):
    """(name, value) for every value the line gives a name — each unquoted value in every form it may be printed
    in: whole, without an inline comment, up to a separator, its first word."""
    found = []
    for match in NAME.finditer(line):
        rest = line[match.end():]
        quoted = QUOTED.match(rest)
        if quoted:
            raw = quoted.group(1) if quoted.group(1) is not None else quoted.group(2)
            candidates = [raw, re.sub(r"\\(.)", r"\1", raw)]
        else:
            rest = rest.strip()
            candidates = [rest, re.split(r"\s+#", rest)[0].strip(), re.split(r"[,;}]", rest)[0].strip(),
                          rest.split()[0] if rest.split() else ""]
        found += [(match.group(2), value) for value in dict.fromkeys(candidates) if value]
    return found


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
    """(name, value) for every value the project's secret files give a name. A secret file that cannot be read stops
    the run: its values could not be masked."""
    found = []
    for path in secret_files(project):
        try:
            if not os.path.isfile(path):  # a link to nothing, or to a folder: no values to mask
                continue
            if os.path.getsize(path) > LARGEST_SECRET_FILE:
                raise Fail("%s is larger than a secret file (%d bytes) — its values cannot be masked" % (path, os.path.getsize(path)))
            text = Path(path).read_text(encoding="utf-8", errors="replace")
        except OSError as error:
            raise Fail("cannot read %s to mask its values (%s)" % (path, error.strerror or error))
        for line in text.splitlines():
            if not line.lstrip().startswith("#"):
                found += values_on(line)
    return found


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
    """text with every secret value replaced, and how many were. A value under four characters, or all digits, is
    replaced only where it stands as a whole word — a PIN of 1234 is not the inside of 12345 — every other value
    wherever it appears."""
    count = 0
    for value, name in values:
        if len(value) >= 4 and not value.isdigit():
            count += text.count(value)
            text = text.replace(value, "<masked %s>" % name)
        else:
            text, found = re.subn(r"(?<![\w-])%s(?![\w-])" % re.escape(value), "<masked %s>" % name, text)
            count += found
    for shape in SHAPES:
        text, found = shape.subn("<masked>", text)
        count += found
    text, found = NAMED.subn(lambda match: match.group(1) + match.group(2) + "<masked>", text)
    return text, count + found


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
