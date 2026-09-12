"""Trusted repository identity and live stop gate, derived from the isolated trial."""
import base64
import re
from urllib.parse import quote

from . import security as sec

CONFIG = "scripts/contributions/repository.json"


def local_scope(root, env):
    value = sec.read_json(root / CONFIG, 2000)
    if (set(value) != {"repository", "real_calls_enabled"}
            or type(value["real_calls_enabled"]) is not bool):
        raise ValueError("投稿仓库配置结构无效")
    expected = value["repository"]
    if (not isinstance(expected, str)
            or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9-]{0,38}/[A-Za-z0-9_.-]{1,100}", expected)
            or "REPLACE" in expected.upper()
            or env.get("GITHUB_REPOSITORY") != expected):
        raise ValueError("投稿仓库与可信配置不一致, 禁止访问 GitHub")
    return value


def guard(root, api, env):
    config = local_scope(root, env)
    if api.repository != config["repository"]:
        raise ValueError("API 仓库与可信配置不一致")
    repo = api("/")
    if repo.get("full_name") != api.repository:
        raise ValueError("只允许配置中指定的投稿仓库")
    rules = api("/rules/branches/" + quote(repo["default_branch"], safe="") + "?per_page=100")
    if (not isinstance(rules, list) or any(not isinstance(rule, dict) for rule in rules)
            or "update" not in {rule.get("type") for rule in rules}):
        raise ValueError("默认分支必须限制更新; 仅可信维护者可通过单独 ruleset 的 bypass 写入")
    return config


def real_gate(root, api, env, snapshot):
    config = guard(root, api, env)
    if env.get("BMS_AI_ENABLED") != "true" or not config["real_calls_enabled"]:
        raise ValueError("真实调用总开关尚未启用")
    branch = sec.current_context(api, env)["default_branch"]
    head = api("/git/ref/heads/" + quote(branch, safe=""))
    if head.get("object", {}).get("sha") != snapshot["base_commit"]:
        raise ValueError("可信版本已经改变, 停止请求")
    live = api("/contents/" + CONFIG + "?ref=" + quote(branch, safe=""))
    if live.get("type") != "file" or live.get("encoding") != "base64":
        raise ValueError("无法核对最新停止开关")
    raw = base64.b64decode(live["content"], validate=False)
    if len(raw) > 2000 or sec.strict_json(raw.decode("utf-8")) != config:
        raise ValueError("最新开关与批准时不同, 停止请求")
