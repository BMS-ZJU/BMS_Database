"""Bounded suggestions from public contributions; no tools, downloads or Git writes."""
import argparse
import difflib
import hashlib
import html
import json
import os
from pathlib import Path
import re
import sys
from urllib.error import HTTPError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener
import yaml

try:
    from .catalog import AUTO_COURSE, courses
except ImportError:
    from catalog import AUTO_COURSE, courses

LABELS = ("课程", "页面地址", "适用范围", "内容", "来源与依据", "网页署名",
          "本站使用范围", "允许使用的外部模型服务", "Ginkgo 使用意愿", "公开确认",
          "问题位置与现状", "建议修改")
PUBLIC = "我确认本次填写的文字和附件可以立即公开, 并有权提供这些内容"
SCOPES = ("仅提供线索, 暂不授权整理", "允许整理文字并在本站展示, 附件仅作核对",
          "允许整理文字及原附件在本站展示")


def digest(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def parse_fields(body):
    if not isinstance(body, str) or len(body) > 20000:
        raise ValueError("投稿正文为空或超过处理上限")
    sections, current = {}, None
    for line in body.splitlines():
        if line.startswith("### "):
            name = line[4:].strip()
            if name not in LABELS or name in sections:
                raise ValueError("投稿字段不符合表单结构, 请人工核对重复标题")
            current = name
            sections[name] = []
        elif current:
            sections[current].append(line)
    fields = {key: "\n".join(value).strip() for key, value in sections.items()}
    fields = {key: ("" if value in ("_No response_", "None") else value)
              for key, value in fields.items()}
    if "问题位置与现状" in fields:
        if "内容" in fields or not fields["问题位置与现状"]:
            raise ValueError("纠错表单缺少现状或混入资料表单字段")
        fields["内容"] = "问题位置与现状: " + fields["问题位置与现状"]
        if fields.get("建议修改"):
            fields["内容"] += "\n建议修改: " + fields["建议修改"]
    elif "建议修改" in fields:
        raise ValueError("纠错表单缺少问题位置与现状")
    if not fields.get("内容") or fields.get("本站使用范围") not in SCOPES:
        raise ValueError("缺少内容或明确的本站使用范围")
    if fields.get("公开确认") not in ("- [X] " + PUBLIC, "- [x] " + PUBLIC):
        raise ValueError("缺少公开确认, 不生成公开处理产物")
    return fields


def resolve_target(root, target):
    if not re.fullmatch(r"docs/(mandatory|elective)/[a-z0-9_/-]+\.md", target):
        raise ValueError("只能选择已登记课程中的现有 Markdown 页面")
    candidate = root / target
    if any(part.is_symlink() for part in [candidate, *candidate.parents]):
        raise ValueError("目标路径不能经过符号链接")
    if not candidate.resolve().is_relative_to((root / "docs").resolve()):
        raise ValueError("目标超出课程目录")
    courses = yaml.safe_load((root / "COURSE_NAME_MAP.yml").read_text(encoding="utf-8"))["courses"]
    if not any(target.startswith("docs/" + item["path"] + "/")
               for item in courses if item.get("path")):
        raise ValueError("目标课程未在课程映射中登记")
    if not candidate.is_file() or candidate.stat().st_size > 240000:
        raise ValueError("目标不存在或超过处理上限")
    content = candidate.read_text(encoding="utf-8")
    if len(content) > 60000:
        raise ValueError("目标页面过长, 请人工分块处理")
    return candidate, content


def validate_selection(root, target, fields):
    course = next(item for item in courses(root) if target.startswith("docs/" + item["id"] + "/"))
    # Auto matching still requires the exact page URL below; it never chooses a target.
    if fields.get("课程") not in (AUTO_COURSE, course["label"]):
        raise ValueError("表单课程与目标页面不匹配, 请人工核对")
    # Read scalar configuration without executing the YAML Python-tag extensions.
    config = yaml.load((root / "mkdocs.yml").read_text(encoding="utf-8"), Loader=yaml.BaseLoader)
    site = urlsplit(config["site_url"])
    page = urlsplit(fields.get("页面地址", ""))
    relative = target.removeprefix("docs/").removesuffix(".md")
    if config.get("use_directory_urls", "true").lower() == "false":
        relative += ".html"
    elif relative.endswith("/index"):
        relative = relative[:-5]
    else:
        relative += "/"
    expected_path = site.path.rstrip("/") + "/" + relative
    if (page.scheme != site.scheme or page.netloc.lower() != site.netloc.lower()
            or page.path != expected_path or page.query or page.username or page.password):
        raise ValueError("表单页面地址与本次修改目标不匹配, 请从网站重新选择")


def evidence_units(fields):
    keys = ("课程", "适用范围", "问题位置与现状", "建议修改", "来源与依据") if "问题位置与现状" in fields \
        else ("课程", "适用范围", "内容", "来源与依据")
    return {f"{key}:L{number}": line
            for key in keys
            for number, line in enumerate(fields.get(key, "").splitlines(), 1) if line.strip()}


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError("接口重定向被拒绝")


class APIError(ValueError):
    def __init__(self, code):
        self.code = code
        super().__init__(f"接口请求失败 HTTP {code}; 未输出响应正文")


def request_json(url, payload=None, token="", limit=131072, *, auth_header="Authorization", method=None):
    parsed = urlsplit(url)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("接口必须是无用户凭据的 HTTPS 地址")
    headers = {"Accept": "application/json", "User-Agent": "BMS-contribution-intake"}
    if auth_header not in ("Authorization", "x-goog-api-key"):
        raise ValueError("接口认证方式无效")
    if token:
        headers[auth_header] = ("Bearer " if auth_header == "Authorization" else "") + token
    data = None
    if payload is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    try:
        with build_opener(NoRedirect()).open(Request(url, data=data, headers=headers, method=method), timeout=45) as response:
            raw = response.read(limit + 1)
    except HTTPError as error:
        raise APIError(error.code) from None
    if len(raw) > limit:
        raise ValueError("接口响应超过上限")
    return json.loads(raw)


def fetch_issue(repo, number, token, transport=request_json):
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repo) or number < 1:
        raise ValueError("仓库或投稿编号无效")
    issue = transport(f"https://api.github.com/repos/{repo}/issues/{number}", token=token)
    if "pull_request" in issue or issue.get("state") != "open" or issue.get("number") != number:
        raise ValueError("只能处理编号一致且尚未关闭的投稿 Issue")
    return {key: issue.get(key) for key in ("number", "html_url", "title", "body", "updated_at")}


