"""TC-019-01..13 — Tab 4 信号仪表盘: Gauge targets, chip colors, mini strip, CTA."""

from __future__ import annotations

from datetime import date, timedelta
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest


# ── TC-019-01..02 ─────────────────────────────────────────────────────────────


class TestElasticTargets:
    """TC-019-01/02: ELASTIC_TARGETS[green]=38, ELASTIC_TARGETS[red]=20."""

    def test_green_target_38(self):
        from app.components.tab4_signals import ELASTIC_TARGETS
        assert ELASTIC_TARGETS["green"] == 38

    def test_yellow_target_33(self):
        from app.components.tab4_signals import ELASTIC_TARGETS
        assert ELASTIC_TARGETS["yellow"] == 33

    def test_red_target_20(self):
        from app.components.tab4_signals import ELASTIC_TARGETS
        assert ELASTIC_TARGETS["red"] == 20

    def test_keys_are_lowercase(self):
        from app.components.tab4_signals import ELASTIC_TARGETS
        for key in ELASTIC_TARGETS:
            assert key == key.lower(), f"key '{key}' is not lowercase"


# ── TC-019-03..04 ─────────────────────────────────────────────────────────────


class TestGaugeColor:
    """TC-019-03/04: gauge_color(deviation) returns correct color band."""

    def test_within_5pct_is_green(self):
        from app.components.tab4_signals import gauge_color
        assert gauge_color(3) == "#00C47A"
        assert gauge_color(-4) == "#00C47A"
        assert gauge_color(0) == "#00C47A"

    def test_5_to_10pct_is_yellow(self):
        from app.components.tab4_signals import gauge_color
        assert gauge_color(6) == "#F5A623"
        assert gauge_color(-7) == "#F5A623"
        assert gauge_color(10) == "#F5A623"

    def test_over_10pct_is_red(self):
        from app.components.tab4_signals import gauge_color
        assert gauge_color(11) == "#E84040"
        assert gauge_color(-15) == "#E84040"


# ── TC-019-05..06 ─────────────────────────────────────────────────────────────


class TestChipColor:
    """TC-019-05/06: chip_color(score) returns correct color."""

    def test_score_72_is_green(self):
        from app.components.tab4_signals import chip_color
        assert chip_color(72) == "#00C47A"

    def test_score_70_is_green(self):
        from app.components.tab4_signals import chip_color
        assert chip_color(70) == "#00C47A"

    def test_score_48_is_red(self):
        from app.components.tab4_signals import chip_color
        assert chip_color(48) == "#E84040"

    def test_score_50_is_yellow(self):
        from app.components.tab4_signals import chip_color
        assert chip_color(50) == "#F5A623"

    def test_score_65_is_yellow(self):
        from app.components.tab4_signals import chip_color
        assert chip_color(65) == "#F5A623"

    def test_score_0_is_red(self):
        from app.components.tab4_signals import chip_color
        assert chip_color(0) == "#E84040"

    def test_score_100_is_green(self):
        from app.components.tab4_signals import chip_color
        assert chip_color(100) == "#00C47A"


# ── TC-019-07 ─────────────────────────────────────────────────────────────────


class TestOwnedSymbol:
    """TC-019-07: owned=True stock displays ◉ prefix in chip HTML."""

    def test_owned_chip_contains_circle_symbol(self):
        from app.components.tab4_signals import render_scarcity_chip_html
        html = render_scarcity_chip_html(
            code="300308", name="中际旭创", rank=1, score=84,
            owned=True, warn=False, flow_values=[],
        )
        assert "◉" in html, "owned chip should contain ◉ symbol"

    def test_warn_chip_contains_warning_symbol(self):
        from app.components.tab4_signals import render_scarcity_chip_html
        html = render_scarcity_chip_html(
            code="688041", name="某股票", rank=2, score=60,
            owned=False, warn=True, flow_values=[],
        )
        assert "⚠" in html, "warn chip should contain ⚠ symbol"

    def test_non_owned_no_circle_symbol(self):
        from app.components.tab4_signals import render_scarcity_chip_html
        html = render_scarcity_chip_html(
            code="000001", name="平安银行", rank=3, score=55,
            owned=False, warn=False, flow_values=[],
        )
        assert "◉" not in html


# ── TC-019-08 ─────────────────────────────────────────────────────────────────


class TestMacroOverride:
    """TC-019-08: set_macro_state_override(MacroState.RED) called; json writes {"state":"red"}."""

    def test_override_called_with_macro_state_enum(self, tmp_path):
        from engine.macro_gate import MacroState
        from unittest.mock import patch as p
        import json

        cache_file = tmp_path / "macro_state.json"
        with p("engine.macro_gate._CACHE_FILE", cache_file):
            from engine.macro_gate import set_macro_state_override
            set_macro_state_override(MacroState.RED)

        data = json.loads(cache_file.read_text())
        assert data["state"] == "red"

    def test_override_writes_only_state_field(self, tmp_path):
        from engine.macro_gate import MacroState
        import json
        cache_file = tmp_path / "macro_state.json"
        with patch("engine.macro_gate._CACHE_FILE", cache_file):
            from engine.macro_gate import set_macro_state_override
            set_macro_state_override(MacroState.RED)
        data = json.loads(cache_file.read_text())
        # Implementation only writes {"state": "<value>"}, not override flag
        assert "state" in data
        assert data["state"] == "red"

    def test_macro_state_from_string(self):
        from engine.macro_gate import MacroState
        assert MacroState("red") == MacroState.RED
        assert MacroState("green") == MacroState.GREEN


