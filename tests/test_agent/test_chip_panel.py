"""TC-039-01..04 — Phase 11 chip_panel: Streamlit rendering + OCR guard."""

from __future__ import annotations

from unittest.mock import MagicMock, call, patch

import pytest

chip_fetcher = pytest.importorskip("engine.agent.chip_fetcher")
chip_analysis_mod = pytest.importorskip("engine.agent.chip_analysis")
chip_panel_mod = pytest.importorskip("app.pages.chip_panel")

ChipBar = chip_fetcher.ChipBar
ChipSummary = chip_fetcher.ChipSummary
ChipAnalysis = chip_analysis_mod.ChipAnalysis
ChipLockLevel = chip_analysis_mod.ChipLockLevel

render_chip_panel = chip_panel_mod.render_chip_panel
build_chip_chart = chip_panel_mod.build_chip_chart
chip_panel_page = chip_panel_mod.chip_panel_page

# ── Mock factories ─────────────────────────────────────────────────────────────


def _analysis_above_90() -> ChipAnalysis:
    return ChipAnalysis(
        code="688143", date="2026-05-20", current_price=131.60,
        avg_cost=99.96, profitable_pct=0.9973, concentration=33.92,
        range_70_lower=80.0, range_70_upper=120.0,
        range_90_lower=63.28, range_90_upper=128.24,
        above_90_band=True, below_90_band=False,
        cost_deviation_pct=31.7, chip_spread_90=64.96,
        chip_lock_level=ChipLockLevel.LOW,
        signal_summary="价格突破90%筹码上界，99.7%筹码浮盈，获利兑现压力大",
    )


def _analysis_in_band() -> ChipAnalysis:
    return ChipAnalysis(
        code="000001", date="2026-05-20", current_price=10.5,
        avg_cost=10.0, profitable_pct=0.9973, concentration=45.0,
        range_70_lower=9.0, range_70_upper=13.0,
        range_90_lower=7.0, range_90_upper=15.0,
        above_90_band=False, below_90_band=False,
        cost_deviation_pct=5.0, chip_spread_90=8.0,
        chip_lock_level=ChipLockLevel.MEDIUM,
        signal_summary="价格在90%筹码区间内，均成本偏离5.0%",
    )


def _summary() -> ChipSummary:
    bars = [
        ChipBar(price_lower=60.0, price_upper=70.0, chip_ratio=0.05),
        ChipBar(price_lower=70.0, price_upper=80.0, chip_ratio=0.08),
        ChipBar(price_lower=120.0, price_upper=130.0, chip_ratio=0.12),
        ChipBar(price_lower=130.0, price_upper=140.0, chip_ratio=0.10),
    ]
    return ChipSummary(
        code="688143", date="2026-05-20",
        avg_cost=99.96, profitable_pct=0.9973, concentration=33.92,
        range_70_lower=80.0, range_70_upper=120.0,
        range_90_lower=63.28, range_90_upper=128.24,
        bars=bars,
    )


# ── TC-039-01 ─────────────────────────────────────────────────────────────────


class TestRenderChipPanelSignalCard:
    """TC-039-01: above_90_band=True → st.error called exactly once, no exception."""

    def test_no_exception_raised(self):
        with patch("streamlit.error"), patch("streamlit.metric"), \
             patch("streamlit.info"), patch("streamlit.plotly_chart"), \
             patch("streamlit.columns", return_value=[MagicMock()] * 4):
            render_chip_panel("688143", 131.60, _analysis_above_90(), _summary())

    def test_st_error_called_once_when_above_band(self):
        with patch("streamlit.error") as mock_err, \
             patch("streamlit.metric"), patch("streamlit.info"), \
             patch("streamlit.plotly_chart"), \
             patch("streamlit.columns", return_value=[MagicMock()] * 4):
            render_chip_panel("688143", 131.60, _analysis_above_90(), _summary())
        assert mock_err.call_count == 1

    def test_st_warning_not_called_when_above_band(self):
        with patch("streamlit.error"), \
             patch("streamlit.warning") as mock_warn, \
             patch("streamlit.metric"), patch("streamlit.info"), \
             patch("streamlit.plotly_chart"), \
             patch("streamlit.columns", return_value=[MagicMock()] * 4):
            render_chip_panel("688143", 131.60, _analysis_above_90(), _summary())
        assert mock_warn.call_count == 0


# ── TC-039-02 ─────────────────────────────────────────────────────────────────


