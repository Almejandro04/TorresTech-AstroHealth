"""Local atomic mission import; no simulation clock or analysis engine."""

import csv
import json
import math
import re
from contextlib import closing
from pathlib import Path

from pydantic import ValidationError

from app.config import SchemaVersion, database_path
from app.database import repository as repo
from app.database.connection import connect, init_schema, transaction
from app.models.fields import Identifier, parse_timestamp
from app.models.schemas import (Astronaut, ContractModel, HealthJournalInput,
                               HealthReadingInput, SourceManifestEntry)
from app.models.validation import RecordValidationError, AstronautNotFoundError


class ImportReading(HealthReadingInput):
    astronaut_id: Identifier


class ImportJournal(HealthJournalInput):
    astronaut_id: Identifier


class Bundle(ContractModel):
    schema_version: SchemaVersion
    source: SourceManifestEntry
    astronauts: list[Astronaut]
    readings: list[ImportReading]
    journal: list[ImportJournal]


class ImportFailure(ValueError):
    """Location-rich error; no import writes are committed."""


def _json(path: Path):
    def decimal(text):
        value = float(text)
        if not math.isfinite(value):
            raise ImportFailure(f"{path}: non-finite JSON number {text}")
        return value

    def constant(text):
        raise ImportFailure(f"{path}: invalid JSON constant {text}")

    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ImportFailure(f"{path}: duplicate JSON field {key}")
            result[key] = value
        return result
    return json.loads(path.read_text(encoding="utf-8-sig"), object_pairs_hook=pairs,
                      parse_float=decimal, parse_constant=constant)


def _csv(path: Path, model: type, locations: dict, kind: str) -> list[dict]:
    headers = set(model.model_fields)
    nullable = {"heart_rate_bpm", "spo2_percent", "respiratory_rate_bpm",
                "sleep_hours_last_night", "mood_score", "notes"}
    integers = {"mission_day", "mood_score"}
    numbers = nullable - {"notes"} - integers
    output = []
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.reader(handle, strict=True)
        header = next(reader, [])
        if len(header) != len(set(header)) or set(header) != headers:
            raise ImportFailure(f"{path}: row 1: headers must be exactly {sorted(headers)}")
        for cells in reader:
            row_number = reader.line_num
            if len(cells) != len(header):
                raise ImportFailure(f"{path}: row {row_number}: wrong column count")
            record = dict(zip(header, cells))
            for field, text in record.items():
                try:
                    if text == "" and field in nullable:
                        record[field] = None
                    elif field in integers:
                        if not re.fullmatch(r"[+-]?[0-9]+", text):
                            raise ValueError("expected integer")
                        record[field] = int(text)
                    elif field in numbers:
                        record[field] = float(text)
                except ValueError as error:
                    raise ImportFailure(f"{path}: row {row_number}: {field}: {error}") from error
            locations[f"{kind}[{len(output)}]"] = f"{path}: row {row_number}"
            output.append(record)
    return output


def load_bundle(path: Path, readings: str | None = None, journal: str | None = None):
    locations = {}
    raw = _json(path)
    if readings is not None or journal is not None:
        if readings is None or journal is None:
            raise ImportFailure("Both --readings and --journal are required")
        if not isinstance(raw, dict) or not {"schema_version", "source", "astronauts"} <= raw.keys() or raw.keys() - set(Bundle.model_fields):
            raise ImportFailure(f"{path}: invalid CSV manifest fields")
        # Metadata only: choosing CSV NEVER loads observations from JSON.
        raw = {k: raw[k] for k in ("schema_version", "source", "astronauts")}
        raw["readings"] = _csv(path.parent / readings, ImportReading, locations, "readings")
        raw["journal"] = _csv(path.parent / journal, ImportJournal, locations, "journal")
    try:
        return Bundle.model_validate(raw), locations
    except ValidationError as error:
        messages = []
        for item in error.errors():
            parts = item["loc"] or ("bundle",)
            key = f"{parts[0]}[{parts[1]}]" if len(parts) > 1 else str(parts[0])
            messages.append(f"{locations.get(key, str(path) + ': ' + key)}: {'.'.join(map(str, parts))}: {item['msg']}")
        raise ImportFailure("; ".join(messages)) from error


