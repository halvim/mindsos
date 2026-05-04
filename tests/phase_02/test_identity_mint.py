"""Phase 02 — `mindsos identity mint` exercises every IdStrategy."""

from __future__ import annotations

import json
import re


_UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
)


def test_strategy_required(cli):
    proc = cli("identity", "mint")
    assert proc.returncode == 2, (proc.returncode, proc.stderr)
    assert "--strategy is required" in proc.stderr


def test_uuid4_mint_yields_a_uuid(cli):
    proc = cli("identity", "mint", "--strategy", "uuid4", "--json")
    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["strategy"] == "uuid4"
    assert _UUID_RE.match(payload["id"]), payload["id"]


def test_uuid4_mints_are_distinct_across_invocations(cli):
    a = json.loads(cli("identity", "mint", "--strategy", "uuid4", "--json").stdout)["id"]
    b = json.loads(cli("identity", "mint", "--strategy", "uuid4", "--json").stdout)["id"]
    assert a != b


def test_uuid5_requires_seed(cli):
    proc = cli("identity", "mint", "--strategy", "uuid5", "--json")
    # UUID5FromContentStrategy.generate raises IdentityError when content is None.
    # The CLI catches it and exits 1 (not 2 — input WAS valid; the strategy
    # decided at generate() time).
    assert proc.returncode == 1, (proc.returncode, proc.stdout, proc.stderr)
    assert "UUID5FromContentStrategy requires non-None content" in proc.stderr


def test_uuid5_is_deterministic_for_the_same_seed(cli):
    seed = '{"value": "hello", "n": 1}'
    a = cli("identity", "mint", "--strategy", "uuid5", "--seed", seed, "--json")
    b = cli("identity", "mint", "--strategy", "uuid5", "--seed", seed, "--json")
    assert a.returncode == 0 and b.returncode == 0
    id_a = json.loads(a.stdout)["id"]
    id_b = json.loads(b.stdout)["id"]
    assert id_a == id_b
    assert _UUID_RE.match(id_a), id_a


def test_uuid5_changes_when_kind_changes(cli):
    seed = '{"x": 1}'
    a = cli("identity", "mint", "--strategy", "uuid5", "--seed", seed, "--kind", "node", "--json")
    b = cli("identity", "mint", "--strategy", "uuid5", "--seed", seed, "--kind", "edge", "--json")
    assert json.loads(a.stdout)["id"] != json.loads(b.stdout)["id"]


def test_iri_passthrough_returns_supplied_iri(cli):
    seed = '{"iri": "oewn-2024:synset:01234567-n"}'
    proc = cli("identity", "mint", "--strategy", "iri", "--seed", seed, "--json")
    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["id"] == "oewn-2024:synset:01234567-n"


def test_iri_passthrough_falls_back_to_uuid4_without_seed(cli):
    proc = cli("identity", "mint", "--strategy", "iri", "--json")
    assert proc.returncode == 0
    payload = json.loads(proc.stdout)
    assert _UUID_RE.match(payload["id"]), payload["id"]


def test_iri_passthrough_rejects_empty_iri(cli):
    seed = '{"iri": ""}'
    proc = cli("identity", "mint", "--strategy", "iri", "--seed", seed)
    assert proc.returncode == 1, (proc.returncode, proc.stdout, proc.stderr)
    assert "non-empty string" in proc.stderr


def test_invalid_strategy_name_exits_2(cli):
    proc = cli("identity", "mint", "--strategy", "uuid7")
    assert proc.returncode == 2, (proc.returncode, proc.stderr)
    assert "unknown --strategy" in proc.stderr


def test_seed_must_be_a_json_object(cli):
    proc = cli("identity", "mint", "--strategy", "uuid5", "--seed", "[1,2,3]")
    assert proc.returncode == 2
    assert "must decode to a JSON object" in proc.stderr


def test_seed_invalid_json_exits_2(cli):
    proc = cli("identity", "mint", "--strategy", "uuid5", "--seed", "{not-json}")
    assert proc.returncode == 2
    assert "not valid JSON" in proc.stderr
