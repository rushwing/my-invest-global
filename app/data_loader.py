"""REQ-020: All data-loading and compute helpers for the dashboard."""
from __future__ import annotations

import json
from datetime import date as _date
from datetime import timedelta
from pathlib import Path

import duckdb
import pandas as pd
import streamlit as st

DB_PATH = "data/db/aidc.duckdb"


# ── File-based loaders ────────────────────────────────────────────────────────


@st.cache_data(ttl=300)
def load_latest_holdings() -> pd.DataFrame | None:
    # CSV snapshots take priority (saved by sidebar editor)
    files = sorted(Path("data/agent_input/cn").glob("holdings_*.csv"), reverse=True)
    if files:
        return pd.read_csv(files[0])
    # Fall back to holdings.yaml (source-of-truth maintained by hand)
    yaml_path = Path("data/agent_input/cn/holdings.yaml")
    if yaml_path.exists():
        import yaml  # type: ignore
        data = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
        rows = data.get("holdings", [])
        return pd.DataFrame(rows) if rows else None
    return None


@st.cache_data(ttl=300)
def load_latest_signals() -> dict | None:
    files = sorted(Path("data/processed").glob("signals_*.json"), reverse=True)
    if not files:
        return None
    return json.loads(files[0].read_text())


@st.cache_data(ttl=300)
def load_recommendations() -> str | None:
    files = sorted(Path("data/processed").glob("recommendations_*.md"), reverse=True)
    if not files:
        return None
    return files[0].read_text(encoding="utf-8")


@st.cache_data(ttl=300)
def load_macro_state() -> dict:
    path = Path("data/cache/macro_state.json")
    if not path.exists():
        return {"state": "yellow"}
    data = json.loads(path.read_text())
    data["state"] = data.get("state", "yellow").lower()
    return data


@st.cache_data(ttl=300)
def load_cloud_capex() -> pd.DataFrame:
    path = Path("data/cache/cloud_capex.json")
    static = [
        {"vendor": "MSFT", "fy2025": 80.3, "fy2026_est": 95.0},
        {"vendor": "AMZN", "fy2025": 83.0, "fy2026_est": 98.0},
        {"vendor": "GOOG", "fy2025": 52.1, "fy2026_est": 62.0},
        {"vendor": "META", "fy2025": 40.0, "fy2026_est": 49.0},
    ]
    if not path.exists():
        return pd.DataFrame(static)
    return pd.DataFrame(json.loads(path.read_text()))


@st.cache_data(ttl=300)
def load_scarcity_matrix() -> pd.DataFrame:
    path = Path("data/processed/scarcity_matrix.json")
    cols = ["code", "name", "rank", "composite_score", "owned", "warn", "rating"]
    if not path.exists():
        return pd.DataFrame(columns=cols)
    return pd.DataFrame(json.loads(path.read_text()))


@st.cache_data(ttl=300)
def load_rebalance_history() -> pd.DataFrame:
    path = Path("data/processed/rebalance_history.json")
    if not path.exists():
        return pd.DataFrame(columns=["date", "action", "reason"])
    return pd.DataFrame(json.loads(path.read_text()))


# ── DuckDB-backed loaders ─────────────────────────────────────────────────────


@st.cache_data(ttl=300)
def load_ohlcv(ticker: str, days: int = 180) -> pd.DataFrame:
    try:
        conn = duckdb.connect(DB_PATH, read_only=True)
        cutoff = (_date.today() - timedelta(days=days)).isoformat()
        df = conn.execute(
            """
            SELECT trade_date AS date, open, high, low, close, volume
            FROM stock_prices
            WHERE code = ? AND trade_date >= ?
            ORDER BY trade_date
            """,
            [ticker, cutoff],
        ).df()
        conn.close()
    except Exception:
        df = pd.DataFrame(columns=["date", "open", "high", "low", "close", "volume"])

    if df.empty:
        try:
            df = fetch_akshare_history(ticker, days)
            if not df.empty:
                write_ohlcv_to_duckdb(ticker, df)
        except Exception:
            df = pd.DataFrame(columns=["date", "open", "high", "low", "close", "volume"])

    return df.sort_values("date").reset_index(drop=True)


