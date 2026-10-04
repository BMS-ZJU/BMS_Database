"""Render resource directories before first paint, without browser rewrites."""
from copy import deepcopy
from html import escape, unescape
from html.parser import HTMLParser
import re
from urllib.parse import urlencode, urljoin, urlsplit

from mkdocs.utils import get_relative_url

INDEX = re.compile(r"^courses/[^/]+/(exams|quizzes|discussions|notes)/index\.md$")
VOID = frozenset("area base br col embed hr img input link meta param source track wbr".split())


class Element:
    """A small fragment tree that preserves untouched tags, entities and comments."""

    def __init__(self, tag="", attrs=(), opening="", closing=""):
        self.tag, self.attrs = tag, dict(attrs)
        self.opening, self.closing = opening, closing
        self.children = []

    def has_class(self, name):
        return name in (self.attrs.get("class") or "").split()

    def set_attr(self, name, value):
        self.attrs[name] = value
        self.opening = "<" + self.tag + "".join(
            " " + key + (f'="{escape(value, quote=True)}"' if value is not None else "")
            for key, value in self.attrs.items()
        ) + ">"

    def add_class(self, name):
        if not self.has_class(name):
            self.set_attr("class", ((self.attrs.get("class") or "") + " " + name).strip())

    def elements(self, tag=None):
        return [child for child in self.children
                if isinstance(child, Element) and (tag is None or child.tag == tag)]

    def walk(self):
        yield self
        for child in self.elements():
            yield from child.walk()

    def render(self):
        return self.opening + "".join(
            child.render() if isinstance(child, Element) else child for child in self.children
        ) + self.closing


class Fragment(HTMLParser):
    def __init__(self, html):
        super().__init__(convert_charrefs=False)
        self.root = Element()
        self.stack = [self.root]
        self.feed(html)
        self.close()

    def handle_starttag(self, tag, attrs):
        node = Element(tag, attrs, self.get_starttag_text())
        self.stack[-1].children.append(node)
        if tag not in VOID:
            self.stack.append(node)

    def handle_startendtag(self, tag, attrs):
        self.stack[-1].children.append(Element(tag, attrs, self.get_starttag_text()))

    def handle_endtag(self, tag):
        # MkDocs emits balanced fragments; preserve an unmatched tag verbatim.
        if len(self.stack) > 1 and self.stack[-1].tag == tag:
            self.stack.pop().closing = f"</{tag}>"
        else:
            self.handle_data(f"</{tag}>")

    def handle_data(self, value):
        self.stack[-1].children.append(value)

    def handle_entityref(self, name):
        self.handle_data(f"&{name};")

    def handle_charref(self, name):
        self.handle_data(f"&#{name};")

    def handle_comment(self, value):
        self.handle_data(f"<!--{value}-->")


def _is_action(paragraph):
    return any(link.attrs.get("href") for link in paragraph.elements("a")) and all(
        (child.tag == "a" and child.attrs.get("href") or child.has_class("divider"))
        if isinstance(child, Element) else
        child.startswith("<!--") or re.fullmatch(r"[\s·|]*", unescape(child))
        for child in paragraph.children
    )


def _prepare_card(card):
    paragraphs = card.elements("p")
    if not paragraphs:
        return []
    actions = []
    notes = []
    for index, paragraph in enumerate(paragraphs):
        if _is_action(paragraph):
            paragraph.add_class("resource-index-actions")
            actions.append(paragraph)
        elif index:
            paragraph.add_class("resource-index-note")
            notes.append(paragraph)
    if not actions:
        return []

    links = [link for row in actions for link in row.elements("a") if link.attrs.get("href")]
    read = next((link for link in links if link.has_class("resource-read-link")), None)
    practice = next((link for link in links if link.has_class("resource-practice-link")), None)
    if read is not None and practice is not None:
        links = [read, practice] + [link for link in links if link not in (read, practice)]
    comments = [child for row in actions for child in row.children
                if isinstance(child, str) and child.startswith("<!--")]
    row = actions[0]
    row.children = comments[:]
    for index, link in enumerate(links):
        if index:
            row.children.append('<span class="divider" aria-hidden="true">|</span>')
        row.children.append(link)
    if len(links) > 1:
        row.add_class("link-divider")
    for extra in actions[1:]:
        card.children.remove(extra)

    heading = paragraphs[0]
    titles = heading.elements("strong")
    if titles and links:
        title = titles[0]
        if not any(node.tag == "a" for node in title.walk()):
            link = deepcopy(links[0])
            link.attrs.pop("id", None)
            link.attrs.pop("aria-label", None)
            link.set_attr("class", "resource-index-title")
            link.children, title.children = title.children, [link]
        metadata = [node for node in heading.elements()
                    if node.has_class("exam-resource-tag") or node.has_class("course-resource-detail")]
        for node in metadata:
            heading.children.remove(node)
        for node in notes:
            card.children.remove(node)
        card.children.extend(metadata + notes)
    return links


def _local_source(href, page, config):
    base = urlsplit(config.site_url)
    target = urlsplit(urljoin(urljoin(config.site_url, page.url), href))
    section = urlsplit(urljoin(config.site_url, page.url)).path
    if (target.scheme, target.netloc) != (base.scheme, base.netloc):
        return None
    if target.query or target.fragment or not target.path.startswith(section):
        return None
    relative = target.path[len(section):]
    if (not re.fullmatch(r"[^/]+(?:/|\.html)", relative) or relative == "index.html"
            or re.search(r"\.(?:pdf|docx?|zip)/?$", relative, re.I)):
        return None
    return target.path


def on_page_content(html, page, config, files):
    index = INDEX.fullmatch(page.file.src_uri)
    if not index:
        return html
    fragment = Fragment(html)
    grids = [node for node in fragment.root.walk() if node.has_class("course-resource-grid")]
    if not grids or all(grid.has_class("resource-export-index") for grid in grids):
        return html
    sources = []
    for grid in grids:
        grid.add_class("resource-export-index")
        for listing in grid.elements("ul"):
            for card in listing.elements("li"):
                links = _prepare_card(card)
                targets = list(dict.fromkeys(
                    source for link in links
                    if (source := _local_source(link.attrs["href"], page, config))
                )) if index[1] in ("exams", "quizzes") else []
                if len(targets) == 1 and targets[0] not in sources:
                    sources.append(targets[0])
    if sources:
        href = get_relative_url("resource-export.html", page.url) + "?" + urlencode(
            [("source", source) for source in sources] + [("select", "first")]
        )
        toolbar = (
            '<div class="resource-batch-toolbar resource-index-print" role="group" aria-label="资料打印">'
            f'<a href="{escape(href, quote=True)}" target="_blank" rel="noopener" data-instant="false" '
            'title="在打印预览中选择资料，再打印或保存为 PDF" '
            'aria-label="打印 / 保存 PDF（新标签页）">打印 / 保存 PDF</a></div>'
        )
        # A directory-wide print entry precedes its first group heading.
        parent = next(node for node in fragment.root.walk() if grids[0] in node.children)
        anchor = parent.children.index(grids[0])
        if len(grids) > 1:
            for index in range(anchor - 1, -1, -1):
                node = parent.children[index]
                if isinstance(node, Element) and node.tag in ("h1", "h2"):
                    if node.tag == "h2":
                        anchor = index
                    break
        parent.children.insert(anchor, toolbar + "\n")
    return fragment.root.render()
