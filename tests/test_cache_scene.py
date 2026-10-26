"""Phase V1 (post-delivery): The Cache Machine 3D view tests.

Payload fidelity (the builder copies engine fields verbatim), snapshot
alignment, deterministic HTML, layout geometry for all three
organizations, availability rules, and the regression that requesting
per-access snapshots does not change simulation results. Engine-backed
tests are skipped loudly when build/cache_sim.exe is missing.
"""

import json

import pytest

import test_smoke as ts
from bots import engine_client
from ui import cache_scene

ENGINE = ts.ROOT / "build" / "cache_sim.exe"
ENGINE_SKIP = ts.ENGINE_SKIP

E2_TRACE = [0, 8, 16, 24, 0]
E2_CONFIG = {"capacity_bytes": 8, "block_size_bytes": 2,
             "organization": "direct", "address_width_bits": 8,
             "hit_time": 1.0, "miss_penalty": 20.0}


def run_envelope(config, addresses, with_snapshots=True):
    job = {"config": config,
           "trace": {"name": "t", "addresses": addresses}}
    if with_snapshots:
        job["options"] = {"include_state_after_each": True}
    return engine_client.run_simulate(job)


# --- Pure builder tests (no engine needed) -----------------------------------


class TestPayloadBuilder:
    ENVELOPE = {
        "geometry": {"capacity_bytes": 8, "block_size_bytes": 2,
                     "organization": "set_associative", "associativity": 2,
                     "address_width_bits": 8, "lines": 4, "sets": 2,
                     "offset_bits": 1, "index_bits": 1, "tag_bits": 6},
        "events": [
            {"n": 1, "address": 0, "block": 0, "tag": 0, "index": 0,
             "offset": 0, "set": 0, "way": 0, "result": "miss",
             "loaded": True, "evicted": None,
             "policy_meta": {"policy": "LRU", "victim_selection": "none"},
             "explanation": "Miss: block 0 loaded into set 0 way 0 (empty line)."},
            {"n": 2, "address": 8, "block": 4, "tag": 2, "index": 0,
             "offset": 0, "set": 0, "way": 1, "result": "miss",
             "loaded": True,
             "evicted": {"block": 0, "tag": 0, "way": 0},
             "policy_meta": {"policy": "LRU", "victim_selection": "lru"},
             "explanation": "Miss: block 4 loaded into set 0 way 1, evicting block 0 (LRU)."},
        ],
        "state": {"snapshots": [
            {"n": 1, "sets": [[
                {"way": 0, "valid": True, "tag": 0, "block": 0,
                 "last_used_rank": 1, "insert_order_rank": None},
                {"way": 1, "valid": False, "tag": None, "block": None,
                 "last_used_rank": None, "insert_order_rank": None}]]},
            {"n": 2, "sets": [[
                {"way": 0, "valid": True, "tag": 2, "block": 4,
                 "last_used_rank": 1, "insert_order_rank": None},
                {"way": 1, "valid": True, "tag": 0, "block": 0,
                 "last_used_rank": 2, "insert_order_rank": None}]]},
        ]},
        "summary": {"accesses": 2, "hits": 0, "misses": 2, "evictions": 1},
    }

    def test_payload_maps_events_verbatim(self):
        result = cache_scene.build_payload(self.ENVELOPE)
        assert result["ok"] is True
        events = result["payload"]["events"]
        assert len(events) == 2
        first = events[0]
        assert first["n"] == 1 and first["address"] == 0
        assert first["block"] == 0 and first["tag"] == 0
        assert first["set"] == 0 and first["way"] == 0
        assert first["result"] == "miss" and first["loaded"] is True
        assert first["evicted"] is None
        assert first["victimSelection"] == "none"
        second = events[1]
        assert second["evicted"] == {"block": 0, "tag": 0, "way": 0}
        assert second["victimSelection"] == "lru"
        assert second["explanation"].startswith("Miss: block 4")

    def test_payload_maps_snapshots_aligned_with_events(self):
        result = cache_scene.build_payload(self.ENVELOPE)
        payload = result["payload"]
        snapshots = payload["snapshots"]
        events = payload["events"]
        assert len(snapshots) == len(events) == 2
        assert snapshots[0]["n"] == events[0]["n"] == 1
        assert snapshots[1]["n"] == events[1]["n"] == 2
        # snapshot content is the engine's per-way state, copied verbatim
        assert snapshots[1]["sets"][0][0] == {
            "way": 0, "valid": True, "tag": 2, "block": 4,
            "last_used_rank": 1, "insert_order_rank": None}

    def test_payload_maps_geometry(self):
        result = cache_scene.build_payload(self.ENVELOPE)
        geometry = result["payload"]["geometry"]
        assert geometry["sets"] == 2
        assert geometry["waysPerSet"] == 2
        assert geometry["lines"] == 4
        assert geometry["indexBits"] == 1 and geometry["tagBits"] == 6

    def test_memory_blocks_sorted_unique_and_capped(self):
        envelope = json.loads(json.dumps(self.ENVELOPE))
        envelope["events"] = [
            dict(envelope["events"][0], block=block, n=n + 1,
                 address=block * 2)
            for n, block in enumerate([5, 1, 5, 2, 1])]
        envelope["state"]["snapshots"] = [
            {"n": n + 1, "sets": [[{"way": 0, "valid": True, "tag": block,
                                    "block": block, "last_used_rank": 1,
                                    "insert_order_rank": None}]]}
            for n, block in enumerate([5, 1, 5, 2, 1])]
        envelope["summary"] = {"accesses": 5, "hits": 0, "misses": 5,
                               "evictions": 4}
        result = cache_scene.build_payload(envelope)
        blocks = result["payload"]["memory"]["blocks"]
        assert blocks == sorted(set([5, 1, 2]))  # unique + sorted
        assert result["payload"]["memory"]["truncated"] is False

    def test_deterministic_html(self):
        first = cache_scene.build_html(self.ENVELOPE)["html"]
        second = cache_scene.build_html(json.loads(
            json.dumps(self.ENVELOPE)))["html"]
        assert first == second and len(first) > 1000
        assert "window.CACHE_PAYLOAD" in first

    def test_html_never_breaks_script_tag(self):
        envelope = json.loads(json.dumps(self.ENVELOPE))
        envelope["events"][0]["explanation"] = "evil </script> attempt"
        html = cache_scene.build_html(envelope)["html"]
        # the escaped payload must not contain a raw </script> from the JSON
        body = html.split("window.CACHE_PAYLOAD = ")[1]
        assert "</script>" not in body.split(";</script>")[0]

    def test_missing_snapshots_reported(self):
        envelope = json.loads(json.dumps(self.ENVELOPE))
        envelope["state"]["snapshots"] = None
        result = cache_scene.build_payload(envelope)
        assert result["ok"] is False
        assert "snapshots were not captured" in result["reason"]

    def test_empty_trace_is_supported(self):
        envelope = json.loads(json.dumps(self.ENVELOPE))
        envelope["events"] = []
        envelope["state"]["snapshots"] = []
        envelope["summary"] = {"accesses": 0, "hits": 0, "misses": 0,
                               "evictions": 0}
        result = cache_scene.build_payload(envelope)
        assert result["ok"] is True
        assert result["payload"]["events"] == []
        assert result["payload"]["snapshots"] == []


