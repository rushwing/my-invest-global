from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from neo4j import Session


@dataclass
class StockSeedRow:
    code: str
    name: str
    exchange: str
    board: str
    scarcity: str
    rating: str
    active: bool
    sub_sector_id: str
    sub_sector_name: str
    sector_id: str
    sector_name: str
    exposed_concepts: list[str] = field(default_factory=list)


@dataclass
class ConceptSeedRow:
    id: str
    name: str
    description: str
    theme: str


_MERGE_SECTOR = """
MERGE (sec:Sector {id: $sector_id})
ON CREATE SET sec.name = $sector_name
"""

_MERGE_SUBSECTOR = """
MERGE (sub:SubSector {id: $sub_id})
ON CREATE SET sub.name = $sub_name
WITH sub
MATCH (sec:Sector {id: $sector_id})
MERGE (sub)-[:PART_OF]->(sec)
"""

_MERGE_STOCK = """
MERGE (s:Stock {code: $code})
ON CREATE SET s.name=$name, s.exchange=$exchange, s.board=$board,
              s.scarcity=$scarcity, s.rating=$rating, s.active=$active
ON MATCH SET  s.rating=$rating, s.active=$active
WITH s
MATCH (sub:SubSector {id: $sub_id})
MERGE (s)-[:BELONGS_TO]->(sub)
"""

_MERGE_CONCEPT = """
MERGE (c:Concept {id: $id})
ON CREATE SET c.name=$name, c.description=$description, c.theme=$theme
"""

_MERGE_EXPOSED_TO = """
MATCH (s:Stock {code: $code})
MATCH (c:Concept {id: $concept_id})
MERGE (s)-[r:EXPOSED_TO]->(c)
ON CREATE SET r.as_of = date()
"""


def run_seed(
    session: Session,
    stocks: list[StockSeedRow],
    concepts: list[ConceptSeedRow],
) -> None:
    seen_sectors: set[str] = set()
    seen_subs: set[str] = set()
    for s in stocks:
        if s.sector_id not in seen_sectors:
            session.run(_MERGE_SECTOR, sector_id=s.sector_id, sector_name=s.sector_name)
            seen_sectors.add(s.sector_id)
        if s.sub_sector_id not in seen_subs:
            session.run(
                _MERGE_SUBSECTOR,
                sub_id=s.sub_sector_id,
                sub_name=s.sub_sector_name,
                sector_id=s.sector_id,
            )
            seen_subs.add(s.sub_sector_id)
    for s in stocks:
        session.run(
            _MERGE_STOCK,
            code=s.code,
            name=s.name,
            exchange=s.exchange,
            board=s.board,
            scarcity=s.scarcity,
            rating=s.rating,
            active=s.active,
            sub_id=s.sub_sector_id,
        )
    for c in concepts:
        session.run(_MERGE_CONCEPT, id=c.id, name=c.name, description=c.description, theme=c.theme)
    for s in stocks:
        for concept_id in s.exposed_concepts:
            session.run(_MERGE_EXPOSED_TO, code=s.code, concept_id=concept_id)


def load_concepts_yaml(path: Path) -> list[ConceptSeedRow]:
    import yaml  # lazy: pyyaml only needed for seed scripts

    data = yaml.safe_load(path.read_text())
    return [ConceptSeedRow(**c) for c in data["concepts"]]
