#!/usr/bin/python3 -I
"""Publish plan records and check baseline approval inside the project's locked state directory."""
import argparse
import ctypes
import os
from pathlib import Path
import stat
import sys
import uuid

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
from checkpoint import STATE_DIR, require_untracked_state, resolve_project
from gitrun import Fail, git
from platformgate import PlatformRefusal, require_supported_platform
from render_map import LEDGER, MAP_DATA, PLAN, PlanEntries, project_directory_fd
from store_transaction import entry, move_exclusive
from trusted_tools import no_acl

TARGETS = {"plan": PLAN, "append-ledger": LEDGER, "map-data": MAP_DATA}


def snapshot(directory, name):
    info = entry(directory, name)
    if info is None:
        return None, None
    if (not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_uid != os.geteuid()
            or info.st_mode & 0o022):
        raise Fail("state record must be a single, owner-controlled regular file: " + name)
    with os.fdopen(os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory), "rb") as src:
        if not no_acl(src.fileno()):
            raise Fail("cannot establish exclusive access to state record: " + name)
        if not os.path.samestat(os.fstat(src.fileno()), info):
            raise Fail("state record changed while opening: " + name)
        data = src.read()
        if stamp(os.fstat(src.fileno())) != stamp(info):
            raise Fail("state record changed while reading: " + name)
    return info, data


def stamp(info):
    return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns)


def check_folder(project, parent, directory):
    info = entry(parent, STATE_DIR)
    owner = os.fstat(parent)
    if (info is None or not os.path.samestat(info, os.fstat(directory))
            or not os.path.samestat(os.stat(project, follow_symlinks=False), owner)
            or owner.st_uid != os.geteuid() or owner.st_mode & 0o022 or not no_acl(parent)
            or not no_acl(directory)
            or info.st_uid != os.geteuid() or info.st_mode & 0o022):
        raise Fail("the state directory changed or is not owner-controlled")


def exchange(directory, first, second):
    # A replace would discard an intervening file. Exchange retains the actual
    # occupant until we have verified it and still hold the named directory.
    lib = ctypes.CDLL(None, use_errno=True)
    rename = lib.renameatx_np if sys.platform == "darwin" else lib.renameat2
    if rename(directory, os.fsencode(first), directory, os.fsencode(second), 2):
        number = ctypes.get_errno()
        raise OSError(number, os.strerror(number))


def publish(project, parent, directory, proposals, ignore=None):
    staged, cleanup, installed = {}, {}, []
    try:
        for name, (_, data) in proposals.items():
            temp = ".v2e-plan-" + uuid.uuid4().hex
            fd = os.open(temp, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600, dir_fd=directory)
            staged[name] = temp
            with os.fdopen(fd, "wb") as dest:
                cleanup[temp] = os.fstat(fd)
                dest.write(data)
                dest.flush()
                os.fsync(dest.fileno())
        for name, (before, _) in proposals.items():
            check_folder(project, parent, directory)
            if ignore is not None:
                check_record(directory, ".gitignore", ignore)
            now = entry(directory, name)
            if (before is None) != (now is None) or (now and stamp(before) != stamp(now)):
                raise Fail("state record changed before publication: " + name)
            temp = staged[name]
            new = entry(directory, temp)
            if before is None:
                move_exclusive(directory, temp, directory, name)
            else:
                exchange(directory, temp, name)
            installed.append((name, before, new))
            cleanup.pop(temp)
            if before is not None:
                old = entry(directory, temp)
                if (not os.path.samestat(old, before) or old.st_nlink != 1
                        or old.st_mtime_ns != before.st_mtime_ns or old.st_size != before.st_size):
                    raise Fail("state record changed at publication: " + name)
                cleanup[temp] = old
            check_folder(project, parent, directory)
        if ignore is not None:
            check_record(directory, ".gitignore", ignore)
    except BaseException:
        for name, before, new in reversed(installed):
            temp = staged[name]
            current = entry(directory, name)
            if current is None or not os.path.samestat(current, new):
                cleanup.clear()
                raise Fail("state changed during rollback; preserve the current entry and " + temp)
            cleanup.pop(temp, None)
            if before is None:
                move_exclusive(directory, name, directory, temp)
            else:
                exchange(directory, temp, name)
            cleanup[temp] = new
        raise
    finally:
        for temp, owned in cleanup.items():
            now = entry(directory, temp)
            if now is not None and os.path.samestat(now, owned):
                os.unlink(temp, dir_fd=directory)


