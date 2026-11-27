"""Executable selection for the bundled inspection and printing tools."""

import ctypes
import errno
import os
import sys
from pathlib import Path


def inside_project(path, project):
    """Check folder identities too: differently cased paths can be the same Mac folder."""
    root = Path(project).resolve()
    for folder in (path, *path.parents):
        if folder == root or (folder.exists() and folder.samefile(root)):
            return True
    return False


def external_executable(name, project):
    """Return the absolute executable actually selected, or refuse this candidate."""
    path = Path(name)
    if not path.is_absolute() or not path.is_file() or not os.access(path, os.X_OK):
        return None
    resolved = path.resolve(strict=True)
    if inside_project(path, project) or inside_project(resolved, project):
        return None
    return str(resolved)


def external_temp_root(project):
    """Choose an existing outside directory without probing candidate paths by writing to them."""
    choices = [os.environ.get(key) for key in ("TMPDIR", "TEMP", "TMP")]
    if os.name != "nt":
        choices.append("/tmp")
    for choice in choices:
        if choice and Path(choice).is_absolute():
            candidate = Path(choice).resolve()
            if candidate.is_dir() and not inside_project(candidate, project):
                return candidate
    raise ValueError("no temporary directory outside the inspected project")


def tool_environment(project):
    """Children and their helpers get system search folders and no executable redirects."""
    if os.name == "nt":  # Portable test logic only; execution on Windows is gated.
        folders = (Path(os.environ["SystemRoot"]) / "System32",)
    else:
        folders = tuple(map(Path, ("/usr/bin", "/bin", "/usr/sbin", "/sbin")))
    env = {key: value for key, value in os.environ.items()
           if key not in ("DEVELOPER_DIR", "TOOLCHAINS", "SDKROOT", "GIT_EXEC_PATH", "ENV", "BASH_ENV")
           and not key.startswith(("DYLD_", "LD_", "BASH_FUNC_"))}
    dirs = [str(folder) for folder in folders if folder.is_absolute() and folder.is_dir()
            and not inside_project(folder.resolve(), project)]
    if not dirs:
        raise ValueError("no system helper directory outside the inspected project")
    env["PATH"] = os.pathsep.join(dirs)
    return env


def no_acl(fd):
    """Prove absence of a Darwin extended ACL on the open file or directory."""
    if sys.platform != "darwin":
        return False
    try:
        libc = ctypes.CDLL(None, use_errno=True)
        libc.acl_get_fd.argtypes, libc.acl_get_fd.restype = [ctypes.c_int], ctypes.c_void_p
        libc.acl_free.argtypes, libc.acl_free.restype = [ctypes.c_void_p], ctypes.c_int
    except (AttributeError, OSError):
        return False
    ctypes.set_errno(0)
    acl = libc.acl_get_fd(fd)
    if acl:
        libc.acl_free(acl)
        return False
    # On a valid descriptor acl_get_fd reports no extended ACL as NULL/ENOENT.
    return ctypes.get_errno() == errno.ENOENT
