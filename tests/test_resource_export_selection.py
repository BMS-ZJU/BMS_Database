"""Regression checks for export choices surviving URL updates and refreshes."""
from pathlib import Path
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]


class ExportSelectionTests(unittest.TestCase):
    def run_javascript(self, checks):
        text = (ROOT / "docs/assets/scripts/resource-export-view.js").read_text(encoding="utf-8")
        helpers = text[text.index("  const validateSource ="):text.index("  const namespaceReferences =")]
        script = """
const assert = require("node:assert/strict");
const siteRoot = new URL("https://example.org/BMS_Database/");
let location = new URL("resource-export.html", siteRoot);
const sourceError = "invalid source";
let pathMigrations = {};
const source = (name) => new URL(`courses/example-course/exams/${name}/`, siteRoot);
const unit = (url, selected = true) => ({ sourceUrl: url, selected });
const hrefs = (urls) => urls.map((url) => url.href);
const sorted = (values) => Array.from(values).sort();
const openExport = (sources, params = []) => {
  location = new URL("resource-export.html", siteRoot);
  sources.forEach((url) => location.searchParams.append("source", url.pathname + url.hash));
  params.forEach(([key, value]) => location.searchParams.append(key, value));
};
""" + helpers + checks
        result = subprocess.run(["node", "-e", script], text=True, encoding="utf-8", capture_output=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_deselected_paper_remains_available_after_refresh(self):
        self.run_javascript("""
const sources = [source("paper-a"), source("paper-b"), source("paper-c")];
const units = sources.map((url) => unit(url));
openExport(sources, [["answer", "end"], ["view", "compact"]]);
location = new URL(selectionUrl(getSources(), [units[0], units[2]]));
assert.deepEqual(hrefs(getSources()), hrefs(sources), "refresh must still load all three papers");
assert.deepEqual(sorted(getInitialSelection(units)), sorted([sources[0].href, sources[2].href]));
assert.equal(location.searchParams.get("answer"), "end");
assert.equal(location.searchParams.get("view"), "compact");
assert.equal(location.searchParams.has("select"), false);
""")

    def test_empty_selection_and_select_all_round_trip(self):
        self.run_javascript("""
const sources = [source("paper-a"), source("paper-b"), source("paper-c")];
const units = sources.map((url) => unit(url));
openExport(sources, [["selected", sources[0].pathname]]);
location = new URL(selectionUrl(getSources(), []));
assert.deepEqual(hrefs(getSources()), hrefs(sources));
assert.equal(location.searchParams.get("select"), "none");
assert.equal(location.searchParams.has("selected"), false, "empty state must clear stale choices");
assert.deepEqual(Array.from(getInitialSelection(units)), []);
location = new URL(selectionUrl(getSources(), units));
assert.deepEqual(hrefs(getSources()), hrefs(sources));
assert.equal(location.searchParams.has("select"), false, "select all must clear the empty state");
assert.deepEqual(sorted(getInitialSelection(units)), sorted(hrefs(sources)));
""")

    def test_existing_links_keep_their_original_default_selection(self):
        self.run_javascript("""
const sources = [source("paper-a"), source("paper-b"), source("paper-c")];
const units = [unit(sources[0]), unit(sources[1], false), unit(sources[2])];
openExport(sources);
assert.deepEqual(sorted(getInitialSelection(units)), sorted([sources[0].href, sources[2].href]));
location.searchParams.set("select", "none");
assert.deepEqual(Array.from(getInitialSelection(units)), []);
""")

    def test_collection_sections_keep_original_source_and_selected_section(self):
        self.run_javascript("""
const collection = new URL("courses/example-course/quizzes/2025-2026-quizzes/", siteRoot);
const request = new URL("#group-one", collection);
const units = [
  unit(new URL("#quiz-one", collection)),
  unit(new URL("#quiz-two", collection)),
  unit(new URL("#quiz-three", collection), false),
];
openExport([request]);
assert.deepEqual(sorted(getInitialSelection(units)), sorted(hrefs(units.slice(0, 2).map((item) => item.sourceUrl))));
location = new URL(selectionUrl(getSources(), [units[2]]));
assert.deepEqual(hrefs(getSources()), [request.href], "selected sections must not replace the collection source");
assert.deepEqual(Array.from(getInitialSelection(units)), [units[2].sourceUrl.href]);
location = new URL(selectionUrl(getSources(), [units[0], units[2]]));
assert.deepEqual(hrefs(getSources()), [request.href]);
assert.deepEqual(sorted(getInitialSelection(units)), sorted([units[0].sourceUrl.href, units[2].sourceUrl.href]));
""")

    def test_selected_urls_must_be_valid_and_present_in_available_units(self):
        self.run_javascript("""
const sources = [source("paper-a"), source("paper-b")];
const units = sources.map((url) => unit(url));
for (const invalid of [
  "https://evil.example/BMS_Database/courses/example-course/exams/paper-a/",
  source("paper-c").href,
  sources[0].href + "#missing-section",
  "courses/another-course/exams/paper-a/",
  "javascript:alert(1)",
  "",
]) {
  openExport(sources, [["selected", invalid]]);
  assert.throws(() => getInitialSelection(units), undefined, `accepted invalid choice: ${invalid}`);
}
openExport(sources, [["selected", sources[0].pathname], ["selected", sources[0].href]]);
assert.deepEqual(Array.from(getInitialSelection(units)), [sources[0].href], "duplicate spellings must select once");
""")

    def test_regular_paper_anchor_survives_empty_and_reselected_states(self):
        self.run_javascript("""
const request = new URL("#section-one", source("paper-a"));
const units = [unit(request)];
openExport([request], [["answer", "questions"]]);
const original = request.href;
location = new URL(selectionUrl(getSources(), []));
assert.deepEqual(hrefs(getSources()), [original], "empty selection must preserve a regular paper's source anchor");
assert.deepEqual(Array.from(getInitialSelection(units)), []);
location = new URL(selectionUrl(getSources(), units));
assert.deepEqual(hrefs(getSources()), [original]);
assert.deepEqual(Array.from(getInitialSelection(units)), [original]);
assert.equal(location.searchParams.get("answer"), "questions");
assert.equal(request.href, original, "serializing selection must not mutate source objects");
""")


if __name__ == "__main__":
    unittest.main()