def check_record(directory, name, original):
    now = entry(directory, name)
    if now is None or stamp(now) != stamp(original):
        raise Fail("state record changed: " + name)


def run(project, operation, data=None):
    import fcntl
    if operation != "check-approval":
        require_untracked_state(project)
    with project_directory_fd(project, ()) as parent:
        owner = os.fstat(parent)
        if owner.st_uid != os.geteuid() or owner.st_mode & 0o022 or not no_acl(parent):
            raise Fail("the project directory must be owner-controlled for state publication")
        if entry(parent, STATE_DIR) is None and operation != "check-approval":
            try:
                os.mkdir(STATE_DIR, 0o700, dir_fd=parent)
            except FileExistsError:
                raise Fail("the state directory appeared during preparation; retry")
        with project_directory_fd(project, (STATE_DIR,)) as directory:
            try:
                fcntl.flock(directory, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                raise Fail("the state directory is busy; retry after the current operation finishes")
            check_folder(project, parent, directory)
            if operation == "check-approval":
                from mapledger import current_approval
                plan_info, plan = snapshot(directory, PLAN)
                ledger_info, ledger = snapshot(directory, LEDGER)
                if plan is None or ledger is None:
                    raise Fail("the plan and its approval record are required")
                versions = PlanEntries(plan.decode("utf-8")).versions
                if len(versions) != 1:
                    raise Fail("the plan must show one version")
                fingerprint = git(["hash-object", "--no-filters", "--stdin"], cwd=project,
                                  stdin=plan).stdout.decode("ascii").strip()
                _, events, _, _, approved, _ = current_approval(
                    ledger.decode("utf-8"), versions.pop(), fingerprint, require_open=True)
                if (events[approved][2] != "DISPOSABLE FIXTURE CONFIRMED"
                        and not any(event == "DISPOSABLE FIXTURE CONFIRMED"
                                    for _, event, _ in events[approved + 1:])):
                    raise Fail("PLAN ONLY: record the owner's confirmation of a disposable project "
                               "with synthetic secrets before creating the baseline")
                check_folder(project, parent, directory)
                for name, info in ((PLAN, plan_info), (LEDGER, ledger_info)):
                    check_record(directory, name, info)
                return
            name = TARGETS[operation]
            existing, old = snapshot(directory, name)
            ignore, contents = snapshot(directory, ".gitignore")
            if contents not in (None, b"*\n", b"*"):
                raise Fail("the state .gitignore must contain the single line *")
            proposals = {} if ignore else {".gitignore": (None, b"*\n")}
            if operation == "append-ledger":
                if old and not old.endswith(b"\n"):
                    old += b"\n"
                data = (old or b"") + data
            proposals[name] = (existing, data)
            publish(project, parent, directory, proposals, ignore)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", required=True)
    parser.add_argument("operation", choices=(*TARGETS, "check-approval"))
    args = parser.parse_args()
    try:
        require_supported_platform()
        data = None
        if args.operation != "check-approval":
            data = sys.stdin.buffer.read()
            if not data:
                raise Fail("supply the complete new record on standard input")
            data.decode("utf-8")
        run(resolve_project(args.project), args.operation, data)
    except (Fail, PlatformRefusal, OSError, ValueError) as error:
        print("planstate.py: " + str(error), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
