"""Path migration contracts, including actual redirect script execution."""
from html import unescape
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest

from mkdocs.structure.files import File, Files

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from hooks import path_migrations as migrations


class PathMigrationTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        (self.root / "data").mkdir()
        (self.root / "docs").mkdir()
        (self.root / "site").mkdir()
        self.config = SimpleNamespace(
            config_file_path=str(self.root / "mkdocs.yml"),
            docs_dir=str(self.root / "docs"), site_dir=str(self.root / "site"),
            use_directory_urls=True, site_url="https://example.test/BMS_Database/",
        )

    def mapping(self, pages=None, assets=None, source_files=None):
        data = {"version": 1, "pages": pages or {}, "assets": assets or {},
                "source_files": source_files or {}}
        (self.root / migrations.MAPPING_PATH).write_text(json.dumps(data), encoding="utf-8")
        migrations.on_pre_build(self.config)
        return data

    def built(self, source, content=b"<html><body>Current page</body></html>"):
        file = File(source, self.config.docs_dir, self.config.site_dir,
                    self.config.use_directory_urls)
        path = self.root / "site" / file.dest_uri
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        return file

    def output(self, source):
        return self.root / "site" / File(
            source, self.config.docs_dir, self.config.site_dir,
            self.config.use_directory_urls).dest_uri

    def test_pages_and_assets_are_created_without_search_entries(self):
        self.mapping(
            {"mandatory/example/index.md": "courses/example/index.md"},
            {"css/example.css": "assets/styles/example.css",
             "css/fonts/example.woff2": "assets/styles/fonts/example.woff2"},
        )
        page = self.built("courses/example/index.md")
        css = self.built("assets/styles/example.css", b"src:url(fonts/example.woff2)")
        font = self.built("assets/styles/fonts/example.woff2", b"\x00\x01original-font")
        files = Files([page, css, font])
        returned = migrations.on_files(files, self.config)
        migrations.on_post_build(self.config)
        self.assertIs(returned, files)
        self.assertEqual(len(files), 3)
        html = self.output("mandatory/example/index.md").read_text(encoding="utf-8")
        self.assertIn('name="robots" content="noindex,follow"', html)
        self.assertIn('href="https://example.test/BMS_Database/courses/example/"', html)
        self.assertIn('name="resource-export-source" content="../../courses/example/"', html)
        self.assertIn("../assets/styles/example.css", self.output("css/example.css").read_text(encoding="utf-8"))
        self.assertEqual(self.output("css/fonts/example.woff2").read_bytes(),
                         b"\x00\x01original-font")

    def test_only_unique_whole_page_moves_inherit_comment_identity(self):
        self.mapping({
            "mandatory/example/index.md": "courses/example/index.md",
            "mandatory/index.md": "courses/index.md",
            "elective/index.md": "courses/index.md",
            "error.md": "guide/index.md#finding-resources",
        })
        page = SimpleNamespace(
            file=SimpleNamespace(src_uri="courses/example/index.md"), meta={})
        original = "# Example\n\nAuthor's text."
        self.assertEqual(migrations.on_page_markdown(original, page, self.config, None), original)
        self.assertEqual(page.meta["legacy_comment_path"],
                         "/BMS_Database/mandatory/example/")
        self.assertIsNone(migrations.legacy_comment_path("courses/index.md", self.config))
        self.assertIsNone(migrations.legacy_comment_path("guide/index.md", self.config))

    def test_comment_helper_works_without_hook_module_state(self):
        self.mapping({"mandatory/course/quizzes/quiz-01.md": "courses/course/quizzes/quiz-01.md"})
        migrations._migrations = None
        self.assertEqual(
            migrations.legacy_comment_path("courses/course/quizzes/quiz-01.md", self.config),
            "/BMS_Database/mandatory/course/quizzes/quiz-01/",
        )

    def test_flat_html_urls_are_supported(self):
        self.config.use_directory_urls = False
        self.mapping({"old/index.md": "courses/example/index.md"})
        self.built("courses/example/index.md")
        migrations.on_post_build(self.config)
        html = self.output("old/index.md").read_text(encoding="utf-8")
        self.assertIn('content="../courses/example/index.html"', html)
        self.assertEqual(migrations.legacy_comment_path("courses/example/index.md", self.config),
                         "/BMS_Database/old/index.html")

    def test_existing_generated_literacy_quiz_urls_are_in_the_real_manifest(self):
        # These three URLs came from resource_aliases, so git ls-files alone
        # cannot enumerate the public routes which need migration.
        root = Path(__file__).resolve().parents[1]
        config = SimpleNamespace(**vars(self.config))
        config.config_file_path = str(root / "mkdocs.yml")
        config.docs_dir = str(root / "docs")
        data = migrations.load_migrations(config)
        for name in ("online-quizzes", "offline-quizzes", "practice-and-examples"):
            old = f"mandatory/medical_science_literacy_2/quizzes/{name}.md"
            current = f"courses/medical-science-literacy-2/quizzes/{name}.md"
            with self.subTest(name=name):
                self.assertEqual(data["pages"].get(old), current)
                self.assertEqual(
                    migrations.legacy_comment_path(current, config),
                    f"/BMS_Database/mandatory/medical_science_literacy_2/quizzes/{name}/",
                )

    def test_generated_resource_alias_can_be_a_migration_target(self):
        self.mapping({"mandatory/course/quizzes/quiz-01.md": "courses/course/quizzes/quiz-01.md"})
        # resource_aliases generates this file after the normal page pipeline.
        self.built("courses/course/quizzes/quiz-01.md",
                   b'<meta name="resource-export-source" content="../2025-2026-quizzes/#quiz-1">')
        migrations.on_post_build(self.config)
        self.assertTrue(self.output("mandatory/course/quizzes/quiz-01.md").is_file())

    @unittest.skipUnless(shutil.which("node"), "Node is needed to execute the redirect script")
    def test_redirect_preserves_query_and_user_fragment(self):
        html = migrations.redirect_html("error.md", "guide/index.md#finding-resources", self.config)
        script = re.search(r"<script>(.*?)</script>", html)[1]
        for suffix, expected in (
            ("", "https://example.test/BMS_Database/guide/#finding-resources"),
            ("?source=a%2Fb&comments=1",
             "https://example.test/BMS_Database/guide/?source=a%2Fb&comments=1#finding-resources"),
            ("?view=all#existing-anchor",
             "https://example.test/BMS_Database/guide/?view=all#existing-anchor"),
        ):
            with self.subTest(suffix=suffix):
                program = (
                    "const vm=require('vm');"
                    "const original=new URL(" + json.dumps(
                        "https://example.test/BMS_Database/error/" + suffix) + ");"
                    "const location={href:original.href,search:original.search,hash:original.hash,"
                    "replace:value=>process.stdout.write(value)};"
                    "vm.runInNewContext(" + json.dumps(script) + ",{URL,location});"
                )
                result = subprocess.run(["node", "-e", program], check=True,
                                        capture_output=True, text=True)
                self.assertEqual(result.stdout, expected)

    def test_redirect_escapes_html_and_script_sensitive_fragment(self):
        html = migrations.redirect_html(
            "old.md", 'guide/index.md#</script><script>alert("x")</script>', self.config)
        self.assertEqual(html.count("<script>"), 1)
        self.assertEqual(html.count("</script>"), 1)
        self.assertIn("\\u003c", html)
        content = re.search(r'name="resource-export-source" content="([^"]*)"', html)[1]
        self.assertEqual(unescape(content),
                         '../guide/#</script><script>alert("x")</script>')

    def test_runtime_output_cannot_overwrite_source_asset(self):
        self.mapping()
        runtime = self.built("assets/path-migrations.json", b"original")
        with self.assertRaisesRegex(ValueError, "runtime.*canonical"):
            migrations.on_files(Files([runtime]), self.config)
        self.assertEqual(self.output("assets/path-migrations.json").read_bytes(), b"original")

    def test_runtime_output_cannot_overwrite_other_hook_output(self):
        self.mapping()
        self.built("assets/path-migrations.json", b"original")
        with self.assertRaisesRegex(ValueError, "runtime.*existing"):
            migrations.on_post_build(self.config)
        self.assertEqual(self.output("assets/path-migrations.json").read_bytes(), b"original")

    def test_canonical_outputs_cannot_be_overwritten(self):
        self.mapping({"old.md": "new.md"})
        canonical = self.built("old.md")
        with self.assertRaisesRegex(ValueError, "canonical"):
            migrations.on_files(Files([canonical]), self.config)

    def test_two_source_spellings_cannot_claim_the_same_output(self):
        self.mapping({"old.md": "new.md", "old/index.md": "new.md"})
        with self.assertRaisesRegex(ValueError, "collision"):
            migrations.on_files(Files([]), self.config)

    def test_asset_cannot_claim_redirect_output(self):
        self.mapping({"old.md": "new.md"}, {"old/index.html": "assets/page.html"})
        with self.assertRaisesRegex(ValueError, "collision"):
            migrations.on_files(Files([]), self.config)

    def test_existing_generated_output_cannot_be_overwritten(self):
        self.mapping({"old.md": "new.md"})
        self.built("new.md")
        self.built("old.md", b"generated-by-another-hook")
        with self.assertRaisesRegex(ValueError, "overwrite existing"):
            migrations.on_post_build(self.config)
        self.assertEqual(self.output("old.md").read_bytes(), b"generated-by-another-hook")

    def test_missing_target_stops_the_batch_before_any_compatibility_writes(self):
        self.mapping({"old.md": "new.md"}, {"old.png": "missing.png"})
        self.built("new.md")
        with self.assertRaisesRegex(ValueError, "Asset migration target was not built"):
            migrations.on_post_build(self.config)
        self.assertFalse(self.output("old.md").exists())

    def test_missing_page_target_fails(self):
        self.mapping({"old.md": "missing.md"})
        with self.assertRaisesRegex(ValueError, "Page migration target was not built"):
            migrations.on_post_build(self.config)

    def test_chains_are_resolved_and_first_fragment_is_preserved(self):
        self.mapping({"old.md": "middle.md#chosen", "middle.md": "new.md#default"},
                     {"old.png": "middle.png", "middle.png": "new.png"})
        loaded = migrations.load_migrations(self.config)
        self.assertEqual(loaded["pages"]["old.md"], "new.md#chosen")
        self.assertEqual(loaded["assets"]["old.png"], "new.png")

    def test_cycles_are_rejected_in_all_mapping_groups(self):
        for group in ("pages", "assets", "source_files"):
            with self.subTest(group=group):
                with self.assertRaisesRegex(ValueError, "cycle"):
                    self.mapping(**{group: {"a.md": "b.md", "b.md": "a.md"}})

    def test_absolute_traversal_encoded_and_query_paths_are_rejected(self):
        invalid = ("/outside.md", "../outside.md", "course/../outside.md",
                   "course//outside.md", r"C:\outside.md", "https://example.test/a.md",
                   "course\\outside.md", "course/%2e%2e/a.md", "course/a.md?query=1",
                   "a\x00.md")
        for path in invalid:
            with self.subTest(path=path):
                with self.assertRaisesRegex(ValueError, "Invalid migration"):
                    self.mapping({path: "new.md"})
                with self.assertRaisesRegex(ValueError, "Invalid migration"):
                    self.mapping({"old.md": path})

    def test_duplicate_json_keys_and_unsupported_versions_are_rejected(self):
        path = self.root / migrations.MAPPING_PATH
        path.write_text('{"version":1,"pages":{"old.md":"a.md","old.md":"b.md"},'
                        '"assets":{},"source_files":{}}', encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            migrations.load_migrations(self.config)
        path.write_text('{"version":true,"pages":{},"assets":{},"source_files":{}}',
                        encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "version"):
            migrations.load_migrations(self.config)

    def test_case_collisions_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "Ambiguous"):
            self.mapping({"OLD.md": "a.md", "old.md": "b.md"})

    def test_resolved_paths_stay_inside_the_output_root(self):
        with self.assertRaisesRegex(ValueError, "escapes"):
            migrations._inside(self.root / "site", "../outside")


if __name__ == "__main__":
    unittest.main()