def text_list(value, name):
    if not isinstance(value, list) or len(value) > 12 or any(
            not isinstance(item, str) or len(item) > 800 for item in value):
        raise ValueError(f"{name}格式无效")


def validate_proposal(proposal, original, units, fields):
    if not isinstance(proposal, dict) or set(proposal) != {"summary", "changes", "questions", "conflicts"}:
        raise ValueError("模型输出必须符合固定结构")
    if not isinstance(proposal["summary"], str) or len(proposal["summary"]) > 800:
        raise ValueError("修改说明格式无效")
    text_list(proposal["questions"], "疑点")
    text_list(proposal["conflicts"], "冲突")
    changes = proposal["changes"]
    if not isinstance(changes, list) or len(changes) > 3:
        raise ValueError("每次最多提出三处修改")
    if changes and (proposal["conflicts"] or fields["本站使用范围"] == SCOPES[0]):
        raise ValueError("存在冲突或未获整理许可时不能生成修改")
    frontmatter = re.match(r"\A---\n.*?\n---(?:\n|$)", original, re.S)
    minimum = frontmatter.end() if frontmatter else 0
    spans, inserted, removed = [], 0, 0
    for change in changes:
        if not isinstance(change, dict) or set(change) != {"before", "after", "reason", "evidence"}:
            raise ValueError("修改项结构无效")
        before, after = change["before"], change["after"]
        if not isinstance(before, str) or not isinstance(after, str):
            raise ValueError("修改内容必须是文字")
        if not before or not after or before == after or len(before) > 1600 or len(after) > 2400:
            raise ValueError("修改范围过大或为空")
        if original.count(before) != 1 or original.index(before) < minimum:
            raise ValueError("原文不能唯一定位, 或涉及页面元数据")
        if re.search(r"[<>]|\{[{%]|!\[|^\s*(?:\x60{3}|~~~)", after, re.M):
            raise ValueError("候选不能新增原始 HTML、模板、图片或代码块")
        if re.search(r"\{[^{}\n]*\b(?:on\w+|srcdoc|srcset|ping|style)\s*=", after, re.I):
            raise ValueError("候选不能添加执行属性或嵌入属性")
        if re.search(r"(?:javascript|data|vbscript|file)\s*:", after, re.I):
            raise ValueError("候选含不允许的链接协议")
        if fields["本站使用范围"] != SCOPES[2] and "user-attachments" in after:
            raise ValueError("附件未获本站展示许可")
        if re.search(r"[<>]|\{[{%]|^\s*(?:\x60{3}|~~~)", before, re.M):
            raise ValueError("原文包含结构或代码, 请人工编辑")
        if not isinstance(change["reason"], str) or len(change["reason"]) > 800:
            raise ValueError("修改理由无效")
        references = change["evidence"]
        if not isinstance(references, list) or not 1 <= len(references) <= 8:
            raise ValueError("每处修改必须提供投稿原文依据")
        for reference in references:
            if not isinstance(reference, dict) or set(reference) != {"id", "quote"}:
                raise ValueError("证据格式无效")
            quote = reference["quote"]
            if not isinstance(quote, str) or len(quote.strip()) < 4 or len(quote) > 1000:
                raise ValueError("证据引文长度无效")
            if reference["id"] not in units or quote not in units[reference["id"]]:
                raise ValueError("引用不能在投稿原文中定位")
        start = original.index(before)
        spans.append((start, start + len(before), after))
        inserted += max(0, len(after) - len(before))
        removed += max(0, len(before) - len(after))
    if inserted > 3500 or removed > 500:
        raise ValueError("单次增删超出小范围修改上限")
    spans.sort(reverse=True)
    candidate, last_start = original, len(original)
    for start, end, after in spans:
        if end > last_start:
            raise ValueError("修改片段互相重叠")
        candidate = candidate[:start] + after + candidate[end:]
        last_start = start
    if changes:
        try:
            from .markup import validate_markup
        except ImportError:
            from markup import validate_markup
        validate_markup(original, candidate, fields, changes)
    return candidate


