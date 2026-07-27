"""Populate and save daily trainee training reports."""

from datetime import date
from pathlib import Path
from typing import Any

from trainee_service import format_start_date
from training_directory_service import TRAINING_DIRECTORY_ROOT, full_name


TRAINING_REPORT_TEMPLATE = Path(
    r"T:\BAE\Training\Onboarding\Masters\STARS Adaptation Specialist Training Report.pdf"
)


def build_report_fields(
    trainee: dict[str, Any],
    profile: dict[str, Any],
    team_members: list[dict[str, Any]],
    *,
    instructor_id: str,
    training_summary: str,
    instructor_comments: str,
    report_date: date | None = None,
) -> dict[str, str]:
    """Build the PDF field mapping for a daily training report."""
    by_id = {str(member.get("id", "")): member for member in team_members}
    instructor = by_id.get(instructor_id)
    if instructor is None:
        raise ValueError("Select a valid instructor.")
    summary = training_summary.strip()
    comments = instructor_comments.strip()
    if not summary:
        raise ValueError("Enter a Training Summary.")
    if not comments:
        raise ValueError("Enter Instructor Comments.")

    training_lead = next(
        (member for member in team_members if member.get("is_training_lead")), None
    )
    if training_lead is None:
        raise ValueError("Assign a Training Lead before creating a training report.")
    effective_date = report_date or date.today()
    trainee_initials = str(trainee.get("operating_initials", "")).upper()
    return {
        "Trainees_Name": full_name(trainee),
        "Trainees_Initials": trainee_initials,
        "Date": format_start_date(effective_date.isoformat()),
        "Primary_Instructor": full_name(
            by_id.get(str(profile.get("primary_instructor_id", "")))
        ),
        "Secondary_Instructor": full_name(
            by_id.get(str(profile.get("secondary_instructor_id", "")))
        ),
        "Training_Lead": full_name(training_lead),
        "Training_Summary": summary,
        "Instructor_Comments": comments,
        "Instructor_Initials": str(instructor.get("operating_initials", "")).upper(),
        "Trainees_Initials1": trainee_initials,
        "Training_Lead1": str(training_lead.get("operating_initials", "")).upper(),
    }


def _available_report_path(reports_directory: Path, initials: str, day: date) -> Path:
    """Return a non-conflicting filename so an earlier report is never overwritten."""
    stem = f"STARS Training Report - {initials} - {day.isoformat()}"
    candidate = reports_directory / f"{stem}.pdf"
    sequence = 2
    while candidate.exists():
        candidate = reports_directory / f"{stem} ({sequence}).pdf"
        sequence += 1
    return candidate


def create_training_report(
    trainee: dict[str, Any],
    profile: dict[str, Any],
    team_members: list[dict[str, Any]],
    *,
    instructor_id: str,
    training_summary: str,
    instructor_comments: str,
    template_path: Path = TRAINING_REPORT_TEMPLATE,
    output_root: Path = TRAINING_DIRECTORY_ROOT,
    report_date: date | None = None,
) -> Path:
    """Fill the daily-report template and save it in the trainee's Reports folder."""
    if not template_path.is_file():
        raise FileNotFoundError(f"Training report template was not found: {template_path}")
    initials = str(trainee.get("operating_initials", "")).strip().upper()
    reports_directory = output_root / initials / "Reports"
    if not reports_directory.is_dir():
        raise FileNotFoundError(
            "Create the trainee's training directory before adding a daily report."
        )

    from pypdf import PdfReader, PdfWriter

    effective_date = report_date or date.today()
    fields = build_report_fields(
        trainee,
        profile,
        team_members,
        instructor_id=instructor_id,
        training_summary=training_summary,
        instructor_comments=instructor_comments,
        report_date=effective_date,
    )
    output_path = _available_report_path(reports_directory, initials, effective_date)
    reader = PdfReader(str(template_path))
    writer = PdfWriter()
    writer.clone_document_from_reader(reader)
    for pdf_page in writer.pages:
        writer.update_page_form_field_values(pdf_page, fields, auto_regenerate=False)
    with output_path.open("wb") as output_file:
        writer.write(output_file)
    return output_path
