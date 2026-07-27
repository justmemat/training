"""Training-history records created from completed daily reports."""

from datetime import date
import os
from pathlib import Path, PureWindowsPath
from typing import Any, Callable
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
        "file_name": PureWindowsPath(report_path).name,
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


def report_file_uri(record: dict[str, Any]) -> str:
    """Return a local file URI suitable for opening a saved history report."""
    report_path = str(record.get("report_path", "")).strip()
    if not report_path:
        raise ValueError("This history entry does not have a saved report location.")
    return Path(report_path).resolve().as_uri()


def open_report_file(
    record: dict[str, Any], opener: Callable[[str], Any] | None = None
) -> Path:
    """Open a saved report with the operating system's associated PDF viewer."""
    report_path = Path(str(record.get("report_path", "")).strip())
    if not str(report_path) or not report_path.is_file():
        raise FileNotFoundError(f"The saved report could not be found: {report_path}")
    if opener is None:
        startfile = getattr(os, "startfile", None)
        if startfile is None:
            raise OSError("Opening reports is only supported by this app on Windows.")
        opener = startfile
    opener(str(report_path))
    return report_path
