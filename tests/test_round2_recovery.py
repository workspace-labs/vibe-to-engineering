"""Round 2 recovery contracts on disposable projects."""
import contextlib
import io
import os
from pathlib import Path
import stat
import sys
import unittest
from unittest import mock

from support import Fixture, ROOT, STATE, identities, write

sys.path.insert(0, str(ROOT / "skills/vibe-to-engineering/scripts"))
import checkpoint
import gitrun
import watched


class RecoveryRound2(Fixture):
    def test_noop_restore_agrees_with_diff_on_watched_data(self):
        p = self.plain_project()
        self.tool(p, "create", "start")
        for args in (("diff", "start"), ("restore", "start", "--apply")):
            self.tool(p, *args)
        watched_path = p / "debug.log"
        watched_path.write_bytes(b"changed")
        before = watched_path.stat()
        for args in (("diff", "start"), ("restore", "start", "--apply")):
            output, _ = self.tool(p, *args, expect=3)
            self.assertIn("debug.log", output)
            self.assertNotIn("the project already matches", output)
        self.assertEqual(watched_path.read_bytes(), b"changed")
        self.assertEqual(watched_path.stat().st_mtime_ns, before.st_mtime_ns)
        watched_path.unlink()
        for args in (("diff", "start"), ("restore", "start", "--apply")):
            output, _ = self.tool(p, *args, expect=3)
            self.assertRegex(output, r"gone\s+debug.log")
            self.assertFalse(watched_path.exists())

    def test_list_and_labeled_tree_preserve_store_metadata(self):
        p = self.plain_project()
        self.tool(p, "create", "start")
        store = self.store(p)
        for args in (("list",), ("tree", "start")):
            before = identities(store)
            self.tool(p, *args)
            self.assertEqual(identities(store), before)
        (store / "info/exclude").write_text("incomplete\n")
        before = identities(store)
        for args in (("list",), ("tree", "start")):
            _, error = self.tool(p, *args, expect=1)
            self.assertIn("exclude", error)
            self.assertEqual(identities(store), before)

    def test_inspection_uses_external_scratch_and_disables_configured_trace_targets(self):
        for project in (self.plain_project(), self.git_project()):
            global_ignore = self.home / "global-ignore"
            global_ignore.write_text("workspace.cache\n")
            write(project / "workspace.cache", b"ignored by user configuration")
            before = identities(project)
            trace = self.tmp / "trace-record"
            config = self.home / "gitconfig"
            with config.open("a") as target:
                target.write("[core]\n    excludesFile = %s\n[trace2]\n    eventTarget = %s\n"
                             % (global_ignore, trace))
            environment = dict(self.env, TMPDIR=str(project), TMP=str(project), TEMP=str(project))
            genuine = gitrun.subprocess.run
            with mock.patch.dict(os.environ, environment, clear=True), \
                    mock.patch.object(gitrun.subprocess, "run") as launch:
                # Inspect the first proposed child before allowing an ordinary Git call.
                def guarded(command, **kwargs):
                    env = kwargs["env"]
                    self.assertEqual([env.get(k) for k in ("GIT_TRACE2", "GIT_TRACE2_EVENT", "GIT_TRACE2_PERF")],
                                     ["0", "0", "0"])
                    self.assertNotEqual(Path(env["TMPDIR"]).resolve(), project)
                    return genuine(command, **kwargs)
                launch.side_effect = guarded
                found = checkpoint.current_survey_read_only(project)
            self.assertIn(b"workspace.cache", found.ignored)
            self.assertFalse(trace.exists())
            self.assertEqual(identities(project), before)

    def test_imported_fingerprint_key_requires_private_owner_and_single_identity(self):
        key = self.tmp / "key"
        generated = watched.fingerprint_key(key)
        self.assertEqual(len(generated), 32)
        self.assertEqual(stat.S_IMODE(key.stat().st_mode), 0o600)
        self.assertEqual(watched.fingerprint_key(key), generated)
        key.chmod(0o640)
        with self.assertRaises(gitrun.Fail):
            watched.fingerprint_key(key)
        self.assertEqual(stat.S_IMODE(key.stat().st_mode), 0o640)
        key.chmod(0o600)
        os.link(key, self.tmp / "second-name")
        with self.assertRaises(gitrun.Fail):
            watched.fingerprint_key(key)
        self.assertEqual(key.stat().st_nlink, 2)
        (self.tmp / "second-name").unlink()
        with mock.patch.object(watched.os, "geteuid", return_value=key.stat().st_uid + 1):
            with self.assertRaises(gitrun.Fail):
                watched.fingerprint_key(key)
        self.assertEqual(watched.fingerprint_key(key), generated)

        from store_transaction import transaction
        project = self.plain_project()
        self.tool(project, "create", "start")
        live_key = project / STATE / watched.KEY_NAME
        with transaction(project, STATE, checkpoint.STORE_NAME, False, checkpoint.check_state_folder):
            with self.assertRaises(gitrun.Fail):
                watched.fingerprint_key(live_key, create=True)
        self.assertFalse(live_key.exists())

    def test_git_store_updates_are_staged_and_lost_ownership_preserves_both_directories(self):
        p = self.plain_project()
        self.tool(p, "create", "start")
        live = self.store(p)
        original = identities(live)
        replacement = self.tmp / "replacement"
        replacement.mkdir()
        write(replacement / "sentinel", b"second directory")
        old = self.tmp / "previous"
        save = checkpoint.save_checkpoint
        def change_owner(store, *args):
            self.assertNotEqual(Path(store).resolve(), live.resolve())
            # A regular directory handoff before publication, using only this fixture.
            live.rename(old)
            replacement.rename(live)
            return save(store, *args)
        with mock.patch.dict(os.environ, self.env, clear=True), \
                mock.patch.object(checkpoint, "save_checkpoint", side_effect=change_owner), \
                contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(checkpoint.main(["--project", str(p), "create", "later"]), 1)
        self.assertEqual(identities(old), original)
        self.assertEqual(sorted(path.name for path in live.iterdir()), ["sentinel"])
        self.assertEqual((live / "sentinel").read_bytes(), b"second directory")
        live.rename(replacement)
        old.rename(live)
        self.tool(p, "create", "later")
        listed, _ = self.tool(p, "list")
        self.assertIn("later", listed)
        self.assertIn("start", listed)
        self.assertEqual(stat.S_IMODE(live.stat().st_mode), 0o700)

    def test_losing_state_after_store_publication_restores_both_generations_and_new_key(self):
        try:
            import store_transaction
        except ImportError:
            self.fail("checkpoint store publication has no pinned directory transaction")
        p = self.plain_project()
        self.tool(p, "create", "start")
        write(p / ".gitignore", b"*.log\n.env\n")
        write(p / ".env", b"SAMPLE=synthetic\n")
        live_state = p / STATE
        previous = self.tmp / "previous-state"
        alternate = self.tmp / "alternate-state"
        alternate.mkdir()
        write(alternate / "sentinel", b"independent synthetic state")
        before = identities(live_state)
        other = identities(alternate)
        actual = store_transaction.move_exclusive
        def handoff(src_fd, src, dst_fd, dst):
            actual(src_fd, src, dst_fd, dst)
            if src == "complete.git" and dst == "checkpoints.git":
                live_state.rename(previous)
                alternate.rename(live_state)
        with mock.patch.dict(os.environ, self.env, clear=True), \
                mock.patch.object(store_transaction, "move_exclusive", side_effect=handoff), \
                contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(checkpoint.main(["--project", str(p), "create", "next"]), 1)
        # Directory-entry moves update the containing directory's timestamp.
        for directory, expected in ((previous, before), (live_state, other)):
            actual_entries = identities(directory)
            self.assertEqual(actual_entries.pop(".")[::2], expected.pop(".")[::2])
            self.assertEqual(actual_entries, expected)
        self.assertFalse((previous / watched.KEY_NAME).exists())
        self.assertFalse((live_state / watched.KEY_NAME).exists())
