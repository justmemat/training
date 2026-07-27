"""Tests for the feature-based JSON storage layer."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import data_store
from team_member_service import display_name, upsert_member


class DataStoreTests(unittest.TestCase):
    def test_initializes_separate_files_and_round_trips_records(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(data_store, "DATA_DIRECTORY", Path(directory)):
                data_store.initialize_data_files()

                self.assertEqual(
                    {path.name for path in Path(directory).iterdir()},
                    set(data_store.DATA_FILES.values()),
                )
                records = [{"name": "Example Team Member"}]
                data_store.save_records("team_members", records)
                self.assertEqual(data_store.load_records("team_members"), records)

    def test_unknown_feature_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "Unknown data feature"):
            data_store.load_records("unknown")


class TeamMemberServiceTests(unittest.TestCase):
    def test_add_update_and_display_member(self) -> None:
        members: list[dict] = []
        created = upsert_member(
            members,
            first_name="  Jamie ",
            last_name="Rivera",
            operating_initials=" jr ",
            is_manager=True,
            is_training_lead=False,
        )
        self.assertEqual(display_name(created), "J. Rivera")
        self.assertEqual(created["operating_initials"], "JR")
        self.assertTrue(created["is_manager"])

        updated = upsert_member(
            members,
            first_name="James",
            last_name="Rivera",
            operating_initials="JR",
            is_manager=False,
            is_training_lead=True,
            member_id=created["id"],
        )
        self.assertEqual(len(members), 1)
        self.assertEqual(updated["first_name"], "James")
        self.assertTrue(updated["is_training_lead"])

    def test_assigning_training_lead_replaces_previous_lead(self) -> None:
        members: list[dict] = []
        first = upsert_member(
            members,
            first_name="Alex",
            last_name="One",
            operating_initials="AO",
            is_manager=False,
            is_training_lead=True,
        )
        second = upsert_member(
            members,
            first_name="Blair",
            last_name="Two",
            operating_initials="BT",
            is_manager=False,
            is_training_lead=True,
        )
        self.assertFalse(first["is_training_lead"])
        self.assertTrue(second["is_training_lead"])

    def test_required_and_unique_operating_initials(self) -> None:
        members: list[dict] = []
        upsert_member(
            members,
            first_name="Alex",
            last_name="One",
            operating_initials="AO",
            is_manager=False,
            is_training_lead=False,
        )
        with self.assertRaisesRegex(ValueError, "unique"):
            upsert_member(
                members,
                first_name="Another",
                last_name="Operator",
                operating_initials="ao",
                is_manager=False,
                is_training_lead=False,
            )


if __name__ == "__main__":
    unittest.main()
