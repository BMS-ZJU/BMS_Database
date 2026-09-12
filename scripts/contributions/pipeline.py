"""Manual snapshot -> durable reservation -> one call -> preview without editing source."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

from . import intake, models, security as sec
from .ledger import Ledger, initialize
from . import runtime, diagnostics


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(sec.canonical(value), encoding="utf-8")


def rules(root):
    return (root / "scripts/contributions/rules.md").read_text(encoding="utf-8")


def record_for(root, snapshot, context, snapshot_hash):
    record = sec.approval_record(snapshot, context, snapshot_hash)
    record["input_chars"] = len(rules(root)) + len(sec.model_input(snapshot))
    return record


def collect(root, target, issue_number, out, api, env):
    runtime.guard(root, api, env)
    context = sec.current_context(api, env)
    snapshot = sec.freeze(root, target, sec.issue_record(api, issue_number), context, env, api.repository)
    sha = sec.hashed(snapshot)
    write_json(out / "snapshot.json", snapshot)
    report = ("# 待批准的投稿快照\n\n本次没有调用模型。请先核对完整材料, 再批准这一版本。\n\n"
              f"快照运行: {context['run_id']}\n\n快照 SHA-256: {sha}\n\n"
              f"目标: {target}\n\n基准提交: {context['base_commit']}\n\n"
              f"服务 / 请求模型: {snapshot['model_service']} / {snapshot['model_name']}\n\n"
              "附件只列出正文中的入口, 未下载、解析或核验文件内容。\n\n"
              + intake.fence(json.dumps(snapshot, ensure_ascii=False, indent=2)) + "\n")
    (out / "review.md").write_text(report, encoding="utf-8")
    if env.get("GITHUB_STEP_SUMMARY"):
        Path(env["GITHUB_STEP_SUMMARY"]).write_text(
            f"免费快照已生成。先下载 snapshot-{context['run_id']} 审阅 review.md。\n\n"
            f"快照运行: `{context['run_id']}`\n\n快照 SHA-256: `{sha}`\n", encoding="utf-8")
    return sha


def approved(root, snapshot, expected_hash, api, env):
    runtime.guard(root, api, env)
    context = sec.current_context(api, env)
    if str(snapshot["run_id"]) != env.get("BMS_SNAPSHOT_RUN_ID"):
        raise ValueError("指定的快照运行不一致")
    sec.verify_snapshot(root, snapshot, expected_hash, api, context, env)
    sec.eligible(snapshot, env)
    sec.protected_model_environment(api, context)
    sec.protected_ledger_branch(api)
    runtime.real_gate(root, api, env, snapshot)
    return context, record_for(root, snapshot, context, expected_hash)


def reserve(root, snapshot, expected_hash, api, env):
    _, record = approved(root, snapshot, expected_hash, api, env)
    Ledger(api, env.get("BMS_LEDGER_ANCHOR", ""), env.get("BMS_LEDGER_KEY", "")).reserve(record, snapshot["policy"])
    return record


def receipt_metadata(response, service, cap):
    metadata = models.response_metadata(response, service)
    usage = metadata["model_usage"] or {}
    count = usage.get({"DeepSeek": "completion_tokens", "OpenAI": "output_tokens",
                       "Gemini": "candidatesTokenCount"}[service])
    if count is not None and service == "Gemini":
        count += usage.get("thoughtsTokenCount", 0)
    return {"state": "complete" if count is not None and count <= cap else "unknown",
            "usage": metadata["model_usage"], "model_version": metadata["model_version"]}


def execute(root, snapshot, expected_hash, out, receipt_path, api, env, transport=intake.request_json):
    _, record = approved(root, snapshot, expected_hash, api, env)
    models.configuration(env)
    Ledger(api, env.get("BMS_LEDGER_ANCHOR", ""), env.get("BMS_LEDGER_KEY", "")).verify_reservation(record)
    secrets = [env.get("GH_TOKEN"), env.get("BMS_LEDGER_KEY"), *(env.get(item[2]) for item in models.PROVIDERS.values())]
    sec.safe_public(snapshot, secrets)
    runner_temp = Path(env["RUNNER_TEMP"]).resolve()
    marker = runner_temp / ("contribution-call-" + record["run_id"] + ".lock")
    # A second command in the same runner also stops; fresh reruns are rejected by GitHub run_attempt.
    with marker.open("x", encoding="utf-8") as handle:
        handle.write(record["approval_id"])
        handle.flush()
        os.fsync(handle.fileno())
    receipt = {"approval_id": record["approval_id"], "run_id": record["run_id"],
               "state": "unknown", "usage": None, "model_version": None}
    write_json(receipt_path, receipt)
    calls = 0

    def once(url, payload, token, **kwargs):
        nonlocal calls
        if calls:
            raise ValueError("每次批准最多调用一次, 不允许重试")
        calls += 1
        runtime.real_gate(root, api, env, snapshot)
        receipt["stage"] = "request_sent"
        response = transport(url, payload, token, **kwargs)
        receipt["stage"] = "model_response"
        receipt["diagnostics"] = diagnostics.response_diagnostics(response, snapshot["model_service"])
        receipt.update(receipt_metadata(response, snapshot["model_service"], record["output_tokens"]))
        sec.safe_public(receipt, secrets)
        write_json(receipt_path, receipt)
        return response

    try:
        proposal, metadata = models.generate(env, rules(root), sec.model_input(snapshot), once,
                                            max_output_tokens=record["output_tokens"])
        receipt["stage"] = "candidate_validation"
        candidate = intake.validate_proposal(proposal, snapshot["page_content"],
                                             snapshot["source_units"], snapshot["fields"])
        report_snapshot = {**snapshot, "submission_sha256": intake.digest(snapshot["issue"]["body"]),
                           "approval": record, **metadata}
        sec.safe_public({"snapshot": report_snapshot, "proposal": proposal, "candidate": candidate}, secrets)
        receipt["stage"] = "usage_validation"
        if receipt["state"] != "complete":
            raise ValueError("用量未知或超出预留上限, 停止并人工核账")
        out.mkdir(parents=True, exist_ok=True)
        for name, value in (("approved-snapshot.json", snapshot), ("snapshot.json", report_snapshot),
                            ("proposal.json", proposal), ("approval.json", record)):
            write_json(out / name, value)
        (out / "candidate.md").write_text(candidate, encoding="utf-8")
        status = "已生成模型候选, 等待人工核对; 采用前仍须确认来源与版本"
        (out / "review.md").write_text(intake.make_report(report_snapshot, proposal, status,
            snapshot["page_content"], candidate, snapshot["target"]), encoding="utf-8")
        preview = Path(snapshot["target"]).relative_to("docs").with_suffix("")
        if preview.name != "index":
            preview /= "index"
        (out / "review.html").write_text(intake.review_html(report_snapshot, proposal, status,
            "site/" + preview.as_posix() + ".html", candidate != snapshot["page_content"]), encoding="utf-8")
        receipt["stage"] = "review_generated"
        write_json(receipt_path, receipt)
        return candidate != snapshot["page_content"]
    except (ValueError, KeyError, TypeError, OSError, IndexError) as error:
        failure = diagnostics.failure(receipt, error)
        try:
            sec.safe_public(receipt, secrets)
        except ValueError:
            receipt = {"approval_id": record["approval_id"], "run_id": record["run_id"],
                       "state": "unknown", "usage": None, "model_version": None}
        receipt["failure"] = failure
        write_json(receipt_path, receipt)
        raise


def checked_candidate(root, source):
    snapshot = sec.read_json(source / "approved-snapshot.json")
    approval = sec.read_json(source / "approval.json", 10000)
    if sec.hashed(snapshot) != approval["snapshot_hash"]:
        raise ValueError("候选快照与批准记录不符")
    if (snapshot["base_commit"] != approval["base_commit"]
            or snapshot["policy_sha256"] != sec.hashed(sec.policy(root))
            or snapshot["rules_sha256"] != intake.digest(rules(root))):
        raise ValueError("候选与可信代码或规则版本不一致")
    _, original = intake.resolve_target(root, snapshot["target"])
    if original != snapshot["page_content"] or intake.digest(original) != snapshot["page_sha256"]:
        raise ValueError("候选基准页面不一致")
    fields = intake.parse_fields(snapshot["issue"]["body"])
    intake.validate_selection(root, snapshot["target"], fields)
    candidate = intake.validate_proposal(sec.read_json(source / "proposal.json", 100000), original,
                                         intake.evidence_units(fields), fields)
    path = source / "candidate.md"
    if path.is_symlink() or path.stat().st_size > 250000 or candidate != path.read_text(encoding="utf-8"):
        raise ValueError("候选文件不等于已校验的限定修改")
    return snapshot["target"], candidate, candidate != original


def build_preview(root, source, output_dir):
    """MkDocs reads the checked candidate from memory. Source files are never modified."""
    if root.resolve().is_relative_to(output_dir.resolve()) or source.resolve().is_relative_to(output_dir.resolve()):
        raise ValueError("预览输出不能覆盖源码或审阅材料目录")
    from mkdocs.config import load_config
    from mkdocs.commands.build import build
    from mkdocs.plugins import BasePlugin
    target, candidate, changed = checked_candidate(root, source)
    if not changed:
        return False
    class CandidateSource(BasePlugin):
        def on_page_read_source(self, page, config):
            if page.file.src_uri == target.removeprefix("docs/"):
                return candidate
            return None
    config = load_config(config_file=str(root / "mkdocs.yml"), site_dir=str(output_dir), strict=True)
    config.plugins["contribution-preview"] = CandidateSource()
    build(config)
    return True


def output(env, key, value):
    if env.get("GITHUB_OUTPUT"):
        with Path(env["GITHUB_OUTPUT"]).open("a", encoding="utf-8") as handle:
            handle.write(f"{key}={value}\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=("snapshot", "reserve", "call", "build", "settle", "initialize", "reconcile"))
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--source", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--receipt", type=Path)
    args = parser.parse_args()
    env, root = os.environ, args.root.resolve()
    runtime.local_scope(root, env)
    for folder in (args.source, args.output, args.receipt):
        if folder and folder.resolve().is_relative_to(root):
            raise ValueError("处理产物必须位于仓库外")
        if folder and not folder.resolve().is_relative_to(Path(env["RUNNER_TEMP"]).resolve()):
            raise ValueError("处理产物必须位于本次 runner 临时目录")
    if env.get("GITHUB_ACTIONS") != "true":
        raise ValueError("此入口只供可信 Actions 运行; 本地使用模拟测试")
    actual = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, check=True,
                            capture_output=True, text=True).stdout.strip()
    if actual != env.get("GITHUB_SHA"):
        raise ValueError("代码检出版本与工作流不一致")
    if args.operation == "build":
        snapshot = sec.read_json(args.source / "approved-snapshot.json")
        if snapshot["base_commit"] != actual:
            raise ValueError("构建检出版本与批准不一致")
        build_preview(root, args.source, args.output)
        return
    api = sec.GitHub(env.get("GITHUB_REPOSITORY", ""), env.get("GH_TOKEN", ""))
    runtime.guard(root, api, env)
    context = sec.current_context(api, env)
    if args.operation in ("initialize", "settle", "reconcile"):
        sec.protected_model_environment(api, context)
        sec.protected_ledger_branch(api)
    if args.operation == "initialize":
        anchor = initialize(api, env.get("BMS_LEDGER_KEY", ""))
        if env.get("GITHUB_STEP_SUMMARY"):
            Path(env["GITHUB_STEP_SUMMARY"]).write_text(
                f"账本已初始化, 将 CONTRIBUTION_LEDGER_ANCHOR 设置为 `{anchor}`。额度仍默认关闭。\n", encoding="utf-8")
        return
    ledger = Ledger(api, env.get("BMS_LEDGER_ANCHOR", ""), env.get("BMS_LEDGER_KEY", "")) if args.operation in ("settle", "reconcile") else None
    if args.operation == "reconcile":
        ledger.reconcile(env.get("BMS_APPROVAL_ID", ""))
        return
    if args.operation == "settle":
        approval_id = env.get("BMS_APPROVAL_ID", "")
        receipt = {"state": "unknown", "usage": None, "model_version": None}
        if args.receipt and args.receipt.is_file():
            received = sec.read_json(args.receipt, 10000)
            if received["approval_id"] != approval_id or received["run_id"] != context["run_id"]:
                raise ValueError("用量回执与本次批准不符")
            receipt = {key: received[key] for key in receipt}
        ledger.settle(approval_id, context["run_id"], receipt)
        return
    if args.operation == "snapshot":
        collect(root, env.get("BMS_TARGET_PAGE", ""), int(env.get("BMS_ISSUE_NUMBER", "0")), args.output, api, env)
        return
    snapshot = sec.read_json(args.source / "snapshot.json")
    expected = env.get("BMS_SNAPSHOT_HASH", "")
    if args.operation == "reserve":
        record = reserve(root, snapshot, expected, api, env)
        output(env, "service", record["service"])
        output(env, "approval_id", record["approval_id"])
    else:
        changed = execute(root, snapshot, expected, args.output, args.receipt, api, env)
        output(env, "changed", str(changed).lower())


if __name__ == "__main__":
    try:
        main()
    except (ValueError, KeyError, TypeError, OSError, IndexError, subprocess.SubprocessError) as error:
        print("投稿处理已停止: " + diagnostics.safe_detail(error), file=sys.stderr)
        sys.exit(1)