class TestBuildChipChart:
    """TC-039-02: build_chip_chart() returns go.Figure with correct colors and shapes.

    build_chip_chart is a pure function — no st.* calls, no mock needed.
    """

    def test_returns_plotly_figure(self):
        import plotly.graph_objects as go
        fig = build_chip_chart(_summary(), current_price=131.60)
        assert isinstance(fig, go.Figure)

    def test_color_below_current_price_is_green(self):
        fig = build_chip_chart(_summary(), current_price=131.60)
        colors = fig.data[0].marker.color
        # bars with midpoint < 131.60: (60+70)/2=65, (70+80)/2=75, (120+130)/2=125
        # bars with midpoint >= 131.60: (130+140)/2=135
        for bar, color in zip(_summary().bars, colors):
            mid = (bar.price_lower + bar.price_upper) / 2
            if mid < 131.60:
                assert color == "#00C47A", f"bar midpoint {mid} should be green"
            else:
                assert color == "#E84040", f"bar midpoint {mid} should be red"

    def test_shapes_contain_current_price_label(self):
        fig = build_chip_chart(_summary(), current_price=131.60)
        shape_labels = [
            s.get("label", {}).get("text", "") if isinstance(s, dict)
            else getattr(getattr(s, "label", None), "text", "")
            for s in fig.layout.shapes
        ]
        assert any("现价" in lbl for lbl in shape_labels), \
            f"'现价' not found in shapes: {shape_labels}"

    def test_shapes_contain_avg_cost_label(self):
        fig = build_chip_chart(_summary(), current_price=131.60)
        shape_labels = [
            s.get("label", {}).get("text", "") if isinstance(s, dict)
            else getattr(getattr(s, "label", None), "text", "")
            for s in fig.layout.shapes
        ]
        assert any("均成本" in lbl for lbl in shape_labels), \
            f"'均成本' not found in shapes: {shape_labels}"

    def test_figure_has_dark_background(self):
        fig = build_chip_chart(_summary(), current_price=131.60)
        bg = fig.layout.plot_bgcolor or fig.layout.paper_bgcolor
        assert "#0E1117" in (bg or "").upper() or bg == "#0e1117"


# ── TC-039-03 ─────────────────────────────────────────────────────────────────


class TestChipSummaryCardMetrics:
    """TC-039-03: profitable_pct=0.9973 displays '99.7%' and non-empty delta."""

    def test_profitable_pct_format_in_metric(self):
        captured_calls: list[tuple] = []

        def capture_metric(*args, **kwargs):
            captured_calls.append((args, kwargs))

        with patch("streamlit.metric", side_effect=capture_metric), \
             patch("streamlit.error"), patch("streamlit.info"), \
             patch("streamlit.plotly_chart"), \
             patch("streamlit.columns", return_value=[MagicMock()] * 4):
            render_chip_panel("688143", 131.60, _analysis_above_90(), _summary())

        # Find the metric call whose value contains "99.7%"
        matching = [
            (args, kwargs) for args, kwargs in captured_calls
            if "99.7%" in str(args) + str(kwargs)
        ]
        assert len(matching) >= 1, \
            f"No st.metric call contained '99.7%'. Calls: {captured_calls}"

    def test_delta_nonempty_for_profitable_pct_metric(self):
        """When profitable_pct >= 0.95, delta must be non-empty (warning indicator)."""
        captured_calls: list[tuple] = []

        def capture_metric(*args, **kwargs):
            captured_calls.append((args, kwargs))

        with patch("streamlit.metric", side_effect=capture_metric), \
             patch("streamlit.error"), patch("streamlit.info"), \
             patch("streamlit.plotly_chart"), \
             patch("streamlit.columns", return_value=[MagicMock()] * 4):
            render_chip_panel("688143", 131.60, _analysis_above_90(), _summary())

        profitable_pct_calls = [
            (args, kwargs) for args, kwargs in captured_calls
            if "99.7%" in str(args) + str(kwargs)
        ]
        assert profitable_pct_calls, "No metric call found with '99.7%'"
        args, kwargs = profitable_pct_calls[0]
        delta = kwargs.get("delta") or (args[2] if len(args) > 2 else None)
        assert delta is not None and delta != ""


# ── TC-039-04 ─────────────────────────────────────────────────────────────────


class TestChipPanelPageOCRGuard:
    """TC-039-04: radio=OCR, file_uploader=None, button=False → parse_chip_screenshot not called."""

    def test_parse_not_called_when_no_file_uploaded(self):
        with patch("streamlit.title"), \
             patch("streamlit.selectbox", return_value="688143"), \
             patch("streamlit.number_input", return_value=131.60), \
             patch("streamlit.radio", return_value="截图解析（OCR）"), \
             patch("streamlit.file_uploader", return_value=None), \
             patch("streamlit.button", return_value=False), \
             patch("streamlit.warning"), \
             patch(
                 "app.pages.chip_panel.parse_chip_screenshot",
                 side_effect=AssertionError("parse_chip_screenshot should NOT be called"),
             ):
            chip_panel_page()  # should complete without triggering parse
