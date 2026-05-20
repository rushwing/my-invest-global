"""Unit tests for tab1_overview pure helpers."""
from __future__ import annotations

import pandas as pd
import pytest


def _overview():
    from app.components.tab1_overview import _df_changed, _enrich, _pbar_html
    return _enrich, _df_changed, _pbar_html


def test_enrich_computes_market_value():
    _enrich, _, _ = _overview()
    df = pd.DataFrame([{
        "code": "300308", "name": "中际旭创", "category": "弹性股",
        "cost_price": 100.0, "current_price": 120.0, "quantity": 100,
    }])
    result = _enrich(df)
    assert result["market_value"].iloc[0] == pytest.approx(12000.0)
    assert result["pnl_pct"].iloc[0] == pytest.approx(20.0)


def test_enrich_handles_zero_cost():
    _enrich, _, _ = _overview()
    df = pd.DataFrame([{
        "code": "000001", "name": "平安银行", "category": "白马股",
        "cost_price": 0.0, "current_price": 10.0, "quantity": 50,
    }])
    result = _enrich(df)
    assert result["pnl_pct"].iloc[0] == pytest.approx(0.0)


def test_enrich_adds_missing_columns():
    _enrich, _, _ = _overview()
    df = pd.DataFrame([{"code": "000001"}])
    result = _enrich(df)
    assert "market_value" in result.columns
    assert "pnl_pct" in result.columns


def test_df_changed_detects_difference():
    _, _df_changed, _ = _overview()
    a = pd.DataFrame([{"code": "A", "name": "X", "category": "白马股",
                        "cost_price": 10.0, "current_price": 11.0, "quantity": 100}])
    b = pd.DataFrame([{"code": "A", "name": "Y", "category": "白马股",
                        "cost_price": 10.0, "current_price": 11.0, "quantity": 100}])
    assert _df_changed(a, b) is True


def test_df_changed_same_data():
    _, _df_changed, _ = _overview()
    a = pd.DataFrame([{"code": "A", "name": "X", "category": "白马股",
                        "cost_price": 10.0, "current_price": 11.0, "quantity": 100}])
    assert _df_changed(a, a.copy()) is False


def test_df_changed_shape_mismatch():
    _, _df_changed, _ = _overview()
    a = pd.DataFrame([{"code": "A"}])
    b = pd.DataFrame()
    assert _df_changed(a, b) is True


def test_pbar_html_contains_width():
    _, _, _pbar_html = _overview()
    html = _pbar_html(50.0, 33.0, "#00C47A")
    assert "50.0%" in html
    assert "33.0%" in html
    assert "#00C47A" in html
