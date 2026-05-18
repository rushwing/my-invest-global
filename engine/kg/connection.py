from __future__ import annotations

from neo4j import Driver, GraphDatabase
from pydantic_settings import BaseSettings


class KGSettings(BaseSettings):
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "invest_local"

    model_config = {"env_file": ".env", "extra": "ignore"}


class KGConnection:
    def __init__(self, settings: KGSettings | None = None) -> None:
        self._settings = settings or KGSettings()
        self._driver: Driver | None = None

    def driver(self) -> Driver:
        if self._driver is None:
            self._driver = GraphDatabase.driver(
                self._settings.neo4j_uri,
                auth=(self._settings.neo4j_user, self._settings.neo4j_password),
            )
        return self._driver

    def ping(self) -> bool:
        try:
            self.driver().verify_connectivity()
            return True
        except Exception:
            return False

    def close(self) -> None:
        if self._driver:
            self._driver.close()
            self._driver = None

    def __enter__(self) -> KGConnection:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()
