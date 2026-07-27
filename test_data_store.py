"""Tests for the feature-based JSON storage layer."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import data_store
from team_member_service import display_name, role_sort_key, upsert_member
from trainee_service import TRAINING_PHASES, ensure_profile, update_profile


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
            email=" jamie.rivera@example.com ",
            is_manager=True,
            is_training_lead=False,
        )
        self.assertEqual(display_name(created), "J. Rivera")
        self.assertEqual(created["operating_initials"], "JR")
        self.assertEqual(created["email"], "jamie.rivera@example.com")
        self.assertTrue(created["is_manager"])
        self.assertFalse(created["is_trainee"])

        updated = upsert_member(
            members,
            first_name="James",
            last_name="Rivera",
            operating_initials="JR",
            email="james.rivera@example.com",
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
            email="",
            is_manager=False,
            is_training_lead=True,
        )
        second = upsert_member(
            members,
            first_name="Blair",
            last_name="Two",
            operating_initials="BT",
            email="",
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
            email="",
            is_manager=False,
            is_training_lead=False,
        )
        with self.assertRaisesRegex(ValueError, "unique"):
            upsert_member(
                members,
                first_name="Another",
                last_name="Operator",
                operating_initials="ao",
                email="",
                is_manager=False,
                is_training_lead=False,
            )

    def test_optional_email_is_validated(self) -> None:
        with self.assertRaisesRegex(ValueError, "valid email"):
            upsert_member(
                [],
                first_name="Alex",
                last_name="One",
                operating_initials="AO",
                email="not-an-email",
                is_manager=False,
                is_training_lead=False,
            )

    def test_members_sort_by_role_then_name(self) -> None:
        members = [
            {"first_name": "Zoe", "last_name": "Member"},
            {"first_name": "Taylor", "last_name": "Lead", "is_training_lead": True},
            {"first_name": "Morgan", "last_name": "Boss", "is_manager": True},
            {"first_name": "Aaron", "last_name": "Able", "is_manager": True},
        ]
        ordered = sorted(members, key=role_sort_key)
        self.assertEqual(
            [member["first_name"] for member in ordered],
            ["Aaron", "Morgan", "Taylor", "Zoe"],
        )


class TraineeServiceTests(unittest.TestCase):
    def test_profile_creation_and_update(self) -> None:
        profiles: list[dict] = []
        profile = ensure_profile(profiles, "member-1")
        self.assertEqual(profile["training_phase"], "Ground School")
        self.assertEqual(profile["start_date"], "")

        update_profile(
            profile, start_date="2026-07-27", training_phase="Phase Two"
        )
        self.assertEqual(profile["start_date"], "2026-07-27")
        self.assertEqual(profile["training_phase"], "Phase Two")
        self.assertIs(ensure_profile(profiles, "member-1"), profile)
        self.assertEqual(len(profiles), 1)

    def test_training_phase_and_date_are_validated(self) -> None:
        profile = ensure_profile([], "member-1")
        with self.assertRaisesRegex(ValueError, "YYYY-MM-DD"):
            update_profile(
                profile, start_date="07/27/2026", training_phase=TRAINING_PHASES[0]
            )
        with self.assertRaisesRegex(ValueError, "Training Phase"):
            update_profile(
                profile, start_date="2026-07-27", training_phase="Phase Four"
            )


if __name__ == "__main__":
    unittest.main()
