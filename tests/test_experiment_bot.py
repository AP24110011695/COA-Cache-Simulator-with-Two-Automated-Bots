"""Phase 7: Bot 2 (experiment_bot) tests (AC-P7.1..P7.5).

Unit tests run against canned schema-shaped envelopes via a stub
`simulate_fn` (no engine logic reimplemented); integration tests use the
real engine through `bots.engine_client.run_simulate` and assert the
published E3/E5 outcomes (D-15) and the E2 organization comparison.
"""

import hashlib
import json

import pytest

import test_smoke as ts
from bots import engine_client
from bots.experiment_bot import run_experiment, save_report

ENGINE = ts.ROOT / "build" / "cache_sim.exe"
ENGINE_SKIP = ts.ENGINE_SKIP

FAKE_SHA = "ab" * 32  # schema-shaped 64-hex placeholder for canned summaries


def canned_summary(hits, accesses=5, evictions=2):
    """A complete, summary.schema.json-shaped summary with chosen numbers."""
    return {
        "accesses": accesses,
        "hits": hits,
        "misses": accesses - hits,
        "evictions": evictions,
        "hit_rate": hits / accesses,
        "miss_rate": (accesses - hits) / accesses,
        "amat": {"hit_time": 1.0, "miss_penalty": 20.0,
                 "value": 1.0 + (accesses - hits) / accesses * 20.0,
                 "unit": "cycles"},
        "trace_sha256": FAKE_SHA,
    }


def canned_policy_simulate(hits_by_policy, evictions=2):
    """Stub simulate_fn keyed by the run config's policy."""
    def simulate_fn(job):
        policy = job["config"]["policy"]
        return {"ok": True,
                "engine": {"name": "cache_sim", "version": "0.1.0"},
                "summary": canned_summary(hits_by_policy[policy],
                                          evictions=evictions)}
    return simulate_fn


def canned_org_simulate(hits_by_org, accesses=5, evictions=2):
    """Stub simulate_fn keyed by the run config's organization."""
    def simulate_fn(job):
        organization = job["config"]["organization"]
        return {"ok": True,
                "engine": {"name": "cache_sim", "version": "0.1.0"},
                "summary": canned_summary(hits_by_org[organization],
                                          accesses=accesses,
                                          evictions=evictions)}
    return simulate_fn


def policy_request(**overrides):
    request = {
        "mode": "policy_comparison",
        "trace": {"name": "lru-vs-fifo-demo", "addresses": [0, 4, 0, 8, 4]},
        "config": ts.CONFIG_SET_ASSOCIATIVE,
        "random_seed": 12345,
    }
    request.update(overrides)
    return request


def org_request(**overrides):
    request = {
        "mode": "organization_comparison",
        "trace": {"name": "e2-conflict", "addresses": [0, 8, 16, 24, 0]},
        "config": ts.CONFIG_SET_ASSOCIATIVE,
    }
    request.update(overrides)
    return request


# --- Policy comparison: construction, refusal, templates --------------------


