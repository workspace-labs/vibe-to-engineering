#!/usr/bin/env python3
"""Recovery checkpoints for the vibe-to-engineering skill.

Implements the recovery contract and store format in references/recovery.md.
A checkpoint is a git tree kept in a separate bare repository at
<project>/.vibe-to-engineering/checkpoints.git; the project's own git
repository is only ever read.

Python 3.8+, standard library only. git is called with argument lists, never
through a shell, so this one file runs on macOS, Linux and Windows. The few
operating-system differences live in the "Platform helpers" section.
"""

import argparse
import fnmatch
import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import time
from collections import namedtuple
from pathlib import Path

STATE_DIR = ".vibe-to-engineering"
STORE_NAME = "checkpoints.git"
REF_PREFIX = "refs/checkpoints/"
ATTRIBUTES = "* -text -filter -ident -working-tree-encoding\n"
DEFAULT_EXCLUDES = (
    "node_modules/", "bower_components/", ".venv/", "venv/", "__pycache__/", "*.pyc",
    ".pytest_cache/", ".mypy_cache/", ".tox/", ".gradle/", ".next/", ".nuxt/",
    ".parcel-cache/", ".turbo/", ".DS_Store", "Thumbs.db",
)
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
    "GIT_AUTHOR_DATE", "GIT_COMMITTER_DATE",
    "GIT_CONFIG", "GIT_CONFIG_PARAMETERS", "GIT_CONFIG_COUNT", "GIT_TEMPLATE_DIR", "GIT_EXTERNAL_DIFF",
)
GIT_ENV_PREFIXES_TO_DROP = ("GIT_CONFIG_KEY_", "GIT_CONFIG_VALUE_", "GIT_TRACE")  # ...and the trace files git writes
# Given to every git call, above every configuration file: no hook and no file-system monitor program ever runs.
SAFE_SETTINGS = ("core.quotePath=false", "core.fsmonitor=false", "core.hooksPath=" + os.devnull)
LABEL_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{0,63}$")
GITLINK, SYMLINK, EXECUTABLE = "160000", "120000", "100755"
IGNORED_MARK = "ignored-by-git: "  # the line in a checkpoint's message that lists every ignored file it did not save
NESTED_MARK = "nested-repositories: "  # ...and the one that lists the nested repositories, which it does not save either
CONTENTS_MARK = "ignored-contents: "  # ...and the one that records each watched ignored file's size and fingerprint
# Ignored files that change by themselves and are too many to fingerprint: dependency, build-output and cache folders,
# and the default excluded files. Every other ignored file is watched for changes (G10).
UNWATCHED_FOLDERS = frozenset([entry[:-1] for entry in DEFAULT_EXCLUDES if entry.endswith("/")]
                              + ["dist", "build", "target", "coverage", ".cache"])
UNWATCHED_FILES = tuple(entry for entry in DEFAULT_EXCLUDES if not entry.endswith("/"))
# Files that hold secrets are never read: their fingerprint is their modification time, not a hash of their bytes.
SECRET_FILES = (".env", ".env.*", "*.env", "*.pem", "*.key", "*.p12", "*.pfx", "*.keystore", "*.jks", "id_rsa*",
                "id_ecdsa*", "id_ed25519*", "*credential*", "*secret*")
INDEX_ENTRY = re.compile(  # one entry of `git ls-files -z -s -v --debug`: tag, mode, id, stage, path, recorded stat data
    rb"([A-Za-z]) (\d{6}) ([0-9a-f]{40}|[0-9a-f]{64}) ([0-3])\t([^\0]*)\0"
    rb"  ctime: (\d+):(\d+)\n  mtime: (\d+):(\d+)\n  dev: (\d+)\tino: (\d+)\n  uid: (\d+)\tgid: (\d+)\n"
    rb"  size: (\d+)\tflags: [0-9a-f]+\n")

Found = namedtuple("Found", "files ignored nested disk")  # what a survey of the project found


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
# Store files the tool itself replaces whole (git config writes a lock file and renames it): a second name for one of
# them is harmless, because the write never reaches it. Any other store file with a second name is refused.
REPLACED_WHOLE = ("config", os.path.join("info", "attributes"), os.path.join("info", "exclude"))


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


# ---------------------------------------------------------------- project and store

def resolve_project(raw):
    project = Path(raw).expanduser().resolve()
    if not project.is_dir():
        raise Fail("project folder not found: %s" % project)
    if project == Path(project.anchor) or project == Path.home().resolve():
        raise Fail("%s is a home folder or a file-system root, not a project — pass the project's own folder" % project)
    if STATE_DIR in project.parts:
        raise Fail("the project folder cannot be inside %s" % STATE_DIR)
    return project


def store_path(project):
    return project / STATE_DIR / STORE_NAME


def is_git_project(project):
    """True when the folder is inside a git work tree whose repository does not ignore it. Only a folder git calls
    "not a git repository" follows the plain-folder rules: a repository git refuses to open (another user's folder,
    for example) stops the command, because those rules would drop its tracked files that match an ignore rule."""
    inside = git(["rev-parse", "--is-inside-work-tree"], cwd=project, ok=(0, 128), english=True)
    if inside.returncode != 0:
        message = inside.stderr.decode("utf-8", "replace").strip()
        if re.search(r"^fatal: not a git repository", message, re.M):
            return False
        raise Fail("git cannot open the repository this folder belongs to — %s" % message)
    if inside.stdout.strip() != b"true":
        return False
    return git(["check-ignore", "-q", "."], cwd=project, ok=(0, 1, 128)).returncode != 0


