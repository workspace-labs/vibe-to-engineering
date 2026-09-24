"""Running git safely, and the few things that differ between operating systems — shared by every module of
the checkpoint tool.

Every git call goes through git(): argument lists, never a shell; hooks, file-system monitors and lazy fetching
off; the environment variables that would point git elsewhere dropped (G11). The platform helpers keep the
operating-system differences in one place, as references/recovery.md section 4 promises.
"""

import hashlib
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
from pathlib import Path

IDENTITY = {
    "GIT_AUTHOR_NAME": "vibe-to-engineering",
    "GIT_AUTHOR_EMAIL": "checkpoint@vibe-to-engineering.invalid",
    "GIT_COMMITTER_NAME": "vibe-to-engineering",
    "GIT_COMMITTER_EMAIL": "checkpoint@vibe-to-engineering.invalid",
}
# Inherited variables that would point git at another repository, index or date, or at other files to read or
# write: settings given for one command, the file `git config` writes, templates, an outside diff program.
GIT_ENV_TO_DROP = (
    "GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_OBJECT_DIRECTORY",
    "GIT_ALTERNATE_OBJECT_DIRECTORIES", "GIT_COMMON_DIR", "GIT_NAMESPACE",
    "GIT_AUTHOR_DATE", "GIT_COMMITTER_DATE", "GIT_CEILING_DIRECTORIES",
    "GIT_CONFIG", "GIT_CONFIG_PARAMETERS", "GIT_CONFIG_COUNT", "GIT_TEMPLATE_DIR", "GIT_EXTERNAL_DIFF",
)
GIT_ENV_PREFIXES_TO_DROP = ("GIT_CONFIG_KEY_", "GIT_CONFIG_VALUE_", "GIT_TRACE")  # ...and the trace files git writes
# Given to every git call, above every configuration file: no hook and no file-system monitor program ever runs.
SAFE_SETTINGS = ("core.quotePath=false", "core.fsmonitor=false", "core.hooksPath=" + os.devnull)
GITLINK, SYMLINK, EXECUTABLE = "160000", "120000", "100755"


class Fail(Exception):
    """An expected failure: reported as one message, exit code 1."""


# ---------------------------------------------------------------- platform helpers

