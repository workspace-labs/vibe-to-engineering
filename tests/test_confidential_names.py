"""Owner-designated path names, from the inventory to the two actual PDFs."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
from test_render_map import APPROVAL, MapFixture, SCRIPTS


class NameMapPortable(unittest.TestCase):
    def test_inventory_and_measurements_share_one_reversible_name(self):
        with mock.patch.object(sys, "path", [str(SCRIPTS)] + sys.path):
            from private_names import NameMap
        names = NameMap({"Orchard drafts": "private-folder", "Notebook.py": "private-source"})
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            original = "Orchard drafts/Notebook.py"
            public = "/".join(names.display(part) for part in original.split("/"))
            self.assertEqual(public, "private-folder/private-source")
            self.assertEqual(names.disk_path(project, public), original)
            self.assertEqual(names.display("ordinary.py"), "ordinary.py")
            with self.assertRaisesRegex(ValueError, "My<private-source>"):
                names.display("MyNotebook.py")
            with self.assertRaises(ValueError):
                NameMap({'Notes "A".py': 'private-file'}).check_values({"title": ['Notes "A".py']})
            for markup in ("<p>Orchard&#32;drafts</p>", "<p>Note<b>book</b>.py</p>"):
                with self.assertRaises(ValueError):
                    names.check_html(markup)
            with self.assertRaises(ValueError):
                names.display("private-folder")

    def test_embedded_declared_word_requires_a_complete_private_mapping(self):
        with mock.patch.object(sys, "path", [str(SCRIPTS)] + sys.path):
            from private_names import NameMap
        entries = {"Orion": "private-one"}
        names = NameMap(entries)
        for component, hint in (("OrionClient.js", "<private-one>Client.js"),
                                ("orion_api", "<private-one>_api"),
                                ("orion-web", "<private-one>-web"),
                                ("Orion.md", "<private-one>.md")):
            with self.subTest(component=component):
                with self.assertRaises(ValueError) as caught:
                    names.display(component)
                self.assertIn(hint, str(caught.exception))
                if component.startswith("orion"):
                    self.assertIn("private-one at character 1: lowercase", str(caught.exception))
                self.assertNotIn("orion", str(caught.exception).lower())
                with self.assertRaises(ValueError):
                    names.check_values({"phase": [component]})
                self.assertEqual(NameMap(dict(entries, **{component: "private-two"})).display(component),
                                 "private-two")
        self.assertEqual(names.display("ordinary.js"), "ordinary.js")

    def test_private_map_must_be_outside_the_project_even_through_a_link(self):
        with mock.patch.object(sys, "path", [str(SCRIPTS)] + sys.path):
            from private_names import load_name_map
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder).resolve()
            project = root / "project"
            project.mkdir()
            internal = project / "names.json"
            outside = root / "owner"
            outside.mkdir()
            external = outside / "names.json"
            for path in (internal, external):
                path.write_text(json.dumps({"Example": "private-one"}))
            self.assertEqual(load_name_map(external, project).display("Example"), "private-one")
            for link, folder in ((root / "shortcut", project), (project / "shortcut", outside)):
                if os.name == "nt":
                    # Directory junctions work without Windows symbolic-link privileges.
                    subprocess.run(["cmd.exe", "/d", "/c", "mklink", "/J", str(link), str(folder)],
                                   check=True, stdout=subprocess.PIPE)
                else:
                    link.symlink_to(folder, target_is_directory=True)
            for location in (internal, root / "shortcut" / "names.json", project / "shortcut" / "names.json"):
                with self.subTest(location=location), self.assertRaisesRegex(ValueError, "outside"):
                    load_name_map(location, project)


@unittest.skipUnless(sys.platform == "darwin", "the inventory and PDF tools require macOS")
class ConfidentialNames(MapFixture, unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.private = "Orchard notebook.py"
        self.folder = "Orchard drafts"
        self.names = self.base / "name-map.json"
        self.names.write_text(json.dumps({self.private: "private-source", self.folder: "private-folder"}))
        self.project.joinpath("src", "large.py").rename(self.project / "src" / self.private)
        (self.project / "src").rename(self.project / self.folder)
        self.project.joinpath(self.folder, "visible.py").write_text("ordinary\n")

    def tool(self, script, *args):
        return subprocess.run([sys.executable, "-IB", str(SCRIPTS / script), *map(str, args),
                               "--name-map", str(self.names)], stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT, encoding="utf-8", timeout=90)

    def inventory(self):
        return self.tool("checkpoint.py", "--project", self.project, "tree", "--current")

    def assert_public(self, text):
        self.assertNotIn(self.private, text)
        self.assertNotIn(self.folder, text)

    def test_confidential_inventory_preserves_each_ordinary_component(self):
        result = self.inventory()
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assert_public(result.stdout)
        for label in ("private-folder/", "private-source", "visible.py"):
            self.assertIn(label, result.stdout)
        (self.project / "private-folder").mkdir()
        (self.project / "private-folder" / "ordinary.py").touch()
        result = self.inventory()
        self.assertNotEqual(result.returncode, 0)
        self.assert_public(result.stdout)
        self.assertNotIn("visible.py", result.stdout)

    def test_inventory_refusal_identifies_the_complete_name_using_its_public_label(self):
        (self.project / ("My" + self.private)).touch()
        result = self.inventory()
        self.assertNotEqual(result.returncode, 0)
        self.assert_public(result.stdout)
        self.assertIn("My<private-source>", result.stdout)
        self.assertNotIn("visible.py", result.stdout)

    def test_both_printed_documents_use_inventory_labels_for_measured_source(self):
        result = self.inventory()
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assert_public(result.stdout)
        folder, source = (next(line.split("── ", 1)[1].strip("/") for line in result.stdout.splitlines()
                               if "── " + name in line) for name in ("private-folder", "private-source"))
        self.specification["sources"][0]["path"] = folder + "/" + source
        self.write_plan()
        self.write_ledger(APPROVAL)
        self.write_mapping()
        plan_pdf = self.plan.with_suffix(".pdf")
        for result in (self.tool("render_pdf.py", self.plan, plan_pdf),
                       self.tool("render_map.py", "--project", self.project)):
            self.assertEqual(result.returncode, 0, result.stdout)
            self.assert_public(result.stdout)
        extractor = next((p for p in ("/opt/homebrew/bin/pdftotext", "/usr/local/bin/pdftotext")
                          if os.access(p, os.X_OK)), None)
        self.assertIsNotNone(extractor, "the native PDF check requires an installed pdftotext")
        for pdf in (plan_pdf, self.pdf):
            body = subprocess.check_output([extractor, str(pdf), "-"], encoding="utf-8")
            self.assert_public(body)
            for label in (folder, source, "flow.py"):
                self.assertIn(label, body)
        for record in (self.plan, self.mapping, self.html, self.approved_copy()):
            self.assert_public(record.read_text())
        previous = plan_pdf.read_bytes()
        self.plan.write_text(self.plan.read_text().replace("Sample plan", self.private))
        rejected = self.tool("render_pdf.py", self.plan, plan_pdf)
        self.assertNotEqual(rejected.returncode, 0)
        self.assert_public(rejected.stdout)
        self.assertEqual(plan_pdf.read_bytes(), previous)