# ── TC-019-09..10 ─────────────────────────────────────────────────────────────


class TestMiniFlowStrip:
    """TC-019-09/10: mini strip cell colors match main_net_inflow sign."""

    def test_strip_colors_match_sign(self):
        from app.components.tab4_signals import build_flow_strip_cells
        flow = [1.0, -2.0, 3.0, -1.0, 5.0]
        cells = build_flow_strip_cells(flow)
        expected = ["pos", "neg", "pos", "neg", "pos"]
        for cell, exp in zip(cells, expected):
            assert exp in cell, f"expected '{exp}' class in cell HTML, got: {cell}"

    def test_empty_flow_returns_5_gray_cells(self):
        from app.components.tab4_signals import build_flow_strip_cells
        cells = build_flow_strip_cells([])
        assert len(cells) == 5
        for cell in cells:
            assert "gray" in cell or "#888" in cell or "neutral" in cell or "empty" in cell, \
                f"empty flow should produce gray cells, got: {cell}"

    def test_strip_returns_5_cells(self):
        from app.components.tab4_signals import build_flow_strip_cells
        cells = build_flow_strip_cells([1.0, -1.0, 0.5])
        assert len(cells) == 5


# ── TC-019-11 ─────────────────────────────────────────────────────────────────


class TestCTAButton:
    """TC-019-11: clicking 进入 → sets session_state["tab3_code"]."""

    def test_cta_sets_tab3_code(self):
        from app.components.tab4_signals import handle_enter_cta
        session_state = {}
        with patch("streamlit.session_state", session_state), \
             patch("streamlit.rerun"):
            handle_enter_cta("300308")
        assert session_state.get("tab3_code") == "300308"

    def test_cta_calls_st_rerun(self):
        from app.components.tab4_signals import handle_enter_cta
        with patch("streamlit.session_state", {}), \
             patch("streamlit.rerun") as mock_rerun:
            handle_enter_cta("688143")
        mock_rerun.assert_called_once()


# ── TC-019-12 ─────────────────────────────────────────────────────────────────


class TestDualHeaderCharts:
    """TC-019-12: fund_flow bar chart builds without exception; x-axis is date sequence."""

    def _fund_flow_df(self):
        today = date.today()
        rows = []
        for i in range(20):
            d = today - timedelta(days=i)
            rows.append({"trade_date": d.isoformat(), "main_net_inflow": float(i % 5 - 2)})
        return pd.DataFrame(rows)

    def test_bar_chart_no_exception(self):
        import plotly.graph_objects as go
        from app.components.tab4_signals import build_fund_flow_bar
        fig = build_fund_flow_bar(self._fund_flow_df())
        assert isinstance(fig, go.Figure)

    def test_bar_chart_has_data(self):
        from app.components.tab4_signals import build_fund_flow_bar
        fig = build_fund_flow_bar(self._fund_flow_df())
        assert len(fig.data) >= 1

    def test_bar_chart_empty_df_no_exception(self):
        import plotly.graph_objects as go
        from app.components.tab4_signals import build_fund_flow_bar
        fig = build_fund_flow_bar(pd.DataFrame(columns=["trade_date", "main_net_inflow"]))
        assert isinstance(fig, go.Figure)


# ── TC-019-13 ─────────────────────────────────────────────────────────────────


class TestMarketBreadthChart:
    """TC-019-13: up_ratio scatter chart builds without exception; y-axis values in [0,1]."""

    def _breadth_df(self):
        today = date.today()
        rows = []
        for i in range(20):
            d = today - timedelta(days=i)
            rows.append({"date": d.isoformat(), "up_ratio": 0.3 + (i % 5) * 0.1})
        return pd.DataFrame(rows)

    def test_scatter_no_exception(self):
        import plotly.graph_objects as go
        from app.components.tab4_signals import build_breadth_scatter
        fig = build_breadth_scatter(self._breadth_df())
        assert isinstance(fig, go.Figure)

    def test_scatter_y_values_in_range(self):
        from app.components.tab4_signals import build_breadth_scatter
        df = self._breadth_df()
        fig = build_breadth_scatter(df)
        y_vals = list(fig.data[0].y)
        for v in y_vals:
            assert 0 <= v <= 1, f"up_ratio {v} out of [0,1]"

    def test_scatter_empty_df_no_exception(self):
        import plotly.graph_objects as go
        from app.components.tab4_signals import build_breadth_scatter
        fig = build_breadth_scatter(pd.DataFrame(columns=["date", "up_ratio"]))
        assert isinstance(fig, go.Figure)