class TestSceneAvailability:
    def test_available_for_small_cache(self):
        reasons = cache_scene.scene_unavailable_reasons(
            ts.CONFIG_SET_ASSOCIATIVE, 5)
        assert reasons == []

    def test_trace_over_2000(self):
        reasons = cache_scene.scene_unavailable_reasons(
            ts.CONFIG_SET_ASSOCIATIVE, 2001)
        assert any("2,000" in r or "2000" in r for r in reasons)

    def test_lines_over_stage_cap(self):
        config = dict(ts.CONFIG_DIRECT, capacity_bytes=2048,
                      block_size_bytes=2)  # 1024 lines
        reasons = cache_scene.scene_unavailable_reasons(config, 5)
        assert any("1,024 lines" in r or "1024 lines" in r for r in reasons)

    def test_fully_associative_ways_cap(self):
        config = dict(ts.CONFIG_FULLY_ASSOCIATIVE,
                      capacity_bytes=2048, block_size_bytes=2,
                      address_width_bits=16)  # 1024 ways in one set
        reasons = cache_scene.scene_unavailable_reasons(config, 5)
        assert any("1,024 ways" in r or "1024 ways" in r for r in reasons)


# --- Integration with the real engine ----------------------------------------


@pytest.mark.skipif(not ENGINE.exists(), reason=ENGINE_SKIP)
class TestRealEngineIntegration:
    def test_snapshots_do_not_change_simulation_results(self):
        without = run_envelope(ts.CONFIG_SET_ASSOCIATIVE, [0, 4, 0, 8, 4],
                               with_snapshots=False)
        with_snap = run_envelope(ts.CONFIG_SET_ASSOCIATIVE, [0, 4, 0, 8, 4],
                                 with_snapshots=True)
        assert without["events"] == with_snap["events"]
        assert without["summary"] == with_snap["summary"]
        assert without["geometry"] == with_snap["geometry"]
        # the only difference is the captured snapshots
        assert with_snap["state"]["snapshots"] is not None
        assert len(with_snap["state"]["snapshots"]) == 5

    def test_e2_events_and_snapshots_aligned(self):
        envelope = run_envelope(E2_CONFIG, E2_TRACE)
        events = envelope["events"]
        assert [(e["result"], e["evicted"] and e["evicted"]["block"])
                for e in events] == [
            ("miss", None), ("miss", 0), ("miss", 4), ("miss", 8), ("miss", 12)]
        snapshots = envelope["state"]["snapshots"]
        assert [s["n"] for s in snapshots] == [1, 2, 3, 4, 5]
        # final state matches the documented corrected E2 end state
        final = snapshots[-1]["sets"]
        flat = [line for ways in final for line in ways if line["valid"]]
        assert [(line["block"], line["tag"]) for line in flat] == [(0, 0)]

    def test_layouts_for_three_organizations(self):
        configs = {
            "direct": dict(ts.CONFIG_DIRECT),
            "set_associative": dict(ts.CONFIG_SET_ASSOCIATIVE),
            "fully_associative": dict(ts.CONFIG_FULLY_ASSOCIATIVE),
        }
        expected = {
            "direct": {"sets": 4, "waysPerSet": 1},
            "set_associative": {"sets": 2, "waysPerSet": 2},
            "fully_associative": {"sets": 1, "waysPerSet": 4},
        }
        for organization, config in configs.items():
            envelope = run_envelope(config, [0, 4])
            geometry = envelope["geometry"]
            assert geometry["sets"] == expected[organization]["sets"], \
                organization
            assert geometry["lines"] // geometry["sets"] \
                == expected[organization]["waysPerSet"], organization

    def test_payload_and_html_for_e2(self):
        envelope = run_envelope(E2_CONFIG, E2_TRACE)
        result = cache_scene.build_payload(envelope)
        assert result["ok"] is True
        payload = result["payload"]
        assert payload["geometry"]["sets"] == 4
        assert payload["geometry"]["waysPerSet"] == 1
        assert [e["evicted"]["block"] for e in payload["events"]
                if e["evicted"]] == [0, 4, 8, 12]
        html = cache_scene.build_html(envelope)["html"]
        assert "window.CACHE_PAYLOAD" in html

    def test_limit_reasons_flow_from_real_config(self):
        # capacity 2048 / block 2 = 1024 lines > 512-line stage cap
        reasons = cache_scene.scene_unavailable_reasons(
            dict(ts.CONFIG_DIRECT, capacity_bytes=2048), 5)
        assert reasons
