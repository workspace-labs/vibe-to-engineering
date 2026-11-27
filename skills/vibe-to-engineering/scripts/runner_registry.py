"""Admission and atomic updates of the local user's enrollment registry (macOS runtime)."""
import json
import os
import stat

from evidencefile import Destination, identity, literal_path, write_lf
from gitrun import Fail
from trusted_tools import no_acl


class RunnerRegistry:
    def __init__(self, path):
        self.path = literal_path(path)
        self.folder = self.path.parent
        home = self.folder.parent
        self.destination = Destination(home, self.path, kind="runner registry")
        if home not in self.destination.expected:
            raise Fail("the runner registry requires an existing home directory")
        self.check_owner(home.lstat(), "home directory")

    @staticmethod
    def check_owner(info, name):
        if info.st_uid != os.geteuid() or info.st_mode & 0o022:
            raise Fail("the runner registry %s must belong to the current user and disallow other writers" % name)

    @classmethod
    def check_private(cls, fd, name):
        info = os.fstat(fd)
        cls.check_owner(info, name)
        if not no_acl(fd):
            raise Fail("the runner registry %s must have a verified absence of extended ACLs" % name)
        return info

    def open_folder(self):
        descriptor = self.destination.open_parent()
        try:
            info = self.check_private(descriptor, "directory")
            self.destination.expected[self.folder] = identity(info)
            return descriptor
        except BaseException:
            os.close(descriptor)
            raise

    def read_at(self, directory):
        try:
            fd = os.open(self.path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory)
        except FileNotFoundError:
            self.destination.expected_file = None
            return None
        except OSError as error:
            raise Fail("cannot open the runner registry without following links") from error
        with os.fdopen(fd, "rb") as stream:
            info = self.check_private(fd, "file")
            if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
                raise Fail("the runner registry must be a regular file with one name")
            self.destination.expected_file = identity(info)
            try:
                record = json.loads(stream.read().decode("utf-8"))
            except (UnicodeError, ValueError):
                record = None
        if (not isinstance(record, dict) or type(record.get("version")) is not int or record["version"] != 1
                or not isinstance(record.get("runners"), dict)):
            raise Fail("the runner registry %s is malformed — repair it or re-enroll the runner manually "
                       "(python3 evidence.py --enroll-runner <runner>); the check is refused before execution"
                       % self.path)
        return record

    def read(self):
        if self.folder not in self.destination.expected:
            return None   # no registry folder yet; disclosure must not create one
        directory = self.open_folder()
        try:
            return self.read_at(directory)
        finally:
            os.close(directory)

    def save(self, kind, entry):
        import fcntl   # native enrollment runs only on macOS
        directory = self.open_folder()
        try:
            fcntl.flock(directory, fcntl.LOCK_EX)
            current = self.read_at(directory) or {"version": 1, "runners": {}}
            current["runners"][kind] = entry
            # Reopen the admitted chain before the chmod; both the mode change and all writes
            # target the verified directory. write_lf revalidates again before publication.
            verified = self.open_folder()
            try:
                os.fchmod(verified, 0o700)
            finally:
                os.close(verified)
            write_lf(self.destination, json.dumps(current, indent=2, sort_keys=True) + "\n")
        finally:
            os.close(directory)
