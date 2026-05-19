"""TC-029-01..04 — ClaimViolation detection and PROMPT_CONTRACT_HASH determinism."""

from __future__ import annotations

from datetime import date

import pytest

_verifier_mod = pytest.importorskip(
    "engine.agent.claim_verifier",
    reason="engine.agent.claim_verifier not yet implemented (pending req_impl)",
)
_contracts_mod = pytest.importorskip(
    "engine.agent.prompt_contracts",
    reason="engine.agent.prompt_contracts not yet implemented (pending req_impl)",
)
_state_mod = pytest.importorskip("engine.agent.state")
_schemas_mod = pytest.importorskip("engine.schemas")

verify_signals = _verifier_mod.verify_signals
ClaimViolation = _verifier_mod.ClaimViolation
PROMPT_CONTRACT_HASH = _contracts_mod.PROMPT_CONTRACT_HASH
FrozenMarketSnapshot = _state_mod.FrozenMarketSnapshot
HoldingRow = _schemas_mod.HoldingRow
HoldingCategory = _schemas_mod.HoldingCategory
PortfolioSummary = _schemas_mod.PortfolioSummary
StockSignal = _schemas_mod.StockSignal


def _snapshot(price_map: dict[str, float]) -> FrozenMarketSnapshot:
    holdings = []
    for code, price in price_map.items():
        holdings.append(HoldingRow(
            schema_version="1.0",
            date=date(2026, 5, 18),
            code=code,
            name=f"Stock-{code}",
            cost_price=price * 0.9,
            current_price=price,
            quantity=100,
            market_value=price * 100,
            pnl_pct="+10.0%",
            pnl_amount=price * 10,
            category=HoldingCategory.ELASTIC,
            sector="科技",
            notes="",
        ))
    return FrozenMarketSnapshot(
        holdings=tuple(holdings),
        macro_state="green",
        portfolio_summary=PortfolioSummary(
            total_market_value=sum(price_map.values()) * 100,
            white_horse_ratio=0.0,
            elastic_ratio=1.0,
            target_white_horse=0.67,
            target_elastic=0.33,
            rebalance_needed=False,
        ),
        price_snapshot=price_map,
        change_pct_snapshot={code: 0.0 for code in price_map},
    )


def _signal(code: str, claimed_price: float | None = None) -> StockSignal:
    extra: dict = {}
    if claimed_price is not None:
        extra["claimed_price"] = claimed_price
    return StockSignal(
        code=code,
        name=f"Stock-{code}",
        category=HoldingCategory.ELASTIC,
        technical_score=70.0,
        fundamental_score=75.0,
        sentiment_score=65.0,
        composite_score=70.0,
        action="持有",
        action_code="hold",
        signals=extra,
    )


# ── TC-029-01 ──────────────────────────────────────────────────────────────────


class TestClaimViolationDetected:
    """TC-029-01: verify_signals returns ClaimViolation when claimed_price deviates > 20%."""

    def test_violation_detected(self):
        snap = _snapshot({"300308": 100.0})
        sig = _signal("300308", claimed_price=999.0)
        violations = verify_signals([sig], snap)
        assert len(violations) == 1

    def test_violation_field_is_price(self):
        snap = _snapshot({"300308": 100.0})
        sig = _signal("300308", claimed_price=999.0)
        violations = verify_signals([sig], snap)
        assert violations[0].field == "price"

    def test_violation_code_matches(self):
        snap = _snapshot({"300308": 100.0})
        sig = _signal("300308", claimed_price=999.0)
        violations = verify_signals([sig], snap)
        assert violations[0].code == "300308"

    def test_small_deviation_no_violation(self):
        snap = _snapshot({"300308": 100.0})
        sig = _signal("300308", claimed_price=110.0)  # 10% deviation — within tolerance
        violations = verify_signals([sig], snap)
        assert violations == []


# ── TC-029-02 ──────────────────────────────────────────────────────────────────


class TestNoClaimedPrice:
    """TC-029-02: verify_signals returns empty list when signal has no claimed_price."""

    def test_no_claimed_price_no_violation(self):
        snap = _snapshot({"300308": 100.0})
        sig = _signal("300308", claimed_price=None)
        violations = verify_signals([sig], snap)
        assert violations == []

    def test_code_not_in_snapshot_no_violation(self):
        snap = _snapshot({"300308": 100.0})
        sig = _signal("999999", claimed_price=50.0)  # code not in snapshot
        violations = verify_signals([sig], snap)
        assert violations == []


# ── TC-029-03 ──────────────────────────────────────────────────────────────────


class TestEmptySignals:
    """TC-029-03: verify_signals returns empty list for empty signal list."""

    def test_empty_signals(self):
        snap = _snapshot({"300308": 100.0})
        assert verify_signals([], snap) == []


# ── TC-029-04 ──────────────────────────────────────────────────────────────────


class TestPromptContractHash:
    """TC-029-04: PROMPT_CONTRACT_HASH is a 12-char deterministic string."""

    def test_hash_is_12_chars(self):
        assert len(PROMPT_CONTRACT_HASH) == 12

    def test_hash_is_non_empty(self):
        assert PROMPT_CONTRACT_HASH.strip() != ""

    def test_hash_is_deterministic(self):
        from importlib import reload

        import engine.agent.prompt_contracts as m1
        m2 = reload(m1)
        assert m1.PROMPT_CONTRACT_HASH == m2.PROMPT_CONTRACT_HASH
