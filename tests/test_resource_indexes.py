"""Directory first paint must not depend on JavaScript or change export scope."""
from pathlib import Path
from types import SimpleNamespace
import sys
import unittest
from urllib.parse import parse_qs, urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "hooks"))
from resource_indexes import Fragment, on_page_content


class ResourceIndexTests(unittest.TestCase):
    def render(self, html, source="courses/demo/exams/index.md", site="https://example.org/BMS_Database/"):
        page = SimpleNamespace(file=SimpleNamespace(src_uri=source), url=source.removesuffix("index.md"))
        return on_page_content(html, page, SimpleNamespace(site_url=site), None)

    def test_static_layout_preserves_links_badges_notes_and_source_comments(self):
        html = '''<h1 id="title">目录</h1><!-- source-attribution: A & B -->
<div class="grid cards course-resource-grid"><ul><li>
<p><strong>资料 <em>A &amp; B</em></strong> <span class="exam-resource-tag">老师版</span></p>
<hr />
<p><a class="resource-practice-link" target="_blank" href="https://example.net/?a=1&amp;b=2">练习</a></p>
<p><!-- keep --><a class="resource-read-link" href="paper/">查看资料</a> · <a href="paper/?view=original">原帖</a></p>
<p>说明 <a href="https://example.net/source">来源</a></p>
</li></ul></div>'''
        output = self.render(html)
        tree = Fragment(output).root
        nodes = list(tree.walk())
        self.assertEqual(sum(n.has_class("resource-export-index") for n in nodes), 1)
        actions = next(n for n in nodes if n.has_class("resource-index-actions"))
        self.assertEqual([n.attrs['href'] for n in actions.elements('a')],
                         ['paper/', 'https://example.net/?a=1&b=2', 'paper/?view=original'])
        self.assertEqual(output.count('class="divider"'), 2)
        title = next(n for n in nodes if n.has_class("resource-index-title"))
        self.assertEqual(title.attrs['href'], 'paper/')
        self.assertIn('<em>A &amp; B</em>', title.render())
        self.assertIn('<!-- source-attribution: A & B -->', output)
        self.assertIn('<!-- keep -->', output)
        self.assertIn('老师版', output)
        self.assertIn('说明 <a href="https://example.net/source">来源</a>', output)
        print_link = next(n for n in nodes if n.has_class('resource-index-print')).elements('a')[0]
        self.assertEqual(parse_qs(urlsplit(print_link.attrs['href']).query),
                         {'source': ['/BMS_Database/courses/demo/exams/paper/'], 'select': ['first']})
        self.assertEqual(self.render(output), output)

    def test_no_print_for_external_download_or_ambiguous_cards(self):
        for links in ['<a href="https://outside.org/exams/paper/">站外</a>',
                      '<a href="file.pdf">PDF</a>',
                      '<a href="file.pdf/">PDF</a>',
                      '<a href="../quizzes/paper/">其他分组</a>',
                      '<a href="paper/#answer">锚点</a>',
                      '<a href="a/">A</a> | <a href="b/">B</a>']:
            html = '<div class="course-resource-grid"><ul><li><p><strong>材料</strong></p><p>' + links + '</p></li></ul></div>'
            output = self.render(html)
            self.assertIn('resource-export-index', output)
            self.assertNotIn('resource-index-print', output)

    def test_multiple_groups_print_once_before_heading_and_deduplicate(self):
        def grid(href):
            return f'<div class="course-resource-grid"><ul><li><p><strong>材料</strong></p><p><a href="{href}">阅读</a></p></li></ul></div>'
        html = '<h1>目录</h1><p>介绍</p><h2>一</h2>' + grid('a.html') + '<h2>二</h2>' + grid('a.html') + grid('b/')
        output = self.render(html, site='https://example.org/')
        self.assertLess(output.index('resource-index-print'), output.index('<h2>一</h2>'))
        self.assertEqual(output.count('resource-index-print'), 1)
        link = next(n for n in Fragment(output).root.walk() if n.has_class('resource-index-print')).elements('a')[0]
        self.assertEqual(parse_qs(urlsplit(link.attrs['href']).query)['source'],
                         ['/courses/demo/exams/a.html', '/courses/demo/exams/b/'])

    def test_other_pages_and_direct_papers_are_untouched(self):
        html = '<div class="course-resource-grid"><ul><li><p>原文 &amp; 图<img src="a.png" /></p></li></ul></div>'
        for path in ['courses/demo/exams/exams.md', 'guide/index.md']:
            self.assertEqual(self.render(html, source=path), html)

    def test_discussion_and_note_indexes_share_layout_without_print(self):
        html = '<div class="course-resource-grid"><ul><li><p><strong>材料</strong> <span class="course-resource-detail">说明</span></p><p><a href="paper/">阅读</a></p></li></ul></div>'
        for path in ['courses/demo/discussions/index.md', 'courses/demo/notes/index.md']:
            output = self.render(html, source=path)
            self.assertIn('resource-export-index', output)
            self.assertIn('resource-index-title', output)
            self.assertNotIn('resource-index-print', output)
            self.assertIn('说明', output)


if __name__ == '__main__':
    unittest.main()
