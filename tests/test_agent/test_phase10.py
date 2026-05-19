"""TC-032-01..02, TC-033-01..03, TC-034-01 — Phase 10 account field + technical indicators."""

from __future__ import annotations

import json
from datetime import date
from unittest.mock import MagicMock, patch

import pytest

_schemas_mod = pytest.importorskip("engine.schemas")
_portfolio_mod = pytest.importorskip("engine.portfolio")
_nodes_mod = pytest.importorskip("engine.agent.nodes")
_state_mod = pytest.importorskip("engine.agent.state")

HoldingRow = _schemas_mod.HoldingRow
HoldingCategory = _schemas_mod.HoldingCategory
PortfolioSummary = _schemas_mod.PortfolioSummary
load_holdings = _portfolio_mod.load_holdings
load_holdings_raw = _portfolio_mod.load_holdings_raw
technical_fetcher_node = _nodes_mod.technical_fetcher
signal_ranker = _nodes_mod.signal_ranker
FrozenMarketSnapshot = _state_mod.FrozenMarketSnapshot


# ── shared helpers ─────────────────────────────────────────────────────────────


def _holding(**kwargs) -> HoldingRow:
    defaults: dict = {
        "schema_version": "1.0",
        "date": date(2026, 5, 18),
        "code": "300308",
        "name": "中际旭创",
        "cost_price": 955.14,
        "current_price": 1045.0,
        "quantity": 200,
        "market_value": 209000.0,
        "pnl_pct": "+9.408%",
        "pnl_amount": 17961.53,
        "category": HoldingCategory.WHITE_HORSE,
        "sector": "光模块/CPO",
        "notes": "",
        "account": "西南证券",
    }
    defaults.update(kwargs)
    return HoldingRow(**defaults)


def _summary() -> PortfolioSummary:
    return PortfolioSummary(
        total_market_value=209000.0,
        white_horse_ratio=1.0,
        elastic_ratio=0.0,
        target_white_horse=0.67,
        target_elastic=0.33,
        rebalance_needed=False,
    )


def _snapshot(holdings=None) -> FrozenMarketSnapshot:
    if holdings is None:
        holdings = (_holding(),)
    return FrozenMarketSnapshot(
        holdings=holdings,
        macro_state="yellow",
        portfolio_summary=_summary(),
        price_snapshot={h.code: h.current_price for h in holdings},
        change_pct_snapshot={h.code: 9.4 for h in holdings},
    )


def _base_state(snap=None) -> dict:
    if snap is None:
        snap = _snapshot()
    return {
        "snapshot": snap,
        "kg_subgraph": {},
        "rag_chunks": {},
        "technical_data": {},
        "source_index": {},
        "signals": [],
        "reasoning": {},
        "errors": [],
        "session_id": snap.session_id,
    }


def _signals_json(code="300308", name="中际旭创") -> str:
    return json.dumps([{
        "code": code,
        "name": name,
        "category": "白马股",
        "technical_score": 70.0,
        "fundamental_score": 75.0,
        "sentiment_score": 65.0,
        "composite_score": 70.0,
        "action": "持有",
        "action_code": "hold",
        "technical_reasoning": "MA5>MA20 多头排列 [T1][T3]",
        "fundamental_reasoning": "光模块景气度高 [S4]",
        "sentiment_reasoning": "宏观防御期 [M]",
        "sources_cited": ["T1", "T3", "S4", "M"],
        "signals": {},
    }], ensure_ascii=False)


# ── TC-032-01 ──────────────────────────────────────────────────────────────────


class TestHoldingRowAccountField:
    """TC-032-01: HoldingRow account 字段构造与默认值。"""

    def test_account_field_explicit(self):
        row = _holding(account="华西证券")
        assert row.account == "华西证券"

    def test_account_field_default_empty_string(self):
        row = _holding()
        row2 = HoldingRow(
            schema_version="1.0",
            date=date(2026, 5, 18),
            code="300308",
            name="中际旭创",
            cost_price=955.14,
            current_price=1045.0,
            quantity=200,
            market_value=209000.0,
            pnl_pct="+9.408%",
            pnl_amount=17961.53,
            category=HoldingCategory.WHITE_HORSE,
            sector="光模块/CPO",
        )
        assert row2.account == ""

    def test_account_in_model_dump(self):
        row = _holding(account="西南证券")
        dumped = row.model_dump()
        assert "account" in dumped
        assert dumped["account"] == "西南证券"


