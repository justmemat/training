"""Trainee assignment and training-information page."""

from datetime import date, datetime
from pathlib import Path

import flet as ft

from data_store import load_records, save_records
from team_member_service import display_name
from trainee_service import (
    TRAINING_PHASES,
    ensure_profile,
    format_start_date,
    update_profile,
)
from training_directory_service import create_training_directory, trainee_directory_exists
from training_history_service import (
    create_history_record,
    open_report_file,
    trainee_history,
)
from history_report_service import generate_history_report
from training_report_service import create_training_report


def build_trainees_view(page: ft.Page) -> ft.View:
    """Build the trainee selector and selected trainee's training details."""
    members = load_records("team_members")
    profiles = load_records("trainees")
    history_records = load_records("training_history")
    trainee_selector = ft.Dropdown(
        label="Select a trainee", width=420, prefix_icon=ft.Icons.SCHOOL
    )
    details = ft.Column()

    def assigned_members() -> list[dict]:
        return sorted(
            (member for member in members if member.get("is_trainee")),
            key=lambda member: (
                str(member.get("last_name", "")).lower(),
                str(member.get("first_name", "")).lower(),
            ),
        )

    def save_all() -> None:
        save_records("team_members", members)
        save_records("trainees", profiles)

    def render_details() -> None:
        member = next(
            (
                item
                for item in assigned_members()
                if item.get("id") == trainee_selector.value
            ),
            None,
        )
        if member is None:
            details.controls = [
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Icon(ft.Icons.PERSON_SEARCH, size=58, color=ft.Colors.INDIGO_300),
                            ft.Text("Select a trainee to view training information.", size=17),
                        ],
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=14,
                    ),
                    alignment=ft.alignment.center,
                    padding=60,
                )
            ]
            return

        profile = ensure_profile(profiles, member["id"])
        selected_start_date = str(profile.get("start_date", ""))
        start_date = ft.TextField(
            label="Start date",
            value=format_start_date(selected_start_date),
            hint_text="Select a date",
            prefix_icon=ft.Icons.CALENDAR_MONTH,
            read_only=True,
            width=260,
        )

        def date_selected(_: ft.ControlEvent) -> None:
            nonlocal selected_start_date
            if date_picker.value is None:
                return
            selected_start_date = date_picker.value.strftime("%Y-%m-%d")
            start_date.value = format_start_date(selected_start_date)
            start_date.update()

        date_picker = ft.DatePicker(
            value=(
                datetime.fromisoformat(selected_start_date)
                if selected_start_date
                else datetime.now()
            ),
            first_date=datetime(2000, 1, 1),
            last_date=datetime(2100, 12, 31),
            help_text="Select trainee start date",
            on_change=date_selected,
        )
        start_date.on_click = lambda _: page.open(date_picker)
        phase = ft.Dropdown(
            label="Training Phase",
            value=profile.get("training_phase", TRAINING_PHASES[0]),
            options=[ft.dropdown.Option(value) for value in TRAINING_PHASES],
            width=260,
        )
        def member_dropdown_options() -> list[ft.dropdown.Option]:
            return [
                ft.dropdown.Option(key="", text="Unassigned"),
                *[
                    ft.dropdown.Option(
                        key=team_member["id"],
                        text=f"{team_member.get('first_name', '')} "
                        f"{team_member.get('last_name', '')} "
                        f"({team_member.get('operating_initials', '')})",
                    )
                    for team_member in sorted(
                        members,
                        key=lambda item: (
                            str(item.get("last_name", "")).lower(),
                            str(item.get("first_name", "")).lower(),
                        ),
                    )
                ],
            ]
        manager_options = [
            ft.dropdown.Option(key="", text="Unassigned"),
            *[
                ft.dropdown.Option(
                    key=manager["id"],
                    text=f"{manager.get('first_name', '')} "
                    f"{manager.get('last_name', '')} "
                    f"({manager.get('operating_initials', '')})",
                )
                for manager in sorted(
                    (item for item in members if item.get("is_manager")),
                    key=lambda item: (
                        str(item.get("last_name", "")).lower(),
                        str(item.get("first_name", "")).lower(),
                    ),
                )
            ],
        ]
        member_ids = {str(item.get("id", "")) for item in members}
        manager_ids = {
            str(item.get("id", "")) for item in members if item.get("is_manager")
        }
        primary_value = str(profile.get("primary_instructor_id", ""))
        secondary_value = str(profile.get("secondary_instructor_id", ""))
        manager_value = str(profile.get("manager_id", ""))
        primary_instructor = ft.Dropdown(
            label="Primary instructor",
            value=primary_value if primary_value in member_ids else "",
            options=member_dropdown_options(),
            width=310,
            prefix_icon=ft.Icons.PERSON,
        )
        secondary_instructor = ft.Dropdown(
            label="Secondary instructor",
            value=secondary_value if secondary_value in member_ids else "",
            options=member_dropdown_options(),
            width=310,
            prefix_icon=ft.Icons.PERSON_OUTLINE,
        )
        assigned_manager = ft.Dropdown(
            label="Assigned manager",
            value=manager_value if manager_value in manager_ids else "",
            options=manager_options,
            width=310,
            prefix_icon=ft.Icons.BADGE,
        )
        message = ft.Text(visible=False)
        creation_progress = ft.ProgressBar(
            visible=False,
            color=ft.Colors.INDIGO_600,
            bgcolor=ft.Colors.INDIGO_100,
        )
        directory_already_exists = trainee_directory_exists(member)
        history_report_progress = ft.ProgressBar(
            visible=False,
            color=ft.Colors.INDIGO_600,
            bgcolor=ft.Colors.INDIGO_100,
        )

        def update_training_profile() -> bool:
            try:
                update_profile(
                    profile,
                    start_date=selected_start_date,
                    training_phase=phase.value or "",
                    primary_instructor_id=primary_instructor.value or "",
                    secondary_instructor_id=secondary_instructor.value or "",
                    manager_id=assigned_manager.value or "",
                    team_members=members,
                )
            except ValueError as error:
                message.value = str(error)
                message.color = ft.Colors.RED_700
                message.visible = True
                details.update()
                return False
            save_all()
            return True

        def save_training(_: ft.ControlEvent) -> None:
            if not update_training_profile():
                return
            render_details()
            page.update()
            page.open(ft.SnackBar(ft.Text("Training information saved.")))

        def build_training_directory(_: ft.ControlEvent) -> None:
            if not update_training_profile():
                return
            create_directory_button.disabled = True
            creation_progress.visible = True
            message.value = "Creating training directory and populating the guide..."
            message.color = ft.Colors.INDIGO_700
            message.visible = True
            details.update()
            try:
                output_path = create_training_directory(member, profile, members)
            except ModuleNotFoundError as error:
                if error.name != "pypdf":
                    raise
                message.value = (
                    "PDF support is not installed. Close the app, open Command Prompt "
                    "in the application folder, and run: "
                    "python -m pip install -r requirements.txt"
                )
                message.color = ft.Colors.RED_700
                message.visible = True
                creation_progress.visible = False
                create_directory_button.disabled = trainee_directory_exists(member)
                details.update()
                return
            except (FileNotFoundError, OSError, ValueError) as error:
                message.value = str(error)
                message.color = ft.Colors.RED_700
                message.visible = True
                creation_progress.visible = False
                create_directory_button.disabled = trainee_directory_exists(member)
                details.update()
                return
            message.value = f"Training directory created: {output_path}"
            message.color = ft.Colors.GREEN_700
            message.visible = True
            creation_progress.visible = False
            create_directory_button.disabled = True
            daily_report_button.disabled = False
            daily_report_button.tooltip = "Create a populated daily training report"
            history_report_button.disabled = False
            history_report_button.tooltip = "Create or update the Excel training history report"
            details.update()

        create_directory_button = ft.OutlinedButton(
            "Create training directory",
            icon=ft.Icons.CREATE_NEW_FOLDER,
            disabled=directory_already_exists,
            tooltip=(
                "A directory already exists for these operating initials."
                if directory_already_exists
                else "Create the trainee directory and populated training guide"
            ),
            on_click=build_training_directory,
        )

        history_list = ft.Column(spacing=8)
        history_empty = ft.Text(
            "No daily training reports have been recorded.",
            color=ft.Colors.GREY_600,
            italic=True,
        )

        def render_history() -> None:
            entries = trainee_history(history_records, str(member.get("id", "")))
            history_empty.visible = not entries
            history_list.controls = []
            for entry in entries:
                instructor_member = next(
                    (
                        item
                        for item in members
                        if item.get("id") == entry.get("instructor_id")
                    ),
                    None,
                )
                instructor_name = (
                    f"{instructor_member.get('first_name', '')} "
                    f"{instructor_member.get('last_name', '')} "
                    f"({instructor_member.get('operating_initials', '')})"
                    if instructor_member
                    else "Unknown instructor"
                )

                def open_report(_: ft.ControlEvent, history_entry: dict = entry) -> None:
                    try:
                        open_report_file(history_entry)
                    except (FileNotFoundError, OSError, ValueError) as error:
                        page.open(ft.SnackBar(ft.Text(str(error))))

                history_list.controls.append(
                    ft.Container(
                        content=ft.Row(
                            [
                                ft.IconButton(
                                    icon=ft.Icons.DESCRIPTION,
                                    icon_color=ft.Colors.INDIGO_500,
                                    tooltip=f"Open {entry.get('file_name', 'training report')}",
                                    on_click=open_report,
                                ),
                                ft.Column(
                                    [
                                        ft.Text(
                                            format_start_date(str(entry.get("date", ""))),
                                            weight=ft.FontWeight.BOLD,
                                        ),
                                        ft.Text(
                                            f"Instructor: {instructor_name}",
                                            color=ft.Colors.GREY_700,
                                        ),
                                        ft.Text(
                                            str(
                                                entry.get("file_name")
                                                or Path(
                                                    str(entry.get("report_path", ""))
                                                ).name
                                            ),
                                            size=12,
                                            color=ft.Colors.GREY_500,
                                        ),
                                    ],
                                    spacing=2,
                                    expand=True,
                                ),
                            ]
                        ),
                        bgcolor=ft.Colors.INDIGO_50,
                        border_radius=8,
                        padding=12,
                    )
                )

        render_history()

        def open_daily_report_dialog() -> None:
            if not update_training_profile():
                return
            instructor = ft.Dropdown(
                label="Instructor",
                options=member_dropdown_options()[1:],
                width=420,
                prefix_icon=ft.Icons.PERSON,
            )
            training_summary = ft.TextField(
                label="Training Summary",
                multiline=True,
                min_lines=4,
                max_lines=8,
                width=560,
            )
            instructor_comments = ft.TextField(
                label="Instructor Comments (optional)",
                multiline=True,
                min_lines=4,
                max_lines=8,
                width=560,
            )
            report_message = ft.Text(visible=False)
            report_progress = ft.ProgressBar(
                visible=False,
                color=ft.Colors.INDIGO_600,
                bgcolor=ft.Colors.INDIGO_100,
            )

            def create_report(_: ft.ControlEvent) -> None:
                generate_button.disabled = True
                report_progress.visible = True
                report_message.value = "Creating and saving the daily training report..."
                report_message.color = ft.Colors.INDIGO_700
                report_message.visible = True
                dialog.update()
                try:
                    generated_on = date.today()
                    output_path = create_training_report(
                        member,
                        profile,
                        members,
                        instructor_id=instructor.value or "",
                        training_summary=training_summary.value or "",
                        instructor_comments=instructor_comments.value or "",
                        report_date=generated_on,
                    )
                    history_records.append(
                        create_history_record(
                            trainee_id=str(member.get("id", "")),
                            instructor_id=instructor.value or "",
                            report_date=generated_on,
                            report_path=str(output_path),
                        )
                    )
                    save_records("training_history", history_records)
                except ModuleNotFoundError as error:
                    if error.name != "pypdf":
                        raise
                    report_message.value = (
                        "PDF support is not installed. Run: "
                        "python -m pip install -r requirements.txt"
                    )
                except (FileNotFoundError, OSError, ValueError) as error:
                    report_message.value = str(error)
                else:
                    report_message.value = f"Daily training report created: {output_path}"
                    report_message.color = ft.Colors.GREEN_700
                    report_progress.visible = False
                    generate_button.disabled = False
                    render_history()
                    details.update()
                    dialog.update()
                    return
                report_message.color = ft.Colors.RED_700
                report_progress.visible = False
                generate_button.disabled = False
                dialog.update()

            generate_button = ft.FilledButton(
                "Create report", icon=ft.Icons.PICTURE_AS_PDF, on_click=create_report
            )
            dialog = ft.AlertDialog(
                modal=True,
                title=ft.Text("Add daily training report"),
                content=ft.Container(
                    content=ft.Column(
                        [
                            instructor,
                            training_summary,
                            instructor_comments,
                            report_message,
                            report_progress,
                        ],
                        tight=True,
                        spacing=14,
                        scroll=ft.ScrollMode.AUTO,
                    ),
                    width=580,
                ),
                actions=[
                    ft.TextButton("Close", on_click=lambda _: page.close(dialog)),
                    generate_button,
                ],
            )
            page.open(dialog)

        daily_report_button = ft.OutlinedButton(
            "Add daily training report",
            icon=ft.Icons.NOTE_ADD,
            disabled=not directory_already_exists,
            tooltip=(
                "Create the trainee's training directory first."
                if not directory_already_exists
                else "Create a populated daily training report"
            ),
            on_click=lambda _: open_daily_report_dialog(),
        )

        def assigned_name(member_id: str) -> str:
            assigned = next(
                (item for item in members if item.get("id") == member_id), None
            )
            if assigned is None:
                return "Unassigned"
            return (
                f"{assigned.get('first_name', '')} {assigned.get('last_name', '')} "
                f"({assigned.get('operating_initials', '')})"
            ).strip()

        plain_information = ft.Column(
            [
                ft.Row(
                    [
                        ft.Column(
                            [
                                ft.Text("Start date", color=ft.Colors.GREY_600),
                                ft.Text(
                                    format_start_date(selected_start_date) or "Not assigned",
                                    size=17,
                                    weight=ft.FontWeight.W_500,
                                ),
                            ],
                            width=260,
                        ),
                        ft.Column(
                            [
                                ft.Text("Training Phase", color=ft.Colors.GREY_600),
                                ft.Text(
                                    str(profile.get("training_phase", TRAINING_PHASES[0])),
                                    size=17,
                                    weight=ft.FontWeight.W_500,
                                ),
                            ],
                            width=260,
                        ),
                    ],
                    wrap=True,
                    spacing=18,
                ),
                ft.Text(
                    "Training Team",
                    size=18,
                    weight=ft.FontWeight.BOLD,
                    color=ft.Colors.INDIGO_900,
                ),
                ft.Row(
                    [
                        ft.Column(
                            [
                                ft.Text("Primary instructor", color=ft.Colors.GREY_600),
                                ft.Text(assigned_name(primary_value), size=16),
                            ],
                            width=280,
                        ),
                        ft.Column(
                            [
                                ft.Text("Secondary instructor", color=ft.Colors.GREY_600),
                                ft.Text(assigned_name(secondary_value), size=16),
                            ],
                            width=280,
                        ),
                        ft.Column(
                            [
                                ft.Text("Assigned manager", color=ft.Colors.GREY_600),
                                ft.Text(assigned_name(manager_value), size=16),
                            ],
                            width=280,
                        ),
                    ],
                    wrap=True,
                    spacing=18,
                ),
            ],
            spacing=18,
        )

        def cancel_edit(_: ft.ControlEvent) -> None:
            render_details()
            page.update()

        editing_information = ft.Column(
            [
                ft.Row([start_date, phase], wrap=True, spacing=18),
                ft.Text(
                    "Training Team",
                    size=18,
                    weight=ft.FontWeight.BOLD,
                    color=ft.Colors.INDIGO_900,
                ),
                ft.Row(
                    [primary_instructor, secondary_instructor, assigned_manager],
                    wrap=True,
                    spacing=18,
                ),
                ft.Row(
                    [
                        ft.FilledButton(
                            "Save changes", icon=ft.Icons.SAVE, on_click=save_training
                        ),
                        ft.TextButton("Cancel", on_click=cancel_edit),
                    ]
                ),
            ],
            visible=False,
            spacing=18,
        )

        def begin_edit(_: ft.ControlEvent) -> None:
            plain_information.visible = False
            editing_information.visible = True
            edit_button.visible = False
            details.update()

        edit_button = ft.FilledTonalButton(
            "Edit training information", icon=ft.Icons.EDIT, on_click=begin_edit
        )

        def build_history_report(_: ft.ControlEvent) -> None:
            history_report_button.disabled = True
            history_report_progress.visible = True
            message.value = "Creating or updating the Excel history report..."
            message.color = ft.Colors.INDIGO_700
            message.visible = True
            details.update()
            try:
                output_path = generate_history_report(
                    member, profile, members, history_records
                )
                open_report_file({"report_path": str(output_path)})
            except ModuleNotFoundError as error:
                if error.name != "openpyxl":
                    raise
                message.value = (
                    "Excel support is not installed. Run: "
                    "python -m pip install -r requirements.txt"
                )
                message.color = ft.Colors.RED_700
            except (FileNotFoundError, OSError, ValueError) as error:
                message.value = str(error)
                message.color = ft.Colors.RED_700
            else:
                message.value = f"History report created and opened: {output_path}"
                message.color = ft.Colors.GREEN_700
            history_report_progress.visible = False
            history_report_button.disabled = not trainee_directory_exists(member)
            details.update()

        history_report_button = ft.OutlinedButton(
            "Generate History Report",
            icon=ft.Icons.TABLE_VIEW,
            disabled=not directory_already_exists,
            tooltip=(
                "Create the trainee's training directory first."
                if not directory_already_exists
                else "Create or update the Excel training history report"
            ),
            on_click=build_history_report,
        )

        details.controls = [
            ft.Container(
                content=ft.Column(
                    [
                        ft.Row(
                            [
                                ft.CircleAvatar(
                                    content=ft.Text(
                                        str(member.get("operating_initials", "")).upper(),
                                        weight=ft.FontWeight.BOLD,
                                    ),
                                    radius=30,
                                    bgcolor=ft.Colors.INDIGO_100,
                                    color=ft.Colors.INDIGO_900,
                                ),
                                ft.Column(
                                    [
                                        ft.Text(
                                            f"{member.get('first_name', '')} "
                                            f"{member.get('last_name', '')}",
                                            size=26,
                                            weight=ft.FontWeight.BOLD,
                                        ),
                                        ft.Text(
                                            f"Operating initials: "
                                            f"{member.get('operating_initials', '')}",
                                            color=ft.Colors.GREY_700,
                                        ),
                                    ],
                                    spacing=2,
                                ),
                            ],
                            spacing=18,
                        ),
                        ft.Divider(),
                        plain_information,
                        editing_information,
                        ft.Row(
                            [
                                edit_button,
                                create_directory_button,
                                daily_report_button,
                                history_report_button,
                                message,
                            ],
                            wrap=True,
                        ),
                        creation_progress,
                        history_report_progress,
                        ft.Divider(height=28),
                        ft.Text(
                            "Training History",
                            size=20,
                            weight=ft.FontWeight.BOLD,
                            color=ft.Colors.INDIGO_900,
                        ),
                        history_empty,
                        history_list,
                    ],
                    spacing=18,
                ),
                bgcolor=ft.Colors.WHITE,
                border=ft.border.all(1, ft.Colors.INDIGO_100),
                border_radius=14,
                padding=28,
            )
        ]

    def refresh_selector(selected_id: str | None = None) -> None:
        assigned = assigned_members()
        trainee_selector.options = [
            ft.dropdown.Option(
                key=member["id"],
                text=f"{display_name(member)} ({member.get('operating_initials', '')})",
            )
            for member in assigned
        ]
        valid_ids = {member["id"] for member in assigned}
        trainee_selector.value = selected_id if selected_id in valid_ids else None
        render_details()

    def add_trainee_dialog() -> None:
        available = [member for member in members if not member.get("is_trainee")]
        if not available:
            page.open(
                ft.SnackBar(ft.Text("All team members are already assigned as trainees."))
            )
            return
        selection = ft.Dropdown(
            label="Team member",
            width=400,
            options=[
                ft.dropdown.Option(
                    key=member["id"],
                    text=f"{member.get('first_name', '')} {member.get('last_name', '')} "
                    f"({member.get('operating_initials', '')})",
                )
                for member in available
            ],
        )
        error = ft.Text("Select a team member.", color=ft.Colors.RED_700, visible=False)

        def add_trainee(_: ft.ControlEvent) -> None:
            member = next(
                (item for item in available if item.get("id") == selection.value), None
            )
            if member is None:
                error.visible = True
                dialog.update()
                return
            member["is_trainee"] = True
            ensure_profile(profiles, member["id"])
            save_all()
            page.close(dialog)
            refresh_selector(member["id"])
            page.update()

        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Add trainee"),
            content=ft.Column([selection, error], tight=True),
            actions=[
                ft.TextButton("Cancel", on_click=lambda _: page.close(dialog)),
                ft.FilledButton("Add", icon=ft.Icons.PERSON_ADD, on_click=add_trainee),
            ],
        )
        page.open(dialog)

    trainee_selector.on_change = lambda _: (render_details(), page.update())
    refresh_selector()
    return ft.View(
        route="/trainees",
        bgcolor=ft.Colors.INDIGO_50,
        appbar=ft.AppBar(
            leading=ft.IconButton(
                icon=ft.Icons.ARROW_BACK,
                tooltip="Back to home",
                on_click=lambda _: page.go("/"),
            ),
            title=ft.Text("Trainees"),
            bgcolor=ft.Colors.WHITE,
        ),
        controls=[
            ft.Container(
                content=ft.Column(
                    [
                        ft.Row(
                            [
                                ft.Column(
                                    [
                                        ft.Text("Trainees", size=30, weight=ft.FontWeight.BOLD),
                                        ft.Text(
                                            "Select a trainee to review or update their training.",
                                            color=ft.Colors.GREY_700,
                                        ),
                                    ],
                                    expand=True,
                                ),
                                ft.FilledButton(
                                    "Add trainee",
                                    icon=ft.Icons.PERSON_ADD,
                                    on_click=lambda _: add_trainee_dialog(),
                                ),
                            ]
                        ),
                        trainee_selector,
                        details,
                    ],
                    spacing=22,
                ),
                padding=32,
                width=900,
            )
        ],
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        scroll=ft.ScrollMode.AUTO,
    )
