"""Shared backend configuration: contract version and local file locations."""

import os
from pathlib import Path
from typing import Literal, get_args

# The contract version is written once, here. Models use the type; code uses
# the value.
SchemaVersion = Literal["0.1.0"]
SCHEMA_VERSION: SchemaVersion = get_args(SchemaVersion)[0]

BACKEND_DIR = Path(__file__).resolve().parents[1]

DB_PATH_ENV = "ASTROHEALTH_DB_PATH"
DEFAULT_DB_PATH = BACKEND_DIR / "astrohealth.db"

SEED_PATH = BACKEND_DIR.parent / "docs" / "examples" / "mission_seed.json"


def database_path() -> Path:
    """Return the configured SQLite file; unset or blank uses the default.

    A relative value is resolved against the current working directory.
    """
    raw = os.environ.get(DB_PATH_ENV, "").strip()
    return Path(raw) if raw else DEFAULT_DB_PATH
