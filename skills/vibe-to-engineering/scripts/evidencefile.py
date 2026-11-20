"""Keep an evidence destination tied to the directory chain admitted before launch.

The check is not sandboxed. After it returns, refuse replaced ancestors and links;
write relative to directory descriptors opened without following links. This does
not claim to prevent a separate process from concurrently moving open directories.
"""
import errno
import os
from pathlib import Path
import secrets
import stat

from gitrun import Fail


def identity(info):
    return info.st_dev, info.st_ino


class Destination:
    def __init__(self, project, path):
        self.path = Path(path)
        if Path(project) not in self.path.parents:
            raise Fail("the evidence destination is outside the project")
        self.directories = list(reversed(self.path.parent.parents)) + [self.path.parent]
        self.expected = {}
        missing = False
        for directory in self.directories:
            if missing:
                continue
            try:
                info = directory.lstat()
            except FileNotFoundError:
                missing = True
                continue
            if not stat.S_ISDIR(info.st_mode):
                raise Fail("evidence parent is a link or not a directory: %s" % directory)
            self.expected[directory] = identity(info)
        try:
            existing = self.path.lstat()
        except FileNotFoundError:
            existing = None
        if existing is not None and not stat.S_ISREG(existing.st_mode):
            raise Fail("the evidence output is a link or nonregular file: %s" % self.path)

    def __str__(self):
        return str(self.path)

    def open_parent(self):
        """Revalidate admitted identities, safely creating only missing descendants."""
        flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
        descriptor = os.open(str(self.directories[0]), flags)
        try:
            if identity(os.fstat(descriptor)) != self.expected[self.directories[0]]:
                raise Fail("the evidence directory chain changed after admission")
            for directory in self.directories[1:]:
                try:
                    child = os.open(directory.name, flags, dir_fd=descriptor)
                except FileNotFoundError:
                    if directory in self.expected:
                        raise Fail("evidence parent disappeared after admission: %s" % directory)
                    try:
                        os.mkdir(directory.name, mode=0o700, dir_fd=descriptor)
                    except FileExistsError:
                        pass
                    child = os.open(directory.name, flags, dir_fd=descriptor)
                expected = self.expected.get(directory)
                if expected is not None and identity(os.fstat(child)) != expected:
                    os.close(child)
                    raise Fail("evidence parent changed after admission: %s" % directory)
                os.close(descriptor)
                descriptor = child
            return descriptor
        except OSError as error:
            os.close(descriptor)
            if error.errno in (errno.ELOOP, errno.ENOTDIR, errno.ENOENT):
                raise Fail("the evidence directory chain changed or contains a link") from error
            raise
        except BaseException:
            os.close(descriptor)
            raise


def write_lf(destination, text):
    """Atomically replace evidence without resolving parent paths during the write."""
    descriptor = destination.open_parent()
    temporary = None
    try:
        try:
            existing = os.stat(destination.path.name, dir_fd=descriptor, follow_symlinks=False)
        except FileNotFoundError:
            existing = None
        if existing is not None and not stat.S_ISREG(existing.st_mode):
            raise Fail("the evidence output became a link or nonregular file")
        candidate = ".v2e-evidence-" + secrets.token_hex(16)
        output = os.open(candidate, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                         0o600, dir_fd=descriptor)
        temporary = candidate  # cleanup owns the entry only after exclusive creation succeeds
        with os.fdopen(output, "wb") as stream:
            stream.write(text.encode("utf-8"))
        os.replace(temporary, destination.path.name, src_dir_fd=descriptor, dst_dir_fd=descriptor)
        temporary = None
    finally:
        if temporary is not None:
            os.unlink(temporary, dir_fd=descriptor)
        os.close(descriptor)
