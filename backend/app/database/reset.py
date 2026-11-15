"""Offline demo replacement: validate ownership, prepare, then publish once.

This is a maintenance operation in a directory controlled by the operator.
All service/CLI connections must be closed first. Sidecars are never deleted.
"""

import hashlib
import os
import sqlite3
import stat
import tempfile
from contextlib import closing, contextmanager
from pathlib import Path

from app.database.connection import APPLICATION_ID, expected_schema, schema_signature
from app.models.fields import compare_timestamps


def _safe_path(path: Path) -> Path:
    if ".." in path.parts or (path.drive and not path.is_absolute()):
        raise ValueError(
            "Reset needs an unambiguous local file path (no '..').")
    target = path.absolute()
    if target.anchor.startswith("\\\\"):
        raise ValueError("Reset does not support network paths.")
    for part in target.parts[1:]:
        if part != part.rstrip(" .") or (os.name == "nt" and (
            ":" in part or os.path.isreserved(part)
        )):
            raise ValueError(
                "Reset refuses ambiguous or reserved path components.")
    for component in (*reversed(target.parents), target):
        try:
            info = component.lstat()
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
            raise ValueError(
                "Reset refuses links, junctions, and reparse points.")
        if component == target and (not stat.S_ISREG(info.st_mode) or info.st_nlink != 1):
            raise ValueError(
                "Reset needs a regular file with exactly one hard link.")
    return target


def _no_sidecars(target: Path) -> None:
    for suffix in ("-journal", "-wal", "-shm"):
        if os.path.lexists(f"{target}{suffix}"):
            raise ValueError(
                "Reset refuses SQLite sidecars; stop all clients and close/checkpoint SQLite first.")


def _identity(target: Path) -> tuple | None:
    try:
        info = target.lstat()
    except FileNotFoundError:
        return None
    return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns,
            info.st_ctime_ns, info.st_nlink)


def _parents(target: Path) -> list[tuple]:
    return [(p, p.stat().st_dev, p.stat().st_ino) for p in target.parents]


def _validate_owned(target: Path) -> None:
    if target.stat().st_size == 0:
        raise ValueError(
            "Empty file is not an identified AstroHealth SQLite database.")
    # immutable prevents read-only inspection from creating/recovering sidecars.
    try:
        with closing(sqlite3.connect(target.as_uri() + "?mode=ro&immutable=1", uri=True)) as conn:
            conn.create_collation("ASTROHEALTH_TIMESTAMP", compare_timestamps)
            if (conn.execute("PRAGMA application_id").fetchone()[0] != APPLICATION_ID
                    or schema_signature(conn) != expected_schema()
                    or conn.execute("PRAGMA quick_check").fetchall() != [("ok",)]
                    or conn.execute("PRAGMA foreign_key_check").fetchall()):
                raise ValueError(
                    "Not an identified, intact AstroHealth SQLite database.")
    except sqlite3.Error as error:
        raise ValueError(
            "Not a SQLite database owned by AstroHealth, or database is damaged.") from error


@contextmanager
def _exclusive_file(target: Path):
    """Reject active handles on Windows; reject SQLite locks on other hosts.

    Windows holds DELETE access and shares reading/deletion for atomic replace.
    SQLite handles do not share deletion, so active/new SQLite clients conflict;
    writers are also denied while the validated file handle is held.
    """
    if os.name == "nt":
        import ctypes
        import msvcrt
        from ctypes import wintypes

        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        create = kernel.CreateFileW
        create.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
                           wintypes.LPVOID, wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE]
        create.restype = wintypes.HANDLE
        handle = create(str(target), 0x80010000, 0x5,
                        None, 3, 0x00200000, None)
        if handle == wintypes.HANDLE(-1).value:
            raise OSError(ctypes.get_last_error(),
                          "Reset requires all database clients to be stopped.")
        fd = msvcrt.open_osfhandle(handle, os.O_RDONLY | os.O_BINARY)
        with os.fdopen(fd, "rb") as locked:
            yield locked
    else:
        with closing(sqlite3.connect(target, timeout=0, isolation_level=None)) as conn:
            try:
                conn.execute("BEGIN EXCLUSIVE")
                with target.open("rb") as locked:
                    yield locked
            finally:
                if conn.in_transaction:
                    conn.execute("ROLLBACK")


def replace_demo(path: Path, prepare) -> dict[str, int]:
    """Prepare a validated replacement without modifying the old database."""
    target = _safe_path(path)
    _no_sidecars(target)
    identity = _identity(target)
    if identity is not None:
        _validate_owned(target)
        digest = hashlib.sha256(target.read_bytes()).digest()
    target.parent.mkdir(parents=True, exist_ok=True)
    _safe_path(target)
    parents = _parents(target)
    fd, name = tempfile.mkstemp(
        prefix=f".{target.name}.reset-", suffix=".db", dir=target.parent)
    os.close(fd)
    prepared = Path(name)
    try:
        counts = prepare(prepared)
        _validate_owned(prepared)
        _no_sidecars(prepared)
        with prepared.open("r+b") as handle:
            os.fsync(handle.fileno())
        if (_safe_path(target) != target or _parents(target) != parents
                or _identity(target) != identity):
            raise ValueError(
                "Reset target or its parent identity changed during preparation.")
        _no_sidecars(target)
        if identity is None:
            # Unlike replace(), hard-link publication cannot overwrite a file
            # created concurrently. finally removes only our preparation name.
            os.link(prepared, target)
        else:
            with _exclusive_file(target) as locked:
                if (_identity(target) != identity
                        or hashlib.sha256(locked.read()).digest() != digest
                        or _parents(target) != parents):
                    raise ValueError(
                        "Reset target changed before replacement.")
                _safe_path(target)
                _no_sidecars(target)
            os.replace(prepared, target)
        return counts
    finally:
        prepared.unlink(missing_ok=True)