def check_state_folder(project):
    """Refuse a state folder, ignore file or store that could make a write land anywhere else (G7): a link or
    junction on the way, a special file, or a store that git would redirect to another repository."""
    state = project / STATE_DIR
    store = state / STORE_NAME
    for path, folder in ((state, True), (state / ".gitignore", False), (store, True)):
        if os.path.lexists(str(path)) and (is_link(str(path)) or not (path.is_dir() if folder else path.is_file())):
            raise Fail("%s is a link or not a plain %s — checkpoints are written only inside the project's own %s "
                       "folder. Nothing was changed" % (path, "folder" if folder else "file", STATE_DIR))
    if not store.is_dir():
        return
    for redirect in ("commondir", os.path.join("objects", "info", "alternates")):
        if os.path.lexists(str(store / redirect)):
            raise Fail("the store %s has a %s file, which makes git use another repository. Nothing was changed"
                       % (store, redirect))
    def unreadable(error):
        raise Fail("cannot read the folder %s inside the store (%s) — a link or a second name for another file could "
                   "hide there. Nothing was changed" % (error.filename, error.strerror or error))
    for folder, dirs, names in os.walk(str(store), onerror=unreadable):
        for name in dirs + names:
            path = os.path.join(folder, name)
            if is_link(path) or not (os.path.isdir(path) or os.path.isfile(path)):
                raise Fail("%s is a link or a special file inside the store. Nothing was changed" % path)
            if name in names and os.stat(path).st_nlink > 1 and os.path.relpath(path, str(store)) not in REPLACED_WHOLE:
                raise Fail("%s inside the store is also another file's name (a hard link), so a write to it would "
                           "change that file too. Nothing was changed" % path)


def prepare_store(project, git_project):
    """Create the store if needed and (re)write the settings that keep snapshots byte-exact — after making sure
    that every write stays inside the state folder (G7)."""
    check_state_folder(project)
    state = project / STATE_DIR
    if not state.exists():
        os.mkdir(str(state))
    ignore = state / ".gitignore"
    if not os.path.lexists(str(ignore)):
        with open(str(ignore), "x", encoding="utf-8", newline="\n") as handle:  # "x" never follows a link
            handle.write("*\n")
    store = state / STORE_NAME
    if not (store / "HEAD").exists():
        git(["init", "--bare", "--quiet", "--template=", str(store)])  # no template: no hooks copied in
    for key, value in (("core.autocrlf", "false"), ("core.safecrlf", "false"), ("core.longpaths", "true")):
        git(["config", "--file", str(store / "config"), key, value])
    write_lf(store / "info" / "attributes", ATTRIBUTES)
    excludes = ["/" + STATE_DIR + "/"] + ([] if git_project else list(DEFAULT_EXCLUDES))
    write_lf(store / "info" / "exclude", "\n".join(excludes) + "\n")
    return store


def open_store(project):
    if not (store_path(project) / "HEAD").exists():
        raise Fail("no checkpoints yet in %s — create one first" % project)
    return prepare_store(project, is_git_project(project))


# ---------------------------------------------------------------- what is on disk

def child(folder, name):
    return folder + b"/" + name if folder else name


def inside(rel, folders):
    """Whether rel lies inside one of `folders` (paths without a trailing '/')."""
    parts = rel.split(b"/")
    return any(b"/".join(parts[:depth]) in folders for depth in range(1, len(parts)))


def walk_disk(root):
    """Every file and link under root as the file system spells it (bytes, '/'-separated), and the names in each
    folder — found without git. Entries named .git and the state folder are left out, as git leaves them out.
    A folder that cannot be read stops the command (G1)."""
    files, folders, pending = set(), {}, [b""]
    while pending:
        folder = pending.pop()
        try:
            with os.scandir(local_path(root, folder)) as scan:
                entries = list(scan)
        except OSError as error:
            raise Fail("cannot read the folder %s (%s) — every folder has to be readable, or files could be left "
                       "out without anyone noticing" % (local_path(root, folder), error.strerror or error))
        folders[folder] = {os.fsencode(entry.name) for entry in entries}
        for entry in entries:
            name = os.fsencode(entry.name)
            rel = child(folder, name)
            if name == b".git" or rel == STATE_DIR.encode():
                continue
            if entry.is_symlink() or entry.is_file(follow_symlinks=False):
                files.add(rel)
            elif entry.is_dir(follow_symlinks=False):
                pending.append(rel)
    return files, folders


class Disk:
    """What is on disk under root and how the file system spells each name, read once per folder."""

    def __init__(self, root, folders=None):
        self.root, self.folders, self.inodes = root, dict(folders or {}), {}

    def names(self, folder):
        if folder not in self.folders:
            try:
                self.folders[folder] = {os.fsencode(name) for name in os.listdir(local_path(self.root, folder))}
            except OSError as error:
                raise Fail("cannot read the folder %s (%s)" % (local_path(self.root, folder), error.strerror or error))
        return self.folders[folder]

    def lstat(self, rel):
        return os.lstat(local_path(self.root, rel))

    def entry(self, folder, name):
        """The name under which `folder` lists what the file system opens for `name`: the name itself or, on a
        disk that ignores letter case or Unicode normalization, the one entry that is the same file — found by
        the file's identity, never by comparing spellings. None when nothing is there."""
        names = self.names(folder)
        if name in names:
            return name
        try:
            wanted = self.lstat(child(folder, name))
        except (FileNotFoundError, NotADirectoryError):
            return None
        if folder not in self.inodes:
            self.inodes[folder] = {}
            for other in names:
                found = self.lstat(child(folder, other))
                self.inodes[folder].setdefault((found.st_dev, found.st_ino), []).append(other)
        matches = self.inodes[folder].get((wanted.st_dev, wanted.st_ino), [])
        if len(matches) != 1:
            raise Fail("cannot tell which entry the name %s means on this disk (%d match) — did the project change "
                       "while it was being read?" % (show(child(folder, name)), len(matches)))
        return matches[0]

    def locate(self, rel):
        """(rel spelled as the file system spells it, its lstat), or (rel, None) when nothing is there — including
        when a name on the way is a file or a link instead of a folder."""
        spelled, parts = [], rel.split(b"/")
        for depth, part in enumerate(parts, 1):
            name = self.entry(b"/".join(spelled), part)
            if name is None:
                return rel, None
            spelled.append(name)
            here = b"/".join(spelled)
            if depth < len(parts) and here not in self.folders and not stat.S_ISDIR(self.lstat(here).st_mode):
                return rel, None
        return here, self.lstat(here)

    def emptied(self, folder, deleting, memo):
        """Whether deleting the files in `deleting`, then every folder that leaves empty (remove_emptied_folders),
        removes `folder` too."""
        if folder not in memo:
            removed = kept = False
            for name in self.names(folder):
                rel = child(folder, name)
                if name != b".git" and stat.S_ISDIR(self.lstat(rel).st_mode):
                    gone = self.emptied(rel, deleting, memo)
                else:
                    gone = rel in deleting
                removed, kept = removed or gone, kept or not gone
            memo[folder] = removed and not kept
        return memo[folder]


