"""UI state-machine sequence tests (Streamlit AppTest; audit-2 §9).

Exercises action ORDER, not single tabs: successful run → invalid input →
recovery, workflow failure → retry → completion (without re-running
successful stages), malformed sample → valid sample, and theme switching
while results are visible. Engine calls are counted through a wrapper on
bots.engine_client.run_simulate to pin retry semantics.

Skipped with the same loud message as the integration tests when the
engine has not been built (the workflow and simulations run it for real).
"""


import pytest

import test_smoke as ts
from streamlit.testing.v1 import AppTest

ENGINE = ts.ROOT / "build" / "cache_sim.exe"
ENGINE_SKIP = ts.ENGINE_SKIP

APP = ts.ROOT / "ui" / "app.py"


def fresh_app():
    at = AppTest.from_file(str(APP), default_timeout=120)
    return at


def set_sidebar_org(at, organization):
    for box in at.sidebar.selectbox:
        if box.label == "Organization":
            box.set_value(organization)
            return
    raise AssertionError("Organization selectbox not found")


def set_sidebar(at, label, value):
    for box in at.sidebar.selectbox:
        if box.label == label:
            box.set_value(value)
            return
    raise AssertionError(f"sidebar selectbox {label!r} not found")


def set_main_number(at, label, value):
    for widget in at.number_input:
        if widget.label == label:
            widget.set_value(value)
            return
    raise AssertionError(f"number input {label!r} not found")


def click_button(at, label):
    for button in at.button:
        if button.label == label:
            button.set_value(True)
            return
    raise AssertionError(f"button {label!r} not found")


def has_error(at):
    return len(at.error) > 0


@pytest.mark.skipif(not ENGINE.exists(), reason=ENGINE_SKIP)
class TestSimulatorSequences:
    def test_default_load_is_clean_and_gated(self):
        at = fresh_app()
        at.run()
        assert not at.exception, [e.value for e in at.exception]
        assert not has_error(at)
        run_sim = [b for b in at.button if b.label == "Run simulation"][0]
        assert run_sim.disabled  # no trace yet

    def test_run_then_invalid_generate_keeps_earlier_results(self):
        # Valid run → invalid generation → design.md 7: the error card
        # appears and the successful results stay visible; a subsequent
        # valid generation replaces them.
        at = fresh_app()
        at.run()
        set_main_number(at, "Access count", 16)
        click_button(at, "Generate trace")
        at.run()
        assert not at.exception
        click_button(at, "Run simulation")
        at.run()
        assert not at.exception
        first_accesses = [m.value for m in at.metric if m.label == "Accesses"]
        assert first_accesses == ["16"]

        # Invalid generation: over-limit count — a valid number for the
        # widget, rejected by Bot 1 (E_LIMIT).
        set_main_number(at, "Access count", 100001)
        click_button(at, "Generate trace")
        at.run()
        assert not at.exception
        assert has_error(at), "expected the E_LIMIT error card"
        # earlier results still on screen
        assert [m.value for m in at.metric if m.label == "Accesses"] == ["16"]

        # Recovery: valid generation replaces trace and results.
        set_main_number(at, "Access count", 8)
        click_button(at, "Generate trace")
        at.run()
        click_button(at, "Run simulation")
        at.run()
        assert not at.exception
        assert [m.value for m in at.metric if m.label == "Accesses"] == ["8"]

    def test_manual_paste_error_then_recovery(self):
        at = fresh_app()
        at.run()
        at.radio[0].set_value("Manual paste")
        at.run()
        # re-acquire the text area after every rerun (tree rebuilds)
        at.text_area[0].set_value("0x10\nabc\n")
        click_button(at, "Parse & load trace")
        at.run()
        assert not at.exception
        assert has_error(at)  # line 2 is not a valid address
        at.text_area[0].set_value("0x10\n16\n")
        click_button(at, "Parse & load trace")
        at.run()
        assert not at.exception
        assert not has_error(at)  # recovery: the error card is gone
        click_button(at, "Run simulation")
        at.run()
        assert [m.value for m in at.metric if m.label == "Accesses"] == ["2"]

    def test_config_change_rerun_replaces_results(self):
        # Hand-computed with the default trace (8 accesses, stride 4):
        # default 8 B / 2 B / 2-way config → blocks 0,2,…,14 all map to set 0
        # (block mod 2 = 0) → 2 fills + 6 evictions. Raising capacity to
        # 32 B gives 8 sets → blocks alternate sets 0,2,4,6, two per set →
        # 0 evictions. The displayed metrics must follow the new config.
        at = fresh_app()
        at.run()
        set_main_number(at, "Access count", 8)
        click_button(at, "Generate trace")
        at.run()
        click_button(at, "Run simulation")
        at.run()
        assert int([m.value for m in at.metric
                    if m.label == "Evictions"][0]) == 6
        set_sidebar(at, "Capacity (bytes, power of two)", 32)
        at.run()
        click_button(at, "Run simulation")
        at.run()
        assert not at.exception
        assert int([m.value for m in at.metric
                    if m.label == "Evictions"][0]) == 0

    def test_theme_switch_preserves_results(self):
        at = fresh_app()
        at.run()
        set_main_number(at, "Access count", 8)
        click_button(at, "Generate trace")
        at.run()
        click_button(at, "Run simulation")
        at.run()
        summary_before = [m.value for m in at.metric]
        set_sidebar(at, "Theme", "Dark")
        at.run()
        assert not at.exception
        assert [m.value for m in at.metric] == summary_before


