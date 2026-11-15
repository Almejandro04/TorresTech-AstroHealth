"""Shared fixtures. Every database lives under pytest's tmp_path."""

import json
import sqlite3
from collections.abc import Iterator
from contextlib import closing
from pathlib import Path

import pytest

from app.config import DB_PATH_ENV
from app.database import connect, init_schema, save_astronaut, save_source
from app.models import Astronaut, SourceManifestEntry

REPO_ROOT = Path(__file__).resolve().parents[2]
EXAMPLES = REPO_ROOT / "docs" / "examples"

SOURCE_ID = "SYN-CORE-001"


def api_case(name: str) -> dict:
    cases = json.loads((EXAMPLES / "api_examples.json").read_text(encoding="utf-8"))["cases"]
    return next(case for case in cases if case["name"] == name)


def reading_body(**changes) -> dict:
    return {**api_case("reading_created")["request"]["body"], **changes}


def journal_body(**changes) -> dict:
    return {**api_case("journal_created")["request"]["body"], **changes}


def alert_record(**changes) -> dict:
    """The fixture alert without its fixture-assigned ID."""
    alert = dict(api_case("explainable_synthetic_alert")["response"]["body"]["data"][0])
    del alert["alert_id"]
    return {**alert, **changes}


@pytest.fixture(autouse=True)
def _never_use_the_real_database(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv(DB_PATH_ENV, str(tmp_path / "configured.db"))


@pytest.fixture
def db_path(tmp_path: Path) -> Path:
    return tmp_path / "test.db"


@pytest.fixture
def conn(db_path: Path) -> Iterator[sqlite3.Connection]:
    """An initialized database with the fixture source and both profiles."""
    with closing(connect(db_path)) as connection:
        init_schema(connection)
        save_source(
            connection,
            SourceManifestEntry(source_id=SOURCE_ID, source_type="synthetic"),
        )
        for astronaut_id in ("AST-001", "AST-002"):
            save_astronaut(
                connection,
                Astronaut(
                    astronaut_id=astronaut_id,
                    name=f"Demo {astronaut_id}",
                    is_fictional=True,
                    mission_start_date="2026-11-01",
                    planned_duration_days=30,
                ),
            )
        yield connection
