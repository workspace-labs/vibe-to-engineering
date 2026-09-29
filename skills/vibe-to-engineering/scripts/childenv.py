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
did not make; the no-deletion rule has no exception left). The base's chain (~/.vibe-to-engineering,
then runs) is made once, at construction: each level a real directory owned by this user — a link or
any other object is refused, because a link could point the base anywhere and creation or chmod would
act on a stranger — mode 0700 whatever the umask, and the base never stands inside the project
(check_base, which the launch path calls before construction). Retention itself creates and changes
nothing at the base: it only inspects the chain (lstat), and a base that is missing, unreadable, a
link, a non-directory or another user's is the same governed integrity failure — never a traceback.
Retention only confirms the root still
stands where the run made it: a path that is not a run-owned scratch root (made by this process and
registered, this tool's own prefix, directly inside the one scratch base) is refused, and so is the
object standing at a registered path when it is not the very folder the run made — the check can move
its root away or put another object in its place, so the object is matched by device and inode. A
mismatch is reported as an integrity failure and whatever stands there is left exactly as found — a
foreign object moved inside the root is as untouchable as one standing at its path. The identity match
itself is made on an open descriptor (O_DIRECTORY|O_NOFOLLOW, fstat), and the 0700 the evidence records
is re-asserted with fchmod on that same descriptor (the check can loosen its own root during the run),
so no swap between check and chmod can carry it onto a stranger; home/ and tmp/ are opened through that
descriptor the same way, and a missing or non-directory one is simply skipped — only a failure on the
root itself is the integrity failure.
The retained root
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

import binascii
import errno
import os
import re
import stat
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # the modules beside this file
from gitrun import Fail  # noqa: E402
import emission  # noqa: E402 — the governed emission path: redaction whose marker holds no value (R2-F2)

PATH_FOLDERS = "/usr/bin:/bin:/usr/sbin:/sbin"      # the whole PATH, before --with-path adds to it
LOCALE, TIMEZONE = "en_US.UTF-8", "UTC"
SCRATCH_PREFIX = "v2e-run-"                         # a name only this tool's scratch roots carry
_ROOTS = {}                                       # the scratch roots this process made: realpath ->
                                                  # ((root's device, inode), {"home": (device, inode),
                                                  # "tmp": (device, inode)}) — retention's proof that the
                                                  # object standing at each path is the one this run made,
                                                  # never one that took its place (a foreign folder moved
                                                  # in as home/ or tmp/ is a stranger too: A3-P2)
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


BASE_LEVELS = (".vibe-to-engineering", "runs")   # the scratch base's chain under the user's home
DIR_FLAGS = getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0)   # open a directory pinned by
                                                  # descriptor: a link fails, and no swap can take the object's
                                                  # place between check and fchmod (A3-N1). Absent on Windows —
                                                  # the documented structural fallback there opens without them
                                                  # (never run natively).


def open_base():
    """The scratch base, created and validated and returned PINNED OPEN: (its real path, the descriptor
    of runs/). Each level is opened through its parent's descriptor (dir_fd, O_DIRECTORY|O_NOFOLLOW) —
    never by re-walking the full path, so a swap of a level already judged cannot redirect the next one
    (A3-P1) — created with mkdir(dir_fd=) when missing, judged by fstat (a real directory owned by this
    user), and re-asserted mode 0700 with fchmod on the same descriptor, so the umask never loosens one
    (A3-F4) and no chmod can land on a stranger (A3-N1). Every failure is a governed refusal (Fail),
    never a raw error, and every error path closes the descriptor it holds."""
    path = os.path.expanduser("~")
    try:
        fd = os.open(path, os.O_RDONLY | DIR_FLAGS)
    except OSError as error:
        raise Fail("cannot inspect the user's home (%s) — %s" % (path, error.strerror or error))
    try:
        for level in BASE_LEVELS:
            path = os.path.join(path, level)
            try:
                child = os.open(level, os.O_RDONLY | DIR_FLAGS, dir_fd=fd)
            except FileNotFoundError:
                try:
                    os.mkdir(level, stat.S_IRWXU, dir_fd=fd)
                    child = os.open(level, os.O_RDONLY | DIR_FLAGS, dir_fd=fd)
                except OSError as error:
                    raise Fail("cannot create the scratch base (%s) — %s" % (path, error.strerror or error))
            except OSError as error:
                if error.errno in (errno.ELOOP, errno.ENOTDIR):
                    raise Fail("the scratch base's %s is not a real directory — a link could point the "
                               "base anywhere, and any other object cannot hold it; refused" % path)
                raise Fail("cannot inspect the scratch base (%s) — %s" % (path, error.strerror or error))
            os.close(fd)                    # the parent is judged; the child becomes the pinned level
            fd = child
            try:
                standing = os.fstat(fd)
            except OSError as error:
                raise Fail("cannot inspect the scratch base (%s) — %s" % (path, error.strerror or error))
            if not stat.S_ISDIR(standing.st_mode) or standing.st_uid != os.getuid():
                raise Fail("the scratch base's %s is not a real directory owned by this user — refused"
                           % path)
            try:
                os.fchmod(fd, stat.S_IRWXU)
            except OSError as error:
                raise Fail("cannot make the scratch base private (%s) — %s"
                           % (path, error.strerror or error))
    except BaseException:
        os.close(fd)
        raise
    return Path(os.path.realpath(path)), fd


