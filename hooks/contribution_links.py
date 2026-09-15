"""Build the contribution picker from current published pages."""
import json
from pathlib import Path
import posixpath
import sys
from urllib.parse import urlencode, urljoin

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.contributions.catalog import GENERAL, courses, page_migrations, sync_forms

_courses = []
_pages = []


def on_config(config):
    root = Path(config.config_file_path).parent
    sync_forms(root)
    _courses[:] = courses(root)


def on_pre_build(config):
    _pages.clear()


def on_page_markdown(markdown, page, config, files):
    path = page.file.src_uri
    if path.startswith("contribute/"):
        return markdown
    base = posixpath.relpath("contribute/submit/", posixpath.dirname(page.url)) + "/?"
    page.meta["contribution_links"] = {
        mode: base + urlencode({"kind": mode, "page": path})
        for mode in ("material", "correction")
    }
    return markdown


def on_post_page(output, page, config):
    course = next((item["id"] for item in _courses
                   if page.file.src_uri.startswith(item["id"] + "/")), "general")
    # Called only for rendered pages: excludes private drafts and retired aliases.
    _pages.append({"path": page.file.src_uri, "course": course,
                   "title": str(page.title), "url": urljoin(config.site_url, page.url)})
    return output


def on_post_build(config):
    groups = [*_courses, {"id": "general", "name": GENERAL, "label": GENERAL}]
    root = Path(config.config_file_path).parent
    published = {page["path"] for page in _pages}
    aliases = {old: new for old, new in page_migrations(root).items()
               if new.split("#", 1)[0] in published}
    data = {"courses": groups, "pages": sorted(_pages, key=lambda p: (p["course"], p["path"])),
            "aliases": aliases,
            "repository": config.repo_url.rstrip("/")}
    output = Path(config.site_dir) / "contribute/catalog.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
