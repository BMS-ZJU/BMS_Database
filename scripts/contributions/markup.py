"""Validate a complete contribution candidate without loading project code or plugins.

The caller retains intake's size, permission, uniqueness and evidence checks.
This module does not fetch URLs, evaluate templates, include files, or write files.
Keep the fixed renderer in sync with mkdocs.yml; its contract is tested locally.
"""
from collections import Counter
from copy import deepcopy
from difflib import SequenceMatcher
from html import unescape
from html.parser import HTMLParser
import posixpath
import re
from urllib.parse import unquote, urlsplit, urlunsplit

import markdown
from material.extensions.emoji import to_svg, twemoji
from mkdocs.utils import meta
from pymdownx.superfences import fence_code_format


# MkDocs adds these builtins before the extensions explicitly in mkdocs.yml.
MKDOCS_BUILTINS = ("toc", "tables", "fenced_code")
SITE_EXTENSIONS = (
    "abbr", "attr_list", "admonition", "def_list", "footnotes", "md_in_html",
    "pymdownx.caret", "pymdownx.betterem", "pymdownx.critic",
    "pymdownx.details", "pymdownx.inlinehilite", "pymdownx.keys",
    "pymdownx.mark", "pymdownx.smartsymbols", "pymdownx.tilde",
    "pymdownx.superfences", "pymdownx.arithmatex", "toc",
    "pymdownx.highlight", "pymdownx.emoji", "pymdownx.tabbed",
    "pymdownx.tasklist",
)
TRUSTED_EXTENSIONS = tuple(dict.fromkeys((*MKDOCS_BUILTINS, *SITE_EXTENSIONS)))
TRUSTED_EXTENSION_CONFIGS = {
    "pymdownx.superfences": {"custom_fences": [
        {"name": "mermaid", "class": "mermaid", "format": fence_code_format},
    ]},
    "pymdownx.arithmatex": {"generic": True},
    "toc": {"permalink": True},
    "pymdownx.highlight": {"anchor_linenums": True, "linenums": True},
    "pymdownx.emoji": {"emoji_index": twemoji, "emoji_generator": to_svg},
    "pymdownx.tabbed": {"alternate_style": True},
    "pymdownx.tasklist": {"custom_checkbox": True},
}
ATTACHMENT_PERMISSION = "允许整理文字及原附件在本站展示"

# Ordinary document elements and the static SVG primitives used by Material icons.
# Active embeds, forms, MathML, SVG animation and foreignObject are excluded.
SAFE_TAGS = frozenset((
    "a abbr acronym address article aside b bdi bdo blockquote br caption center "
    "cite code col colgroup dd del details dfn div dl dt em figcaption figure "
    "font footer h1 h2 h3 h4 h5 h6 header hgroup hr i img input ins kbd label "
    "li main mark menu nav ol p pre q rp rt ruby s samp section small span "
    "strike strong sub summary sup table tbody td tfoot th thead time tr tt u ul "
    "var wbr svg path g circle ellipse rect line polyline polygon title desc defs "
    "clippath mask lineargradient radialgradient stop symbol"
).split())
URL_ATTRIBUTES = frozenset((
    "href", "src", "xlink:href", "action", "formaction", "background",
    "cite", "longdesc", "poster", "data", "manifest", "profile",
))
FORBIDDEN_ATTRIBUTES = frozenset(("srcdoc", "srcset", "ping", "is"))
# Python-Markdown tables emit this one safe inline style for aligned columns.
SAFE_STYLE = re.compile(r"\s*text-align\s*:\s*(?:left|center|right)\s*;?\s*", re.I)
DIRECTIVES = re.compile(
    r"\{\{|\{%|\{#[\s\S]*?#\}|\{!|-+8<-+"
    r"|!\s*include\b|<!--\s*#(?:include|exec)\b"
    r"|(?:^|\n)\s*(?:\.\.\s+(?:include|literalinclude|raw)::|include::)",
    re.I,
)
CONTROL_CHARACTERS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
URL_WHITESPACE = re.compile(r"[\x00-\x20\x7f]")


def _render(body):
    # Only package constants above are callable. No YAML loader, hooks, custom
    # icon directories, snippets, macros, or input-selected extensions are used.
    return markdown.markdown(
        body, extensions=TRUSTED_EXTENSIONS,
        extension_configs=deepcopy(TRUSTED_EXTENSION_CONFIGS),
    )


