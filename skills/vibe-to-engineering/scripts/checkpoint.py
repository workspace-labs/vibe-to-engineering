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
# Inherited variables that would point git at another repository, index or date.
GIT_ENV_TO_DROP = (
    "GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_OBJECT_DIRECTORY",
    "GIT_ALTERNATE_OBJECT_DIRECTORIES", "GIT_COMMON_DIR", "GIT_NAMESPACE",
    "GIT_AUTHOR_DATE", "GIT_COMMITTER_DATE",
)
LABEL_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{0,63}$")
GITLINK, SYMLINK, EXECUTABLE = "160000", "120000", "100755"
IGNORED_MARK = "ignored-by-git: "  # the line in a checkpoint's message that lists the ignored files it did not save


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


def write_lf(path, text):
    """Write a small text file with '\\n' line endings on every platform."""
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)


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

def git(args, store=None, work_tree=None, cwd=None, index=None, stdin=None, ok=(0,)):
    """Run one git command; raise Fail on an unexpected exit code."""
    command = ["git", "-c", "core.quotePath=false", "-c", "core.fsmonitor=false"]
    if store is not None:
        command.append("--git-dir=" + str(store))
    if work_tree is not None:
        command.append("--work-tree=" + str(work_tree))
    command += args
    env = {key: value for key, value in os.environ.items() if key not in GIT_ENV_TO_DROP}
    env.update(IDENTITY)
    env["GIT_OPTIONAL_LOCKS"] = "0"  # read-only commands never refresh the project's index
    env["GIT_TERMINAL_PROMPT"] = "0"
    if index is not None:
        env["GIT_INDEX_FILE"] = str(index)
    try:
        done = subprocess.run(command, cwd=None if cwd is None else str(cwd), input=stdin,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)
    except FileNotFoundError:
        raise Fail("git is not installed or not on the PATH")
    if done.returncode not in ok:
        detail = done.stderr.decode("utf-8", "replace").strip() or "exit code %d" % done.returncode
        raise Fail("git %s failed: %s" % (args[0], detail))
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
    """True when the folder is inside a git work tree whose repository does not ignore it."""
    inside = git(["rev-parse", "--is-inside-work-tree"], cwd=project, ok=(0, 128))
    if inside.returncode != 0 or inside.stdout.strip() != b"true":
        return False
    return git(["check-ignore", "-q", "."], cwd=project, ok=(0, 1, 128)).returncode != 0


def prepare_store(project, git_project):
    """Create the store if needed and (re)write the settings that keep snapshots byte-exact."""
    ignore = project / STATE_DIR / ".gitignore"
    if not ignore.exists():
        write_lf(ignore, "*\n")
    store = store_path(project)
    if not (store / "HEAD").exists():
        git(["init", "--bare", "--quiet", str(store)])
    for key, value in (("core.autocrlf", "false"), ("core.safecrlf", "false"), ("core.longpaths", "true")):
        git(["config", key, value], store=store)
    write_lf(store / "info" / "attributes", ATTRIBUTES)
    excludes = ["/" + STATE_DIR + "/"] + ([] if git_project else list(DEFAULT_EXCLUDES))
    write_lf(store / "info" / "exclude", "\n".join(excludes) + "\n")
    return store


def open_store(project):
    if not (store_path(project) / "HEAD").exists():
        raise Fail("no checkpoints yet in %s — create one first" % project)
    return prepare_store(project, is_git_project(project))


# ---------------------------------------------------------------- snapshots

def spelled_on_disk(project, rel, listings):
    """The path as the file system spells it now. On a case-insensitive disk git can report
    the letter case a file had when it was added, not the case it has today."""
    folder = os.fsencode(str(project))
    parts = []
    for part in rel.split(b"/"):
        if folder not in listings:
            try:
                names = os.listdir(folder)
            except OSError:
                names = []
            listings[folder] = (set(names), names)
        exact, names = listings[folder]
        if part not in exact:
            matches = [name for name in names if name.lower() == part.lower()]
            if len(matches) == 1:
                part = matches[0]
        parts.append(part)
        folder = os.path.join(folder, part)
    return b"/".join(parts)