@pytest.mark.skipif(not ENGINE.exists(), reason=ENGINE_SKIP)
class TestWorkflowSequences:
    def test_failure_retry_recovery_without_rerunning_success_stages(self,
                                                                     monkeypatch):
        # Sequence: direct-mapped org makes workflow step 3 (policy
        # comparison) fail by contract; steps 1-2 stay done. Then fixing the
        # organization and retrying completes the workflow — and the retry
        # must re-run ONLY the failed stage (3 simulate calls for the three
        # policies), not steps 1-2.
        calls = []
        real_run_simulate = __import__("bots.engine_client",
                                       fromlist=["run_simulate"]).run_simulate

        def counting_run_simulate(job, timeout_s=30.0):
            calls.append(job["config"]["organization"])
            return real_run_simulate(job, timeout_s)

        import bots.engine_client as engine_client
        monkeypatch.setattr(engine_client, "run_simulate",
                            counting_run_simulate)

        at = fresh_app()
        at.run()
        set_sidebar_org(at, "direct")
        at.run()
        set_main_number(at, "Conflict blocks", 2)
        set_main_number(at, "Passes", 1)
        click_button(at, "Run automated workflow")
        at.run()
        # The workflow results (and with them the Retry button) are stored
        # at the END of the click run — the post-click render shows them.
        at.run()
        assert not at.exception
        assert has_error(at)  # step 3: direct-mapped cannot be policy-compared
        workflow = at.session_state["workflow"]
        assert workflow["failed_step"] == 3
        assert workflow["trace"] is not None and \
            workflow["sim_envelope"] is not None  # steps 1-2 kept
        retry = [b for b in at.button if b.label == "Retry failed step"]
        assert retry and not retry[0].disabled
        assert calls.count("direct") == 1  # step 2 ran exactly once
        baseline = len(calls)

        # Fix the organization, retry the failed step.
        set_sidebar_org(at, "set_associative")
        at.run()
        click_button(at, "Retry failed step")
        at.run()
        assert not at.exception
        assert not has_error(at)
        # exactly the three policy runs of step 3 — no step 1/2 repeats
        assert len(calls) - baseline == 3
        assert calls[baseline:] == ["set_associative"] * 3
        # the saved-report pill shows DONE for all four steps
        pills = " ".join(e.value for e in at.markdown)
        assert "DONE" in pills and "FAILED" not in pills

    def test_repeated_workflow_runs_are_independent(self):
        # Two back-to-back runs with different conflict sizes both succeed
        # and the displayed trace name follows the latest run.
        at = fresh_app()
        at.run()
        set_main_number(at, "Conflict blocks", 2)
        set_main_number(at, "Passes", 1)
        click_button(at, "Run automated workflow")
        at.run()
        assert not at.exception and not has_error(at)
        set_main_number(at, "Conflict blocks", 4)
        click_button(at, "Run automated workflow")
        at.run()
        assert not at.exception and not has_error(at)
        pills = " ".join(e.value for e in at.markdown)
        assert "conflict-4b-set0-p1" in pills


@pytest.mark.skipif(not ENGINE.exists(), reason=ENGINE_SKIP)
class TestSampleSequences:
    def test_valid_sample_load_replaces_trace(self):
        at = fresh_app()
        at.run()
        at.radio[0].set_value("Sample file")
        at.run()
        for box in at.selectbox:
            if box.label == "Sample trace":
                box.set_value("e3-lru-vs-fifo.json")
        click_button(at, "Load sample")
        at.run()
        assert not at.exception and not has_error(at)

    def test_malformed_sample_shows_error_card_then_recovers(self):
        bad = ts.ROOT / "traces" / "zz-audit2-malformed.json"
        bad.write_text('{"name": "broken", "addresses": "not-a-list"}',
                       encoding="utf-8")
        try:
            at = fresh_app()
            at.run()
            at.radio[0].set_value("Sample file")
            at.run()
            for box in at.selectbox:
                if box.label == "Sample trace":
                    box.set_value("zz-audit2-malformed.json")
            click_button(at, "Load sample")
            at.run()
            assert not at.exception, [e.value for e in at.exception]
            assert has_error(at)
            assert any("not a valid trace file" in e.value
                       for e in at.error)
        finally:
            bad.unlink(missing_ok=True)
