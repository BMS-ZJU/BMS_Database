"""Shared course identities and generated native GitHub dropdowns."""
import argparse
from pathlib import Path

import yaml

GENERAL = "站点公共页面"
UNKNOWN = "未找到课程或页面 (人工核对)"


def courses(root):
    entries = yaml.safe_load((root / "COURSE_NAME_MAP.yml").read_text(encoding="utf-8"))["courses"]
    return [{"id": item["path"], "name": item["chinese_name"],
             "label": item["chinese_name"] + (f" ({item['course_code']})" if item.get("course_code") else "")}
            for item in entries if item.get("path")]


def sync_forms(root, check=True):
    options = [item["label"] for item in courses(root)] + [GENERAL, UNKNOWN]
    if len(options) != len(set(options)):
        raise ValueError("课程选项不唯一, 请核对课程代码")
    for name in ("material.yml", "correction.yml"):
        path = root / ".github/ISSUE_TEMPLATE" / name
        form = yaml.safe_load(path.read_text(encoding="utf-8"))
        field = next(item for item in form["body"] if item.get("id") == "course")
        if check:
            if field["type"] != "dropdown" or field["attributes"].get("options") != options:
                raise ValueError("投稿课程下拉框已过期, 请运行 python scripts/contributions/catalog.py --write")
        else:
            field["type"] = "dropdown"
            field["attributes"] = {
                "label": "课程",
                "description": "必选。按页面地址选择对应课程; 无匹配项时选“未找到课程或页面”, 由人工核对",
                "options": options,
            }
            field["validations"] = {"required": True}
            path.write_text(yaml.safe_dump(form, allow_unicode=True, sort_keys=False, width=120), encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true", help="更新两份 GitHub 表单的课程选项")
    args = parser.parse_args()
    sync_forms(Path(__file__).resolve().parents[2], check=not args.write)
