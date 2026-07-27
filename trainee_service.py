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
        }
        profiles.append(profile)
    return profile


def update_profile(
    profile: dict[str, Any], *, start_date: str, training_phase: str
) -> None:
    """Update a trainee profile after validating its training details."""
    start_date, training_phase = validate_training_details(start_date, training_phase)
    profile["start_date"] = start_date
    profile["training_phase"] = training_phase