# ---------------------------------------------------------------- snapshots

def list_git(project, store, git_project, ignored):
    """git's own list of the project's files — with ignored=True, of every file it ignores — read-only, and only
    when git could see every folder."""
    args = ["ls-files", "-z", "--others", "--exclude-standard"] + (
        ["--ignored"] if ignored else ["--cached"] if git_project else [])
    view = {} if git_project else {"store": store, "work_tree": project}
    out = git(args, cwd=project, quiet=True, **view).stdout
    state = STATE_DIR.encode()
    return [rel for rel in out.split(b"\0") if rel and rel.rstrip(b"/") != state and not rel.startswith(state + b"/")]


def survey(project, store, git_project):
    """The project as a checkpoint must hold it (G1): the files to save, every ignored file and the nested
    repositories, each spelled as the file system spells it, and checked against a walk of the disk made without
    git, so nothing is left out unseen. In a git project it is the project's own view (git ls-files, read-only);
    otherwise the store's view."""
    on_disk, folders = walk_disk(project)
    disk = Disk(project, folders)
    files, ignored, nested = set(), set(), set()
    for rel in list_git(project, store, git_project, ignored=False):
        if rel.endswith(b"/"):  # a nested repository: git does not look inside it
            nested.add(disk.locate(rel[:-1])[0] + b"/")
            continue
        spelled, found = disk.locate(rel)
        if found is None:
            continue  # a tracked file that is gone from disk
        if not stat.S_ISDIR(found.st_mode):
            files.add(spelled)
        elif b".git" in disk.names(spelled):
            nested.add(spelled + b"/")  # a nested repository the project's own git tracks
        # else a tracked file that is now a folder: git lists the folder's files themselves
    for rel in list_git(project, store, git_project, ignored=True):
        spelled = disk.locate(rel.rstrip(b"/"))[0] + (b"/" if rel.endswith(b"/") else b"")
        ignored.add(spelled)
        if spelled.endswith(b"/"):
            nested.add(spelled)  # an ignored nested repository — git lists one as "x/", wherever it is — is checked too
    unsaved = {rel[:-1] for rel in nested | ignored if rel.endswith(b"/")}
    expected = {rel for rel in on_disk if not inside(rel, unsaved)}
    listed = files | {rel for rel in ignored if not rel.endswith(b"/")}
    if expected != listed:
        problems = ["%s: %s" % (words, ", ".join(show(rel) for rel in sorted(rels)[:10]))
                    for words, rels in (("on disk but not in git's list", expected - listed),
                                        ("in git's list but not on disk under that name", listed - expected)) if rels]
        raise Fail("git's list of the project's files does not match the disk (%s)" % "; ".join(problems))
    return Found(sorted(files), sorted(ignored), sorted(nested), disk)


