"""Print notices preserve each resource's usage scope without relying on links."""
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from xml.etree import ElementTree

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from hooks.resource_usage import on_page_content


class ResourceUsageTests(unittest.TestCase):
    def render(self, meta=None, name="paper"):
        page = SimpleNamespace(
            file=SimpleNamespace(src_uri=f"courses/example/exams/{name}.md", name=name),
            url=f"courses/example/exams/{name}/", canonical_url=None, meta=meta or {},
        )
        config = SimpleNamespace(site_url="https://example.org/BMS_Database/")
        files = SimpleNamespace(get_file_from_path=lambda _: SimpleNamespace(
            url="contribute/sources-and-permissions/"))
        html = on_page_content("<h1>示例资料</h1><p>原始题目</p>", page, config, files)
        return ElementTree.fromstring(f"<article>{html}</article>")

    def print_notice(self, article):
        notice = article.find(".//p[@class='resource-use-print']")
        self.assertIsNotNone(notice)
        self.assertIsNone(notice.find(".//a"), "printed meaning must not depend on a link")
        return "".join(notice.itertext())

    def test_default_print_has_actionable_guidance_without_assigning_a_licence(self):
        article = self.render()
        text = self.print_notice(article)
        for required in ("请保留原有署名、来源和使用说明", "请核对具体材料的许可", "本站不提供商业使用授权"):
            self.assertIn(required, text)
        self.assertNotIn("禁止商业使用", text)
        reading = article.find(".//p[@class='resource-use-reading']")
        self.assertEqual("".join(reading.itertext()), "资料免费获取 · 欢迎分享本站链接 · 使用限制")
        footer = article.find(".//footer")
        self.assertTrue(all(a.get("href").startswith("https://example.org/BMS_Database/") for a in footer.iter("a")))
        self.assertIn("原始题目", "".join(article.itertext()))

    def test_site_policy_keeps_its_explicit_restrictions_and_exception(self):
        article = self.render({"resource_usage": "site-policy"})
        self.assertEqual(self.print_notice(article), "欢迎分享本站链接 · 全文转载、文件重传须经许可 · 禁止商业使用")
        self.assertIn("具体材料的既有许可与原有要求仍适用。", "".join(article.itertext()))

    def test_source_restriction_is_preserved_and_escaped(self):
        note = '作者限定 "个人学习"；A & B <不得重传>'
        article = self.render({"resource_usage": "source-restriction", "resource_usage_note": note})
        self.assertEqual(self.print_notice(article), note)
        self.assertNotIn("本站不提供商业使用授权", self.print_notice(article))

    def test_resource_index_has_no_notice(self):
        article = self.render(name="index")
        self.assertIsNone(article.find(".//div"))
        self.assertIsNone(article.find(".//footer"))


if __name__ == "__main__":
    unittest.main()