def _normalize_url(value):
    """Conservatively decode entities/percent escapes, without resolving a URL."""
    value = value or ""
    for _ in range(8):
        decoded = unquote(unescape(value), errors="strict")
        if decoded == value:
            break
        value = decoded
    else:
        raise ValueError("链接编码嵌套过深")
    value = URL_WHITESPACE.sub("", value).replace("\\", "/")
    if value.startswith("//"):
        raise ValueError("不允许协议相对链接")
    try:
        parsed = urlsplit(value)
        scheme = parsed.scheme.lower()
        if scheme not in ("", "https", "http"):
            raise ValueError("候选含不允许的链接协议")
        if parsed.username is not None or parsed.password is not None:
            raise ValueError("链接不能包含用户凭据")
        host, port = parsed.hostname, parsed.port
        if scheme and not host:
            raise ValueError("HTTP 链接缺少主机名")
    except (ValueError, UnicodeError) as error:
        raise ValueError("候选链接无效或不安全") from error
    authority = ""
    if host:
        # Browsers canonicalize DNS names, including a trailing dot and IDNA.
        host = host.rstrip(".").encode("idna").decode("ascii").lower()
        authority = "[" + host + "]" if ":" in host else host
        if port is not None and port != {"http": 80, "https": 443}.get(scheme):
            authority += ":" + str(port)
    path = posixpath.normpath(parsed.path) if parsed.path else ""
    if parsed.path.endswith("/") and path != "/":
        path += "/"
    return urlunsplit((scheme, authority, path, parsed.query, ""))


def _is_attachment(url):
    parsed = urlsplit(url)
    host = (parsed.hostname or "").lower()
    path = parsed.path.lower()
    return (
        "user-attachments" in path.split("/")
        or host in ("user-images.githubusercontent.com", "private-user-images.githubusercontent.com")
        or (host in ("github.com", "www.github.com")
            and re.match(r"^/[^/]+/[^/]+/files/[0-9]+(?:/|$)", path) is not None)
    )


class _RenderedHTML(HTMLParser):
    def __init__(self, enforce=True):
        super().__init__(convert_charrefs=True)
        self.enforce = enforce
        self.attachments = Counter()

    def handle_starttag(self, tag, attrs):
        if self.enforce and tag not in SAFE_TAGS:
            raise ValueError("候选包含不允许的 HTML 元素")
        seen = set()
        for key, value in attrs:
            name = key.lower()
            if self.enforce:
                if name in seen:
                    raise ValueError("候选包含重复 HTML 属性")
                if name.split(":")[-1].startswith("on") or name in FORBIDDEN_ATTRIBUTES:
                    raise ValueError("候选不能包含执行属性或不受支持的嵌入属性")
            seen.add(name)
            if self.enforce and name == "style" and not SAFE_STYLE.fullmatch(value or ""):
                raise ValueError("候选不能包含不受支持的内联样式")
            if name in URL_ATTRIBUTES:
                try:
                    url = _normalize_url(value)
                except (ValueError, UnicodeError):
                    if self.enforce:
                        raise ValueError("候选含危险链接") from None
                    continue
                if _is_attachment(url):
                    # Counts prevent adding a second use of an already present
                    # URL; tag/attribute distinguish a link from an embedded image.
                    self.attachments[(tag, name, url)] += 1
        if self.enforce and tag == "input":
            if (dict(attrs).get("type") or "").lower() not in ("checkbox", "radio"):
                raise ValueError("候选仅允许 Material 的复选框和标签页输入")

    def handle_endtag(self, tag):
        if self.enforce and tag not in SAFE_TAGS:
            raise ValueError("候选包含不允许的 HTML 结束标签")

    def handle_comment(self, data):
        # Avoid browser/parser disagreement on malformed comments. Normal
        # attribution and maintenance comments continue to work.
        if self.enforce and re.search(r"[<>]|--", data):
            raise ValueError("候选包含不明确的 HTML 注释")

    def handle_decl(self, decl):
        if self.enforce:
            raise ValueError("候选不能包含 HTML 声明")

    def unknown_decl(self, data):
        self.handle_decl(data)

    def handle_pi(self, data):
        self.handle_decl(data)


