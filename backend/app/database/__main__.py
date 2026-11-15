"""Command line: `python -m app.database init|seed|reset` (from `backend`)."""

import argparse
import sys

from app.config import DB_PATH_ENV, database_path
from app.database.seed import init_database, reset_database, seed_configured_database
from app.models.validation import RecordValidationError

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
        choices=sorted(ACTIONS),
        help="init: create the schema; seed: load the demo data; "
        "reset: prepare and atomically replace an owned database (all clients stopped)",
    )
    action = parser.parse_args(argv).action

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