def fence(value):
    longest = max((len(match) for match in re.findall(r"\x60+", value)), default=0)
    edge = "\x60" * max(3, longest + 1)
    return edge + "\n" + value + "\n" + edge


def make_report(snapshot, proposal, status, original, candidate, target):
    lines = [
        "# 投稿审阅", "", status, "", f"目标页面: {target}", "",
        f"基线提交: {snapshot['base_commit']}", "",
        f"页面 SHA-256: {snapshot['page_sha256']}", "",
        f"投稿正文 SHA-256: {snapshot['submission_sha256']}", "",
        f"投稿更新于: {snapshot['issue'].get('updated_at', '未提供')}", "",
        "处理批准、服务与用量:", "", fence(json.dumps({key: snapshot.get(key) for key in
            ("approval", "model_service", "model_name", "model_version", "model_usage")},
            ensure_ascii=False, indent=2)), "",
        "模型只提出候选, 不判定来源真实或自动发布。行号属于投稿文字, 不代表附件页码。",
        "附件和站外链接未自动下载或读取; 图片、表格及原件完整性需要另行核对。", "",
        "## 投稿与使用范围", "", fence(json.dumps(snapshot["fields"], ensure_ascii=False, indent=2)), "",
        "## 来源定位", "", fence(json.dumps(snapshot["source_units"], ensure_ascii=False, indent=2)), "",
        "## 修改说明", "", fence(proposal["summary"]), "",
    ]
    for index, change in enumerate(proposal["changes"], 1):
        lines.extend([f"## R{index:02d}", "", "原文:", "", fence(change["before"]), "",
                      "建议:", "", fence(change["after"]), "", "理由及依据:", "",
                      fence(json.dumps({"reason": change["reason"], "evidence": change["evidence"]},
                                       ensure_ascii=False, indent=2)), ""])
    lines.extend(["## 待确认与冲突", "", fence(json.dumps({
        "questions": proposal["questions"], "conflicts": proposal["conflicts"],
    }, ensure_ascii=False, indent=2)), "", "## 差异", "",
        fence("".join(difflib.unified_diff(original.splitlines(True), candidate.splitlines(True),
                                         fromfile=target, tofile="候选/" + target))), "",
        "采用前重新核对投稿是否编辑过、目标页面是否更新, 以及链接和网页显示。"])
    return "\n".join(lines) + "\n"


