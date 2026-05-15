from datetime import date, datetime

from scripts.refresh_aidc_data import (
    STOCKS,
    TARGET_CUTOFF,
    RefreshedStock,
    TargetPrice,
    calculate_return,
    format_market_cap,
    format_share_percent,
    format_target,
    market_symbol,
    validate_refreshed_rows,
)


def test_market_symbol_uses_exchange_prefix() -> None:
    assert market_symbol("300308") == "sz300308"
    assert market_symbol("688256") == "sh688256"


def test_calculate_return_uses_latest_prior_base_date() -> None:
    kline = [
        ["2026-02-12", "10", "10", "11", "9", "100"],
        ["2026-02-13", "11", "12", "12", "10", "100"],
        ["2026-05-13", "19", "20", "21", "18", "100"],
    ]

    assert calculate_return(kline, date(2026, 5, 13), 90) == 100


def test_validate_rejects_stale_or_below_market_target() -> None:
    meta = STOCKS[0]
    row = RefreshedStock(
        meta=meta,
        price=100,
        one_month_return=1,
        three_month_return=2,
        market_cap_yi=1000,
        dynamic_pe=30,
        quote_time=datetime(2026, 5, 13, 15, 0),
        target=TargetPrice(value=90, broker="示例证券", report_date=TARGET_CUTOFF),
        daily_return=0.5,
        volume_lot=12345,
        amount_wan=67890,
    )

    assert validate_refreshed_rows([row]) == [
        "中际旭创(300308): target price is below current price"
    ]


def test_formatters_keep_unverified_targets_blank() -> None:
    assert format_target(None) == ""
    assert format_market_cap(11683.9) == "1.17万亿"
    assert format_market_cap(6252.22) == "6252亿"
    assert format_share_percent(63.9) == "63.9%"
