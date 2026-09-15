"""Exercise the exporter's real URL validator across the directory migration."""
import json
from pathlib import Path
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]


class ExportMigrationTests(unittest.TestCase):
    def test_registered_migrations_preserve_scope_and_reject_unregistered_urls(self):
        text = (ROOT / "docs/assets/scripts/resource-export-view.js").read_text(encoding="utf-8")
        validator = text[text.index("  const validateSource ="):text.index("  const sourceIndex =")]
        script = """
const siteRoot = new URL("https://example.org/BMS_Database/");
const location = siteRoot;
const sourceError = "invalid source";
let pathMigrations = {
 "mandatory/example_course/exams/2024-final/": "courses/example-course/exams/2024-final/",
 "mandatory/example_course/quizzes/2024-anatomy/": "courses/example-course/exams/2024-anatomy/",
 "mandatory/example_course/quizzes/quiz-01/": "courses/example-course/quizzes/quiz-01/"
};
""" + validator + """
const cases = [
 ["mandatory/example_course/exams/2024-final/#q1", "courses/example-course/exams/2024-final/#q1"],
 ["mandatory/example_course/quizzes/2024-anatomy/", "courses/example-course/exams/2024-anatomy/"],
 ["mandatory/example_course/quizzes/quiz-01/", "courses/example-course/quizzes/quiz-01/"],
 ["courses/example-course/exams/2024-final/", "courses/example-course/exams/2024-final/"]
];
for (const [source, target] of cases) {
 if (validateSource(source).href !== new URL(target, siteRoot).href) throw Error(source);
}
for (const bad of [
 "mandatory/unknown/exams/2024-final/", "https://evil.example/courses/a/exams/b/",
 "../courses/a/exams/b/", "courses/a/exams/", "courses/a/exams/index.html",
 "courses/a/exams/b/?redirect=elsewhere", "courses/a/exams/b/#bad fragment",
 "courses/a/exams/a%2fb/", "courses/a/exams/%252e%252e/", "javascript:alert(1)"
]) {
 let rejected = false; try { validateSource(bad); } catch { rejected = true; }
 if (!rejected) throw Error("accepted: " + bad);
}
pathMigrations["courses/a/exams/b/"] = "https://evil.example/courses/a/exams/c/";
try { validateSource("courses/a/exams/b/"); throw Error("external accepted"); }
catch (e) { if (e.message === "external accepted") throw e; }
pathMigrations["courses/a/exams/b/"] = "courses/a/exams/b/";
try { validateSource("courses/a/exams/b/"); throw Error("cycle accepted"); }
catch (e) { if (e.message === "cycle accepted") throw e; }
console.log("export migration boundaries passed");
"""
        result = subprocess.run(["node", "-e", script], text=True, encoding="utf-8", capture_output=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
