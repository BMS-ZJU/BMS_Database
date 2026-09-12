"""Local, key-free walkthrough. Production workflow never imports this module."""
import argparse
import hmac
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import mimetypes
from pathlib import Path
import secrets
import sys
from urllib.parse import unquote, urlsplit

from . import intake, pipeline, security
from .ledger import Ledger

REPO = Path(__file__).resolve().parents[2]
# Deliberately reuse the offline fixtures, including their socket connection ban.
# No GitHub client, environment credentials or real provider transport is selected.
sys.path.insert(0, str(REPO / "tests"))
import test_contribution_pipeline as fixtures
from test_contributions import fields, issue, proposal


class DemoSession:
    def __init__(self, output):
        self.case = fixtures.PipelineTests()
        self.case.setUp()
        self.folder = Path(output) / secrets.token_hex(8)
        self.case.source = self.folder / "snapshot"
        self.case.output = self.folder / "review"
        self.case.receipt = self.folder / "receipt.json"
        (self.case.root / "mkdocs.yml").write_text(
            "site_name: 投稿流程演示\nsite_url: https://example.org/BMS/\n"
            "theme:\n  name: material\n  font: false\n", encoding="utf-8")
        limits = security.policy(self.case.root)
        limits.update(cumulative_calls=1, cumulative_input_chars=50000,
                      cumulative_output_tokens=limits["max_output_tokens"], max_in_flight=1)
        pipeline.write_json(self.case.root / security.POLICY_PATH, limits)
        self.phase, self.enabled, self.viewed = "new", True, False
        self.record = None
        self.content = fields()["内容"]

    def close(self):
        self.case.doCleanups()

    def state(self):
        prefix = "/artifacts/" + self.folder.name
        return {"phase": self.phase, "enabled": self.enabled,
                "mock_calls": len(self.case.calls), "real_calls": 0,
                "default_content": self.content,
                "hash": self.case.sha if self.viewed else "",
                "target": self.case.target,
                "base": self.case.env["GITHUB_SHA"],
                "snapshot_url": prefix + "/snapshot/snapshot.json" if self.viewed else None,
                "review_url": prefix + "/review/review.html" if self.phase == "review" else None,
                "preview_url": prefix + "/review/site/mandatory/example/index.html" if self.phase == "review" else None,
                "candidate_url": prefix + "/review/candidate.md" if self.phase == "review" else None}

    def action(self, name, data):
        if not isinstance(data, dict):
            raise ValueError("请求格式无效")
        if name == "stop":
            self.enabled = False
            return {}
        if not self.enabled:
            raise ValueError("演示处理已停止; 可开始新一轮演示")
        if name == "submit" and self.phase == "new":
            if set(data) != {"content", "consent"} or type(data["consent"]) is not bool:
                raise ValueError("请填写演示投稿")
            content = data["content"]
            if not isinstance(content, str) or not 1 <= len(content.strip()) <= 10000:
                raise ValueError("演示正文需为1至10000字")
            security.safe_public({"content": content})
            value = fields()
            value["内容"] = self.content = content
            value["来源与依据"] = "合成演示材料, 不对应真实课程或学生"
            value["允许使用的外部模型服务"] = "DeepSeek" if data["consent"] else "仅人工处理"
            self.case.api.issue = {**issue(value), "state": "open"}
            self.phase = "received"
        elif name == "snapshot" and self.phase == "received":
            self.case.refresh_snapshot()
            self.phase = "snapshot"
        elif name == "view" and self.phase in ("snapshot", "approved", "review"):
            self.viewed = True
            return {"snapshot_text": (self.case.source / "review.md").read_text(encoding="utf-8")}
        elif name == "approve" and self.phase == "snapshot":
            if not self.viewed or data.get("reviewed") is not True:
                raise ValueError("请先查看快照并确认已审阅")
            self.record = pipeline.reserve(self.case.root, self.case.snapshot, data.get("hash", ""),
                                           self.case.api, self.case.env)
            self.phase = "approved"
        elif name == "generate" and self.phase == "approved":
            value = proposal()
            value["summary"] = "模拟固定响应: 补充示例笔记入口, 没有调用真实模型"
            self.case.response["model"] = "demo-fixed-response-v1"
            self.case.response["choices"][0]["message"]["content"] = json.dumps(value, ensure_ascii=False)
            self.case.execute()
            receipt = security.read_json(self.case.receipt)
            Ledger(self.case.api, self.case.env["BMS_LEDGER_ANCHOR"], self.case.env["BMS_LEDGER_KEY"]).settle(
                self.record["approval_id"], self.case.env["GITHUB_RUN_ID"],
                {key: receipt[key] for key in ("state", "usage", "model_version")})
            pipeline.build_preview(self.case.root, self.case.output, self.case.output / "site")
            if (self.case.root / self.case.target).read_text(encoding="utf-8") != self.case.original:
                raise ValueError("演示源文件发生了意外变化")
            self.phase = "review"
        elif name == "change" and self.phase in ("snapshot", "approved"):
            self.case.api.issue["body"] += "\n演示: 快照之后投稿正文发生变化"
        else:
            raise ValueError("当前步骤不可执行此操作; 请按顺序操作, 不重复生成")
        return {}


