"""Shared course identities and GitHub course-field contract."""
import argparse
from pathlib import Path

import yaml

GENERAL = "站点公共页面"
UNKNOWN = "未找到课程或页面 (人工核对)"
AUTO_COURSE = "按页面地址自动匹配"


def courses(root):
    entries = yaml.safe_load((root / "COURSE_NAME_MAP.yml").read_text(encoding="utf-8"))["courses"]
    return [{"id": item["path"], "name": item["chinese_name"],
             "label": item["chinese_name"] + (f" ({item['course_code']})" if item.get("course_code") else "")}
            for item in entries if item.get("path")]


def sync_forms(root, check=True):
    options = [AUTO_COURSE, *[item["label"] for item in courses(root)], GENERAL, UNKNOWN]
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


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true", help="更新两份 GitHub 表单的课程字段")
    args = parser.parse_args()
    sync_forms(Path(__file__).resolve().parents[2], check=not args.write)
