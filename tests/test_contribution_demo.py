"""The interactive walkthrough never selects a real network transport."""
from pathlib import Path
import socket
import tempfile
import unittest

from scripts.contributions.demo import DemoSession, artifact_file


class DemoTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.demo = DemoSession(Path(self.temp.name))
        self.addCleanup(self.demo.close)

    def snapshot(self, consent=True):
        self.demo.action("submit", {"content": self.demo.content, "consent": consent})
        self.assertEqual(self.demo.state()["mock_calls"], 0)
        self.demo.action("snapshot", {})
        result = self.demo.action("view", {})
        self.assertIn("快照 SHA-256", result["snapshot_text"])
        return {"hash": self.demo.state()["hash"], "reviewed": True}

    def test_walkthrough_generates_review_after_explicit_approval_only(self):
        with self.assertRaises(ValueError): self.demo.action("generate", {})
        approval = self.snapshot()
        self.demo.action("approve", approval)
        self.assertEqual(self.demo.state()["mock_calls"], 0)
        self.demo.action("generate", {})
        self.assertEqual(self.demo.state()["mock_calls"], 1)
        self.assertEqual(self.demo.phase, "review")
        self.assertTrue(artifact_file(Path(self.temp.name), self.demo.state()["review_url"]).is_file())
        self.assertEqual((self.demo.case.root / self.demo.case.target).read_text(encoding="utf-8"), self.demo.case.original)
        with self.assertRaises(ValueError): self.demo.action("generate", {})
        self.assertEqual(self.demo.state()["mock_calls"], 1)

    def test_missing_consent_wrong_hash_and_changed_material_never_call(self):
        approval = self.snapshot(consent=False)
        with self.assertRaises(ValueError): self.demo.action("approve", approval)
        self.assertEqual(self.demo.state()["mock_calls"], 0)
        self.demo.case.api.issue["body"] = self.demo.case.api.issue["body"].replace("仅人工处理", "DeepSeek")
        with self.assertRaises(ValueError): self.demo.action("approve", approval)
        self.assertEqual(self.demo.state()["mock_calls"], 0)

    def test_wrong_hash_post_approval_change_and_stop_do_not_generate(self):
        approval = self.snapshot()
        with self.assertRaises(ValueError): self.demo.action("approve", {**approval, "hash": "0" * 64})
        self.demo.action("approve", approval)
        self.demo.action("change", {})
        with self.assertRaises(ValueError): self.demo.action("generate", {})
        self.demo.action("stop", {})
        with self.assertRaises(ValueError): self.demo.action("generate", {})
        self.assertEqual(self.demo.state()["mock_calls"], 0)

    def test_connections_and_outside_artifacts_are_blocked(self):
        with self.assertRaises(AssertionError): socket.create_connection(("127.0.0.1", 9))
        with socket.socket() as connection, self.assertRaises(AssertionError):
            connection.connect(("192.0.2.1", 443))
        with self.assertRaises(ValueError): artifact_file(Path(self.temp.name), "/artifacts/../../secret.txt")
