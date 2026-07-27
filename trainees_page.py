"""Trainee assignment and training-information page."""

from datetime import datetime

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


def build_trainees_view(page: ft.Page) -> ft.View:
    """Build the trainee selector and selected trainee's training details."""
    members = load_records("team_members")
    profiles = load_records("trainees")
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
            message.value = "Training information saved."
            message.color = ft.Colors.GREEN_700
            message.visible = True
            details.update()

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
                                    "Save training information",
                                    icon=ft.Icons.SAVE,
                                    on_click=save_training,
                                ),
                                create_directory_button,
                                message,
                            ],
                            wrap=True,
                        ),
                        creation_progress,
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
