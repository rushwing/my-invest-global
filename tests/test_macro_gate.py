"""Tests for engine/macro_gate — REQ-001: MacroState enum and manual override.

TC coverage:
  TC-001-01  write/read cycle
  TC-001-02  runtime str compatibility
  TC-001-03  default when cache file missing
  TC-001-04  invalid file content fallback
  TC-001-05  idempotent write
  TC-001-06  CLI invalid args → non-zero exit
  TC-001-07  TARGET_ELASTIC_BY_MACRO_STATE constants
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pandas as pd
import pytest

import engine.macro_gate as _mg
from engine.macro_gate import (
    TARGET_ELASTIC_BY_MACRO_STATE,
    MacroState,
    get_macro_state,
    set_macro_state_override,
)


@pytest.fixture()
def cache_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Redirect macro_gate's _CACHE_FILE to a temp path for full isolation."""
    path = tmp_path / "macro_state.json"
    monkeypatch.setattr(_mg, "_CACHE_FILE", path)
    return path


# ── TC-001-01: normal write/read cycle ────────────────────────────────────────


def test_write_read_green(cache_file: Path) -> None:
    set_macro_state_override(MacroState.GREEN)
    assert get_macro_state() == MacroState.GREEN


def test_write_read_red(cache_file: Path) -> None:
    set_macro_state_override(MacroState.RED)
    assert get_macro_state() == MacroState.RED


def test_write_read_yellow(cache_file: Path) -> None:
    set_macro_state_override(MacroState.YELLOW)
    assert get_macro_state() == MacroState.YELLOW


def test_file_stores_lowercase_json(cache_file: Path) -> None:
    set_macro_state_override(MacroState.GREEN)
    assert json.loads(cache_file.read_text()) == {"state": "green"}


# ── TC-001-02: runtime str compatibility ──────────────────────────────────────


def test_str_equality() -> None:
    assert MacroState.GREEN == "green"
    assert MacroState.YELLOW == "yellow"
    assert MacroState.RED == "red"


def test_value_attribute() -> None:
    assert MacroState.GREEN.value == "green"
    assert MacroState.YELLOW.value == "yellow"
    assert MacroState.RED.value == "red"


def test_isinstance_str() -> None:
    assert isinstance(MacroState.GREEN, str)
    assert isinstance(MacroState.YELLOW, str)
    assert isinstance(MacroState.RED, str)


def test_value_passes_to_check_portfolio_balance() -> None:
    from engine.portfolio import check_portfolio_balance

    df = pd.DataFrame({"category": ["弹性股", "白马股"], "market_value": [30.0, 70.0]})
    result = check_portfolio_balance(df, macro_state=MacroState.GREEN.value)
    assert "rebalance_needed" in result


# ── TC-001-03: default when cache file missing ────────────────────────────────


def test_default_when_file_missing(cache_file: Path) -> None:
    assert not cache_file.exists()
    assert get_macro_state() == MacroState.YELLOW


# ── TC-001-04: invalid file content fallback ─────────────────────────────────


def test_invalid_state_string_falls_back_to_yellow(cache_file: Path) -> None:
    cache_file.write_text(json.dumps({"state": "INVALID"}))
    assert get_macro_state() == MacroState.YELLOW


def test_null_state_falls_back_to_yellow(cache_file: Path) -> None:
    cache_file.write_text(json.dumps({"state": None}))
    assert get_macro_state() == MacroState.YELLOW


# ── TC-001-05: idempotent write ───────────────────────────────────────────────


def test_idempotent_write(cache_file: Path) -> None:
    set_macro_state_override(MacroState.YELLOW)
    content_first = cache_file.read_text()
    set_macro_state_override(MacroState.YELLOW)
    content_second = cache_file.read_text()
    assert content_first == content_second
    assert get_macro_state() == MacroState.YELLOW


# ── TC-001-06: CLI invalid args ───────────────────────────────────────────────


def test_cli_invalid_value_exits_nonzero() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "engine.macro_gate", "--set", "foo"],
        capture_output=True,
    )
    assert result.returncode != 0


def test_cli_uppercase_value_exits_nonzero() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "engine.macro_gate", "--set", "GREEN"],
        capture_output=True,
    )
    assert result.returncode != 0


def test_cli_missing_set_arg_exits_nonzero() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "engine.macro_gate"],
        capture_output=True,
    )
    assert result.returncode != 0


# ── TC-001-07: TARGET_ELASTIC_BY_MACRO_STATE constants ───────────────────────


def test_target_elastic_green() -> None:
    assert TARGET_ELASTIC_BY_MACRO_STATE[MacroState.GREEN] == pytest.approx(0.38)


def test_target_elastic_yellow() -> None:
    assert TARGET_ELASTIC_BY_MACRO_STATE[MacroState.YELLOW] == pytest.approx(0.33)


def test_target_elastic_red() -> None:
    assert TARGET_ELASTIC_BY_MACRO_STATE[MacroState.RED] == pytest.approx(0.20)


def test_target_elastic_has_all_states() -> None:
    assert set(TARGET_ELASTIC_BY_MACRO_STATE.keys()) == {
        MacroState.GREEN,
        MacroState.YELLOW,
        MacroState.RED,
    }
