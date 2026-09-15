"""Offline reproductions and compatibility checks for contribution markup."""
from copy import deepcopy
from pathlib import Path
import socket
import unittest
from unittest.mock import patch

import markdown
import yaml
from mkdocs.utils import meta

from scripts.contributions import markup


REPO = Path(__file__).resolve().parents[1]
TEXT_ONLY = {"本站使用范围": "允许整理文字并在本站展示, 附件仅作核对"}
WITH_ATTACHMENTS = {"本站使用范围": markup.ATTACHMENT_PERMISSION}
ATTACHMENT = "https://github.com/user-attachments/files/123/a.pdf"
FENCE = "\x60" * 3


def change(before, after):
    return {"before": before, "after": after}


class MarkupTests(unittest.TestCase):
    def setUp(self):
        # A regression may fail here, but may never make a real API request.
        self.network = patch.object(socket.socket, "connect",
                                    side_effect=AssertionError("network is forbidden"))
        self.network.start()
        self.addCleanup(self.network.stop)

    def check(self, original, before, after, fields=None):
        candidate = original.replace(before, after, 1)
        result = markup.validate_markup(
            original, candidate, TEXT_ONLY if fields is None else fields,
            [change(before, after)],
        )
        self.assertIsNone(result)
        return candidate

    def rejects(self, payload, fields=None):
        with self.assertRaises(ValueError):
            self.check("# Example\n\nOriginal text.\n", "Original text.", payload, fields)

    def test_existing_html_attribute_payload_is_rejected(self):
        original = '<nav class="course-links" aria-label="课程资料">正文</nav>'
        with self.assertRaisesRegex(ValueError, "现有 HTML"):
            self.check(original, 'class="course-links"',
                       'class="course-links" onmouseover="alert(1)"')

    def test_reference_url_payload_is_checked_in_complete_document(self):
        original = "[打开资料][notes]\n\n[notes]: https://example.org/notes\n"
        after = "jav&#x61;script:alert(1)"
        candidate = original.replace("https://example.org/notes", after)
        self.assertIn('href="jav&#x61;script:alert(1)"', markdown.markdown(candidate))
        with self.assertRaisesRegex(ValueError, "危险链接"):
            self.check(original, "https://example.org/notes", after)

    def test_real_extension_mismatch_payloads_are_rejected(self):
        for after in (
            '==文字=={ onmouseover="alert(1)" }',
            ':smile:{ onerror="alert(1)" }',
            ':material-book:{ onmouseover="alert(1)" }',
            '++ctrl++{ onmouseover="alert(1)" }',
        ):
            with self.subTest(after=after):
                # These were only plain text to intake's old "extra" renderer.
                self.assertNotIn("<mark", markdown.markdown(after, extensions=["extra"]))
                self.assertIn('on', markup._render(after))
                self.rejects(after)

    def test_all_mkdocs_metadata_forms_are_protected(self):
        originals = (
            "---\ntitle: Old\n---\nBody\n",
            "--- \ntitle: Old\n---\nBody\n",
            "---\ntitle: Old\n...\nBody\n",
            "title: Old\n\nBody\n",
        )
        for original in originals:
            with self.subTest(original=original):
                self.assertEqual(meta.get_data(original)[1], {"title": "Old"})
                with self.assertRaisesRegex(ValueError, "元数据"):
                    self.check(original, "title: Old", "title: New")
                self.check(original, "Body", "Updated body")

    def test_metadata_cannot_be_added_or_removed(self):
        with self.assertRaisesRegex(ValueError, "元数据"):
            self.check("# Example\n\nBody", "# Example",
                       "template: missing-audit-template.html\n\n# Example")
        original = "title: Old\n\nBody"
        with self.assertRaisesRegex(ValueError, "元数据"):
            self.check(original, "title: Old\n\n", "")

    def test_attachment_entity_payload_requires_permission(self):
        payload = "[附件](https://github.com/user&#45;attachments/files/123/a.pdf)"
        self.assertNotIn("user-attachments", payload)
        self.rejects(payload)
        self.check("# Example\n\nBody", "Body", payload, WITH_ATTACHMENTS)

    def test_attachment_normalization_and_legacy_hosts(self):
        urls = (
            ATTACHMENT,
            "https://github.com/user&#x2d;attachments/files/123/a.pdf",
            "https://github.com/user%2Dattachments/files/123/a.pdf",
            "https://github.com/user%252Dattachments/files/123/a.pdf",
            "HTTPS://GITHUB.COM:443/x/../user-attachments/files/123/a.pdf#page=2",
            "/user%2dattachments/files/123/a.pdf",
            "https://user-images.githubusercontent.com/1/example.png",
            "https://user-images.githubusercontent.com.:443/1/example.png",
            "https://ｕｓｅｒ-images.githubusercontent.com/1/example.png",
            "https://private-user-images.githubusercontent.com/1/example.png",
            "https://github.com/owner/repo/files/123/example.pdf",
        )
        for url in urls:
            with self.subTest(url=url):
                self.rejects(f"[附件]({url})")
                self.check("# Example\n\nBody", "Body", f"[附件]({url})", WITH_ATTACHMENTS)

    def test_existing_attachments_can_remain_but_not_be_duplicated(self):
        original = f"# Example\n\n[附件]({ATTACHMENT})\n\nBody"
        self.check(original, "Body", "Updated body")
        with self.assertRaisesRegex(ValueError, "附件"):
            self.check(original, "Body", f"[新增入口]({ATTACHMENT})")
        self.check(original, f"[附件]({ATTACHMENT})", "附件已移除")

    def test_attachment_link_cannot_become_image_without_permission(self):
        original = f"# Example\n\n[附件]({ATTACHMENT})"
        with self.assertRaisesRegex(ValueError, "附件"):
            self.check(original, "[附件]", "![附件]")

    def test_new_reference_attachment_and_emoji_src_are_checked(self):
        original = f"# Example\n\nBody\n\n[asset]: {ATTACHMENT}"
        with self.assertRaisesRegex(ValueError, "附件"):
            self.check(original, "Body", "[附件][asset]")
        self.rejects(':smile:{ src="https://github.com/user&#45;attachments/assets/123" }')

    def test_dangerous_and_decoded_urls(self):
        for url in (
            "javascript:alert(1)", "jav&#x61;script:alert(1)",
            "java&#9;script:alert(1)", "java%0Ascript:alert(1)",
            "%6a%61vascript%3Aalert(1)", "%256aavascript%253Aalert(1)",
            "data:text/html,hello", "vbscript:msgbox(1)", "file:///etc/passwd",
            "ftp://example.org/file", "//example.org/x", r"\\example.org/x",
            "%2f%2fexample.org/x", "https://user:password@example.org/x",
        ):
            with self.subTest(url=url):
                self.rejects(f'<a href="{url}">链接</a>')

    def test_active_html_and_attributes_are_rejected(self):
        for after in (
            "<script>alert(1)</script>", '<iframe src="https://example.org"></iframe>',
            '<object data="https://example.org"></object>', "<style>body{}</style>",
            '<base href="https://example.org">', '<meta http-equiv="refresh" content="0">',
            '<svg><foreignObject>text</foreignObject></svg>',
            '<svg><animate attributeName="href"></animate></svg>',
            '<svg><a xlink:href="jav&#x61;script:alert(1)">x</a></svg>',
            '<img src="x" ONERROR="alert(1)">', '<p style="background:url(x)">text</p>',
            '<p style="width:expression(alert(1))">text</p>',
            '<input type="submit" formaction="https://example.org">',
            '<img src="x" srcset="https://example.org/a 1x">',
            '<p id="one" id="two">text</p>',
            '<!--><img src="x" onerror="alert(1)">',
        ):
            with self.subTest(after=after):
                self.rejects(after)

    def test_existing_active_html_is_not_grandfathered(self):
        with self.assertRaises(ValueError):
            self.check('<script>alert(1)</script>\n\nBody', "Body", "Updated body")

    def test_existing_safe_tag_changes_are_conservatively_rejected(self):
        original = '<nav class="course-links">Body</nav>'
        with self.assertRaisesRegex(ValueError, "现有 HTML"):
            self.check(original, "course-links", "different-class")
        with self.assertRaisesRegex(ValueError, "现有 HTML"):
            self.check(original, "</nav>", "</div>")

    def test_cross_boundary_tag_assembly_is_rejected(self):
        for original, before, after in (
            ("< PLACEHOLDER >", " PLACEHOLDER ", "strong"),
            ("<TOKEN", "TOKEN", "img src=x>"),
        ):
            with self.subTest(original=original), self.assertRaisesRegex(ValueError, "边界"):
                self.check(original, before, after)
        with self.assertRaisesRegex(ValueError, "边界"):
            markup.validate_markup(
                "< TOKEN END>", "<img src=x>", TEXT_ONLY,
                [change(" TOKEN", "img"), change(" END", " src=x")],
            )

    def test_template_and_include_directives_stop_before_render(self):
        for after in (
            "{{ arbitrary }}", "{% include 'requirements.txt' %}", "{# secret #}",
            '--8<-- "requirements.txt"', '-8<- "requirements.txt"',
            "--8<--\nrequirements.txt\n--8<--",
            "{! requirements.txt !}", '!INCLUDE "requirements.txt"',
            ".. include:: requirements.txt", "include::requirements.txt[]",
            '<!--#include file="requirements.txt" -->',
        ):
            with self.subTest(after=after), patch.object(markup, "_render") as renderer:
                self.rejects(after)
                renderer.assert_not_called()
        with self.assertRaises(ValueError):
            self.check("{TOKEN}", "TOKEN", "{ arbitrary }")

    def test_safe_material_and_markdown_features(self):
        examples = (
            "## 标题\n\n普通 **粗体**、*斜体*、~~删除~~、==高亮==。\n\n"
            "> 引用\n\n- 第一项\n- 第二项\n\n[站外](https://example.org/notes)",
            "| 左 | 右 |\n| :--- | ---: |\n| a | b |",
            "!!! info \"提示\"\n\n    普通正文与 [站内](../other/index.md#notes)",
            "??? note \"展开\"\n\n    折叠正文",
            "???+ tip \"默认展开\"\n\n    折叠正文",
            '=== "第一栏"\n\n    内容一\n\n=== "第二栏"\n\n    内容二',
            ':smile: :material-book: ++ctrl++ ==文字=={ .highlight #safe-note }',
            "- [x] 完成\n- [ ] 待办",
            "说明[^1]\n\n[^1]: 脚注内容",
            "HTML\n\n*[HTML]: HyperText Markup Language",
            "术语\n: 定义",
            "H~2~O、x^2^、++alt+f4++、{++新增文字++}",
            "$x^2 + y^2$\n\n$$\n\\frac{a}{b}\n$$",
            FENCE + 'python\nprint("<tag>")\n' + FENCE,
            FENCE + "mermaid\ngraph LR\n  A --> B\n" + FENCE,
            '![说明](assets/diagram.png "图注")',
            '<div class="course-links" markdown="1">\n\n**安全正文**\n\n</div>',
            '[资料](https://example.org/a){ .course-link target="_blank" rel="noopener" }',
            "普通比较 a < b、c > d 与 " + "\x60" + "<tag>" + "\x60",
        )
        for after in examples:
            with self.subTest(after=after):
                self.check("# Example\n\nBody", "Body", after)

    def test_safe_existing_html_survives_text_changes(self):
        original = (
            '<!-- source-attribution: public source -->\n'
            '<nav class="course-links" aria-label="课程资料">'
            '<a class="course-link" href="exams/"><strong>旧说明</strong></a></nav>\n'
            '<div class="course-score" role="list"><div role="listitem">30%</div></div>'
        )
        self.check(original, "旧说明", "新说明")
        # A caller can supply a larger snippet if the actual tag text is intact.
        self.check(original, original, original.replace("旧说明", "新说明"))

    def test_real_course_components_and_metadata_regression(self):
        for relative in (
            "docs/courses/basic-pharmacology/index.md",
            "docs/courses/neuroscience/index.md",
            "docs/courses/cancer-biology/index.md",
        ):
            with self.subTest(relative=relative):
                original = (REPO / relative).read_text(encoding="utf-8")
                title = original.splitlines()[0]
                self.check(original, title, title + " (审阅样例)")

    def test_candidate_must_match_nonoverlapping_change_records(self):
        for candidate, changes in (
            ("Unreported edit", []),
            ("New", [change("Missing", "New")]),
            ("aNewc", [change("ab", "aNew"), change("bc", "Newc")]),
        ):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                markup.validate_markup("abc", candidate, TEXT_ONLY, changes)
        with self.assertRaises(ValueError):
            markup.validate_markup("abc", "abc", TEXT_ONLY, [{}])
        self.assertIsNone(markup.validate_markup("# Heading\n\nText", "# Heading\n\nText", TEXT_ONLY, []))

    def test_normal_autolinks_remain_editable(self):
        self.check("# Example\n\n<https://example.org/old>", "example.org/old", "example.org/new")

    def test_control_characters_cannot_inject_markdown_stash_tokens(self):
        for text in ("\x02wzxhzdk:0\x03", "\x00", "\x01czjqqkd:0\x04"):
            with self.subTest(text=text):
                self.rejects(text)

    def test_fixed_renderer_matches_site_config_without_loading_python_tags(self):
        class NamesOnly(yaml.SafeLoader):
            pass
        NamesOnly.add_multi_constructor(
            "tag:yaml.org,2002:python/name:", lambda loader, suffix, node: suffix,
        )
        config = yaml.load((REPO / "mkdocs.yml").read_text(encoding="utf-8"), Loader=NamesOnly)
        names, settings = [], {}
        for item in config["markdown_extensions"]:
            if isinstance(item, str):
                names.append(item)
            else:
                for name, options in item.items():
                    names.append(name)
                    settings[name] = options
        self.assertEqual(tuple(names), markup.SITE_EXTENSIONS)
        self.assertEqual(markup.MKDOCS_BUILTINS, ("toc", "tables", "fenced_code"))

        def named(value):
            if callable(value):
                return value.__module__ + "." + value.__name__
            if isinstance(value, dict):
                return {key: named(item) for key, item in value.items()}
            if isinstance(value, list):
                return [named(item) for item in value]
            return value
        self.assertEqual(settings, named(markup.TRUSTED_EXTENSION_CONFIGS))
        self.assertNotIn("pymdownx.snippets", markup.TRUSTED_EXTENSIONS)
        before = deepcopy(markup.TRUSTED_EXTENSION_CONFIGS)
        markup._render(":material-book: and a table")
        self.assertEqual(before, markup.TRUSTED_EXTENSION_CONFIGS)


if __name__ == "__main__":
    unittest.main()
