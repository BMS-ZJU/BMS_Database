"""Old contribution links resolve to current pages without widening URL scope."""
import json
from pathlib import Path
import shutil
import subprocess
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from hooks import contribution_links
from scripts.contributions import catalog, intake, runtime, security
import test_contributions as base


class ContributionMigrationTests(unittest.TestCase):
    def setUp(self):
        base.IntakeTests.setUp(self)
        self.old_source = "mandatory/old_example/index.md"
        self.new_source = self.target.removeprefix("docs/")
        self.pages = {
            self.old_source: self.new_source,
            "elective/other/index.md": "courses/other/index.md",
            "error.md": "guide/index.md#finding-resources",
        }
        self.write_manifest()

    def write_manifest(self):
        (self.root / "data/path-migrations.json").write_text(json.dumps({
            "version": 1, "pages": self.pages, "assets": {}, "source_files": {},
        }), encoding="utf-8")

    def old_fields(self):
        return {**base.fields(), "页面地址": "https://example.org/BMS/mandatory/old_example/"}

    def collection(self):
        old = "mandatory/old_example/quizzes/quiz-01.md"
        retained = "courses/example/quizzes/quiz-01.md"
        current = "courses/example/quizzes/2025-2026-quizzes.md"
        self.pages[old] = retained
        self.write_manifest()
        directory = self.root / "docs/courses/example/quizzes"
        directory.mkdir()
        (directory / "quiz-01.md").write_text("Frozen original", encoding="utf-8")
        (directory / "2025-2026-quizzes.md").write_text(
            "---\nresource_aliases:\n- path: quiz-01.md\n  target: quiz-1\n"
            "  export: quiz-1\n---\n# Current collection\n", encoding="utf-8")
        return old, retained, current

    def test_current_and_old_targets_and_urls_can_be_combined(self):
        for target in (self.target, "docs/" + self.old_source):
            for value in (base.fields(), self.old_fields()):
                with self.subTest(target=target, address=value["页面地址"]):
                    intake.validate_selection(self.root, target, value)
                    path, content = intake.resolve_target(self.root, target)
                    self.assertEqual(path, self.root / self.target)
                    self.assertEqual(content, self.original)

    def test_existing_old_source_is_never_selected_over_current_page(self):
        old = self.root / "docs" / self.old_source
        old.parent.mkdir(parents=True)
        old.write_text("Stale source still on disk", encoding="utf-8")
        path, content = intake.resolve_target(self.root, "docs/" + self.old_source)
        self.assertEqual(path, self.root / self.target)
        self.assertEqual(content, self.original)

    def test_alias_collection_does_not_read_a_symlink_before_target_rejection(self):
        link = self.root / "docs/courses/example/link.md"
        link.write_text("Must not be read", encoding="utf-8")
        read_text = Path.read_text

        def guarded_read(path, *args, **kwargs):
            if path == link:
                raise AssertionError("A symlink must not be read while collecting aliases")
            return read_text(path, *args, **kwargs)

        with (
            patch.object(Path, "is_symlink", lambda path: path == link),
            patch.object(Path, "read_text", guarded_read),
        ):
            with self.assertRaises(ValueError):
                intake.resolve_target(self.root, "docs/courses/example/link.md")

    def test_unregistered_old_course_is_not_accepted(self):
        with self.assertRaises(ValueError):
            intake.resolve_target(self.root, "docs/mandatory/example/index.md")

    def test_migration_cannot_change_the_site_or_accept_traversal(self):
        addresses = (
            "https://evil.example/BMS/mandatory/old_example/",
            "http://example.org/BMS/mandatory/old_example/",
            "https://example.org/mandatory/old_example/",
            "https://example.org/BMS-copy/mandatory/old_example/",
            "https://example.org/BMS/mandatory/old_example/?redirect=elsewhere",
            "https://example.org/BMS/mandatory/old_example/../other/",
            "https://example.org/BMS/mandatory/%6Fld_example/",
            "https://example.org@evil.example/BMS/mandatory/old_example/",
            "https://example.org/BMS/elective/other/",
            "https://example.org/BMS/mandatory/old_\nexample/",
        )
        for address in addresses:
            with self.subTest(address=address), self.assertRaises(ValueError):
                intake.validate_selection(self.root, self.target,
                                          {**self.old_fields(), "页面地址": address})

    def test_flat_html_old_urls_are_supported_only_in_flat_html_mode(self):
        value = {**self.old_fields(),
                 "页面地址": "https://example.org/BMS/mandatory/old_example/index.html#notes"}
        with self.assertRaises(ValueError):
            intake.validate_selection(self.root, self.target, value)
        (self.root / "mkdocs.yml").write_text(
            "site_url: https://example.org/BMS/\nuse_directory_urls: false\n",
            encoding="utf-8")
        intake.validate_selection(self.root, self.target, value)

    def test_retained_quiz_targets_resolve_to_the_published_collection(self):
        old, retained, current = self.collection()
        self.assertEqual(catalog.normalize_page_path(self.root, old), current + "#quiz-1")
        for target in (old, retained, current):
            path, content = intake.resolve_target(self.root, "docs/" + target)
            self.assertEqual(path, self.root / "docs" / current)
            self.assertIn("Current collection", content)
        intake.validate_selection(
            self.root, "docs/" + current,
            {**base.fields(), "页面地址":
             "https://example.org/BMS/mandatory/old_example/quizzes/quiz-01/#old-heading"},
        )

    def test_course_ids_are_current_even_if_catalog_path_is_registered_old_name(self):
        (self.root / "data/courses.yml").write_text(
            "courses:\n- path: mandatory/old_example\n  chinese_name: 示例课程\n",
            encoding="utf-8")
        self.assertEqual(catalog.courses(self.root)[0]["id"], "courses/example")

    def test_prepare_preserves_submission_and_stores_only_canonical_target(self):
        submission = base.issue(self.old_fields())
        transport = Mock(side_effect=AssertionError("No actual network or model"))
        intake.prepare(self.root, "docs/" + self.old_source, submission,
                       self.output, base.environment(), transport)
        snapshot = json.loads((self.output / "snapshot.json").read_text(encoding="utf-8"))
        self.assertEqual(snapshot["target"], self.target)
        self.assertEqual(snapshot["issue"], submission)
        self.assertEqual(snapshot["fields"]["页面地址"], self.old_fields()["页面地址"])
        transport.assert_not_called()

    def test_frozen_approval_snapshot_uses_canonical_target_and_original_submission(self):
        submission = base.issue(self.old_fields())
        (self.root / security.POLICY_PATH).write_text(
            json.dumps(security.policy(base.REPO)), encoding="utf-8")
        repository = "Example/Repository"
        (self.root / runtime.CONFIG).write_text(
            json.dumps({"repository": repository, "real_calls_enabled": False}), encoding="utf-8")
        snapshot = security.freeze(
            self.root, "docs/" + self.old_source, submission,
            {"run_id": "10", "base_commit": "a" * 40},
            {**base.environment(), "GITHUB_REPOSITORY": repository}, repository,
        )
        self.assertEqual(snapshot["target"], self.target)
        self.assertEqual(snapshot["issue"], submission)
        self.assertEqual(snapshot["page_sha256"], intake.digest(self.original))
        self.assertEqual(snapshot["base_commit"], "a" * 40)

    def test_catalog_publishes_only_aliases_whose_final_page_was_rendered(self):
        config = SimpleNamespace(
            config_file_path=str(self.root / "mkdocs.yml"), site_dir=str(self.root / "site"),
            repo_url="https://github.com/Example/Repository",
        )
        contribution_links._courses[:] = catalog.courses(self.root)
        contribution_links._pages[:] = [
            {"path": self.new_source, "course": "courses/example", "title": "Example",
             "url": "https://example.org/BMS/courses/example/"},
            {"path": "guide/index.md", "course": "general", "title": "Guide",
             "url": "https://example.org/BMS/guide/"},
        ]
        contribution_links.on_post_build(config)
        data = json.loads((self.root / "site/contribute/catalog.json").read_text(encoding="utf-8"))
        self.assertEqual(data["aliases"][self.old_source], self.new_source)
        self.assertEqual(data["aliases"]["error.md"], "guide/index.md#finding-resources")
        self.assertNotIn("elective/other/index.md", data["aliases"])
        self.assertEqual(len(data["pages"]), 2)

    def test_cycles_and_invalid_paths_cannot_be_used_as_compatibility(self):
        for target in ("../outside.md", "https://example.org/a.md", "courses/example/index.md?x=1"):
            self.pages[self.old_source] = target
            self.write_manifest()
            with self.subTest(target=target), self.assertRaises(ValueError):
                intake.resolve_target(self.root, "docs/" + self.old_source)
        self.pages[self.old_source] = self.new_source
        self.pages[self.new_source] = self.old_source
        self.write_manifest()
        with self.assertRaises(ValueError):
            catalog.page_migrations(self.root)

    @unittest.skipUnless(shutil.which("node"), "Node is needed to execute the browser resolver")
    def test_browser_picker_selects_current_page_and_preserves_fragment(self):
        script = (base.REPO / "docs/assets/scripts/contribution-picker.js").read_text(encoding="utf-8")
        function = script[script.index("  function resolvePageReference("):
                          script.index("  async function mount()")]
        data = {"pages": [{"path": self.new_source, "url": "https://example.org/BMS/courses/example/"}],
                "aliases": {self.old_source: self.new_source + "#default"}}
        for request, fragment in (
            (self.old_source, "default"), ("docs/" + self.old_source + "#notes", "notes"),
            (self.new_source, ""),
        ):
            program = (function + "\nprocess.stdout.write(JSON.stringify(resolvePageReference("
                       + json.dumps(data) + "," + json.dumps(request) + ")));")
            result = subprocess.run(["node", "-e", program], check=True, capture_output=True, text=True)
            resolved = json.loads(result.stdout)
            self.assertEqual(resolved["page"]["path"], self.new_source)
            self.assertEqual(resolved["fragment"], fragment)


if __name__ == "__main__":
    unittest.main()
