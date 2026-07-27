import sqlite3
import tempfile
import unittest
from pathlib import Path

from database import Database, ReferencedMemberError, ValidationError, validate_date, validate_file_location, validate_hours, validate_initials


class DatabaseTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db = Database(Path(self.temp.name) / "test.db")
        self.alex = self.db.add_member("Alex", "Instructor", "AI", True, True)
        self.taylor = self.db.add_member("Taylor", "Trainee", "TT")

    def tearDown(self):
        self.temp.cleanup()

    def test_initialization_and_member_crud(self):
        self.assertEqual(len(self.db.list_members()), 2)
        self.db.update_member(self.alex, "Alex", "Updated", "AU", True, True)
        self.assertEqual(dict(self.db.list_members()[1])["display_name"], "A. Updated")
        unused = self.db.add_member("Unused", "Person", "U")
        self.db.delete_member(unused)
        self.assertEqual(len(self.db.list_members()), 2)

    def test_unique_initials_and_validation(self):
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.add_member("Duplicate", "Person", "ai")
        for invalid in ("", "A!", "TOO-LONG-VALUE"):
            with self.assertRaises(ValidationError):
                validate_initials(invalid)
        with self.assertRaises(ValidationError):
            validate_hours(-0.1)
        with self.assertRaises(ValidationError):
            validate_date("2025-13-40")
        with self.assertRaises(ValidationError):
            validate_file_location("  ")

    def test_profile_foreign_keys_and_safe_delete(self):
        self.db.save_profile(self.taylor, "2025-01-02", "Phase 1", self.alex, None, self.alex, self.alex)
        with self.assertRaises(ReferencedMemberError):
            self.db.delete_member(self.alex)
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.save_profile(999, "2025-01-02", "Phase 1", self.alex, None, self.alex, self.alex)

    def test_roles_and_last_name_sorting(self):
        manager = self.db.add_member("Zoe", "Able", "ZA", True)
        members = self.db.list_members()
        self.assertEqual([row["last_name"] for row in members], ["Able", "Instructor", "Trainee"])
        self.assertEqual([row["id"] for row in self.db.list_managers()], [manager, self.alex])
        self.assertEqual(self.db.get_training_lead()["id"], self.alex)
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.add_member("Another", "Lead", "AL", False, True)

    def test_time_history_and_aggregation(self):
        self.db.add_time(self.taylor, "2025-02-01", self.alex, 1.5, "Review")
        self.db.add_time(self.taylor, "2025-02-02", self.alex, 2)
        self.assertEqual(len(self.db.time_history(self.taylor)), 2)
        self.assertEqual(self.db.time_totals(self.taylor)[0]["total_hours"], 3.5)
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.add_time(self.taylor, "2025-02-01", self.alex, 1)

    def test_session_attendance_create_and_edit(self):
        session = self.db.save_session(None, "2025-03-01", "Safety", "/files/safety.pdf", self.alex,
                                       [self.taylor, self.taylor])
        self.assertEqual(self.db.session_attendee_ids(session), [self.taylor])
        self.db.save_session(session, "2025-03-02", "Safety update", "https://example.test/file", self.alex,
                             [self.alex, self.taylor])
        row = self.db.list_sessions()[0]
        self.assertEqual(row["topic"], "Safety update")
        self.assertEqual(set(self.db.session_attendee_ids(session)), {self.alex, self.taylor})
        with self.db.connect() as connection:
            with self.assertRaises(sqlite3.IntegrityError):
                connection.execute("INSERT INTO session_attendance VALUES (?, ?)", (session, self.taylor))


if __name__ == "__main__":
    unittest.main()
