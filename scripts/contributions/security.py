"""Frozen inputs and GitHub-authenticated approval; no model calls or Git writes."""
import base64
import hashlib
import json
from pathlib import Path
import re
from urllib.parse import quote

from . import intake, models

WORKFLOW = ".github/workflows/contribution-intake.yml"
POLICY_PATH = "scripts/contributions/policy.json"


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def hashed(value):
    return intake.digest(canonical(value))


def strict_json(raw):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("JSON 字段重复")
            result[key] = value
        return result
    return json.loads(raw, object_pairs_hook=unique,
                      parse_constant=lambda value: (_ for _ in ()).throw(ValueError("非法数字")))


def read_json(path, limit=500000):
    path = Path(path)
    if path.is_symlink() or not path.is_file() or path.stat().st_size > limit:
        raise ValueError("输入文件缺失或超过上限")
    return strict_json(path.read_text(encoding="utf-8"))


def safe_public(value, secrets=()):
    text = canonical(value)
    if any(isinstance(secret, str) and len(secret) >= 8 and secret in text for secret in secrets):
        raise ValueError("处理材料中检测到运行凭据, 不输出产物")
    if re.search(r"-----BEGIN [A-Z ]*PRIVATE KEY-----|\b(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{30,}|AIza[\w-]{30,}|sk-(?:proj-)?[A-Za-z0-9_-]{24,})", text):
        raise ValueError("材料疑似包含密钥, 请人工核对公开范围")


class GitHub:
    def __init__(self, repository, token, transport=intake.request_json):
        if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository) or not token:
            raise ValueError("GitHub 身份配置不完整")
        self.repository, self.token, self.transport = repository, token, transport

    def __call__(self, path, payload=None, method=None):
        comparison = re.fullmatch(r"/compare/[a-f0-9]{40}\.\.\.[a-f0-9]{40}", path)
        if not path.startswith("/") or path.startswith("//") or (".." in path and not comparison):
            raise ValueError("GitHub API 路径无效")
        return self.transport("https://api.github.com/repos/" + self.repository + ("" if path == "/" else path),
                              payload, self.token, limit=1500000, method=method)


def trusted_run(api, run_id, *, completed=False):
    if not re.fullmatch(r"[1-9][0-9]{0,19}", str(run_id)):
        raise ValueError("运行编号无效")
    repo = api("/")
    run = api(f"/actions/runs/{run_id}")
    if (str(run.get("id")) != str(run_id) or run.get("event") != "workflow_dispatch"
            or run.get("path", "").split("@")[0] != WORKFLOW
            or run.get("head_branch") != repo["default_branch"]
            or run.get("repository", {}).get("full_name") != api.repository
            or run.get("head_repository", {}).get("full_name") != api.repository
            or run.get("run_attempt") != 1
            or not re.fullmatch(r"[a-f0-9]{40}", run.get("head_sha", ""))):
        raise ValueError("只接受本仓库默认分支的首次手动运行")
    if completed and (run.get("status") != "completed" or run.get("conclusion") != "success"):
        raise ValueError("快照运行尚未成功完成")
    if not completed and run.get("status") != "in_progress":
        raise ValueError("当前运行已经结束或尚未开始")
    actor = run["actor"]
    if actor.get("type") != "User" or run.get("triggering_actor", {}).get("id") != actor.get("id"):
        raise ValueError("只接受可核验维护者的首次操作")
    login = actor.get("login", "")
    if not re.fullmatch(r"[A-Za-z0-9-]{1,39}", login):
        raise ValueError("GitHub 身份无效")
    permission = api(f"/collaborators/{login}/permission")
    if (permission.get("role_name") not in ("admin", "maintain")
            or permission.get("user", {}).get("id") != actor.get("id")):
        raise ValueError("需要当前仓库的 maintain 或 admin 权限")
    return {"run_id": str(run_id), "base_commit": run["head_sha"],
            "actor_id": actor["id"], "default_branch": repo["default_branch"]}


def current_context(api, env):
    if env.get("GITHUB_EVENT_NAME") != "workflow_dispatch" or env.get("GITHUB_RUN_ATTEMPT") != "1":
        raise ValueError("只有首次手动运行可以进入处理流程")
    context = trusted_run(api, env.get("GITHUB_RUN_ID", ""))
    if (context["base_commit"] != env.get("GITHUB_SHA")
            or str(context["actor_id"]) != env.get("GITHUB_ACTOR_ID")
            or env.get("GITHUB_REF") != "refs/heads/" + context["default_branch"]):
        raise ValueError("运行身份或版本不一致")
    return context


def protected_model_environment(api, context):
    name = "contribution-model"
    environment = api("/environments/" + name)
    if (environment.get("name") != name or environment.get("deployment_branch_policy") !=
            {"protected_branches": False, "custom_branch_policies": True}):
        raise ValueError("模型 Environment 必须限制为指定默认分支")
    policies = api("/environments/" + name + "/deployment-branch-policies")
    branches = policies.get("branch_policies", [])
    if (policies.get("total_count") != 1 or len(branches) != 1
            or branches[0].get("type") != "branch"
            or branches[0].get("name") != context["default_branch"]):
        raise ValueError("模型 Environment 只允许默认分支, 不允许通配符或标签")


def protected_ledger_branch(api):
    rules = api("/rules/branches/contribution-ledger?per_page=100")
    if (not isinstance(rules, list) or any(not isinstance(rule, dict) for rule in rules)
            or not {"deletion", "non_fast_forward"} <= {rule.get("type") for rule in rules}):
        raise ValueError("账本必须有生效的禁止删除和强推规则")


