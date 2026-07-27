"""SQLite persistence and validation for the training tracker."""

from __future__ import annotations

import os
import sqlite3
from datetime import date, datetime
from pathlib import Path
from typing import Iterable

DEFAULT_DB_PATH = Path(os.environ.get("TRAINING_DB_PATH", "training.db"))
PHASES = ("Orientation", "Phase 1", "Phase 2", "Phase 3", "Qualified")


class ValidationError(ValueError):
    """Raised when application input is invalid."""


class ReferencedMemberError(ValueError):
    """Raised when a referenced team member cannot be deleted."""


def clean_required(value: str, label: str) -> str:
    value = value.strip()
    if not value:
        raise ValidationError(f"{label} is required.")
    return value


def validate_initials(value: str) -> str:
    value = clean_required(value, "Operating initials").upper()
    if not value.isalnum() or len(value) > 10:
        raise ValidationError("Operating initials must be 1–10 letters or numbers.")
    return value


def validate_date(value: str | date) -> str:
    if isinstance(value, date):
        return value.isoformat()
    try:
        return date.fromisoformat(value).isoformat()
    except (TypeError, ValueError) as exc:
        raise ValidationError("Enter a valid date.") from exc


def validate_hours(value: float) -> float:
    try:
        hours = float(value)
    except (TypeError, ValueError) as exc:
        raise ValidationError("Time spent must be a number.") from exc
    if hours < 0:
        raise ValidationError("Time spent cannot be negative.")
    return hours


def validate_file_location(value: str) -> str:
    value = clean_required(value, "File location")
    if any(ord(char) < 32 for char in value):
        raise ValidationError("File location contains unreadable control characters.")
    return value


