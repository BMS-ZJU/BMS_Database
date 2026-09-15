"""Preserve published URLs and comment identities when source paths change."""
from html import escape
import json
from pathlib import Path
import posixpath
import re
import shutil
from urllib.parse import urljoin, urlsplit

from mkdocs.plugins import event_priority
from mkdocs.structure.files import File


MAPPING_PATH = "data/path-migrations.json"
RUNTIME_PATH = "assets/path-migrations.json"
_migrations = None


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate migration key: {key}")
        result[key] = value
    return result


def _safe_path(value):
    if (not isinstance(value, str) or not value or value != value.strip()
            or re.search(r"[\\:%?#\x00-\x1f\x7f]", value)
            or any(part in ("", ".", "..") for part in value.split("/"))):
        raise ValueError(f"Invalid migration path: {value!r}")
    return value


def _page_target(value):
    if not isinstance(value, str):
        raise ValueError("Page migration targets must be strings")
    path, separator, fragment = value.partition("#")
    _safe_path(path)
    if not path.endswith(".md") or (separator and not fragment):
        raise ValueError(f"Invalid page migration target: {value!r}")
    if re.search(r"[\x00-\x1f\x7f]", fragment):
        raise ValueError(f"Invalid migration fragment: {fragment!r}")
    return path, fragment


def _flatten(entries, pages=False):
    resolved = {}
    for start in entries:
        current, fragment, seen = start, "", set()
        while current in entries:
            if current in seen:
                raise ValueError(f"Migration cycle at: {current}")
            seen.add(current)
            value = entries[current]
            if pages:
                current, target_fragment = _page_target(value)
                fragment = fragment or target_fragment
            else:
                current = value
        resolved[start] = current + ("#" + fragment if fragment else "")
    return resolved


def load_migrations(config):
    root = Path(config.config_file_path).resolve().parent
    data = json.loads((root / MAPPING_PATH).read_text(encoding="utf-8"),
                      object_pairs_hook=_unique_object)
    if (not isinstance(data, dict) or type(data.get("version")) is not int
            or data["version"] != 1):
        raise ValueError("Unsupported path migration version")
    result = {"version": 1}
    for group in ("pages", "assets", "source_files"):
        entries = data.get(group)
        if not isinstance(entries, dict):
            raise ValueError(f"Missing migration object: {group}")
        folded = set()
        for source, target in entries.items():
            _safe_path(source)
            if source.casefold() in folded:
                raise ValueError(f"Ambiguous migration source: {source}")
            folded.add(source.casefold())
            if group == "pages":
                if not source.endswith(".md"):
                    raise ValueError(f"Page migration source is not Markdown: {source}")
                _page_target(target)
            else:
                _safe_path(target)
        result[group] = _flatten(entries, pages=group == "pages")
    return result


def _file(source, config):
    return File(source, config.docs_dir, config.site_dir, config.use_directory_urls)


def _inside(root, relative):
    root = Path(root).resolve()
    path = (root / relative).resolve()
    if not path.is_relative_to(root):
        raise ValueError(f"Migration path escapes its root: {relative}")
    return path


def _comment_path(source, config, migrations):
    # Merged entry pages have no single discussion identity. Fragment targets
    # describe a section of another page, not a replacement for that whole page.
    originals = [old for old, target in migrations["pages"].items()
                 if target == source]
    if len(originals) != 1:
        return None
    return urlsplit(urljoin(config.site_url, _file(originals[0], config).url)).path


def legacy_comment_path(source_uri, config):
    """Return a moved page's old pathname, including the configured site prefix.

    Load independently so other hooks can import this helper even when MkDocs
    loaded this file under a different module name.
    """
    return _comment_path(source_uri, config, load_migrations(config))


def on_pre_build(config):
    global _migrations
    _migrations = load_migrations(config)


