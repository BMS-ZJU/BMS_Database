"""Rendered page identity checks without building the whole website."""
from pathlib import Path
import sys
import unittest

from mkdocs.config import load_config
from mkdocs.structure.files import File, Files, get_files
from mkdocs.structure.pages import Page
from material.plugins.search.plugin import SearchIndex

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from hooks.page_identity import heading_title, on_env


ROOT = Path(__file__).resolve().parents[1]


class PageIdentityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = load_config(str(ROOT / "mkdocs.yml"))
        cls.config.plugins.on_startup(command="build", dirty=False)

    def render_pages(self, entries):
        files = Files([])
        link_targets = get_files(self.config)
        for path, nav_title, content in entries:
            file = File.generated(self.config, path, content=content)
            files.append(file)
            Page(nav_title, file, self.config)
            previous = link_targets.get_file_from_path(path)
            if previous is not None:
                link_targets.remove(previous)
            link_targets.append(file)
        for file in files:
            file.page.read_source(self.config)
            file.page.render(self.config, link_targets)
        before = {file.src_uri: file.page.content for file in files}
        on_env(None, self.config, Files(files))
        for file in files:
            self.assertEqual(file.page.content, before[file.src_uri])
        return list(files)

    def real(self, path, nav_title):
        return path, nav_title, (ROOT / "docs" / path).read_text(encoding="utf-8")

    def html_title(self, page):
        env = self.config.theme.get_env()
        template = env.get_template("base.html")
        context = template.new_context({"config": self.config, "page": page})
        return "".join(template.blocks["htmltitle"](context)).strip()

    def test_course_title_and_short_navigation_are_independent(self):
        path = "mandatory/medical_science_literacy_2/index.md"
        page = self.render_pages([self.real(path, "课程主页")])[0].page
        self.assertEqual(page.title, "课程主页")
        self.assertEqual(page.meta["title"], "医学科学素养Ⅱ")
        self.assertEqual(self.html_title(page), "<title>医学科学素养Ⅱ - BMS Database</title>")
        # Search keeps the already-complete H1, including the course identity.
        search = SearchIndex(lang=["zh"])
        search.add_entry_from_context(page)
        self.assertEqual(search.entries[0]["title"].replace("\u200b", ""), "医学科学素养Ⅱ")

    def test_intro_before_h1_does_not_turn_into_the_document_title(self):
        files = self.render_pages([(
            "mandatory/example/index.md", "课程主页",
            '!!! info "说明"\n\n    一段说明\n\n# 示例课程\n',
        )])
        self.assertEqual(files[0].page.meta["title"], "示例课程")

    def test_explicit_exam_identity_is_kept(self):
        path = "mandatory/medical_science_literacy_2/exams/2025-2026-final-exam-recall.md"
        page = self.render_pages([self.real(path, "2025-2026 秋期末回忆卷")])[0].page
        expected = "医学科学素养Ⅱ 2025-2026 学年秋学期期末回忆卷"
        self.assertEqual(page.meta["title"], expected)
        self.assertEqual(page.title, "2025-2026 秋期末回忆卷")
        self.assertEqual(self.html_title(page), f"<title>{expected} - BMS Database</title>")

    def test_group_and_quiz_without_explicit_title_use_complete_h1(self):
        for path, nav_title, expected in (
            ("mandatory/medical_science_literacy_2/exams/index.md", "考试资料", "医学科学素养Ⅱ考试资料"),
            ("mandatory/the_basis_for_human_diseases/quizzes/2025-2026-quiz-01.md", "小测 1",
             "2025-2026 学年秋冬学期疾病基础小测 1"),
        ):
            with self.subTest(path=path):
                page = self.render_pages([self.real(path, nav_title)])[0].page
                self.assertEqual(page.meta["title"], expected)
                self.assertEqual(page.title, nav_title)

    def test_anatomy_keeps_material_name_and_adds_confirmed_course(self):
        home = "mandatory/structure_and_function_of_the_human_body/index.md"
        source = "mandatory/structure_and_function_of_the_human_body/quizzes/2025-2026-summer-anatomy-test.md"
        # Child-first ordering proves this does not depend on render order.
        files = self.render_pages([self.real(source, "2025-2026 夏回忆整理"), self.real(home, "课程主页")])
        title = "人体结构与功能学 · 2025-2026 学年夏学期解剖学实验考试（回忆整理）"
        self.assertEqual(files[0].page.meta["title"], title)
        self.assertEqual(files[0].page.title, "2025-2026 夏回忆整理")
        on_env(None, self.config, Files(files))
        self.assertEqual(files[0].page.meta["title"], title)

    def test_discussion_adds_course_but_no_unknown_year(self):
        home = "mandatory/basic_pharmacology/index.md"
        path = "mandatory/basic_pharmacology/discussions/01-central-nervous-system.md"
        files = self.render_pages([self.real(path, "第一次讨论课"), self.real(home, "课程主页")])
        self.assertEqual(files[0].page.meta["title"], "基础药理学 · 第一次讨论课：中枢神经系统药理")

    def test_historical_independent_course_does_not_inherit_archive_course(self):
        home = "mandatory/medical_life_fundamentals/index.md"
        path = "mandatory/medical_life_fundamentals/exams/2020-2021-deferred-exam-recall.md"
        files = self.render_pages([self.real(home, "课程主页"), self.real(path, "2020-2021 缓考回忆卷")])
        self.assertEqual(files[1].page.meta["title"], "生命科学基础 2020-2021 学年缓考回忆卷")

    def test_information_page_does_not_inherit_course_context(self):
        files = self.render_pages([("guide/index.md", "说明", "# 使用说明\n\n正文")])
        self.assertEqual(files[0].page.meta["title"], "使用说明")
        self.assertEqual(files[0].page.title, "说明")

    def test_missing_h1_does_not_guess_identity_from_file_or_navigation(self):
        files = self.render_pages([("guide/untitled.md", "短名称", "仅有正文")])
        self.assertNotIn("title", files[0].page.meta)

    def test_heading_text_excludes_permalink_hidden_text_and_markup(self):
        content = ('<p>引言</p><h1 id="course">医学<strong>科学</strong>素养Ⅱ '
                   '&amp; R<a class="headerlink" href="#course">¶</a>'
                   '<span aria-hidden="true"><img alt="隐藏图片"/><b>隐藏</b></span></h1><h1>第二个标题</h1>')
        self.assertEqual(heading_title(content), "医学科学素养Ⅱ & R")


if __name__ == "__main__":
    unittest.main()
