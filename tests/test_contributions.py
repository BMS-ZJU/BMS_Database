import copy
import json
import re
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

import yaml
from scripts.contributions import intake
from scripts.contributions import models
from scripts.contributions import security
from scripts.contributions.catalog import AUTO_COURSE, GENERAL, UNKNOWN, courses, sync_forms

REPO = Path(__file__).resolve().parents[1]


def fields():
    return {"课程": "示例课程", "页面地址": "https://example.org/BMS/courses/example/",
            "内容": "我提供的公开链接为 https://example.org/notes",
            "来源与依据": "本人整理的学习笔记", "本站使用范围": intake.SCOPES[1],
            "允许使用的外部模型服务": "DeepSeek", "Ginkgo 使用意愿": "未同意或尚未确认",
            "公开确认": "- [X] " + intake.PUBLIC}


def issue(value=None):
    return {"number": 123, "title": "[资料] 示例", "updated_at": "2026-09-12T00:00:00Z",
            "body": "\n\n".join("### " + k + "\n\n" + v for k, v in (value or fields()).items())}


def proposal():
    return {"summary": "补充笔记入口", "changes": [{
        "before": "现有资料入口。", "after": "现有资料入口。\n\n- [学习笔记](https://example.org/notes)",
        "reason": "作者提供公开笔记链接",
        "evidence": [{"id": "内容:L1", "quote": "公开链接为 https://example.org/notes"}],
    }], "questions": [], "conflicts": []}


def environment():
    return {"BMS_AI_ENABLED": "true", "BMS_MODEL_SERVICE": "DeepSeek",
            "BMS_DEEPSEEK_API_KEY": "test-deepseek", "BMS_OPENAI_API_KEY": "test-openai",
            "BMS_GEMINI_API_KEY": "test-gemini",
            "GH_TOKEN": "github-token-must-not-reach-model"}


def response_for(service, content=None):
    if content is None:
        content = json.dumps(proposal(), ensure_ascii=False)
    if service == "DeepSeek":
        return {"model": "fixture-deepseek-version", "choices": [{"finish_reason": "stop",
                "message": {"content": content, "reasoning_content": "不作为候选"}}]}
    if service == "OpenAI":
        return {"model": "fixture-openai-version", "status": "completed", "output": [
            {"type": "reasoning", "summary": []},
            {"type": "message", "status": "completed", "content": [
                {"type": "output_text", "text": content}]}]}
    return {"modelVersion": "fixture-gemini-version", "candidates": [{"finishReason": "STOP",
            "content": {"parts": [{"thought": True, "text": "不作为候选"}, {"text": content}]}}]}


def load_workflow():
    return yaml.load((REPO / ".github/workflows/contribution-intake.yml").read_text(encoding="utf-8"),
                     Loader=yaml.BaseLoader)