class Database:
    def __init__(self, path: str | Path = DEFAULT_DB_PATH):
        self.path = str(path)
        self.initialize()

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def initialize(self) -> None:
        with self.connect() as db:
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS team_members (
                    id INTEGER PRIMARY KEY,
                    full_name TEXT NOT NULL CHECK(length(trim(full_name)) > 0),
                    initials TEXT NOT NULL COLLATE NOCASE UNIQUE
                );
                CREATE TABLE IF NOT EXISTS trainee_profiles (
                    trainee_id INTEGER PRIMARY KEY REFERENCES team_members(id) ON DELETE RESTRICT,
                    start_date TEXT NOT NULL,
                    phase TEXT NOT NULL,
                    primary_instructor_id INTEGER NOT NULL REFERENCES team_members(id) ON DELETE RESTRICT,
                    secondary_instructor_id INTEGER REFERENCES team_members(id) ON DELETE RESTRICT,
                    training_lead_id INTEGER NOT NULL REFERENCES team_members(id) ON DELETE RESTRICT,
                    manager_id INTEGER NOT NULL REFERENCES team_members(id) ON DELETE RESTRICT
                );
                CREATE TABLE IF NOT EXISTS daily_instructor_time (
                    id INTEGER PRIMARY KEY,
                    trainee_id INTEGER NOT NULL REFERENCES team_members(id) ON DELETE RESTRICT,
                    work_date TEXT NOT NULL,
                    instructor_id INTEGER NOT NULL REFERENCES team_members(id) ON DELETE RESTRICT,
                    hours REAL NOT NULL CHECK(hours >= 0),
                    notes TEXT,
                    UNIQUE(trainee_id, work_date, instructor_id)
                );
                CREATE TABLE IF NOT EXISTS training_sessions (
                    id INTEGER PRIMARY KEY,
                    session_date TEXT NOT NULL,
                    topic TEXT NOT NULL CHECK(length(trim(topic)) > 0),
                    file_location TEXT NOT NULL CHECK(length(trim(file_location)) > 0),
                    instructor_id INTEGER NOT NULL REFERENCES team_members(id) ON DELETE RESTRICT
                );
                CREATE TABLE IF NOT EXISTS session_attendance (
                    session_id INTEGER NOT NULL REFERENCES training_sessions(id) ON DELETE CASCADE,
                    member_id INTEGER NOT NULL REFERENCES team_members(id) ON DELETE RESTRICT,
                    PRIMARY KEY(session_id, member_id)
                );
                """
            )

    def _all(self, sql: str, parameters: tuple = ()) -> list[sqlite3.Row]:
        with self.connect() as db:
            return db.execute(sql, parameters).fetchall()

    def add_member(self, full_name: str, initials: str) -> int:
        with self.connect() as db:
            cursor = db.execute("INSERT INTO team_members(full_name, initials) VALUES (?, ?)",
                                (clean_required(full_name, "Full name"), validate_initials(initials)))
            return cursor.lastrowid

    def list_members(self) -> list[sqlite3.Row]:
        return self._all("SELECT * FROM team_members ORDER BY full_name COLLATE NOCASE")

    def update_member(self, member_id: int, full_name: str, initials: str) -> None:
        with self.connect() as db:
            cursor = db.execute("UPDATE team_members SET full_name=?, initials=? WHERE id=?",
                                (clean_required(full_name, "Full name"), validate_initials(initials), member_id))
            if not cursor.rowcount:
                raise ValidationError("Team member was not found.")

    def delete_member(self, member_id: int) -> None:
        try:
            with self.connect() as db:
                cursor = db.execute("DELETE FROM team_members WHERE id=?", (member_id,))
                if not cursor.rowcount:
                    raise ValidationError("Team member was not found.")
        except sqlite3.IntegrityError as exc:
            raise ReferencedMemberError("This member is referenced by training records and cannot be removed.") from exc

    def save_profile(self, trainee_id: int, start_date: str | date, phase: str,
                     primary_id: int, secondary_id: int | None, lead_id: int, manager_id: int) -> None:
        phase = clean_required(phase, "Training phase")
        with self.connect() as db:
            db.execute("""INSERT INTO trainee_profiles VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(trainee_id) DO UPDATE SET start_date=excluded.start_date, phase=excluded.phase,
                primary_instructor_id=excluded.primary_instructor_id,
                secondary_instructor_id=excluded.secondary_instructor_id,
                training_lead_id=excluded.training_lead_id, manager_id=excluded.manager_id""",
                       (trainee_id, validate_date(start_date), phase, primary_id, secondary_id, lead_id, manager_id))

    def get_profile(self, trainee_id: int) -> sqlite3.Row | None:
        rows = self._all("SELECT * FROM trainee_profiles WHERE trainee_id=?", (trainee_id,))
        return rows[0] if rows else None

    def add_time(self, trainee_id: int, work_date: str | date, instructor_id: int,
                 hours: float, notes: str = "") -> int:
        with self.connect() as db:
            cursor = db.execute("""INSERT INTO daily_instructor_time
                (trainee_id, work_date, instructor_id, hours, notes) VALUES (?, ?, ?, ?, ?)""",
                (trainee_id, validate_date(work_date), instructor_id, validate_hours(hours), notes.strip() or None))
            return cursor.lastrowid

    def time_history(self, trainee_id: int) -> list[sqlite3.Row]:
        return self._all("""SELECT t.id, t.work_date, m.full_name AS instructor, t.hours, t.notes
            FROM daily_instructor_time t JOIN team_members m ON m.id=t.instructor_id
            WHERE t.trainee_id=? ORDER BY t.work_date DESC, t.id DESC""", (trainee_id,))

    def time_totals(self, trainee_id: int) -> list[sqlite3.Row]:
        return self._all("""SELECT m.full_name AS instructor, SUM(t.hours) AS total_hours
            FROM daily_instructor_time t JOIN team_members m ON m.id=t.instructor_id
            WHERE t.trainee_id=? GROUP BY m.id, m.full_name ORDER BY m.full_name""", (trainee_id,))

    def save_session(self, session_id: int | None, session_date: str | date, topic: str,
                     file_location: str, instructor_id: int, attendee_ids: Iterable[int]) -> int:
        attendee_ids = list(dict.fromkeys(attendee_ids))
        with self.connect() as db:
            values = (validate_date(session_date), clean_required(topic, "Topic"),
                      validate_file_location(file_location), instructor_id)
            if session_id is None:
                session_id = db.execute("""INSERT INTO training_sessions
                    (session_date, topic, file_location, instructor_id) VALUES (?, ?, ?, ?)""", values).lastrowid
            else:
                cursor = db.execute("""UPDATE training_sessions SET session_date=?, topic=?,
                    file_location=?, instructor_id=? WHERE id=?""", values + (session_id,))
                if not cursor.rowcount:
                    raise ValidationError("Training session was not found.")
                db.execute("DELETE FROM session_attendance WHERE session_id=?", (session_id,))
            db.executemany("INSERT INTO session_attendance(session_id, member_id) VALUES (?, ?)",
                           ((session_id, member_id) for member_id in attendee_ids))
            return session_id

    def list_sessions(self) -> list[sqlite3.Row]:
        return self._all("""SELECT s.id, s.session_date, s.topic, s.file_location,
            s.instructor_id, i.full_name AS instructor,
            COALESCE(GROUP_CONCAT(a.full_name, ', '), '') AS attendees
            FROM training_sessions s JOIN team_members i ON i.id=s.instructor_id
            LEFT JOIN session_attendance sa ON sa.session_id=s.id
            LEFT JOIN team_members a ON a.id=sa.member_id
            GROUP BY s.id ORDER BY s.session_date DESC, s.id DESC""")

    def session_attendee_ids(self, session_id: int) -> list[int]:
        return [row["member_id"] for row in self._all(
            "SELECT member_id FROM session_attendance WHERE session_id=? ORDER BY member_id", (session_id,))]
