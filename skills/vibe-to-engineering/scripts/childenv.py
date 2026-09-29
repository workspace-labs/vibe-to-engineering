#!/usr/bin/env python3
"""The constructed environment every check runs with — NEW-5 stage 1, owner decisions D2, D3 and D4.

Nothing of the parent's environment is inherited. A check's child environment is built here, once, before any
preflight reading, and that one mapping is what the launch path (evidence.py, slice 2) hands to the analysis
and to the child alike: PATH is the four system folders, plus only folders --with-path gives (each validated
an absolute, existing, real directory, recorded in the evidence header by the launch path); HOME and TMPDIR
are one fresh private scratch root per run — home/ and tmp/ inside it, every folder mode 0700, made by
absolute path directly inside the one scratch base (~/.vibe-to-engineering/runs, itself mode 0700),
never inside the project and never by consulting the parent's TMPDIR; LC_ALL and LANG are en_US.UTF-8, TZ is UTC. On
macOS one name is pinned besides: __CF_USER_TEXT_ENCODING, which CoreFoundation otherwise sets inside any
child that links it (CPython does) — after exec, before the child's own code — a fixed value per user id,
never taken from the parent, so the mapping stays the whole of what the check's environment holds. On Windows,
where environment names are case-insensitive, every name rule folds case — a case variant of a prohibited,
synthesized or already-declared name is refused, never silently normalized into a collapse at spawn — and the
profile gains a synthesized SystemRoot, valued by the OS itself, never inherited: the minimum a constructed
Windows child needs. Windows support is not claimed — this is the recorded corrective, verified structurally
only, never natively. There is nothing else. When the run ends the scratch root is RETAINED, never
deleted (A3 — the retained R2-F1 obligation: a tool that never deletes can never delete data the run
did not make; the no-deletion rule has no exception left). Retention only confirms the root still
stands where the run made it: a path that is not a run-owned scratch root (made by this process and
registered, this tool's own prefix, directly inside the one scratch base) is refused, and so is the
object standing at a registered path when it is not the very folder the run made — the check can move
its root away or put another object in its place, so the object is matched by device and inode. A
mismatch is reported as an integrity failure and whatever stands there is left exactly as found — a
foreign object moved inside the root is as untouchable as one standing at its path. The retained root
may hold sensitive output (a pin-copy runner's launched bytes, anything the check wrote to its HOME
or TMPDIR), so the launch path records its path in the evidence and on stderr; listing it is allowed,
deleting it is the human's own act.

Some names are never admitted — construction already guarantees they are not inherited, and --env never adds
them: the shells' startup and function channels (BASH_ENV, ENV, SHELLOPTS, BASHOPTS, BASH_FUNC_*), the
runtime and linker channels (NODE_OPTIONS, PYTHON*, DYLD_*, and LD_PRELOAD and LD_LIBRARY_PATH for other
platforms), DOTENV_* (so DOTENV_KEY can never make a recognized .env.vault readable and DOTENV_CONFIG_PATH
can never name a file), package-manager and git configuration (NPM_CONFIG_* however it is cased — npm reads
it in any letter case — YARN_*, PNPM_*, PIP_*, GIT_*) and the proxies (HTTP_PROXY, HTTPS_PROXY, ALL_PROXY,
NO_PROXY, matched case-insensitively, strictly wider than the approved upper- and lowercase set: a refusal
is loud, an admission is silent). On Windows the exact names and the prefixes fold case as well — the OS
treats a case variant as the same name. No carve-outs — an exception is a separate owner decision, supported by a
concrete need and independent review.

An --env setting is NAME=VALUE, the name a shell's name ([A-Za-z_][A-Za-z0-9_]*), never a prohibited one,
never one the constructed environment itself holds (the synthesized six — SystemRoot too on Windows — or a
pinned one; tool folders go through --with-path alone) and never given twice (on Windows, never a case variant
of one given). A value of only whitespace and '=' is refused: it could not be masked wherever printed. A
declared value is sensitive from admission on: a refusal or any other diagnostic names the setting's name,
never its value — even when the value appears inside another argument (discreet) — and the launch path
(evidence.py, slice 3) collects every maskable --env value from the raw arguments BEFORE validating any of
them (two-phase admission, R2-F3), so even a refusal on an early argument is redacted against the values
supplied later; it then masks each admitted value wherever the check prints it, under its declared name,
however short or plain it is. A --with-path folder never holds the PATH separator: one folder enters PATH
as exactly one entry — and the validated entries are retained with the constructed mapping, so what the
evidence header records is what the child received, never a mutable original argument re-resolved after
the run (R2-F4).

Standard library only. Every refusal is a gitrun.Fail, the refusal the launch path already raises.
"""

