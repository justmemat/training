"""Business rules for creating and updating team members."""

import re
from typing import Any
from uuid import uuid4


EMAIL_PATTERN = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


def display_name(member: dict[str, Any]) -> str:
    """Return the compact name used in the team-member list."""
    first_name = str(member.get("first_name", "")).strip()
    last_name = str(member.get("last_name", "")).strip()
    first_initial = f"{first_name[0].upper()}." if first_name else ""
    return " ".join(part for part in (first_initial, last_name) if part)


def validate_member(
    first_name: str, last_name: str, operating_initials: str, email: str = ""
) -> tuple[str, str, str, str]:
    """Normalize member fields and reject incomplete entries."""
    normalized = (
        first_name.strip(),
        last_name.strip(),
        operating_initials.strip().upper(),
        email.strip(),
    )
    if not all(normalized[:3]):
        raise ValueError("First name, last name, and operating initials are required.")
    if len(normalized[2]) > 6:
        raise ValueError("Operating initials must be 6 characters or fewer.")
    if normalized[3] and not EMAIL_PATTERN.fullmatch(normalized[3]):
        raise ValueError("Enter a valid email address.")
    return normalized


def role_sort_key(member: dict[str, Any]) -> tuple[int, str, str]:
    """Sort managers first, then Training Lead, then other team members."""
    if member.get("is_manager"):
        role_priority = 0
    elif member.get("is_training_lead"):
        role_priority = 1
    else:
        role_priority = 2
    return (
        role_priority,
        str(member.get("last_name", "")).lower(),
        str(member.get("first_name", "")).lower(),
    )


def upsert_member(
    members: list[dict[str, Any]],
    *,
    first_name: str,
    last_name: str,
    operating_initials: str,
    email: str = "",
    is_manager: bool,
    is_training_lead: bool,
    member_id: str | None = None,
) -> dict[str, Any]:
    """Add or update a member, ensuring there is at most one Training Lead."""
    first_name, last_name, operating_initials, email = validate_member(
        first_name, last_name, operating_initials, email
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
        "email": email,
        "is_manager": is_manager,
        "is_training_lead": is_training_lead,
    }
    for index, member in enumerate(members):
        if member.get("id") == member_id:
            members[index] = record
            return record
    members.append(record)
    return record
