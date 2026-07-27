# Training Tracker

A local Streamlit application for team rosters, individual trainee oversight, instructor time, and monthly training sessions. People are maintained once and selected throughout the application, while SQLite provides durable local storage.

## Setup and running

Python 3.10 or newer is recommended.

### Windows (easiest method)

1. Install [Python 3](https://www.python.org/downloads/) if it is not already installed. On the installer screen, select **Add Python to PATH**.
2. Download **all** repository files into one folder. Do not download only `main.py`.
3. Double-click `run_app.bat`. The launcher works with folders containing spaces (including OneDrive folders), creates an isolated `.venv`, installs Streamlit and pandas from `requirements.txt`, and starts the app.
4. Leave the command window open while using the app. The browser normally opens automatically; otherwise, open the local URL shown in that window.

The application cannot be launched by typing `main.py`. Streamlit is an installed Python package and must start the script with `streamlit run`. If you see `ModuleNotFoundError: No module named 'streamlit'`, the dependencies have not yet been installed in the Python environment running the file; use `run_app.bat` or follow the manual commands below.

### Manual setup (Windows Command Prompt)

Open Command Prompt in the folder containing these files, then run:

```bat
py -3 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe -m streamlit run main.py
```

Using `.venv\Scripts\python.exe -m ...` ensures that `pip` and Streamlit use the same Python installation. If `py` is not recognized, replace `py -3` in the first command with `python`.

### macOS or Linux

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m streamlit run main.py
```

The canonical Streamlit command is `streamlit run main.py`; using `python -m streamlit run main.py` as shown above is equivalent and avoids selecting a Streamlit executable from a different Python installation.

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