import os
import re
import stat
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # the modules beside this file
from gitrun import Fail  # noqa: E402
import emission  # noqa: E402 — the governed emission path: redaction whose marker holds no value (R2-F2)

PATH_FOLDERS = "/usr/bin:/bin:/usr/sbin:/sbin"      # the whole PATH, before --with-path adds to it
LOCALE, TIMEZONE = "en_US.UTF-8", "UTC"
SCRATCH_PREFIX = "v2e-run-"                         # a name only this tool's scratch roots carry
_ROOTS = {}                                       # the scratch roots this process made: realpath -> (device,
                                                  # inode) — retention's proof that the object standing at the
                                                  # path is the one this run made, never one that took its place
SYNTHESIZED = ("PATH", "HOME", "TMPDIR", "LC_ALL", "LANG", "TZ")
# macOS: CoreFoundation, initializing inside any child that links it (CPython does), sets
# __CF_USER_TEXT_ENCODING in the child's environment when it is absent — after exec, before the child's own
# code (Apple OSS: CF/CFStringEncodings.c; the Gate-3 investigation corrected the earlier belief that
# posix_spawn injected it). Pinned here — a fixed value per user id, never taken from the parent's
# environment — so the constructed mapping stays the whole of what the check's environment holds, and the name
# is refused to --env like the six above.
PINNED = {"__CF_USER_TEXT_ENCODING": "0x%X:0:0" % os.getuid()} if sys.platform == "darwin" else {}

NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")        # a shell's name for a variable
PROHIBITED_EXACT = frozenset(("BASH_ENV", "ENV", "SHELLOPTS", "BASHOPTS", "NODE_OPTIONS",
                              "LD_PRELOAD", "LD_LIBRARY_PATH"))
