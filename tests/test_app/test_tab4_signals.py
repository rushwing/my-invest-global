"""TC-019-01..13 — Tab 4 信号仪表盘: Gauge, chip colors, triggers, mini strip, CTA."""

from __future__ import annotations

from datetime import date, timedelta
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

# Skip entire file if module under test is not yet implemented.
pytest.importorskip("app.components.tab4_signals")

import app.components.tab4_signals as tab4  # noqa: E402


# ── TC-019-01..02 ─────────────────────────────────────────────────────────────


class TestElasticTargets:
    """TC-019-01/02: ELASTIC_TARGETS["green"]=38, ["red"]=20."""

    def test_green_target_38(self):
        assert tab4.ELASTIC_TARGETS["green"] == 38

    def test_yellow_target_33(self):
        assert tab4.ELASTIC_TARGETS["yellow"] == 33

    def test_red_target_20(self):
        assert tab4.ELASTIC_TARGETS["red"] == 20

    def test_all_keys_lowercase(self):
        for key in tab4.ELASTIC_TARGETS:
            assert key == key.lower()


# ── TC-019-03 ─────────────────────────────────────────────────────────────────


class TestGaugeColorNeutral:
    """TC-019-03: deviation=6% → gauge_color=#F5A623 (neutral)."""

    def test_6pct_deviation_is_yellow(self):
        assert tab4.gauge_color(6) == "#F5A623"

    def test_minus_6pct_deviation_is_yellow(self):
        assert tab4.gauge_color(-6) == "#F5A623"

    def test_within_5pct_is_green(self):
        assert tab4.gauge_color(3) == "#00C47A"
        assert tab4.gauge_color(0) == "#00C47A"

    def test_trigger_status_watch_when_deviation_6pct(self):
        pytest.importorskip("app.data_loader")
        from app.data_loader import compute_trigger_status
        # elastic 39% vs yellow target 33% → deviation = 6% → watch
        holdings = pd.DataFrame([
            {"category": "弹性股", "market_value": 39.0},
            {"category": "白马股", "market_value": 61.0},
        ])
        triggers = compute_trigger_status(holdings, "yellow")
        assert any(triggers["status"] == "watch"), \
            "expected at least one 'watch' trigger when elastic deviation is 6%"
        assert not any(triggers["status"] == "triggered"), \
            "no trigger should fire at 6% deviation"


# ── TC-019-04 ─────────────────────────────────────────────────────────────────


class TestGaugeColorTriggered:
    """TC-019-04: deviation=11% → gauge_color=#E84040 (bear); triggers show red background."""

    def test_11pct_deviation_is_red(self):
        assert tab4.gauge_color(11) == "#E84040"

    def test_minus_15pct_deviation_is_red(self):
        assert tab4.gauge_color(-15) == "#E84040"

    def test_trigger_status_triggered_when_deviation_11pct(self):
        pytest.importorskip("app.data_loader")
        from app.data_loader import compute_trigger_status
        # elastic 44% vs yellow target 33% → deviation = 11% → triggered
        holdings = pd.DataFrame([
            {"category": "弹性股", "market_value": 44.0},
            {"category": "白马股", "market_value": 56.0},
        ])
        triggers = compute_trigger_status(holdings, "yellow")
        assert any(triggers["status"] == "triggered"), \
            "expected at least one 'triggered' when elastic deviation is 11%"

    def test_triggered_row_style_contains_red_background(self):
        # The status→style mapping must give red background for "triggered"
        style = tab4.trigger_row_style("triggered")
        assert "#E84040" in style or "red" in style.lower() or "bear" in style.lower(), \
            f"'triggered' row style should include red background, got: {style}"

    def test_normal_row_style_not_red(self):
        style = tab4.trigger_row_style("normal")
        assert "#E84040" not in style


# ── TC-019-05..06 ─────────────────────────────────────────────────────────────