def list_files(project, store, git_project):
    """The files a checkpoint must hold (G1): git's own view of the project, or the store's view."""
    if git_project:
        out = git(["ls-files", "-z", "--cached", "--others", "--exclude-standard"], cwd=project).stdout
    else:
        out = git(["ls-files", "-z", "--others", "--exclude-standard"],
                  store=store, work_tree=project, cwd=project).stdout
    state = STATE_DIR.encode()
    paths, nested, seen, listings = [], [], set(), {}
    for rel in out.split(b"\0"):
        if not rel or rel == state or rel.startswith(state + b"/"):
            continue
        if rel.endswith(b"/"):  # a nested repository: git does not look inside it
            nested.append(rel)
            continue
        if git_project:
            rel = spelled_on_disk(project, rel, listings)
        path = local_path(project, rel)
        if os.path.isdir(path) and not os.path.islink(path) and not os.path.exists(os.path.join(path, ".git")):
            continue  # a tracked file that is now a folder: the folder's files are listed themselves
        if rel not in seen:
            seen.add(rel)
            paths.append(rel)
    return paths, nested


def list_ignored(project, store, git_project):
    """The ignored files and folders (a folder counts once) that checkpoints do not hold (G10)."""
    args = ["ls-files", "-z", "--others", "--ignored", "--exclude-standard", "--directory"]
    if git_project:
        out = git(args, cwd=project).stdout
    else:
        out = git(args, store=store, work_tree=project, cwd=project).stdout
    state = STATE_DIR.encode()
    return sorted(rel for rel in out.split(b"\0")
                  if rel and rel.rstrip(b"/") != state and not rel.startswith(state + b"/"))


def recorded_ignored(store, commit):
    """The ignored entries a checkpoint recorded, or None for a checkpoint that recorded none."""
    message = git(["cat-file", "commit", commit], store=store).stdout.decode("utf-8", "surrogateescape")
    for line in message.splitlines():
        if line.startswith(IGNORED_MARK):
            return [os.fsencode(name) for name in json.loads(line[len(IGNORED_MARK):])]
    return None


def snapshot(project, store, git_project, allow_empty):
    """Write the project's current files into the store; return (tree id, file count, nested repositories)."""
    paths, nested = list_files(project, store, git_project)
    if not paths and not allow_empty:
        raise Fail("found no files to save in %s — check the folder and its ignore rules" % project)
    temp = tempfile.mkdtemp(prefix="v2e-")
    try:
        index = os.path.join(temp, "index")
        if paths:
            git(["update-index", "--add", "--remove", "-z", "--stdin"], store=store, work_tree=project,
                cwd=project, index=index, stdin=b"\0".join(paths) + b"\0")
        tree = git(["write-tree"], store=store, index=index).stdout.strip().decode()
    finally:
        remove_temp(temp)
    return tree, len(paths), nested


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


def save_checkpoint(store, tree, label, ignored):
    """Commit a tree under a new label; a label that exists already is refused (G3)."""
    if label_exists(store, label):
        raise Fail("checkpoint %r already exists — labels are permanent; choose a new one" % label)
    names = json.dumps([os.fsdecode(rel) for rel in ignored])
    message = "vibe-to-engineering checkpoint: %s\n\n%s%s\n" % (label, IGNORED_MARK, names)
    commit = git(["commit-tree", "--no-gpg-sign", "-m", message, tree], store=store).stdout.strip().decode()
    git(["update-ref", REF_PREFIX + label, commit, ""], store=store)  # "": only if the ref does not exist
    return commit


# ---------------------------------------------------------------- commands

