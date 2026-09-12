"""Use complete document identities without expanding navigation labels."""
from html.parser import HTMLParser
from pathlib import Path
import re

import yaml


VOID_TAGS = frozenset(("area", "base", "br", "col", "embed", "hr", "img", "input",
                       "link", "meta", "param", "source", "track", "wbr"))


class _Heading(HTMLParser):
    """Read the first rendered H1, excluding permalink and hidden text."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.started = False
        self.finished = False
        self.hidden = 0
        self.parts = []

    def handle_starttag(self, tag, attrs):
        if self.finished:
            return
        if tag == "h1":
            self.started = True
        elif self.started:
            attrs = dict(attrs)
            if self.hidden:
                if tag not in VOID_TAGS:
                    self.hidden += 1
            elif "headerlink" in attrs.get("class", "").split() or attrs.get("aria-hidden") == "true":
                if tag not in VOID_TAGS:
                    self.hidden = 1
            elif tag == "img":
                self.parts.append(attrs.get("alt", ""))
            elif tag == "br":
                self.parts.append(" ")

    def handle_endtag(self, tag):
        if tag == "h1" and self.started:
            self.finished = True
        elif self.hidden and tag not in VOID_TAGS:
            self.hidden -= 1

    def handle_data(self, data):
        if self.started and not self.finished and not self.hidden:
            self.parts.append(data)


def heading_title(content):
    parser = _Heading()
    parser.feed(content or "")
    return " ".join("".join(parser.parts).split())


def _archived_names(config):
    mapping = Path(config.config_file_path).parent / "COURSE_NAME_MAP.yml"
    data = yaml.safe_load(mapping.read_text(encoding="utf-8"))
    # A different historical course can share a directory for archive purposes.
    # Its documented name must not acquire the current directory's course name.
    return [
        (item["archived_materials_path"].rstrip("/") + "/", item["chinese_name"])
        for item in data.get("curriculum_only_courses", [])
        if item.get("archived_materials_path") and item.get("chinese_name")
    ]


def on_env(env, config, files):
    # MkDocs has rendered every page at this point, so course lookup does not
    # depend on file order or on a Markdown heading being the first block.
    pages = [file.page for file in files.documentation_pages()
             if file.page is not None and file.page.content is not None]
    headings = {page.file.src_uri: heading_title(page.content) for page in pages}
    archived = _archived_names(config)
    for page in pages:
        title = page.meta.get("title") or headings[page.file.src_uri]
        if not title:
            continue
        title = str(title)
        match = re.match(r"^((?:mandatory|elective)/[^/]+)/", page.file.src_uri)
        if match and page.file.src_uri != match[1] + "/index.md":
            course = headings.get(match[1] + "/index.md", "")
            historical = any(page.file.src_uri.startswith(path) and name in title
                             for path, name in archived)
            if course and course not in title and not historical:
                title = f"{course} · {title}"
        # Material uses metadata for the browser/bookmark and header titles.
        # Page.title retains explicit short labels supplied by mkdocs.yml.
        page.meta["title"] = title
    return env