class IntakeTests(unittest.TestCase):
    def setUp(self):
        for method in ("connect", "connect_ex"):
            self.enterContext(patch("socket.socket." + method,
                                    side_effect=AssertionError("测试禁止联网")))
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / "repo"
        self.target = "docs/courses/example/index.md"
        path = self.root / self.target
        path.parent.mkdir(parents=True)
        self.original = "---\ntitle: 示例\n---\n# 示例\n\n现有资料入口。\n"
        path.write_text(self.original, encoding="utf-8")
        (self.root / "data").mkdir(exist_ok=True)
        (self.root / "data/courses.yml").write_text(
            "courses:\n  - path: courses/example\n    chinese_name: 示例课程\n", encoding="utf-8")
        (self.root / "mkdocs.yml").write_text("site_url: https://example.org/BMS/\n", encoding="utf-8")
        rules = self.root / "scripts/contributions/rules.md"
        rules.parent.mkdir(parents=True)
        rules.write_text("仅用于测试", encoding="utf-8")
        self.output = Path(self.tmp.name) / "review"
        self.units = intake.evidence_units(fields())
        self.rules = rules.read_text(encoding="utf-8")

    def model_submission(self, value=None):
        value = fields() if value is None else value
        return json.dumps({"submission": value, "source_units": intake.evidence_units(value),
                           "current_page": self.original}, ensure_ascii=False)

    def validate(self, value):
        return intake.validate_proposal(value, self.original, self.units, fields())

    def test_valid_change_is_free_and_auditable_even_with_all_model_keys(self):
        for service, (_, allowed, _) in models.PROVIDERS.items():
            for model in allowed:
                with self.subTest(service=service, model=model):
                    env = {**environment(), "BMS_MODEL_SERVICE": service, "BMS_MODEL_NAME": model}
                    value = {**fields(), "允许使用的外部模型服务": service}
                    submission = issue(value)
                    transport = Mock(side_effect=AssertionError("免费收件不能调用模型"))
                    with patch.object(models, "generate") as generate:
                        self.assertFalse(intake.prepare(
                            self.root, self.target, submission, self.output, env, transport))
                    transport.assert_not_called()
                    generate.assert_not_called()
                    self.assertEqual((self.root / self.target).read_text(encoding="utf-8"), self.original)
                    self.assertEqual((self.output / "candidate.md").read_text(encoding="utf-8"), self.original)
                    snapshot = json.loads((self.output / "snapshot.json").read_text(encoding="utf-8"))
                    self.assertEqual(snapshot["submission_sha256"], intake.digest(submission["body"]))
                    self.assertEqual(snapshot["page_sha256"], intake.digest(self.original))
                    self.assertEqual(snapshot["fields"], value)
                    self.assertEqual(snapshot["fields"]["Ginkgo 使用意愿"], "未同意或尚未确认")
                    self.assertEqual(snapshot["source_units"], intake.evidence_units(value))
                    for key in ("model_service", "model_name", "model_version"):
                        self.assertIsNone(snapshot[key])
                    result = json.loads((self.output / "proposal.json").read_text(encoding="utf-8"))
                    self.assertEqual(result["changes"], [])
                    report = (self.output / "review.md").read_text(encoding="utf-8")
                    report_html = (self.output / "review.html").read_text(encoding="utf-8")
                    for source in ("内容:L1", "来源与依据:L1", value["来源与依据"]):
                        self.assertIn(source, report)
                        self.assertIn(source, report_html)
                    self.assertNotIn("site/courses/example/index.html", report_html)
                    artifacts = "".join(path.read_text(encoding="utf-8") for path in self.output.iterdir())
                    for key in ("GH_TOKEN", *(item[2] for item in models.PROVIDERS.values())):
                        self.assertNotIn(env[key], artifacts)

    def test_free_receipts_do_not_depend_on_model_configuration_or_consent(self):
        def forbidden(*args, **kwargs):
            self.fail("不应调用模型")
        for override in ({"BMS_AI_ENABLED": ""}, {"BMS_MODEL_SERVICE": "其他服务"},
                         {"BMS_DEEPSEEK_API_KEY": ""}, {"BMS_MODEL_NAME": "gpt-6-astra"}):
            env = {**environment(), **override}
            self.assertFalse(intake.prepare(self.root, self.target, issue(), self.output, env, forbidden))
        value = fields()
        value["本站使用范围"] = intake.SCOPES[0]
        self.assertFalse(intake.prepare(self.root, self.target, issue(value), self.output, environment(), forbidden))

    def test_missing_public_confirmation_writes_nothing(self):
        value = fields()
        value["公开确认"] = "- [ ] " + intake.PUBLIC
        with self.assertRaises(ValueError):
            intake.prepare(self.root, self.target, issue(value), self.output, environment())
        self.assertFalse(self.output.exists())

    def test_duplicate_or_unknown_field_fails_closed(self):
        for extra in ("\n### 公开确认\n- [X] " + intake.PUBLIC, "\n### 任意字段\n内容"):
            with self.assertRaises(ValueError):
                intake.parse_fields(issue()["body"] + extra)

    def test_path_traversal_configuration_and_unknown_courses_rejected(self):
        for target in ("../mkdocs.yml", "docs/courses/example/../../index.md",
                       ".github/workflows/deploy.yml", "docs/courses/unknown/index.md",
                       "docs/courses/example/index.md/other", "C:/tmp/a.md"):
            with self.subTest(target=target), self.assertRaises(ValueError):
                intake.resolve_target(self.root, target)

    def test_symlink_target_rejected(self):
        link = self.root / "docs/courses/example/link.md"
        try:
            link.symlink_to(self.root / self.target)
        except OSError:
            self.skipTest("此环境没有符号链接权限")
        with self.assertRaises(ValueError):
            intake.resolve_target(self.root, "docs/courses/example/link.md")

    def test_fabricated_evidence_is_rejected(self):
        for change in ({"id": "附件第3页", "quote": "原文中不存在的资料"},
                       {"id": "内容:L1", "quote": "原文中不存在的资料"}):
            value = proposal()
            value["changes"][0]["evidence"] = [change]
            with self.assertRaises(ValueError):
                self.validate(value)

    def test_conflicts_and_stale_snippets_do_not_apply(self):
        value = proposal()
        value["conflicts"] = ["投稿与原文存在冲突"]
        with self.assertRaises(ValueError):
            self.validate(value)
        value = proposal()
        value["changes"][0]["before"] = "已经变化的原文"
        with self.assertRaises(ValueError):
            self.validate(value)

    def test_script_markup_and_metadata_are_rejected(self):
        for after in ('<script>alert(1)</script>', '[链接](javascript:alert)',
                      '[链接](jav&#x61;script:alert)', '{{ arbitrary }}',
                      '文字{: onclick="alert(1)"}', '![远程图](https://example.org/x)'):
            value = proposal()
            value["changes"][0]["after"] = after
            with self.subTest(after=after), self.assertRaises(ValueError):
                self.validate(value)
        value = proposal()
        value["changes"][0].update(before="title: 示例", after="title: 修改")
        with self.assertRaises(ValueError):
            self.validate(value)

    def test_overlap_and_model_selected_path_are_rejected(self):
        value = proposal()
        value["changes"].append(copy.deepcopy(value["changes"][0]))
        with self.assertRaises(ValueError):
            self.validate(value)
        value = proposal()
        value["path"] = ".github/workflows/deploy.yml"
        with self.assertRaises(ValueError):
            self.validate(value)

    def test_attachment_reuse_needs_separate_permission(self):
        value = proposal()
        value["changes"][0]["after"] = "[附件](https://github.com/user-attachments/files/123/a.pdf)"
        with self.assertRaises(ValueError):
            self.validate(value)

    def test_report_escapes_untrusted_html_and_fences(self):
        value = fields()
        value["内容"] += "\n</pre><script>alert(1)</script>\n" + "\x60" * 10
        intake.prepare(self.root, self.target, issue(value), self.output, {}, None)
        report = (self.output / "review.html").read_text(encoding="utf-8")
        self.assertNotIn("<script>", report)
        self.assertIn("&lt;script&gt;", report)
        self.assertIn("\x60" * 11, (self.output / "review.md").read_text(encoding="utf-8"))

    def test_malformed_model_response_produces_no_artifact(self):
        for service in models.PROVIDERS:
            for content in (json.dumps({"shell": "run this"}), '{"summary":'):
                with self.subTest(service=service, content=content):
                    env = {**environment(), "BMS_MODEL_SERVICE": service}
                    transport = Mock(return_value=response_for(service, content))
                    with self.assertRaises(ValueError):
                        generated, _ = models.generate(env, self.rules, self.model_submission(), transport)
                        self.validate(generated)
                    self.assertEqual(transport.call_count, 1)
                    self.assertFalse(self.output.exists())
                    self.assertEqual((self.root / self.target).read_text(encoding="utf-8"), self.original)

    def test_form_contracts_and_workflow_permissions(self):
        sync_forms(REPO, check=True)
        for filename in ("material.yml", "correction.yml", "material-direct.yml", "correction-direct.yml"):
            form = yaml.safe_load((REPO / ".github/ISSUE_TEMPLATE" / filename).read_text(encoding="utf-8"))
            controls = [entry for entry in form["body"] if entry["type"] != "markdown"]
            labels = [entry["attributes"]["label"] for entry in controls]
            exclusive = {"问题位置与现状", "建议修改"} if filename.startswith("material") else {"内容"}
            self.assertEqual(set(labels), set(intake.LABELS) - exclusive)
            self.assertEqual(len(labels), len(set(labels)))
            primary = "content" if filename.startswith("material") else "problem"
            self.assertTrue(next(e for e in controls if e["id"] == primary)["validations"]["required"])
            course = next(e for e in controls if e["id"] == "course")
            if "-direct" in filename:
                self.assertEqual(course["type"], "dropdown")
                self.assertEqual(course["attributes"]["options"],
                                 [c["label"] for c in courses(REPO)] + [GENERAL, UNKNOWN])
                self.assertNotIn("default", course["attributes"])
            else:
                self.assertEqual(course["type"], "input")
                self.assertEqual(course["attributes"]["value"], AUTO_COURSE)
                self.assertNotIn("options", course["attributes"])
                self.assertNotIn("default", course["attributes"])
            self.assertTrue(course["validations"]["required"])
            service = next(e for e in controls if e["id"] == "model_service")
            self.assertEqual(service["type"], "dropdown")
            self.assertEqual(service["attributes"]["options"], ["仅人工处理", *models.PROVIDERS])
            self.assertEqual(service["attributes"]["default"], 0)
            confirmation = next(e for e in controls if e["id"] == "public_confirmation")
            self.assertEqual(confirmation["attributes"]["options"][0]["label"], intake.PUBLIC)

        workflow = load_workflow()
        self.assertEqual(set(workflow["on"]), {"workflow_dispatch"})
        self.assertEqual(workflow["on"]["workflow_dispatch"]["inputs"]["operation"]["default"], "snapshot")
        permissions = {"contents": "read", "issues": "read", "actions": "read"}
        self.assertEqual(workflow["permissions"], permissions)
        jobs = workflow["jobs"]
        self.assertEqual(jobs["checks"]["if"],
                         "github.ref == format('refs/heads/{0}', github.event.repository.default_branch)"
                         " && github.run_attempt == 1")
        for name in ("snapshot", "reserve", "ledger-maintenance"):
            self.assertEqual(jobs[name]["needs"], "checks")
        self.assertEqual(jobs["snapshot"]["if"], "inputs.operation == 'snapshot'")
        self.assertEqual(jobs["reserve"]["if"], "inputs.operation == 'process'")
        self.assertEqual(jobs["model"]["needs"], "reserve")
        self.assertEqual(set(jobs["settle"]["needs"]), {"reserve", "model"})
        self.assertEqual(jobs["settle"]["if"], "always() && needs.reserve.result == 'success'")
        self.assertEqual(jobs["ledger-maintenance"]["if"],
                         "inputs.operation == 'initialize' || inputs.operation == 'reconcile'")
        ledger_jobs = {"reserve": ("reserve",), "settle": ("settle",),
                       "ledger-maintenance": ("initialize", "reconcile")}
        write_jobs = {name for name, job in jobs.items()
                      if "write" in job.get("permissions", permissions).values()}
        self.assertEqual(write_jobs, set(ledger_jobs))
        for name, commands in ledger_jobs.items():
            job = jobs[name]
            self.assertEqual(job["permissions"], {**permissions, "contents": "write"})
            operations = [operation for step in job["steps"]
                          for operation in re.findall(r"scripts\.contributions\.pipeline\s+(\w+)",
                                                       step.get("run", ""))]
            self.assertCountEqual(operations, commands)
        for name, job in jobs.items():
            with self.subTest(job=name):
                if name not in ledger_jobs:
                    self.assertTrue(all(level == "read" for level in
                                        job.get("permissions", permissions).values()))
                checkouts = [step for step in job["steps"]
                             if step.get("uses", "").startswith("actions/checkout@")]
                self.assertEqual(len(checkouts), 1)
                self.assertEqual(checkouts[0]["with"]["ref"], "${{ github.sha }}")
                self.assertEqual(checkouts[0]["with"]["persist-credentials"], "false")

    def test_automatic_checks_cannot_enter_paid_workflow(self):
        checks = yaml.load((REPO / ".github/workflows/contribution-checks.yml").read_text(encoding="utf-8"),
                           Loader=yaml.BaseLoader)
        self.assertEqual(set(checks["on"]), {"push", "pull_request"})
        self.assertEqual(checks["permissions"], {"contents": "read"})
        self.assertEqual(set(checks["jobs"]), {"tests"})
        job = checks["jobs"]["tests"]
        self.assertNotIn("environment", job)
        self.assertNotIn("permissions", job)
        self.assertNotIn("uses", job)  # Cannot call a privileged reusable workflow.
        text = json.dumps(checks)
        self.assertNotIn("secrets.", text)
        self.assertNotIn("github.token", text)
        self.assertNotIn("scripts.contributions.pipeline", text)
        self.assertNotIn("workflow_dispatch", text)
        checkout = next(step for step in job["steps"] if step.get("uses", "").startswith("actions/checkout@"))
        self.assertEqual(checkout["with"]["persist-credentials"], "false")
        runs = [step["run"] for step in job["steps"] if "run" in step]
        self.assertEqual(runs, ["python -m pip install -r requirements.txt",
                               'python -m unittest discover -s tests -p "test_contribution*.py"'])
        # The separate paid entry still has no push, PR, issue or comment trigger.
        self.assertEqual(set(load_workflow()["on"]), {"workflow_dispatch"})

    def test_workflow_model_secrets_are_confined_to_three_exclusive_steps(self):
        workflow = load_workflow()
        self.assertNotRegex(json.dumps({key: value for key, value in workflow.items() if key != "jobs"}),
                            r"\bsecrets\b")
        key_names = {item[2] for item in models.PROVIDERS.values()}
        self.assertTrue(key_names.isdisjoint(workflow.get("env", {})))
        model = workflow["jobs"]["model"]
        self.assertEqual(model["permissions"], {"contents": "read", "issues": "read", "actions": "read"})
        call_command = ('python -m scripts.contributions.pipeline call'
                        ' --source "$RUNNER_TEMP/contribution-source"'
                        ' --output "$RUNNER_TEMP/contribution-review"'
                        ' --receipt "$RUNNER_TEMP/contribution-receipt/receipt.json"')
        call_steps = [step for step in model["steps"]
                      if re.search(r"scripts\.contributions\.pipeline\s+call\b", step.get("run", ""))]
        self.assertEqual(len(call_steps), 3)
        self.assertCountEqual([step.get("if") for step in call_steps],
                              [f"needs.reserve.outputs.service == '{service}'" for service in models.PROVIDERS])
        for service, (_, _, key) in models.PROVIDERS.items():
            step = next(step for step in call_steps if step["if"] == f"needs.reserve.outputs.service == '{service}'")
            with self.subTest(service=service):
                self.assertEqual(step["run"], call_command)
                self.assertEqual(step["env"], {
                    "GH_TOKEN": "${{ github.token }}",
                    "BMS_LEDGER_KEY": "${{ secrets.CONTRIBUTION_LEDGER_KEY }}",
                    key: "${{ secrets.CONTRIBUTION_" + service.upper() + "_API_KEY }}",
                })
                self.assertEqual(len(re.findall(r"\bsecrets\b", json.dumps(step))), 2)
        for name, job in workflow["jobs"].items():
            self.assertNotRegex(json.dumps({key: value for key, value in job.items() if key != "steps"}),
                                r"\bsecrets\b")
            self.assertTrue(key_names.isdisjoint(job.get("env", {})))
            for step in job["steps"]:
                if name == "model" and step in call_steps:
                    continue
                if "BMS_LEDGER_KEY" in step.get("env", {}):
                    self.assertIn(name, ("reserve", "settle", "ledger-maintenance"))
                    self.assertEqual(step["env"]["BMS_LEDGER_KEY"], "${{ secrets.CONTRIBUTION_LEDGER_KEY }}")
                    self.assertEqual(len(re.findall(r"\bsecrets\b", json.dumps(step))), 1)
                    self.assertEqual(job["environment"], "contribution-model")
                else:
                    self.assertNotRegex(json.dumps(step), r"\bsecrets\b")
                self.assertTrue(key_names.isdisjoint(step.get("env", {})))
                self.assertNotRegex(step.get("run", ""), r"scripts\.contributions\.pipeline\s+call\b")

    def test_workflow_preview_builds_without_model_secrets_or_source_write_route(self):
        workflow = load_workflow()
        preview = workflow["jobs"]["preview"]
        self.assertEqual(preview["needs"], "model")
        self.assertEqual(preview["permissions"], {"contents": "read"})
        self.assertNotRegex(json.dumps(preview), r"\bsecrets\b")
        self.assertNotIn("--apply-preview", json.dumps(workflow))
        self.assertNotIn("scripts.contributions.intake", json.dumps(workflow))
        build_steps = [step for step in preview["steps"]
                       if re.search(r"scripts\.contributions\.pipeline\s+build\b", step.get("run", ""))]
        self.assertEqual(len(build_steps), 1)
        self.assertEqual(build_steps[0]["run"],
                         'python -m scripts.contributions.pipeline build'
                         ' --source "$RUNNER_TEMP/contribution-review"'
                         ' --output "$RUNNER_TEMP/contribution-review/site"')

    def test_course_and_page_binding_precedes_network_and_output(self):
        def forbidden(*args, **kwargs):
            self.fail("错误定位不应触发模型")
        for override in (
            {"课程": "别的课程"}, {"课程": ""}, {"页面地址": ""},
            {"页面地址": "https://evil.example/BMS/courses/example/"},
            {"页面地址": "https://example.org/BMS/courses/example/exams/"},
            {"页面地址": "https://example.org/BMS/courses/example/?redirect=elsewhere"},
            {"页面地址": "https://example.org/BMS/courses/example/../other/"},
        ):
            with self.subTest(override=override), self.assertRaises(ValueError):
                intake.prepare(self.root, self.target, issue({**fields(), **override}),
                               self.output, environment(), forbidden)
            self.assertFalse(self.output.exists())
        value = {**fields(), "页面地址": fields()["页面地址"] + "#notes"}
        intake.validate_selection(self.root, self.target, value)

    def test_auto_course_still_requires_the_exact_approved_page(self):
        transport = Mock(side_effect=AssertionError("自动匹配不应调用模型"))
        for address in ("", "https://evil.example/BMS/courses/example/",
                        "https://example.org/BMS/courses/other/",
                        "https://example.org/BMS/courses/example/exams/",
                        "https://example.org/BMS/courses/example/../other/",
                        "https://example.org/BMS/courses/example/?redirect=elsewhere",
                        "https://example.org@evil.example/BMS/courses/example/"):
            value = {**fields(), "课程": AUTO_COURSE, "页面地址": address}
            with self.subTest(address=address), self.assertRaises(ValueError):
                intake.prepare(self.root, self.target, issue(value), self.output, environment(), transport)
            self.assertFalse(self.output.exists())
        transport.assert_not_called()
        # Explicit selections remain binding even when the page address is correct.
        for course in ("", "None", "站点公共页面", "未找到课程或页面 (人工核对)", "别的课程"):
            with self.subTest(course=course), self.assertRaises(ValueError):
                intake.validate_selection(self.root, self.target, {**fields(), "课程": course})

    def test_auto_course_keeps_submission_and_course_code_boundaries(self):
        (self.root / "data").mkdir(exist_ok=True)
        (self.root / "data/courses.yml").write_text(
            "courses:\n  - path: courses/example\n    chinese_name: 示例课程\n    course_code: MED01\n"
            "  - path: courses/example-alternate\n    chinese_name: 示例课程\n    course_code: MED02\n", encoding="utf-8")
        value = {**fields(), "课程": AUTO_COURSE}
        submission = issue(value)
        transport = Mock(side_effect=AssertionError("收件不应调用模型"))
        self.assertFalse(intake.prepare(self.root, self.target, submission, self.output, {}, transport))
        transport.assert_not_called()
        snapshot = json.loads((self.output / "snapshot.json").read_text(encoding="utf-8"))
        self.assertEqual(snapshot["issue"], submission)
        self.assertEqual(snapshot["fields"], value)
        self.assertEqual(snapshot["target"], self.target)
        with self.assertRaises(ValueError):
            intake.validate_selection(self.root, "docs/courses/example-alternate/index.md", value)

    def test_correction_fields_keep_problem_and_suggestion_as_evidence(self):
        value = fields()
        del value["内容"]
        value.update({"问题位置与现状": "笔记链接打不开", "建议修改": "请核对原作者的新链接"})
        parsed = intake.parse_fields(issue(value)["body"])
        self.assertIn("笔记链接打不开", parsed["内容"])
        self.assertEqual("请核对原作者的新链接", intake.evidence_units(parsed)["建议修改:L1"])
        self.assertFalse(intake.prepare(self.root, self.target, issue(value), self.output, {}))
        value["内容"] = "混入另一种表单"
        with self.assertRaises(ValueError):
            intake.parse_fields(issue(value)["body"])

    def test_all_official_adapters_generate_auditable_candidates(self):
        cases = [
            ("DeepSeek", "deepseek-flash", "https://api.deepseek.com/chat/completions", "test-deepseek"),
            ("OpenAI", "gpt-6-astra", "https://api.openai.com/v1/responses", "test-openai"),
            ("Gemini", "gemini-flash-latest", "https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent", "test-gemini"),
            ("Gemini", "gemini-pro-latest", "https://generativelanguage.googleapis.com/v1beta/models/gemini-pro-latest:generateContent", "test-gemini"),
        ]
        for service, model, endpoint, secret in cases:
            calls = []
            def transport(url, payload, token, **kwargs):
                calls.append((url, payload, token, kwargs))
                return response_for(service)
            with self.subTest(service=service, model=model):
                env = {**environment(), "BMS_MODEL_SERVICE": service, "BMS_MODEL_NAME": model,
                       "BMS_MODEL_ENDPOINT": "https://untrusted.invalid/ignored"}
                value = {**fields(), "允许使用的外部模型服务": service}
                generated, metadata = models.generate(env, self.rules, self.model_submission(value), transport)
                self.assertEqual(generated, proposal())
                candidate = intake.validate_proposal(generated, self.original, intake.evidence_units(value), value)
                self.assertEqual(candidate, self.original.replace(
                    generated["changes"][0]["before"], generated["changes"][0]["after"]))
                self.assertNotEqual(candidate, self.original)
                self.assertEqual((self.root / self.target).read_text(encoding="utf-8"), self.original)
                self.assertFalse(self.output.exists())
                self.assertEqual(len(calls), 1)
                url, payload, token, kwargs = calls[0]
                self.assertEqual(url, endpoint)
                self.assertEqual(token, secret)
                self.assertEqual(kwargs, {"auth_header": "x-goog-api-key"} if service == "Gemini" else {})
                self.assertNotIn("tools", payload)
                self.assertNotIn("temperature", payload)
                if service == "OpenAI":
                    self.assertIs(payload["store"], False)
                    self.assertEqual(payload["text"]["format"], {"type": "json_object"})
                serialized = json.dumps(payload)
                self.assertEqual(metadata["model_service"], service)
                self.assertEqual(metadata["model_name"], model)
                self.assertEqual(metadata["model_version"], "fixture-" + service.lower() + "-version")
                self.assertIsNone(metadata["model_usage"])
                for credential in ("test-deepseek", "test-openai", "test-gemini", env["GH_TOKEN"]):
                    self.assertNotIn(credential, serialized + json.dumps(metadata))

    def test_provider_selection_does_not_reuse_consent_or_other_keys(self):
        forbidden = Mock(side_effect=AssertionError("配置或同意不匹配时不能调用模型"))
        for service, (_, _, key) in models.PROVIDERS.items():
            env = {**environment(), "BMS_MODEL_SERVICE": service, key: ""}
            value = {**fields(), "允许使用的外部模型服务": service}
            with self.subTest(service=service, missing_key=key):
                with self.assertRaises(ValueError):
                    models.generate(env, self.rules, self.model_submission(value), forbidden)
                forbidden.assert_not_called()
                self.assertFalse(self.output.exists())
            env[key] = "mock"
            self.assertEqual(models.configuration(env)[2], "mock")
            snapshot = {"fields": value, "model_service": service, "policy": {
                "cumulative_calls": 1, "cumulative_input_chars": 10000, "cumulative_output_tokens": 6000}}
            security.eligible(snapshot, env)
            with self.subTest(service=service, enabled=False), self.assertRaises(ValueError):
                security.eligible(snapshot, {**env, "BMS_AI_ENABLED": ""})
            for consent in ("仅人工处理", "", "DeepSeek, OpenAI", "未知服务",
                            *(other for other in models.PROVIDERS if other != service)):
                value["允许使用的外部模型服务"] = consent
                with self.subTest(service=service, consent=consent), self.assertRaises(ValueError):
                    security.eligible(snapshot, env)
            value["允许使用的外部模型服务"] = service
            value["本站使用范围"] = intake.SCOPES[0]
            with self.subTest(service=service, scope=intake.SCOPES[0]), self.assertRaises(ValueError):
                security.eligible(snapshot, env)
        forbidden.assert_not_called()

    def test_provider_model_allowlist_blocks_arbitrary_routes(self):
        for service in models.PROVIDERS:
            for model in ("../other", "gemini-pro-latest?key=oops", "unknown", "https://evil.invalid"):
                with self.subTest(service=service, model=model), self.assertRaises(ValueError):
                    models.configuration({**environment(), "BMS_MODEL_SERVICE": service, "BMS_MODEL_NAME": model})
            _, model, _ = models.configuration({**environment(), "BMS_MODEL_SERVICE": service})
            self.assertEqual(model, models.PROVIDERS[service][0])

    def test_truncation_refusal_and_unexpected_outputs_write_nothing(self):
        cases = []
        for service in models.PROVIDERS:
            cases.extend((service, bad) for bad in (None, {}, {"error": {"message": "not logged"}}))
            truncated = response_for(service)
            if service == "DeepSeek":
                truncated["choices"][0]["finish_reason"] = "length"
                refusal = response_for(service)
                refusal["choices"][0]["message"]["tool_calls"] = [{"name": "shell"}]
            elif service == "OpenAI":
                truncated["status"] = "incomplete"
                refusal = response_for(service)
                refusal["output"][1]["content"] = [{"type": "refusal", "refusal": "拒绝"}]
            else:
                truncated["candidates"][0]["finishReason"] = "MAX_TOKENS"
                refusal = response_for(service)
                refusal["candidates"][0]["content"]["parts"] = [{"functionCall": {"name": "shell"}}]
            cases.extend(((service, truncated), (service, refusal)))
        for service, bad in cases:
            with self.subTest(service=service, response=bad), self.assertRaises(ValueError):
                generated, _ = models.generate(
                    {**environment(), "BMS_MODEL_SERVICE": service}, self.rules,
                    self.model_submission({**fields(), "允许使用的外部模型服务": service}),
                    lambda *args, **kwargs: bad)
                self.validate(generated)
            self.assertFalse(self.output.exists())

    def test_provider_failure_is_not_retried_or_routed_elsewhere(self):
        for service in models.PROVIDERS:
            calls = []
            def transport(*args, **kwargs):
                calls.append(args[0])
                raise OSError("模拟超时")
            with self.assertRaises(OSError):
                models.generate({**environment(), "BMS_MODEL_SERVICE": service}, self.rules,
                                self.model_submission({**fields(), "允许使用的外部模型服务": service}), transport)
            self.assertEqual(len(calls), 1)
            self.assertFalse(self.output.exists())

    def test_gemini_key_is_sent_only_in_header(self):
        class Response:
            def __enter__(self): return self
            def __exit__(self, *args): return False
            def read(self, limit): return b'{}'
        with patch.object(intake, "build_opener") as opener:
            opener.return_value.open.return_value = Response()
            url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent"
            intake.request_json(url, {"contents": []}, "fixture-key", auth_header="x-goog-api-key")
            request = opener.return_value.open.call_args.args[0]
            self.assertEqual(request.full_url, url)
            self.assertEqual(request.get_header("X-goog-api-key"), "fixture-key")
            self.assertIsNone(request.get_header("Authorization"))
            self.assertNotIn(b"fixture-key", request.data)

    def test_course_codes_disambiguate_same_name_and_html_urls(self):
        (self.root / "data").mkdir(exist_ok=True)
        (self.root / "data/courses.yml").write_text(
            "courses:\n  - path: courses/example\n    chinese_name: 示例课程\n    course_code: MED01\n"
            "  - path: courses/example-alternate\n    chinese_name: 示例课程\n    course_code: MED02\n", encoding="utf-8")
        for label in ("示例课程", "示例课程 (MED02)"):
            with self.assertRaises(ValueError):
                intake.validate_selection(self.root, self.target, {**fields(), "课程": label})
        (self.root / "mkdocs.yml").write_text(
            "site_url: https://example.org/BMS/\nuse_directory_urls: false\n", encoding="utf-8")
        value = {**fields(), "课程": "示例课程 (MED01)",
                 "页面地址": "https://example.org/BMS/courses/example/index.html"}
        intake.validate_selection(self.root, self.target, value)


if __name__ == "__main__":
    unittest.main()