def cmd_create(project, args):
    check_label(args.label)
    git_project = is_git_project(project)
    store = prepare_store(project, git_project)
    if label_exists(store, args.label):
        raise Fail("checkpoint %r already exists — labels are permanent; choose a new one" % args.label)
    tree, count, nested = snapshot(project, store, git_project, allow_empty=False)
    commit = save_checkpoint(store, tree, args.label, list_ignored(project, store, git_project))
    for rel in nested:
        warn("nested repository %s is not included — its own git keeps it" % show(rel))
    print("created checkpoint %s: %d files (commit %s)" % (args.label, count, commit[:12]))
    return 0


def cmd_verify(project, args):
    store = open_store(project)
    commit = resolve(store, args.label)
    files = tree_files(store, commit)
    problems = []
    temp = tempfile.mkdtemp(prefix="v2e-verify-")
    try:
        restored = os.path.join(temp, "restored")
        os.mkdir(restored)
        write_files(store, commit, restored)
        for rel, (mode, oid) in files.items():
            path = local_path(restored, rel)
            if mode == SYMLINK and os.path.islink(path):
                data = os.fsencode(os.readlink(path))
            elif mode == SYMLINK and os.name != "nt":
                problems.append(rel)  # should have come back as a link
                continue
            elif os.path.isfile(path) and not os.path.islink(path):
                with open(path, "rb") as handle:
                    data = handle.read()
                if mode != SYMLINK and executable_bit(path) not in (None, mode == EXECUTABLE):
                    problems.append(rel)
                    continue
            else:
                problems.append(rel)
                continue
            if blob_id(data, len(oid)) != oid:
                problems.append(rel)
        found = set()
        for folder, dirs, names in os.walk(restored):
            for name in names + [d for d in dirs if os.path.islink(os.path.join(folder, d))]:
                found.add(os.fsencode(os.path.relpath(os.path.join(folder, name), restored).replace(os.sep, "/")))
        problems += sorted(found - set(files))
    finally:
        remove_temp(temp)
    if problems:
        listed = ", ".join(show(rel) for rel in problems[:20])
        raise Fail("checkpoint %s did not come back identical (%d files): %s" % (args.label, len(problems), listed))
    print("verified %s: all %d files come back byte for byte" % (args.label, len(files)))
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


def missing_ignored(before, after):
    """Ignored entries recorded before that are gone now. git lists a wholly ignored folder once, so an entry
    still counts as there when something inside it is listed, or when a listed folder contains it."""
    if before is None or after is None:
        return []
    folders = [other for other in after if other.endswith(b"/")]
    return [rel for rel in before
            if rel not in after
            and not any(other.startswith(rel.rstrip(b"/") + b"/") for other in after)
            and not any(rel.startswith(folder) for folder in folders)]


def cmd_diff(project, args):
    store = open_store(project)
    old = resolve(store, args.old)
    if args.new:
        new, new_name = resolve(store, args.new), args.new
        ignored_now = recorded_ignored(store, new)
    else:
        git_project = is_git_project(project)
        new = snapshot(project, store, git_project, allow_empty=True)[0]
        new_name = "the current files"
        ignored_now = list_ignored(project, store, git_project)
    limit = ["--"] + args.path if args.path else []
    out = git(["diff-tree", "-r", "-z", "-M", "--name-status", "--no-ext-diff", old, new] + limit, store=store).stdout
    changes = parse_name_status(out)
    gone = [] if args.path else missing_ignored(recorded_ignored(store, old), ignored_now)
    if not changes and not gone:
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
        print("files git ignores that were there at %s and are gone now — checkpoints do not hold them, "
              "so they cannot be restored from here:" % args.old)
        for rel in gone:
            print("  gone  %s" % show(rel))
    if args.patch:
        patch = git(["diff-tree", "-r", "-M", "-p", "--no-ext-diff", "--no-textconv", old, new] + limit,
                    store=store).stdout
        sys.stdout.flush()
        sys.stdout.buffer.write(patch)
        sys.stdout.buffer.flush()
    return 3


