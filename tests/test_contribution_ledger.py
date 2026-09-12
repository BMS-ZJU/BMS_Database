"""Offline ledger tests, with a locked fake Git graph and atomic ref updates."""
import base64
from concurrent.futures import ThreadPoolExecutor
import copy
import hashlib
import hmac
import io
import json
import socket
import threading
import traceback
import unittest
from contextlib import redirect_stderr, redirect_stdout
from unittest.mock import patch

from scripts.contributions import ledger as module
from scripts.contributions.ledger import Ledger, initialize


# Public, deterministic test fixture; production callers supply a random key.
KEY = "0123456789abcdef" * 4


def authenticated(data, repository, parent, key=KEY):
    unsigned = {name: value for name, value in data.items() if name != "authentication"}
    message = json.dumps({**unsigned, "repository": repository, "parent": parent},
                         ensure_ascii=True, sort_keys=True,
                         separators=(",", ":"), allow_nan=False).encode("utf-8")
    return {**unsigned, "authentication":
            hmac.new(bytes.fromhex(key), message, hashlib.sha256).hexdigest()}



def record(number=1, **changes):
    result = {
        "approval_id": f"{number:064x}", "run_id": str(number),
        "snapshot_hash": f"{number + 100:064x}", "base_commit": "a" * 40,
        "service": "DeepSeek", "model": "deepseek-flash",
        "policy_sha256": "b" * 64, "input_chars": 10, "output_tokens": 5,
        "actor_id": 7,
    }
    return {**result, **changes}


def policy(**changes):
    return {
        "cumulative_calls": 100, "cumulative_input_chars": 10000,
        "cumulative_output_tokens": 10000, "max_in_flight": 3, **changes,
    }


def receipt(state="complete", usage=None, model_version=None):
    return {"state": state, "usage": usage, "model_version": model_version}


class APIError(OSError):
    def __init__(self, status):
        super().__init__("private HTTP response or credential must not escape")
        self.status = status


class FakeGitHub:
    """Repository-scoped Git graph; PATCH checks ancestry while holding a lock."""

    repository = "BMS-ZJU/BMS_Database"

    def __init__(self):
        self.lock = threading.RLock()
        self.refs = {"refs/heads/main": "f" * 40}
        self.blobs, self.trees, self.commits, self.runs = {}, {}, {}, {}
        self.calls = []
        self.failures = {}
        self.ref_barrier = None
        self.lose_patch_response = False

    @staticmethod
    def oid(kind, value):
        if type(value) is not bytes:
            value = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
        return hashlib.sha1(kind.encode() + b" " + str(len(value)).encode()
                            + b"\0" + value).hexdigest()

    def blob(self, raw):
        sha = self.oid("blob", raw)
        self.blobs[sha] = {
            "sha": sha, "size": len(raw), "encoding": "base64",
            "content": base64.encodebytes(raw).decode("ascii"),
        }
        return sha

    def tree(self, entries):
        sha = self.oid("tree", entries)
        self.trees[sha] = {"sha": sha, "tree": copy.deepcopy(entries), "truncated": False}
        return sha

    def commit(self, tree_sha, parents, message):
        value = {"tree": {"sha": tree_sha}, "parents": [{"sha": p} for p in parents],
                 "message": message}
        sha = self.oid("commit", value)
        self.commits[sha] = {"sha": sha, **value}
        return sha

    def install_raw(self, raw):
        """Install a possibly corrupt descendant for adversarial read tests."""
        with self.lock:
            blob = self.blob(raw)
            tree = self.tree([{"path": "ledger.json", "mode": "100644", "type": "blob",
                               "sha": blob, "size": len(raw)}])
            parents = [self.refs[module.REF]] if module.REF in self.refs else []
            sha = self.commit(tree, parents, "fixture")
            self.refs[module.REF] = sha
            return sha

    def signed_raw(self, data, key=KEY, repository=None):
        signed = authenticated(data, repository or self.repository,
                               self.refs.get(module.REF), key)
        return json.dumps(signed, separators=(",", ":")).encode()

    def install(self, data):
        raw = self.signed_raw(data) if type(data) is dict else json.dumps(data).encode()
        return self.install_raw(raw)

    def ancestors(self, sha):
        pending, seen = [sha], set()
        while pending:
            current = pending.pop()
            if current not in seen:
                seen.add(current)
                pending.extend(p["sha"] for p in self.commits.get(current, {}).get("parents", []))
        return seen

    @staticmethod
    def ref(sha):
        return {"ref": module.REF, "object": {"type": "commit", "sha": sha}}

    def __call__(self, path, payload=None, method=None):
        method = method or ("GET" if payload is None else "POST")
        error, response = None, None
        with self.lock:
            self.calls.append((method, path, copy.deepcopy(payload)))
            barrier = self.ref_barrier if method == "GET" and path == module.READ_REF else None
            try:
                failure = self.failures.get((method, path))
                if failure is not None:
                    raise failure
                response = copy.deepcopy(self.dispatch(path, payload, method))
            except Exception as caught:
                error = caught
        # Both readers receive the same snapshot; the barrier must be outside the lock.
        if barrier is not None:
            barrier.wait(timeout=5)
        if error is not None:
            raise error
        return response

    def dispatch(self, path, payload, method):
        if method == "GET":
            if path == module.READ_REF:
                if module.REF not in self.refs:
                    raise APIError(404)
                return self.ref(self.refs[module.REF])
            if path.startswith("/compare/"):
                anchor, head = path.removeprefix("/compare/").split("...")
                shared = self.ancestors(anchor) & self.ancestors(head)
                if anchor == head:
                    status, merge_base = "identical", anchor
                elif anchor in self.ancestors(head):
                    status, merge_base = "ahead", anchor
                elif head in self.ancestors(anchor):
                    status, merge_base = "behind", head
                else:
                    status, merge_base = "diverged", next(iter(shared), "0" * 40)
                return {"status": status, "merge_base_commit": {"sha": merge_base}}
            for prefix, objects in (
                    ("/git/commits/", self.commits), ("/git/trees/", self.trees),
                    ("/git/blobs/", self.blobs)):
                if path.startswith(prefix):
                    sha = path.removeprefix(prefix)
                    if sha not in objects:
                        raise APIError(404)
                    return objects[sha]
            if path.startswith("/actions/runs/"):
                run = path.removeprefix("/actions/runs/")
                if run not in self.runs:
                    raise APIError(404)
                status = self.runs[run]
                return status if type(status) is dict else {"id": int(run), "status": status}
        if method == "POST":
            if path == "/git/blobs":
                assert set(payload) == {"content", "encoding"}
                assert payload["encoding"] == "base64"
                return {"sha": self.blob(base64.b64decode(payload["content"], validate=True))}
            if path == "/git/trees":
                assert set(payload) == {"tree"}  # No base_tree or inherited repository files.
                assert len(payload["tree"]) == 1
                entries = copy.deepcopy(payload["tree"])
                for entry in entries:
                    assert set(entry) == {"path", "mode", "type", "sha"}
                    assert (entry["path"], entry["mode"], entry["type"]) == (
                        "ledger.json", "100644", "blob")
                    entry["size"] = self.blobs[entry["sha"]]["size"]
                return {"sha": self.tree(entries)}
            if path == "/git/commits":
                assert payload["tree"] in self.trees
                assert len(payload["parents"]) <= 1
                assert all(parent in self.commits for parent in payload["parents"])
                return {"sha": self.commit(payload["tree"], payload["parents"], payload["message"])}
            if path == "/git/refs":
                assert payload["ref"] == module.REF
                if module.REF in self.refs:
                    raise APIError(422)
                self.refs[module.REF] = payload["sha"]
                return self.ref(payload["sha"])
        if method == "PATCH" and path == module.WRITE_REF:
            assert set(payload) == {"sha", "force"} and payload["force"] is False
            current = self.refs.get(module.REF)
            target = payload["sha"]
            if current is None or current not in self.ancestors(target):
                raise APIError(422)
            self.refs[module.REF] = target
            if self.lose_patch_response:
                self.lose_patch_response = False
                raise OSError("private HTTP response or credential must not escape")
            return self.ref(target)
        raise AssertionError("Unexpected API scope")


