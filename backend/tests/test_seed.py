"""BACKEND-02 checks: demo seed, deterministic reset, and the command line."""

import json
import sqlite3
from contextlib import closing
from pathlib import Path

import pytest

from app.config import DB_PATH_ENV, SEED_PATH
from app.database import (
    connect,
    count_records,
    init_database,
    init_schema,
    list_alerts,
    list_astronauts,
    list_journal,
    list_readings,
    reset_database,
    seed_database,
)
from app.database.__main__ import main
from app.models import RecordValidationError

from conftest import api_case

SEEDED = {"sources": 1, "astronauts": 2, "readings": 7, "journal": 7, "alerts": 0}


def snapshot(path: Path) -> dict:
    """Every stored row of every table, in a comparable form."""
    with closing(connect(path)) as raw:
        raw.row_factory = sqlite3.Row
        return {
            table: [dict(row) for row in raw.execute(f"SELECT * FROM {table} ORDER BY 1")]
            for table in ("sources", "astronauts", "readings", "journal", "alerts")
        }


def broken_seed(tmp_path: Path, change) -> Path:
    bundle = json.loads(SEED_PATH.read_text(encoding="utf-8"))
    change(bundle)
    path = tmp_path / "broken_seed.json"
    path.write_text(json.dumps(bundle), encoding="utf-8")
    return path


def test_init_creates_an_empty_database(db_path: Path) -> None:
    assert not db_path.exists()
    assert init_database(db_path) == dict.fromkeys(SEEDED, 0)
    assert db_path.exists()
    assert init_database(db_path) == dict.fromkeys(SEEDED, 0)


def test_seed_loads_the_shared_fixture(db_path: Path) -> None:
    with closing(connect(db_path)) as conn:
        init_schema(conn)
        assert seed_database(conn) == SEEDED

        profiles = api_case("fictional_profiles")["response"]["body"]["data"]
        assert [a.model_dump() for a in list_astronauts(conn)] == profiles

        readings = list_readings(conn, "AST-001")
        journal = list_journal(conn, "AST-001")
        assert [r.reading_id for r in readings] == [f"READING-000{n}" for n in range(1, 8)]
        assert [j.journal_id for j in journal] == [f"JOURNAL-000{n}" for n in range(1, 8)]
        assert [r.mission_day for r in readings] == [j.mission_day for j in journal] == list(range(1, 8))
        assert readings[6].respiratory_rate_bpm is None

        expected_readings = api_case("readings_history_with_null_metric")["response"]["body"]["data"]
        expected_journal = api_case("journal_history_for_sleep_chart")["response"]["body"]["data"]
        assert [r.model_dump() for r in readings[5:]] == expected_readings
        assert [j.model_dump() for j in journal[5:]] == expected_journal

        assert list_readings(conn, "AST-002") == []
        assert list_journal(conn, "AST-002") == []
        assert list_alerts(conn, "AST-001") == []

        manifest = json.loads(conn.execute("SELECT manifest_json FROM sources").fetchone()[0])
        assert manifest == json.loads(SEED_PATH.read_text(encoding="utf-8"))["source"]


def test_seed_is_idempotent(db_path: Path) -> None:
    with closing(connect(db_path)) as conn:
        init_schema(conn)
        seed_database(conn)
    first = snapshot(db_path)

    with closing(connect(db_path)) as conn:
        assert seed_database(conn) == SEEDED
        assert seed_database(conn) == SEEDED
    assert snapshot(db_path) == first


@pytest.mark.parametrize(
    ("change", "field"),
    [
        (lambda b: b["readings"][6].update(spo2_percent=101), "readings[6].spo2_percent"),
        (lambda b: b["readings"][6].update(mission_day=6), "readings[6].mission_day"),
        (lambda b: b["readings"][6].update(source_id="SYN-NOPE"), "readings[6].source_id"),
        (lambda b: b["readings"][6].update(astronaut_id="AST-999"), "readings[6].astronaut_id"),
        (lambda b: b["readings"][6].update(heart_rate_bpm="84"), "readings[6].heart_rate_bpm"),
        (lambda b: b["readings"].append({**b["readings"][0], "heart_rate_bpm": 99}), "readings[7]"),
        (lambda b: b["journal"][6].update(mood_score=6), "journal[6].mood_score"),
        (lambda b: b["journal"][6].pop("notes"), "journal[6].notes"),
        (lambda b: b["astronauts"][1].update(is_fictional=False), "astronauts[1].is_fictional"),
        (lambda b: b.update(schema_version="9.9.9"), "seed.schema_version"),
        (lambda b: b.update(extra=[]), "seed"),
    ],
)
def test_invalid_seed_commits_nothing(tmp_path: Path, db_path: Path, change, field: str) -> None:
    with closing(connect(db_path)) as conn:
        init_schema(conn)
        with pytest.raises(RecordValidationError) as caught:
            seed_database(conn, broken_seed(tmp_path, change))

        assert [detail["field"] for detail in caught.value.details] == [field]
        assert count_records(conn) == dict.fromkeys(SEEDED, 0)
        assert not conn.in_transaction
        assert seed_database(conn) == SEEDED


