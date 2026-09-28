"""Shared runner-enrollment fixture for the evidence.py tests (A2, R2-F5): an isolated per-process HOME whose
~/.vibe-to-engineering/runners.json enrolls the runners the suite's checks use — the interpreter running the
tests (the python kind) and /bin/sh — so no test ever touches the real per-user registry, and the enrollment
gate is satisfied the same deliberate way a user's is: disclosure shown, the approval word given, the one
disclosed probe run (once per runner per test process).

A test runs the tool with environ() as the subprocess environment, or HOME=str(enrolled_home()) inside one.
When V2E_EVIDENCE points at another candidate, that candidate's evidence.py supplies the enrollment API, so the
fixture always enrolls the runners the tool under test will validate against.
"""

import atexit
import os
import shutil
import sys
import tempfile
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
TOOL = Path(os.environ.get("V2E_EVIDENCE", ROOT / "skills" / "vibe-to-engineering" / "scripts" / "evidence.py"))
sys.path.insert(0, str(TOOL.parent))
import evidence  # noqa: E402

_HOME = None


def enrolled_home():
    """The one isolated HOME for this test process, the suite's runners enrolled into it on first use."""
    global _HOME
    if _HOME is None:
        home = Path(tempfile.mkdtemp(prefix="v2e-enrolled-home-")).resolve()
        with mock.patch.dict(os.environ, {"HOME": str(home)}):
            for program in (os.path.realpath(sys.executable), os.path.realpath("/bin/sh")):
                with open(os.devnull, "w") as quiet:
                    evidence.enroll_runner(program, ask=lambda prompt: evidence.APPROVAL, out=quiet)
        atexit.register(shutil.rmtree, str(home), True)
        _HOME = home
    return _HOME


def environ(base=None, **extra):
    """A subprocess environment for running the tool: base (default: this process's own) with HOME pointed at
    the enrolled home, plus any extras."""
    env = dict(os.environ if base is None else base)
    env["HOME"] = str(enrolled_home())
    env.update(extra)
    return env
