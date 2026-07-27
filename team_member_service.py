"""Business rules for creating and updating team members."""

from typing import Any
from uuid import uuid4


def display_name(member: dict[str, Any]) -> str:
    """Return the compact name used in the team-member list."""
    first_name = str(member.get("first_name", "")).strip()
    last_name = str(member.get("last_name", "")).strip()
    first_initial = f"{first_name[0].upper()}." if first_name else ""
    return " ".join(part for part in (first_initial, last_name) if part)


def validate_member(
    first_name: str, last_name: str, operating_initials: str
) -> tuple[str, str, str]:
    """Normalize member fields and reject incomplete entries."""
    normalized = (
        first_name.strip(),
        last_name.strip(),
        operating_initials.strip().upper(),
    )
    if not all(normalized):
        raise ValueError("First name, last name, and operating initials are required.")
    if len(normalized[2]) > 6:
        raise ValueError("Operating initials must be 6 characters or fewer.")
    return normalized


def upsert_member(
    members: list[dict[str, Any]],
    *,
    first_name: str,
    last_name: str,
    operating_initials: str,
    is_manager: bool,
    is_training_lead: bool,
    member_id: str | None = None,
) -> dict[str, Any]:
    """Add or update a member, ensuring there is at most one Training Lead."""
    first_name, last_name, operating_initials = validate_member(
        first_name, last_name, operating_initials
    )
    if any(
        str(member.get("operating_initials", "")).upper() == operating_initials
        and member.get("id") != member_id
        for member in members
    ):
        raise ValueError("Operating initials must be unique.")

    if is_training_lead:
        for member in members:
            member["is_training_lead"] = member.get("id") == member_id

    record = {
        "id": member_id or str(uuid4()),
        "first_name": first_name,
        "last_name": last_name,
        "operating_initials": operating_initials,
        "is_manager": is_manager,
        "is_training_lead": is_training_lead,
    }
    for index, member in enumerate(members):
        if member.get("id") == member_id:
            members[index] = record
            return record
    members.append(record)
    return record
