"""Official API adapters. No tools, cross-provider fallback or arbitrary endpoints."""
import json


PROVIDERS = {
    "DeepSeek": ("deepseek-flash", ("deepseek-flash",), "BMS_DEEPSEEK_API_KEY"),
    "OpenAI": ("gpt-6-astra", ("gpt-6-astra",), "BMS_OPENAI_API_KEY"),
    "Gemini": ("gemini-flash-latest", ("gemini-flash-latest", "gemini-pro-latest"),
               "BMS_GEMINI_API_KEY"),
}
MAX_OUTPUT_TOKENS = 6000


def model_choice(env):
    service = env.get("BMS_MODEL_SERVICE", "").strip()
    if service not in PROVIDERS:
        raise ValueError("请选择 DeepSeek、OpenAI 或 Gemini 官方服务")
    default, allowed, secret = PROVIDERS[service]
    model = env.get("BMS_MODEL_NAME", "").strip() or default
    if model not in allowed:
        raise ValueError("模型名称与所选官方服务不匹配")
    return service, model


def configuration(env):
    service, model = model_choice(env)
    token = env.get(PROVIDERS[service][2], "").strip()
    if not token:
        raise ValueError("所选服务的密钥尚未配置")
    return service, model, token


def generate(env, rules, submission, transport, *, max_output_tokens=MAX_OUTPUT_TOKENS):
    if type(max_output_tokens) is not int or not 128 <= max_output_tokens <= MAX_OUTPUT_TOKENS:
        raise ValueError("生成上限无效")
    try:
        return _generate(env, rules, submission, transport, max_output_tokens)
    except (KeyError, IndexError, TypeError, AttributeError):
        raise ValueError("模型响应结构不完整或无效") from None


def response_metadata(response, service):
    actual = response.get("modelVersion" if service == "Gemini" else "model")
    if actual is not None and (not isinstance(actual, str) or len(actual) > 200):
        raise ValueError("模型版本格式无效")
    raw = response.get("usageMetadata" if service == "Gemini" else "usage")
    keys = {"DeepSeek": ("prompt_tokens", "completion_tokens", "total_tokens", "prompt_cache_hit_tokens", "prompt_cache_miss_tokens"),
            "OpenAI": ("input_tokens", "output_tokens", "total_tokens"),
            "Gemini": ("promptTokenCount", "candidatesTokenCount", "totalTokenCount", "thoughtsTokenCount", "cachedContentTokenCount")}
    usage = None
    if raw is not None:
        if not isinstance(raw, dict):
            raise ValueError("模型用量格式无效")
        usage = {key: raw[key] for key in keys[service] if key in raw}
        if any(type(value) is not int or not 0 <= value <= 10000000 for value in usage.values()):
            raise ValueError("模型用量格式无效")
        usage = usage or None
    return {"model_version": actual, "model_usage": usage}


def _generate(env, rules, submission, transport, max_output_tokens):
    service, model, token = configuration(env)
    if service == "DeepSeek":
        url = "https://api.deepseek.com/chat/completions"
        payload = {
            "model": model,
            "messages": [{"role": "system", "content": rules},
                         {"role": "user", "content": submission}],
            "thinking": {"type": "enabled"}, "reasoning_effort": "low",
            "max_tokens": max_output_tokens, "response_format": {"type": "json_object"},
        }
        response = transport(url, payload, token)
        choices = response.get("choices", [])
        if len(choices) != 1 or choices[0].get("finish_reason") != "stop":
            raise ValueError("模型未完整结束生成")
        message = choices[0]["message"]
        if message.get("tool_calls") or message.get("refusal"):
            raise ValueError("模型未返回文字候选")
        content = message.get("content")
    elif service == "OpenAI":
        url = "https://api.openai.com/v1/responses"
        payload = {
            "model": model, "instructions": rules, "input": submission,
            "text": {"format": {"type": "json_object"}}, "store": False,
            "reasoning": {"effort": "low"}, "max_output_tokens": max_output_tokens,
        }
        response = transport(url, payload, token)
        if response.get("status") != "completed" or response.get("error"):
            raise ValueError("模型未完整结束生成")
        texts = []
        for item in response.get("output", []):
            if item.get("type") == "reasoning":
                continue
            if item.get("type") != "message" or item.get("status") != "completed":
                raise ValueError("模型返回了非文字结果")
            for part in item.get("content", []):
                if part.get("type") != "output_text":
                    raise ValueError("模型拒绝或未返回文字候选")
                texts.append(part["text"])
        content = "".join(texts)
    else:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
        payload = {
            "systemInstruction": {"parts": [{"text": rules}]},
            "contents": [{"role": "user", "parts": [{"text": submission}]}],
            "generationConfig": {"responseMimeType": "application/json", "candidateCount": 1,
                                 "maxOutputTokens": max_output_tokens},
        }
        response = transport(url, payload, token, auth_header="x-goog-api-key")
        candidates = response.get("candidates", [])
        if (response.get("promptFeedback", {}).get("blockReason")
                or len(candidates) != 1 or candidates[0].get("finishReason") != "STOP"):
            raise ValueError("模型未完整结束生成")
        texts = []
        for part in candidates[0].get("content", {}).get("parts", []):
            if part.get("thought"):
                continue
            if "text" not in part or set(part) - {"text", "thought", "thoughtSignature"}:
                raise ValueError("模型返回了非文字结果")
            texts.append(part["text"])
        content = "".join(texts)
    if not isinstance(content, str) or not content.strip() or len(content) > 30000:
        raise ValueError("模型输出为空、超过上限或格式不符")
    from .security import strict_json
    return strict_json(content), {"model_service": service, "model_name": model,
                                  **response_metadata(response, service)}