PROHIBITED_PREFIXES = ("BASH_FUNC_", "PYTHON", "DYLD_", "DOTENV_", "YARN_", "PNPM_", "PIP_", "GIT_")
PROHIBITED_PROXIES = frozenset(("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "NO_PROXY"))

WINDOWS = sys.platform == "win32"   # Windows environment names are case-insensitive (the Gate-3 cross-platform
# investigation): a name that differs only by case IS the same name to the OS and to CPython, which collapse
# case-variant duplicates when a child is spawned — so on Windows every name rule below folds case, and an
# ambiguous case variant is refused, never silently normalized. Read at call time so tests can exercise it.
FOLDED_EXACT = frozenset(name.upper() for name in PROHIBITED_EXACT)
FOLDED_PREFIXES = tuple(prefix.upper() for prefix in PROHIBITED_PREFIXES)
# Windows adds one synthesized name: SystemRoot. The OS adds nothing to a caller-supplied environment block, but
# the side-by-side assembly machinery most programs (CPython included) load through needs it (CPython's own
# subprocess documentation: a supplied environment must include a valid SystemRoot) — so the minimum correct
# constructed Windows environment holds it, valued by the OS, never inherited from the parent.
SYNTHESIZED_WINDOWS = ("SystemRoot",)
FOLDED_HELD = frozenset(name.upper() for name in SYNTHESIZED + SYNTHESIZED_WINDOWS + tuple(PINNED))


def prohibited(name):
    """Whether a name may never enter a check's environment: the D3 set — the exact names, the prefixes,
    npm's configuration however it is cased, and the proxies case-insensitively. On Windows the exact names and
    prefixes fold case too: a case variant of a prohibited name is that name there, and admitting it would let
    the OS's case-insensitive collapse bypass the prohibition."""
    upper = name.upper()
    return (name in PROHIBITED_EXACT or upper in PROHIBITED_PROXIES
            or name.startswith(PROHIBITED_PREFIXES) or upper.startswith("NPM_CONFIG_")
            or WINDOWS and (upper in FOLDED_EXACT or upper.startswith(FOLDED_PREFIXES)))


def held(name):
    """Whether the constructed environment itself holds this name — a synthesized one (SystemRoot too, on
    Windows) or a pinned one — so --env may never override it. Case-insensitive on Windows: a case variant of a
    held name would be collapsed onto it when the child is spawned, silently replacing the analyzed value."""
    return name in SYNTHESIZED or name in PINNED or WINDOWS and name.upper() in FOLDED_HELD


def system_root():
    """The value for the synthesized SystemRoot, from the OS itself (GetWindowsDirectoryW), never from the
    parent's environment; a failure refuses the run rather than guess. Structural only — never yet run on
    native Windows."""
    import ctypes
    buffer = ctypes.create_unicode_buffer(32768)
    if not ctypes.windll.kernel32.GetWindowsDirectoryW(buffer, 32768):
        raise Fail("cannot determine SystemRoot from the OS — a constructed Windows environment without it is "
                   "refused rather than guessed")
    return buffer.value


def discreet(text, values):
    """text with every declared value replaced by a bare mask: a diagnostic never shows one (D4 rule 4 —
    sensitive from admission on), even when the value appears inside another argument the diagnostic names,
    such as a --with-path folder. The replacement is emission's fallback marker, which holds none of the
    values itself — a redaction can never reintroduce a secret inside its own marker (R2-F2)."""
    return emission.scrub(text, values)


def setting(text):
    """One --env setting as (name, value) — refused unless it is NAME=VALUE with a shell's name that is
    neither prohibited nor one the constructed environment itself holds. The value may hold anything, '='
    included, and may be empty; a non-empty value made only of whitespace and '=' is refused, because it could
    not be masked wherever the check prints it (masking '=' or a blank would destroy the evidence) — and D4
    admits no value this tool cannot keep secret. A refusal names the setting's name, never its value."""
    name, equals, value = text.partition("=")
    if not equals or not NAME.fullmatch(name):
        raise Fail("every --env setting must be NAME=VALUE, the name a shell's name "
                   "([A-Za-z_][A-Za-z0-9_]*) — this one is not")
    if prohibited(name):
        raise Fail("--env %s: that name may never enter a check's environment" % name)
    if held(name):
        raise Fail("--env %s: that name comes from the constructed environment and cannot be overridden "
                   "(tool folders go through --with-path)" % name)
    if value and not re.sub(r"[\s=]+", "", value):
        raise Fail("--env %s: a value of only whitespace and '=' could not be masked — give it real content, "
                   "or leave it empty" % name)
    return name, value


def declared(settings):
    """Every --env setting validated, as an ordered name -> value mapping — a name given twice is refused,
    so no declared value is ever silently discarded. On Windows the duplicate test folds case: two names that
    differ only by case are one name there, and keeping both would let the spawn collapse them."""
    values, seen = {}, set()
    for text in settings:
        name, value = setting(text)
        folded = name.upper() if WINDOWS else name
        if folded in seen:
            raise Fail("--env %s: given twice — give each name once" % name)
        seen.add(folded)
        values[name] = value
    return values


def with_path(raw, secrets=()):
    """A --with-path folder, validated: absolute, existing, a real directory (links resolved — the resolved
    path is what the check's PATH and the evidence header will hold), and never holding the PATH separator
    itself — one folder must enter PATH as exactly one entry, so a name that would split into further,
    unvalidated entries is refused. Diagnostics are redacted (discreet): a declared value embedded in the
    argument is never shown."""
    if os.pathsep in raw:
        raise Fail("--with-path: a folder whose name holds the PATH separator '%s' would enter PATH as more "
                   "than one entry — refused" % os.pathsep)
    if not os.path.isabs(raw):
        raise Fail("--with-path %s: the folder must be absolute" % discreet(raw, secrets))
    real = os.path.realpath(raw)
    if os.pathsep in real:
        raise Fail("--with-path: the folder resolves to a name holding the PATH separator '%s' — refused"
                   % os.pathsep)
    if not os.path.isdir(real):
        raise Fail("--with-path %s: not an existing directory" % discreet(raw, secrets))
    return real


def scratch_base():
    """The one base every scratch root stands directly inside: ~/.vibe-to-engineering/runs — fixed, per-user,
    outside any project, and never the parent's TMPDIR. NOT /tmp: the operating system reaps /tmp on its own
    schedule, and a retained root's deletion is the human's act alone (A3), so the base lives beside the
    runner registry. Created on first use, mode 0700 whatever the umask — re-asserted on every call, because
    the retention contract promises 0700."""
    base = os.path.join(os.path.expanduser("~"), ".vibe-to-engineering", "runs")
    os.makedirs(base, exist_ok=True)
    os.chmod(base, stat.S_IRWXU)
    return Path(os.path.realpath(base))


def scratch_root():
    """One run's fresh private scratch root: a new folder directly inside the fixed scratch base — the
    parent's TMPDIR is never consulted — mode 0700, holding home/ and tmp/, mode 0700. Two runs never share
    a root. Every root made here is registered by identity (device and inode), so retention can tell the root
    this run made from anything later standing at the same path."""
    root = Path(os.path.realpath(tempfile.mkdtemp(prefix=SCRATCH_PREFIX, dir=str(scratch_base()))))  # 0700
    for name in ("home", "tmp"):
        folder = root / name
        folder.mkdir()
        os.chmod(folder, stat.S_IRWXU)                                       # 0700 whatever the umask
    made = os.stat(str(root))
    _ROOTS[str(root)] = (made.st_dev, made.st_ino)
    return root


def retain(root):
    """Confirm a run's scratch root still stands where the run made it — and leave it there, returning its
    real path for the evidence record. Nothing is deleted, ever: retention is the whole of the tool's
    end-of-run act (A3, the retained R2-F1 obligation — a tool that never deletes can never delete data the
    run did not make). The identity proof stands because the confirmation must be about the very folder the
    run made: a path this process did not register as a scratch root (the path checks stand too: directly
    inside the scratch base, run-prefixed) is refused, and so is — even at a registered path — an object
    that is not the very folder this run made. A check runs with the root as its HOME and TMPDIR and can
    move it away or put another folder, a link or a file in its place: the object at the path is matched by
    device and inode against the run's own root, and a mismatch is reported by the launch path as an
    integrity failure — whatever stands there is left exactly as found, and a foreign object moved inside
    the root is as untouchable as one standing at its path. The retained root may hold sensitive output:
    listing it is allowed, deleting it is the human's own act."""
    real = Path(os.path.realpath(str(root)))
    base = scratch_base()
    owned = _ROOTS.get(str(real))
    if owned is None or real.parent != base or not real.name.startswith(SCRATCH_PREFIX):
        raise Fail("retention is limited to a run's own scratch root (%s* directly inside %s) — refusing %s"
                   % (SCRATCH_PREFIX, base, root))
    try:
        standing = os.lstat(str(root))
    except OSError:
        del _ROOTS[str(real)]
        raise Fail("the run's scratch root is no longer at its path (the check moved or removed it) — "
                   "nothing else was touched")
    if not stat.S_ISDIR(standing.st_mode) or (standing.st_dev, standing.st_ino) != owned:
        raise Fail("the scratch root's path now holds something this run did not make — left exactly as "
                   "found, nothing touched")
    return str(real)


def profile(root, extra_paths=(), systemroot=None):
    """The synthesized environment over a run's scratch root: the six names — the system PATH plus each
    validated --with-path folder, HOME and TMPDIR inside the root, the locale and the timezone — plus the one
    name the platform would otherwise add (PINNED), and on Windows the synthesized SystemRoot (already resolved
    when `systemroot` is given, so a failure there never leaves a root behind). `extra_paths` are ALREADY
    validated with_path() results — validate once, retain the result, and construct, analyze, launch and
    record from those same entries (R2-F4): this function never resolves a mutable original argument again."""
    env = {"PATH": ":".join([PATH_FOLDERS] + list(extra_paths)),
           "HOME": str(Path(root) / "home"), "TMPDIR": str(Path(root) / "tmp"),
           "LC_ALL": LOCALE, "LANG": LOCALE, "TZ": TIMEZONE}
    env.update(PINNED)
    if WINDOWS:
        env["SystemRoot"] = systemroot if systemroot is not None else system_root()
    return env


def construct(extra_paths=(), settings=()):
    """The whole child environment for one run, built once — the mapping that governs both the preflight
    analysis and the launch (the D4 invariant) — the run's scratch root, retained when the run ends, and
    the validated --with-path entries, retained: what the launch path records is exactly what the child
    received, never a mutable original argument resolved again after the run (R2-F4). The --env settings
    and --with-path folders are validated first — and on Windows the SystemRoot is resolved
    before the root exists — so a refusal leaves nothing behind. Refusal diagnostics are redacted against the
    settings admitted so far: a declared value embedded in a --with-path argument is never shown (D4 rule 4)."""
    values = declared(settings)
    extras = [with_path(raw, values.values()) for raw in extra_paths]
    systemroot = system_root() if WINDOWS else None   # before the root exists: a failure leaves nothing
    root = scratch_root()
    env = profile(root, extras, systemroot)
    env.update(values)
    return env, root, extras
