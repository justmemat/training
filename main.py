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
        if "team_members.initials" in str(exc):
            message = "Operating initials must be unique."
        elif "team_members.is_training_lead" in str(exc):
            message = "Only one team member can be assigned as Training Lead."
        else:
            message = str(exc)
        st.error(message)
    else:
        st.success("Saved successfully.")


def choices(members):
    return {f"{m['display_name']} ({m['initials']})": m["id"] for m in members}


def member_page():
    st.header("Team Members")
    members = db.list_members()
    member_rows = [{"Name": m["display_name"], "Operating initials": m["initials"],
                    "Manager": bool(m["is_manager"]),
                    "Training Lead": bool(m["is_training_lead"])} for m in members]
    st.dataframe(pd.DataFrame(member_rows), hide_index=True, use_container_width=True)
    with st.form("add_member", clear_on_submit=True):
        st.subheader("Add member")
        first_name = st.text_input("First name")
        last_name = st.text_input("Last name")
        initials = st.text_input("Operating initials")
        is_manager = st.checkbox("Manager")
        is_training_lead = st.checkbox("Training Lead")
        if st.form_submit_button("Add member"):
            report(lambda: db.add_member(first_name, last_name, initials,
                                         is_manager, is_training_lead))
    if members:
        labels = choices(members)
        selected = st.selectbox("Member to edit", labels)
        member = next(m for m in members if m["id"] == labels[selected])
        with st.form("edit_member"):
            first_name = st.text_input("First name", member["first_name"], key="edit_first_name")
            last_name = st.text_input("Last name", member["last_name"], key="edit_last_name")
            initials = st.text_input("Operating initials", member["initials"], key="edit_initials")
            is_manager = st.checkbox("Manager", bool(member["is_manager"]), key="edit_manager")
            is_training_lead = st.checkbox("Training Lead", bool(member["is_training_lead"]),
                                           key="edit_training_lead")
            if st.form_submit_button("Save changes"):
                report(lambda: db.update_member(member["id"], first_name, last_name, initials,
                                                is_manager, is_training_lead))
        confirm = st.checkbox("I understand deletion is permanent", key="confirm_delete")
        if st.button("Remove member", disabled=not confirm):
            report(lambda: db.delete_member(member["id"]))


def trainee_page():
    st.header("Trainees")
    members = db.list_members()
    if not members:
        st.info("Add team members before creating a trainee profile.")
        return
    labels = choices(members)
    trainee_label = st.selectbox("Trainee", labels)
    trainee_id = labels[trainee_label]
    profile = db.get_profile(trainee_id)
    managers = db.list_managers()
    training_lead = db.get_training_lead()
    if not managers or training_lead is None:
        missing = []
        if not managers:
            missing.append("at least one Manager")
        if training_lead is None:
            missing.append("one Training Lead")
        st.warning(f"Assign {' and '.join(missing)} on the Team Members page before saving a trainee profile.")
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
        st.text_input("Training Lead", training_lead["display_name"] if training_lead else "Not assigned",
                      disabled=True)
        manager_labels = list(choices(managers))
        manager_choices = choices(managers)
        manager_index = next((i for i, label in enumerate(manager_labels)
                              if profile and manager_choices[label] == profile["manager_id"]), 0)
        manager = st.selectbox("Manager", manager_labels, index=manager_index,
                               disabled=not manager_labels)
        if st.form_submit_button("Save trainee profile", disabled=not managers or training_lead is None):
            report(lambda: db.save_profile(trainee_id, start, phase, labels[primary],
                   None if secondary == "None" else labels[secondary], training_lead["id"],
                   manager_choices[manager]))
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


page = st.sidebar.radio("Navigation", ("Team Members", "Trainees", "Monthly Training Sessions"))
{"Team Members": member_page, "Trainees": trainee_page,
 "Monthly Training Sessions": sessions_page}[page]()
