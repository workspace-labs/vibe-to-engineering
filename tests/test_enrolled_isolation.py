"""Fixture isolation checks; enrollment is mocked and no real registry is read or written."""
import ntpath
import os
import posixpath
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import enrolled


class EnrollmentIsolation(unittest.TestCase):
    def test_home_mapping_isolates_posix_and_windows_resolution(self):
        with tempfile.TemporaryDirectory(prefix="v2e-home-vars-") as folder:
            home = Path(folder).resolve()
            with mock.patch.dict(os.environ, enrolled.home_environment(home)):
                self.assertEqual(posixpath.expanduser("~"), str(home))
                self.assertEqual(ntpath.expanduser("~"), str(home))
                self.assertEqual(Path(enrolled.evidence.registry_path()).resolve(),
                                 home / ".vibe-to-engineering" / "runners.json")
                with mock.patch.dict(os.environ):
                    os.environ.pop("USERPROFILE")
                    self.assertEqual(ntpath.expanduser("~"), str(home))

    def test_fixture_checks_registry_location_before_mocked_enrollment(self):
        with tempfile.TemporaryDirectory(prefix="v2e-isolated-enrollment-") as folder:
            home = Path(folder).resolve()
            paths = []
            def observe(*args, **kwargs):
                paths.append(Path(enrolled.evidence.registry_path()).resolve())
            with mock.patch.object(enrolled, "_HOME", None), \
                    mock.patch.object(enrolled.tempfile, "mkdtemp", return_value=str(home)), \
                    mock.patch.object(enrolled.atexit, "register"), \
                    mock.patch.object(enrolled.evidence, "enroll_runner", side_effect=observe):
                self.assertEqual(enrolled.enrolled_home(), home)
            self.assertEqual(paths, [home / ".vibe-to-engineering" / "runners.json"] * 2)
            self.assertEqual(list(home.iterdir()), [])

    def test_misdirected_registry_refuses_before_enrollment(self):
        with tempfile.TemporaryDirectory(prefix="v2e-registry-misdirection-") as folder:
            home = Path(folder).resolve()
            with mock.patch.object(enrolled, "_HOME", None), \
                    mock.patch.object(enrolled.tempfile, "mkdtemp", return_value=str(home)), \
                    mock.patch.object(enrolled.atexit, "register"), \
                    mock.patch.object(enrolled.evidence, "registry_path", return_value=str(home.parent / "wrong.json")), \
                    mock.patch.object(enrolled.evidence, "enroll_runner") as enroll:
                with self.assertRaisesRegex(RuntimeError, "escaped the isolated home"):
                    enrolled.enrolled_home()
                enroll.assert_not_called()
            self.assertEqual(list(home.iterdir()), [])

    def test_subprocess_environment_uses_all_isolated_home_variables(self):
        with tempfile.TemporaryDirectory(prefix="v2e-subprocess-home-") as folder:
            home = Path(folder).resolve()
            with mock.patch.object(enrolled, "enrolled_home", return_value=home):
                env = enrolled.environ({"HOME": "wrong", "USERPROFILE": "wrong", "KEEP": "value"})
            for name, value in enrolled.home_environment(home).items():
                self.assertEqual(env[name], value)
            self.assertEqual(env["KEEP"], "value")


if __name__ == "__main__":
    unittest.main()
