"""Running git safely, and the few things that differ between operating systems — shared by every module of
the checkpoint tool.

Every git call goes through git(): argument lists, never a shell; hooks, file-system monitors and lazy fetching
off; the environment variables that would point git elsewhere dropped (G11). One question is answered without git,
because asking git would change the repository: whether its index is a sparse or a split index. The platform helpers
keep the operating-system differences in one place, as references/recovery.md section 4 promises.
"""

import hashlib
import os
import re
import shutil
import stat
import struct
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


# ---------------------------------------------------------------- git's index, read without git

def offset_varint(data, at):
    """The number git's offset varint encodes at `at` (as index version 4 and pack files use it), and where it ends."""
    byte = data[at]
    value, at = byte & 0x7F, at + 1
    while byte & 0x80:
        byte = data[at]
        value, at = (value + 1) << 7 | byte & 0x7F, at + 1
    return value, at


def read_index(data, oid_size):
    """What the bytes of one git index file hold, read the way git's read-cache.c reads them when object ids are
    `oid_size` bytes long: (sparse, shared) — whether an entry stands for a whole folder (mode 040000) or the "sdir"
    extension is there, and the id of the shared index a split index names ("link"), or None. None instead when the
    bytes do not end exactly where the trailing checksum of that length begins: then the ids have another length."""
    try:
        signature, version, count = struct.unpack_from(">4sLL", data, 0)
        if signature != b"DIRC" or version not in (2, 3, 4):
            return None
        at, previous, sparse, shared, end = 12, 0, False, None, len(data) - oid_size
        for _ in range(count):  # 40 bytes of stat data (the mode at 24), the id, 16 bits of flags, perhaps 16 more
            mode, = struct.unpack_from(">L", data, at + 24)
            flags, = struct.unpack_from(">H", data, at + 40 + oid_size)
            sparse = sparse or (mode & 0o170000) == 0o040000
            name, length = at + 42 + oid_size + (2 if version >= 3 and flags & 0x4000 else 0), flags & 0xFFF
            if version == 4:  # strip that many bytes from the previous path, add a NUL-terminated suffix, no padding
                strip, name = offset_varint(data, name)
                if strip > previous:
                    return None
                kept = previous - strip
                if length == 0xFFF:
                    length = data.index(b"\0", name) - name + kept
                if length < kept:
                    return None
                at, previous = name + length - kept + 1, length
            else:  # NUL-terminated, padded with NULs to a multiple of 8 bytes: git's ondisk_ce_size
                if length == 0xFFF:
                    length = data.index(b"\0", name) - name
                at += (name - at + length + 8) & ~7
            if at > end:
                return None
        while at + 8 <= end:  # extensions: a 4-byte signature, a 32-bit size, the data
            extension, size = struct.unpack_from(">4sL", data, at)
            sparse = sparse or extension == b"sdir"
            if extension == b"link" and data[at + 8:at + 8 + oid_size].strip(b"\0"):
                shared = data[at + 8:at + 8 + oid_size].hex()  # all zeros: the index needs no shared index
            at += 8 + size
        return (sparse, shared) if at == end else None
    except (struct.error, ValueError, IndexError):
        return None


def index_readings(git_dir, shared=None):
    """What the index git keeps in `git_dir` holds — or the shared index a split index names — as read_index reads
    it for each length of object id; [] when there is no index. Read here, byte by byte, because asking git changes
    the repository. An index this tool cannot read is not inspected (Fail)."""
    path = os.path.join(str(git_dir), "index" if shared is None else "sharedindex." + shared)
    try:
        with open(path, "rb") as handle:
            data = handle.read()
    except FileNotFoundError:
        if shared is None:
            return []
        raise Fail("cannot read git's index at %s: the file is missing" % path)
    except OSError as error:
        raise Fail("cannot read git's index at %s (%s)" % (path, error.strerror or error))
    readings = [reading for reading in (read_index(data, 20), read_index(data, 32)) if reading is not None]
    if not readings:
        raise Fail("cannot read git's index at %s: it is not in a form this tool knows" % path)
    return readings


def sparse_index(git_dir, shared=None):
    """Whether the index git keeps in `git_dir` — or, for a split index, the shared index it names — is a sparse
    index: one where an entry stands for a whole folder outside a sparse checkout. False when there is no index."""
    return any(sparse or (link is not None and shared is None and sparse_index(git_dir, link))
               for sparse, link in index_readings(git_dir, shared))


def refuse_sparse_index(git_dir, name):
    """git expands a sparse index to list a repository's files — writing tree objects there, and on a partial clone
    fetching them from its remote first — and it rewrites the time of a split index's shared index file every time it
    reads the index; so a repository whose index is either is refused before git runs any command that reads its
    index (G11)."""
    if sparse_index(git_dir):
        raise Fail("%s keeps a sparse index, which git expands just to list its files — writing new objects into that "
                   "repository, and on a partial clone fetching them from its remote — so it cannot be inspected "
                   "without changing it, and turning the sparse index off there is the human's decision" % name)
    if any(link is not None for _, link in index_readings(git_dir)):
        raise Fail("%s keeps a split index, and git rewrites the time of its shared index file every time it reads "
                   "the index — so it cannot be inspected without changing it, and turning the split index off there "
                   "is the human's decision" % name)


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
