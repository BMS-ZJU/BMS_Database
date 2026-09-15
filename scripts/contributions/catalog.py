"""Shared course identities and GitHub course-field contract."""
import argparse
import copy
import json
import posixpath
import re
from pathlib import Path

import yaml

GENERAL = "站点公共页面"
UNKNOWN = "未找到课程或页面 (人工核对)"
AUTO_COURSE = "按页面地址自动匹配"


def resolve_page_reference(reference, aliases):
    """Resolve only registered source-page aliases; keep the first fragment."""
    if not isinstance(reference, str):
        raise ValueError("页面路径必须是字符串")
    path, _, fragment = reference.partition("#")
    seen = set()
    while True:
        if not re.fullmatch(r"[a-z0-9_-]+(?:/[a-z0-9_-]+)*\.md", path):
            raise ValueError("页面路径不符合站内 Markdown 路径格式")
        if any(ord(character) < 32 or ord(character) == 127 for character in fragment):
            raise ValueError("页面锚点含无效字符")
        if path not in aliases:
            return path + ("#" + fragment if fragment else "")
        if path in seen:
            raise ValueError("页面迁移映射存在循环")
        seen.add(path)
        target = aliases[path]
        if not isinstance(target, str):
            raise ValueError("页面迁移目标必须是字符串")
        path, _, target_fragment = target.partition("#")
        fragment = fragment or target_fragment


def page_migrations(root):
    """Share file moves and retained quiz aliases with picker and intake."""
    manifest = root / "data/path-migrations.json"
    aliases = {}
    if manifest.is_file():
        data = json.loads(manifest.read_text(encoding="utf-8"))
        if (not isinstance(data, dict) or type(data.get("version")) is not int
                or data["version"] != 1 or not isinstance(data.get("pages"), dict)):
            raise ValueError("页面迁移映射格式不正确")
        aliases.update(data["pages"])
    # Retained quiz files are source archives. Suggestions belong to their
    # published collection, whose front matter already defines this relation.
    for path in (root / "docs/courses").rglob("*.md"):
        if any(part.is_symlink() for part in [path, *path.parents]):
            continue
        text = path.read_text(encoding="utf-8")
        if not text.startswith("---\n"):
            continue
        header, separator, _ = text[4:].partition("\n---")
        if not separator or "resource_aliases:" not in header:
            continue
        meta = yaml.safe_load(header)
        current = path.relative_to(root / "docs").as_posix()
        for alias in meta.get("resource_aliases", []):
            name = alias["path"]
            if not re.fullmatch(r"[a-z0-9][a-z0-9-]*\.md", name):
                raise ValueError("小测别名必须是同目录 Markdown 文件名")
            source = posixpath.join(posixpath.dirname(current), name)
            target = current + "#" + alias["target"]
            if source in aliases and aliases[source] != target:
                raise ValueError("页面迁移映射与资料别名冲突")
            aliases[source] = target
    return {source: resolve_page_reference(source, aliases) for source in aliases}


def normalize_page_path(root, source):
    return resolve_page_reference(source, page_migrations(root))


def courses(root):
    entries = yaml.safe_load((root / "data/courses.yml").read_text(encoding="utf-8"))["courses"]
    aliases = page_migrations(root)
    result = []
    for item in entries:
        if not item.get("path"):
            continue
        source = resolve_page_reference(item["path"] + "/index.md", aliases)
        if not re.fullmatch(r"courses/[a-z0-9][a-z0-9-]*/index\.md", source):
            raise ValueError("课程目录必须使用已登记的 courses 路径")
        result.append({"id": source.removesuffix("/index.md"), "name": item["chinese_name"],
                       "label": item["chinese_name"] + (f" ({item['course_code']})" if item.get("course_code") else "")})
    if len({item["id"] for item in result}) != len(result):
        raise ValueError("课程目录路径不唯一")
    return result


def sync_forms(root, check=True):
    options = [item["label"] for item in courses(root)] + [GENERAL, UNKNOWN]
    if len(options) != len(set(options)):
        raise ValueError("课程选项不唯一, 请核对课程代码")
    for name in ("material.yml", "correction.yml"):
        path = root / ".github/ISSUE_TEMPLATE" / name
        form = yaml.safe_load(path.read_text(encoding="utf-8"))
        field = next(item for item in form["body"] if item.get("id") == "course")
        attributes = {
            "label": "课程",
            "description": "从网站进入时会自动填写, 无需重复选择。直接投稿可填写课程名称与代码; 已填页面地址时也可保留“按页面地址自动匹配”",
            "value": AUTO_COURSE,
        }
        if check:
            if (field["type"] != "input" or field["attributes"] != attributes
                    or field.get("validations") != {"required": True}):
                raise ValueError("投稿课程字段已过期, 请运行 python scripts/contributions/catalog.py --write")
        else:
            field["type"] = "input"
            field["attributes"] = attributes
            field["validations"] = {"required": True}
            path.write_text(yaml.safe_dump(form, allow_unicode=True, sort_keys=False, width=120), encoding="utf-8")
        # Keep existing website links stable. Generate the repository-entry variant
        # from the same form so consent fields and issue-body labels cannot diverge.
        direct = copy.deepcopy(form)
        direct["name"] = form["name"].removesuffix(" (网页预填)")
        direct["description"] = "直接在 GitHub 投稿, 从课程列表选择; 需要关键词搜索时使用下方的课程与页面搜索入口"
        direct_field = next(item for item in direct["body"] if item.get("id") == "course")
        direct_field.update(type="dropdown", attributes={
            "label": "课程",
            "description": "请选择课程; 无匹配项时选“未找到课程或页面”, 由人工核对",
            "options": options,
        }, validations={"required": True})
        direct_path = path.with_name(path.stem + "-direct.yml")
        if check:
            if not direct_path.is_file() or yaml.safe_load(direct_path.read_text(encoding="utf-8")) != direct:
                raise ValueError("仓库投稿表单已过期, 请运行 python scripts/contributions/catalog.py --write")
        else:
            direct_path.write_text("# Generated by scripts/contributions/catalog.py; edit " + name + " instead.\n"
                                   + yaml.safe_dump(direct, allow_unicode=True, sort_keys=False, width=120),
                                   encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true", help="同步 GitHub 课程字段与仓库直填表单")
    args = parser.parse_args()
    sync_forms(Path(__file__).resolve().parents[2], check=not args.write)
