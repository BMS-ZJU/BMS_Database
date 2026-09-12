"""Bounded diagnostics: enums, counts and trusted static errors, never provider prose."""
import ast
import json
from pathlib import Path

from . import intake


def response_diagnostics(response, service):
    result = {"finish_reason": "unknown"}
    if not isinstance(response, dict):
        return result
    if service == "DeepSeek":
        choices = response.get("choices")
        one = choices[0] if isinstance(choices, list) and len(choices) == 1 else None
        one = one if isinstance(one, dict) else {}
        message = one.get("message")
        message = message if isinstance(message, dict) else {}
        finish = one.get("finish_reason")
        allowed = ("stop", "length", "content_filter", "tool_calls", "insufficient_system_resource")
        result.update(content_chars=len(message["content"]) if isinstance(message.get("content"), str) else None,
                      reasoning_chars=len(message["reasoning_content"]) if isinstance(message.get("reasoning_content"), str) else None,
                      has_tool_calls=bool(message.get("tool_calls")))
    elif service == "OpenAI":
        finish = response.get("status")
        allowed = ("completed", "incomplete", "failed", "cancelled", "queued", "in_progress")
        detail = response.get("incomplete_details")
        if isinstance(detail, dict) and detail.get("reason") == "max_output_tokens":
            finish, allowed = "length", (*allowed, "length")
    else:
        candidates = response.get("candidates")
        one = candidates[0] if isinstance(candidates, list) and len(candidates) == 1 else None
        finish = one.get("finishReason") if isinstance(one, dict) else None
        allowed = ("STOP", "MAX_TOKENS", "SAFETY", "RECITATION", "OTHER", "MALFORMED_FUNCTION_CALL")
    if isinstance(finish, str) and finish in allowed:
        result["finish_reason"] = finish
    return result


def safe_detail(error):
    # Only literal raise messages in these trusted modules can appear in logs.
    # No arbitrary exception text, request/response body, stack locals or reasoning.
    allowed = {"疑点格式无效", "冲突格式无效"}
    for name in ("intake", "markup", "security", "runtime", "ledger", "models", "pipeline"):
        tree = ast.parse(Path(__file__).with_name(name + ".py").read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Raise) and isinstance(node.exc, ast.Call) and node.exc.args:
                value = node.exc.args[0]
                if isinstance(value, ast.Constant) and isinstance(value.value, str):
                    allowed.add(value.value)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "_require" and len(node.args) > 1:
                value = node.args[1]
                if isinstance(value, ast.Constant) and isinstance(value.value, str):
                    allowed.add(value.value)
    message = str(error)
    return message if message in allowed else "错误文字未列入安全白名单, 请查看回执中的阶段与状态"


def failure(receipt, error):
    if isinstance(error, intake.APIError):
        code = "AUTHENTICATION_FAILED" if error.code == 401 else "HTTP_ERROR"
    elif isinstance(error, TimeoutError):
        code = "TIMEOUT_UNKNOWN"
    elif receipt.get("diagnostics", {}).get("finish_reason") in ("length", "MAX_TOKENS"):
        code = "OUTPUT_LIMIT"
    elif isinstance(error, json.JSONDecodeError):
        code = "INVALID_JSON"
    else:
        code = {"usage_validation": "USAGE_UNCONFIRMED", "candidate_validation": "CANDIDATE_REJECTED",
                "model_response": "MODEL_RESPONSE_REJECTED"}.get(receipt.get("stage"), "STOPPED")
    result = {"code": code, "detail": safe_detail(error)}
    if isinstance(error, intake.APIError) and type(error.code) is int and 100 <= error.code <= 599:
        result["http_status"] = error.code
    return result