def scratch_base():
    """The one base every scratch root stands directly inside: ~/.vibe-to-engineering/runs — fixed, per-user,
    outside any project, and never the parent's TMPDIR. NOT /tmp: the operating system reaps /tmp on its own
    schedule, and a retained root's deletion is the human's act alone (A3), so the base lives beside the
    runner registry. This is open_base for callers that need only the path: the chain is created and
    validated exactly once per call, descriptor-chained (A3-P1), and the descriptor is closed before
    returning. A caller that CREATES inside the base must use open_base and keep the descriptor."""
    path, fd = open_base()
    os.close(fd)
    return path


def verify_base():
    """The scratch base as retention checks it: the same chain, lstat ONLY — retention creates and changes
    nothing (A3-F1). A base that is missing, unreadable, a link, a non-directory or another user's is a
    governed Fail, so a base failure after the launch is the wrapper's integrity failure (exit 3) with the
    run's outcome standing — never a traceback, an exit 1 or an unmasked emission."""
    path = os.path.expanduser("~")
    try:
        for level in BASE_LEVELS:
            path = os.path.join(path, level)
            standing = os.lstat(path)
            if not stat.S_ISDIR(standing.st_mode):
                raise Fail("the scratch base's %s is not a real directory — retention changes nothing, so "
                           "it cannot be repaired here" % path)
            if standing.st_uid != os.getuid():
                raise Fail("the scratch base's %s is owned by another user" % path)
    except OSError as error:
        raise Fail("cannot inspect the scratch base (%s) — %s" % (path, error.strerror or error))
    return Path(os.path.realpath(path))


def check_base(project):
    """The construction-time base contract for a run over `project`: the chain is created and validated
    (scratch_base), and the base may never stand inside the project — a scratch root there would sit in the
    very tree the run guards (A3-F2). Containment is judged by identity, never by string comparison: the
    base's ancestors are walked, and any that IS the project (same device and inode) refuses the run — a
    different letter case on a case-insensitive filesystem, or a link in the path, cannot launder the
    comparison (A3-N3)."""
    base = scratch_base()
    target = os.stat(str(project))
    current = base
    while True:
        standing = os.stat(str(current))
        if (standing.st_dev, standing.st_ino) == (target.st_dev, target.st_ino):
            raise Fail("the scratch base (%s) stands inside the project — the run is refused" % (base,))
        if current.parent == current:
            break
        current = current.parent
    return base


