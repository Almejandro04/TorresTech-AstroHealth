"""Validation errors and checks that depend on a stored astronaut profile.

Nothing here is HTTP. Each issue names the affected field (for example
`body.mission_day`) so the API layer can build the contract's error envelope.
"""

from typing import TypedDict

from pydantic import ValidationError

from app.models.fields import mission_day_for
from app.models.schemas import Astronaut


class FieldIssue(TypedDict):
    field: str
    message: str


class RecordValidationError(ValueError):
    """A structurally parsed record that the contract still rejects."""

    def __init__(self, details: list[FieldIssue]) -> None:
        self.details = details
        super().__init__("; ".join(f"{d['field']}: {d['message']}" for d in details))


class AstronautNotFoundError(LookupError):
    def __init__(self, astronaut_id: str) -> None:
        self.astronaut_id = astronaut_id
        super().__init__(f"Astronaut {astronaut_id} was not found.")


class AlertNotFoundError(LookupError):
    def __init__(self, alert_id: str) -> None:
        self.alert_id = alert_id
        super().__init__(f"Alert {alert_id} was not found.")


def issues_from_errors(errors: list, prefix: str | None = None) -> list[FieldIssue]:
    """Convert Pydantic-style error items into `{field, message}` issues.

    `prefix` is prepended to each location; request errors already start with
    `body` or `query`, so they pass none.
    """
    issues: list[FieldIssue] = []
    for item in errors:
        parts = [str(part) for part in item["loc"]]
        message = item["msg"]
        if item["type"] == "json_invalid":
            parts, message = ["body"], "Must be valid JSON."
        elif item["type"] in ("float_type", "int_type") and isinstance(item.get("input"), str):
            message = "Enter a JSON number, not text."
        field = ".".join(parts if prefix is None else [prefix, *parts])
        issues.append({"field": field, "message": message})
    return issues


def issues_from_pydantic(error: ValidationError, prefix: str = "body") -> list[FieldIssue]:
    """Convert Pydantic errors into `{field, message}` issues under `prefix`."""
    return issues_from_errors(error.errors(), prefix)


def mission_day_issues(
    astronaut: Astronaut, timestamp: str, mission_day: int, prefix: str = "body"
) -> list[FieldIssue]:
    """Check that the supplied day matches the timestamp and the mission."""
    expected = mission_day_for(timestamp, astronaut.mission_start_date)
    if mission_day != expected:
        message = "Does not match the observation UTC date."
    elif not 1 <= mission_day <= astronaut.planned_duration_days:
        message = "Must be within the planned mission duration."
    else:
        return []
    return [{"field": f"{prefix}.mission_day", "message": message}]
