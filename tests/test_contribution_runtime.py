"""Formal migration checks; every model call uses the socket-blocked shared fixture."""
import copy
import json
import sys
import unittest
from unittest.mock import Mock, patch

from scripts.contributions import diagnostics, intake, models, pipeline, runtime, security as sec
import test_contribution_pipeline as existing


class RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.case = existing.PipelineTests()
        self.case.setUp()
        self.addCleanup(self.case.doCleanups)

    def test_wrong_repository_stops_before_git_or_github(self):
        c = self.case
        with patch.dict("os.environ", {**c.env, "GITHUB_REPOSITORY": "other/other"}, clear=True), \
                patch.object(sys, "argv", ["pipeline", "initialize", "--root", str(c.root)]), \
                patch.object(sec, "GitHub") as network, patch.object(pipeline.subprocess, "run") as git, \
                self.assertRaises(ValueError):
            pipeline.main()
        network.assert_not_called()
        git.assert_not_called()
        self.assertEqual(c.calls, [])

    def test_invalid_or_missing_scope_stops_before_network(self):
        c = self.case
        for value in ({"repository": "REPLACE/repo", "real_calls_enabled": False},
                      {"repository": c.api.repository, "real_calls_enabled": "true"}, {}):
            pipeline.write_json(c.root / runtime.CONFIG, value)
            api = Mock()
            with self.assertRaises((ValueError, KeyError)):
                runtime.guard(c.root, api, c.env)
            api.assert_not_called()
        (c.root / runtime.CONFIG).unlink()
        c.blocked(c.process)

    def test_actual_api_repository_must_match(self):
        c = self.case
        api = Mock(return_value={"full_name": "other/other"})
        api.repository = c.api.repository
        with self.assertRaises(ValueError): runtime.guard(c.root, api, c.env)
        self.assertEqual(c.calls, [])

    def test_missing_default_branch_protection_stops(self):
        c = self.case
        c.api.main_rules = []
        c.blocked(c.process)

    def test_closed_source_switch_allows_snapshot_but_never_call(self):
        c = self.case
        pipeline.write_json(c.root / runtime.CONFIG, {"repository": c.api.repository, "real_calls_enabled": False})
        c.refresh_snapshot()
        self.assertTrue((c.source / "review.md").is_file())
        c.blocked(c.process)

    def test_changed_repository_configuration_invalidates_approval(self):
        c = self.case
        pipeline.write_json(c.root / runtime.CONFIG, {"repository": c.api.repository, "real_calls_enabled": False})
        c.blocked(c.process)

    def test_live_stop_is_checked_immediately_before_transport(self):
        c = self.case
        c.reserve()
        generate = models.generate
        def close_gate(*args, **kwargs):
            pipeline.write_json(c.root / runtime.CONFIG, {"repository": c.api.repository, "real_calls_enabled": False})
            return generate(*args, **kwargs)
        with patch.object(models, "generate", side_effect=close_gate), self.assertRaises(ValueError):
            c.execute()
        self.assertEqual(c.calls, [])
        self.assertFalse(c.output.exists())

    def test_changed_live_switch_and_read_failure_never_reach_provider(self):
        c = self.case
        original = c.api.dispatch
        def changed(path, payload, method):
            if path == "/contents/" + runtime.CONFIG + "?ref=main":
                raise OSError("synthetic read failure")
            return original(path, payload, method)
        c.api.dispatch = changed
        c.blocked(c.process)

    def test_formal_configuration_retains_repository_and_one_call_boundary(self):
        # Validate trusted configuration without forbidding an explicitly reviewed activation.
        # Missing/closed gates and zero budgets are exercised with isolated fixtures below.
        config = runtime.local_scope(existing.REPO, {"GITHUB_REPOSITORY": "BMS-ZJU/BMS_Database"})
        self.assertIs(type(config["real_calls_enabled"]), bool)
        self.assertEqual(sec.policy(existing.REPO)["max_calls_per_approval"], 1)
        self.assertEqual(set(models.PROVIDERS), {"DeepSeek", "OpenAI", "Gemini"})

    def test_missing_or_false_runtime_switch_never_calls_with_enabled_source(self):
        c = self.case
        self.assertTrue(c.snapshot["repository_config"]["real_calls_enabled"])
        c.env.pop("BMS_AI_ENABLED", None)
        c.blocked(c.process)
        c.env["BMS_AI_ENABLED"] = "false"
        c.blocked(c.process)

    def test_valid_call_reserves_and_sends_same_output_cap(self):
        c = self.case
        limits = sec.policy(c.root)
        limits["max_output_tokens"] = 1024  # Different from the deployed default.
        pipeline.write_json(c.root / sec.POLICY_PATH, limits)
        c.refresh_snapshot()
        self.assertTrue(c.process())
        self.assertEqual(len(c.calls), 1)
        self.assertEqual(c.calls[0][1]["max_tokens"], 1024)
        self.assertEqual(sec.read_json(c.output / "approval.json")["output_tokens"], 1024)
        self.assertEqual(sec.read_json(c.receipt)["stage"], "review_generated")
        self.assertEqual((c.root / c.target).read_text(encoding="utf-8"), c.original)

    def test_truncation_has_diagnostic_but_no_retry_or_candidate(self):
        c = self.case
        c.response["choices"][0]["finish_reason"] = "length"
        with self.assertRaises(ValueError): c.process()
        self.assertEqual(len(c.calls), 1)
        self.assertEqual(sec.read_json(c.receipt)["failure"]["code"], "OUTPUT_LIMIT")
        self.assertFalse(c.output.exists())
        with self.assertRaises((ValueError, OSError)): c.execute()
        self.assertEqual(len(c.calls), 1)

    def test_invalid_json_has_diagnostic_without_full_answer(self):
        c = self.case
        c.response["choices"][0]["message"]["content"] = "PROVIDER_PRIVATE_PROSE"
        with self.assertRaises(ValueError): c.process()
        self.assertEqual(sec.read_json(c.receipt)["failure"]["code"], "INVALID_JSON")
        self.assertNotIn("PROVIDER_PRIVATE_PROSE", c.receipt.read_text(encoding="utf-8"))
        self.assertEqual(len(c.calls), 1)
        self.assertFalse(c.output.exists())

    def test_conflicting_candidate_records_safe_rule_without_writing(self):
        c = self.case
        proposal = json.loads(c.response["choices"][0]["message"]["content"])
        proposal["changes"][0]["before"] = "not present"
        c.response["choices"][0]["message"]["content"] = json.dumps(proposal)
        with self.assertRaises(ValueError): c.process()
        failure = sec.read_json(c.receipt)["failure"]
        self.assertEqual(failure["code"], "CANDIDATE_REJECTED")
        self.assertNotIn("安全白名单", failure["detail"])
        self.assertFalse(c.output.exists())
        self.assertEqual(len(c.calls), 1)

    def test_timeout_preserves_unknown_and_only_one_request(self):
        c = self.case
        def timeout(*args, **kwargs):
            c.calls.append(args[0])
            raise TimeoutError("PRIVATE_EXCEPTION_TEXT")
        c.transport = timeout
        with self.assertRaises(TimeoutError): c.process()
        receipt = sec.read_json(c.receipt)
        self.assertEqual(receipt["state"], "unknown")
        self.assertEqual(receipt["failure"]["code"], "TIMEOUT_UNKNOWN")
        self.assertNotIn("PRIVATE_EXCEPTION_TEXT", sec.canonical(receipt))
        self.assertEqual(len(c.calls), 1)

    def test_diagnostics_do_not_copy_provider_text_or_reasoning(self):
        response = {"choices": [{"finish_reason": "SECRET_FINISH", "message": {
            "content": "SECRET_CONTENT", "reasoning_content": "SECRET_REASONING"}}]}
        result = diagnostics.response_diagnostics(response, "DeepSeek")
        self.assertEqual(result["finish_reason"], "unknown")
        self.assertNotIn("SECRET", sec.canonical(result))
        self.assertNotIn("SECRET", diagnostics.safe_detail(ValueError("SECRET")))
        self.assertEqual(diagnostics.response_diagnostics({"status": "incomplete", "incomplete_details": {
            "reason": "max_output_tokens"}}, "OpenAI")["finish_reason"], "length")
        self.assertEqual(diagnostics.response_diagnostics({"candidates": [{"finishReason": "MAX_TOKENS"}]},
                                                         "Gemini")["finish_reason"], "MAX_TOKENS")

    def test_secret_model_version_does_not_leak_in_failure_receipt(self):
        c = self.case
        c.response["model"] = c.env["BMS_DEEPSEEK_API_KEY"]
        with self.assertRaises(ValueError): c.process()
        self.assertNotIn(c.env["BMS_DEEPSEEK_API_KEY"], c.receipt.read_text(encoding="utf-8"))
        self.assertEqual(sec.read_json(c.receipt)["state"], "unknown")
        self.assertFalse(c.output.exists())


if __name__ == "__main__":
    unittest.main()