def scratch_root():
    """One run's fresh private scratch root: a new folder directly inside the fixed scratch base — the
    parent's TMPDIR is never consulted — mode 0700, holding home/ and tmp/, mode 0700. Two runs never share
    a root. The base descriptor stays OPEN the whole time (A3-P1): the root is created with
    mkdir(dir_fd=base) — never by re-walking the base's path, so a swap of a base level cannot redirect the
    creation into a stranger — then opened through the base with O_NOFOLLOW and registered from fstat, and
    home/ and tmp/ are made and registered through the root's own descriptor: retention's identity proof
    covers all three (A3-P2)."""
    path, base_fd = open_base()
    try:
        while True:
            name = SCRATCH_PREFIX + binascii.hexlify(os.urandom(9)).decode()
            try:
                os.mkdir(name, stat.S_IRWXU, dir_fd=base_fd)
                break
            except FileExistsError:
                continue
            except OSError as error:
                raise Fail("cannot create the run's scratch root inside %s — %s"
                           % (path, error.strerror or error))
        try:
            fd = os.open(name, os.O_RDONLY | DIR_FLAGS, dir_fd=base_fd)
        except OSError as error:
            raise Fail("cannot open the run's fresh scratch root — %s" % (error.strerror or error))
    finally:
        os.close(base_fd)
    root = Path(os.path.realpath(os.path.join(str(path), name)))
    try:
        try:
            made = os.fstat(fd)
        except OSError as error:
            raise Fail("cannot inspect the run's fresh scratch root — %s" % (error.strerror or error))
        folders = {}
        for inner in ("home", "tmp"):
            try:
                os.mkdir(inner, stat.S_IRWXU, dir_fd=fd)
                inner_fd = os.open(inner, os.O_RDONLY | DIR_FLAGS, dir_fd=fd)
            except OSError as error:
                raise Fail("cannot prepare the run's scratch root — %s" % (error.strerror or error))
            try:
                os.fchmod(inner_fd, stat.S_IRWXU)                      # 0700 whatever the umask
                standing = os.fstat(inner_fd)
                folders[inner] = (standing.st_dev, standing.st_ino)
            except OSError as error:
                raise Fail("cannot prepare the run's scratch root — %s" % (error.strerror or error))
            finally:
                os.close(inner_fd)
    finally:
        os.close(fd)
    _ROOTS[str(root)] = ((made.st_dev, made.st_ino), folders)
    return root


def reopen_unreadable(root, real, root_id):
    """P3: the check stripped its own root's read permission, so the descriptor open failed EACCES on the
    very folder this run made — not on a stranger. Confirm identity with lstat against the registered
    device and inode, restore the owner's permission never through a link (follow_symlinks=False), then
    open again with O_NOFOLLOW so the caller can re-verify with fstat. Only a real identity mismatch says
    "did not make"; on 9204241 this same check exited 0 with the root restored to 0700."""
    try:
        standing = os.lstat(str(root))
    except OSError:
        del _ROOTS[str(real)]
        raise Fail("the run's scratch root is no longer at its path (the check moved or removed it) — "
                   "nothing else was touched")
    if not stat.S_ISDIR(standing.st_mode) or (standing.st_dev, standing.st_ino) != root_id:
        raise Fail("the scratch root's path now holds something this run did not make — left exactly as "
                   "found, nothing touched")
    try:
        if os.chmod in os.supports_follow_symlinks:
            os.chmod(str(root), stat.S_IRWXU, follow_symlinks=False)   # never through a link
        else:
            os.chmod(str(root), stat.S_IRWXU)   # the lstat just proved a real directory, never a link
    except OSError as error:
        raise Fail("cannot restore the run's scratch root permission — %s" % (error.strerror or error))
    try:
        return os.open(str(root), os.O_RDONLY | DIR_FLAGS)
    except OSError as error:
        raise Fail("cannot open the run's scratch root after restoring its permission — %s"
                   % (error.strerror or error))


