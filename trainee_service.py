"""Business rules for trainee profiles and training phases."""

from datetime import date
from typing import Any


TRAINING_PHASES = ("Ground School", "Phase One", "Phase Two", "Phase Three")


def validate_training_details(start_date: str, training_phase: str) -> tuple[str, str]:
    """Validate and normalize editable training details."""
    normalized_date = start_date.strip()
    if normalized_date:
        try:
            date.fromisoformat(normalized_date)
        except ValueError as error:
            raise ValueError("Start date must use YYYY-MM-DD format.") from error
    if training_phase not in TRAINING_PHASES:
        raise ValueError("Select a valid Training Phase.")
    return normalized_date, training_phase


def format_start_date(start_date: str) -> str:
    """Format a stored ISO date for display, for example ``27 Jul 2026``."""
    if not start_date:
        return ""
    try:
        return date.fromisoformat(start_date).strftime("%d %b %Y")
    except ValueError:
        return start_date


def get_profile(
    profiles: list[dict[str, Any]], team_member_id: str
) -> dict[str, Any] | None:
    """Find a trainee profile using its linked team-member ID."""
    return next(
        (
            profile
            for profile in profiles
            if profile.get("team_member_id") == team_member_id
        ),
        None,
    )


def ensure_profile(
    profiles: list[dict[str, Any]], team_member_id: str
) -> dict[str, Any]:
    """Return an existing profile or create one with initial training defaults."""
    profile = get_profile(profiles, team_member_id)
    if profile is None:
        profile = {
            "team_member_id": team_member_id,
            "start_date": "",
            "training_phase": TRAINING_PHASES[0],
            "primary_instructor_id": "",
            "secondary_instructor_id": "",
            "manager_id": "",
        }
        profiles.append(profile)
    return profile


def update_profile(
    profile: dict[str, Any],
    *,
    start_date: str,
    training_phase: str,
    primary_instructor_id: str = "",
    secondary_instructor_id: str = "",
    manager_id: str = "",
    team_members: list[dict[str, Any]] | None = None,
) -> None:
    """Update a trainee profile after validating its training details."""
    start_date, training_phase = validate_training_details(start_date, training_phase)
    if team_members is not None:
        member_ids = {str(member.get("id", "")) for member in team_members}
        for instructor_id in (primary_instructor_id, secondary_instructor_id):
            if instructor_id and instructor_id not in member_ids:
                raise ValueError("Select a valid instructor.")
        manager_ids = {
            str(member.get("id", ""))
            for member in team_members
            if member.get("is_manager")
        }
        if manager_id and manager_id not in manager_ids:
            raise ValueError("Assigned manager must have the Manager role.")
    profile["start_date"] = start_date
    profile["training_phase"] = training_phase
    profile["primary_instructor_id"] = primary_instructor_id
    profile["secondary_instructor_id"] = secondary_instructor_id
    profile["manager_id"] = manager_id
