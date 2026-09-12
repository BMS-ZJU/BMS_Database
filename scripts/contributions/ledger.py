"""Durable, fail-closed quota reservations on one repository-scoped Git branch.

The injected API owns repository selection and authentication. This module uses
only fixed repository-relative Git/Actions paths and never logs API responses.
Normal operations require an externally pinned anchor and a 32-byte signing key.
Version 2 authenticates canonical JSON (sorted keys, compact separators, ASCII
escaping) of the unsigned data plus repository and actual commit parent. Only
authentication is persisted; the key stays in memory. Initialization is explicit.
Server-side rules must still prohibit force updates and branch deletion.
Returned reservation dictionaries contain the immutable input fields plus state.
Terminal entries additionally contain sanitized usage and model_version.
"""
import base64
import binascii
import hashlib
import hmac
import json
import math
import re
import uuid


BRANCH = "contribution-ledger"
REF = "refs/heads/" + BRANCH
READ_REF = "/git/ref/heads/" + BRANCH
WRITE_REF = "/git/refs/heads/" + BRANCH
MAX_BYTES = 1024 * 1024
MAX_USAGE = 2**53 - 1
FIELDS = frozenset({
    "approval_id", "run_id", "snapshot_hash", "base_commit", "service", "model",
    "policy_sha256", "input_chars", "output_tokens", "actor_id",
})
POLICY_FIELDS = frozenset({
    "cumulative_calls", "cumulative_input_chars", "cumulative_output_tokens",
    "max_in_flight",
})
ACTIVE = frozenset({"queued", "in_progress", "waiting", "pending", "requested"})
USAGE_FIELDS = frozenset({
    "input_tokens", "output_tokens", "total_tokens", "prompt_tokens",
    "completion_tokens", "cached_tokens", "reasoning_tokens",
    "prompt_cache_hit_tokens", "prompt_cache_miss_tokens",
    "promptTokenCount", "candidatesTokenCount", "totalTokenCount",
    "cachedContentTokenCount", "thoughtsTokenCount", "toolUsePromptTokenCount",
})


def _require(condition, message="Invalid contribution ledger"):
    if not condition:
        raise ValueError(message)


def _hex(value, length):
    return (type(value) is str
            and re.fullmatch(r"[0-9a-fA-F]{" + str(length) + r"}", value) is not None)


def _sha(value):
    _require(_hex(value, 40), "Invalid ledger object SHA")
    return value.lower()



def _key(value):
    _require(type(value) is str and re.fullmatch(r"[0-9a-f]{64}", value) is not None,
             "Missing or invalid ledger authentication key")
    return bytes.fromhex(value)