class LedgerTests(unittest.TestCase):
    def setUp(self):
        self.network = patch.object(socket, "socket", side_effect=AssertionError("Network forbidden"))
        self.connection = patch.object(
            socket, "create_connection", side_effect=AssertionError("Network forbidden"))
        self.network.start()
        self.connection.start()
        self.addCleanup(self.network.stop)
        self.addCleanup(self.connection.stop)
        self.api, self.book, self.anchor = self.fresh()

    @staticmethod
    def fresh():
        api = FakeGitHub()
        anchor = initialize(api, KEY)
        return api, Ledger(api, anchor, KEY), anchor

    def reserve(self, number=1, limits=None, **changes):
        value = record(number, **changes)
        self.api.runs[value["run_id"].lstrip("0") or "0"] = "in_progress"
        return self.book.reserve(value, limits or policy())

    def assert_no_writes(self, start):
        self.assertFalse(any(method != "GET" for method, _, _ in self.api.calls[start:]))

    def test_initialize_is_orphan_and_existing_branch_is_not_reset(self):
        initial = self.api.commits[self.anchor]
        self.assertEqual(initial["parents"], [])
        self.assertEqual(self.book.read(), (self.anchor, authenticated(
            {"version": 2, "reservations": {}}, self.api.repository, None)))
        self.assertEqual(len(self.api.trees[initial["tree"]["sha"]]["tree"]), 1)
        self.reserve()
        head, before = self.book.read()
        start = len(self.api.calls)
        self.assertEqual(initialize(self.api, KEY), head)
        self.assertEqual(self.api.refs[module.REF], head)
        self.assertEqual(self.book.anchor, self.anchor)
        self.assertEqual(self.book.read(), (head, before))
        self.assert_no_writes(start)
        self.assertEqual(self.api.refs["refs/heads/main"], "f" * 40)

    def test_anchor_is_required_and_must_be_full_hex(self):
        with self.assertRaises(TypeError):  # Python enforces the required argument.
            Ledger(self.api)
        for value in (None, "", "a" * 39, "a" * 41, "g" * 40, 1, True, "a" * 40 + "\n"):
            with self.subTest(anchor=value), self.assertRaises(ValueError):
                Ledger(self.api, value, KEY)
        self.assertEqual(Ledger(self.api, self.anchor.upper(), KEY).read()[0], self.anchor)

        start = len(self.api.calls)
        for key in (None, "", "ab" * 31, "ab" * 33, "AB" * 32, "g" * 64,
                    KEY + "\n", 7, True, bytes.fromhex(KEY)):
            with self.subTest(key_type=type(key).__name__):
                with self.assertRaises(ValueError):
                    Ledger(self.api, self.anchor, key)
                with self.assertRaises(ValueError):
                    initialize(self.api, key)
        with self.assertRaises(ValueError):
            Ledger(self.api, self.anchor)
        with self.assertRaises(ValueError):
            initialize(self.api)
        for repository in (None, "", "org", "org/repo/extra", "https://example.org/repo"):
            api = FakeGitHub()
            api.repository = repository
            with self.assertRaises(ValueError):
                Ledger(api, self.anchor, KEY)
            with self.assertRaises(ValueError):
                initialize(api, KEY)
        self.assertEqual(len(self.api.calls), start)

    def test_missing_ledger_never_auto_initializes_any_normal_operation(self):
        api = FakeGitHub()
        book = Ledger(api, "a" * 40, KEY)
        operations = [
            book.read, lambda: book.reserve(record(), policy()),
            lambda: book.verify_reservation(record()),
            lambda: book.settle(record()["approval_id"], "1", receipt()),
            lambda: book.reconcile(record()["approval_id"]),
        ]
        for operation in operations:
            with self.subTest(operation=operation), self.assertRaises(OSError):
                operation()
        self.assertTrue(all(method == "GET" for method, _, _ in api.calls))
        self.assertNotIn(module.REF, api.refs)

    def test_initialization_requires_unambiguous_absence(self):
        for failure in (APIError(403), APIError(500), OSError("offline"), ValueError("404")):
            api = FakeGitHub()
            api.failures[("GET", module.READ_REF)] = failure
            with self.subTest(failure=type(failure)), self.assertRaises(OSError):
                initialize(api, KEY)
            self.assertEqual(len(api.calls), 1)
        api = FakeGitHub()
        api.failures[("GET", module.READ_REF)] = FileNotFoundError()
        self.assertIn(initialize(api, KEY), api.commits)
        def malformed(*args, **kwargs):
            return None
        malformed.repository = FakeGitHub.repository
        with self.assertRaises(ValueError):
            initialize(malformed, KEY)

        for attribute in ("code", "status", "status_code"):
            with self.subTest(attribute=attribute):
                api = FakeGitHub()
                error = ValueError("HTTP response must stay private")
                setattr(error, attribute, 404)
                api.failures[("GET", module.READ_REF)] = error
                head = initialize(api, KEY)
                self.assertEqual(api.refs[module.REF], head)
                self.assertEqual(api.commits[head]["parents"], [])


    def test_existing_corrupt_ledger_is_not_reinitialized(self):
        self.api.install({"version": 3, "reservations": {}})
        start = len(self.api.calls)
        with self.assertRaises(ValueError):
            initialize(self.api, KEY)
        self.assert_no_writes(start)

        self.api, self.book, self.anchor = self.fresh()
        for key in ("f" * 64, "0" * 64):
            start = len(self.api.calls)
            with self.assertRaisesRegex(ValueError, "authentication failed"):
                Ledger(self.api, self.anchor, key).read()
            with self.assertRaisesRegex(ValueError, "authentication failed"):
                initialize(self.api, key)
            self.assertEqual(self.api.refs[module.REF], self.anchor)
            self.assert_no_writes(start)
        self.api.repository = "another/repository"
        with self.assertRaisesRegex(ValueError, "authentication failed"):
            Ledger(self.api, self.anchor, KEY).read()
        with self.assertRaisesRegex(ValueError, "authentication failed"):
            initialize(self.api, KEY)

    def test_durable_round_trip_and_immutable_fields(self):
        original = record()
        reserved = self.reserve()
        self.assertEqual(reserved, {**original, "state": "reserved"})
        reloaded = Ledger(self.api, self.anchor, KEY)
        self.assertEqual(reloaded.verify_reservation(reserved), reserved)
        self.assertEqual(reloaded.verify_reservation(original), reserved)
        head, data = reloaded.read()
        self.assertNotEqual(head, self.anchor)
        self.assertEqual(data["reservations"][original["approval_id"]], reserved)
        self.assertEqual(self.api.commits[head]["parents"], [{"sha": self.anchor}])
        self.assertEqual(data, authenticated(data, self.api.repository, self.anchor))
        start = len(self.api.calls)
        with patch.object(module.hmac, "compare_digest", wraps=hmac.compare_digest) as compare:
            self.book.read()
        compare.assert_called_once()
        commit_reads = [path for method, path, _ in self.api.calls[start:]
                        if method == "GET" and path.startswith("/git/commits/")]
        self.assertEqual(commit_reads, ["/git/commits/" + head])
        self.assertNotIn(KEY, json.dumps(self.api.calls))
        for blob in self.api.blobs.values():
            self.assertNotIn(KEY.encode(), base64.b64decode(blob["content"]))
        reserved["input_chars"] = 0
        data["reservations"].clear()
        self.assertEqual(reloaded.read()[1]["reservations"][original["approval_id"]]["input_chars"], 10)

    def test_verify_reservation_works_with_a_read_only_api(self):
        self.reserve()
        reserved = self.reserve(2)
        def read_only(path, payload=None, method=None):
            if method not in (None, "GET") or payload is not None:
                raise PermissionError("Read-only token")
            return self.api(path, payload=payload, method=method)
        read_only.repository = self.api.repository
        start = len(self.api.calls)
        checked = Ledger(read_only, self.anchor, KEY).verify_reservation(reserved)
        self.assertEqual(checked, reserved)
        self.assert_no_writes(start)
        self.assertIn(("GET", "/actions/runs/1", None), self.api.calls[start:])

    def test_duplicate_approval_and_run_reuse_even_after_completion(self):
        original = self.reserve(10)
        self.book.settle(original["approval_id"], "10", receipt())
        attempts = [
            record(10), record(10, run_id="11"),
            record(11, run_id="10"), record(11, run_id="0010"),
            record(11, approval_id=original["approval_id"].upper()),
        ]
        for value in attempts:
            start = len(self.api.calls)
            with self.subTest(record=value), self.assertRaises(ValueError):
                self.book.reserve(value, policy())
            self.assert_no_writes(start)

    def test_all_three_quotas_at_boundary_across_all_scopes_without_refunds(self):
        for limit, maximum in (("cumulative_calls", 2), ("cumulative_input_chars", 20),
                               ("cumulative_output_tokens", 10)):
            with self.subTest(limit=limit):
                self.api, self.book, self.anchor = self.fresh()
                limits = policy(**{limit: maximum})
                first = self.reserve(1, limits, service="DeepSeek", actor_id=1)
                self.book.settle(first["approval_id"], "1",
                                 receipt(usage={"input_tokens": 0, "output_tokens": 0}))
                second = self.reserve(2, limits, service="OpenAI", model="another-model",
                                      actor_id=2, policy_sha256="c" * 64,
                                      snapshot_hash="d" * 64, base_commit="e" * 40)
                self.book.settle(second["approval_id"], "2", receipt())
                start = len(self.api.calls)
                with self.assertRaises(ValueError):
                    self.book.reserve(record(3, service="Gemini"), limits)
                self.assert_no_writes(start)
                values = self.book.read()[1]["reservations"].values()
                self.assertEqual(sum(value["input_chars"] for value in values), 20)

    def test_minimum_positive_reservations_still_consume_calls(self):
        value = self.reserve(input_chars=1, output_tokens=1)
        self.book.settle(value["approval_id"], "1",
                         receipt(usage={"input_tokens": 0, "output_tokens": 0}))
        with self.assertRaises(ValueError):
            self.book.reserve(record(2, input_chars=1, output_tokens=1),
                              policy(cumulative_calls=1))

    def test_active_statuses_and_maximum_in_flight(self):
        for status in module.ACTIVE:
            with self.subTest(status=status):
                self.api, self.book, self.anchor = self.fresh()
                first = self.reserve()
                self.api.runs["1"] = status
                second = self.reserve(2, policy(max_in_flight=2))
                self.book.verify_reservation(second)
                with self.assertRaises(ValueError):
                    self.reserve(3, policy(max_in_flight=2))
                third = self.reserve(3)
                self.assertEqual(third["state"], "reserved")
                with self.assertRaises(ValueError):
                    self.reserve(4)
                self.book.settle(first["approval_id"], "1", receipt())
                self.assertEqual(self.reserve(4)["state"], "reserved")

    def test_stale_other_run_blocks_reserve_and_verify(self):
        for status in ("completed", "cancelled", "failure", "unknown", "", None):
            with self.subTest(status=status):
                self.api, self.book, self.anchor = self.fresh()
                self.reserve()
                other = self.reserve(2)
                self.api.runs["1"] = status
                start = len(self.api.calls)
                with self.assertRaises(ValueError):
                    self.reserve(3)
                with self.assertRaises(ValueError):
                    self.book.verify_reservation(other)
                self.assert_no_writes(start)

    def test_run_read_failure_and_wrong_identity_fail_closed(self):
        self.reserve()
        other = self.reserve(2)
        for response in ({"status": "in_progress", "id": 999}, {},
                         {"status": ["in_progress"]}, {"status": "in_progress", "id": True}):
            self.api.runs["1"] = response
            with self.subTest(response=response), self.assertRaises(ValueError):
                self.book.verify_reservation(other)
        self.api.failures[("GET", "/actions/runs/1")] = APIError(403)
        with self.assertRaises(OSError):
            self.book.verify_reservation(other)
        with self.assertRaises(OSError):
            self.reserve(3)

    def test_unknown_blocks_new_calls_but_does_not_block_settling_other_entries(self):
        first, second = self.reserve(), self.reserve(2)
        terminal = self.book.settle(first["approval_id"], "1", receipt("unknown"))
        self.assertEqual(terminal["state"], "unknown")
        self.assertEqual(self.book.read()[1]["reservations"][first["approval_id"]], terminal)
        with self.assertRaises(ValueError):
            self.reserve(3)
        with self.assertRaises(ValueError):
            self.book.verify_reservation(second)
        self.assertEqual(self.book.settle(second["approval_id"], "2", receipt())["state"], "complete")
        with self.assertRaises(ValueError):
            self.book.settle(first["approval_id"], "1", receipt())
        with self.assertRaises(ValueError):
            self.book.verify_reservation(first)

    def test_verify_matches_every_immutable_field_and_reserved_state(self):
        original = self.reserve()
        alternative = record(2)
        for key in module.FIELDS:
            modified = dict(original)
            modified[key] = alternative[key] if original[key] != alternative[key] else (
                original[key] + 1 if type(original[key]) is int else original[key] + "x")
            with self.subTest(field=key), self.assertRaises(ValueError):
                self.book.verify_reservation(modified)
        for modified in ({**original, "state": "complete"}, {**original, "extra": 1},
                         {key: value for key, value in original.items() if key != "actor_id"}):
            with self.assertRaises(ValueError):
                self.book.verify_reservation(modified)
        self.book.settle(original["approval_id"], "1", receipt())
        with self.assertRaises(ValueError):
            self.book.verify_reservation(original)

    def test_record_and_policy_validation_fail_before_writes(self):
        bad_records = [
            {**record(), "extra": 1}, {**record(), "state": "reserved"}, {},
            *[record(**{field: value}) for field, values in {
                "approval_id": ["x" * 64, None, "a" * 63],
                "snapshot_hash": ["g" * 64], "base_commit": ["a" * 39],
                "policy_sha256": ["b" * 65], "run_id": [1, "", "-1", "1/../2", "1\n", "１２"],
                "service": ["", None, "x\n"], "model": [[], "", "x" * 201],
                "input_chars": [0, -1, True, 1.5], "output_tokens": [0, -1, False, "5"],
                "actor_id": [-1, True, "7"],
            }.items() for value in values],
        ]
        for bad in bad_records:
            start = len(self.api.calls)
            with self.subTest(record=bad), self.assertRaises(ValueError):
                self.book.reserve(bad, policy())
            self.assert_no_writes(start)
        bad_policies = [None, {}, policy(max_in_flight=4)]
        for key in module.POLICY_FIELDS:
            bad_policies.extend(policy(**{key: value}) for value in (0, -1, True, 1.5, "2"))
        for bad in bad_policies:
            start = len(self.api.calls)
            with self.subTest(policy=bad), self.assertRaises(ValueError):
                self.book.reserve(record(), bad)
            self.assert_no_writes(start)
        # The ledger consumes four limits from the caller's full policy object.
        self.reserve(limits=policy(enabled=True, model_allowlist=["deepseek-flash"]))

    def test_settlement_sanitizes_usage_and_version_without_refunding(self):
        original = self.reserve()
        usage = {
            "input_tokens": 12, "output_tokens": 2.5, "total_tokens": float("inf"),
            "prompt_tokens": True, "completion_tokens": -1, "reasoning_tokens": float("nan"),
            "cached_tokens": module.MAX_USAGE + 1, "prompt_cache_hit_tokens": "12",
            "promptTokenCount": 3, "Authorization": "Bearer secret",
            "input_tokens_details": {"cached_tokens": 5},
        }
        final = self.book.settle(original["approval_id"], "1",
                                 receipt(usage=usage, model_version="model-version.1"))
        self.assertEqual(final["usage"], {"input_tokens": 12, "output_tokens": 2.5,
                                          "promptTokenCount": 3})
        self.assertEqual(final["model_version"], "model-version.1")
        self.assertEqual({key: final[key] for key in module.FIELDS},
                         {key: original[key] for key in module.FIELDS})
        self.assertEqual(self.book.read()[1]["reservations"][original["approval_id"]], final)
        self.assertNotIn("Bearer secret", json.dumps(self.api.blobs))

    def test_noncomplete_receipts_become_unknown_and_unsafe_versions_are_dropped(self):
        for state in ("unknown", "completed", "", None, False, {"error": "secret"}):
            with self.subTest(state=state):
                self.api, self.book, self.anchor = self.fresh()
                value = self.reserve()
                final = self.book.settle(value["approval_id"], "1",
                                         receipt(state, {}, "Authorization: Bearer secret"))
                self.assertEqual((final["state"], final["usage"], final["model_version"]),
                                 ("unknown", None, None))
                with self.assertRaises(ValueError):
                    self.reserve(2)
        self.api, self.book, self.anchor = self.fresh()
        value = self.reserve()
        self.assertIsNone(self.book.settle(value["approval_id"], "1",
                                          receipt(model_version="x" * 201))["model_version"])

    def test_settle_rejects_wrong_ids_malformed_receipts_and_second_settlement(self):
        value = self.reserve()
        invalid = [
            (record(2)["approval_id"], "1", receipt()), (value["approval_id"], "2", receipt()),
            (value["approval_id"], "01", receipt()), (value["approval_id"], "1", {}),
            (value["approval_id"], "1", receipt(usage=[])),
            (value["approval_id"], "1", receipt(model_version=1)),
            (value["approval_id"], "1", {**receipt(), "response": "secret"}),
        ]
        for args in invalid:
            start = len(self.api.calls)
            with self.subTest(args=args), self.assertRaises(ValueError):
                self.book.settle(*args)
            self.assert_no_writes(start)
        self.book.settle(value["approval_id"], "1", receipt())
        with self.assertRaises(ValueError):
            self.book.settle(value["approval_id"], "1", receipt("unknown"))

    def test_reconcile_only_completed_unknown_or_stale_reserved_and_never_reauthorizes(self):
        for unknown in (False, True):
            with self.subTest(unknown=unknown):
                self.api, self.book, self.anchor = self.fresh()
                value = self.reserve()
                if unknown:
                    self.book.settle(value["approval_id"], "1",
                                     receipt("unknown", {"input_tokens": 1}, "version"))
                for status in (*module.ACTIVE, "cancelled", "invalid"):
                    self.api.runs["1"] = status
                    with self.assertRaises(ValueError):
                        self.book.reconcile(value["approval_id"])
                self.api.runs["1"] = "completed"
                final = self.book.reconcile(value["approval_id"])
                self.assertEqual(final, {**value, "state": "complete",
                                         "usage": None, "model_version": None})
                with self.assertRaises(ValueError):
                    self.book.verify_reservation(value)
                with self.assertRaises(ValueError):
                    self.book.reserve(record(), policy())
                with self.assertRaises(ValueError):
                    self.book.reserve(record(2, run_id="1"), policy())
                with self.assertRaises(ValueError):
                    self.book.reserve(record(2), policy(cumulative_input_chars=10))
                with self.assertRaises(ValueError):
                    self.book.reconcile(value["approval_id"])
                self.assertEqual(self.reserve(2)["state"], "reserved")

    def test_reconcile_missing_entry_run_or_run_read_failure_fails_closed(self):
        with self.assertRaises(ValueError):
            self.book.reconcile(record()["approval_id"])
        value = self.reserve()
        del self.api.runs["1"]
        with self.assertRaises(OSError):
            self.book.reconcile(value["approval_id"])
        self.assertEqual(self.book.read()[1]["reservations"][value["approval_id"]]["state"], "reserved")

    def test_schema_and_records_are_revalidated_on_every_read(self):
        valid = {**record(), "state": "reserved"}
        wrapped = lambda entry: {"version": 2, "reservations": {record()["approval_id"]: entry}}
        invalid = [
            None, [], {}, {"version": True, "reservations": {}},
            {"version": 3, "reservations": {}}, {"version": 2, "reservations": []},
            {"version": 2, "reservations": {}, "cumulative_calls": 0},
            wrapped({**valid, "state": "surprise"}), wrapped({**valid, "state": []}),
            wrapped({**valid, "usage": None}), wrapped({**valid, "input_chars": -1}),
            wrapped({**valid, "input_chars": 0}), wrapped({**valid, "output_tokens": 0}),
            wrapped({**valid, "output_tokens": True}), wrapped({**valid, "extra": 1}),
            wrapped({**valid, "approval_id": record(2)["approval_id"]}),
            wrapped({**valid, "state": "complete"}),
            *[wrapped({**valid, "state": "complete", "model_version": None, "usage": usage})
              for usage in ({}, [], {"input_tokens": True}, {"input_tokens": -1},
                            {"input_tokens": module.MAX_USAGE + 1}, {"unknown": 1})],
            wrapped({**valid, "state": "unknown", "usage": None, "model_version": "x\n"}),
        ]
        duplicated = {"version": 2, "reservations": {
            valid["approval_id"]: valid, record(2)["approval_id"]: {**record(2, run_id="01"),
                                                                   "state": "reserved"}}}
        invalid.append(duplicated)
        approval = record(10)["approval_id"]
        invalid.append({"version": 2, "reservations": {
            approval: {**record(10), "state": "reserved"},
            approval.upper(): {**record(11, approval_id=approval.upper()), "state": "reserved"},
        }})
        for data in invalid:
            with self.subTest(data=data):
                self.api.install(data)
                start = len(self.api.calls)
                with self.assertRaises(ValueError):
                    self.book.read()
                self.assert_no_writes(start)

    def test_invalid_json_encoding_duplicates_and_size_limits(self):
        for raw in (b'{"version":2,"version":2,"reservations":{}}',
                    b'{"version":2,"reservations":{},"reservations":{}}',
                    b'{"version":NaN,"reservations":{}}', b"\xff", b"{} trailing",
                    b"[" * 2000 + b"]" * 2000, b"\x00", b" " * (module.MAX_BYTES + 1)):
            with self.subTest(size=len(raw)):
                self.api.install_raw(raw)
                with self.assertRaises(ValueError):
                    self.book.read()
        raw = self.api.signed_raw({"version": 2, "reservations": {}})
        self.api.install_raw(raw + b" " * (module.MAX_BYTES - len(raw)))
        self.assertEqual(self.book.read()[1]["reservations"], {})
        raw = self.api.signed_raw({"version": 2, "reservations": {}})
        self.api.install_raw(raw)  # Read fits; the new reservation must fail before blob creation.
        with patch.object(module, "MAX_BYTES", len(raw) + 1):
            start = len(self.api.calls)
            with self.assertRaises(ValueError):
                self.book.reserve(record(), policy())
            self.assert_no_writes(start)

    def test_corrupt_git_object_responses_fail_closed(self):
        corruptions = [
            (module.READ_REF, lambda r: {**r, "ref": "refs/heads/main"}),
            (module.READ_REF, lambda r: {**r, "object": {"type": "tag", "sha": self.anchor}}),
            ("/compare/", lambda r: {**r, "status": "behind"}),
            ("/compare/", lambda r: {**r, "status": "diverged"}),
            ("/compare/", lambda r: {**r, "status": "ahead"}),
            ("/compare/", lambda r: {**r, "merge_base_commit": {"sha": "c" * 40}}),
            ("/git/commits/", lambda r: {**r, "sha": "c" * 40}),
            ("/git/commits/", lambda r: {**r, "tree": None}),
            ("/git/commits/", lambda r: {k: v for k, v in r.items() if k != "parents"}),
            *[("/git/commits/", lambda r, parents=parents: {**r, "parents": parents})
              for parents in (None, {}, [None], [{"sha": "bad"}],
                              [{"sha": "b" * 40}, {"sha": "c" * 40}],
                              [{"sha": "b" * 40}])],
            ("/git/trees/", lambda r: {**r, "truncated": True}),
            ("/git/trees/", lambda r: {**r, "truncated": None}),
            ("/git/trees/", lambda r: {**r, "tree": []}),
            ("/git/trees/", lambda r: {**r, "tree": r["tree"] * 2}),
            *[("/git/trees/", lambda r, changes=changes:
               {**r, "tree": [{**r["tree"][0], **changes}]})
              for changes in ({"path": "other.json"}, {"path": "../ledger.json"},
                              {"mode": "120000"}, {"type": "tree"}, {"size": True},
                              {"size": module.MAX_BYTES + 1}, {"sha": "../outside"})],
            ("/git/blobs/", lambda r: {**r, "encoding": "utf-8"}),
            ("/git/blobs/", lambda r: {**r, "sha": "c" * 40}),
            ("/git/blobs/", lambda r: {**r, "size": r["size"] + 1}),
            ("/git/blobs/", lambda r: {**r, "content": "%%%"}),
            ("/git/blobs/", lambda r: {**r, "content": "é"}),
            ("/git/blobs/", lambda r: {**r, "content": "e30="}),
            ("/git/blobs/", lambda r: {**r, "content": "A" * (3 * module.MAX_BYTES)}),
        ]
        for prefix, corrupt in corruptions:
            def api(path, payload=None, method=None):
                response = self.api(path, payload=payload, method=method)
                return corrupt(response) if path.startswith(prefix) else response
            api.repository = self.api.repository
            with self.subTest(prefix=prefix), self.assertRaises(ValueError):
                Ledger(api, self.anchor, KEY).read()

    def test_anchor_rejects_unrelated_or_rewound_branches(self):
        value = self.reserve()
        head = self.api.refs[module.REF]
        self.assertEqual(Ledger(self.api, self.anchor, KEY).read()[0], head)
        with self.assertRaises(ValueError):
            Ledger(self.api, "f" * 40, KEY).read()
        self.api.refs[module.REF] = self.anchor
        with self.assertRaises(ValueError):
            Ledger(self.api, head, KEY).read()
        self.assertEqual(value["state"], "reserved")

    def test_failures_at_each_read_stage_never_write_or_leak_transport_details(self):
        head = self.api.refs[module.REF]
        commit = self.api.commits[head]
        tree = self.api.trees[commit["tree"]["sha"]]
        paths = [module.READ_REF, f"/compare/{self.anchor}...{head}",
                 f"/git/commits/{head}", f"/git/trees/{tree['sha']}",
                 f"/git/blobs/{tree['tree'][0]['sha']}"]
        for path in paths:
            self.api.failures[("GET", path)] = APIError(500)
            output = io.StringIO()
            start = len(self.api.calls)
            with redirect_stdout(output), redirect_stderr(output):
                try:
                    self.book.read()
                except OSError:
                    rendered = traceback.format_exc()
                else:
                    self.fail("Read should fail")
            self.assertEqual(output.getvalue(), "")
            self.assertNotIn("credential", rendered)
            self.assertNotIn("private HTTP", rendered)
            self.assert_no_writes(start)
            self.api.failures.clear()

    def test_failed_writes_are_not_retried_or_reported_as_reserved(self):
        for path in ("/git/blobs", "/git/trees", "/git/commits", module.WRITE_REF):
            with self.subTest(path=path):
                self.api, self.book, self.anchor = self.fresh()
                method = "PATCH" if path == module.WRITE_REF else "POST"
                self.api.failures[(method, path)] = APIError(500)
                start = len(self.api.calls)
                with self.assertRaises(OSError):
                    self.book.reserve(record(), policy())
                attempts = [call for call in self.api.calls[start:] if call[:2] == (method, path)]
                self.assertEqual(len(attempts), 1)
                self.assertEqual(self.api.refs[module.REF], self.anchor)

    def test_lost_patch_response_keeps_reservation_and_prevents_reuse(self):
        self.api.lose_patch_response = True
        with self.assertRaises(OSError):
            self.reserve()
        self.assertEqual(len(self.book.read()[1]["reservations"]), 1)
        with self.assertRaises(ValueError):
            self.reserve()
        patches = [call for call in self.api.calls if call[0] == "PATCH"]
        self.assertEqual(len(patches), 1)

        self.api, self.book, self.anchor = self.fresh()
        def api(path, payload=None, method=None):
            response = self.api(path, payload=payload, method=method)
            return {} if method == "PATCH" else response
        api.repository = self.api.repository
        with self.assertRaises(ValueError):
            Ledger(api, self.anchor, KEY).reserve(record(), policy())
        self.assertEqual(len(self.book.read()[1]["reservations"]), 1)
        self.assertEqual(sum(method == "PATCH" for method, _, _ in self.api.calls), 1)


    def race(self, operations):
        self.api.ref_barrier = threading.Barrier(2)
        def attempt(operation):
            try:
                return operation()
            except (ValueError, OSError) as error:
                return error
        try:
            with ThreadPoolExecutor(max_workers=2) as pool:
                futures = [pool.submit(attempt, operation) for operation in operations]
                results = [future.result(timeout=10) for future in futures]
        finally:
            self.api.ref_barrier = None
        self.assertEqual(sum(not isinstance(result, Exception) for result in results), 1)
        self.assertEqual(sum(isinstance(result, OSError) for result in results), 1)
        return results

    def test_concurrent_reservations_have_one_winner_even_for_identical_records(self):
        for second in (record(2), record(), record(2, run_id="1")):
            with self.subTest(second=second):
                self.api, self.book, self.anchor = self.fresh()
                limits = policy(cumulative_calls=1, max_in_flight=1)
                self.race([
                    lambda: Ledger(self.api, self.anchor, KEY).reserve(record(), limits),
                    lambda: Ledger(self.api, self.anchor, KEY).reserve(second, limits),
                ])
                data = self.book.read()[1]
                self.assertEqual(len(data["reservations"]), 1)
                patches = [payload for method, _, payload in self.api.calls if method == "PATCH"]
                self.assertEqual(len(patches), 2)
                self.assertNotEqual(patches[0]["sha"], patches[1]["sha"])
                for payload in patches:
                    self.assertIs(payload["force"], False)
                    self.assertEqual(self.api.commits[payload["sha"]]["parents"],
                                     [{"sha": self.anchor}])

    def test_concurrent_initialize_never_resets_winner(self):
        self.api = FakeGitHub()
        self.race([lambda: initialize(self.api, KEY), lambda: initialize(self.api, KEY)])
        self.assertEqual(sum(method == "POST" and path == "/git/refs"
                             for method, path, _ in self.api.calls), 2)
        self.assertFalse(any(method == "PATCH" for method, _, _ in self.api.calls))
        head = self.api.refs[module.REF]
        self.assertEqual(self.api.commits[head]["parents"], [])
        self.assertEqual(Ledger(self.api, head, KEY).read()[1]["reservations"], {})

    def test_concurrent_settlements_cannot_overwrite_each_other(self):
        first, second = self.reserve(), self.reserve(2)
        self.race([
            lambda: Ledger(self.api, self.anchor, KEY).settle(first["approval_id"], "1", receipt()),
            lambda: Ledger(self.api, self.anchor, KEY).settle(second["approval_id"], "2", receipt()),
        ])
        entries = self.book.read()[1]["reservations"].values()
        self.assertCountEqual([entry["state"] for entry in entries], ["reserved", "complete"])
        self.assertEqual(sum(entry["input_chars"] for entry in entries), 20)

    def test_hmac_rejects_fast_forward_tampering_and_old_signed_blob_replay(self):
        for attack in ("clear", "unsigned", "unknown_complete", "old_blob", "current_blob",
                       "wrong_key", "cross_repository", "bad_mac", "legacy_v1"):
            with self.subTest(attack=attack):
                self.api, self.book, self.anchor = self.fresh()
                initial_tree = self.api.commits[self.anchor]["tree"]["sha"]
                initial_blob = self.api.trees[initial_tree]["tree"][0]["sha"]
                reserved = self.reserve()
                self.book.settle(reserved["approval_id"], "1", receipt("unknown"))
                parent, data = self.book.read()
                current_tree = self.api.commits[parent]["tree"]["sha"]
                current_blob = self.api.trees[current_tree]["tree"][0]["sha"]
                if attack == "clear":
                    data["reservations"] = {}
                elif attack == "unsigned":
                    data.pop("authentication")
                elif attack == "unknown_complete":
                    data["reservations"][reserved["approval_id"]]["state"] = "complete"
                elif attack == "bad_mac":
                    data["authentication"] = "G" * 64
                elif attack == "legacy_v1":
                    data["version"] = 1
                    data = authenticated(data, self.api.repository, parent)
                if attack in ("old_blob", "current_blob"):
                    blob = initial_blob if attack == "old_blob" else current_blob
                else:
                    if attack == "wrong_key":
                        raw = self.api.signed_raw(data, key="f" * 64)
                    elif attack == "cross_repository":
                        raw = self.api.signed_raw(data, repository="other/repository")
                    else:
                        raw = json.dumps(data, separators=(",", ":")).encode()
                    blob = self.api.blob(raw)
                tree = self.api.tree([{"path": "ledger.json", "mode": "100644", "type": "blob",
                                      "sha": blob, "size": self.api.blobs[blob]["size"]}])
                head = self.api.commit(tree, [parent], "external writer fixture")
                # Genuine fast-forward under the original anchor, with no signing key.
                self.api(module.WRITE_REF, {"sha": head, "force": False}, "PATCH")
                comparison = self.api("/compare/" + self.anchor + "..." + head)
                self.assertEqual(comparison["status"], "ahead")
                self.assertEqual(comparison["merge_base_commit"]["sha"], self.anchor)
                start = len(self.api.calls)
                for operation in (
                        self.book.read, lambda: self.book.reserve(record(2), policy()),
                        lambda: self.book.verify_reservation(reserved),
                        lambda: self.book.settle(reserved["approval_id"], "1", receipt()),
                        lambda: self.book.reconcile(reserved["approval_id"]),
                        lambda: initialize(self.api, KEY)):
                    with self.assertRaises(ValueError):
                        operation()
                self.assert_no_writes(start)
                self.assertEqual(self.api.refs[module.REF], head)

    def test_api_calls_stay_in_fixed_git_and_actions_scopes(self):
        first = self.reserve()
        second = self.reserve(2)
        self.book.verify_reservation(second)
        self.book.settle(first["approval_id"], "1", receipt("unknown"))
        self.api.runs["1"] = "completed"
        self.book.reconcile(first["approval_id"])
        for method, path, payload in self.api.calls:
            with self.subTest(method=method, path=path):
                if method == "GET":
                    self.assertIsNone(payload)
                    self.assertRegex(path, r"^(/git/ref/heads/contribution-ledger|"
                                     r"/git/(commits|trees|blobs)/[a-f0-9]{40}|"
                                     r"/compare/[a-f0-9]{40}\.\.\.[a-f0-9]{40}|"
                                     r"/actions/runs/[0-9]+)$")
                elif method == "POST":
                    self.assertIn(path, {"/git/blobs", "/git/trees", "/git/commits", "/git/refs"})
                else:
                    self.assertEqual((method, path), ("PATCH", module.WRITE_REF))
                    self.assertIs(payload["force"], False)
        self.assertEqual(set(self.api.refs), {"refs/heads/main", module.REF})
        self.assertEqual(self.api.refs["refs/heads/main"], "f" * 40)


if __name__ == "__main__":
    unittest.main()