# ── TC-032-02 ──────────────────────────────────────────────────────────────────


class TestLoadHoldingsAccount:
    """TC-032-02: load_holdings() 聚合后 603986 account='华西证券+西南证券'。"""

    def test_load_holdings_raw_eight_rows(self):
        raw = load_holdings_raw()
        assert len(raw) == 8

    def test_raw_603986_has_two_rows(self):
        raw = load_holdings_raw()
        rows_603986 = [h for h in raw if h.code == "603986"]
        assert len(rows_603986) == 2
        accounts = {h.account for h in rows_603986}
        assert accounts == {"华西证券", "西南证券"}

    def test_aggregated_603986_account_merged(self):
        agg = load_holdings()
        row = next(h for h in agg if h.code == "603986")
        assert row.account == "华西证券+西南证券"

    def test_all_raw_rows_have_nonempty_account(self):
        raw = load_holdings_raw()
        for h in raw:
            assert h.account != "", f"{h.code} {h.name} has empty account"


# ── TC-033-01 ──────────────────────────────────────────────────────────────────


class TestFetchTechnicalsReturnShape:
    """TC-033-01: fetch_technicals mock akshare 返回含 MA5/MACD_DIF 的指标 dict。

    akshare 在 optional [data] 组，无需安装即可运行 CI。
    通过 patch 源模块的 ak.stock_zh_a_hist 替换掉真实 HTTP 调用。
    """

    @staticmethod
    def _make_mock_df(n: int = 60):
        import numpy as np
        import pandas as pd

        close = np.linspace(100, 130, n)
        return pd.DataFrame({
            "收盘": close,
            "开盘": close - 1,
            "最高": close + 1,
            "最低": close - 2,
            "成交量": [1_000_000] * n,
        })

    def test_all_keys_present_with_mock_ohlcv(self):
        import sys
        from types import ModuleType

        # Provide a minimal akshare stub if not installed
        mock_df = self._make_mock_df()
        ak_stub = ModuleType("akshare")
        ak_stub.stock_zh_a_hist = MagicMock(return_value=mock_df)

        with patch.dict(sys.modules, {"akshare": ak_stub}):
            # Re-import to pick up stub
            import importlib
            import engine.agent.technical_fetcher as tf_mod
            importlib.reload(tf_mod)
            result = tf_mod.fetch_technicals(["300308"])

        assert "300308" in result
        tech = result["300308"]
        for key in ["MA5", "MA10", "MA20", "MA30", "MACD_DIF", "MACD_DEA", "MACD_BAR", "RSI14"]:
            assert key in tech, f"missing key: {key}"
            assert isinstance(tech[key], float), f"{key} is not float"

    def test_ma5_value_is_recent_average(self):
        import importlib
        import sys
        from types import ModuleType

        import numpy as np

        n = 60
        close_prices = np.linspace(100, 130, n)
        mock_df = self._make_mock_df(n)
        ak_stub = ModuleType("akshare")
        ak_stub.stock_zh_a_hist = MagicMock(return_value=mock_df)

        with patch.dict(sys.modules, {"akshare": ak_stub}):
            import engine.agent.technical_fetcher as tf_mod
            importlib.reload(tf_mod)
            result = tf_mod.fetch_technicals(["300308"])

        ma5 = result["300308"]["MA5"]
        expected_ma5 = float(close_prices[-5:].mean())
        assert abs(ma5 - expected_ma5) < 0.5


# ── TC-033-02 ──────────────────────────────────────────────────────────────────


