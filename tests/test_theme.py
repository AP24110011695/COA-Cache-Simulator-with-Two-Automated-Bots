"""Dark mode (post-delivery): theme palette, CSS bundles, and the
presentation-only separation between theme and simulation data.

The light palette values are asserted verbatim — they are the delivered
appearance and must not drift. Dark values are verified with computed
WCAG contrast ratios from the 2026-10-27 dark-mode audit.
"""

import json

import pytest

import test_smoke as ts

ENGINE = ts.ROOT / "build" / "cache_sim.exe"
ENGINE_SKIP = ts.ENGINE_SKIP
from ui import tokens


def _luminance(color):
    color = color.lstrip("#")
    r, g, b = (int(color[i:i + 2], 16) / 255 for i in (0, 2, 4))
    def channel(v):
        return v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4
    r, g, b = channel(r), channel(g), channel(b)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _contrast(fg, bg):
    l1, l2 = sorted([_luminance(fg), _luminance(bg)], reverse=True)
    return (l1 + 0.05) / (l2 + 0.05)


class TestTokenPalette:
    def test_light_tokens_unchanged(self):
        # Regression: Light is the delivered appearance — these must not drift.
        light = tokens.THEMES["light"]
        assert light["BG"] == "#FFFFFF"
        assert light["BG_SUBTLE"] == "#F5F7FA"
        assert light["BORDER"] == "#D9DEE4"
        assert light["TEXT"] == "#1F2933"
        assert light["TEXT_SECONDARY"] == "#52606D"
        assert light["ACCENT"] == "#1F5FA8"
        assert light["ACCENT_SOFT"] == "#E8F0F8"
        assert light["SUCCESS"] == "#2E7D32"
        assert light["DANGER"] == "#C62828"
        assert light["WARNING"] == "#B26A00"

    def test_dark_tokens_complete(self):
        # Every light token must have a dark counterpart.
        assert set(tokens.THEMES["dark"]) == set(tokens.THEMES["light"])

    def test_get_tokens_defaults_to_light(self):
        assert tokens.get_tokens()[ "BG"] == "#FFFFFF"
        assert tokens.get_tokens(None)["BG"] == "#FFFFFF"

    def test_get_tokens_unknown_falls_back_to_light(self):
        assert tokens.get_tokens("sepia")["BG"] == "#FFFFFF"

    def test_dark_text_contrast_meets_wcag(self):
        dark = tokens.THEMES["dark"]
        assert _contrast(dark["TEXT"], dark["BG"]) >= 4.5
        assert _contrast(dark["TEXT"], dark["BG_SUBTLE"]) >= 4.5
        assert _contrast(dark["TEXT_SECONDARY"], dark["BG"]) >= 4.5
        assert _contrast(dark["TEXT_SECONDARY"], dark["BG_SUBTLE"]) >= 4.5
        assert _contrast(dark["ACCENT"], dark["BG"]) >= 4.5

    def test_dark_semantic_colors_meet_wcag(self):
        dark = tokens.THEMES["dark"]
        assert _contrast(dark["SUCCESS"], dark["BG_SUBTLE"]) >= 4.5
        assert _contrast(dark["DANGER"], dark["BG_SUBTLE"]) >= 4.5
        assert _contrast(dark["WARNING"], dark["BG_SUBTLE"]) >= 4.5

    def test_light_text_contrast_regression(self):
        light = tokens.THEMES["light"]
        assert _contrast(light["TEXT"], light["BG"]) >= 4.5
        assert _contrast(light["TEXT_SECONDARY"], light["BG"]) >= 4.5

    def test_dark_border_meets_ui_contrast(self):
        # WCAG 1.4.11 non-text contrast: borders need >= 3:1.
        dark = tokens.THEMES["dark"]
        assert _contrast(dark["BORDER"], dark["BG"]) >= 3.0
        assert _contrast(dark["BORDER"], dark["BG_SUBTLE"]) >= 3.0


class TestCssBundles:
    def test_light_bundle_unchanged(self):
        import ui.components as components
        css = components.inject_styles("light")
        assert "#16181D" not in css
        assert "#F5F7FA" in css

    def test_dark_bundle_present(self):
        import ui.components as components
        css = components.inject_styles("dark")
        assert "#16181D" in css
        assert 'data-testid="stSidebar"' in css
        assert 'data-testid="stMetricValue"' in css

    def test_light_and_dark_bundles_differ(self):
        import ui.components as components
        assert components.inject_styles("light") != \
            components.inject_styles("dark")


class TestSceneTheme:
    def test_build_html_embeds_theme(self):
        from ui import cache_scene
        from tests.test_cache_scene import TestPayloadBuilder
        envelope = TestPayloadBuilder.ENVELOPE
        light = cache_scene.build_html(envelope, theme="light")["html"]
        dark = cache_scene.build_html(envelope, theme="dark")["html"]
        assert '"theme": "light"' in light
        assert '"theme": "dark"' in dark
        # the dark bundle appends scene_dark.css (dark variable overrides);
        # the shared scene_app.js palette map is inert data in both themes
        assert "--cm-accent: #4F8DE8" in dark
        assert "--cm-accent: #4F8DE8" not in light

    def test_theme_does_not_change_simulation_fields(self):
        from ui import cache_scene
        from tests.test_cache_scene import TestPayloadBuilder
        envelope = TestPayloadBuilder.ENVELOPE
        light = json.loads(cache_scene.build_html(
            envelope, theme="light")["html"].split(
            "window.CACHE_PAYLOAD = ")[1].split(";</script>")[0])
        dark = json.loads(cache_scene.build_html(
            envelope, theme="dark")["html"].split(
            "window.CACHE_PAYLOAD = ")[1].split(";</script>")[0])
        for field in ("events", "snapshots", "geometry", "summary", "memory"):
            assert light[field] == dark[field], field
        assert light["theme"] == "light" and dark["theme"] == "dark"

    def test_deterministic_per_envelope_and_theme(self):
        from ui import cache_scene
        from tests.test_cache_scene import TestPayloadBuilder
        envelope = TestPayloadBuilder.ENVELOPE
        assert cache_scene.build_html(envelope, theme="dark")["html"] == \
            cache_scene.build_html(envelope, theme="dark")["html"]


# --- Integration: identical simulation results in both themes ----------------


@pytest.mark.skipif(not ENGINE.exists(), reason=ENGINE_SKIP)
class TestThemeDoesNotAffectSimulation:
    def test_e3_identical_in_both_themes(self):
        from bots import engine_client
        from ui import cache_scene
        config = dict(ts.CONFIG_SET_ASSOCIATIVE, policy="LRU")
        trace = {"name": "e3", "addresses": [0, 4, 0, 8, 4]}
        job = {"config": config, "trace": trace,
               "options": {"include_state_after_each": True}}
        envelope = engine_client.run_simulate(job)
        payloads = {}
        for theme in ("light", "dark"):
            built = cache_scene.build_html(envelope, theme)
            assert built["ok"] is True
            match = built["html"].split("window.CACHE_PAYLOAD = ")[1]
            payloads[theme] = json.loads(match.split(";</script>")[0])
        for field in ("events", "snapshots", "geometry", "summary", "memory"):
            assert payloads["light"][field] == payloads["dark"][field], field
        assert payloads["light"]["theme"] == "light"
        assert payloads["dark"]["theme"] == "dark"
        # E3 LRU verified numbers unchanged
        assert payloads["light"]["summary"] == {
            "accesses": 5, "hits": 1, "misses": 4, "evictions": 2}
