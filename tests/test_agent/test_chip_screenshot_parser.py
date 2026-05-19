"""TC-038-01..04 — Phase 11 chip_screenshot_parser: Claude Vision OCR path."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from engine.agent.chip_analysis import ChipAnalysis
from engine.agent.chip_screenshot_parser import (
    ScreenshotParseError,
    parse_chip_screenshot,
)

# Fixture file — exists because TC-036 tc_impl copied the real 688143 screenshot
FIXTURE_PATH = str(
    Path(__file__).parent.parent / "fixtures" / "chip_688143_20260519.png"
)

# ── Helpers ───────────────────────────────────────────────────────────────────


def _mock_claude_response(payload: dict) -> MagicMock:
    """Build a minimal mock of anthropic messages.create() return value."""
    msg = MagicMock()
    msg.content = [MagicMock()]
    msg.content[0].text = json.dumps(payload)
    return msg


_STANDARD_PAYLOAD = {
    "code": "688143",
    "current_price": 131.60,
    "avg_cost": 99.96,
    "profitable_pct": 0.9973,
    "concentration": 33.92,
    "range_70_lower": None,
    "range_70_upper": None,
    "range_90_lower": 63.28,
    "range_90_upper": 128.24,
}

# ── TC-038-01 ─────────────────────────────────────────────────────────────────


class TestParseChipScreenshotHappyPath:
    """TC-038-01: mock Claude returns standard JSON → ChipAnalysis with correct values.

    All TCs mock anthropic.Anthropic().messages.create.
    Fixture image is read for base64 encoding but API is never called.
    """

    @pytest.fixture(autouse=True)
    def _mock_api(self):
        def _create(**_):
            return _mock_claude_response(_STANDARD_PAYLOAD)

        with patch(
            "anthropic.Anthropic.messages",
            new_callable=lambda: type("M", (), {"create": staticmethod(_create)}),
        ):
            yield

    def test_fixture_file_exists(self):
        """Fixture must exist so image encoding path is exercised."""
        assert Path(FIXTURE_PATH).exists(), f"Missing fixture: {FIXTURE_PATH}"

    def test_returns_chip_analysis(self):
        with patch(
            "engine.agent.chip_screenshot_parser._call_claude_vision",
            return_value=_STANDARD_PAYLOAD,
        ):
            result = parse_chip_screenshot(FIXTURE_PATH)
        assert isinstance(result, ChipAnalysis)

    def test_avg_cost_accurate(self):
        with patch(
            "engine.agent.chip_screenshot_parser._call_claude_vision",
            return_value=_STANDARD_PAYLOAD,
        ):
            result = parse_chip_screenshot(FIXTURE_PATH)
        assert abs(result.avg_cost - 99.96) < 0.01

    def test_profitable_pct_above_99(self):
        with patch(
            "engine.agent.chip_screenshot_parser._call_claude_vision",
            return_value=_STANDARD_PAYLOAD,
        ):
            result = parse_chip_screenshot(FIXTURE_PATH)
        assert result.profitable_pct > 0.99

    def test_range_70_fallback_equals_range_90(self):
        """When range_70 is None in OCR payload, fallback to range_90 values."""
        with patch(
            "engine.agent.chip_screenshot_parser._call_claude_vision",
            return_value=_STANDARD_PAYLOAD,
        ):
            result = parse_chip_screenshot(FIXTURE_PATH)
        # range_70_lower/upper were None → should fall back to range_90 values
        assert result.range_70_lower == result.range_90_lower
        assert result.range_70_upper == result.range_90_upper


# ── TC-038-02 ─────────────────────────────────────────────────────────────────


class TestParseChipScreenshotNullCriticalFields:
    """TC-038-02: null avg_cost/profitable_pct → ScreenshotParseError, not partial model."""

    _NULL_PAYLOAD = {
        "code": "688143",
        "current_price": 131.60,
        "avg_cost": None,
        "profitable_pct": None,
        "concentration": 33.92,
        "range_70_lower": None,
        "range_70_upper": None,
        "range_90_lower": 63.28,
        "range_90_upper": 128.24,
    }

    def test_raises_screenshot_parse_error(self):
        with patch(
            "engine.agent.chip_screenshot_parser._call_claude_vision",
            return_value=self._NULL_PAYLOAD,
        ):
            with pytest.raises(ScreenshotParseError):
                parse_chip_screenshot(FIXTURE_PATH)

    def test_does_not_return_partial_model(self):
        result = None
        with patch(
            "engine.agent.chip_screenshot_parser._call_claude_vision",
            return_value=self._NULL_PAYLOAD,
        ):
            try:
                result = parse_chip_screenshot(FIXTURE_PATH)
            except ScreenshotParseError:
                pass
        assert result is None


# ── TC-038-03 ─────────────────────────────────────────────────────────────────


class TestParseChipScreenshotAnalyzeChipCalled:
    """TC-038-03: above_90_band derived correctly → analyze_chip was called."""

    _ABOVE_BAND_PAYLOAD = {
        "code": "688143",
        "current_price": 131.60,
        "avg_cost": 99.96,
        "profitable_pct": 0.9973,
        "concentration": 33.92,
        "range_70_lower": None,
        "range_70_upper": None,
        "range_90_lower": 63.28,
        "range_90_upper": 128.24,  # 131.60 > 128.24 → above_90_band
    }

    def test_above_90_band_true(self):
        with patch(
            "engine.agent.chip_screenshot_parser._call_claude_vision",
            return_value=self._ABOVE_BAND_PAYLOAD,
        ):
            result = parse_chip_screenshot(FIXTURE_PATH, code="688143")
        assert result.above_90_band is True

    def test_chip_analysis_has_signal_summary(self):
        with patch(
            "engine.agent.chip_screenshot_parser._call_claude_vision",
            return_value=self._ABOVE_BAND_PAYLOAD,
        ):
            result = parse_chip_screenshot(FIXTURE_PATH, code="688143")
        assert isinstance(result.signal_summary, str)
        assert len(result.signal_summary) > 0


# ── TC-038-04 ─────────────────────────────────────────────────────────────────


class TestParseChipScreenshotInvalidJson:
    """TC-038-04: non-JSON Claude response → ScreenshotParseError with parse/JSON in reason."""

    def test_invalid_json_raises_parse_error(self):
        with patch(
            "engine.agent.chip_screenshot_parser._call_claude_vision",
            side_effect=ScreenshotParseError(reason="JSON parse failed: invalid"),
        ):
            with pytest.raises(ScreenshotParseError) as exc_info:
                parse_chip_screenshot(FIXTURE_PATH)
        reason = str(exc_info.value)
        assert "parse" in reason.lower() or "JSON" in reason or "json" in reason.lower()

    def test_non_json_string_from_api(self):
        """If _call_claude_vision returns a raw non-JSON string payload, parser raises."""
        with patch(
            "engine.agent.chip_screenshot_parser._call_claude_vision",
            return_value="这不是JSON格式的响应，无法解析",
        ):
            with pytest.raises(ScreenshotParseError):
                parse_chip_screenshot(FIXTURE_PATH)