def current_files_read_only(project):
    """The files a checkpoint would hold now, found without writing anything in the project (G9)."""
    if is_git_project(project):
        return list_files(project, None, True)[0]
    temp = tempfile.mkdtemp(prefix="v2e-tree-")
    try:
        store = os.path.join(temp, "store.git")
        git(["init", "--bare", "--quiet", store])
        write_lf(os.path.join(store, "info", "exclude"),
                 "\n".join(["/" + STATE_DIR + "/"] + list(DEFAULT_EXCLUDES)) + "\n")
        return list_files(project, store, False)[0]
    finally:
        remove_temp(temp)


def print_tree(title, paths, depth):
    root = {}
    for rel in paths:
        node, parts = root, show(rel).split("/")
        for part in parts[:-1]:
            node = node.setdefault(part + "/", {})
        node[parts[-1]] = None

    def count(node):
        return sum(1 if child is None else count(child) for child in node.values())

    def walk(node, prefix, level):
        names = sorted(node, key=lambda name: (node[name] is None, name.lower()))
        for position, name in enumerate(names):
            last = position == len(names) - 1
            child = node[name]
            line = prefix + ("└── " if last else "├── ") + name
            if child is not None and level >= depth:
                files = count(child)
                print("%s (%d %s)" % (line, files, "file" if files == 1 else "files"))
                continue
            print(line)
            if child is not None:
                walk(child, prefix + ("    " if last else "│   "), level + 1)

    print(title)
    walk(root, "", 1)
    print("\n%d files" % len(paths))


def cmd_tree(project, args):
    if args.label and args.current:
        raise Fail("give a label or --current, not both")
    if args.depth < 1:
        raise Fail("--depth must be 1 or more")
    if args.label:
        store = open_store(project)
        paths = list(tree_files(store, resolve(store, args.label)))
        title = "%s @ %s" % (project.name, args.label)
    else:
        paths = current_files_read_only(project)
        title = "%s (current files)" % project.name
    print_tree(title, paths, args.depth)
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


def cmd_restore(project, args):
    store = open_store(project)
    git_project = is_git_project(project)
    commit = resolve(store, args.label)
    wanted = tree_files(store, commit)
    now_tree = snapshot(project, store, git_project, allow_empty=True)[0]
    now = tree_files(store, now_tree)
    to_delete = sorted(rel for rel in now if rel not in wanted)
    to_write = sorted(rel for rel, entry in wanted.items() if now.get(rel) != entry)
    ignored_now = list_ignored(project, store, git_project)
    gone = missing_ignored(recorded_ignored(store, commit), ignored_now)
    if gone:
        print("warning: files git ignores that were there at %s are gone, and a restore cannot bring them back:"
              % args.label)
        list_some("gone   ", gone)
    if not to_delete and not to_write:
        print("the project already matches %s — nothing to restore" % args.label)
        return 0
    print("restoring %s rewrites %d file(s) and deletes %d file(s) added since then:"
          % (args.label, len(to_write), len(to_delete)))
    list_some("rewrite", to_write)
    list_some("delete ", to_delete)
    if not args.apply:
        print("nothing was changed. Run again with --apply only after the human approves this restore.")
        return 0
    saved = "pre-restore-" + time.strftime("%Y%m%dt%H%M%Sz", time.gmtime())
    save_checkpoint(store, now_tree, saved, ignored_now)
    print("saved the current state as checkpoint %s" % saved)
    stuck = []
    for rel in to_delete:  # delete first: on a case-insensitive disk the old and new name are one file
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
    after = tree_files(store, snapshot(project, store, git_project, allow_empty=True)[0])
    different = sorted(rel for rel in set(after) | set(wanted) if after.get(rel) != wanted.get(rel))
    if stuck or different:
        details = stuck + ["differs: " + show(rel) for rel in different[:20]]
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
    tree = add("tree", "tree view of a checkpoint, or of the current files (writes nothing)")
    tree.add_argument("label", nargs="?")
    tree.add_argument("--current", action="store_true", help="the current files (the default)")
    tree.add_argument("--depth", type=int, default=3, help="folder levels to open (default 3)")
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