class TestPolicyComparisonUnit:
    def test_matrix_changes_only_the_policy(self):
        response = run_experiment(
            policy_request(), canned_policy_simulate({"LRU": 1, "FIFO": 2,
                                                      "RANDOM": 2}))
        assert response["ok"] is True
        record = response["record"]
        configs = [run["config"] for run in record["runs"]]
        stripped = [{k: v for k, v in c.items() if k not in ("policy", "seed")}
                    for c in configs]
        assert stripped[0] == stripped[1] == stripped[2]
        assert [c["policy"] for c in configs] == ["LRU", "FIFO", "RANDOM"]
        assert [run["seed"] for run in record["runs"]] == [None, None, 12345]
        assert [run["run_id"] for run in record["runs"]] == [1, 2, 3]

    def test_stale_seed_stripped_from_lru_and_fifo_runs(self):
        # A RANDOM-shaped base config must not leak its seed into the
        # LRU/FIFO run configs (D-17: non-null seed with non-RANDOM is
        # invalid at the engine).
        base = dict(ts.CONFIG_SET_ASSOCIATIVE, policy="RANDOM", seed=7)
        response = run_experiment(
            {"mode": "policy_comparison",
             "trace": {"name": "t", "addresses": [0, 4, 0, 8, 4]},
             "config": base, "random_seed": 42},
            canned_policy_simulate({"LRU": 1, "FIFO": 1, "RANDOM": 1}))
        assert response["ok"] is True
        for run in response["record"]["runs"]:
            if run["policy"] != "RANDOM":
                assert "seed" not in run["config"]
        random_run = response["record"]["runs"][2]
        assert random_run["config"]["seed"] == 42

    def test_refuses_direct_mapped(self):
        response = run_experiment(
            policy_request(config=ts.CONFIG_DIRECT),
            canned_policy_simulate({"LRU": 1, "FIFO": 1, "RANDOM": 1}))
        assert response["ok"] is False
        assert response["error"]["code"] == "E_CONFIG_INVALID"
        assert "direct-mapped" in response["error"]["message"]

    def test_random_seed_required(self):
        request = policy_request()
        del request["random_seed"]
        response = run_experiment(request,
                                  canned_policy_simulate({"LRU": 1,
                                                          "FIFO": 1,
                                                          "RANDOM": 1}))
        assert response["error"]["code"] == "E_JOB_INVALID"
        assert "random_seed" in response["error"]["message"]

    def test_random_seed_range(self):
        response = run_experiment(policy_request(random_seed=-1),
                                  canned_policy_simulate({"LRU": 1,
                                                          "FIFO": 1,
                                                          "RANDOM": 1}))
        assert response["error"]["code"] == "E_JOB_INVALID"

    def test_summary_text_single_winner(self):
        response = run_experiment(
            policy_request(random_seed=42),
            canned_policy_simulate({"LRU": 2, "FIFO": 1, "RANDOM": 1}))
        text = response["record"]["summary_text"]
        assert text == (
            "LRU: 2 hits / 5 accesses (40.00%), 2 evictions. "
            "FIFO: 1 hit / 5 accesses (20.00%), 2 evictions. "
            "RANDOM (seed 42): 1 hit / 5 accesses (20.00%), 2 evictions. "
            "Best hit rate: LRU (40.00% vs FIFO 20.00% and RANDOM 20.00%).")

    def test_summary_text_two_way_tie(self):
        response = run_experiment(
            policy_request(),
            canned_policy_simulate({"LRU": 1, "FIFO": 2, "RANDOM": 2}))
        text = response["record"]["summary_text"]
        assert text.endswith(
            "Best hit rate: FIFO and RANDOM tie at 40.00% (LRU 20.00%).")

    def test_summary_text_three_way_tie(self):
        response = run_experiment(
            policy_request(random_seed=42),
            canned_policy_simulate({"LRU": 1, "FIFO": 1, "RANDOM": 1}))
        text = response["record"]["summary_text"]
        assert text.endswith("Best hit rate: LRU, FIFO and RANDOM tie at "
                             "20.00%.")

    def test_summary_text_changes_when_numbers_change(self):
        first = run_experiment(policy_request(),
                               canned_policy_simulate({"LRU": 1, "FIFO": 2,
                                                       "RANDOM": 2}))
        second = run_experiment(policy_request(),
                                canned_policy_simulate({"LRU": 2, "FIFO": 2,
                                                        "RANDOM": 2}))
        assert first["record"]["summary_text"] != \
            second["record"]["summary_text"]
        assert first["record"]["summary_text"].startswith("LRU: 1 hit")
        assert second["record"]["summary_text"].startswith("LRU: 2 hits")

    def test_summary_text_deterministic(self):
        first = run_experiment(policy_request(),
                               canned_policy_simulate({"LRU": 1, "FIFO": 2,
                                                       "RANDOM": 2}))
        second = run_experiment(policy_request(),
                                canned_policy_simulate({"LRU": 1, "FIFO": 2,
                                                        "RANDOM": 2}))
        assert first["record"]["summary_text"] == \
            second["record"]["summary_text"]


# --- Organization comparison -------------------------------------------------


class TestOrganizationComparisonUnit:
    def test_matrix_changes_only_the_organization(self):
        response = run_experiment(
            org_request(), canned_org_simulate({"direct": 0,
                                                "set_associative": 2,
                                                "fully_associative": 3}))
        assert response["ok"] is True
        record = response["record"]
        runs = record["runs"]
        assert [r["config"]["organization"] for r in runs] == [
            "direct", "set_associative", "fully_associative"]
        # LRU wherever a policy exists; direct-mapped has none (AC-P7.5).
        assert "policy" not in runs[0]["config"]
        assert runs[1]["config"]["policy"] == "LRU"
        assert runs[2]["config"]["policy"] == "LRU"
        # Associativity only where it applies.
        assert "associativity" not in runs[0]["config"]
        assert runs[1]["config"]["associativity"] == 2
        assert "associativity" not in runs[2]["config"]
        assert all(run["seed"] is None for run in runs)
        # Capacity/block/width held fixed (AC-P7.5).
        for run in runs:
            assert run["config"]["capacity_bytes"] == 8
            assert run["config"]["block_size_bytes"] == 2
            assert run["config"]["address_width_bits"] == 8

    def test_caveat_sentence_present(self):
        response = run_experiment(
            org_request(), canned_org_simulate({"direct": 0,
                                                "set_associative": 2,
                                                "fully_associative": 3}))
        text = response["record"]["summary_text"]
        assert text.endswith(
            "Caveat: direct-mapped has no selectable replacement policy; "
            "the set-associative and fully-associative runs use LRU.")

    def test_requires_set_associative_base(self):
        response = run_experiment(
            org_request(config=ts.CONFIG_DIRECT),
            canned_org_simulate({"direct": 0, "set_associative": 0,
                                 "fully_associative": 0}))
        assert response["error"]["code"] == "E_JOB_INVALID"
        assert "set_associative" in response["error"]["message"]

    def test_rejects_random_seed(self):
        response = run_experiment(org_request(random_seed=5),
                                  canned_org_simulate({"direct": 0,
                                                       "set_associative": 0,
                                                       "fully_associative": 0}))
        assert response["error"]["code"] == "E_JOB_INVALID"
        assert "random_seed" in response["error"]["message"]


