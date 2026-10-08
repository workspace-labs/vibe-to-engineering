#!/usr/bin/env python3
"""Run explicit validation scopes in a disposable copy and isolated user profile.

The macOS copy redirects only childenv.SCRATCH_BASE to a harness-owned directory.
Production retains scratch; the test harness removes its own disposable tree on exit.
No runtime guard, reader requirement, enrollment rule or test assertion is bypassed.
"""
import argparse
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tempfile
import time
import unittest

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
PORTABLE = (
    "test_package", "test_reader_platform", "test_a1_matrix_regressions", "test_emission_result",
    "test_protocol", "test_env_literal.Grammar", "test_r2_confidentiality.EmissionModule",
    "test_f3_ambiguous.AmbiguousCollection", "test_platform_evidence",
    "test_platform_render", "test_enrolled_isolation", "test_recovery_review",
    "test_scratch_retention",
)


def worker(scope, summary):
    sys.path.insert(0, str(ROOT / "tests"))
    loader = unittest.TestLoader()
    suite = (loader.loadTestsFromNames(PORTABLE) if scope == "portable" else
             loader.discover(str(ROOT / "tests"), pattern="test_*.py"))
    started = time.time()
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    report = {
        "scope": scope, "platform": platform.platform(), "machine": platform.machine(),
        "python": sys.version, "executable": sys.executable,
        "tests_run": result.testsRun, "failures": len(result.failures),
        "errors": len(result.errors), "skips": [(str(t), why) for t, why in result.skipped],
        "seconds": round(time.time() - started, 3),
        "passed": result.wasSuccessful() and not result.skipped,
        "portable_selection": list(PORTABLE) if scope == "portable" else None,
        "scratch_redirection": "test-owned disposable base; runtime source copy only",
        "release_readiness": False,
    }
    summary.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0 if report["passed"] else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scope", required=True, choices=("portable", "macos"))
    parser.add_argument("--output", type=Path, help="directory for log and JSON summary")
    parser.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.worker:
        if os.environ.get("V2E_VALIDATION_ROOT") != str(ROOT.parent):
            parser.error("--worker is internal; use the normal isolated validation entry point")
        return worker(args.scope, args.output / "summary.json")
    if args.scope == "macos" and (sys.platform != "darwin" or platform.machine() != "arm64"):
        parser.error("the complete reviewed regression scope requires native macOS arm64")
    output = (args.output.resolve() if args.output else
              Path(tempfile.mkdtemp(prefix="v2e-validation-results-")))
    output.mkdir(parents=True, exist_ok=True)
    # A failed preparation/import must never leave a prior run's success as evidence.
    (output / "summary.json").write_text(json.dumps({
        "scope": args.scope, "passed": False, "state": "incomplete",
        "started_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "release_readiness": False,
    }, indent=2) + "\n", encoding="utf-8")
    (output / "tests.log").write_text("Preparing isolated validation.\n", encoding="utf-8")
    with tempfile.TemporaryDirectory(prefix="v2e-validation-") as directory:
        base = Path(directory).resolve()
        copy = base / "repo"
        copy.mkdir()
        for name in ("skills", "tests"):
            shutil.copytree(ROOT / name, copy / name, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        for path in ROOT.glob("*.md"):
            shutil.copyfile(path, copy / path.name)
        shutil.copyfile(ROOT / "LICENSE", copy / "LICENSE")
        scratch = base / "scratch"
        scratch.mkdir(mode=0o700)
        source = copy / "skills" / "vibe-to-engineering" / "scripts" / "childenv.py"
        text = source.read_text(encoding="utf-8")
        marker = 'SCRATCH_BASE = "/tmp"'
        if text.count(marker) != 1:
            raise RuntimeError("test scratch redirection needs review: source marker changed")
        source.write_text(text.replace(marker, "SCRATCH_BASE = " + repr(str(scratch))), encoding="utf-8")
        home, temp = base / "home", base / "temp"
        home.mkdir()
        temp.mkdir()
        config = home / "gitconfig"
        config.write_text("[user]\n\tname = Validation\n\temail = validation@example.invalid\n", encoding="utf-8")
        env = {k: v for k, v in os.environ.items()
               if not k.startswith(("GIT_", "PYTHON", "V2E_"))}
        # Only explicit external test prerequisites cross into the isolated process.
        for name in ("V2E_READER_MATRIX_DIR", "V2E_BROWSER"):
            if name in os.environ:
                env[name] = str(Path(os.environ[name]).expanduser().resolve())
        drive, tail = os.path.splitdrive(str(home))
        env.update(HOME=str(home), USERPROFILE=str(home), HOMEDRIVE=drive, HOMEPATH=tail,
                   APPDATA=str(home / "AppData" / "Roaming"), LOCALAPPDATA=str(home / "AppData" / "Local"),
                   TMP=str(temp), TEMP=str(temp), TMPDIR=str(temp), GIT_CONFIG_GLOBAL=str(config),
                   GIT_CONFIG_NOSYSTEM="1", PYTHONUTF8="1", PYTHONDONTWRITEBYTECODE="1",
                   V2E_VALIDATION_ROOT=str(base))
        if args.scope == "macos":
            env.update(V2E_REQUIRE_NODE="1", V2E_REQUIRE_MATRIX="1")
        command = [sys.executable, "-B", str(copy / "tests" / "run_validation.py"),
                   "--scope", args.scope, "--worker", "--output", str(output)]
        with (output / "tests.log").open("wb") as log:
            done = subprocess.run(command, cwd=str(copy), env=env, stdout=log, stderr=subprocess.STDOUT)
        print((output / "tests.log").read_text(encoding="utf-8", errors="replace"))
        print("Validation evidence:", output)
        return done.returncode


if __name__ == "__main__":
    sys.exit(main())