def review_html(snapshot, proposal, status, preview_url, changed):
    esc = lambda value: html.escape(str(value), quote=True)
    blocks = [
        '<!doctype html><html lang="zh"><meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width,initial-scale=1">',
        '<title>投稿审阅</title><style>body{max-width:70em;margin:2em auto;padding:0 1em;'
        'font:16px/1.7 system-ui;color:#202428;background:#fff}'
        'pre{white-space:pre-wrap;overflow-wrap:anywhere;font:inherit;background:#f5f6f7;padding:1em}'
        '.compare{display:grid;grid-template-columns:1fr 1fr;gap:1em}section{margin:2em 0}'
        'h2{font-size:1.2em}h3{font-size:1em}details{margin:1em 0}'
        '@media(max-width:650px){.compare{grid-template-columns:1fr}}</style>',
        '<h1>投稿审阅</h1><p>' + esc(status) + '</p>',
        '<p>目标页面: ' + esc(snapshot["target"]) + '</p>',
        '<p>' + esc(proposal["summary"]) + '</p>',
    ]
    if changed:
        blocks.append('<p><a href="' + esc(preview_url) + '">打开候选网页 (构建成功后可用)</a></p>')
    for index, change in enumerate(proposal["changes"], 1):
        blocks.extend([
            f'<section><h2>R{index:02d}</h2><p>' + esc(change["reason"]) + '</p>',
            '<div class="compare"><div><h3>原文</h3><pre>' + esc(change["before"]) + '</pre></div>',
            '<div><h3>建议修改</h3><pre>' + esc(change["after"]) + '</pre></div></div>',
            '<h3>投稿依据</h3><ul>',
        ])
        for reference in change["evidence"]:
            blocks.append('<li>' + esc(reference["id"]) + ': ' + esc(reference["quote"]) + '</li>')
        blocks.append('</ul></section>')
    blocks.append('<section><h2>待确认与冲突</h2><ul>')
    for item in proposal["questions"] + proposal["conflicts"]:
        blocks.append('<li>' + esc(item) + '</li>')
    blocks.append('</ul><p>依据行号只定位投稿文字, 不是附件页码。附件与链接未自动读取。'
                  '采用前仍需核对课程事实、使用范围和页面是否已经更新。</p></section>')
    blocks.extend([
        '<details><summary>查看完整投稿与使用范围</summary><pre>',
        esc(json.dumps(snapshot["fields"], ensure_ascii=False, indent=2)), '</pre></details>',
        '<details><summary>查看来源行与版本记录</summary><pre>',
        esc(json.dumps({key: snapshot.get(key) for key in (
            "source_units", "base_commit", "page_sha256", "submission_sha256",
            "approval", "model_service", "model_name", "model_version", "model_usage")}, ensure_ascii=False, indent=2)),
        '</pre></details><p><a href="review.md">完整 Markdown 审阅稿与差异</a></p></html>',
    ])
    return "".join(blocks)


def prepare(root, target, issue, out, env, transport=request_json):
    path, original = resolve_target(root, target)
    fields = parse_fields(issue.get("body"))
    validate_selection(root, target, fields)
    units = evidence_units(fields)
    # Receipt is free even if the environment contains model keys and an enable flag.
    status = "已收件, 尚未取得维护者对快照的处理批准"
    proposal = {"summary": status, "changes": [], "questions": [], "conflicts": []}
    model_record = {"model_service": None, "model_name": None, "model_version": None}
    candidate = validate_proposal(proposal, original, units, fields)
    snapshot = {
        "issue": issue, "fields": fields, "source_units": units, "target": target,
        "base_commit": env.get("GITHUB_SHA", "本地未提交工作树"),
        "page_sha256": digest(original), "submission_sha256": digest(issue["body"]),
        **model_record,
    }
    # Write only after consent, parsing and all candidate validation have succeeded.
    out.mkdir(parents=True, exist_ok=True)
    for name, value in (("snapshot.json", snapshot), ("proposal.json", proposal)):
        (out / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (out / "candidate.md").write_text(candidate, encoding="utf-8")
    report = make_report(snapshot, proposal, status, original, candidate, target)
    (out / "review.md").write_text(report, encoding="utf-8")
    preview = Path(target).relative_to("docs").with_suffix("")
    if preview.name != "index":
        preview /= "index"
    preview_url = "site/" + preview.as_posix() + ".html"
    (out / "review.html").write_text(
        review_html(snapshot, proposal, status, preview_url, candidate != original), encoding="utf-8")
    return candidate != original


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--target", required=True)
    parser.add_argument("--issue-file", type=Path)
    parser.add_argument("--issue-number", type=int)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root, output = args.root.resolve(), args.output.resolve()
    if output.is_relative_to(root):
        raise ValueError("处理产物必须放在仓库外")
    if bool(args.issue_file) == bool(args.issue_number):
        raise ValueError("必须选择一个投稿输入")
    issue = (json.loads(args.issue_file.read_text(encoding="utf-8"))
             if args.issue_file else fetch_issue(
                 os.environ.get("GITHUB_REPOSITORY", ""), args.issue_number,
                 os.environ.get("GH_TOKEN", "")))
    changed = prepare(root, args.target, issue, output, os.environ)
    if os.environ.get("GITHUB_OUTPUT"):
        with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as handle:
            handle.write(f"changed={str(changed).lower()}\n")
    print("已生成待审材料" if changed else "已生成供人工处理的投稿记录")


if __name__ == "__main__":
    try:
        main()
    except (ValueError, KeyError, TypeError, OSError, IndexError) as error:
        print(f"投稿处理未完成 ({type(error).__name__}), 请按维护指南核对输入与配置", file=sys.stderr)
        sys.exit(1)