def configure_output():
    """Print file names as UTF-8, even on a console set to another code page (Windows)."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass


def local_path(root, rel):
    """A path from git (bytes, always '/'-separated) as a path on this system."""
    return os.path.join(str(root), *os.fsdecode(rel).split("/"))


def remove_file(path):
    """Delete one file or symbolic link, never following the link."""
    try:
        if os.name == "nt" and os.path.islink(path) and os.path.isdir(path):
            os.rmdir(path)  # Windows removes a link to a folder like a folder
        else:
            os.unlink(path)
    except PermissionError:
        if os.name != "nt":
            raise
        # Windows will not delete a read-only file: clear the flag and try once more.
        # A file another program holds open still fails here, and the caller reports it.
        os.chmod(path, stat.S_IWRITE)
        os.unlink(path)


def executable_bit(path):
    """Whether a file is marked executable; None on Windows, which has no such bit."""
    if os.name == "nt":
        return None
    return bool(os.stat(path).st_mode & 0o111)


def fidelity_settings():
    """git settings that keep executable bits and links exact in the store. Windows keeps what git found when it
    created the store: it has no executable bit, and links need Developer Mode."""
    return () if os.name == "nt" else ("core.filemode=true", "core.symlinks=true")


# Given to every command on the store: git creates no missing reference log there. It still appends to a log that
# already exists; the link-count check in check_state_folder keeps that append from reaching another file (G7).
STORE_SETTINGS = ("core.logAllRefUpdates=false",)


def is_link(path):
    """Whether a path is a symbolic link — or, on Windows, any reparse point, junctions included."""
    try:
        if os.name == "nt":
            return bool(getattr(os.lstat(path), "st_file_attributes", 0) & 0x400)  # FILE_ATTRIBUTE_REPARSE_POINT
        return os.path.islink(path)
    except OSError:
        return False


def write_lf(path, text):
    """Write a small text file with '\\n' line endings on every platform. The file is replaced whole, so a write
    never goes through a link or into another name for the same file."""
    path, data = Path(path), text.encode("utf-8")
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        if not is_link(str(path)) and path.read_bytes() == data:
            return
    except OSError:
        pass
    handle, temp = tempfile.mkstemp(prefix=path.name + ".", dir=str(path.parent))
    try:
        with os.fdopen(handle, "wb") as out:
            out.write(data)
        os.replace(temp, str(path))
    finally:
        if os.path.lexists(temp):
            os.unlink(temp)


def remove_temp(path):
    """Best-effort removal of a temporary folder, read-only files included."""
    def make_writable(func, target, _info):
        os.chmod(target, stat.S_IWRITE)
        func(target)
    try:
        if sys.version_info >= (3, 12):
            shutil.rmtree(path, onexc=make_writable)
        else:
            shutil.rmtree(path, onerror=make_writable)
    except OSError:
        pass  # a leftover in the system's temporary folder is harmless


# ---------------------------------------------------------------- git

def git(args, store=None, work_tree=None, cwd=None, index=None, stdin=None, ok=(0,), quiet=False, english=False):
    """Run one git command; raise Fail on an unexpected exit code — and, with quiet=True, on any warning: for a
    listing that means git could not see everything (an unreadable folder, for example). english=True keeps git's
    messages untranslated, for a message the tool has to recognize."""
    command = ["git"]
    for setting in SAFE_SETTINGS + (STORE_SETTINGS + fidelity_settings() if store is not None else ()):
        command += ["-c", setting]
    if store is not None:
        command.append("--git-dir=" + str(store))
    if work_tree is not None:
        command.append("--work-tree=" + str(work_tree))
    command += args
    env = {key: value for key, value in os.environ.items()
           if key not in GIT_ENV_TO_DROP and not key.startswith(GIT_ENV_PREFIXES_TO_DROP)}
    env.update(IDENTITY)
    env["GIT_OPTIONAL_LOCKS"] = "0"  # read-only commands never refresh the project's index
    env["GIT_TERMINAL_PROMPT"] = "0"
    # A partial clone makes git fetch an object it lacks the moment a command reads it — through a remote helper, a
    # credential helper or the network, none of which may run here (G11). git 2.46 and later obey this switch; for
    # an older git, nested_work() and prepare_store() refuse a partial clone instead.
    env["GIT_NO_LAZY_FETCH"] = "1"
    if index is not None:
        env["GIT_INDEX_FILE"] = str(index)
    if english:
        env["LC_ALL"] = "C"
    try:
        done = subprocess.run(command, cwd=None if cwd is None else str(cwd), input=stdin,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)
    except FileNotFoundError:
        raise Fail("git is not installed or not on the PATH")
    if done.returncode not in ok or (quiet and done.stderr.strip()):
        detail = done.stderr.decode("utf-8", "replace").strip() or "exit code %d" % done.returncode
        raise Fail("git %s %s: %s" % (args[0], "failed" if done.returncode not in ok else "reported a problem", detail))
    return done


def show(rel):
    return rel.decode("utf-8", "replace")


def warn(message):
    print("checkpoint.py: warning: " + message, file=sys.stderr)


_GIT_VERSION = []
PROMISOR_KEYS = r"^(extensions\.partialclone|remote\..*\.(promisor|partialclonefilter))$"


def git_version():
    """(major, minor) of the git on the PATH, read once."""
    if not _GIT_VERSION:
        found = re.search(rb"(\d+)\.(\d+)", git(["version"]).stdout)
        _GIT_VERSION.append((int(found.group(1)), int(found.group(2))) if found else (0, 0))
    return _GIT_VERSION[0]


def promisor_configured(folder=None, config=None):
    """Whether a repository (or a configuration file) tells git to fetch missing objects from a remote."""
    where = ["--file", str(config)] if config is not None else []
    return git(["config"] + where + ["--get-regexp", "-z", PROMISOR_KEYS], cwd=folder, ok=(0, 1)).returncode == 0


def blob_id(data, oid_length):
    """The id git gives these exact bytes, computed here so that no git setting can bend the check."""
    algorithm = hashlib.sha1 if oid_length == 40 else hashlib.sha256
    return algorithm(b"blob %d\0" % len(data) + data).hexdigest()


def file_id(path, oid_length):
    """blob_id of the bytes of the file at `path`, read in pieces."""
    digest = hashlib.sha1() if oid_length == 40 else hashlib.sha256()
    with open(path, "rb") as handle:
        digest.update(b"blob %d\0" % os.fstat(handle.fileno()).st_size)
        for piece in iter(lambda: handle.read(1 << 20), b""):
            digest.update(piece)
    return digest.hexdigest()
