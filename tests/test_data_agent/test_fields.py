"""Tests for engine.data_agent.fields — FieldGroup enum and FIELD_POLICIES."""

import pytest

from engine.data_agent.fields import (
    FAST_SOURCES,
    FIELD_POLICIES,
    FieldGroup,
    SourcePolicy,
)


class TestFieldGroup:
    def test_all_members_present(self):
        expected = {"quote", "kline", "kline_min", "fundamental", "segment",
                    "fund_flow", "shareholder", "announcement", "index"}
        assert {g.value for g in FieldGroup} == expected

    def test_str_enum(self):
        assert FieldGroup.QUOTE == "quote"
        assert FieldGroup.KLINE.value == "kline"

    def test_from_value(self):
        assert FieldGroup("fund_flow") is FieldGroup.FUND_FLOW


class TestSourcePolicy:
    def test_defaults(self):
        p = SourcePolicy(primary="tencent", backups=["sina"])
        assert p.timeout_s == 20
        assert p.retries == 3
        assert p.circuit_break_after == 3
        assert p.cooldown_s == 600

    def test_backups_list(self):
        p = SourcePolicy(primary="tushare", backups=["eastmoney", "akshare"])
        assert len(p.backups) == 2


class TestFieldPolicies:
    def test_all_groups_covered(self):
        for group in FieldGroup:
            assert group in FIELD_POLICIES, f"{group} missing from FIELD_POLICIES"

    def test_quote_primary_is_tencent(self):
        assert FIELD_POLICIES[FieldGroup.QUOTE].primary == "tencent"

    def test_fundamental_primary_is_tushare(self):
        assert FIELD_POLICIES[FieldGroup.FUNDAMENTAL].primary == "tushare"

    def test_announcement_primary_is_cninfo(self):
        assert FIELD_POLICIES[FieldGroup.ANNOUNCEMENT].primary == "cninfo"

    def test_all_policies_have_backups(self):
        for group, policy in FIELD_POLICIES.items():
            assert len(policy.backups) >= 1, f"{group} has no backup sources"

    def test_policy_primary_not_in_backups(self):
        for group, policy in FIELD_POLICIES.items():
            assert policy.primary not in policy.backups, (
                f"{group}: primary '{policy.primary}' appears in backups"
            )


class TestFastSources:
    def test_fast_sources_is_frozenset(self):
        assert isinstance(FAST_SOURCES, frozenset)

    def test_tencent_is_fast(self):
        assert "tencent" in FAST_SOURCES

    def test_eastmoney_is_not_fast(self):
        assert "eastmoney" not in FAST_SOURCES