class _SourceTags(HTMLParser):
    """Locate raw tags, including closing tags and comments, in source offsets."""

    def __init__(self, source):
        super().__init__(convert_charrefs=False)
        self.source = source
        self.offsets = [0]
        self.offsets.extend(match.end() for match in re.finditer("\n", source))
        self.spans = []
        self.feed(source)
        self.close()

    def _record(self, end_marker, length=None):
        line, column = self.getpos()
        start = self.offsets[line - 1] + column
        end = start + length if length is not None else self.source.find(end_marker, start)
        if length is None:
            end = len(self.source) if end < 0 else end + len(end_marker)
        self.spans.append((start, end))

    def handle_starttag(self, tag, attrs):
        raw = self.get_starttag_text()
        # Markdown HTTP autolinks are editable links, not raw HTML tags.
        if not re.fullmatch(r"<https?://[^<>\s]+>", raw, re.I):
            self._record(">", len(raw))

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)

    def handle_endtag(self, tag):
        self._record(">")

    def handle_comment(self, data):
        self._record("-->")

    def handle_decl(self, decl):
        self._record(">")

    def unknown_decl(self, data):
        self._record(">")

    def handle_pi(self, data):
        self._record(">")


def _overlaps(edit_start, edit_end, tag_start, tag_end):
    if edit_start == edit_end:
        return tag_start < edit_start < tag_end
    return edit_start < tag_end and edit_end > tag_start


def _check_html_edits(original, candidate, changes):
    """Verify change coordinates and prevent tag edits or boundary assembly."""
    ranges = []
    for change in changes:
        if not isinstance(change, dict):
            raise ValueError("修改项必须是对象")
        before, after = change.get("before"), change.get("after")
        if not isinstance(before, str) or not isinstance(after, str) or not before:
            raise ValueError("修改项缺少原文或候选文字")
        if original.count(before) != 1:
            raise ValueError("原文不能唯一定位")
        start = original.index(before)
        ranges.append((start, start + len(before), before, after))
    ranges.sort(key=lambda item: item[0])
    pieces, position, delta, edits, replacements = [], 0, 0, [], []
    for start, end, before, after in ranges:
        if start < position:
            raise ValueError("修改片段互相重叠")
        pieces.extend((original[position:start], after))
        new_start = start + delta
        replacements.append((new_start, new_start + len(after)))
        # Diff only the caller's bounded snippets, not an unbounded whole page.
        for kind, a, b, c, d in SequenceMatcher(None, before, after, autojunk=False).get_opcodes():
            if kind != "equal":
                edits.append((start + a, start + b, new_start + c, new_start + d))
        delta += len(after) - len(before)
        position = end
    pieces.append(original[position:])
    if "".join(pieces) != candidate:
        raise ValueError("完整候选与修改项不一致")
    original_tags = _SourceTags(original).spans
    candidate_tags = _SourceTags(candidate).spans
    for a, b, c, d in edits:
        if any(_overlaps(a, b, x, y) for x, y in original_tags):
            raise ValueError("不能修改现有 HTML 标签或注释本身")
        for x, y in candidate_tags:
            if _overlaps(c, d, x, y) and not any(lo <= x and y <= hi for lo, hi in replacements):
                raise ValueError("不能跨替换边界拼接 HTML 标签")


def validate_markup(original, candidate, fields, changes):
    """Return None for safe markup, otherwise raise ValueError.

    Whole-candidate checks are deliberately conservative about active HTML.
    Existing safe course components and ordinary Material markup are supported.
    Local link existence is not checked: this API has no project root.
    """
    if not isinstance(original, str) or not isinstance(candidate, str):
        raise ValueError("原文和候选必须是文字")
    if not isinstance(fields, dict) or not isinstance(changes, list):
        raise ValueError("投稿字段和修改项格式无效")
    try:
        original_body, original_meta = meta.get_data(original)
        candidate_body, candidate_meta = meta.get_data(candidate)
        if original_meta != candidate_meta:
            raise ValueError("候选不能新增、删除或修改页面元数据")
        if CONTROL_CHARACTERS.search(candidate):
            raise ValueError("候选不能包含控制字符")
        if DIRECTIVES.search(candidate):
            raise ValueError("候选不能包含模板或文件包含指令")
        _check_html_edits(original, candidate, changes)
        rendered = _RenderedHTML()
        rendered.feed(_render(candidate_body))
        rendered.close()
        if fields.get("本站使用范围") != ATTACHMENT_PERMISSION:
            baseline = _RenderedHTML(enforce=False)
            baseline.feed(_render(original_body))
            baseline.close()
            if rendered.attachments - baseline.attachments:
                raise ValueError("新增附件链接或图片未获本站展示许可")
    except (AssertionError, RecursionError, TypeError, UnicodeError) as error:
        raise ValueError("无法安全解析候选标记") from error
