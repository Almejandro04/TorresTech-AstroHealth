"""Demo seed and deterministic reset from docs/examples/mission_seed.json.

CSV import, replay, and generated datasets are out of scope here.
"""

import json
import sqlite3
from contextlib import closing
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ValidationError

from app.config import SCHEMA_VERSION, SEED_PATH, database_path
from app.database import repository
from app.database.connection import connect, init_schema, transaction
from app.models.schemas import (
    Astronaut,
    HealthJournalInput,
    HealthReadingInput,
    SourceManifestEntry,
)
from app.models.validation import (
    AstronautNotFoundError,
    RecordValidationError,
    issues_from_pydantic,
)

_SEED_KEYS = {"schema_version", "source", "astronauts", "readings", "journal"}


def _fail(field: str, message: str) -> RecordValidationError:
    return RecordValidationError([{"field": field, "message": message}])


def _parse(model: type[BaseModel], data: Any, where: str) -> Any:
    try:
        return model.model_validate(data)
    except ValidationError as error:
        raise RecordValidationError(issues_from_pydantic(error, where)) from None


def _split_astronaut_id(record: Any, where: str) -> tuple[str, dict[str, Any]]:
    """Import records are the Input fields plus `astronaut_id`."""
    if not isinstance(record, dict):
        raise _fail(where, "Must be an object.")
    fields = dict(record)
    astronaut_id = fields.pop("astronaut_id", None)
    if not isinstance(astronaut_id, str):
        raise _fail(f"{where}.astronaut_id", "Is required.")
    return astronaut_id, fields


def seed_database(conn: sqlite3.Connection, seed_path: Path = SEED_PATH) -> dict[str, int]:
    """Load the seed bundle with the normal validations, all or nothing.

    Running it again on a seeded database changes nothing: identical readings
    are recognised and each journal day is rewritten with the same values.
    """
    bundle = json.loads(Path(seed_path).read_text(encoding="utf-8"))
    if not isinstance(bundle, dict) or set(bundle) != _SEED_KEYS:
        raise _fail("seed", f"Must contain exactly: {', '.join(sorted(_SEED_KEYS))}.")
    if bundle["schema_version"] != SCHEMA_VERSION:
        raise _fail("seed.schema_version", f"Must be {SCHEMA_VERSION}.")

    with transaction(conn):
        repository.save_source(conn, _parse(SourceManifestEntry, bundle["source"], "source"))

        for index, item in enumerate(bundle["astronauts"]):
            repository.save_astronaut(conn, _parse(Astronaut, item, f"astronauts[{index}]"))

        for index, item in enumerate(bundle["readings"]):
            where = f"readings[{index}]"
            astronaut_id, fields = _split_astronaut_id(item, where)
            payload = _parse(HealthReadingInput, fields, where)
            try:
                result = repository.create_reading(
                    conn, astronaut_id, payload, field_prefix=where
                )
            except AstronautNotFoundError:
                raise _fail(f"{where}.astronaut_id", "Is not a known astronaut.") from None
            if result.status == "conflict":
                raise _fail(where, "Conflicts with a stored reading for the same key.")

        for index, item in enumerate(bundle["journal"]):
            where = f"journal[{index}]"
            astronaut_id, fields = _split_astronaut_id(item, where)
            payload = _parse(HealthJournalInput, fields, where)
            try:
                repository.upsert_journal(conn, astronaut_id, payload, field_prefix=where)
            except AstronautNotFoundError:
                raise _fail(f"{where}.astronaut_id", "Is not a known astronaut.") from None

    return repository.count_records(conn)


def init_database(path: Path | None = None) -> dict[str, int]:
    """Create the schema in the configured database if it is missing."""
    with closing(connect(path)) as conn:
        init_schema(conn)
        return repository.count_records(conn)


def seed_configured_database(
    path: Path | None = None, seed_path: Path = SEED_PATH
) -> dict[str, int]:
    """Create the schema if needed, then load the seed."""
    with closing(connect(path)) as conn:
        init_schema(conn)
        return seed_database(conn, seed_path)


def reset_database(path: Path | None = None, seed_path: Path = SEED_PATH) -> dict[str, int]:
    """Prepare and atomically publish a validated demo with all clients stopped.

    The result is always the same rows with the same IDs.
    """
    from app.database.reset import replace_demo

    target = Path(path) if path is not None else database_path()
    return replace_demo(target, lambda staged: seed_configured_database(staged, seed_path))
