"""TC-022-01..04 — KG seed loader: MERGE call counts and idempotent Cypher."""

from __future__ import annotations

import re
from pathlib import Path
from unittest.mock import MagicMock

import pytest

_seed_mod = pytest.importorskip(
    "engine.kg.seed_loader",
    reason="engine.kg.seed_loader not yet implemented (pending req_impl)",
)

StockSeedRow = _seed_mod.StockSeedRow
ConceptSeedRow = _seed_mod.ConceptSeedRow
run_seed = _seed_mod.run_seed
load_concepts_yaml = _seed_mod.load_concepts_yaml
_MERGE_SECTOR = _seed_mod._MERGE_SECTOR
_MERGE_SUBSECTOR = _seed_mod._MERGE_SUBSECTOR
_MERGE_STOCK = _seed_mod._MERGE_STOCK
_MERGE_CONCEPT = _seed_mod._MERGE_CONCEPT
_MERGE_EXPOSED_TO = _seed_mod._MERGE_EXPOSED_TO

_ALL_STMTS = [_MERGE_SECTOR, _MERGE_SUBSECTOR, _MERGE_STOCK, _MERGE_CONCEPT, _MERGE_EXPOSED_TO]


def _stock(code: str, name: str, sector_id: str, sub_id: str, concepts: list[str] | None = None) -> StockSeedRow:
    return StockSeedRow(
        code=code, name=name, exchange="SZSE", board="创业板",
        scarcity="Tier-1", rating="A", active=True,
        sub_sector_id=sub_id, sub_sector_name=sub_id + "_name",
        sector_id=sector_id, sector_name=sector_id + "_name",
        exposed_concepts=concepts or [],
    )


def _concept(id: str) -> ConceptSeedRow:
    return ConceptSeedRow(id=id, name=id, description=id, theme="test")


# ── TC-022-01 ──────────────────────────────────────────────────────────────────


class TestRunSeedCallCount:
    """TC-022-01: session.run call count matches formula for shared sector/subsector."""

    def test_shared_sector_subsector(self):
        session = MagicMock()
        stocks = [
            _stock("300308", "中际旭创", "光通信", "光模块", concepts=["cpo"]),
            _stock("600519", "test", "光通信", "光模块"),
        ]
        concepts = [_concept("cpo"), _concept("hbm")]
        run_seed(session, stocks, concepts)
        # 1 Sector + 1 SubSector + 2 Stocks + 2 Concepts + 1 EXPOSED_TO = 7
        assert session.run.call_count == 7

    def test_no_concepts_no_exposed_to_calls(self):
        session = MagicMock()
        stocks = [_stock("300308", "中际旭创", "光通信", "光模块")]
        run_seed(session, stocks, [])
        # 1 Sector + 1 SubSector + 1 Stock + 0 EXPOSED_TO = 3
        assert session.run.call_count == 3


# ── TC-022-02 ──────────────────────────────────────────────────────────────────


class TestRunSeedDifferentSectors:
    """TC-022-02: stocks in different sectors each get their own MERGE_SECTOR call."""

    def test_two_distinct_sector_merges(self):
        session = MagicMock()
        stocks = [
            _stock("300308", "中际旭创", "光通信", "光模块"),
            _stock("688981", "中芯国际", "半导体", "晶圆代工"),
        ]
        run_seed(session, stocks, [])

        sector_calls = [
            c for c in session.run.call_args_list
            if c.args[0] == _MERGE_SECTOR
        ]
        assert len(sector_calls) == 2
        sector_ids = {c.kwargs["sector_id"] for c in sector_calls}
        assert sector_ids == {"光通信", "半导体"}


# ── TC-022-03 ──────────────────────────────────────────────────────────────────


class TestLoadConceptsYaml:
    """TC-022-03: load_concepts_yaml returns 8 ConceptSeedRow from the bundled YAML."""

    def test_returns_8_concepts(self):
        yaml_path = Path("data/kg_seed/concepts.yaml")
        concepts = load_concepts_yaml(yaml_path)
        assert len(concepts) == 8

    def test_all_are_concept_seed_rows(self):
        yaml_path = Path("data/kg_seed/concepts.yaml")
        concepts = load_concepts_yaml(yaml_path)
        assert all(isinstance(c, ConceptSeedRow) for c in concepts)

    def test_required_ids_present(self):
        yaml_path = Path("data/kg_seed/concepts.yaml")
        concepts = load_concepts_yaml(yaml_path)
        ids = {c.id for c in concepts}
        assert {"cpo", "hbm", "ai_server"}.issubset(ids)


# ── TC-022-04 ──────────────────────────────────────────────────────────────────


class TestCypherIdempotency:
    """TC-022-04: all Cypher strings use MERGE and contain no bare CREATE."""

    @pytest.mark.parametrize("stmt", _ALL_STMTS)
    def test_contains_merge(self, stmt: str):
        assert "MERGE" in stmt

    @pytest.mark.parametrize("stmt", _ALL_STMTS)
    def test_no_bare_create(self, stmt: str):
        # Remove "ON CREATE SET" (allowed); then assert no remaining CREATE
        cleaned = stmt.replace("ON CREATE SET", "")
        assert "CREATE" not in cleaned, (
            f"Bare CREATE found after removing 'ON CREATE SET':\n{stmt!r}"
        )
