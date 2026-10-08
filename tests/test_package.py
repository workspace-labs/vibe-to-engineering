"""Portable package constraints; the external skill validator is a separate check."""
import ast
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "vibe-to-engineering"


class Package(unittest.TestCase):
    def test_installable_package_contains_the_exact_license(self):
        self.assertEqual((SKILL / "LICENSE").read_bytes(), (ROOT / "LICENSE").read_bytes())

    def test_declared_metadata_meets_skill_and_ui_constraints(self):
        text = (SKILL / "SKILL.md").read_text(encoding="utf-8")
        self.assertTrue(text.startswith("---\n"))
        header = text.split("---\n", 2)[1]
        self.assertRegex(header, r"(?m)^name: vibe-to-engineering$")
        description = re.search(r'(?m)^description: "(.*)"$', header)
        self.assertIsNotNone(description)
        self.assertTrue(0 < len(description.group(1)) <= 1024)
        self.assertNotRegex(description.group(1), r"[<>]")
        self.assertIn('version: "0.1.0-dev"', header)
        config = (SKILL / "agents" / "openai.yaml").read_text(encoding="utf-8")
        summary = re.search(r'(?m)^\s+short_description: "(.*)"$', config)
        self.assertIsNotNone(summary)
        self.assertTrue(25 <= len(summary.group(1)) <= 64)

    def test_bundled_runtime_parses_as_documented_python_38(self):
        for script in sorted((SKILL / "scripts").glob("*.py")):
            with self.subTest(script=script.name):
                ast.parse(script.read_text(encoding="utf-8"), filename=str(script), feature_version=(3, 8))


if __name__ == "__main__":
    unittest.main()
