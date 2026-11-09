"""Portable integrity checks for the offline engineering-standard snapshot.

These checks validate package provenance, completeness and discoverability. They do
not claim that an agent obeys an approval gate; that needs a separate workflow exam.
"""
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import unittest
from urllib.parse import unquote, urlsplit


ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "vibe-to-engineering"
BUNDLE = SKILL / "references" / "build-standard"
COMMIT = "a27317b9f7885b18dc6b5eedc24b5dd29d27fdb9"
VERSION = "1.4.0"
REPOSITORY = "https://github.com/workspace-labs/agent-engineering-standard"
UPSTREAM_SKILL = "skills/software-engineering-build-standard/"
GUIDES = {
    "architecture-and-boundaries.md", "backend.md", "coverage-and-evidence.md",
    "data-state-and-runtime.md", "frontend.md", "layout-map.md",
    "platform-services.md", "repository-and-delivery.md", "review-and-completion.md",
    "team-and-lifecycle.md",
}
TREES = {
    "ai-service.md", "api-backend.md", "cli-tool.md", "data-pipeline.md",
    "desktop-app.md", "game.md", "library.md", "mobile-app.md", "monorepo.md",
    "webapp.md", "website.md",
}
EXPECTED_FILES = ({"standard.md", "LICENSE"}
                  | {"references/" + name for name in GUIDES}
                  | {"references/trees/" + name for name in TREES | {"README.md"}})
LINK = re.compile(r"\[[^\]\n]+\]\(([^)\n]+)\)")


class StandardAlignment(unittest.TestCase):
    def manifest(self):
        path = BUNDLE / "source.json"
        self.assertTrue(path.is_file(), "the offline standard snapshot manifest is missing")
        for directory in (SKILL / "references", BUNDLE):
            self.assertFalse(directory.is_symlink(), "a snapshot directory must not be a symlink")
        self.assertFalse(path.is_symlink(), "the snapshot manifest must not be a symlink")
        self.assertIn(SKILL.resolve(), BUNDLE.resolve().parents)
        return json.loads(path.read_text(encoding="utf-8"))

    def local_links(self, source):
        """Check real Markdown targets component by component, even on a case-folding disk."""
        targets = set()
        text = source.read_text(encoding="utf-8")
        for raw in LINK.findall(text):
            address = raw.strip().strip("<>")
            parsed = urlsplit(address)
            if parsed.scheme or parsed.netloc or not parsed.path:
                continue
            relative = unquote(parsed.path)
            self.assertNotIn("\\", relative, str(source))
            self.assertFalse(PurePosixPath(relative).is_absolute(), str(source))
            candidate = source.parent
            for part in PurePosixPath(relative).parts:
                if part == "..":
                    candidate = candidate.parent
                elif part != ".":
                    self.assertTrue(candidate.is_dir(), "%s: missing parent for %s" % (source, raw))
                    self.assertIn(part, {p.name for p in candidate.iterdir()},
                                  "%s: missing or incorrectly capitalized link %s" % (source, raw))
                    candidate = candidate / part
                self.assertFalse(candidate.is_symlink(), "%s: linked target %s" % (source, raw))
                self.assertTrue(candidate.resolve() == SKILL.resolve()
                                or SKILL.resolve() in candidate.resolve().parents,
                                "%s: link escapes the installable skill: %s" % (source, raw))
            targets.add(candidate.resolve())
        return targets

    def test_snapshot_records_the_known_upstream_revision_and_version(self):
        manifest = self.manifest()
        self.assertEqual(manifest["schemaVersion"], 1)
        self.assertEqual(manifest["repository"], REPOSITORY)
        self.assertEqual(manifest["commit"], COMMIT)
        self.assertEqual(manifest["version"], VERSION)
        text = (BUNDLE / "standard.md").read_text(encoding="utf-8")
        versions = re.findall(r"(?m)^Standard version: (\d+\.\d+\.\d+)$", text)
        self.assertEqual(versions, [manifest["version"]])

    def test_manifest_accounts_for_every_bundled_file_and_all_project_families(self):
        manifest = self.manifest()
        self.assertEqual(set(manifest["files"]), EXPECTED_FILES)
        actual = set()
        for path in BUNDLE.rglob("*"):
            self.assertFalse(path.is_symlink(), "a bundled reference must not be a symlink: %s" % path)
            self.assertTrue(path.is_dir() or path.is_file(), "nonregular bundled resource: %s" % path)
            if path.is_file():
                actual.add(path.relative_to(BUNDLE).as_posix())
        self.assertEqual(actual, EXPECTED_FILES | {"source.json"})

    def test_snapshot_bytes_match_the_manifest_and_source_paths(self):
        for relative, entry in self.manifest()["files"].items():
            with self.subTest(file=relative):
                path = PurePosixPath(relative)
                self.assertFalse(path.is_absolute())
                self.assertNotIn("..", path.parts)
                self.assertNotIn("\\", relative)
                self.assertEqual(path.as_posix(), relative)
                destination = BUNDLE / relative
                self.assertTrue(destination.is_file(), relative)
                self.assertFalse(destination.is_symlink(), relative)
                self.assertIn(BUNDLE.resolve(), destination.resolve().parents)
                upstream = ("LICENSE" if relative == "LICENSE" else UPSTREAM_SKILL
                            + ("SKILL.md" if relative == "standard.md" else relative))
                self.assertEqual(entry["upstream_path"], upstream)
                self.assertRegex(entry["sha256"], r"^[0-9a-f]{64}$")
                self.assertEqual(hashlib.sha256(destination.read_bytes()).hexdigest(), entry["sha256"])

    def test_the_snapshot_is_self_contained_with_case_correct_markdown_links(self):
        self.manifest()
        for source in sorted(BUNDLE.rglob("*.md")):
            with self.subTest(source=source.relative_to(BUNDLE)):
                self.local_links(source)

    def test_alignment_router_exposes_the_standard_layout_and_tree_chooser(self):
        source = SKILL / "references" / "standard-alignment.md"
        self.assertTrue(source.is_file(), "the migration-to-standard routing reference is missing")
        targets = self.local_links(source)
        for relative in ("standard.md", "references/layout-map.md", "references/trees/README.md"):
            self.assertIn((BUNDLE / relative).resolve(), targets,
                          "the alignment router must link the installable offline reference: " + relative)

    def test_the_snapshot_cannot_be_discovered_as_a_second_agent_skill(self):
        self.assertEqual(list(SKILL.rglob("SKILL.md")), [SKILL / "SKILL.md"])
        self.assertFalse(any(BUNDLE.rglob("openai.yaml")), "do not bundle a second skill's UI metadata")

    def test_plan_form_records_its_standard_and_project_specific_choices(self):
        template = (SKILL / "assets" / "plan-template.html").read_text(encoding="utf-8")
        for field in ("STANDARD_VERSION", "STANDARD_COMMIT", "PROJECT_TYPE", "TREE_GUIDES",
                      "STANDARD_DECISIONS", "PROJECT_RULES"):
            with self.subTest(field=field):
                self.assertTrue("{{" + field + "}}" in template, "missing plan form field: " + field)
        # The filled form must identify the approved plan independently of the standard version.
        self.assertIn("{{PLAN_VERSION}}", template)


if __name__ == "__main__":
    unittest.main()
