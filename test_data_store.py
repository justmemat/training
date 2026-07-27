"""Tests for the feature-based JSON storage layer."""

import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

import data_store
from team_member_service import display_name, role_sort_key, upsert_member
from trainee_service import (
    TRAINING_PHASES,
    ensure_profile,
    format_start_date,
    update_profile,
)
from training_directory_service import (
    add_business_days,
    build_guide_fields,
    create_trainee_folders,
    trainee_directory_exists,
)


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
    def test_start_date_uses_readable_display_format(self) -> None:
        self.assertEqual(format_start_date("2026-07-27"), "27 Jul 2026")
        self.assertEqual(format_start_date(""), "")

    def test_profile_creation_and_update(self) -> None:
        profiles: list[dict] = []
        profile = ensure_profile(profiles, "member-1")
        self.assertEqual(profile["training_phase"], "Ground School")
        self.assertEqual(profile["start_date"], "")

        update_profile(
            profile,
            start_date="2026-07-27",
            training_phase="Phase Two",
            primary_instructor_id="instructor-1",
            secondary_instructor_id="instructor-2",
            manager_id="manager-1",
            team_members=[
                {"id": "instructor-1"},
                {"id": "instructor-2"},
                {"id": "manager-1", "is_manager": True},
            ],
        )
        self.assertEqual(profile["start_date"], "2026-07-27")
        self.assertEqual(profile["training_phase"], "Phase Two")
        self.assertEqual(profile["primary_instructor_id"], "instructor-1")
        self.assertEqual(profile["secondary_instructor_id"], "instructor-2")
        self.assertEqual(profile["manager_id"], "manager-1")
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

    def test_assigned_manager_requires_manager_role(self) -> None:
        profile = ensure_profile([], "trainee-1")
        with self.assertRaisesRegex(ValueError, "Manager role"):
            update_profile(
                profile,
                start_date="2026-07-27",
                training_phase="Ground School",
                manager_id="member-1",
                team_members=[{"id": "member-1", "is_manager": False}],
            )

    def test_instructors_must_reference_team_members(self) -> None:
        profile = ensure_profile([], "trainee-1")
        with self.assertRaisesRegex(ValueError, "valid instructor"):
            update_profile(
                profile,
                start_date="2026-07-27",
                training_phase="Ground School",
                primary_instructor_id="missing",
                team_members=[],
            )


class TrainingDirectoryServiceTests(unittest.TestCase):
    def test_trainee_directory_contains_reports_subfolder(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            trainee_directory = create_trainee_folders(Path(directory), "JR")
            self.assertEqual(trainee_directory, Path(directory) / "JR")
            self.assertTrue(trainee_directory.is_dir())
            self.assertTrue((trainee_directory / "Reports").is_dir())
            self.assertTrue(
                trainee_directory_exists(
                    {"operating_initials": "jr"}, Path(directory)
                )
            )
            with self.assertRaisesRegex(FileExistsError, "already exists"):
                create_trainee_folders(Path(directory), "JR")

    def test_business_day_calculation_skips_weekends(self) -> None:
        self.assertEqual(add_business_days(date(2026, 7, 24), 1), date(2026, 7, 27))
        self.assertEqual(add_business_days(date(2026, 7, 27), 30), date(2026, 9, 7))

    def test_pdf_fields_are_built_from_program_data(self) -> None:
        trainee = {
            "id": "trainee",
            "first_name": "Jamie",
            "last_name": "Rivera",
            "operating_initials": "jr",
        }
        members = [
            trainee,
            {"id": "primary", "first_name": "Pat", "last_name": "Primary"},
            {"id": "secondary", "first_name": "Sam", "last_name": "Second"},
            {
                "id": "lead",
                "first_name": "Lee",
                "last_name": "Lead",
                "is_training_lead": True,
            },
            {
                "id": "manager",
                "first_name": "Morgan",
                "last_name": "Manager",
                "is_manager": True,
            },
        ]
        profile = {
            "start_date": "2026-07-27",
            "primary_instructor_id": "primary",
            "secondary_instructor_id": "secondary",
            "manager_id": "manager",
        }
        fields = build_guide_fields(trainee, profile, members)
        self.assertEqual(fields["NAME"], "Jamie Rivera")
        self.assertEqual(fields["INITIALS"], "JR")
        self.assertEqual(fields["PRIMARY"], "Pat Primary")
        self.assertEqual(fields["SECONDARY"], "Sam Second")
        self.assertEqual(fields["LEAD"], "Lee Lead")
        self.assertEqual(fields["MANAGER"], "Morgan Manager")
        self.assertEqual(fields["StartDate"], "27 Jul 2026")
        self.assertEqual(fields["CheckOne"], "07 Sep 2026")
        self.assertEqual(fields["StudentName"], "Jamie Rivera")

    def test_pypdf_is_declared_as_an_application_dependency(self) -> None:
        requirements = Path("requirements.txt").read_text(encoding="utf-8")
        self.assertIn("pypdf", requirements)


if __name__ == "__main__":
    unittest.main()
