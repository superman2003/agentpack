"""End-to-end and unit tests for agentpack. Run with: python -m unittest discover tests"""

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agentpack import frontmatter, miniyaml
from agentpack.cli import main
from agentpack.project import load_project, validate
from agentpack.scaffold import scaffold_project
from agentpack.targets import build_all


class MiniYamlTests(unittest.TestCase):
    def test_scalars(self):
        doc = miniyaml.loads(
            'name: my-plugin\nversion: "1.2.3"\ncount: 3\nratio: 0.5\n'
            "enabled: true\nnothing: null\n"
        )
        self.assertEqual(doc["name"], "my-plugin")
        self.assertEqual(doc["version"], "1.2.3")
        self.assertEqual(doc["count"], 3)
        self.assertEqual(doc["ratio"], 0.5)
        self.assertIs(doc["enabled"], True)
        self.assertIsNone(doc["nothing"])

    def test_nested_map_and_lists(self):
        doc = miniyaml.loads(
            "author:\n  name: Jane\n  url: https://example.com\n"
            "keywords:\n  - ai\n  - tools\n"
            "targets: [cursor, claude]\n"
        )
        self.assertEqual(doc["author"]["name"], "Jane")
        self.assertEqual(doc["keywords"], ["ai", "tools"])
        self.assertEqual(doc["targets"], ["cursor", "claude"])

    def test_list_of_maps(self):
        doc = miniyaml.loads("plugins:\n  - name: a\n    source: ./a\n  - name: b\n")
        self.assertEqual(doc["plugins"][0], {"name": "a", "source": "./a"})
        self.assertEqual(doc["plugins"][1], {"name": "b"})

    def test_comments_and_colons_in_values(self):
        doc = miniyaml.loads(
            "# leading comment\nurl: https://example.com/x  # trailing\n"
            'desc: "quoted # not a comment"\n'
        )
        self.assertEqual(doc["url"], "https://example.com/x")
        self.assertEqual(doc["desc"], "quoted # not a comment")

    def test_roundtrip(self):
        data = {
            "name": "x", "n": 2, "flag": False,
            "items": ["a", "b: c"], "meta": {"k": "v"},
        }
        self.assertEqual(miniyaml.loads(miniyaml.dumps(data)), data)

    def test_tab_indent_rejected(self):
        with self.assertRaises(miniyaml.MiniYamlError):
            miniyaml.loads("a:\n\tb: 1\n")


class FrontmatterTests(unittest.TestCase):
    def test_split_and_join(self):
        text = "---\nname: s\ndescription: d\n---\n\n# Body\n"
        fm, body = frontmatter.split(text)
        self.assertEqual(fm, {"name": "s", "description": "d"})
        self.assertEqual(body, "\n# Body\n")
        rebuilt = frontmatter.join(fm, body)
        fm2, body2 = frontmatter.split(rebuilt)
        self.assertEqual(fm2, fm)
        self.assertEqual(body2, body)

    def test_no_frontmatter(self):
        fm, body = frontmatter.split("# Just markdown\n")
        self.assertEqual(fm, {})
        self.assertEqual(body, "# Just markdown\n")

    def test_unclosed_frontmatter(self):
        with self.assertRaises(frontmatter.FrontmatterError):
            frontmatter.split("---\nname: x\nno closing fence")


def _make_project(root: Path) -> None:
    (root / "skills" / "review-pr").mkdir(parents=True)
    (root / "skills" / "review-pr" / "SKILL.md").write_text(
        "---\nname: review-pr\ndescription: Review pull requests carefully.\n"
        "paths: \"**/*.py\"\ncustom-field: dropme\n---\n\n# Review\n\nDo the review.\n",
        encoding="utf-8",
    )
    (root / "skills" / "review-pr" / "references").mkdir()
    (root / "skills" / "review-pr" / "references" / "checklist.md").write_text(
        "- check tests\n", encoding="utf-8"
    )
    (root / "commands").mkdir()
    (root / "commands" / "ship-it.md").write_text(
        "---\ndescription: Ship the release.\n---\n\nRun the release workflow.\n",
        encoding="utf-8",
    )
    (root / "agentpack.yaml").write_text(
        "name: my-toolkit\nversion: 1.0.0\ndescription: Test toolkit.\n"
        "author:\n  name: Jane\nlicense: MIT\n",
        encoding="utf-8",
    )


class ProjectTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)

    def test_load_and_validate_ok(self):
        _make_project(self.tmp)
        project = load_project(self.tmp)
        self.assertEqual(project.name, "my-toolkit")
        self.assertEqual(len(project.skills), 1)
        self.assertEqual(len(project.commands), 1)
        self.assertEqual(project.skills[0].extra_files[0].name, "checklist.md")
        errors = [i for i in validate(project) if i.level == "error"]
        self.assertEqual(errors, [])

    def test_validate_catches_bad_names(self):
        _make_project(self.tmp)
        (self.tmp / "agentpack.yaml").write_text(
            "name: My_Bad_Name\nversion: not-semver\ndescription: x\n", encoding="utf-8"
        )
        project = load_project(self.tmp)
        messages = [i.message for i in validate(project) if i.level == "error"]
        self.assertTrue(any("kebab-case" in m for m in messages))
        self.assertTrue(any("semver" in m for m in messages))

    def test_validate_requires_description(self):
        _make_project(self.tmp)
        skill_md = self.tmp / "skills" / "review-pr" / "SKILL.md"
        skill_md.write_text("---\nname: review-pr\n---\n\nbody\n", encoding="utf-8")
        project = load_project(self.tmp)
        errors = [i for i in validate(project) if i.level == "error"]
        self.assertTrue(any("description" in i.message for i in errors))

    def test_name_folder_mismatch_is_error(self):
        _make_project(self.tmp)
        skill_md = self.tmp / "skills" / "review-pr" / "SKILL.md"
        skill_md.write_text(
            "---\nname: other-name\ndescription: d\n---\n\nbody\n", encoding="utf-8"
        )
        project = load_project(self.tmp)
        errors = [i for i in validate(project) if i.level == "error"]
        self.assertTrue(any("must match folder name" in i.message for i in errors))


class BuildTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        _make_project(self.tmp)
        self.project = load_project(self.tmp)
        self.dist = self.tmp / "dist"
        self.results = build_all(
            self.project, self.dist, ["claude", "cursor", "codex", "copilot", "agents"]
        )

    def test_claude_layout(self):
        plugin = self.dist / "claude" / "my-toolkit"
        manifest = json.loads(
            (plugin / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8")
        )
        self.assertEqual(manifest["name"], "my-toolkit")
        self.assertEqual(manifest["version"], "1.0.0")
        self.assertEqual(manifest["author"], {"name": "Jane"})
        self.assertTrue((plugin / "skills" / "review-pr" / "SKILL.md").is_file())
        self.assertTrue(
            (plugin / "skills" / "review-pr" / "references" / "checklist.md").is_file()
        )
        self.assertTrue((plugin / "commands" / "ship-it.md").is_file())
        marketplace = json.loads(
            (self.dist / "claude" / ".claude-plugin" / "marketplace.json")
            .read_text(encoding="utf-8")
        )
        self.assertEqual(marketplace["plugins"][0]["source"], "./my-toolkit")

    def test_cursor_layout_maps_fields(self):
        skill_md = (
            self.dist / "cursor" / ".cursor" / "skills" / "review-pr" / "SKILL.md"
        ).read_text(encoding="utf-8")
        fm, _ = frontmatter.split(skill_md)
        self.assertEqual(fm["name"], "review-pr")
        self.assertEqual(fm["paths"], "**/*.py")
        self.assertNotIn("custom-field", fm)
        # command became a manual skill
        cmd_md = (
            self.dist / "cursor" / ".cursor" / "skills" / "ship-it" / "SKILL.md"
        ).read_text(encoding="utf-8")
        cfm, _ = frontmatter.split(cmd_md)
        self.assertIs(cfm["disable-model-invocation"], True)

    def test_copilot_drops_paths(self):
        skill_md = (
            self.dist / "copilot" / ".github" / "skills" / "review-pr" / "SKILL.md"
        ).read_text(encoding="utf-8")
        fm, _ = frontmatter.split(skill_md)
        self.assertNotIn("paths", fm)
        self.assertEqual(fm["description"], "Review pull requests carefully.")

    def test_codex_and_agents_layouts(self):
        self.assertTrue(
            (self.dist / "codex" / ".codex" / "skills" / "review-pr" / "SKILL.md").is_file()
        )
        agents_md = (
            self.dist / "agents" / ".agents" / "skills" / "review-pr" / "SKILL.md"
        ).read_text(encoding="utf-8")
        fm, _ = frontmatter.split(agents_md)
        # vendor-neutral target keeps unknown fields
        self.assertEqual(fm["custom-field"], "dropme")


class CliTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)

    def test_init_validate_build(self):
        self.assertEqual(main(["init", str(self.tmp), "--name", "demo-pack"]), 0)
        self.assertEqual(main(["validate", str(self.tmp)]), 0)
        self.assertEqual(main(["build", str(self.tmp)]), 0)
        self.assertTrue(
            (self.tmp / "dist" / "claude" / "demo-pack" / ".claude-plugin" / "plugin.json").is_file()
        )
        self.assertTrue(
            (self.tmp / "dist" / "cursor" / ".cursor" / "skills" / "example-skill" / "SKILL.md").is_file()
        )

    def test_init_refuses_overwrite(self):
        scaffold_project(self.tmp, name="demo-pack")
        self.assertEqual(main(["init", str(self.tmp)]), 1)

    def test_build_single_target(self):
        scaffold_project(self.tmp, name="demo-pack")
        self.assertEqual(main(["build", str(self.tmp), "-t", "cursor"]), 0)
        self.assertTrue((self.tmp / "dist" / "cursor").is_dir())
        self.assertFalse((self.tmp / "dist" / "claude").exists())

    def test_build_fails_on_validation_error(self):
        scaffold_project(self.tmp, name="demo-pack")
        (self.tmp / "agentpack.yaml").write_text("name: Bad_Name\n", encoding="utf-8")
        self.assertEqual(main(["build", str(self.tmp)]), 1)


if __name__ == "__main__":
    unittest.main()
