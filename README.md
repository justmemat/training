# Training Tracker

A local Streamlit application for team rosters, individual trainee oversight, instructor time, and monthly training sessions. People are maintained once and selected throughout the application, while SQLite provides durable local storage.

## Setup and running

Python 3.10 or newer is recommended.

```bash
python -m venv .venv
source .venv/bin/activate              # Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run main.py
```

## Storage and backups

By default, data is stored in `training.db` in the directory from which Streamlit is launched. Set `TRAINING_DB_PATH` to use another location (for example, `TRAINING_DB_PATH=/secure/training.db streamlit run main.py`). The file is created automatically.

To back up the application, stop Streamlit and copy `training.db` to a secure, access-controlled location. Regularly retain dated copies and test restoring one by replacing the database while the app is stopped. Do not edit or copy the live file while writes are in progress.

## Pages

* **Team Members** lists the normalized people directory and adds, edits, or—after confirmation—removes unreferenced members. Operating initials are required and unique.
* **Individual Trainees** creates or updates a selected member's profile, records daily instructor hours and notes, and shows entry history and totals by instructor.
* **Monthly Training Sessions** creates or edits session details and attendance, and lists earlier sessions with their attendees.

All people fields use the Team Members directory. Deletion is rejected while a person is referenced, protecting profile, time, session, and attendance history.

## Tests

```bash
python -m unittest discover -s tests
```
