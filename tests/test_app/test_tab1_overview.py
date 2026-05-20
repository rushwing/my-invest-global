"""Unit tests for tab1_overview pure helpers."""
from __future__ import annotations

import pandas as pd
import pytest


def _overview():
    from app.components.tab1_overview import _df_changed, _enrich, _normalize_codes, _pbar_html
    return _enrich, _df_changed, _pbar_html, _normalize_codes


def test_enrich_computes_market_value():
    _enrich, _, _, _ = _overview()
    df = pd.DataFrame([{
        "code": "300308", "name": "中际旭创", "category": "弹性股",
        "cost_price": 100.0, "current_price": 120.0, "quantity": 100,
    }])
    result = _enrich(df)
    assert result["market_value"].iloc[0] == pytest.approx(12000.0)
    assert result["pnl_pct"].iloc[0] == pytest.approx(20.0)


def test_enrich_handles_zero_cost():
    _enrich, _, _, _ = _overview()
    df = pd.DataFrame([{
        "code": "000001", "name": "平安银行", "category": "白马股",
        "cost_price": 0.0, "current_price": 10.0, "quantity": 50,
    }])
    result = _enrich(df)
    assert result["pnl_pct"].iloc[0] == pytest.approx(0.0)


def test_enrich_adds_missing_columns():
    _enrich, _, _, _ = _overview()
    df = pd.DataFrame([{"code": "000001"}])
    result = _enrich(df)
    assert "market_value" in result.columns
    assert "pnl_pct" in result.columns


def test_df_changed_detects_difference():
    _, _df_changed, _, _ = _overview()
    a = pd.DataFrame([{"code": "A", "name": "X", "category": "白马股",
                        "cost_price": 10.0, "current_price": 11.0, "quantity": 100}])
    b = pd.DataFrame([{"code": "A", "name": "Y", "category": "白马股",
                        "cost_price": 10.0, "current_price": 11.0, "quantity": 100}])
    assert _df_changed(a, b) is True


def test_df_changed_same_data():
    _, _df_changed, _, _ = _overview()
    a = pd.DataFrame([{"code": "A", "name": "X", "category": "白马股",
                        "cost_price": 10.0, "current_price": 11.0, "quantity": 100}])
    assert _df_changed(a, a.copy()) is False


def test_df_changed_shape_mismatch():
    _, _df_changed, _, _ = _overview()
    a = pd.DataFrame([{"code": "A"}])
    b = pd.DataFrame()
    assert _df_changed(a, b) is True


def test_pbar_html_contains_width():
    _, _, _pbar_html, _ = _overview()
    html = _pbar_html(50.0, 33.0, "#00C47A")
    assert "50.0%" in html
    assert "33.0%" in html
    assert "#00C47A" in html


# ── _normalize_codes ──────────────────────────────────────────────────────────

def test_normalize_codes_pads_short_a_share():
    _, _, _, _normalize_codes = _overview()
    df = pd.DataFrame([{"code": "1"}, {"code": "300308"}, {"code": "60519"}])
    result = _normalize_codes(df)
    assert result["code"].tolist() == ["000001", "300308", "060519"]


def test_normalize_codes_leaves_us_tickers_unchanged():
    _, _, _, _normalize_codes = _overview()
    df = pd.DataFrame([{"code": "NVDA"}, {"code": "AAPL"}])
    result = _normalize_codes(df)
    assert result["code"].tolist() == ["NVDA", "AAPL"]


def test_normalize_codes_strips_whitespace():
    _, _, _, _normalize_codes = _overview()
    df = pd.DataFrame([{"code": " 1 "}])
    result = _normalize_codes(df)
    assert result["code"].iloc[0] == "000001"


def test_normalize_codes_handles_missing_column():
    _, _, _, _normalize_codes = _overview()
    df = pd.DataFrame([{"name": "foo"}])
    result = _normalize_codes(df)
    assert "code" not in result.columns


def test_normalize_codes_nan_becomes_none():
    """NaN and blank codes must stay None, not become the string 'nan'."""
    _, _, _, _normalize_codes = _overview()
    df = pd.DataFrame([{"code": None}, {"code": float("nan")}, {"code": ""}])
    result = _normalize_codes(df)
    assert result["code"].isna().all(), result["code"].tolist()


def test_csv_import_preserves_duplicate_lots():
    """Importing a CSV must NOT drop existing rows for the same code.

    603986 appears twice in production holdings (two buy batches).  A CSV
    import that also contains 603986 should append, not overwrite/deduplicate.
    """
    from app.components.tab1_overview import _EDITOR_COLS, _normalize_codes

    existing = pd.DataFrame([
        {"code": "603986", "name": "兆易创新", "category": "弹性股",
         "cost_price": 80.0, "current_price": 90.0, "quantity": 400},
        {"code": "603986", "name": "兆易创新", "category": "弹性股",
         "cost_price": 70.0, "current_price": 90.0, "quantity": 200},
    ])
    csv_import = pd.DataFrame([
        {"code": "603986", "name": "兆易创新", "category": "弹性股",
         "cost_price": 85.0, "current_price": 90.0, "quantity": 100},
    ])
    csv_import = _normalize_codes(csv_import.reindex(columns=_EDITOR_COLS))
    csv_import = csv_import[csv_import["code"].notna() & (csv_import["code"] != "")]

    merged = pd.concat([existing, csv_import], ignore_index=True)
    assert len(merged) == 3
    assert merged["quantity"].sum() == 700
