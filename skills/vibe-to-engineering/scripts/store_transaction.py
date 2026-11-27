"""Stage Git writes outside the inspected project and publish a complete checkpoint store.

Git accepts repository paths, not directory descriptors. It works on a private copy.
The process owning the live state handle publishes via exclusive renames. A conflicting
directory is never overwritten. If an interrupted exchange leaves a retired store, its
recovery directory remains in the state folder and subsequent commands refuse to proceed.
"""
import contextlib
import contextvars
import ctypes
import os
from pathlib import Path
import shutil
import stat
import sys
import tempfile

from gitrun import Fail
from trusted_tools import external_temp_root, no_acl

ACTIVE = contextvars.ContextVar("checkpoint_store", default=None)
RETIRED = ".v2e-previous-checkpoints.git"
DIR_FLAGS = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0)


def signature(info):
    return (info.st_dev, info.st_ino, info.st_mode, info.st_size, info.st_mtime_ns, info.st_ctime_ns)


def private_directory(path):
    fd = os.open(path, DIR_FLAGS)
    try:
        info = os.fstat(fd)
        if (info.st_uid != os.geteuid() or info.st_mode & 0o077
                or (sys.platform == "darwin" and not no_acl(fd))):
            raise Fail("checkpoint staging needs a private owner-only directory without an extended ACL")
    finally:
        os.close(fd)


def entry(parent, name):
    try:
        return os.stat(name, dir_fd=parent, follow_symlinks=False)
    except FileNotFoundError:
        return None


def copy_tree(parent, name, destination=None):
    """Inspect pinned entries, optionally copying regular bytes into a fresh private tree."""
    result = {}
    root = os.open(name, DIR_FLAGS, dir_fd=parent)
    try:
        def visit(fd, relative, target):
            before = os.fstat(fd)
            result[relative] = signature(before)
            if target is not None:
                target.mkdir()
            for child in sorted(os.listdir(fd)):
                rel = relative + "/" + child
                info = os.stat(child, dir_fd=fd, follow_symlinks=False)
                path = target / child if target is not None else None
                if rel in ("/commondir", "/objects/info/alternates"):
                    raise Fail("checkpoint store contains a repository redirect: " + rel)
                if stat.S_ISDIR(info.st_mode):
                    with contextlib.ExitStack() as opened:
                        sub = os.open(child, DIR_FLAGS, dir_fd=fd)
                        opened.callback(os.close, sub)
                        if not os.path.samestat(info, os.fstat(sub)):
                            raise Fail("checkpoint store directory changed during inspection")
                        visit(sub, rel, path)
                else:
                    if not stat.S_ISREG(info.st_mode):
                        raise Fail("a link or special file appeared in the checkpoint store")
                    if info.st_nlink != 1 and rel not in ("/config", "/info/attributes", "/info/exclude"):
                        raise Fail("a checkpoint store file has another name (hard link): " + rel)
                    result[rel] = signature(info)
                    if path is not None:
                        with os.fdopen(os.open(child, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK,
                                               dir_fd=fd), "rb") as src:
                            if signature(os.fstat(src.fileno())) != signature(info):
                                raise Fail("checkpoint store file changed before copying")
                            with path.open("xb") as dest:
                                shutil.copyfileobj(src, dest)
                            if signature(os.fstat(src.fileno())) != signature(info):
                                raise Fail("checkpoint store file changed during copying")
                        path.chmod(stat.S_IMODE(info.st_mode))
            if signature(before) != signature(os.fstat(fd)):
                raise Fail("checkpoint store directory changed during inspection")
            if target is not None:
                target.chmod(stat.S_IMODE(before.st_mode))
        visit(root, "", destination)
    finally:
        os.close(root)
    return result


def move_exclusive(source_fd, source, target_fd, target):
    """macOS and Linux provide a no-replace rename for populated directories."""
    lib = ctypes.CDLL(None, use_errno=True)
    if sys.platform == "darwin":
        rename, flag = lib.renameatx_np, 4  # RENAME_EXCL
    else:
        rename, flag = lib.renameat2, 1  # RENAME_NOREPLACE
    if rename(source_fd, os.fsencode(source), target_fd, os.fsencode(target), flag):
        number = ctypes.get_errno()
        raise OSError(number, os.strerror(number))


def same_retired(manifest, current):
    # A rename changes only the root directory's ctime.
    return (manifest[""][:-1] == current[""][:-1] and manifest.keys() == current.keys()
            and all(current[key] == value for key, value in manifest.items() if key))


def open_directory(path):
    """Open every canonical component relative to its pinned parent."""
    result = os.open(path.anchor, DIR_FLAGS)
    try:
        for component in path.parts[1:]:
            child = os.open(component, DIR_FLAGS, dir_fd=result)
            os.close(result)
            result = child
        return result
    except BaseException:
        os.close(result)
        raise