class TestTechnicalFetcherNodeDegradation:
    """TC-033-02: technical_fetcher 节点在 akshare 失败时优雅降级。

    fetch_technicals 在 node 函数体内 lazy import（不是 nodes 模块的顶层属性），
    正确的 patch 路径是源模块 engine.agent.technical_fetcher.fetch_technicals。
    """

    _PATCH_TARGET = "engine.agent.technical_fetcher.fetch_technicals"

    def test_returns_empty_technical_data_on_error(self):
        state = _base_state()

        with patch(self._PATCH_TARGET, side_effect=ConnectionError("mock network error")):
            result = technical_fetcher_node(state)

        assert result["technical_data"] == {}

    def test_appends_error_message_on_failure(self):
        state = _base_state()

        with patch(self._PATCH_TARGET, side_effect=RuntimeError("akshare timeout")):
            result = technical_fetcher_node(state)

        assert len(result["errors"]) == 1
        assert "technical_fetcher" in result["errors"][0]

    def test_no_exception_raised_on_failure(self):
        state = _base_state()

        with patch(self._PATCH_TARGET, side_effect=Exception("any error")):
            result = technical_fetcher_node(state)  # should not raise

        assert isinstance(result, dict)


# ── TC-033-03 ──────────────────────────────────────────────────────────────────


class TestSignalRankerTRefs:
    """TC-033-03: signal_ranker 读取非空 technical_data 后 source_index 含 T1..T8。"""

    def test_source_index_contains_t_refs_for_all_indicators(self):
        snap = _snapshot()
        state = _base_state(snap)
        state["technical_data"] = {
            "300308": {
                "MA5": 1045.2, "MA10": 1038.5, "MA20": 1020.0, "MA30": 1005.0,
                "MACD_DIF": 12.34, "MACD_DEA": 10.21, "MACD_BAR": 4.26, "RSI14": 62.1,
            }
        }
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = MagicMock(content=_signals_json())

        result = signal_ranker(state, llm=mock_llm)

        idx = result["source_index"]["300308"]
        assert "T1" in idx, "T1 (MA5) missing from source_index"
        assert "MA5" in idx["T1"]
        assert "T5" in idx, "T5 (MACD DIF) missing from source_index"
        assert "MACD DIF" in idx["T5"]
        assert "T8" in idx, "T8 (RSI) missing from source_index"
        assert "RSI" in idx["T8"]

    def test_nan_indicators_excluded_from_source_index(self):
        import math

        snap = _snapshot()
        state = _base_state(snap)
        state["technical_data"] = {
            "300308": {
                "MA5": 1045.2, "MA10": float("nan"),  # MA10 is NaN
                "MA20": float("nan"), "MA30": float("nan"),
                "MACD_DIF": 12.34, "MACD_DEA": 10.21, "MACD_BAR": 4.26, "RSI14": 62.1,
            }
        }
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = MagicMock(content=_signals_json())

        result = signal_ranker(state, llm=mock_llm)

        idx = result["source_index"]["300308"]
        assert "T1" in idx          # MA5 present (non-NaN)
        assert "T2" not in idx      # MA10 absent (NaN)
        assert "T3" not in idx      # MA20 absent (NaN)

    def test_empty_technical_data_produces_no_t_refs(self):
        snap = _snapshot()
        state = _base_state(snap)
        state["technical_data"] = {}  # no technical data
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = MagicMock(content=_signals_json())

        result = signal_ranker(state, llm=mock_llm)

        idx = result["source_index"].get("300308", {})
        t_refs = [k for k in idx if k.startswith("T")]
        assert len(t_refs) == 0


# ── TC-034-01 ──────────────────────────────────────────────────────────────────


class TestLoadHoldingsRawAccountFilter:
    """TC-034-01: load_holdings_raw() 按账户过滤后华西 3 只、西南 5 只。"""

    def test_raw_total_eight_rows(self):
        raw = load_holdings_raw()
        assert len(raw) == 8

    def test_huaxi_three_holdings(self):
        raw = load_holdings_raw()
        huaxi = [h for h in raw if h.account == "华西证券"]
        assert len(huaxi) == 3

    def test_xinan_five_holdings(self):
        raw = load_holdings_raw()
        xinan = [h for h in raw if h.account == "西南证券"]
        assert len(xinan) == 5

    def test_huaxi_codes_correct(self):
        raw = load_holdings_raw()
        huaxi_codes = {h.code for h in raw if h.account == "华西证券"}
        assert huaxi_codes == {"603986", "002384", "600150"}

    def test_xinan_codes_correct(self):
        raw = load_holdings_raw()
        xinan_codes = {h.code for h in raw if h.account == "西南证券"}
        assert xinan_codes == {"300308", "603986", "300394", "688820", "002957"}
