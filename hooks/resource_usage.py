"""Render resource notices into page content so reading and export share them."""
from html import escape
import re
from urllib.parse import urljoin

from mkdocs.utils import get_relative_url

RESOURCE = re.compile(r"^(mandatory|elective)/[^/]+/(exams|quizzes)/[^/]+\.md$")
POLICY_SOURCE = "contribute/sources-and-permissions.md"


def on_page_content(html, page, config, files):
    if not RESOURCE.fullmatch(page.file.src_uri):
        return html

    policy_file = files.get_file_from_path(POLICY_SOURCE)
    policy_path = policy_file.url + "#resource-use"
    policy_link = escape(get_relative_url(policy_path, page.url), quote=True)
    is_index = page.file.name == "index"
    mode = page.meta.get("resource_usage")
    if mode not in (None, "site-policy", "source-restriction"):
        raise ValueError(f"{page.file.src_uri}: unknown resource_usage {mode!r}")
    if mode and is_index:
        raise ValueError(f"{page.file.src_uri}: set resource_usage on individual resources")

    if mode == "site-policy":
        label = "<strong>欢迎分享本站链接 · 全文转载、文件重传须经许可 · 禁止商业使用</strong>"
        scope = '<span class="resource-use-scope">具体材料的既有许可与原有要求仍适用。</span>'
    elif mode == "source-restriction":
        note = page.meta.get("resource_usage_note")
        if not isinstance(note, str) or not note.strip():
            raise ValueError(f"{page.file.src_uri}: source-restriction needs resource_usage_note")
        label = escape(note)
        scope = ""
    else:
        label = "资料免费获取 · 欢迎分享本站链接"
        scope = '<span class="resource-use-scope">具体资料请遵守原有署名、许可与使用限制。</span>'

    notice = (
        '<div class="resource-use-notice" role="note" aria-label="资料使用说明">'
        f'<p>{label} · <a href="{policy_link}">使用限制</a></p></div>'
    )
    # Match only the generated top-level heading, leaving source comments untouched.
    heading = re.search(r"</h1>", html, flags=re.IGNORECASE)
    if not heading:
        raise ValueError(f"{page.file.src_uri}: resource page needs an H1")
    html = html[:heading.end()] + "\n" + notice + html[heading.end():]
    if is_index:
        return html

    original_url = escape(page.canonical_url or urljoin(config.site_url, page.url), quote=True)
    policy_url = escape(urljoin(config.site_url, policy_path), quote=True)
    footer = (
        '<footer class="resource-use-source" aria-label="资料来源与使用限制">'
        f'<p>BMS Database · 本资料免费获取{" · " + scope if scope else ""}</p>'
        f'<p>原文：<a href="{original_url}">{original_url}</a></p>'
        f'<p>使用限制：<a href="{policy_url}">{policy_url}</a></p>'
        '</footer>'
    )
    return html + "\n" + footer