class TestChipColor:
    """TC-019-05/06: chip_color thresholds."""

    def test_score_72_is_green(self):
        assert tab4.chip_color(72) == "#00C47A"

    def test_score_70_is_green(self):
        assert tab4.chip_color(70) == "#00C47A"

    def test_score_48_is_red(self):
        assert tab4.chip_color(48) == "#E84040"

    def test_score_50_is_yellow(self):
        assert tab4.chip_color(50) == "#F5A623"

    def test_score_69_is_yellow(self):
        assert tab4.chip_color(69) == "#F5A623"

    def test_score_0_is_red(self):
        assert tab4.chip_color(0) == "#E84040"

    def test_score_100_is_green(self):
        assert tab4.chip_color(100) == "#00C47A"


# ── TC-019-07 ─────────────────────────────────────────────────────────────────


class TestOwnedSymbol:
    """TC-019-07: owned=True → ◉ prefix; warn=True → ⚠ symbol."""

    def test_owned_chip_contains_circle(self):
        html = tab4.render_scarcity_chip_html(
            code="300308", name="中际旭创", rank=1, score=84,
            owned=True, warn=False, flow_values=[],
        )
        assert "◉" in html

    def test_warn_chip_contains_warning(self):
        html = tab4.render_scarcity_chip_html(
            code="688041", name="某股票", rank=2, score=60,
            owned=False, warn=True, flow_values=[],
        )
        assert "⚠" in html

    def test_non_owned_no_circle(self):
        html = tab4.render_scarcity_chip_html(
            code="000001", name="平安银行", rank=3, score=55,
            owned=False, warn=False, flow_values=[],
        )
        assert "◉" not in html


# ── TC-019-08 ─────────────────────────────────────────────────────────────────


class TestMacroOverride:
    """TC-019-08: set_macro_state_override(MacroState.RED); json writes {"state":"red"} only."""

    def test_override_writes_state_red(self, tmp_path):
        import json
        from engine.macro_gate import MacroState

        cache_file = tmp_path / "macro_state.json"
        with patch("engine.macro_gate._CACHE_FILE", cache_file):
            from engine.macro_gate import set_macro_state_override
            set_macro_state_override(MacroState.RED)

        data = json.loads(cache_file.read_text())
        assert data["state"] == "red"

    def test_override_does_not_write_override_flag(self, tmp_path):
        import json
        from engine.macro_gate import MacroState

        cache_file = tmp_path / "macro_state.json"
        with patch("engine.macro_gate._CACHE_FILE", cache_file):
            from engine.macro_gate import set_macro_state_override
            set_macro_state_override(MacroState.RED)

        data = json.loads(cache_file.read_text())
        # Implementation writes {"state": "<value>"} only, not override flag
        assert list(data.keys()) == ["state"], \
            f"expected only 'state' key, got {list(data.keys())}"

    def test_macro_state_from_lowercase_string(self):
        from engine.macro_gate import MacroState
        assert MacroState("red") == MacroState.RED
        assert MacroState("green") == MacroState.GREEN
        assert MacroState("yellow") == MacroState.YELLOW


# ── TC-019-09..10 ─────────────────────────────────────────────────────────────


class TestMiniFlowStrip:
    """TC-019-09/10: strip cell colors follow main_net_inflow sign; empty=gray."""

    def test_colors_match_sign(self):
        cells = tab4.build_flow_strip_cells([1.0, -2.0, 3.0, -1.0, 5.0])
        assert len(cells) == 5
        expected_pos = [True, False, True, False, True]
        for cell, is_pos in zip(cells, expected_pos):
            if is_pos:
                assert "pos" in cell or "#00C47A" in cell, \
                    f"positive flow cell should be green: {cell}"
            else:
                assert "neg" in cell or "#E84040" in cell, \
                    f"negative flow cell should be red: {cell}"

    def test_empty_flow_returns_5_gray_cells(self):
        cells = tab4.build_flow_strip_cells([])
        assert len(cells) == 5
        for cell in cells:
            is_gray = any(kw in cell for kw in ("#888", "#9AA0AC", "gray", "empty", "neutral"))
            assert is_gray, f"empty flow cell should be gray: {cell}"

    def test_partial_flow_padded_to_5(self):
        cells = tab4.build_flow_strip_cells([1.0, -1.0])
        assert len(cells) == 5