def policy(root):
    value = read_json(root / POLICY_PATH, 10000)
    ceilings = {"version": (1, 1), "max_submission_chars": (100, 20000),
                "max_page_chars": (100, 60000), "max_input_chars": (100, 100000),
                "max_output_tokens": (128, 6000), "max_calls_per_approval": (1, 1),
                "max_in_flight": (1, 3), "cumulative_calls": (0, 1000),
                "cumulative_input_chars": (0, 100000000), "cumulative_output_tokens": (0, 6000000)}
    if not isinstance(value, dict) or set(value) != set(ceilings):
        raise ValueError("额度配置结构无效")
    for key, (low, high) in ceilings.items():
        if type(value[key]) is not int or not low <= value[key] <= high:
            raise ValueError("额度配置超出允许范围: " + key)
    return value


def issue_record(api, number):
    if type(number) is not int or number < 1:
        raise ValueError("投稿编号无效")
    issue = api(f"/issues/{number}")
    if issue.get("number") != number or issue.get("state") != "open" or "pull_request" in issue:
        raise ValueError("只能处理仍开放的投稿 Issue")
    return {key: issue.get(key) for key in ("number", "html_url", "title", "body", "updated_at")}


def attachment_links(body):
    # The entire body is hashed too: this list is an aid, not a parser or a file-content hash.
    return sorted(set(re.findall(r"https://(?:github\.com/user-attachments|(?:user-images|private-user-images)\.githubusercontent\.com)/[^\s<>\)]+", body)))


def model_input(snapshot):
    return json.dumps({"submission": snapshot["fields"], "source_units": snapshot["source_units"],
                       "current_page": snapshot["page_content"]}, ensure_ascii=False)


def freeze(root, target, issue, context, env, repository):
    _, page = intake.resolve_target(root, target)
    fields = intake.parse_fields(issue.get("body"))
    intake.validate_selection(root, target, fields)
    limits = policy(root)
    service, model = models.model_choice(env)
    rules = (root / "scripts/contributions/rules.md").read_text(encoding="utf-8")
    from .runtime import local_scope
    snapshot = {"repository_config": local_scope(root, env), "version": 1, "repository": repository, "run_id": context["run_id"],
                "base_commit": context["base_commit"], "target": target, "issue": issue,
                "attachment_links": attachment_links(issue["body"]), "page_content": page,
                "page_sha256": intake.digest(page), "fields": fields,
                "source_units": intake.evidence_units(fields), "model_service": service,
                "model_name": model, "policy": limits, "policy_sha256": hashed(limits),
                "rules_sha256": intake.digest(rules)}
    if (len(issue["body"]) > limits["max_submission_chars"] or len(page) > limits["max_page_chars"]
            or len(rules) + len(model_input(snapshot)) > limits["max_input_chars"]):
        raise ValueError("材料超过单次输入上限, 请人工缩小范围")
    safe_public(snapshot, (env.get("GH_TOKEN"),))
    return snapshot


def verify_snapshot(root, snapshot, expected_hash, api, context, env):
    if not re.fullmatch(r"[a-f0-9]{64}", expected_hash) or hashed(snapshot) != expected_hash:
        raise ValueError("快照摘要不符, 请使用实际审阅的快照")
    origin = trusted_run(api, snapshot["run_id"], completed=True)
    if (snapshot["repository"] != api.repository or snapshot["base_commit"] != origin["base_commit"]
            or snapshot["base_commit"] != context["base_commit"]):
        raise ValueError("快照基准或可信代码已变化, 请重新生成并确认")
    head = api("/git/ref/heads/" + quote(context["default_branch"], safe=""))
    if head.get("object", {}).get("sha") != snapshot["base_commit"]:
        raise ValueError("默认分支已更新, 请重新确认快照和可信配置")
    issue = issue_record(api, snapshot["issue"]["number"])
    rebuilt = freeze(root, snapshot["target"], issue, origin, env, api.repository)
    if rebuilt != snapshot:
        raise ValueError("投稿、附件清单、目标或处理配置已变化, 请重新确认")
    # Check the current default-branch target, not just the workflow's older checkout.
    relative = quote(snapshot["target"], safe="/")
    live = api(f"/contents/{relative}?ref={quote(context['default_branch'], safe='')}")
    if live.get("type") != "file" or live.get("encoding") != "base64":
        raise ValueError("当前目标类型无效")
    content = base64.b64decode(live["content"], validate=False).decode("utf-8").replace("\r\n", "\n")
    if intake.digest(content) != snapshot["page_sha256"]:
        raise ValueError("目标页已更新, 请重新确认")
    return snapshot


def approval_record(snapshot, context, snapshot_hash):
    return {"approval_id": hashed([snapshot["repository"], snapshot["run_id"], snapshot_hash]),
            "run_id": context["run_id"], "snapshot_hash": snapshot_hash,
            "base_commit": snapshot["base_commit"], "service": snapshot["model_service"],
            "model": snapshot["model_name"], "policy_sha256": snapshot["policy_sha256"],
            "input_chars": 0, "output_tokens": snapshot["policy"]["max_output_tokens"],
            "actor_id": context["actor_id"]}


def eligible(snapshot, env):
    if env.get("BMS_AI_ENABLED") != "true":
        raise ValueError("模型调用已关闭")
    if (snapshot["fields"]["本站使用范围"] == intake.SCOPES[0]
            or snapshot["fields"].get("允许使用的外部模型服务") != snapshot["model_service"]):
        raise ValueError("投稿者未同意当前服务, 继续由人工处理")
    if any(snapshot["policy"][key] <= 0 for key in
           ("cumulative_calls", "cumulative_input_chars", "cumulative_output_tokens")):
        raise ValueError("累计额度未配置, 不允许付费调用")
