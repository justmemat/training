"""Training-history records created from completed daily reports."""

from datetime import date
from typing import Any
from uuid import uuid4


def create_history_record(
    *, trainee_id: str, instructor_id: str, report_date: date, report_path: str
) -> dict[str, Any]:
    """Create a persistent history entry for a generated daily report."""
    if not trainee_id or not instructor_id:
        raise ValueError("Trainee and instructor are required for training history.")
    return {
        "id": str(uuid4()),
        "trainee_id": trainee_id,
        "instructor_id": instructor_id,
        "date": report_date.isoformat(),
        "report_path": report_path,
    }


def trainee_history(
    records: list[dict[str, Any]], trainee_id: str
) -> list[dict[str, Any]]:
    """Return one trainee's history with the newest entries first."""
    return sorted(
        (record for record in records if record.get("trainee_id") == trainee_id),
        key=lambda record: str(record.get("date", "")),
        reverse=True,
    )
