"""Command line: `python -m app.database init|seed|reset` (from `backend`)."""

import argparse
import sys
import csv
import json
import sqlite3
from pathlib import Path

from app.config import DB_PATH_ENV, SCHEMA_VERSION, database_path
from app.database.seed import init_database, reset_database, seed_configured_database
from app.models.validation import RecordValidationError
from app.database.ingestion import import_mission

ACTIONS = {
    "init": init_database,
    "seed": seed_configured_database,
    "reset": reset_database,
}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m app.database",
        description=f"Manage the local SQLite database selected by {DB_PATH_ENV}.",
    )
    parser.add_argument(
        "action",
        choices=sorted([*ACTIONS, "import-json", "import-csv"]),
        help="init: create the schema; seed: load the demo data; "
        "reset: prepare and atomically replace an owned database (all clients stopped)",
    )
    parser.add_argument("input", nargs="?", type=Path)
    parser.add_argument("--readings")
    parser.add_argument("--journal")
    parser.add_argument("--until-day", type=int)
    parser.add_argument("--update-journal", action="store_true")
    args = parser.parse_args(argv)
    action = args.action
    if action.startswith("import-"):
        if args.input is None:
            parser.error("import requires an input file")
        if action == "import-json" and (args.readings is not None or args.journal is not None):
            parser.error("CSV flags require import-csv")
        if action == "import-csv" and (args.readings is None or args.journal is None):
            parser.error("import-csv requires --readings and --journal")
        try:
            report = import_mission(args.input, readings=args.readings, journal=args.journal,
                                    until_day=args.until_day, update_journal=args.update_journal)
        except (OSError, ValueError, sqlite3.Error, csv.Error) as error:
            print(json.dumps(dict(committed=False, input=str(args.input.resolve()),
                destination=str(database_path().resolve()), schema_version=SCHEMA_VERSION,
                format="csv" if action == "import-csv" else "json", requested_day=args.until_day,
                created=0, repeated=0, updated=0, rejected=1, rejected_unit="bundle",
                rejected_records=None,
                error=str(error), message="Import rolled back; no rows from this attempt committed.")), file=sys.stderr)
            return 1
        print(json.dumps(report))
        return 0
    if args.input is not None or args.readings is not None or args.journal is not None or args.until_day is not None or args.update_journal:
        parser.error("import options cannot be used with init/seed/reset")

    path = database_path()
    try:
        counts = ACTIONS[action](path)
    except RecordValidationError as error:
        print(f"{action} failed; existing database content was preserved:", file=sys.stderr)
        for detail in error.details:
            print(f"  {detail['field']}: {detail['message']}", file=sys.stderr)
        return 1
    except (OSError, ValueError) as error:
        print(f"{action} failed: {error}", file=sys.stderr)
        return 1

    summary = ", ".join(f"{table}={count}" for table, count in counts.items())
    print(f"{action} completed: {path.resolve()}")
    print(summary)
    return 0


if __name__ == "__main__":
    sys.exit(main())