def artifact_file(output, url):
    relative = unquote(urlsplit(url).path).removeprefix("/artifacts/")
    path = Path(output) / relative
    if (not path.resolve().is_relative_to(Path(output).resolve())
            or any(item.is_symlink() for item in (path, *path.parents)) or not path.is_file()):
        raise ValueError("文件不存在")
    return path


def serve(output, port):
    output = Path(output).resolve()
    if output.is_relative_to(REPO) or REPO.is_relative_to(output):
        raise ValueError("演示输出目录应位于仓库之外, 且不能是仓库的父目录")
    output.mkdir(parents=True, exist_ok=True)
    origin = f"http://127.0.0.1:{port}"
    token = secrets.token_urlsafe(32)
    current = DemoSession(output)

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def send(self, status, body, content_type="application/json; charset=utf-8"):
            if not isinstance(body, bytes):
                body = json.dumps(body, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self' 'unsafe-inline'; "
                "style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self'; connect-src 'self'; "
                "base-uri 'none'; frame-ancestors 'none'; form-action 'self'")
            self.end_headers()
            self.wfile.write(body)

        def valid_host(self):
            return self.headers.get("Host") == f"127.0.0.1:{port}"

        def do_GET(self):
            if not self.valid_host():
                return self.send(403, {"error": "只允许本机地址"})
            if self.path == "/":
                page = Path(__file__).with_suffix(".html").read_text(encoding="utf-8")
                return self.send(200, page.replace("__DEMO_TOKEN__", token).encode("utf-8"), "text/html; charset=utf-8")
            if self.path == "/api/state":
                return self.send(200, current.state())
            if self.path.startswith("/artifacts/"):
                try:
                    path = artifact_file(output, self.path)
                    mime = mimetypes.guess_type(path.name)[0] or "text/plain"
                    if path.suffix == ".md":
                        mime = "text/plain"
                    return self.send(200, path.read_bytes(), mime + ("; charset=utf-8" if mime.startswith("text/") else ""))
                except (OSError, ValueError):
                    pass
            self.send(404, {"error": "文件不存在"})

        def do_POST(self):
            nonlocal current
            if (not self.valid_host() or self.headers.get("Origin") != origin
                    or self.headers.get("Content-Type") != "application/json"
                    or not hmac.compare_digest(self.headers.get("X-Demo-Token", ""), token)):
                return self.send(403, {"error": "请求来源无效"})
            try:
                size = int(self.headers.get("Content-Length", "0"))
                if not 0 < size <= 40000:
                    raise ValueError("请求长度无效")
                data = security.strict_json(self.rfile.read(size).decode("utf-8"))
                if self.path == "/api/reset":
                    current.close()
                    current = DemoSession(output)
                    result = {}
                elif self.path.startswith("/api/"):
                    result = current.action(self.path.removeprefix("/api/"), data)
                else:
                    raise ValueError("操作不存在")
                self.send(200, {**current.state(), **result})
            except (ValueError, OSError, KeyError, TypeError, AssertionError) as error:
                self.send(400, {**current.state(), "error": "操作停止: " + str(error)})

    server = HTTPServer(("127.0.0.1", port), Handler)
    print(origin + "/", flush=True)
    try:
        server.serve_forever()
    finally:
        server.server_close()
        current.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", required=True, type=Path)
    parser.add_argument("--port", default=8977, type=int)
    args = parser.parse_args()
    serve(args.data_dir, args.port)