@event_priority(-50)
def on_files(files, config):
    # Do not add redirects to Files: they must not become search results or nav.
    canonical = {file.dest_uri.casefold(): file.src_uri for file in files if file.inclusion.is_included()}
    if RUNTIME_PATH.casefold() in canonical:
        raise ValueError("Migration runtime would overwrite canonical output")
    outputs = {RUNTIME_PATH.casefold(): "migration runtime"}
    for group in ("pages", "assets"):
        for old, target in _migrations[group].items():
            destination = _file(old, config).dest_uri
            folded = destination.casefold()
            if folded in canonical:
                raise ValueError(f"Migration would overwrite canonical output: {old}")
            if folded in outputs:
                raise ValueError(f"Migration output collision: {old} / {outputs[folded]}")
            outputs[folded] = old
            _inside(config.site_dir, destination)
            new = _page_target(target)[0] if group == "pages" else target
            _inside(config.docs_dir, new)
    return files


def on_page_markdown(markdown, page, config, files):
    old_path = _comment_path(page.file.src_uri, config, _migrations)
    if old_path:
        page.meta["legacy_comment_path"] = old_path
    return markdown


def redirect_html(old, target, config):
    source, fragment = _page_target(target)
    previous, current = _file(old, config), _file(source, config)
    relative = posixpath.relpath(current.url, posixpath.dirname(previous.url) or ".")
    if current.url.endswith("/") and not relative.endswith("/"):
        relative += "/"
    relative += "#" + fragment if fragment else ""
    encoded = json.dumps(relative, ensure_ascii=True).replace("<", "\\u003c")
    script = ("const target=new URL(" + encoded + ",location.href);"
              "target.search=location.search;"
              "if(location.hash)target.hash=location.hash;"
              "location.replace(target.href);")
    canonical = urljoin(config.site_url, current.url)
    return ('<!doctype html><html lang="zh"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1">'
            '<meta name="robots" content="noindex,follow">'
            '<meta name="resource-export-source" content="' + escape(relative, quote=True) + '">'
            '<link rel="canonical" href="' + escape(canonical, quote=True) + '">'
            '<title>页面地址已更新</title><script>' + script + '</script></head>'
            '<body><main><p>页面地址已更新。</p><p><a href="' + escape(relative, quote=True)
            + '">打开页面</a></p></main></body></html>')


@event_priority(-100)
def on_post_build(config):
    # Run after resource_aliases: a moved old quiz may target a generated alias.
    runtime_path = _inside(config.site_dir, RUNTIME_PATH)
    if runtime_path.exists():
        raise ValueError("Migration runtime would overwrite existing output")
    writes = []
    for old, target in _migrations["pages"].items():
        source, _ = _page_target(target)
        current = _inside(config.site_dir, _file(source, config).dest_uri)
        if not current.is_file():
            raise ValueError(f"Page migration target was not built: {target}")
        previous = _inside(config.site_dir, _file(old, config).dest_uri)
        if previous.exists():
            raise ValueError(f"Migration would overwrite existing output: {old}")
        writes.append((previous, redirect_html(old, target, config)))
    copies = []
    for old, target in _migrations["assets"].items():
        current = _inside(config.site_dir, _file(target, config).dest_uri)
        if not current.is_file():
            raise ValueError(f"Asset migration target was not built: {target}")
        previous = _inside(config.site_dir, _file(old, config).dest_uri)
        if previous.exists():
            raise ValueError(f"Migration would overwrite existing output: {old}")
        copies.append((previous, current))
    # Validate the entire batch before creating compatibility output.
    for destination, content in writes:
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(content, encoding="utf-8")
    for destination, source in copies:
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.suffix == ".css":
            relative = posixpath.relpath(source.as_posix(), destination.parent.as_posix())
            destination.write_text("@import url(" + json.dumps(relative) + ");\n", encoding="utf-8")
        else:
            shutil.copy2(source, destination)
    runtime = {
        old: _file(target.split("#", 1)[0], config).url + ("#" + target.split("#", 1)[1] if "#" in target else "")
        for old, target in ((_file(old, config).url, target) for old, target in _migrations["pages"].items())
    }
    runtime_path.parent.mkdir(parents=True, exist_ok=True)
    runtime_path.write_text(json.dumps({"version": 1, "pages": runtime}, ensure_ascii=False), encoding="utf-8")