# ── TC-019-11 ─────────────────────────────────────────────────────────────────


class TestCTAButton:
    """TC-019-11: handle_enter_cta sets session_state["tab3_code"] + calls st.rerun."""

    def test_sets_tab3_code(self):
        session_state = {}
        with patch("streamlit.session_state", session_state), \
             patch("streamlit.rerun"):
            tab4.handle_enter_cta("300308")
        assert session_state.get("tab3_code") == "300308"

    def test_calls_st_rerun(self):
        with patch("streamlit.session_state", {}), \
             patch("streamlit.rerun") as mock_rerun:
            tab4.handle_enter_cta("688143")
        mock_rerun.assert_called_once()


# ── TC-019-12 ─────────────────────────────────────────────────────────────────


class TestFundFlowBarChart:
    """TC-019-12: go.Bar chart from fund_flow df; no exception; x=date sequence."""

    def _fund_flow_df(self, n: int = 20):
        today = date.today()
        rows = [
            {"trade_date": (today - timedelta(days=i)).isoformat(),
             "main_net_inflow": float(i % 5 - 2)}
            for i in range(n)
        ]
        return pd.DataFrame(rows)

    def test_returns_plotly_figure(self):
        import plotly.graph_objects as go
        fig = tab4.build_fund_flow_bar(self._fund_flow_df())
        assert isinstance(fig, go.Figure)

    def test_has_bar_trace(self):
        fig = tab4.build_fund_flow_bar(self._fund_flow_df())
        bar_traces = [t for t in fig.data if t.type == "bar"]
        assert len(bar_traces) >= 1

    def test_x_axis_is_date_sequence(self):
        df = self._fund_flow_df()
        fig = tab4.build_fund_flow_bar(df)
        bar_trace = next(t for t in fig.data if t.type == "bar")
        assert len(bar_trace.x) == len(df["trade_date"].unique())

    def test_empty_df_no_exception(self):
        import plotly.graph_objects as go
        fig = tab4.build_fund_flow_bar(
            pd.DataFrame(columns=["trade_date", "main_net_inflow"])
        )
        assert isinstance(fig, go.Figure)


# ── TC-019-13 ─────────────────────────────────────────────────────────────────


class TestMarketBreadthScatter:
    """TC-019-13: go.Scatter chart; y-axis values in [0,1]; no exception on empty df."""

    def _breadth_df(self, n: int = 20):
        today = date.today()
        return pd.DataFrame([
            {"date": (today - timedelta(days=i)).isoformat(),
             "up_ratio": 0.3 + (i % 5) * 0.1}
            for i in range(n)
        ])

    def test_returns_plotly_figure(self):
        import plotly.graph_objects as go
        fig = tab4.build_breadth_scatter(self._breadth_df())
        assert isinstance(fig, go.Figure)

    def test_y_values_in_0_1(self):
        fig = tab4.build_breadth_scatter(self._breadth_df())
        scatter = next(t for t in fig.data if t.type == "scatter")
        for v in scatter.y:
            assert 0 <= v <= 1, f"up_ratio {v} out of [0,1]"

    def test_has_hline_at_0_5(self):
        fig = tab4.build_breadth_scatter(self._breadth_df())
        hlines = [s for s in fig.layout.shapes if abs(s.y0 - 0.5) < 0.01]
        assert len(hlines) >= 1, "expected a hline at y=0.5"

    def test_empty_df_no_exception(self):
        import plotly.graph_objects as go
        fig = tab4.build_breadth_scatter(
            pd.DataFrame(columns=["date", "up_ratio"])
        )
        assert isinstance(fig, go.Figure)
