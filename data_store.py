"""JSON storage configuration for the OSF Training application."""

import json
import os
from pathlib import Path
from typing import Any


DATA_DIRECTORY = Path(
    os.environ.get("TRAINING_APP_DATA_DIR", r"C:\OSFTOOLS\Training_App")
)

# Keep unrelated records in separate files so each feature can evolve on its own.
DATA_FILES: dict[str, str] = {
    "team_members": "team_members.json",
    "trainees": "trainees.json",
    "monthly_training": "monthly_training.json",
    "training_history": "training_history.json",
}


def initialize_data_files() -> None:
    """Create the data directory and empty feature files when they do not exist."""
    DATA_DIRECTORY.mkdir(parents=True, exist_ok=True)
    for filename in DATA_FILES.values():
        path = DATA_DIRECTORY / filename
        if not path.exists():
            path.write_text("[]\n", encoding="utf-8")


def load_records(feature: str) -> list[dict[str, Any]]:
    """Load records for a feature from its JSON file."""
    path = _feature_path(feature)
    if not path.exists():
        initialize_data_files()
    with path.open(encoding="utf-8") as json_file:
        return json.load(json_file)


def save_records(feature: str, records: list[dict[str, Any]]) -> None:
    """Save a feature's records as readable JSON."""
    initialize_data_files()
    path = _feature_path(feature)
    with path.open("w", encoding="utf-8") as json_file:
        json.dump(records, json_file, indent=2)
        json_file.write("\n")


def _feature_path(feature: str) -> Path:
    try:
        return DATA_DIRECTORY / DATA_FILES[feature]
    except KeyError as error:
        raise ValueError(f"Unknown data feature: {feature}") from error
