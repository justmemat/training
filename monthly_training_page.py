"""Monthly training submission and history page."""

from datetime import date, datetime
from pathlib import Path

import flet as ft

from data_store import load_records, save_records
from monthly_training_service import (
    create_session_record,
    generate_monthly_history_report,
    sorted_sessions,
)
from trainee_service import format_start_date
from training_history_service import open_report_file


def build_monthly_training_view(page: ft.Page) -> ft.View:
    """Build monthly training submission, history, and Excel reporting."""
    async def navigate_home(_: ft.ControlEvent) -> None:
        await page.push_route("/")

    loaded_members = load_records("team_members")
    loaded_sessions = load_records("monthly_training")
    members = loaded_members if isinstance(loaded_members, list) else []
    sessions = loaded_sessions if isinstance(loaded_sessions, list) else []
    history_list = ft.Column(spacing=10)
    empty_history = ft.Text(
        "No dataset available...",
        color=ft.Colors.GREY_600,
        italic=True,
    )
    status = ft.Text(visible=False)
    report_progress = ft.ProgressBar(visible=False)

    def member_name(member_id: str) -> str:
        member = next((item for item in members if item.get("id") == member_id), None)
        if member is None:
            return "Unknown"
        return (
            f"{member.get('first_name', '')} {member.get('last_name', '')} "
            f"({member.get('operating_initials', '')})"
        ).strip()

    def open_presented_file(record: dict) -> None:
        try:
            open_report_file({"report_path": str(record.get("presentation_path", ""))})
        except (FileNotFoundError, OSError, ValueError) as error:
            page.open(ft.SnackBar(ft.Text(str(error))))

    def render_history() -> None:
        ordered = sorted_sessions(sessions)
        empty_history.visible = not ordered
        history_list.controls = []
        for session in ordered:
            attendance = ", ".join(
                member_name(str(attendee_id))
                for attendee_id in session.get("attendee_ids", [])
            )
            history_list.controls.append(
                ft.Container(
                    content=ft.Row(
                        [
                            ft.IconButton(
                                icon=ft.Icons.ATTACH_FILE,
                                tooltip=f"Open {session.get('file_name', 'presented file')}",
                                on_click=lambda _, record=session: open_presented_file(record),
                            ),
                            ft.Column(
                                [
                                    ft.Text(
                                        format_start_date(str(session.get("date", ""))),
                                        weight=ft.FontWeight.BOLD,
                                    ),
                                    ft.Text(
                                        f"Instructor: "
                                        f"{member_name(str(session.get('instructor_id', '')))}"
                                    ),
                                    ft.Text(
                                        f"Attendance: {attendance}",
                                        color=ft.Colors.GREY_700,
                                    ),
                                    ft.Text(
                                        str(session.get("file_name", "")),
                                        size=12,
                                        color=ft.Colors.GREY_500,
                                    ),
                                ],
                                spacing=3,
                                expand=True,
                            ),
                        ]
                    ),
                    bgcolor=ft.Colors.WHITE,
                    border=ft.Border.all(1, ft.Colors.INDIGO_100),
                    border_radius=10,
                    padding=12,
                )
            )

    def open_submission_dialog() -> None:
        selected_path = ""
        selected_date = date.today()
        file_text = ft.Text("No file selected", color=ft.Colors.GREY_600)
        date_text = ft.TextField(
            label="Date presented",
            value=format_start_date(selected_date.isoformat()),
            read_only=True,
            width=260,
            prefix_icon=ft.Icons.CALENDAR_MONTH,
        )
        instructor = ft.Dropdown(
            label="Instructor",
            width=420,
            options=[
                ft.dropdown.Option(
                    key=member["id"],
                    text=f"{member.get('first_name', '')} {member.get('last_name', '')} "
                    f"({member.get('operating_initials', '')})",
                )
                for member in members
            ],
        )
        attendance_boxes = [
            ft.Checkbox(
                label=f"{member.get('first_name', '')} {member.get('last_name', '')} "
                f"({member.get('operating_initials', '')})",
                data=member["id"],
            )
            for member in members
        ]
        error_text = ft.Text(color=ft.Colors.RED_700, visible=False)

        file_picker = ft.FilePicker()
        page.services.append(file_picker)

        async def select_file(_: ft.ControlEvent) -> None:
            nonlocal selected_path
            selected_files = await file_picker.pick_files(allow_multiple=False)
            if selected_files:
                selected_path = selected_files[0].path
                file_text.value = selected_path
                file_text.color = ft.Colors.GREY_800
                dialog.update()

        def date_selected(_: ft.ControlEvent) -> None:
            nonlocal selected_date
            if date_picker.value:
                selected_date = date_picker.value.date()
                date_text.value = format_start_date(selected_date.isoformat())
                date_text.update()

        date_picker = ft.DatePicker(
            value=datetime.combine(selected_date, datetime.min.time()),
            first_date=datetime(2000, 1, 1),
            last_date=datetime(2100, 12, 31),
            on_change=date_selected,
        )
        date_text.on_click = lambda _: page.open(date_picker)

        def submit(_: ft.ControlEvent) -> None:
            try:
                record = create_session_record(
                    presentation_date=selected_date,
                    instructor_id=instructor.value or "",
                    attendee_ids=[
                        str(box.data) for box in attendance_boxes if box.value
                    ],
                    presentation_path=selected_path,
                    team_members=members,
                )
            except ValueError as error:
                error_text.value = str(error)
                error_text.visible = True
                dialog.update()
                return
            sessions.append(record)
            save_records("monthly_training", sessions)
            page.close(dialog)
            render_history()
            page.update()
            page.open(ft.SnackBar(ft.Text("Monthly training session submitted.")))

        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Submit training session"),
            content=ft.Container(
                content=ft.Column(
                    [
                        ft.OutlinedButton(
                            "Select presented file",
                            icon=ft.Icons.UPLOAD_FILE,
                            on_click=select_file,
                        ),
                        file_text,
                        date_text,
                        instructor,
                        ft.Text("Team members in attendance", weight=ft.FontWeight.BOLD),
                        ft.Container(
                            content=ft.Column(attendance_boxes, spacing=2),
                            height=220,
                            border=ft.Border.all(1, ft.Colors.GREY_300),
                            border_radius=8,
                            padding=10,
                        ),
                        error_text,
                    ],
                    tight=True,
                    spacing=12,
                    scroll=ft.ScrollMode.AUTO,
                ),
                width=580,
            ),
            actions=[
                ft.TextButton("Cancel", on_click=lambda _: page.close(dialog)),
                ft.FilledButton("Submit", icon=ft.Icons.SAVE, on_click=submit),
            ],
        )
        page.open(dialog)

    def generate_report(_: ft.ControlEvent) -> None:
        report_button.disabled = True
        report_progress.visible = True
        status.value = "Creating or updating the monthly training history report..."
        status.color = ft.Colors.INDIGO_700
        status.visible = True
        page.update()
        try:
            output_path = generate_monthly_history_report(sessions, members)
            open_report_file({"report_path": str(output_path)})
        except ModuleNotFoundError as error:
            if error.name != "openpyxl":
                raise
            status.value = "Excel support is not installed. Run requirements.txt setup."
            status.color = ft.Colors.RED_700
        except (FileNotFoundError, OSError, ValueError) as error:
            status.value = str(error)
            status.color = ft.Colors.RED_700
        else:
            status.value = f"Monthly history report created and opened: {output_path}"
            status.color = ft.Colors.GREEN_700
        report_progress.visible = False
        report_button.disabled = False
        page.update()

    render_history()
    report_button = ft.OutlinedButton(
        "Generate History Report", icon=ft.Icons.TABLE_VIEW, on_click=generate_report
    )
    page_content = ft.ListView(
        controls=[
            ft.Row(
                [
                    ft.Column(
                        [
                            ft.Text(
                                "Monthly Training",
                                size=30,
                                weight=ft.FontWeight.BOLD,
                            ),
                            ft.Text(
                                "Submit an item to track presented training.",
                                color=ft.Colors.GREY_700,
                            ),
                        ],
                        expand=True,
                    ),
                    ft.FilledButton(
                        "Submit training item",
                        icon=ft.Icons.ADD,
                        on_click=lambda _: open_submission_dialog(),
                    ),
                    report_button,
                ],
                wrap=True,
            ),
            report_progress,
            status,
            ft.Divider(),
            ft.Text(
                "Tracked Training",
                size=22,
                weight=ft.FontWeight.BOLD,
            ),
            empty_history,
            history_list,
        ],
        expand=True,
        padding=32,
        spacing=16,
    )
    return ft.View(
        route="/monthly-training",
        bgcolor=ft.Colors.WHITE,
        appbar=ft.AppBar(
            leading=ft.IconButton(
                icon=ft.Icons.ARROW_BACK,
                tooltip="Back to home",
                on_click=navigate_home,
            ),
            title=ft.Text("Monthly Training"),
            bgcolor=ft.Colors.WHITE,
        ),
        controls=[page_content],
    )