def test_invalid_seed_keeps_previously_seeded_data(tmp_path: Path, db_path: Path) -> None:
    reset_database(db_path)
    before = snapshot(db_path)
    bad = broken_seed(tmp_path, lambda b: b["journal"][6].update(sleep_hours_last_night=30))

    with closing(connect(db_path)) as conn, pytest.raises(RecordValidationError):
        seed_database(conn, bad)
    assert snapshot(db_path) == before


def test_reset_is_deterministic(db_path: Path) -> None:
    assert reset_database(db_path) == SEEDED
    first = snapshot(db_path)

    # Change the database so that a reset has something to undo.
    with closing(connect(db_path)) as conn:
        conn.execute("DELETE FROM readings WHERE seq = 3")
        conn.execute("UPDATE journal SET sleep_hours_last_night = 1 WHERE seq = 2")
        conn.execute(
            "INSERT INTO readings (astronaut_id, timestamp, mission_day, heart_rate_bpm,"
            " measurement_context, source_type, source_id)"
            " VALUES ('AST-002', '2026-11-09T12:00:00.000000Z', 9, 70, 'rest', 'synthetic', 'SYN-CORE-001')"
        )
    assert snapshot(db_path) != first

    assert reset_database(db_path) == SEEDED
    assert snapshot(db_path) == first
    assert reset_database(db_path) == SEEDED
    assert snapshot(db_path) == first


def test_reset_refuses_side_files_without_changing_anything(tmp_path: Path, db_path: Path) -> None:
    reset_database(db_path)
    neighbour = tmp_path / "keep.txt"
    neighbour.write_text("keep", encoding="utf-8")
    stale = Path(f"{db_path}-wal")
    stale.write_bytes(b"stale")

    before = db_path.read_bytes()
    with pytest.raises(ValueError, match="sidecars"):
        reset_database(db_path)
    assert db_path.read_bytes() == before
    assert neighbour.read_text(encoding="utf-8") == "keep"
    assert stale.read_bytes() == b"stale"


def test_reset_refuses_to_delete_a_file_that_is_not_sqlite(tmp_path: Path) -> None:
    notes = tmp_path / "notes.db"
    notes.write_text("these are my notes, not a database", encoding="utf-8")

    with pytest.raises(ValueError):
        reset_database(notes)
    assert notes.read_text(encoding="utf-8") == "these are my notes, not a database"


def test_command_line_uses_the_configured_path(tmp_path: Path, monkeypatch, capsys) -> None:
    target = tmp_path / "nested" / "cli.db"
    monkeypatch.setenv(DB_PATH_ENV, str(target))

    assert main(["init"]) == 0
    assert "sources=0, astronauts=0, readings=0, journal=0, alerts=0" in capsys.readouterr().out
    assert main(["seed"]) == 0
    assert "astronauts=2, readings=7, journal=7" in capsys.readouterr().out
    assert main(["reset"]) == 0
    output = capsys.readouterr().out
    assert str(target) in output and "readings=7" in output

    target.write_text("not a database", encoding="utf-8")
    assert main(["reset"]) == 1
    assert "Not a SQLite database" in capsys.readouterr().err
    assert target.read_text(encoding="utf-8") == "not a database"


@pytest.mark.parametrize("content", [b"", b"SQLite format 3\x00not a database", b"unknown"])
def test_reset_rejects_unknown_files_unchanged(db_path: Path, content: bytes) -> None:
    db_path.write_bytes(content)
    with pytest.raises(ValueError):
        reset_database(db_path)
    assert db_path.read_bytes() == content


def test_reset_rejects_foreign_sqlite(db_path: Path) -> None:
    with closing(sqlite3.connect(db_path)) as foreign:
        foreign.execute("CREATE TABLE personal_notes (note TEXT)")
        foreign.execute("INSERT INTO personal_notes VALUES ('keep me')")
        foreign.commit()
    before = db_path.read_bytes()
    with pytest.raises(ValueError, match="AstroHealth"):
        reset_database(db_path)
    assert db_path.read_bytes() == before


