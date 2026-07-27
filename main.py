"""Streamlit interface for the training tracker."""

import sqlite3
from datetime import date

import pandas as pd
import streamlit as st

from database import Database, PHASES, ReferencedMemberError, ValidationError

st.set_page_config(page_title="Training Tracker", page_icon="🎓", layout="wide")
db = Database()


def report(action):
    try:
        action()
    except (ValidationError, ReferencedMemberError, sqlite3.IntegrityError) as exc:
        message = "Operating initials must be unique." if "UNIQUE constraint failed: team_members.initials" in str(exc) else str(exc)
        st.error(message)
    else:
        st.success("Saved successfully.")


def choices(members):
    return {f"{m['full_name']} ({m['initials']})": m["id"] for m in members}


def member_page():
    st.header("Team Members")
    members = db.list_members()
    st.dataframe(pd.DataFrame([dict(m) for m in members]), hide_index=True, use_container_width=True)
    with st.form("add_member", clear_on_submit=True):
        st.subheader("Add member")
        name = st.text_input("Full name")
        initials = st.text_input("Operating initials")
        if st.form_submit_button("Add member"):
            report(lambda: db.add_member(name, initials))
    if members:
        labels = choices(members)
        selected = st.selectbox("Member to edit", labels)
        member = next(m for m in members if m["id"] == labels[selected])
        with st.form("edit_member"):
            name = st.text_input("Full name", member["full_name"], key="edit_name")
            initials = st.text_input("Operating initials", member["initials"], key="edit_initials")
            if st.form_submit_button("Save changes"):
                report(lambda: db.update_member(member["id"], name, initials))
        confirm = st.checkbox("I understand deletion is permanent", key="confirm_delete")
        if st.button("Remove member", disabled=not confirm):
            report(lambda: db.delete_member(member["id"]))


def trainee_page():
    st.header("Individual Trainees")
    members = db.list_members()
    if not members:
        st.info("Add team members before creating a trainee profile.")
        return
    labels = choices(members)
    trainee_label = st.selectbox("Trainee", labels)
    trainee_id = labels[trainee_label]
    profile = db.get_profile(trainee_id)
    member_labels = list(labels)
    id_to_index = lambda value, fallback=0: next((i for i, label in enumerate(member_labels) if labels[label] == value), fallback)
    with st.form("profile"):
        start = st.date_input("Start date", date.fromisoformat(profile["start_date"]) if profile else date.today())
        phase = st.selectbox("Current training phase", PHASES,
                             index=PHASES.index(profile["phase"]) if profile and profile["phase"] in PHASES else 0)
        primary = st.selectbox("Primary instructor", member_labels, index=id_to_index(profile["primary_instructor_id"]) if profile else 0)
        secondary_options = ["None"] + member_labels
        secondary_index = id_to_index(profile["secondary_instructor_id"]) + 1 if profile and profile["secondary_instructor_id"] else 0
        secondary = st.selectbox("Secondary instructor", secondary_options, index=secondary_index)
        lead = st.selectbox("Training lead", member_labels, index=id_to_index(profile["training_lead_id"]) if profile else 0)
        manager = st.selectbox("Manager", member_labels, index=id_to_index(profile["manager_id"]) if profile else 0)
        if st.form_submit_button("Save trainee profile"):
            report(lambda: db.save_profile(trainee_id, start, phase, labels[primary],
                   None if secondary == "None" else labels[secondary], labels[lead], labels[manager]))
    st.subheader("Daily instructor time")
    with st.form("daily_time", clear_on_submit=True):
        work_date = st.date_input("Work date")
        instructor = st.selectbox("Instructor", member_labels, key="time_instructor")
        hours = st.number_input("Time spent (hours)", min_value=0.0, step=0.25)
        notes = st.text_area("Notes (optional)")
        if st.form_submit_button("Add time entry"):
            report(lambda: db.add_time(trainee_id, work_date, labels[instructor], hours, notes))
    history, totals = db.time_history(trainee_id), db.time_totals(trainee_id)
    st.subheader("History")
    st.dataframe(pd.DataFrame([dict(row) for row in history]), hide_index=True, use_container_width=True)
    st.subheader("Totals by instructor")
    st.dataframe(pd.DataFrame([dict(row) for row in totals]), hide_index=True, use_container_width=True)


def sessions_page():
    st.header("Monthly Training Sessions")
    members = db.list_members()
    if not members:
        st.info("Add team members before creating a session.")
        return
    labels = choices(members)
    sessions = db.list_sessions()
    edit_options = {"Create new session": None} | {f"{s['session_date']} — {s['topic']}": s["id"] for s in sessions}
    edit_label = st.selectbox("Session to create or edit", edit_options)
    session_id = edit_options[edit_label]
    session = next((s for s in sessions if s["id"] == session_id), None)
    member_labels = list(labels)
    attendee_ids = db.session_attendee_ids(session_id) if session_id else []
    defaults = [label for label in member_labels if labels[label] in attendee_ids]
    instructor_index = next((i for i, label in enumerate(member_labels)
                             if session and labels[label] == session["instructor_id"]), 0)
    with st.form("session"):
        session_date = st.date_input("Session date", date.fromisoformat(session["session_date"]) if session else date.today())
        topic = st.text_input("Title or topic", session["topic"] if session else "")
        location = st.text_input("File location", session["file_location"] if session else "",
                                 help="Enter a readable local path, shared-drive path, or URL.")
        instructor = st.selectbox("Instructor", member_labels, index=instructor_index)
        attendees = st.multiselect("Attending students", member_labels, default=defaults)
        if st.form_submit_button("Save session"):
            report(lambda: db.save_session(session_id, session_date, topic, location,
                                           labels[instructor], [labels[a] for a in attendees]))
    st.subheader("Previous sessions and attendance")
    st.dataframe(pd.DataFrame([dict(row) for row in sessions]), hide_index=True, use_container_width=True)


page = st.sidebar.radio("Navigation", ("Team Members", "Individual Trainees", "Monthly Training Sessions"))
{"Team Members": member_page, "Individual Trainees": trainee_page,
 "Monthly Training Sessions": sessions_page}[page]()