def retain(root):
    """Confirm a run's scratch root still stands where the run made it — and leave it there, returning its
    real path for the evidence record. Nothing is deleted, ever: retention is the whole of the tool's
    end-of-run act (A3, the retained R2-F1 obligation — a tool that never deletes can never delete data the
    run did not make). Retention creates and changes nothing at the base: the chain is only inspected
    (verify_base, lstat), and every base failure is a governed Fail — never a traceback (A3-F1). The
    identity proof stands because the confirmation must be about the very folder the
    run made: a path this process did not register as a scratch root (the path checks stand too: directly
    inside the scratch base, run-prefixed) is refused, and so is — even at a registered path — an object
    that is not the very folder this run made. A check runs with the root as its HOME and TMPDIR and can
    move it away or put another folder, a link or a file in its place: the root is opened by descriptor
    (O_RDONLY|O_DIRECTORY|O_NOFOLLOW, the path as given — a link is never followed) and matched with fstat
    against the run's own device and inode, so no
    swap between check and chmod can take the object's place (A3-N1) — a mismatch is reported by the
    launch path as an integrity failure, and whatever stands there is left exactly as found, a foreign
    object moved inside the root as untouchable as one standing at its path. A root the check made
    unreadable is no stranger either: identity is confirmed by lstat, the owner's permission restored
    never through a link, and the root re-opened and re-verified (A3-P3). The 0700 the evidence records
    is re-asserted with fchmod on that same descriptor — the check can loosen its own root during the run
    (A3-F3) — and on home/ and tmp/ opened through it (dir_fd, O_NOFOLLOW) and matched against their
    registered identities: a missing or non-directory one is simply skipped, because only a failure on
    the verified root itself is the integrity failure (A3-N2), and a foreign folder moved in as one is a
    stranger — skipped, untouched (A3-P2).
    The retained root may hold sensitive output:
    listing it is allowed, deleting it is the human's own act."""
    real = Path(os.path.realpath(str(root)))
    base = verify_base()
    owned = _ROOTS.get(str(real))
    if owned is None or real.parent != base or not real.name.startswith(SCRATCH_PREFIX):
        raise Fail("retention is limited to a run's own scratch root (%s* directly inside %s) — refusing %s"
                   % (SCRATCH_PREFIX, base, root))
    root_id, folders = owned
    try:
        fd = os.open(str(root), os.O_RDONLY | DIR_FLAGS)   # the object at the path AS GIVEN — a link is
    except FileNotFoundError:                              # never followed (O_NOFOLLOW) — pinned by
        del _ROOTS[str(real)]                              # descriptor: no swap can take its place (N1)
        raise Fail("the run's scratch root is no longer at its path (the check moved or removed it) — "
                   "nothing else was touched")
    except PermissionError:
        fd = reopen_unreadable(root, real, root_id)   # the check stripped its own root's read bit (P3)
    except OSError:
        raise Fail("the scratch root's path now holds something this run did not make — left exactly as "
                   "found, nothing touched")
    try:
        try:
            standing = os.fstat(fd)
        except OSError as error:
            raise Fail("cannot inspect the run's scratch root — %s" % (error.strerror or error))
        if not stat.S_ISDIR(standing.st_mode) or (standing.st_dev, standing.st_ino) != root_id:
            raise Fail("the scratch root's path now holds something this run did not make — left exactly "
                       "as found, nothing touched")
        try:
            os.fchmod(fd, stat.S_IRWXU)   # the 0700 the evidence records, on the verified root itself (F3)
        except OSError as error:
            raise Fail("cannot re-assert the scratch root's private mode — %s" % (error.strerror or error))
        for name in ("home", "tmp"):        # through the root's own descriptor, never through a swapped
            try:                            # link; a missing or non-directory folder is simply skipped —
                inner = os.open(name, os.O_RDONLY | DIR_FLAGS, dir_fd=fd)   # only a failure on the root
            except OSError:                                                 # itself is exit 3 (N2)
                continue
            try:
                try:
                    standing = os.fstat(inner)
                except OSError:
                    continue
                if (standing.st_dev, standing.st_ino) == folders.get(name):
                    try:
                        os.fchmod(inner, stat.S_IRWXU)
                    except OSError:
                        pass
                # anything else is a foreign folder moved into the root — a stranger: skipped,
                # untouched, exactly as found (A3-P2)
            finally:
                os.close(inner)
    finally:
        os.close(fd)
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


def construct(extra_paths=(), settings=(), project=None):
    """The whole child environment for one run, built once — the mapping that governs both the preflight
    analysis and the launch (the D4 invariant) — the run's scratch root, retained when the run ends, and
    the validated --with-path entries, retained: what the launch path records is exactly what the child
    received, never a mutable original argument resolved again after the run (R2-F4). The --env settings
    and --with-path folders are validated first — and on Windows the SystemRoot is resolved
    before the root exists — so a refusal leaves nothing behind. Only then is the base chain made:
    check_base(project), when a project is given, creating and validating the chain and refusing a base
    inside the project, just before the root itself (A3-N4 — a refusal on the settings or folders creates
    not even the base). Refusal diagnostics are redacted against the
    settings admitted so far: a declared value embedded in a --with-path argument is never shown (D4 rule 4)."""
    values = declared(settings)
    extras = [with_path(raw, values.values()) for raw in extra_paths]
    systemroot = system_root() if WINDOWS else None   # before the root exists: a failure leaves nothing
    if project is not None:
        check_base(project)   # after every validation, just before the root: the chain and the
    root = scratch_root()     # containment contract (A3-F2/N3), so an early refusal creates nothing
    env = profile(root, extras, systemroot)
    env.update(values)
    return env, root, extras
