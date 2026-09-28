"""A2 corrective regressions: approval binds to bytes, every pin survives swaps,
and malformed registries refuse before execution (A2-F01/F02/F03).

The only scheduled operations are real replacements of synthetic files at the
documented identity/launch boundaries. Reads, copies, enrollment probes and check
subprocesses remain real. Each compiled candidate records *every* invocation, so
an unapproved --version execution cannot hide behind its profile answer.

Run from a disposable repository copy, with an optional preserved baseline:
  V2E_EVIDENCE=/path/to/baseline/.../evidence.py python3 -B -m unittest \
      discover -s tests -p test_a2_corrective.py -v

Every HOME and registry is isolated. No system binary or real enrollment changes.
"""

import contextlib
import hashlib
import importlib.util
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
TOOL = Path(os.environ.get("V2E_EVIDENCE", ROOT / "skills" / "vibe-to-engineering"
                           / "scripts" / "evidence.py"))
sys.path.insert(0, str(TOOL.parent))


def subject():
    spec = importlib.util.spec_from_file_location("a2_corrective_subject", str(TOOL))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class RunnerCorrective(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="v2e-a2-corrective-")).resolve()
        self.serial = 0

    def tearDown(self):
        # Restore only our owned directories, including those renamed by a swap.
        # Do not follow the intentionally planted links during cleanup.
        for folder, dirs, _ in os.walk(str(self.tmp), followlinks=False):
            os.chmod(folder, 0o700)
            for name in dirs:
                path = Path(folder) / name
                if not path.is_symlink():
                    path.chmod(0o700)
        shutil.rmtree(str(self.tmp))

    def case(self, name="case"):
        self.serial += 1
        base = self.tmp / ("%02d-%s" % (self.serial, name))
        home, project = base / "home", base / "project"
        home.mkdir(parents=True)
        (project / ".vibe-to-engineering" / "evidence").mkdir(parents=True)
        return base, home, project

    def registry_path(self, home):
        return home / ".vibe-to-engineering" / "runners.json"

    def registry(self, home):
        path = self.registry_path(home)
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None

    def compiled(self, path, label, marker):
        cc = shutil.which("cc")
        if cc is None:
            self.skipTest("NOT VERIFIED: no C compiler for real invocation markers")
        path.parent.mkdir(parents=True, exist_ok=True)
        source = self.tmp / ("marker-%d.c" % self.serial)
        # JSON quoting is valid C string quoting for these ASCII temporary paths.
        source.write_text(
            '#include <stdio.h>\n#include <string.h>\n'
            'int main(int n, char **v) {\n'
            '  FILE *f = fopen(%s, "a");\n'
            '  if (f) { fprintf(f, "%s %%s\\n", n > 1 ? v[1] : "none"); fclose(f); }\n'
            '  if (n > 1 && !strcmp(v[1], "--version")) puts("v20.20.2");\n'
            '  else puts("%s");\n  return 0;\n}\n'
            % (json.dumps(str(marker)), label, label), encoding="utf-8")
        done = subprocess.run([cc, str(source), "-o", str(path)],
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.assertEqual(done.returncode, 0, done.stderr.decode("utf-8", "replace"))
        return path

    def pair(self, base, readonly=False):
        a_marker, b_marker = base / "A.log", base / "B.log"
        a = self.compiled(base / "installation" / "bin" / "node", "APPROVED_A", a_marker)
        b = self.compiled(base / "replacement" / "bin" / "node", "SUBSTITUTE_B", b_marker)
        if readonly:
            for path in (a, a.parent, b, b.parent):
                path.chmod(0o555)
            self.assertFalse(os.access(str(a), os.W_OK))
            self.assertFalse(os.access(str(a.parent), os.W_OK))
            self.assertTrue(os.access(str(a.parent.parent.parent), os.W_OK))
        return a, b, a_marker, b_marker

    def enroll(self, module, program, home, ask=None):
        shown = io.StringIO()
        with mock.patch.dict(os.environ, {"HOME": str(home)}):
            try:
                module.enroll_runner(str(program), ask=ask or (lambda _: "enroll"), out=shown)
            except module.Fail as error:
                return False, shown.getvalue(), str(error)
        return True, shown.getvalue(), ""

    def check(self, module, program, home, project):
        output = project / ".vibe-to-engineering" / "evidence" / "check.txt"
        stdout, stderr = io.StringIO(), io.StringIO()
        with mock.patch.dict(os.environ, {"HOME": str(home)}), \
                contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            code = module.main(["--project", str(project), "--out", str(output),
                                "--", str(program), "actual-check"])
        return code, stdout.getvalue(), stderr.getvalue(), output

    def assert_safe_enrollment(self, accepted, home, a_marker, b_marker, approved_hash, shown):
        self.assertFalse(b_marker.exists(), "unapproved candidate executed: "
                         + (b_marker.read_text() if b_marker.exists() else ""))
        self.assertIn(approved_hash, shown)
        if accepted:
            self.assertEqual(self.registry(home)["runners"]["node"]["sha256"], approved_hash)
            self.assertEqual(a_marker.read_text().splitlines(), ["APPROVED_A --version"])
        else:
            self.assertIsNone(self.registry(home), "refused enrollment must not save an identity")

    def assert_safe_check(self, code, stdout, stderr, output, a_marker, b_marker, approved_hash):
        self.assertFalse(b_marker.exists(), "substituted candidate executed: "
                         + (b_marker.read_text() if b_marker.exists() else ""))
        self.assertIn(code, (0, 2), stderr)
        if code == 0:
            self.assertIn("APPROVED_A", stdout)
            self.assertIn("APPROVED_A actual-check", a_marker.read_text().splitlines())
            self.assertIn(approved_hash, output.read_text(encoding="utf-8"))
        else:
            self.assertFalse(output.exists())
            self.assertNotIn("APPROVED_A actual-check", a_marker.read_text().splitlines())

    # F01: keep the original failure and two neighboring boundaries. The hooks
    # schedule a real source replacement; they do not alter hashes or subprocesses.
    def test_replacement_during_approval_never_receives_that_approval(self):
        base, home, _ = self.case("approval")
        a, b, a_marker, b_marker = self.pair(base)
        approved_hash = digest(a)
        module = subject()

        def approve(_):
            os.replace(str(b), str(a))
            return "enroll"

        accepted, shown, _ = self.enroll(module, a, home, approve)
        self.assert_safe_enrollment(accepted, home, a_marker, b_marker, approved_hash, shown)

    def test_replacement_after_approval_recheck_never_executes_unapproved_copy(self):
        base, home, _ = self.case("recheck-copy-gap")
        a, b, a_marker, b_marker = self.pair(base)
        approved_hash = digest(a)
        module = subject()
        original_hash = module.hashed
        state = {"approved": False, "replaced": False}

        def approve(_):
            state["approved"] = True
            return "enroll"

        def replace_after_read(resolved, into=None):
            value = original_hash(resolved, into=into)
            if state["approved"] and not state["replaced"] and resolved == str(a):
                os.replace(str(b), str(a))
                state["replaced"] = True
            return value

        module.hashed = replace_after_read
        accepted, shown, _ = self.enroll(module, a, home, approve)
        # A design that retains its sole reading before approval has no later
        # source read to hook. The copy/probe test below still changes that source.
        self.assert_safe_enrollment(accepted, home, a_marker, b_marker, approved_hash, shown)

    def test_source_replacement_at_copy_probe_boundary_never_changes_probe_bytes(self):
        base, home, _ = self.case("copy-probe-gap")
        a, b, a_marker, b_marker = self.pair(base)
        approved_hash = digest(a)
        module = subject()
        original_probe = module.probe
        replaced = []

        def replace_at_probe(resolved, kind, env, scratch):
            os.replace(str(b), str(a))
            replaced.append(True)
            return original_probe(resolved, kind, env, scratch)

        module.probe = replace_at_probe
        accepted, shown, _ = self.enroll(module, a, home)
        self.assertTrue(replaced, "the approved control must reach its real probe")
        self.assert_safe_enrollment(accepted, home, a_marker, b_marker, approved_hash, shown)

    # F02: a read-only file and immediate folder do not protect their ancestors.
    # Safe copy pin or refusal is permitted; no particular fix is prescribed.
    def swap_case(self, form, legacy_path=False, change_permissions=False):
        base, home, project = self.case(form)
        a, b, a_marker, b_marker = self.pair(base, readonly=True)
        approved_hash = digest(a)
        module = subject()
        accepted, _, refusal = self.enroll(module, a, home)
        if not accepted:
            self.assertFalse(b_marker.exists())
            self.assertIsNone(self.registry(home))
            self.assertTrue(refusal)
            return
        if legacy_path:
            # Compatibility input: this is precisely the path entry the original
            # A2 implementation issued for these bytes at this location.
            registry = self.registry(home)
            registry["runners"]["node"]["pin"] = "path"
            self.registry_path(home).write_text(json.dumps(registry), encoding="utf-8")
        if change_permissions:
            a.chmod(0o755)
            a.parent.chmod(0o755)
        before = self.registry_path(home).read_bytes()
        original_values = module.secret_values
        swapped = []

        def replace_installation(project_arg, env):
            if form in ("ancestor", "legacy", "permission-change"):
                os.rename(str(a.parent.parent), str(base / "parked-installation"))
                os.rename(str(b.parent.parent), str(a.parent.parent))
            elif form == "intermediate-symlink":
                os.rename(str(a.parent.parent), str(base / "parked-installation"))
                os.symlink(str(b.parent.parent), str(a.parent.parent), target_is_directory=True)
            else:
                raise AssertionError("unknown synthetic replacement form")
            swapped.append(True)
            return original_values(project_arg, env)

        module.secret_values = replace_installation
        code, stdout, stderr, output = self.check(module, a, home, project)
        # A refusal may happen during identity validation before the scheduled
        # replacement. A successful check must have passed the real swap window.
        if code == 0:
            self.assertTrue(swapped)
        self.assert_safe_check(code, stdout, stderr, output, a_marker, b_marker, approved_hash)
        self.assertEqual(self.registry_path(home).read_bytes(), before,
                         "routine validation must not silently re-enroll or rewrite pin mode")

    def test_writable_higher_ancestor_cannot_replace_readonly_runner(self):
        self.swap_case("ancestor")

    def test_intermediate_component_cannot_be_replaced_by_symlink_after_validation(self):
        self.swap_case("intermediate-symlink")

    def test_legacy_path_entry_revalidates_ancestor_assumptions(self):
        self.swap_case("legacy", legacy_path=True)

    def test_changed_permissions_after_enrollment_do_not_preserve_unsafe_path_pin(self):
        self.swap_case("permission-change", legacy_path=True, change_permissions=True)

    def test_ordinary_copy_swap_keeps_the_enrolled_bytes_and_one_probe(self):
        base, home, project = self.case("copy-control")
        a, b, a_marker, b_marker = self.pair(base)
        approved_hash = digest(a)
        module = subject()
        accepted, shown, refusal = self.enroll(module, a, home)
        self.assertTrue(accepted, refusal)
        self.assert_safe_enrollment(accepted, home, a_marker, b_marker, approved_hash, shown)
        before = self.registry_path(home).read_bytes()
        original_values = module.secret_values

        def replace_source(project_arg, env):
            os.replace(str(b), str(a))
            return original_values(project_arg, env)

        module.secret_values = replace_source
        code, stdout, stderr, output = self.check(module, a, home, project)
        self.assertEqual(code, 0, stderr)
        self.assert_safe_check(code, stdout, stderr, output, a_marker, b_marker, approved_hash)
        self.assertEqual(a_marker.read_text().splitlines(),
                         ["APPROVED_A --version", "APPROVED_A actual-check"])
        self.assertEqual(self.registry_path(home).read_bytes(), before)

    def test_denied_access_does_not_make_user_owned_chain_immutable(self):
        base, _, _ = self.case("sandbox-access-denial")
        runner = base / "owned-installation" / "node"
        runner.parent.mkdir()
        runner.write_bytes(b"synthetic metadata-only candidate\n")
        runner.chmod(0o555)
        runner.parent.chmod(0o555)
        self.assertEqual(runner.stat().st_uid, os.geteuid())
        self.assertEqual(runner.parent.stat().st_uid, os.geteuid())
        module = subject()
        # A sandbox can deny access even though the owner can later change the
        # object outside that sandbox. Only this metadata decision is patched;
        # all ownership, mode bits, parent traversal and ACL queries stay real.
        with mock.patch.object(module.os, "access", return_value=False):
            self.assertNotEqual(module.location_pin(str(runner)), "path",
                                "a transient access denial must not prove immutable ownership")

    @unittest.skipUnless(sys.platform == "darwin", "NOT VERIFIED: real ACL proof requires macOS")
    def test_acl_proof_observes_real_owned_file_before_and_after_acl(self):
        base, _, _ = self.case("real-acl-metadata")
        path = base / "owned-metadata-file"
        path.write_bytes(b"synthetic ACL fixture\n")
        module = subject()
        fd = os.open(str(path), os.O_RDONLY)
        try:
            self.assertTrue(module.no_acl(fd), "the fresh private file has no extended ACL")
            added = subprocess.run(["/bin/chmod", "+a", "everyone allow read", str(path)],
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            self.assertEqual(added.returncode, 0, added.stderr.decode("utf-8", "replace"))
            self.assertFalse(module.no_acl(fd), "even a read-only ACL prevents the no-ACL proof")
            removed = subprocess.run(["/bin/chmod", "-N", str(path)],
                                     stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            self.assertEqual(removed.returncode, 0, removed.stderr.decode("utf-8", "replace"))
            self.assertTrue(module.no_acl(fd), "removing this fixture's ACL restores the proof")
        finally:
            os.close(fd)

    @unittest.skipUnless(sys.platform == "darwin", "NOT VERIFIED: real ACL proof requires macOS")
    def test_acl_proof_refuses_invalid_descriptor_or_unavailable_metadata(self):
        base, _, _ = self.case("unknown-acl-metadata")
        path = base / "owned-metadata-file"
        path.write_bytes(b"synthetic ACL fixture\n")
        module = subject()
        fd = os.open(str(path), os.O_RDONLY)
        os.close(fd)
        self.assertFalse(module.no_acl(fd), "a real EBADF response cannot establish no ACL")
        self.assertFalse(module.no_acl(-1), "an invalid descriptor cannot establish no ACL")
        fd = os.open(str(path), os.O_RDONLY)
        try:
            # An unavailable platform metadata provider is an unknown result,
            # not evidence of absence. No candidate or permission is mocked.
            with mock.patch.object(module.ctypes, "CDLL", side_effect=OSError("unavailable metadata")):
                self.assertFalse(module.no_acl(fd))
        finally:
            os.close(fd)

    # F03: actual CLI runs exercise normalization, redaction and exit semantics.
    def registry_fixture(self, name):
        base, old_home, project = self.case(name)
        canary = "SYNTHETIC_A2_SECRET_67298"
        home = base / ("home-" + canary)
        old_home.rename(home)
        module = subject()
        accepted, _, refusal = self.enroll(module, "/bin/sh", home)
        self.assertTrue(accepted, refusal)
        return home, project, canary, self.registry(home)

    def cli_check(self, home, project, canary):
        out = project / ".vibe-to-engineering" / "evidence" / "check.txt"
        marker = project / "check-ran"
        done = subprocess.run(
            [sys.executable, "-B", str(TOOL), "--project", str(project), "--out", str(out),
             "--env", "API_TOKEN=" + canary, "--", "/bin/sh", "-c", "printf ran > check-ran"],
            env=dict(os.environ, HOME=str(home), PYTHONDONTWRITEBYTECODE="1"),
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30)
        return done, out, marker

    def assert_registry_refuses(self, registry_bytes, name):
        home, project, canary, valid = self.registry_fixture(name)
        raw = registry_bytes(valid) if callable(registry_bytes) else registry_bytes
        path = self.registry_path(home)
        path.write_bytes(raw)
        done, out, marker = self.cli_check(home, project, canary)
        report = (done.stdout + done.stderr).decode("utf-8", "replace")
        self.assertEqual(done.returncode, 2, report)
        self.assertFalse(marker.exists(), "a malformed registry launched the check")
        self.assertFalse(out.exists(), "a malformed registry produced evidence")
        self.assertEqual(path.read_bytes(), raw, "a routine refusal rewrote the registry")
        self.assertIn("--enroll-runner", report)
        self.assertRegex(report, r"(?i)(repair|re-enroll)")
        self.assertNotIn("Traceback", report)
        self.assertNotIn(canary, report, "the new refusal diagnostic leaked a declared secret")

    def test_boolean_and_noninteger_registry_versions_refuse(self):
        for name, version in (("boolean-true", True), ("float-one", 1.0),
                              ("boolean-false", False), ("string-one", "1"),
                              ("null", None), ("array", []), ("object", {}), ("two", 2)):
            with self.subTest(name):
                self.assert_registry_refuses(
                    lambda valid: json.dumps(dict(valid, version=version)).encode("utf-8"), name)

    def test_invalid_registry_encodings_refuse_without_traceback_or_secret(self):
        samples = (
            ("invalid-byte", b'{"version":1,"runners":{}}\xff'),
            ("truncated-utf8", b'{"version":1,"runners":{}}\xe2\x82'),
            ("utf8-bom", b'\xef\xbb\xbf{"version":1,"runners":{}}'),
            ("utf16", '{"version":1,"runners":{}}'.encode("utf-16")),
            ("not-json", b'{"version":1,"runners":'),
        )
        for name, raw in samples:
            with self.subTest(name):
                self.assert_registry_refuses(raw, name)

    def test_registry_shape_and_entry_type_neighbors_refuse(self):
        for name, transform in (
                ("root-array", lambda valid: []),
                ("root-null", lambda valid: None),
                ("runners-array", lambda valid: dict(valid, runners=[])),
                ("runners-null", lambda valid: dict(valid, runners=None)),
                ("entry-string", lambda valid: dict(valid, runners={"sh": "wrong"})),
                ("size-boolean", lambda valid: dict(valid, runners={
                    "sh": dict(valid["runners"]["sh"], size=True)})),
                ("size-float", lambda valid: dict(valid, runners={
                    "sh": dict(valid["runners"]["sh"], size=1.0)})),
                ("path-array", lambda valid: dict(valid, runners={
                    "sh": dict(valid["runners"]["sh"], path=[])})),
                ("hash-array", lambda valid: dict(valid, runners={
                    "sh": dict(valid["runners"]["sh"], sha256=[])})),
                ("pin-boolean", lambda valid: dict(valid, runners={
                    "sh": dict(valid["runners"]["sh"], pin=True)}))):
            with self.subTest(name):
                self.assert_registry_refuses(
                    lambda valid: json.dumps(transform(valid)).encode("utf-8"), name)

    def test_valid_registry_and_system_runner_still_succeed_without_mutation(self):
        home, project, canary, _ = self.registry_fixture("valid-system-control")
        before = self.registry_path(home).read_bytes()
        done, out, marker = self.cli_check(home, project, canary)
        report = (done.stdout + done.stderr).decode("utf-8", "replace")
        self.assertEqual(done.returncode, 0, report)
        self.assertTrue(marker.exists())
        self.assertTrue(out.exists())
        self.assertEqual(self.registry_path(home).read_bytes(), before)
        self.assertNotIn(canary, report + out.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
