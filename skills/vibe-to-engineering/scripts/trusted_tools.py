"""Executable selection for the bundled inspection and printing tools."""

import os
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
