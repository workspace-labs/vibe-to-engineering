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
from package_privacy import scan_current
from suite_scope import discovery
from validation_prerequisites import validation_identity, worker_environment

ROOT = Path(__file__).resolve().parents[1]
PORTABLE = (
    "test_package", "test_standard_alignment", "test_reader_platform", "test_a1_matrix_regressions", "test_emission_result",
    "test_protocol", "test_env_literal.Grammar", "test_r2_confidentiality.EmissionModule",
    "test_f3_ambiguous.AmbiguousCollection", "test_platform_evidence",
    "test_platform_render", "test_confidential_names.NameMapPortable", "test_enrolled_isolation", "test_recovery_review",
    "test_scratch_retention", "test_secret_scalars", "test_render_map.MapPortable",
    "test_round3_state.TreeInventory", "test_review_protocol", "test_validation_prerequisites",
    "test_workflow_decisions", "test_validation_scope",
)


def worker(scope, summary):
    sys.path.insert(0, str(ROOT / "tests"))
    loader = unittest.TestLoader()
    suite = (loader.loadTestsFromNames(PORTABLE) if scope == "portable" else
             loader.discover(str(ROOT / "tests"), pattern="test_*.py"))
    selection = discovery(scope, suite)
    started = time.time()
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    report = {
        "scope": scope, "platform": platform.platform(), "machine": platform.machine(),
        "python": sys.version, "executable": sys.executable,
        "tests_run": result.testsRun, "failures": len(result.failures),
        "errors": len(result.errors), "skips": [(str(t), why) for t, why in result.skipped],
        "seconds": round(time.time() - started, 3),
        "passed": selection["complete"] and result.wasSuccessful() and not result.skipped,
        "discovery": selection,
        "portable_selection": list(PORTABLE) if scope == "portable" else None,
        "scratch_redirection": "test-owned disposable base; runtime source copy only",
        "release_readiness": False,
    }
    preparation = json.loads(summary.read_text(encoding="utf-8"))
    for key in ("prerequisites", "source_privacy"):
        report[key] = preparation[key]
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
        home, temp = base / "home", base / "temp"
        home.mkdir()
        temp.mkdir()
        config = home / "gitconfig"
        config.write_text("[user]\n\tname = Validation\n\temail = validation@example.invalid\n", encoding="utf-8")
        env = worker_environment(base, args.scope == "macos", os.environ)
        identity, problems = validation_identity(ROOT, env, args.scope == "macos")
        summary = output / "summary.json"
        current = json.loads(summary.read_text(encoding="utf-8"))
        privacy = scan_current(ROOT)
        if not privacy["entries"] or any(privacy[k] for k in ("matching_paths", "matching_contents", "unreadable")):
            problems.append("Public source privacy check found matches or unreadable entries.")
        current.update(prerequisites=identity, prerequisite_errors=problems, source_privacy=privacy)
        summary.write_text(json.dumps(current, indent=2) + "\n", encoding="utf-8")
        if problems:
            message = "\n".join(problems)
            (output / "tests.log").write_text(message + "\n", encoding="utf-8")
            print(message, file=sys.stderr)
            return 2
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
        command = [sys.executable, "-B", "-u", str(copy / "tests" / "run_validation.py"),
                   "--scope", args.scope, "--worker", "--output", str(output)]
        with (output / "tests.log").open("wb") as log:
            with subprocess.Popen(command, cwd=str(copy), env=env, stdout=subprocess.PIPE,
                                  stderr=subprocess.STDOUT) as process:
                for line in process.stdout:
                    log.write(line)
                    log.flush()
                    sys.stdout.buffer.write(line)
                    sys.stdout.buffer.flush()
                code = process.wait()
        print("Validation evidence:", output)
        return code


if __name__ == "__main__":
    sys.exit(main())
