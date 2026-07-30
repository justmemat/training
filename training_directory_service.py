"""Create and manage a trainee's training directory and guide."""

from datetime import date, timedelta
import os
from pathlib import Path
import shutil
from typing import Any

from trainee_service import format_start_date

TRAINING_GUIDE_TEMPLATE = Path(
    r"T:\BAE\Training\Onboarding\Masters\STARS Adaptation Specialist Training Guide.pdf"
)
TRAINING_DIRECTORY_ROOT = Path(r"T:\BAE\Training\Onboarding")


def add_business_days(start: date, days: int) -> date:
    """Advance by weekdays, excluding the starting date and weekends."""
    current = start
    remaining = days
    while remaining:
        current += timedelta(days=1)
        if current.weekday() < 5:
            remaining -= 1
    return current


def full_name(member: dict[str, Any] | None) -> str:
    """Return a team member's first and last name."""
    if not member:
        return ""
    return f"{member.get('first_name', '')} {member.get('last_name', '')}".strip()


def create_trainee_folders(output_root: Path, initials: str) -> Path:
    """Create the trainee directory and its required subfolders."""
    output_directory = output_root / initials
    try:
        output_directory.mkdir(parents=True, exist_ok=False)
    except FileExistsError as error:
        raise FileExistsError(
            f"A training directory already exists for {initials}: {output_directory}"
        ) from error
    (output_directory / "Reports").mkdir()
    (output_directory / "Uploads").mkdir()
    return output_directory


def trainee_directory(
    trainee: dict[str, Any], output_root: Path = TRAINING_DIRECTORY_ROOT
) -> Path:
    """Return the expected directory for a trainee's operating initials."""
    initials = str(trainee.get("operating_initials", "")).strip().upper()
    if not initials:
        raise ValueError("The trainee must have operating initials.")
    return output_root / initials


def training_guide_path(
    trainee: dict[str, Any], output_root: Path = TRAINING_DIRECTORY_ROOT
) -> Path:
    """Return the populated training guide's expected path."""
    initials = str(trainee.get("operating_initials", "")).strip().upper()
    return trainee_directory(trainee, output_root) / (
        f"STARS Adaptation Specialist Training Guide - {initials}.pdf"
    )


def uploads_directory(
    trainee: dict[str, Any], output_root: Path = TRAINING_DIRECTORY_ROOT
) -> Path:
    """Return the trainee's Uploads directory, requiring it to exist."""
    directory = trainee_directory(trainee, output_root) / "Uploads"
    if not directory.is_dir():
        raise FileNotFoundError(
            "Create the trainee's training directory before uploading files."
        )
    return directory


def copy_files_to_uploads(
    trainee: dict[str, Any],
    source_paths: list[str | Path],
    output_root: Path = TRAINING_DIRECTORY_ROOT,
) -> list[Path]:
    """Copy selected files into the trainee's Uploads directory."""
    destination = uploads_directory(trainee, output_root)
    copied: list[Path] = []
    for source_value in source_paths:
        source = Path(source_value)
        if not source.is_file():
            raise FileNotFoundError(f"Selected upload file was not found: {source}")
        target = destination / source.name
        shutil.copy2(source, target)
        copied.append(target)
    return copied


def open_directory(directory: Path) -> Path:
    """Open a directory in the operating system's file browser."""
    if not directory.is_dir():
        raise FileNotFoundError(f"Directory was not found: {directory}")
    os.startfile(str(directory))  # type: ignore[attr-defined]
    return directory


def trainee_directory_exists(
    trainee: dict[str, Any], output_root: Path = TRAINING_DIRECTORY_ROOT
) -> bool:
    """Return whether the trainee's operating-initials directory already exists."""
    initials = str(trainee.get("operating_initials", "")).strip().upper()
    return bool(initials) and (output_root / initials).is_dir()


def build_guide_fields(
    trainee: dict[str, Any],
    profile: dict[str, Any],
    team_members: list[dict[str, Any]],
) -> dict[str, str]:
    """Build the exact PDF field mapping from application records."""
    by_id = {str(member.get("id", "")): member for member in team_members}
    start_date_text = str(profile.get("start_date", ""))
    if not start_date_text:
        raise ValueError("Assign and save a trainee start date first.")
    try:
        start = date.fromisoformat(start_date_text)
    except ValueError as error:
        raise ValueError("The trainee start date is invalid.") from error

    check_one = add_business_days(start, 30)
    check_two = add_business_days(check_one, 30)
    evaluation = add_business_days(check_two, 30)
    training_lead = next(
        (member for member in team_members if member.get("is_training_lead")), None
    )
    trainee_name = full_name(trainee)
    return {
        "NAME": trainee_name,
        "INITIALS": str(trainee.get("operating_initials", "")).upper(),
        "PRIMARY": full_name(by_id.get(str(profile.get("primary_instructor_id", "")))),
        "SECONDARY": full_name(
            by_id.get(str(profile.get("secondary_instructor_id", "")))
        ),
        "LEAD": full_name(training_lead),
        "MANAGER": full_name(by_id.get(str(profile.get("manager_id", "")))),
        "StartDate": format_start_date(start.isoformat()),
        "CheckOne": format_start_date(check_one.isoformat()),
        "CheckTwo": format_start_date(check_two.isoformat()),
        "Eval": format_start_date(evaluation.isoformat()),
        "StudentName": trainee_name,
    }


def create_training_directory(
    trainee: dict[str, Any],
    profile: dict[str, Any],
    team_members: list[dict[str, Any]],
    *,
    template_path: Path = TRAINING_GUIDE_TEMPLATE,
    output_root: Path = TRAINING_DIRECTORY_ROOT,
) -> Path:
    """Fill the PDF template and save it beneath the trainee's initials."""
    if not template_path.is_file():
        raise FileNotFoundError(
            f"Training guide template was not found: {template_path}"
        )
    initials = str(trainee.get("operating_initials", "")).strip().upper()
    if not initials:
        raise ValueError("The trainee must have operating initials.")
    if trainee_directory_exists(trainee, output_root):
        raise FileExistsError(
            f"A training directory already exists for {initials}: {output_root / initials}"
        )

    from pypdf import PdfReader, PdfWriter

    output_directory = create_trainee_folders(output_root, initials)
    output_path = training_guide_path(trainee, output_root)
    fields = build_guide_fields(trainee, profile, team_members)
    reader = PdfReader(str(template_path))
    writer = PdfWriter()
    writer.clone_document_from_reader(reader)
    for pdf_page in writer.pages:
        writer.update_page_form_field_values(pdf_page, fields, auto_regenerate=False)
    with output_path.open("wb") as output_file:
        writer.write(output_file)
    return output_path