# --- Request and trace validation --------------------------------------------


class TestRequestAndTraceValidation:
    def test_unknown_request_key(self):
        request = policy_request(random_sead=1)
        response = run_experiment(request,
                                  canned_policy_simulate({"LRU": 1,
                                                          "FIFO": 1,
                                                          "RANDOM": 1}))
        assert response["error"]["code"] == "E_JOB_INVALID"
        assert response["error"]["details"][0]["field"] == "random_sead"

    def test_unknown_mode(self):
        response = run_experiment(
            policy_request(mode="policy_shootout"),
            canned_policy_simulate({"LRU": 1, "FIFO": 1, "RANDOM": 1}))
        assert response["error"]["code"] == "E_JOB_INVALID"

    def test_empty_trace_rejected(self):
        request = policy_request(
            trace={"name": "empty", "addresses": []})
        response = run_experiment(request,
                                  canned_policy_simulate({"LRU": 1,
                                                          "FIFO": 1,
                                                          "RANDOM": 1}))
        assert response["error"]["code"] == "E_TRACE_INVALID"
        assert "at least one address" in response["error"]["message"]

    def test_trace_over_limit(self):
        request = policy_request(
            trace={"name": "huge", "addresses": [0] * 100001})
        response = run_experiment(request,
                                  canned_policy_simulate({"LRU": 1,
                                                          "FIFO": 1,
                                                          "RANDOM": 1}))
        assert response["error"]["code"] == "E_LIMIT"

    def test_trace_address_over_width(self):
        request = policy_request(
            trace={"name": "wide", "addresses": [0, 300]})
        response = run_experiment(request,
                                  canned_policy_simulate({"LRU": 1,
                                                          "FIFO": 1,
                                                          "RANDOM": 1}))
        assert response["error"]["code"] == "E_TRACE_INVALID"
        assert "255" in response["error"]["details"][0]["problem"]

    def test_trace_non_integer_address(self):
        request = policy_request(
            trace={"name": "bad", "addresses": [4, "8"]})
        response = run_experiment(request,
                                  canned_policy_simulate({"LRU": 1,
                                                          "FIFO": 1,
                                                          "RANDOM": 1}))
        assert response["error"]["code"] == "E_TRACE_INVALID"
        assert response["error"]["details"][0]["field"] == "trace.addresses[1]"

    def test_trace_name_required(self):
        request = policy_request(trace={"addresses": [4]})
        response = run_experiment(request,
                                  canned_policy_simulate({"LRU": 1,
                                                          "FIFO": 1,
                                                          "RANDOM": 1}))
        assert response["error"]["code"] == "E_TRACE_INVALID"
        assert "trace.name" in response["error"]["details"][0]["field"]

    def test_engine_error_passthrough(self):
        def failing_simulate(job):
            raise engine_client.EngineError(
                "E_TRACE_INVALID", "trace validation failed",
                [{"field": "trace.addresses[0]", "problem": "bad",
                  "received": 999}])
        response = run_experiment(policy_request(), failing_simulate)
        assert response["ok"] is False
        assert response["error"]["code"] == "E_TRACE_INVALID"

    def test_version_mismatch_is_internal(self):
        def mismatched_simulate(job):
            version = "0.1.0" if job["config"]["policy"] == "LRU" else "9.9.9"
            return {"ok": True,
                    "engine": {"name": "cache_sim", "version": version},
                    "summary": canned_summary(1)}
        response = run_experiment(policy_request(), mismatched_simulate)
        assert response["error"]["code"] == "E_INTERNAL"


# --- Report persistence -------------------------------------------------------