def _repository(api):
    value = getattr(api, "repository", None)
    _require(type(value) is str and re.fullmatch(
        r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", value) is not None,
        "Missing or invalid ledger repository")
    return value


def _parent(commit):
    parents = commit.get("parents")
    _require(type(parents) is list and len(parents) <= 1,
             "Ledger commit must have at most one parent")
    if not parents:
        return None
    _require(type(parents[0]) is dict, "Invalid ledger commit parent")
    return _sha(parents[0].get("sha"))


def _canonical(value):
    try:
        return json.dumps(value, ensure_ascii=True, sort_keys=True,
                          separators=(",", ":"), allow_nan=False).encode("utf-8")
    except (ValueError, TypeError, RecursionError, UnicodeError):
        raise ValueError("Invalid ledger serialization") from None


def _authentication(data, repository, parent, key):
    # Domain fields come from trusted API configuration and the actual Git
    # commit, never from attacker-supplied fields in ledger.json.
    message = _canonical({**data, "repository": repository, "parent": parent})
    return hmac.new(key, message, hashlib.sha256).hexdigest()


def _integer(value, minimum=0):
    return type(value) is int and value >= minimum


def _run(value):
    _require(type(value) is str and re.fullmatch(r"[0-9]+", value) is not None,
             "Invalid ledger run ID")
    # Different spellings must not authorize reuse of the same Actions run.
    return value.lstrip("0") or "0"


def _label(value):
    return (type(value) is str and 0 < len(value) <= 200
            and value == value.strip() and value.isprintable())


def _request(api, path, payload=None, method="GET", *, missing_ok=False):
    try:
        response = api(path, payload=payload, method=method)
    except Exception as error:
        if missing_ok and (isinstance(error, FileNotFoundError) or any(
                getattr(error, name, None) == 404
                for name in ("status", "status_code", "code"))):
            return None
        # Transport exceptions can contain authorization headers or response text.
        raise OSError("Contribution ledger API request failed") from None
    _require(type(response) is dict, "Invalid ledger API response")
    return response


def _ref_sha(response):
    _require(response.get("ref") == REF, "Unexpected ledger ref")
    obj = response.get("object")
    _require(type(obj) is dict and obj.get("type") == "commit",
             "Invalid ledger ref object")
    return _sha(obj.get("sha"))


def _record(record):
    _require(type(record) is dict and set(record) == FIELDS,
             "Invalid reservation fields")
    for key in ("approval_id", "snapshot_hash", "policy_sha256"):
        _require(_hex(record[key], 64), "Invalid reservation digest")
    _sha(record["base_commit"])
    _run(record["run_id"])
    _require(_label(record["service"]) and _label(record["model"]),
             "Invalid reservation model")
    for key in ("input_chars", "output_tokens"):
        _require(_integer(record[key], 1), "Reservation amounts must be positive integers")
    _require(_integer(record["actor_id"]), "Invalid reservation actor ID")


def _usage(value):
    _require(value is None or type(value) is dict, "Invalid receipt usage")
    if value is None:
        return None
    # Persist only known numeric counters, never raw provider response fields.
    result = {}
    for key in sorted(USAGE_FIELDS):
        number = value.get(key)
        if (type(number) in (int, float) and 0 <= number <= MAX_USAGE
                and (type(number) is int or math.isfinite(number))):
            result[key] = number
    return result or None


def _version(value):
    _require(value is None or type(value) is str, "Invalid receipt model version")
    if (value is not None and len(value) <= 200
            and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:/+-]*", value)):
        return value
    return None


def _validate(data):
    _require(type(data) is dict and set(data) == {"version", "reservations"})
    _require(type(data["version"]) is int and data["version"] == 2,
             "Unsupported ledger version")
    entries = data["reservations"]
    _require(type(entries) is dict, "Invalid ledger reservations")
    approvals, runs = set(), set()
    for approval, entry in entries.items():
        _require(_hex(approval, 64) and type(entry) is dict)
        state = entry.get("state")
        _require(type(state) is str and state in {"reserved", "complete", "unknown"},
                 "Invalid reservation state")
        expected = FIELDS | {"state"}
        if state != "reserved":
            expected |= {"usage", "model_version"}
        _require(set(entry) == expected, "Invalid stored reservation fields")
        _record({key: entry[key] for key in FIELDS})
        _require(approval == entry["approval_id"], "Reservation key mismatch")
        canonical_run = _run(entry["run_id"])
        _require(approval.lower() not in approvals and canonical_run not in runs,
                 "Duplicate ledger reservation")
        approvals.add(approval.lower())
        runs.add(canonical_run)
        if state != "reserved":
            usage = entry["usage"]
            # Equality alone would accept bool as int and an empty dict as None.
            _require(usage is None or (
                type(usage) is dict and bool(usage)
                and set(usage) <= USAGE_FIELDS
                and all(type(n) in (int, float) for n in usage.values())
                and _usage(usage) == usage), "Invalid stored receipt usage")
            _require(_version(entry["model_version"]) == entry["model_version"],
                     "Invalid stored model version")


def _encoded(data, repository, parent, key):
    _require(type(data) is dict, "Invalid ledger data")
    unsigned = {name: value for name, value in data.items() if name != "authentication"}
    _validate(unsigned)
    authenticated = {**unsigned, "authentication":
                     _authentication(unsigned, repository, parent, key)}
    raw = _canonical(authenticated) + b"\n"
    _require(len(raw) <= MAX_BYTES, "Contribution ledger exceeds size limit")
    return raw


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        _require(key not in result, "Duplicate ledger JSON key")
        result[key] = value
    return result


def _constant(_value):
    raise ValueError("Invalid ledger JSON number")


def _commit(api, data, parent, key, repository):
    raw = _encoded(data, repository, parent, key)
    blob = _request(api, "/git/blobs", {
        "content": base64.b64encode(raw).decode("ascii"), "encoding": "base64",
    }, "POST")
    blob_sha = _sha(blob.get("sha"))
    tree = _request(api, "/git/trees", {"tree": [{
        "path": "ledger.json", "mode": "100644", "type": "blob", "sha": blob_sha,
    }]}, "POST")  # Deliberately no base_tree: no repository contents are inherited.
    tree_sha = _sha(tree.get("sha"))
    # Unique commits also make identical concurrent reservations siblings: a
    # repeated PATCH to the very same SHA would otherwise succeed twice.
    commit = _request(api, "/git/commits", {
        "message": "Update contribution ledger " + uuid.uuid4().hex, "tree": tree_sha,
        "parents": [] if parent is None else [parent],
    }, "POST")
    return _sha(commit.get("sha"))


def initialize(api, key=None):
    """Create an orphan ledger, or return the validated existing head unchanged.

    Pin the returned root SHA only on first creation. For an existing branch,
    the return value is its current head for inspection, NOT a replacement for
    the previously trusted anchor. Keep that anchor and use Ledger(api, anchor)
    for subsequent reads: this function cannot recover or authenticate it.
    Existing-branch validation checks authenticated current objects against their
    own head; it does not establish continuity with the original trusted anchor.
    Neither path removes history or reservations.

    Absence must be explicit (FileNotFoundError or an exception with HTTP 404).
    A failed create-ref race is surfaced without retrying or resetting the branch.
    """
    _require(callable(api), "Invalid ledger API")
    signing_key = _key(key)
    repository = _repository(api)
    existing = _request(api, READ_REF, missing_ok=True)
    if existing is not None:
        head, _ = Ledger(api, _ref_sha(existing), key).read()
        return head
    head = _commit(api, {"version": 2, "reservations": {}}, None, signing_key, repository)
    response = _request(api, "/git/refs", {"ref": REF, "sha": head}, "POST")
    _require(_ref_sha(response) == head, "Ledger initialization was not confirmed")
    return head


class Ledger:
    def __init__(self, api, anchor, key=None):
        _require(callable(api), "Invalid ledger API")
        self._key = _key(key)
        self._repository = _repository(api)
        self.api = api
        self.anchor = _sha(anchor)

    def read(self):
        """Read and validate the anchored Git object chain; never auto-initialize."""
        head = _ref_sha(_request(self.api, READ_REF))
        comparison = _request(self.api, f"/compare/{self.anchor}...{head}")
        expected_status = "identical" if head == self.anchor else "ahead"
        _require(comparison.get("status") == expected_status,
                 "Ledger is not descended from its anchor")
        merge_base = comparison.get("merge_base_commit")
        _require(type(merge_base) is dict
                 and _sha(merge_base.get("sha")) == self.anchor,
                 "Ledger anchor mismatch")
        commit = _request(self.api, f"/git/commits/{head}")
        _require(_sha(commit.get("sha")) == head, "Ledger commit mismatch")
        parent = _parent(commit)
        _require(parent is not None or head == self.anchor, "Unexpected orphan ledger commit")
        tree_ref = commit.get("tree")
        _require(type(tree_ref) is dict, "Invalid ledger commit tree")
        tree_sha = _sha(tree_ref.get("sha"))
        tree = _request(self.api, f"/git/trees/{tree_sha}")
        _require(_sha(tree.get("sha")) == tree_sha and tree.get("truncated") is False,
                 "Invalid or truncated ledger tree")
        items = tree.get("tree")
        _require(type(items) is list and len(items) == 1, "Unexpected ledger tree entries")
        item = items[0]
        _require(type(item) is dict and item.get("path") == "ledger.json"
                 and item.get("type") == "blob" and item.get("mode") == "100644",
                 "Invalid ledger file")
        blob_sha = _sha(item.get("sha"))
        size = item.get("size")
        _require(_integer(size) and size <= MAX_BYTES, "Invalid ledger file size")
        blob = _request(self.api, f"/git/blobs/{blob_sha}")
        _require(_sha(blob.get("sha")) == blob_sha and blob.get("encoding") == "base64"
                 and type(blob.get("size")) is int and blob["size"] == size,
                 "Invalid ledger blob")
        content = blob.get("content")
        max_encoded = 4 * ((MAX_BYTES + 2) // 3)
        _require(type(content) is str and len(content) <= 2 * max_encoded,
                 "Invalid ledger blob content")
        content = content.replace("\r", "").replace("\n", "")
        _require(len(content) <= max_encoded, "Ledger blob exceeds size limit")
        try:
            raw = base64.b64decode(content, validate=True)
            _require(len(raw) == size, "Ledger blob size mismatch")
            data = json.loads(raw.decode("utf-8"), object_pairs_hook=_pairs,
                              parse_constant=_constant)
        except (ValueError, TypeError, UnicodeError, binascii.Error, RecursionError):
            raise ValueError("Invalid ledger JSON or encoding") from None
        _require(type(data) is dict
                 and set(data) == {"version", "reservations", "authentication"},
                 "Invalid authenticated ledger fields")
        authentication = data["authentication"]
        _require(type(authentication) is str
                 and re.fullmatch(r"[0-9a-f]{64}", authentication) is not None,
                 "Invalid ledger authentication")
        unsigned = {name: value for name, value in data.items() if name != "authentication"}
        _validate(unsigned)
        expected = _authentication(unsigned, self._repository, parent, self._key)
        _require(hmac.compare_digest(authentication, expected),
                 "Ledger authentication failed")
        return head, data

    def _write(self, head, data):
        new_head = _commit(self.api, data, head, self._key, self._repository)
        # Siblings share parent=head. Git's atomic fast-forward check accepts at
        # most one; a loser must stop, including when the PATCH result is unknown.
        response = _request(self.api, WRITE_REF, {"sha": new_head, "force": False}, "PATCH")
        _require(_ref_sha(response) == new_head, "Ledger update was not confirmed")

    def _status(self, run_id):
        response = _request(self.api, "/actions/runs/" + _run(run_id))
        if "id" in response:
            _require(_integer(response["id"]) and str(response["id"]) == _run(run_id),
                     "Actions run identity mismatch")
        status = response.get("status")
        _require(type(status) is str, "Invalid Actions run status")
        return status

    def _active(self, entries, exclude=None):
        _require(all(entry["state"] != "unknown" for entry in entries.values()),
                 "Unknown reservation requires reconciliation")
        count = 0
        for approval, entry in entries.items():
            if entry["state"] == "reserved":
                count += 1
                if approval != exclude:
                    _require(self._status(entry["run_id"]) in ACTIVE,
                             "Stale or uncertain reservation requires reconciliation")
        return count

    def reserve(self, record, policy):
        """Persist a full reservation before the caller may request any model."""
        _record(record)
        _require(type(policy) is dict and POLICY_FIELDS <= set(policy),
                 "Invalid reservation policy")
        for key in POLICY_FIELDS:
            _require(_integer(policy[key], 1), "Invalid reservation policy limit")
        _require(policy["max_in_flight"] <= 3, "Invalid in-flight limit")
        head, data = self.read()
        entries = data["reservations"]
        _require(all(key.lower() != record["approval_id"].lower() for key in entries),
                 "Approval already reserved")
        _require(all(_run(entry["run_id"]) != _run(record["run_id"])
                     for entry in entries.values()), "Run already reserved")
        active = self._active(entries)
        _require(active < policy["max_in_flight"], "In-flight limit exceeded")
        _require(len(entries) + 1 <= policy["cumulative_calls"], "Call quota exceeded")
        for field in ("input_chars", "output_tokens"):
            _require(sum(entry[field] for entry in entries.values()) + record[field]
                     <= policy["cumulative_" + field], "Cumulative quota exceeded")
        entry = dict(record, state="reserved")
        entries[record["approval_id"]] = entry
        self._write(head, data)
        return entry

    def verify_reservation(self, record):
        """Recheck the durable reservation immediately before the model request."""
        _require(type(record) is dict and set(record) in (FIELDS, FIELDS | {"state"}),
                 "Invalid reservation fields")
        if "state" in record:
            _require(record["state"] == "reserved", "Reservation is not reserved")
        immutable = {key: record[key] for key in FIELDS}
        _record(immutable)
        _, data = self.read()
        entries = data["reservations"]
        entry = entries.get(record["approval_id"])
        _require(entry == dict(immutable, state="reserved"),
                 "Durable reservation does not match")
        self._active(entries, exclude=record["approval_id"])
        return dict(entry)

    def settle(self, approval_id, run_id, receipt):
        """Finalize a reserved entry without reducing any cumulative reservation."""
        _require(_hex(approval_id, 64), "Invalid approval ID")
        _run(run_id)
        _require(type(receipt) is dict
                 and set(receipt) == {"state", "usage", "model_version"},
                 "Invalid reservation receipt")
        usage, version = _usage(receipt["usage"]), _version(receipt["model_version"])
        head, data = self.read()
        entry = data["reservations"].get(approval_id)
        _require(entry is not None and entry["run_id"] == run_id
                 and entry["state"] == "reserved", "Reservation cannot be settled")
        entry.update(state="complete" if receipt["state"] == "complete" else "unknown",
                     usage=usage, model_version=version)
        self._write(head, data)
        return dict(entry)

    def reconcile(self, approval_id):
        """Close an uncertain entry after its run completes; caller gates maintainers.

        This records unknown usage, keeps the full reservation and never grants a
        second request for either the approval or its Actions run.
        """
        _require(_hex(approval_id, 64), "Invalid approval ID")
        head, data = self.read()
        entry = data["reservations"].get(approval_id)
        _require(entry is not None and entry["state"] in {"reserved", "unknown"},
                 "Reservation cannot be reconciled")
        _require(self._status(entry["run_id"]) == "completed",
                 "Referenced run has not completed")
        entry.update(state="complete", usage=None, model_version=None)
        self._write(head, data)
        return dict(entry)