@st.cache_data(ttl=300)
def load_news_for_ticker(ticker: str, limit: int = 8) -> pd.DataFrame:
    cols = ["title", "source", "published_at", "sentiment", "relevance_score"]
    try:
        conn = duckdb.connect(DB_PATH, read_only=True)
        df = conn.execute(
            """
            SELECT title, source, published_at, sentiment, relevance_score
            FROM news_items
            WHERE ? = ANY(tickers_mentioned)
            ORDER BY published_at DESC
            LIMIT ?
            """,
            [ticker, limit],
        ).df()
        conn.close()
        return df
    except Exception:
        return pd.DataFrame(columns=cols)


@st.cache_data(ttl=300)
def load_fund_flow_5d(codes: list[str], days: int = 5) -> pd.DataFrame:
    empty = pd.DataFrame(columns=["code", "trade_date", "main_net_inflow"])
    if not codes:
        return empty
    cutoff = (_date.today() - timedelta(days=days + 2)).isoformat()
    try:
        conn = duckdb.connect(DB_PATH, read_only=True)
        df = conn.execute(
            """
            SELECT code, trade_date, main_net_inflow
            FROM stock_fund_flow
            WHERE code = ANY($1) AND trade_date >= $2
            ORDER BY code, trade_date
            """,
            [codes, cutoff],
        ).df()
        conn.close()
        return df
    except Exception:
        return empty


@st.cache_data(ttl=300)
def load_market_breadth(days: int = 20) -> pd.DataFrame:
    cutoff = (_date.today() - timedelta(days=days)).isoformat()
    try:
        conn = duckdb.connect(DB_PATH, read_only=True)
        df = conn.execute(
            """
            SELECT DATE(quote_time) AS date,
                   SUM(CASE WHEN pct_change > 0 THEN 1 ELSE 0 END)::DOUBLE
                   / NULLIF(COUNT(*), 0) AS up_ratio
            FROM stock_quotes
            WHERE DATE(quote_time) >= ?
            GROUP BY DATE(quote_time)
            ORDER BY date
            """,
            [cutoff],
        ).df()
        conn.close()
        return df
    except Exception:
        return pd.DataFrame(columns=["date", "up_ratio"])


# ── Pure compute functions (no cache) ─────────────────────────────────────────


def compute_portfolio_metrics(df: pd.DataFrame, macro_state: str) -> dict:
    """macro_state accepts green/yellow/red (case-insensitive)."""
    macro_key = macro_state.lower()
    targets = {"green": 38, "yellow": 33, "red": 20}
    elastic_target = targets.get(macro_key, 33)

    total_mv = float(df["market_value"].sum()) if not df.empty else 0.0
    if total_mv == 0:
        return {
            "total_mv": 0.0, "white_mv": 0.0, "elastic_mv": 0.0,
            "white_pct": 0.0, "elastic_pct": 0.0,
            "elastic_target": elastic_target, "df": df,
        }

    white_mv = float(df[df["category"] == "白马股"]["market_value"].sum())
    elastic_mv = float(df[df["category"] == "弹性股"]["market_value"].sum())
    df = df.copy()
    df["pct"] = df["market_value"] / total_mv * 100
    df["target_pct"] = df["category"].map(
        lambda c: elastic_target if c == "弹性股" else (100 - elastic_target)
    )
    df["deviation"] = df["pct"] - df["target_pct"]
    return {
        "total_mv": total_mv,
        "white_mv": white_mv,
        "elastic_mv": elastic_mv,
        "white_pct": white_mv / total_mv * 100,
        "elastic_pct": elastic_mv / total_mv * 100,
        "elastic_target": elastic_target,
        "df": df,
    }