def index_stat(info):
    """A file's stat data as git records it in an index entry: 32-bit fields, times as seconds and nanoseconds."""
    size = info.st_size & 0xFFFFFFFF
    return ((info.st_ctime_ns // 10**9) & 0xFFFFFFFF, info.st_ctime_ns % 10**9,
            (info.st_mtime_ns // 10**9) & 0xFFFFFFFF, info.st_mtime_ns % 10**9,
            info.st_dev & 0xFFFFFFFF, info.st_ino & 0xFFFFFFFF, info.st_uid & 0xFFFFFFFF, info.st_gid & 0xFFFFFFFF,
            0x80000000 if info.st_size and not size else size)


def nested_work(folder, name):
    """Work the git repository in `folder` holds that its own commits do not — staged, changed, deleted or unmerged
    files, untracked files, or such work in a repository nested inside it — as "<repository>: <what>", or None.

    git is never asked to read a file here: re-reading one runs whatever filter program the git settings name for it
    (G11). Each file is compared with its index entry instead: unchanged when its stat data is exactly what git
    recorded and it was not changed in the same instant the index was written — the test git itself applies —
    otherwise when its bytes hash to the recorded blob. So a file git converts on checkout (line endings, a filter)
    whose stat data changed counts as changed: stricter than `git status`, never looser."""
    where = git(["rev-parse", "--show-toplevel", "--absolute-git-dir"], cwd=folder).stdout.splitlines()
    if len(where) != 2 or not os.path.samefile(os.fsdecode(where[0]), str(folder)):
        raise Fail("git opens another repository there, not the one in %s" % name)
    listed, entries, at = git(["ls-files", "-z", "-s", "-v", "--debug"], cwd=folder, quiet=True).stdout, [], 0
    while at < len(listed):
        entry = INDEX_ENTRY.match(listed, at)
        if entry is None:
            raise Fail("git printed the index of %s in a form this tool does not know" % name)
        entries.append(entry.groups())
        at = entry.end()
    if git(["rev-parse", "-q", "--verify", "HEAD^{commit}"], cwd=folder, ok=(0, 1)).returncode:
        if entries:
            return "%s: files added but never committed" % name
    elif git(["diff-index", "--cached", "--quiet", "--ignore-submodules=none", "HEAD", "--"], cwd=folder,
             ok=(0, 1)).returncode:
        return "%s: staged changes" % name
    untracked = [rel for rel in git(["ls-files", "-z", "--others", "--exclude-standard"], cwd=folder,
                                    quiet=True).stdout.split(b"\0") if rel]
    if untracked:
        return "%s: untracked %s" % (name, show(untracked[0]))
    filemode = git(["config", "--bool", "core.filemode"], cwd=folder, ok=(0, 1)).stdout.strip() != b"false"
    written = os.stat(os.path.join(os.fsdecode(where[1]), "index")).st_mtime_ns if entries else 0
    written = ((written // 10**9) & 0xFFFFFFFF, written % 10**9)
    inner = []
    for tag, mode, oid, stage, rel, *recorded in entries:
        path, mode, oid = local_path(folder, rel), mode.decode(), oid.decode()
        if stage != b"0":
            return "%s: unmerged %s" % (name, show(rel))
        try:
            info = os.lstat(path)
        except (FileNotFoundError, NotADirectoryError):
            if mode == GITLINK or tag in b"Ss":
                continue  # a nested repository that is not checked out, or a file outside a sparse checkout
            return "%s: deleted %s" % (name, show(rel))
        if mode == GITLINK:
            if os.path.lexists(os.path.join(path, ".git")):
                head = git(["rev-parse", "-q", "--verify", "HEAD^{commit}"], cwd=path, ok=(0, 1)).stdout.strip()
                if head.decode() != oid:
                    return "%s: %s is not at the commit %s records" % (name, show(rel), name)
                inner.append(rel)
                continue
            same = stat.S_ISDIR(info.st_mode) and not os.listdir(path)  # an empty folder: not checked out
        elif mode == SYMLINK:
            same = (stat.S_ISLNK(info.st_mode) and blob_id(os.fsencode(os.readlink(path)), len(oid)) == oid) or (
                stat.S_ISREG(info.st_mode) and file_id(path, len(oid)) == oid)  # a link git keeps as a plain file
        else:
            fields = tuple(int(field) for field in recorded)
            same = (stat.S_ISREG(info.st_mode)
                    and (not filemode or executable_bit(path) in (None, mode == EXECUTABLE))
                    and ((fields == index_stat(info) and fields[2:4] < written) or file_id(path, len(oid)) == oid))
        if not same:
            return "%s: changed %s" % (name, show(rel))
    ignored = git(["ls-files", "-z", "--others", "--ignored", "--exclude-standard"], cwd=folder, quiet=True).stdout
    for rel in inner + [rel[:-1] for rel in ignored.split(b"\0") if rel.endswith(b"/")]:  # ignored: git lists a
        found = nested_work(Path(local_path(folder, rel)), "%s%s/" % (name, show(rel)))       # repository as "x/"
        if found:
            return found
    return None


def check_nested(project, nested):
    """A nested repository is not saved in checkpoints: its own git keeps its committed work. Refuse while one — or a
    repository inside it — holds work its own git does not keep, because nothing could bring that work back (G1)."""
    for rel in nested:
        try:
            work = nested_work(Path(local_path(project, rel[:-1])), show(rel))
        except (Fail, OSError) as error:
            raise Fail("cannot tell whether the nested repository %s holds unsaved work (%s)" % (show(rel), error))
        if work:
            raise Fail("the nested repository %s holds uncommitted changes or untracked files (%s). Checkpoints do "
                       "not save nested repositories, so that work would have no recovery point: it has to be "
                       "committed in that repository first, which is the human's decision. If `git status` there "
                       "shows nothing to commit, running it has refreshed git's record of the files: try again"
                       % (show(rel), work))


def snapshot(project, store, git_project, allow_empty):
    """Write the project's current files into the store and prove the tree holds exactly them: the same names,
    bytes, links and executable bits, checked here rather than trusted to git (G1). Returns (tree id, survey)."""
    found = survey(project, store, git_project)
    check_nested(project, found.nested)
    if not found.files and not allow_empty:
        raise Fail("found no files to save in %s — check the folder and its ignore rules" % project)
    temp = tempfile.mkdtemp(prefix="v2e-")
    try:
        index = os.path.join(temp, "index")
        if found.files:
            git(["update-index", "--add", "-z", "--stdin"], store=store, work_tree=project, cwd=project,
                index=index, stdin=b"\0".join(found.files) + b"\0", quiet=True)
        tree = git(["write-tree"], store=store, index=index).stdout.strip().decode()
    finally:
        remove_temp(temp)
    saved = tree_files(store, tree)
    wrong = sorted(set(saved) ^ set(found.files))
    for rel in sorted(set(saved) & set(found.files)):
        mode, oid = saved[rel]
        path = local_path(project, rel)
        if os.path.islink(path):
            same = mode == SYMLINK and blob_id(os.fsencode(os.readlink(path)), len(oid)) == oid
        else:
            same = (mode != SYMLINK and file_id(path, len(oid)) == oid
                    and executable_bit(path) in (None, mode == EXECUTABLE))
        if not same:
            wrong.append(rel)
    if wrong:
        raise Fail("the snapshot does not match the files on disk (%s) — a file changed while it was being saved, or "
                   "git altered it" % ", ".join(show(rel) for rel in wrong[:10]))
    return tree, found


def tree_files(store, treeish):
    """path (bytes) -> (mode, object id) for every file in a tree; nested repositories are left out."""
    out = git(["ls-tree", "-r", "-z", "--full-tree", treeish], store=store).stdout
    files = {}
    for record in out.split(b"\0"):
        if record:
            meta, rel = record.split(b"\t", 1)
            mode, _kind, oid = meta.decode().split(" ")
            if mode != GITLINK:
                files[rel] = (mode, oid)
    return files


def write_files(store, commit, target, paths=None):
    """Write a checkpoint's files — all of them, or only `paths` — into the folder `target`."""
    temp = tempfile.mkdtemp(prefix="v2e-")
    try:
        index = os.path.join(temp, "index")
        git(["read-tree", commit], store=store, index=index)
        if paths is None:
            git(["checkout-index", "--all", "--force"], store=store, work_tree=target, cwd=target, index=index)
        elif paths:
            git(["checkout-index", "--force", "-z", "--stdin"], store=store, work_tree=target, cwd=target,
                index=index, stdin=b"\0".join(paths) + b"\0")
    finally:
        remove_temp(temp)


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


def verify_commit(project, store, commit, label):
    """Write a checkpoint into an empty folder on the project's own disk and compare it with its tree: exactly the
    same names (two names this disk treats as one collide here, and one goes missing) and, for each, the same
    bytes, link and executable bit (G4). Raises Fail naming what did not come back; returns the file count."""
    files = tree_files(store, commit)
    temp = tempfile.mkdtemp(prefix="verify-", dir=str(project / STATE_DIR))
    try:
        try:
            write_files(store, commit, temp)
        except Fail as error:
            raise Fail("checkpoint %s cannot be written back — %s" % (label, error))
        found = walk_disk(temp)[0]
        problems = set(files) ^ found
        for rel in found & set(files):
            mode, oid = files[rel]
            path = local_path(temp, rel)
            if os.path.islink(path):
                same = mode == SYMLINK and blob_id(os.fsencode(os.readlink(path)), len(oid)) == oid
            elif mode == SYMLINK and os.name != "nt":
                same = False  # should have come back as a link (Windows without link support writes a file)
            else:
                same = (file_id(path, len(oid)) == oid
                        and (mode == SYMLINK or executable_bit(path) in (None, mode == EXECUTABLE)))
            if not same:
                problems.add(rel)
    finally:
        remove_temp(temp)
    if problems:
        listed = ", ".join(show(rel) for rel in sorted(problems)[:20])
        raise Fail("checkpoint %s did not come back identical (%d files): %s" % (label, len(problems), listed))
    return len(files)


# ---------------------------------------------------------------- checkpoints

def check_label(label):
    if not LABEL_RE.match(label) or ".." in label or label.endswith((".", ".lock")):
        raise Fail("invalid label %r: use lowercase letters, digits, '.', '_' and '-' (at most 64 characters)" % label)


def label_exists(store, label):
    return git(["rev-parse", "--verify", "--quiet", REF_PREFIX + label], store=store, ok=(0, 1, 128)).returncode == 0


def checkpoints(store):
    """(label, created, commit) for every checkpoint, oldest first."""
    out = git(["for-each-ref", "--sort=refname", "--sort=committerdate",
               "--format=%(refname)%00%(committerdate:iso-strict)%00%(objectname)", REF_PREFIX], store=store).stdout
    rows = []
    for line in out.decode("utf-8", "replace").splitlines():
        ref, created, commit = line.split("\0")
        rows.append((ref[len(REF_PREFIX):], created, commit))
    return rows


def resolve(store, label):
    check_label(label)
    found = git(["rev-parse", "--verify", "--quiet", REF_PREFIX + label + "^{commit}"], store=store, ok=(0, 1, 128))
    if found.returncode != 0:
        known = ", ".join(row[0] for row in checkpoints(store)) or "none yet"
        raise Fail("no checkpoint named %r (existing: %s)" % (label, known))
    return found.stdout.strip().decode()


def save_checkpoint(store, tree, label, found, contents):
    """Commit a tree under a new label with what it does not hold; a label that exists already is refused (G3)."""
    if label_exists(store, label):
        raise Fail("checkpoint %r already exists — labels are permanent; choose a new one" % label)
    message = "vibe-to-engineering checkpoint: %s\n\n%s%s\n%s%s\n%s%s\n" % (
        label, IGNORED_MARK, json.dumps([os.fsdecode(rel) for rel in found.ignored]),
        NESTED_MARK, json.dumps([os.fsdecode(rel) for rel in found.nested]),
        CONTENTS_MARK, json.dumps(contents, sort_keys=True))
    commit = git(["commit-tree", "--no-gpg-sign", "-m", message, tree], store=store).stdout.strip().decode()
    git(["update-ref", REF_PREFIX + label, commit, ""], store=store)  # "": only if the ref does not exist
    return commit


def recorded(store, commit, mark):
    """The entries a checkpoint recorded on its `mark` line — names, or for CONTENTS_MARK a name -> [size,
    fingerprint] object — or None for a checkpoint that recorded none."""
    message = git(["cat-file", "commit", commit], store=store).stdout.decode("utf-8", "surrogateescape")
    for line in message.splitlines():
        if line.startswith(mark):
            found = json.loads(line[len(mark):])
            return found if isinstance(found, dict) else [os.fsencode(name) for name in found]
    return None


def watched_contents(project, ignored):
    """name -> [size, fingerprint] for every ignored file outside dependency, build-output and cache folders, so that
    diff and restore can tell when one changed, though no checkpoint holds it (G10). The fingerprint is the SHA-256 of
    the bytes — for a file that holds secrets, which is never read, its modification time. A watched file that cannot
    be read stops the command: a change to it could not be noticed."""
    contents = {}
    for rel in ignored:
        parts = os.fsdecode(rel).split("/")
        if rel.endswith(b"/") or UNWATCHED_FOLDERS.intersection(parts[:-1]) or any(
                fnmatch.fnmatchcase(parts[-1], pattern) for pattern in UNWATCHED_FILES):
            continue
        path = local_path(project, rel)
        try:
            info = os.lstat(path)
            if any(fnmatch.fnmatchcase(parts[-1].lower(), pattern) for pattern in SECRET_FILES):
                fingerprint = "mtime:%d" % info.st_mtime_ns
            elif stat.S_ISLNK(info.st_mode):
                fingerprint = "sha256:" + hashlib.sha256(os.fsencode(os.readlink(path))).hexdigest()
            else:
                digest = hashlib.sha256()
                with open(path, "rb") as handle:
                    for piece in iter(lambda: handle.read(1 << 20), b""):
                        digest.update(piece)
                fingerprint = "sha256:" + digest.hexdigest()
        except OSError as error:
            raise Fail("cannot read %s, a file git ignores (%s) — without reading it, a change to it could not be "
                       "noticed" % (show(rel), error.strerror or error))
        contents[os.fsdecode(rel)] = [info.st_size, fingerprint]
    return contents


def changed_since(store, commit, contents):
    """Watched ignored files still there whose size or fingerprint differs from what a checkpoint recorded (G10):
    (name, [size, fingerprint] then, [size, fingerprint] now)."""
    before = recorded(store, commit, CONTENTS_MARK)
    if before is None or contents is None:
        return []
    return [(name, before[name], contents[name]) for name in sorted(before)
            if name in contents and before[name] != contents[name]]


def report_changed(changed, label):
    print("files git ignores whose contents changed since %s — checkpoints do not hold them, so their earlier "
          "contents cannot be restored from here:" % label)
    for name, (old_size, _), (new_size, _) in changed[:40]:
        print("  changed  %s  (%s)" % (name, "the same size" if old_size == new_size
                                       else "%d bytes, was %d" % (new_size, old_size)))
    if len(changed) > 40:
        print("  … and %d more" % (len(changed) - 40))


def missing(before, after):
    """Entries recorded before that are gone now. An entry still counts as there while it is listed, while
    something inside it is listed, or while a folder around it is listed as one entry (a nested repository)."""
    if before is None or after is None:
        return []
    present, folders = set(after), {rel for rel in after if rel.endswith(b"/")}
    for rel in after:
        parts = rel.rstrip(b"/").split(b"/")
        present.update(b"/".join(parts[:depth]) + b"/" for depth in range(1, len(parts)))

    def around(rel):
        parts = rel.rstrip(b"/").split(b"/")
        return any(b"/".join(parts[:depth]) + b"/" in folders for depth in range(1, len(parts)))
    return [rel for rel in before if rel not in present and not around(rel)]


def gone_since(store, commit, ignored, nested):
    """What a checkpoint recorded as there but not saved — ignored files, nested repositories — that is gone (G10)."""
    gone = missing(recorded(store, commit, IGNORED_MARK), ignored) + missing(recorded(store, commit, NESTED_MARK), nested)
    return list(dict.fromkeys(gone))  # an ignored nested repository is on both lists: report it once


# ---------------------------------------------------------------- commands

def cmd_create(project, args):
    check_label(args.label)
    git_project = is_git_project(project)
    store = prepare_store(project, git_project)
    if label_exists(store, args.label):
        raise Fail("checkpoint %r already exists — labels are permanent; choose a new one" % args.label)
    tree, found = snapshot(project, store, git_project, allow_empty=False)
    commit = save_checkpoint(store, tree, args.label, found, watched_contents(project, found.ignored))
    for rel in found.nested:
        warn("nested repository %s is not saved in checkpoints — its own git keeps its committed work, and it holds "
             "no other work now" % show(rel))
    print("created checkpoint %s: %d files (commit %s)" % (args.label, len(found.files), commit[:12]))
    return 0


def cmd_verify(project, args):
    store = open_store(project)
    count = verify_commit(project, store, resolve(store, args.label), args.label)
    print("verified %s: all %d files come back byte for byte, under exactly their saved names" % (args.label, count))
    return 0


def cmd_list(project, args):
    store = open_store(project)
    rows = checkpoints(store)
    if not rows:
        print("no checkpoints yet")
    for label, created, commit in rows:
        print("%-34s %s  %6d files  %s" % (label, created, len(tree_files(store, commit)), commit[:12]))
    return 0


def parse_name_status(out):
    fields = out.split(b"\0")
    changes, i = [], 0
    while i < len(fields) and fields[i]:
        status = fields[i].decode()
        width = 2 if status[0] in "RC" else 1
        changes.append((status, fields[i + 1:i + 1 + width]))
        i += 1 + width
    return changes


def cmd_diff(project, args):
    store = open_store(project)
    old = resolve(store, args.old)
    if args.new:
        new, new_name = resolve(store, args.new), args.new
        now = (recorded(store, new, IGNORED_MARK), recorded(store, new, NESTED_MARK))
        contents = recorded(store, new, CONTENTS_MARK)
    else:
        new, found = snapshot(project, store, is_git_project(project), allow_empty=True)
        new_name, now = "the current files", (found.ignored, found.nested)
        contents = watched_contents(project, found.ignored)
    limit = ["--"] + args.path if args.path else []
    out = git(["diff-tree", "-r", "-z", "-M", "--name-status", "--no-ext-diff", old, new] + limit, store=store).stdout
    changes = parse_name_status(out)
    gone = [] if args.path else gone_since(store, old, *now)
    changed = [] if args.path else changed_since(store, old, contents)
    if not changes and not gone and not changed:
        print("no changes from %s to %s" % (args.old, new_name))
        return 0
    if changes:
        words = {"A": "added", "D": "deleted", "M": "modified", "R": "moved", "C": "copied", "T": "type changed"}
        counts = {}
        print("changes from %s to %s:" % (args.old, new_name))
        for status, paths in changes:
            counts[status[0]] = counts.get(status[0], 0) + 1
            print("  %-5s %s" % (status, " -> ".join(show(p) for p in paths)))
        print("%d %s: %s" % (len(changes), "change" if len(changes) == 1 else "changes", ", ".join(
            "%d %s" % (n, words.get(s, s)) for s, n in sorted(counts.items()))))
    if gone:
        print("files git ignores and nested repositories that were there at %s and are gone now — checkpoints do not "
              "hold them, so they cannot be restored from here:" % args.old)
        for rel in gone:
            print("  gone  %s" % show(rel))
    if changed:
        report_changed(changed, args.old)
    if args.patch:
        patch = git(["diff-tree", "-r", "-M", "-p", "--no-ext-diff", "--no-textconv", old, new] + limit,
                    store=store).stdout
        sys.stdout.flush()
        sys.stdout.buffer.write(patch)
        sys.stdout.buffer.flush()
    return 3


def current_survey_read_only(project):
    """What a checkpoint would hold now — the files, and the ignored files and nested repositories it would leave
    out — found without writing anything in the project (G9)."""
    if is_git_project(project):
        return survey(project, None, True)
    temp = tempfile.mkdtemp(prefix="v2e-tree-")
    try:
        store = os.path.join(temp, "store.git")
        git(["init", "--bare", "--quiet", "--template=", store])
        write_lf(os.path.join(store, "info", "exclude"),
                 "\n".join(["/" + STATE_DIR + "/"] + list(DEFAULT_EXCLUDES)) + "\n")
        return survey(project, store, False)
    finally:
        remove_temp(temp)


def plural(count, one, many):
    return "%d %s" % (count, one if count == 1 else many)


MARKS = {"ignored": "[ignored — never touched]", "nested": "[nested repository — never touched]",
         "state": "[the skill's own folder]"}


def print_tree(title, saved, depth, full=False, ignored=(), nested=(), state=False):
    """The saved files as a tree, folders opened `depth` levels deep. With full=True, also every file git ignores and
    every nested repository, each marked where it sits — a folder holding nothing but ignored files as one line —
    and the skill's own folder, then the count of each kind. ignored or nested None: the checkpoint did not record
    them."""
    root = {}
    repos = sorted(set(nested or ()) | {rel for rel in ignored or () if rel.endswith(b"/")})
    leaves = [(rel, "saved") for rel in saved]
    if full:
        leaves += [(rel, "ignored") for rel in ignored or () if not rel.endswith(b"/")]
        leaves += [(rel, "nested") for rel in repos] + ([(STATE_DIR.encode() + b"/", "state")] if state else [])
    for rel, kind in leaves:
        node, parts = root, show(rel).rstrip("/").split("/")
        for part in parts[:-1]:
            node = node.setdefault(part + "/", {})
        node[parts[-1] + ("/" if rel.endswith(b"/") else "")] = kind

    def count(node):
        found = {"saved": 0, "ignored": 0, "nested": 0, "state": 0}
        for child in node.values():
            for kind, number in (count(child).items() if isinstance(child, dict) else [(child, 1)]):
                found[kind] += number
        return found

    lines, folded = [], []

    def walk(node, prefix, level):
        names = sorted(node, key=lambda name: (not name.endswith("/"), name.lower()))
        for position, name in enumerate(names):
            last = position == len(names) - 1
            child = node[name]
            line = prefix + ("└── " if last else "├── ") + name
            if not isinstance(child, dict):
                lines.append((line, MARKS.get(child)))
                continue
            found = count(child)
            if found["ignored"] and not (found["saved"] or found["nested"]):
                folded.append(name)
                lines.append((line, "[ignored folder — %s, never touched]" % plural(found["ignored"], "file", "files")))
            elif level >= depth:
                counts = [plural(found["saved"], "file", "files")] + (
                    ["%d ignored" % found["ignored"]] if found["ignored"] else []) + (
                    [plural(found["nested"], "nested repository", "nested repositories")] if found["nested"] else [])
                lines.append(("%s (%s)" % (line, " · ".join(counts)), None))
            else:
                lines.append((line, None))
                walk(child, prefix + ("    " if last else "│   "), level + 1)

    walk(root, "", 1)
    print(title)
    column = min(max([len(line) for line, mark in lines if mark] or [0]), 40) + 2
    for line, mark in lines:
        print((line + "  ").ljust(column) + mark if mark else line)
    if not full:
        print("\n%d files" % len(saved))
    elif ignored is None or nested is None:
        print("\n%s saved — this checkpoint did not record which files git ignored or which nested repositories there "
              "were" % plural(len(saved), "file", "files"))
    else:
        others = [rel for rel in ignored if not rel.endswith(b"/")]
        print("\n%s saved · %d ignored%s · %s — ignored files and nested repositories are never touched and not in "
              "checkpoints" % (plural(len(saved), "file", "files"), len(others),
                               " (%s)" % plural(len(folded), "folder", "folders") if folded else "",
                               plural(len(repos), "nested repository", "nested repositories")))


def cmd_tree(project, args):
    if args.label and args.current:
        raise Fail("give a label or --current, not both")
    if args.depth < 1:
        raise Fail("--depth must be 1 or more")
    if args.label:
        store = open_store(project)
        commit = resolve(store, args.label)
        saved, state = list(tree_files(store, commit)), True
        ignored, nested = recorded(store, commit, IGNORED_MARK), recorded(store, commit, NESTED_MARK)
        title = "%s @ %s" % (project.name, args.label)
    else:
        found = current_survey_read_only(project)
        saved, ignored, nested = found.files, found.ignored, found.nested
        state = os.path.lexists(str(project / STATE_DIR))
        title = "%s (current files)" % project.name
    print_tree(title, saved, args.depth, not args.saved_only, ignored, nested, state)
    return 0


def cmd_extract(project, args):
    store = open_store(project)
    commit = resolve(store, args.label)
    target = Path(args.folder).expanduser().resolve()
    if target == project or project in target.parents:
        raise Fail("extract into a folder outside the project, not %s" % target)
    if target.exists() and (not target.is_dir() or any(target.iterdir())):
        raise Fail("%s must be a new or empty folder" % target)
    target.mkdir(parents=True, exist_ok=True)
    write_files(store, commit, target)
    print("extracted %s into %s (%d files)" % (args.label, target, len(tree_files(store, commit))))
    return 0


def remove_emptied_folders(project, removed):
    """Remove folders the deletions left empty, deepest first; never the project or the state folder."""
    folders = set()
    for rel in removed:
        parts = rel.split(b"/")[:-1]
        for depth in range(1, len(parts) + 1):
            folders.add(tuple(parts[:depth]))
    for parts in sorted(folders, key=len, reverse=True):
        if parts[0] == STATE_DIR.encode():
            continue
        try:
            os.rmdir(local_path(project, b"/".join(parts)))  # succeeds only when the folder is empty
        except OSError:
            pass


def list_some(verb, paths):
    for rel in paths[:40]:
        print("  %s %s" % (verb, show(rel)))
    if len(paths) > 40:
        print("  … and %d more" % (len(paths) - 40))


def collisions(disk, now, to_delete, to_write):
    """What a restore would overwrite, replace or remove although no checkpoint holds it (G6): a file or link the
    checkpoints do not save where the restore writes, a folder still holding such files where a file goes, or a
    folder the restore could only reach under another spelling. The restore deletes `to_delete`, then the folders
    that leaves empty, then writes `to_write`."""
    deleting, memo, found = set(to_delete), {}, set()
    for rel in to_write:
        parts = rel.split(b"/")
        for depth in range(1, len(parts) + 1):
            here = b"/".join(parts[:depth])
            spelled, entry = disk.locate(here)
            if entry is None:
                break  # nothing there: git creates it
            if stat.S_ISDIR(entry.st_mode):
                if depth < len(parts) and spelled == here and b".git" in disk.names(spelled):
                    found.add(spelled)  # a nested repository: nothing is written inside it
                    break
                if depth < len(parts) and spelled == here:
                    continue  # a folder on the way
                if not disk.emptied(spelled, deleting, memo):
                    found.add(spelled)  # git would remove it with what is inside, or keep its old spelling
                break
            if spelled not in deleting and not (depth == len(parts) and spelled == here and here in now):
                found.add(spelled)  # a file or link no checkpoint holds, or a second name for one the restore writes
            break
    return sorted(found)


def cmd_restore(project, args):
    # 1. validate: the store, the label, the current files, what the restore changes and what it must not touch
    store = open_store(project)
    git_project = is_git_project(project)
    commit = resolve(store, args.label)
    wanted = tree_files(store, commit)
    now_tree, found = snapshot(project, store, git_project, allow_empty=True)
    now = tree_files(store, now_tree)
    to_delete = sorted(rel for rel in now if rel not in wanted)
    to_write = sorted(rel for rel, entry in wanted.items() if now.get(rel) != entry)
    gone = gone_since(store, commit, found.ignored, found.nested)
    if gone:
        print("warning: files git ignores or nested repositories that were there at %s are gone, and a restore cannot "
              "bring them back:" % args.label)
        list_some("gone   ", gone)
    contents = watched_contents(project, found.ignored)
    changed = changed_since(store, commit, contents)
    if changed:
        print("warning: a restore cannot bring back what these ignored files held at %s either." % args.label)
        report_changed(changed, args.label)
    if not to_delete and not to_write:
        print("the project already matches %s — nothing to restore" % args.label)
        return 0
    print("restoring %s rewrites %d file(s) and deletes %d file(s) added since then:"
          % (args.label, len(to_write), len(to_delete)))
    list_some("rewrite", to_write)
    list_some("delete ", to_delete)
    unsafe = collisions(found.disk, now, to_delete, to_write)
    refused = ("this restore is refused: it would overwrite or remove what no checkpoint holds (files git ignores, "
               "nested repositories, or a folder holding them): %s" % ", ".join(show(rel) for rel in unsafe[:20]))
    if not args.apply:
        if unsafe:
            raise Fail(refused + ". Nothing in the project was changed")
        print("nothing was changed. Run again with --apply only after the human approves this restore.")
        return 0
    # 2. keep the current state, 3. prove it comes back, 4. prove the checkpoint to restore comes back
    saved = "pre-restore-" + time.strftime("%Y%m%dt%H%M%Sz", time.gmtime())
    save_checkpoint(store, now_tree, saved, found, contents)
    print("saved the current state as checkpoint %s" % saved)
    try:
        verify_commit(project, store, resolve(store, saved), saved)
        verify_commit(project, store, commit, args.label)
    except Fail as error:
        raise Fail("%s — so the restore did not start. Nothing in the project was changed" % error)
    # 5. safety: nothing it must not touch is in its way, and the project is still exactly what was saved
    if unsafe:
        raise Fail("%s. Nothing in the project was changed; the current state is saved as checkpoint %s"
                   % (refused, saved))
    again_tree, again = snapshot(project, store, git_project, allow_empty=True)
    if (again_tree, again.ignored, again.nested) != (now_tree, found.ignored, found.nested):
        raise Fail("the project changed while the restore was being prepared. Nothing in the project was changed; "
                   "run the restore again")
    # 6. change the project: delete first — on a case-insensitive disk the old and new name are one file
    stuck = []
    for rel in to_delete:
        try:
            remove_file(local_path(project, rel))
        except FileNotFoundError:
            pass
        except OSError as error:
            stuck.append("could not delete %s (%s)" % (show(rel), error.strerror or error))
    remove_emptied_folders(project, to_delete)
    try:
        write_files(store, commit, project, to_write)
    except Fail as error:
        stuck.append(str(error))
    # 7. verify the result, and that everything the checkpoints do not hold is still there
    different = []
    try:
        after = tree_files(store, snapshot(project, store, git_project, allow_empty=True)[0])
        different = sorted(rel for rel in set(after) | set(wanted) if after.get(rel) != wanted.get(rel))
    except Fail as error:
        stuck.append(str(error))
    disk = Disk(project)
    lost = [rel for rel in dict.fromkeys(found.ignored + found.nested) if disk.locate(rel.rstrip(b"/"))[1] is None]
    if stuck or different or lost:
        details = stuck + ["differs: " + show(rel) for rel in different[:20]] + ["lost: " + show(rel) for rel in lost[:20]]
        raise Fail("the restore did not complete — %s. Everything from before the restore is saved as "
                   "checkpoint %s." % ("; ".join(details), saved))
    print("restored %s: the project matches it again (verified)" % args.label)
    return 0


COMMANDS = {
    "create": cmd_create, "verify": cmd_verify, "list": cmd_list, "diff": cmd_diff,
    "tree": cmd_tree, "extract": cmd_extract, "restore": cmd_restore,
}


def build_parser():
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--project", default=argparse.SUPPRESS,
                        help="the project folder (default: the current folder)")
    parser = argparse.ArgumentParser(prog="checkpoint.py", parents=[common],
                                     description="Recovery checkpoints for vibe-to-engineering "
                                                 "(contract: references/recovery.md).")
    commands = parser.add_subparsers(dest="command", metavar="command")
    commands.required = True

    def add(name, summary):
        return commands.add_parser(name, parents=[common], help=summary, description=summary)

    add("create", "save the project's current files as a checkpoint").add_argument("label")
    add("verify", "prove a checkpoint comes back byte for byte").add_argument("label")
    add("list", "list the checkpoints")
    diff = add("diff", "changes from a checkpoint to another one, or to the current files")
    diff.add_argument("old", metavar="from")
    diff.add_argument("new", metavar="to", nargs="?")
    diff.add_argument("--patch", action="store_true", help="also show the changed lines")
    diff.add_argument("--path", action="append", default=[], help="limit to this path (repeatable)")
    tree = add("tree", "tree view of a checkpoint, or of the current files, with every file git ignores and every "
                       "nested repository marked where it sits (writes nothing)")
    tree.add_argument("label", nargs="?")
    tree.add_argument("--current", action="store_true", help="the current files (the default)")
    tree.add_argument("--depth", type=int, default=3, help="folder levels to open (default 3)")
    tree.add_argument("--saved-only", action="store_true", help="only the files checkpoints save, unmarked")
    extract = add("extract", "write a checkpoint's files into a new or empty folder outside the project")
    extract.add_argument("label")
    extract.add_argument("folder")
    restore = add("restore", "show what restoring a checkpoint would change; --apply does it")
    restore.add_argument("label")
    restore.add_argument("--apply", action="store_true", help="do it (only after the human approves)")
    return parser


def main(argv=None):
    configure_output()
    args = build_parser().parse_args(argv)
    try:
        project = resolve_project(getattr(args, "project", "."))
        return COMMANDS[args.command](project, args)
    except Fail as error:
        print("checkpoint.py: error: %s" % error, file=sys.stderr)
    except OSError as error:
        print("checkpoint.py: error: %s" % error, file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
