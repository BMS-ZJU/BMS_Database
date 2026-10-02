"""Page-end navigation must stay inside the reader's course or handbook."""
from pathlib import Path
from types import SimpleNamespace
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from hooks.footer_navigation import on_page_context


def page(source, nav_title="导航短名", **metadata):
    url = source.removesuffix("index.md").removesuffix(".md")
    return SimpleNamespace(file=SimpleNamespace(src_uri=source), url=url,
                           title=nav_title, meta=metadata,
                           previous_page=None, next_page=None)


def navigation(current, *pages):
    context = on_page_context({}, current, None, SimpleNamespace(pages=pages))
    return context["bms_footer"]


class FooterNavigationTests(unittest.TestCase):
    def test_indexes_and_standalone_pages_have_no_sequential_navigation(self):
        for source in ("index.md", "courses/index.md", "courses/a/index.md",
                       "courses/a/exams/index.md", "feiyue/index.md",
                       "contribute/editing.md", "zijingang/course-selection.md"):
            with self.subTest(source=source):
                current = page(source)
                current.next_page = page("courses/b/index.md")
                self.assertEqual(navigation(current), {})

    def test_nested_resource_uses_nearest_index_and_complete_identity(self):
        current = page("courses/a/exams/anatomy/exam.md")
        course = page("courses/a/index.md", title="示例课程")
        group = page("courses/a/exams/index.md", title="示例课程考试资料")
        target = navigation(current, course, group)["return_to"]
        self.assertEqual(target, {"url": group.url, "title": "示例课程考试资料"})
        nested = page("courses/a/exams/anatomy/index.md", title="解剖考试资料")
        self.assertEqual(navigation(current, course, group, nested)["return_to"]["url"], nested.url)

    def test_missing_group_falls_back_to_course_homepage(self):
        current = page("courses/a/assessment/task.md")
        course = page("courses/a/index.md", title="示例课程")
        self.assertEqual(navigation(current, course)["return_to"]["title"], "示例课程")

    def test_missing_course_does_not_link_to_global_or_another_course_index(self):
        self.assertEqual(navigation(page("courses/a/exams/exam.md"),
                                    page("courses/index.md"), page("courses/b/index.md")), {})

    def test_short_index_label_does_not_replace_complete_page_title(self):
        index = page("courses/a/quizzes/index.md", title="示例课程小测资料")
        self.assertEqual(navigation(page("courses/a/quizzes/quizzes.md"), index)
                         ["return_to"]["title"], "示例课程小测资料")

    def test_handbook_links_stop_at_section_boundaries(self):
        current = page("feiyue/preface.md")
        current.previous_page = page("rotation/index.md")
        current.next_page = page("feiyue/anonymous.md")
        self.assertEqual(navigation(current), {"next": current.next_page})
        current.previous_page = page("feiyue/anonymous.md")
        current.next_page = page("courses/a/index.md")
        self.assertEqual(navigation(current), {"previous": current.previous_page})

    def test_explicit_hide_suppresses_both_navigation_types(self):
        for source in ("courses/a/exams/exam.md", "feiyue/anonymous.md"):
            current = page(source, hide=["footer"])
            current.next_page = page("feiyue/cai-chenxi.md")
            self.assertEqual(navigation(current, page("courses/a/exams/index.md")), {})


if __name__ == "__main__":
    unittest.main()