def compute_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Append technical indicator columns to an OHLCV DataFrame."""
    import pandas_ta as ta  # type: ignore

    df = df.copy()
    close = df["close"]

    df["ma65"] = ta.sma(close, length=65) if len(df) >= 65 else float("nan")

    bb = ta.bbands(close, length=20, std=2)
    if bb is not None:
        upper_col = next((c for c in bb.columns if c.startswith("BBU")), None)
        mid_col   = next((c for c in bb.columns if c.startswith("BBM")), None)
        lower_col = next((c for c in bb.columns if c.startswith("BBL")), None)
        df["bb_upper"] = bb[upper_col] if upper_col else float("nan")
        df["bb_mid"]   = bb[mid_col]   if mid_col   else float("nan")
        df["bb_lower"] = bb[lower_col] if lower_col else float("nan")
    else:
        df[["bb_upper", "bb_mid", "bb_lower"]] = float("nan")

    macd = ta.macd(close, fast=12, slow=26, signal=9)
    if macd is not None:
        df["macd"]        = macd.get("MACD_12_26_9",  float("nan"))
        df["macd_signal"] = macd.get("MACDs_12_26_9", float("nan"))
        df["macd_hist"]   = macd.get("MACDh_12_26_9", float("nan"))
    else:
        df[["macd", "macd_signal", "macd_hist"]] = float("nan")

    df["rsi14"] = ta.rsi(close, length=14)
    return df


def compute_trigger_status(holdings_df: pd.DataFrame, macro_state: str) -> pd.DataFrame:
    macro_key = macro_state.lower()
    elastic_target = {"green": 0.38, "yellow": 0.33, "red": 0.20}.get(macro_key, 0.33)

    triggers = [
        {"trigger": "云 CapEx 指引上调（季度）", "direction": "弹性股 ↑",
         "magnitude": "+7%，上限 40%"},
        {"trigger": "云 CapEx 指引下调 >10%", "direction": "弹性股 ↓",
         "magnitude": "-13%，下限 20%"},
        {"trigger": "板块整体回撤 >15%", "direction": "白马股 ↑", "magnitude": "+7%，上限 75%"},
        {"trigger": "板块突破前高（放量）", "direction": "弹性股 ↑", "magnitude": "+5%，上限 38%"},
        {"trigger": "单只弹性股亏损 >20%", "direction": "止损提示", "magnitude": "建议减仓/退出"},
        {"trigger": "单只持仓达目标价 80%", "direction": "止盈提示",
         "magnitude": "建议减仓 30–50%"},
        {"trigger": "单只弹性股超 10%", "direction": "调仓提示", "magnitude": "建议减至 <8%"},
    ]
    rows = []
    for t in triggers:
        status = "normal"
        if not holdings_df.empty:
            total_mv = holdings_df["market_value"].sum()
            if total_mv > 0:
                elastic_pct = (
                    holdings_df[holdings_df["category"] == "弹性股"]["market_value"].sum()
                    / total_mv
                )
                deviation = elastic_pct - elastic_target
                if abs(deviation) > 0.10:
                    status = "triggered"
                elif abs(deviation) > 0.05:
                    status = "watch"
        rows.append({**t, "status": status})
    return pd.DataFrame(rows)


# ── Private helpers ───────────────────────────────────────────────────────────


def fetch_akshare_history(ticker: str, days: int) -> pd.DataFrame:
    import akshare as ak  # type: ignore
    start = (_date.today() - timedelta(days=days + 30)).strftime("%Y%m%d")
    df = ak.stock_zh_a_hist(symbol=ticker, period="daily", start_date=start, adjust="qfq")
    df = df.rename(columns={
        "日期": "date", "开盘": "open", "最高": "high",
        "最低": "low", "收盘": "close", "成交量": "volume",
    })
    return df[["date", "open", "high", "low", "close", "volume"]].copy()


def write_ohlcv_to_duckdb(ticker: str, df: pd.DataFrame) -> None:
    if df.empty:
        return
    conn = duckdb.connect(DB_PATH)
    import datetime
    now = datetime.datetime.now(datetime.UTC)
    rows = [
        (ticker, str(row["date"]), float(row["open"]), float(row["high"]),
         float(row["low"]), float(row["close"]), int(row["volume"]),
         None, None, "qfq", "akshare", now)
        for _, row in df.iterrows()
    ]
    conn.executemany(
        """
        INSERT OR REPLACE INTO stock_prices
          (code, trade_date, open, high, low, close, volume,
           amount, adj_factor, adj_type, source, fetched_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        rows,
    )
    conn.close()
