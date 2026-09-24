"""Shared by the checkpoint tool's tests: throwaway projects of every shape, the tool run the way an agent
runs it (a separate process, or in-process with one step wrapped), and deliberately hostile git settings, so a pass
also shows the tool does not depend on the user's own git configuration.

To test another implementation of the contract, point V2E_CHECKPOINT at it. Run the tests through discovery
(`python3 -m unittest discover -s tests`, one file with `-p test_nested.py`), which puts this module on the path.
"""

import contextlib
import hashlib
import importlib.util
import io
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
import zlib
from pathlib import Path
from unittest import mock



ROOT = Path(__file__).resolve().parents[1]
TOOL = Path(os.environ.get("V2E_CHECKPOINT", ROOT / "skills" / "vibe-to-engineering" / "scripts" / "checkpoint.py"))
STATE = ".vibe-to-engineering"
HOSTILE_GITCONFIG = """\
[user]
\tname = Fixture Author
\temail = fixture@example.invalid
[core]
\tautocrlf = true
[commit]
\tgpgsign = true
[gpg]
\tprogram = /nonexistent/gpg
[init]
\tdefaultBranch = main
"""


def write(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def disk_state(root, skip=(".git", STATE)):
    """Every file and link under root: path -> ("link", target) or ("file", executable, bytes)."""
    state = {}
    for folder, dirs, names in os.walk(root):
        rel_folder = os.path.relpath(folder, root)
        if rel_folder == ".":
            dirs[:] = [d for d in dirs if d not in skip]
        for name in names + [d for d in dirs if os.path.islink(os.path.join(folder, d))]:
            path = os.path.join(folder, name)
            rel = os.path.normpath(os.path.join(rel_folder, name)).replace(os.sep, "/")
            if os.path.islink(path):
                state[rel] = ("link", os.readlink(path))
            else:
                state[rel] = ("file", bool(os.stat(path).st_mode & 0o111), Path(path).read_bytes())
    return state


def folder_digest(root):
    """One hash over every name and byte under root — proves a folder was not touched."""
    digest = hashlib.sha256()
    for folder, dirs, names in sorted(os.walk(root)):
        dirs.sort()
        for name in sorted(names):
            path = os.path.join(folder, name)
            digest.update(os.path.relpath(path, root).encode())
            if not os.path.islink(path):
                digest.update(Path(path).read_bytes())
    return digest.hexdigest()


def identities(root):
    """Every name under root, root included, with its inode, modification time and bytes — proves nothing under it was
    written, replaced, created or removed, not even with the same bytes."""
    found = {}
    for folder, dirs, names in os.walk(root):
        for path in [folder] + [os.path.join(folder, name) for name in names]:
            info = os.lstat(path)
            found[os.path.relpath(path, root)] = (info.st_ino, info.st_mtime_ns,
                                                  Path(path).read_bytes() if stat.S_ISREG(info.st_mode) else None)
    return found


def case_insensitive_disk(folder):
    probe = Path(folder) / "CaseProbe"
    probe.write_text("x")
    try:
        return (Path(folder) / "caseprobe").exists()
    finally:
        probe.unlink()


class Fixture(unittest.TestCase):
    """A test with a temporary folder, isolated git settings and the helpers below."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="v2e-test-")).resolve()
        self.home = self.tmp / "home"
        self.home.mkdir()
        (self.home / "gitconfig").write_text(HOSTILE_GITCONFIG)
        self.env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
        self.env.update({"HOME": str(self.home), "GIT_CONFIG_GLOBAL": str(self.home / "gitconfig"),
                         "GIT_CONFIG_NOSYSTEM": "1", "USERPROFILE": str(self.home)})

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    # ------------------------------------------------------------ helpers

    def git(self, cwd, *args):
        return subprocess.run(["git", "-c", "commit.gpgsign=false", *args], cwd=str(cwd), env=self.env,
                              check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE).stdout.decode()

    def tool(self, project, *args, expect=0, env=None):
        done = subprocess.run([sys.executable, str(TOOL), "--project", str(project), *args], env=dict(self.env, **(env or {})),
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out, err = done.stdout.decode("utf-8", "replace"), done.stderr.decode("utf-8", "replace")
        if expect is not None:
            self.assertEqual(done.returncode, expect, "exit %d\n%s\n%s" % (done.returncode, out, err))
        return out, err

    def git_project(self, name="project"):
        """A repository holding every kind of file and every kind of uncommitted work."""
        p = self.tmp / name
        p.mkdir()
        self.git(p, "init", "-q")
        write(p / ".gitignore", b"node_modules/\n.env\n")
        write(p / ".gitattributes", b"* text=auto eol=crlf\n")
        write(p / "src" / "app.js", b"console.log('app');\n")
        write(p / "src" / "util.js", b"export const x = 1;\n")
        write(p / "windows.txt", b"one\r\ntwo\r\n")
        write(p / "unix.txt", b"one\ntwo\n")
        write(p / "run.sh", b"#!/bin/sh\necho hi\n")
        os.chmod(p / "run.sh", 0o755)
        os.symlink("src/app.js", str(p / "link.js"))
        write(p / "docs" / "Read Me ü.md", b"# read me\n")
        self.git(p, "add", "-A")
        self.git(p, "commit", "-qm", "first")
        write(p / "src" / "util.js", b"export const x = 2;\n")      # changed, not staged
        write(p / "staged.txt", b"staged\n")
        self.git(p, "add", "staged.txt")                              # staged, not committed
        write(p / "untracked.txt", b"new\n")                          # untracked
        write(p / ".env", b"SECRET=1\n")                              # ignored
        write(p / "node_modules" / "pkg" / "index.js", b"module.exports = 1;\n")  # ignored
        return p

    def plain_project(self, name="plain"):
        """A folder with no git at all."""
        p = self.tmp / name
        write(p / "main.py", b"print('hi')\n")
        write(p / "lib" / "calc.py", b"def add(a, b):\n    return a + b\n")
        write(p / "data" / "notes.txt", b"one\r\ntwo\r\n")
        write(p / ".gitignore", b"*.log\n")
        write(p / "debug.log", b"noise\n")
        write(p / "node_modules" / "dep" / "index.js", b"x\n")
        write(p / "__pycache__" / "main.cpython-39.pyc", b"\x00\x01")
        return p

    def without(self, state, *prefixes):
        return {k: v for k, v in state.items() if not any(k == p or k.startswith(p + "/") for p in prefixes)}

    def store(self, project):
        return project / STATE / "checkpoints.git"

    def store_git(self, project, *args, data=None):
        done = subprocess.run(["git", "--git-dir=" + str(self.store(project)), *args], env=self.env, input=data,
                              check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return done.stdout.decode().strip()

    def damage(self, project, label, path, data=None):
        """Delete the stored copy of `path` in checkpoint `label`, or replace its bytes with `data` under the same id."""
        oid = self.store_git(project, "rev-parse", "refs/checkpoints/%s:%s" % (label, path))
        obj = self.store(project) / "objects" / oid[:2] / oid[2:]
        os.chmod(obj, stat.S_IWRITE | stat.S_IREAD)
        if data is None:
            obj.unlink()
        else:
            obj.write_bytes(zlib.compress(b"blob %d\0" % len(data) + data))

    def in_process(self, project, argv, inject):
        """Run the tool inside this process after `inject(tool)` has wrapped one of its steps — to change the project
        at the one moment a safety check exists for — and return the exit code and the error output."""
        spec = importlib.util.spec_from_file_location("checkpoint_under_test", str(TOOL))
        tool = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(tool)
        inject(tool)
        err = io.StringIO()
        with mock.patch.dict(os.environ, self.env, clear=True), contextlib.redirect_stderr(err), \
                contextlib.redirect_stdout(io.StringIO()):
            code = tool.main(["--project", str(project)] + list(argv))
        return code, err.getvalue()

    def repository(self, folder, files):
        """A git repository in `folder` whose one commit holds `files` (name -> bytes)."""
        for name, data in files.items():
            write(folder / name, data)
        self.git(folder, "init", "-q")
        self.git(folder, "add", *files)
        self.git(folder, "commit", "-qm", "committed")
        return folder

    def plant(self, project, label, files):
        """Save by hand a checkpoint holding `files` (name -> bytes), the way a store from another disk could hold it."""
        rows = ["100644 blob %s\t%s" % (self.store_git(project, "hash-object", "-w", "--stdin", data=data), name)
                for name, data in files.items()]
        tree = self.store_git(project, "mktree", data=("\n".join(rows) + "\n").encode())
        commit = self.store_git(project, "commit-tree", "-m", "vibe-to-engineering checkpoint: " + label, tree)
        self.store_git(project, "update-ref", "refs/checkpoints/" + label, commit)

    # ------------------------------------------------------------ G11 no hook runs, no git setting bends a checkpoint (F03)

    def hostile_git(self, p):
        """Hooks for the events checkpoint commands could fire — configured globally, through the environment and as
        templates for new repositories — plus environment settings that would redirect git's own writes."""
        marker, hooks = self.tmp / "hook-ran.txt", self.tmp / "hooks"
        hooks.mkdir()
        for name in ("reference-transaction", "post-index-change", "post-checkout", "pre-commit", "post-commit",
                     "pre-auto-gc", "post-rewrite", "fsmonitor-watchman"):
            (hooks / name).write_text("#!/bin/sh\necho %s >> '%s'\n" % (name, marker))
            os.chmod(hooks / name, 0o755)
        shutil.copytree(str(hooks), str(self.tmp / "templates" / "hooks"))
        with open(self.home / "gitconfig", "a") as config:
            config.write("[core]\n\thooksPath = %s\n\tfsmonitor = %s\n[init]\n\ttemplateDir = %s\n"
                         % (hooks, hooks / "fsmonitor-watchman", self.tmp / "templates"))
        env = {"GIT_CONFIG_COUNT": "1", "GIT_CONFIG_KEY_0": "core.hooksPath", "GIT_CONFIG_VALUE_0": str(hooks),
               "GIT_CONFIG": str(p / "unix.txt"), "GIT_TRACE": str(p / "trace.txt"),
               "GIT_TRACE2_EVENT": str(p / "trace2.txt")}
        return marker, env
