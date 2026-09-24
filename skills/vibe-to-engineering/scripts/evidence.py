#!/usr/bin/env python3
"""Run one check and keep its output as evidence, with every secret value masked.

    python3 evidence.py --project <project> --out <project>/.vibe-to-engineering/evidence/<step>/<name>.txt \\
        [--env NAME=VALUE]… -- <command> [<argument>…]          (Windows: py -3 evidence.py …)

Standard library only. The command runs in the project folder, with each --env setting added to its environment —
how a check is pointed at throwaway data. Its output, standard output and error together, is printed and saved with
secret values masked: the values in the project's secret files (.env and the like — read here, never shown) and
anything shaped like a private key, an access token or a password. The evidence file is replaced whole, and it must
lie inside the project's .vibe-to-engineering/evidence/ folder.

Exit codes: the command's own; 1 when it could not run; 2 usage or a refused evidence path.
"""

import argparse
import fnmatch
import os
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from checkpoint import (SECRET_FILES, STATE_DIR, UNWATCHED_FOLDERS, Fail,  # noqa: E402 — one list of secret files
                        configure_output, is_link, resolve_project, write_lf)

ASSIGNMENT = re.compile(r"^\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_.-]*)\s*[=:]\s*(.*?)\s*$")
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
NAMED = re.compile(r"""(?i)\b([A-Za-z0-9_.-]*(?:key|secret|token|passw(?:or)?d|pwd|credential)[A-Za-z0-9_.-]*)"""
                   r"""(["']?\s*[:=]\s*["']?)(?!<masked)([^\s"',;]{4,})""")


def secret_values(project):
    """(name, value) for each NAME=VALUE or NAME: VALUE line of every secret file in the project, outside dependency,
    build-output and cache folders. A secret file that cannot be read stops the run: its values could not be
    masked."""
    found = []
    for folder, dirs, names in os.walk(str(project)):
        dirs[:] = [name for name in dirs if name not in UNWATCHED_FOLDERS and name not in (".git", STATE_DIR)
                   and not is_link(os.path.join(folder, name))]
        for name in names:
            path = os.path.join(folder, name)
            if is_link(path) or not any(fnmatch.fnmatchcase(name.lower(), pattern) for pattern in SECRET_FILES):
                continue
            try:
                text = Path(path).read_text(encoding="utf-8", errors="replace")
            except OSError as error:
                raise Fail("cannot read %s to mask its values (%s)" % (path, error.strerror or error))
            for line in text.splitlines():
                match = ASSIGNMENT.match(line)
                if match and not line.lstrip().startswith("#"):
                    value = match.group(2).strip().strip("'\"")
                    if len(value) >= 4:
                        found.append((match.group(1), value))
    return found


def mask(text, values):
    """text with every secret value replaced, and how many were."""
    count = 0
    for name, value in sorted(values, key=lambda item: -len(item[1])):  # longest first: no value is split
        count += text.count(value)
        text = text.replace(value, "<masked %s>" % name)
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
        values = secret_values(project)
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
    print("evidence.py: exit code %d; saved to %s (%d secret %s masked)"
          % (done.returncode, out, masked, "value" if masked == 1 else "values"), file=sys.stderr)
    return code


if __name__ == "__main__":
    sys.exit(main())