def test_reset_invalid_seed_preserves_existing_database(tmp_path: Path, db_path: Path) -> None:
    reset_database(db_path)
    before = db_path.read_bytes()
    bad = broken_seed(tmp_path, lambda b: b["journal"][6].update(mood_score=99))
    with pytest.raises(RecordValidationError):
        reset_database(db_path, bad)
    assert db_path.read_bytes() == before
    assert not list(tmp_path.glob(".test.db.reset-*"))


def test_reset_preparation_failure_preserves_database(db_path: Path, monkeypatch) -> None:
    import app.database.seed as seed_module

    reset_database(db_path)
    before = db_path.read_bytes()
    def failed_preparation(*args):
        raise OSError("simulated disk failure")
    monkeypatch.setattr(seed_module, "seed_configured_database", failed_preparation)
    with pytest.raises(OSError, match="disk failure"):
        reset_database(db_path)
    assert db_path.read_bytes() == before
    assert not list(db_path.parent.glob(".test.db.reset-*"))


@pytest.mark.parametrize("suffix", ["-wal", "-shm", "-journal"])
def test_reset_preserves_orphan_sidecars(db_path: Path, suffix: str) -> None:
    side = Path(f"{db_path}{suffix}")
    side.write_bytes(b"unknown owner")
    with pytest.raises(ValueError, match="sidecars"):
        reset_database(db_path)
    assert not db_path.exists()
    assert side.read_bytes() == b"unknown owner"


def test_reset_rejects_hardlinks(tmp_path: Path, db_path: Path) -> None:
    import os

    reset_database(db_path)
    alias = tmp_path / "alias.db"
    os.link(db_path, alias)
    before = db_path.read_bytes()
    with pytest.raises(ValueError, match="hard link"):
        reset_database(alias)
    assert db_path.read_bytes() == alias.read_bytes() == before


def test_reset_rejects_ambiguous_path(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="unambiguous"):
        reset_database(tmp_path / "nested" / ".." / "test.db")


def test_reset_rechecks_target_after_preparation(db_path: Path, monkeypatch) -> None:
    import app.database.seed as seed_module

    reset_database(db_path)
    original = seed_module.seed_configured_database
    def prepare_then_change_target(path, seed_path):
        counts = original(path, seed_path)
        db_path.write_bytes(b"concurrent replacement: preserve this")
        return counts
    monkeypatch.setattr(seed_module, "seed_configured_database", prepare_then_change_target)
    with pytest.raises(ValueError, match="identity changed"):
        reset_database(db_path)
    assert db_path.read_bytes() == b"concurrent replacement: preserve this"


def test_reset_refuses_active_database_handle(db_path: Path) -> None:
    reset_database(db_path)
    before = db_path.read_bytes()
    with closing(connect(db_path)) as active:
        active.execute("BEGIN EXCLUSIVE")
        with pytest.raises((OSError, sqlite3.OperationalError)):
            reset_database(db_path)
        active.execute("ROLLBACK")
    assert db_path.read_bytes() == before


def test_reset_replace_failure_preserves_database(db_path: Path, monkeypatch) -> None:
    import app.database.reset as reset_module

    reset_database(db_path)
    before = db_path.read_bytes()
    def fail_replace(*args):
        raise OSError("simulated replacement failure")
    monkeypatch.setattr(reset_module.os, "replace", fail_replace)
    with pytest.raises(OSError, match="replacement failure"):
        reset_database(db_path)
    assert db_path.read_bytes() == before


def test_reset_rejects_foreign_database_with_copied_marker(db_path: Path) -> None:
    from app.database.connection import APPLICATION_ID

    with closing(sqlite3.connect(db_path)) as foreign:
        foreign.execute("CREATE TABLE private_data (note TEXT)")
        foreign.execute(f"PRAGMA application_id = {APPLICATION_ID}")
    before = db_path.read_bytes()
    with pytest.raises(ValueError, match="AstroHealth"):
        reset_database(db_path)
    assert db_path.read_bytes() == before


@pytest.mark.parametrize("parent_link", [False, True])
def test_reset_rejects_reparse_points_before_preparation(db_path: Path, monkeypatch, parent_link: bool) -> None:
    from types import SimpleNamespace
    import app.database.reset as reset_module

    reset_database(db_path)
    before = db_path.read_bytes()
    original = Path.lstat
    link = db_path.parent if parent_link else db_path
    def linked_stat(path, *args, **kwargs):
        info = original(path, *args, **kwargs)
        if path == link:
            return SimpleNamespace(st_mode=info.st_mode, st_file_attributes=0x400)
        return info
    monkeypatch.setattr(Path, "lstat", linked_stat)
    with pytest.raises(ValueError, match="reparse"):
        reset_module.replace_demo(db_path, lambda _: pytest.fail("must reject before preparing"))
    assert db_path.read_bytes() == before