class TestSaveReport:
    def test_writes_deterministic_json(self, tmp_path):
        response = run_experiment(policy_request(),
                                  canned_policy_simulate({"LRU": 1,
                                                          "FIFO": 2,
                                                          "RANDOM": 2}))
        record = response["record"]
        path = save_report(record, tmp_path)
        assert path.name == f"{record['experiment_id']}.json"
        written = json.loads(path.read_text(encoding="utf-8"))
        assert written == record
        first_bytes = path.read_bytes()
        save_report(record, tmp_path)
        assert path.read_bytes() == first_bytes

    def test_creates_missing_directory(self, tmp_path):
        response = run_experiment(policy_request(),
                                  canned_policy_simulate({"LRU": 1,
                                                          "FIFO": 2,
                                                          "RANDOM": 2}))
        target = tmp_path / "reports"
        path = save_report(response["record"], target)
        assert path.exists() and path.parent == target


# --- Integration with the real engine (Phase 7 task 6) -----------------------


@pytest.mark.skipif(not ENGINE.exists(), reason=ENGINE_SKIP)
class TestRealEngineIntegration:
    def _run_with_engine(self, request):
        return run_experiment(request, engine_client.run_simulate)

    def test_e3_policy_comparison_reproduces_published_outcome(self):
        response = self._run_with_engine(policy_request())
        assert response["ok"] is True, response
        record = response["record"]
        assert [run["policy"] for run in record["runs"]] == [
            "LRU", "FIFO", "RANDOM"]
        lru, fifo, rnd = (run["summary"] for run in record["runs"])
        # architecture.md 13 E3 + E5: LRU 1/4/2 (AMAT 17.00), FIFO 2/3/1
        # (13.00), RANDOM seed 12345 2/3/1 (13.00, rng_draws 1).
        assert (lru["hits"], lru["misses"], lru["evictions"]) == (1, 4, 2)
        assert lru["amat"]["value"] == 17.0
        assert (fifo["hits"], fifo["misses"], fifo["evictions"]) == (2, 3, 1)
        assert fifo["amat"]["value"] == 13.0
        assert (rnd["hits"], rnd["misses"], rnd["evictions"]) == (2, 3, 1)
        assert rnd["amat"]["value"] == 13.0
        assert rnd["replacement_meta"]["rng_draws"] == 1
        assert record["runs"][2]["seed"] == 12345
        assert record["engine_version"] == "0.1.0"
        assert record["trace"]["sha256"] == hashlib.sha256(
            b"addresses:0,4,0,8,4").hexdigest()
        assert record["summary_text"] == (
            "LRU: 1 hit / 5 accesses (20.00%), 2 evictions. "
            "FIFO: 2 hits / 5 accesses (40.00%), 1 eviction. "
            "RANDOM (seed 12345): 2 hits / 5 accesses (40.00%), 1 eviction. "
            "Best hit rate: FIFO and RANDOM tie at 40.00% (LRU 20.00%).")

    def test_record_validates_against_schema(self):
        response = self._run_with_engine(policy_request())
        import test_smoke as _  # noqa: F401  (already imported above)
        from jsonschema import Draft7Validator, RefResolver
        schema = json.loads(
            (ts.ROOT / "schemas" / "experiment.schema.json")
            .read_text(encoding="utf-8"))
        Draft7Validator.check_schema(schema)
        store = {
            p.as_uri(): json.loads(p.read_text(encoding="utf-8"))
            for p in (ts.ROOT / "schemas").glob("*.schema.json")
        }
        resolver = RefResolver(
            base_uri=(ts.ROOT / "schemas").as_uri() + "/", referrer=schema,
            store=store)
        errors = list(Draft7Validator(schema, resolver=resolver)
                      .iter_errors(response["record"]))
        assert not errors, [e.message for e in errors]

    def test_e2_organization_comparison(self):
        response = self._run_with_engine(org_request())
        assert response["ok"] is True, response
        record = response["record"]
        runs = record["runs"]
        assert [r["config"]["organization"] for r in runs] == [
            "direct", "set_associative", "fully_associative"]
        # E2 (architecture.md 13): the direct run on this trace has 5
        # misses, 4 evictions, 0 hits.
        direct = runs[0]["summary"]
        assert (direct["hits"], direct["misses"],
                direct["evictions"]) == (0, 5, 4)
        # One variable at a time: capacity/block/width identical, LRU where
        # a policy exists (AC-P7.5).
        for run in runs:
            assert run["config"]["capacity_bytes"] == 8
            assert run["config"]["block_size_bytes"] == 2
            assert run["config"]["address_width_bits"] == 8
        assert "policy" not in runs[0]["config"]
        assert runs[1]["config"]["policy"] == "LRU"
        assert runs[2]["config"]["policy"] == "LRU"
        assert record["summary_text"].endswith(
            "Caveat: direct-mapped has no selectable replacement policy; "
            "the set-associative and fully-associative runs use LRU.")

    def test_save_report_round_trip(self, tmp_path):
        response = self._run_with_engine(policy_request())
        path = save_report(response["record"], tmp_path)
        reloaded = json.loads(path.read_text(encoding="utf-8"))
        assert reloaded == response["record"]