class StoreTransaction:
    def __init__(self, project, live, work, state_fd, project_fd, store_name):
        self.project, self.live, self.work = project, live, work
        self.state_fd, self.project_fd, self.name = state_fd, project_fd, store_name
        self.preserve_work = False
        self.published = False
        self.sidecars = {}
        for name in (".gitignore", "fingerprint.key"):
            info = entry(state_fd, name)
            self.sidecars[name] = signature(info) if info else None
        self.manifest = None
        if entry(state_fd, store_name):
            self.manifest = copy_tree(state_fd, store_name, work / store_name)

    def assert_owned(self):
        state = entry(self.project_fd, self.live.name)
        if (state is None or not os.path.samestat(state, os.fstat(self.state_fd))
                or not os.path.samestat(self.project.stat(), os.fstat(self.project_fd))):
            raise Fail("checkpoint state directory changed; the staged store was not published")

    def publish(self):
        self.assert_owned()
        current = entry(self.state_fd, self.name)
        if (current is None) != (self.manifest is None):
            raise Fail("checkpoint store was replaced during preparation")
        if current and copy_tree(self.state_fd, self.name) != self.manifest:
            raise Fail("checkpoint store changed during preparation")
        candidate = self.work / "complete.git"
        shutil.copytree(self.work / self.name, candidate)
        candidate.chmod(candidate.stat().st_mode & 0o700)
        private_directory(candidate)
        from_fd = os.open(self.work, DIR_FLAGS)
        undo = []

        def move(src_fd, src, dst_fd, dst):
            moved = os.stat(src, dir_fd=src_fd, follow_symlinks=False)
            move_exclusive(src_fd, src, dst_fd, dst)
            observed = os.stat(dst, dir_fd=dst_fd, follow_symlinks=False)
            undo.append((dst_fd, dst, src_fd, src, observed))
            if not os.path.samestat(moved, observed):
                raise Fail("checkpoint destination changed during exclusive publication")

        try:
            self.assert_owned()
            for name, initial in self.sidecars.items():
                info = entry(self.state_fd, name)
                if (signature(info) if info else None) != initial:
                    raise Fail("checkpoint key or ignore file changed during preparation")
            if current:
                move(self.state_fd, self.name, self.state_fd, RETIRED)
                if not same_retired(self.manifest, copy_tree(self.state_fd, RETIRED)):
                    raise Fail("another checkpoint store occupied the destination during publication")
            for name, initial in self.sidecars.items():
                if initial is None and entry(from_fd, name):
                    self.assert_owned()
                    move(from_fd, name, self.state_fd, name)
            self.assert_owned()
            move(from_fd, candidate.name, self.state_fd, self.name)
            self.assert_owned()
            if current:
                move(self.state_fd, RETIRED, from_fd, "retired.git")
                if not same_retired(self.manifest, copy_tree(from_fd, "retired.git")):
                    raise Fail("checkpoint recovery directory changed during publication")
            self.assert_owned()
            self.published = True
        except BaseException:
            # Unwind through the originally opened directories, even if a new
            # state directory now occupies the visible project name. Each destination
            # must still be empty. Preserve both generations on a competing move.
            try:
                for src_fd, src, dst_fd, dst, identity in reversed(undo):
                    current = entry(src_fd, src)
                    if current is None or not os.path.samestat(current, identity):
                        raise Fail("checkpoint recovery entry changed identity")
                    move_exclusive(src_fd, src, dst_fd, dst)
                    if not os.path.samestat(identity, os.stat(dst, dir_fd=dst_fd, follow_symlinks=False)):
                        raise Fail("checkpoint recovery entry changed during rollback")
            except (OSError, Fail) as error:
                self.preserve_work = True
                raise Fail("concurrent checkpoint publication interrupted recovery; preserve the state "
                           "directory and " + str(self.work)) from error
            raise
        finally:
            os.close(from_fd)



@contextlib.contextmanager
def transaction(project, state_name, store_name, create, check_state):
    import fcntl
    live = project / state_name
    check_state(project)
    with contextlib.ExitStack() as opened:
        project_fd = open_directory(project)
        opened.callback(os.close, project_fd)
        if not entry(project_fd, state_name):
            if not create:
                raise Fail("no checkpoints yet in %s — create one first" % project)
            try:
                os.mkdir(state_name, 0o700, dir_fd=project_fd)
            except FileExistsError:
                raise Fail("checkpoint state appeared during preparation; retry")
        state_fd = os.open(state_name, DIR_FLAGS, dir_fd=project_fd)
        opened.callback(os.close, state_fd)
        try:
            fcntl.flock(state_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise Fail("checkpoint store is busy; retry when the other operation finishes")
        if entry(state_fd, RETIRED):
            raise Fail("checkpoint publication needs recovery: preserve " + RETIRED + " and the current store")
        work = Path(tempfile.mkdtemp(prefix="v2e-checkpoints-", dir=external_temp_root(project)))
        tx = None
        def cleanup():
            if tx and tx.preserve_work:
                print("checkpoint recovery files retained at " + str(work), file=sys.stderr)
            else:
                shutil.rmtree(work)
        opened.callback(cleanup)
        private_directory(work)
        if work.stat().st_dev != os.fstat(state_fd).st_dev:
            raise Fail("checkpoint staging needs an external temporary folder on the project's volume")
        tx = StoreTransaction(project, live, work, state_fd, project_fd, store_name)
        tx.assert_owned()
        check_state(project)
        token = ACTIVE.set(tx)
        opened.callback(ACTIVE.reset, token)
        yield tx