def _apply(conn, bundle: Bundle, until_day: int | None, update_journal: bool, locations: dict):
    stats = {name: dict(created=0, repeated=0, updated=0) for name in ("sources", "astronauts", "readings", "journal")}
    source = bundle.source
    stored = conn.execute("SELECT manifest_json FROM sources WHERE source_id=?", (source.source_id,)).fetchone()
    if stored and json.loads(stored[0]) != source.model_dump():
        raise ImportFailure("source: metadata conflict with stored manifest")
    if stored:
        stats["sources"]["repeated"] += 1
    else:
        repo.save_source(conn, source)
        stats["sources"]["created"] += 1
    for index, astronaut in enumerate(bundle.astronauts):
        existing = repo.get_astronaut(conn, astronaut.astronaut_id)
        if existing and existing != astronaut:
            raise ImportFailure(f"astronauts[{index}]: metadata conflict")
        if existing:
            stats["astronauts"]["repeated"] += 1
        else:
            repo.save_astronaut(conn, astronaut)
            stats["astronauts"]["created"] += 1
    seen = {}
    for kind, records, model in (("readings", bundle.readings, HealthReadingInput),
                                  ("journal", bundle.journal, HealthJournalInput)):
        for index, record in enumerate(records):
            where = f"{kind}[{index}]"
            try:
                if until_day is not None and record.mission_day > until_day:
                    continue
                payload = model.model_validate(record.model_dump(exclude={"astronaut_id"}))
                if kind == "readings":
                    result = repo.create_reading(conn, record.astronaut_id, payload, field_prefix=where)
                    if result.status == "conflict":
                        raise ImportFailure("reading key conflicts with different values/provenance")
                    status = "repeated" if result.status == "existing" else "created"
                else:
                    key = (record.astronaut_id, record.mission_day)
                    if key in seen and seen[key] != payload:
                        raise ImportFailure("conflicting journal duplicates inside input")
                    seen[key] = payload
                    existing = next((j for j in repo.list_journal(conn, record.astronaut_id) if j.mission_day == record.mission_day), None)
                    if existing and existing.model_dump(exclude={"journal_id", "astronaut_id"}) == payload.model_dump():
                        status = "repeated"
                    else:
                        if existing and not update_journal:
                            raise ImportFailure("journal differs from stored entry; use --update-journal deliberately")
                        result = repo.upsert_journal(conn, record.astronaut_id, payload, field_prefix=where)
                        status = result.status
                stats[kind][status] += 1
            except (RecordValidationError, AstronautNotFoundError, ImportFailure) as error:
                raise ImportFailure(f"{locations.get(where, where)}: {error}") from error
    return stats


class _ValidationOnly(Exception):
    pass


def import_mission(path: Path, *, readings: str | None = None, journal: str | None = None,
                   until_day: int | None = None, update_journal: bool = False) -> dict:
    path = path.resolve()
    bundle, locations = load_bundle(path, readings, journal)
    if until_day is not None and (type(until_day) is not int or until_day < 1 or
            not bundle.astronauts or any(until_day > a.planned_duration_days for a in bundle.astronauts)):
        raise ImportFailure("until_day must be within every declared profile's mission")
    with closing(connect()) as conn:
        init_schema(conn)  # Deliberately outside the import transaction.
        with transaction(conn):
            # Validate the ENTIRE input against the current database under one
            # write lock. Nested repository writes join savepoints; none commit.
            try:
                with transaction(conn):
                    _apply(conn, bundle, None, update_journal, locations)
                    raise _ValidationOnly
            except _ValidationOnly:
                pass
            stats = _apply(conn, bundle, until_day, update_journal, locations)
            cutoffs = {}
            latest_stored_cutoffs = {}
            later = []
            profile_ids = sorted({a.astronaut_id for a in bundle.astronauts} |
                                 {r.astronaut_id for r in (*bundle.readings, *bundle.journal)})
            for profile_id in profile_ids:
                records = repo.list_readings(conn, profile_id) + repo.list_journal(conn, profile_id)
                latest_stored_cutoffs[profile_id] = max((r.timestamp for r in records), key=parse_timestamp, default=None)
                visible = [r for r in records if until_day is None or r.mission_day <= until_day]
                cutoffs[profile_id] = max((r.timestamp for r in visible), key=parse_timestamp, default=None)
                if until_day and any(r.mission_day > until_day for r in records):
                    later.append(profile_id)
            days = [r.mission_day for r in (*bundle.readings, *bundle.journal) if until_day is None or r.mission_day <= until_day]
    # Confirmed import event for a future #14/#15 caller. No callback is run:
    # consumers can reevaluate the selected replay view at cutoffs after commit.
    # Later stored data stays intact and is reported separately; it must not
    # leak into a historical analysis through this handoff.
    return dict(committed=True, input=str(path), destination=str(database_path().resolve()),
                schema_version=bundle.schema_version, format="csv" if readings is not None else "json",
                requested_day=until_day, selected_day_range=[min(days), max(days)] if days else None,
                records=stats, rejected=0, profiles_with_later_data=later,
                warning="Later observations remain stored; use post_import.cutoffs as as_of for this replay view." if later else None,
                post_import=dict(profiles=list(cutoffs), cutoffs=cutoffs,
                                 latest_stored_cutoffs=latest_stored_cutoffs,
                                 evaluation_status="not_implemented"))
