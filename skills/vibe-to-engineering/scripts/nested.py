"""Nested repositories — folders with their own git inside the project (G1).

A checkpoint does not save them: their own git keeps their committed work. So a checkpoint is refused while one
holds work its commits do not, and the check asks git only for lists — never to read a file, which would run a
filter program the git settings name (G11).
"""

import os
import re
import stat
from pathlib import Path
from gitrun import (EXECUTABLE, Fail, GITLINK, SYMLINK, blob_id, executable_bit,
    file_id, git, git_version, local_path, promisor_configured, show)

INDEX_ENTRY = re.compile(  # one entry of `git ls-files -z -s -v --debug`: tag, mode, id, stage, path, recorded stat data
    rb"([A-Za-z]) (\d{6}) ([0-9a-f]{40}|[0-9a-f]{64}) ([0-3])\t([^\0]*)\0"
    rb"  ctime: (\d+):(\d+)\n  mtime: (\d+):(\d+)\n  dev: (\d+)\tino: (\d+)\n  uid: (\d+)\tgid: (\d+)\n"
    rb"  size: (\d+)\tflags: [0-9a-f]+\n")


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
    if git_version() < (2, 46) and promisor_configured(folder):
        raise Fail("%s is a partial clone, and a git older than 2.46 fetches its missing objects from a remote the "
                   "moment they are read — which may run a configured program" % name)
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
    symlinks = git(["config", "--bool", "core.symlinks"], cwd=folder, ok=(0, 1)).stdout.strip() != b"false"
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
            if stat.S_ISLNK(info.st_mode):
                same = blob_id(os.fsencode(os.readlink(path)), len(oid)) == oid
            else:  # a plain file where a link was is a change — unless this repository keeps links as plain files
                same = not symlinks and stat.S_ISREG(info.st_mode) and file_id(path, len(oid)) == oid
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


def repositories(found):
    """Every nested repository a survey found: tracked and untracked ones (its nested list) and ignored ones, which git
    lists among the ignored entries as one "x/" entry wherever they are (F06). An ignored one stays on the ignored list
    only, as the store format has always recorded it, so every implementation reads a checkpoint the same way."""
    return sorted(set(found.nested) | {rel for rel in found.ignored if rel.endswith(b"/")})


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
