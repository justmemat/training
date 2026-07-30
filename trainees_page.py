"""Trainee assignment and training-information page."""

import asyncio
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
from training_directory_service import (
    copy_files_to_uploads,
    create_training_directory,
    open_directory,
    trainee_directory_exists,
    training_guide_path,
    uploads_directory,
)
from training_history_service import (
    create_history_record,
    open_report_file,
    trainee_history,
)
from history_report_service import generate_history_report
from progress_dialog import FileProgressDialog
from training_report_service import create_training_report


def build_trainees_view(page: ft.Page) -> ft.View:
    """Build the trainee selector and selected trainee's training details."""

    async def navigate_home(_: ft.ControlEvent) -> None:
        await page.push_route("/")

    members = load_records("team_members")
    profiles = load_records("trainees")
    history_records = load_records("training_history")
    trainee_selector = ft.Dropdown(
        label="Select a trainee", width=420, leading_icon=ft.Icons.SCHOOL
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
                            ft.Icon(
                                ft.Icons.PERSON_SEARCH,
                                size=58,
                                color=ft.Colors.PRIMARY,
                            ),
                            ft.Text(
                                "Select a trainee to view training information.",
                                size=17,
                            ),
                        ],
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=14,
                    ),
                    alignment=ft.Alignment.CENTER,
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
        start_date.on_click = lambda _: page.show_dialog(date_picker)
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
            leading_icon=ft.Icons.PERSON,
        )
        secondary_instructor = ft.Dropdown(
            label="Secondary instructor",
            value=secondary_value if secondary_value in member_ids else "",
            options=member_dropdown_options(),
            width=310,
            leading_icon=ft.Icons.PERSON_OUTLINE,
        )
        assigned_manager = ft.Dropdown(
            label="Assigned manager",
            value=manager_value if manager_value in manager_ids else "",
            options=manager_options,
            width=310,
            leading_icon=ft.Icons.BADGE,
        )
        message = ft.Text(visible=False)
        directory_already_exists = trainee_directory_exists(member)
        guide_already_exists = training_guide_path(member).is_file()

        def update_training_profile(*, persist: bool = True) -> bool:
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
            if persist:
                save_all()
            return True

        async def save_training(_: ft.ControlEvent) -> None:
            if not update_training_profile(persist=False):
                return
            progress_ui = FileProgressDialog(
                page,
                "Saving trainee information",
                ["Validate training information", "Save trainee profile"],
            )
            progress_ui.show()
            await progress_ui.set_step(0, complete=True)
            await progress_ui.set_step(1)
            await asyncio.to_thread(save_all)
            await progress_ui.set_step(1, complete=True)
            render_details()
            page.update()
            progress_ui.close()

        async def build_training_directory(_: ft.ControlEvent) -> None:
            if not update_training_profile():
                return
            create_directory_button.disabled = True
            progress_ui = FileProgressDialog(
                page,
                "Creating trainee directory",
                [
                    "Validate trainee profile",
                    "Create folders",
                    "Populate training guide",
                ],
            )
            progress_ui.show()
            try:
                await progress_ui.set_step(0)
                await progress_ui.set_step(1)
                output_path = await asyncio.to_thread(
                    create_training_directory, member, profile, members
                )
                await progress_ui.set_step(2, complete=True)
            except ModuleNotFoundError as error:
                if error.name != "pypdf":
                    raise
                progress_ui.show_error(
                    "PDF support is not installed. Close the app, open Command Prompt "
                    "in the application folder, and run: "
                    "python -m pip install -r requirements.txt"
                )
                create_directory_button.disabled = trainee_directory_exists(member)
                return
            except (FileNotFoundError, OSError, ValueError) as error:
                progress_ui.show_error(error)
                create_directory_button.disabled = trainee_directory_exists(member)
                return
            message.value = f"Training directory created: {output_path}"
            message.color = ft.Colors.GREEN_700
            message.visible = True
            create_directory_button.disabled = True
            daily_report_button.disabled = False
            daily_report_button.tooltip = "Create a populated daily training report"
            history_report_button.disabled = False
            history_report_button.tooltip = (
                "Create or update the Excel training history report"
            )
            open_guide_button.disabled = False
            upload_files_button.disabled = False
            view_uploads_button.disabled = False
            details.update()
            progress_ui.close()

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

        async def open_training_guide(_: ft.ControlEvent) -> None:
            progress_ui = FileProgressDialog(
                page, "Opening training guide", ["Locate training guide", "Open PDF"]
            )
            progress_ui.show()
            try:
                await progress_ui.set_step(0)
                guide_path = training_guide_path(member)
                if not guide_path.is_file():
                    raise FileNotFoundError(
                        f"Training guide was not found: {guide_path}"
                    )
                await progress_ui.set_step(1)
                await asyncio.to_thread(
                    open_report_file, {"report_path": str(guide_path)}
                )
                await progress_ui.set_step(1, complete=True)
            except (FileNotFoundError, OSError, ValueError) as error:
                progress_ui.show_error(error)
                return
            progress_ui.close()

        open_guide_button = ft.OutlinedButton(
            "Open training guide",
            icon=ft.Icons.PICTURE_AS_PDF,
            disabled=not guide_already_exists,
            tooltip=(
                "Open the populated training guide"
                if guide_already_exists
                else "Create the trainee's training directory first."
            ),
            on_click=open_training_guide,
        )

        async def upload_files(_: ft.ControlEvent) -> None:
            selected = await ft.FilePicker().pick_files(
                dialog_title="Select files to upload", allow_multiple=True
            )
            if not selected:
                return
            progress_ui = FileProgressDialog(
                page,
                "Uploading trainee files",
                ["Validate selected files", "Copy files to Uploads"],
            )
            progress_ui.show()
            try:
                await progress_ui.set_step(0)
                paths = [item.path for item in selected if item.path]
                if len(paths) != len(selected):
                    raise ValueError("One or more selected files cannot be accessed.")
                await progress_ui.set_step(1)
                copied = await asyncio.to_thread(copy_files_to_uploads, member, paths)
                await progress_ui.set_step(1, complete=True)
            except (FileNotFoundError, OSError, ValueError) as error:
                progress_ui.show_error(error)
                return
            message.value = f"Uploaded {len(copied)} file(s) to the Uploads folder."
            message.color = ft.Colors.GREEN_700
            message.visible = True
            details.update()
            progress_ui.close()

        async def view_uploaded_files(_: ft.ControlEvent) -> None:
            progress_ui = FileProgressDialog(
                page, "Opening uploaded files", ["Locate Uploads folder", "Open folder"]
            )
            progress_ui.show()
            try:
                await progress_ui.set_step(0)
                directory = uploads_directory(member)
                await progress_ui.set_step(1)
                await asyncio.to_thread(open_directory, directory)
                await progress_ui.set_step(1, complete=True)
            except (FileNotFoundError, OSError, ValueError) as error:
                progress_ui.show_error(error)
                return
            progress_ui.close()

        upload_files_button = ft.OutlinedButton(
            "Upload files",
            icon=ft.Icons.UPLOAD_FILE,
            disabled=not directory_already_exists,
            on_click=upload_files,
        )
        view_uploads_button = ft.OutlinedButton(
            "View uploaded files",
            icon=ft.Icons.FOLDER_OPEN,
            disabled=not directory_already_exists,
            on_click=view_uploaded_files,
        )

        history_list = ft.Column(spacing=8)
        history_empty = ft.Text(
            "No daily training reports have been recorded.",
            color=ft.Colors.ON_SURFACE_VARIANT,
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

                async def open_report(
                    _: ft.ControlEvent, history_entry: dict = entry
                ) -> None:
                    progress_ui = FileProgressDialog(
                        page, "Opening daily training report", ["Open report file"]
                    )
                    progress_ui.show()
                    try:
                        await progress_ui.set_step(0)
                        await asyncio.to_thread(open_report_file, history_entry)
                        await progress_ui.set_step(0, complete=True)
                    except (FileNotFoundError, OSError, ValueError) as error:
                        progress_ui.show_error(error)
                        return
                    progress_ui.close()

                def confirm_delete(
                    _: ft.ControlEvent, history_entry: dict = entry
                ) -> None:
                    async def delete_entry(_: ft.ControlEvent) -> None:
                        progress_ui = FileProgressDialog(
                            page,
                            "Deleting daily training entry",
                            ["Remove history entry", "Save training history"],
                        )
                        progress_ui.show(replace_current=True)
                        try:
                            await progress_ui.set_step(0)
                            history_records.remove(history_entry)
                            await progress_ui.set_step(1)
                            await asyncio.to_thread(
                                save_records, "training_history", history_records
                            )
                            await progress_ui.set_step(1, complete=True)
                        except (OSError, ValueError) as error:
                            progress_ui.show_error(error)
                            return
                        render_history()
                        details.update()
                        progress_ui.close()

                    page.show_dialog(
                        ft.AlertDialog(
                            modal=True,
                            title=ft.Text("Delete training entry?"),
                            content=ft.Text(
                                f"Delete {history_entry.get('file_name', 'this training entry')}?"
                            ),
                            actions=[
                                ft.TextButton(
                                    "Cancel", on_click=lambda _: page.pop_dialog()
                                ),
                                ft.FilledButton(
                                    "Delete",
                                    icon=ft.Icons.DELETE,
                                    style=ft.ButtonStyle(bgcolor=ft.Colors.RED_600),
                                    on_click=delete_entry,
                                ),
                            ],
                        )
                    )

                history_list.controls.append(
                    ft.ContextMenu(
                        content=ft.Container(
                            content=ft.Row(
                                [
                                    ft.IconButton(
                                        icon=ft.Icons.DESCRIPTION,
                                        icon_color=ft.Colors.PRIMARY,
                                        tooltip=f"Open {entry.get('file_name', 'training report')}",
                                        on_click=open_report,
                                    ),
                                    ft.Column(
                                        [
                                            ft.Text(
                                                format_start_date(
                                                    str(entry.get("date", ""))
                                                ),
                                                weight=ft.FontWeight.BOLD,
                                            ),
                                            ft.Text(
                                                f"Instructor: {instructor_name}",
                                                color=ft.Colors.ON_SURFACE_VARIANT,
                                            ),
                                            ft.Text(
                                                str(
                                                    entry.get("file_name")
                                                    or Path(
                                                        str(
                                                            entry.get("report_path", "")
                                                        )
                                                    ).name
                                                ),
                                                size=12,
                                                color=ft.Colors.ON_SURFACE_VARIANT,
                                            ),
                                        ],
                                        spacing=2,
                                        expand=True,
                                    ),
                                ]
                            ),
                            bgcolor=ft.Colors.SURFACE_CONTAINER,
                            border_radius=8,
                            padding=12,
                        ),
                        secondary_items=[
                            ft.PopupMenuItem(
                                content="Edit",
                                icon=ft.Icons.EDIT,
                                on_click=lambda _, history_entry=entry: open_daily_report_dialog(
                                    history_entry
                                ),
                            ),
                            ft.PopupMenuItem(
                                content="Delete",
                                icon=ft.Icons.DELETE_OUTLINE,
                                on_click=confirm_delete,
                            ),
                        ],
                    )
                )

        render_history()

        def open_daily_report_dialog(record: dict | None = None) -> None:
            if not update_training_profile():
                return
            editing = record is not None
            instructor = ft.Dropdown(
                label="Instructor",
                options=member_dropdown_options()[1:],
                width=420,
                leading_icon=ft.Icons.PERSON,
                value=str(record.get("instructor_id", "")) if record else None,
            )
            training_summary = ft.TextField(
                label="Training Summary",
                multiline=True,
                min_lines=4,
                max_lines=8,
                width=560,
                value=str(record.get("training_summary", "")) if record else "",
            )
            instructor_comments = ft.TextField(
                label="Instructor Comments (optional)",
                multiline=True,
                min_lines=4,
                max_lines=8,
                width=560,
                value=str(record.get("instructor_comments", "")) if record else "",
            )
            selected_report_date = (
                date.fromisoformat(str(record.get("date", "")))
                if record
                else date.today()
            )
            report_date_field = ft.TextField(
                label="Report date",
                value=selected_report_date.strftime("%d %b %Y"),
                hint_text="Select a date",
                read_only=True,
                width=280,
                prefix_icon=ft.Icons.CALENDAR_MONTH,
            )

            def report_date_selected(_: ft.ControlEvent) -> None:
                nonlocal selected_report_date
                if report_date_picker.value is None:
                    return
                selected_report_date = (
                    report_date_picker.value.date()
                    if isinstance(report_date_picker.value, datetime)
                    else report_date_picker.value
                )
                report_date_field.value = selected_report_date.strftime("%d %b %Y")
                report_date_field.update()

            report_date_picker = ft.DatePicker(
                value=selected_report_date,
                first_date=date(2000, 1, 1),
                last_date=date(2100, 12, 31),
                help_text="Select daily report date",
                on_change=report_date_selected,
            )
            report_date_field.on_click = lambda _: page.show_dialog(report_date_picker)

            async def create_report(_: ft.ControlEvent) -> None:
                generate_button.disabled = True
                dialog.update()

                progress_ui = FileProgressDialog(
                    page,
                    (
                        "Updating daily training report"
                        if editing
                        else "Creating daily training report"
                    ),
                    [
                        "Validate report details",
                        "Create and save PDF report",
                        "Record report in training history",
                        "Refresh trainee report history",
                    ],
                )
                progress_ui.show(replace_current=True)

                try:
                    await progress_ui.set_step(0)
                    await progress_ui.set_step(1)
                    output_path = await asyncio.to_thread(
                        create_training_report,
                        member,
                        profile,
                        members,
                        instructor_id=instructor.value or "",
                        training_summary=training_summary.value or "",
                        instructor_comments=instructor_comments.value or "",
                        report_date=selected_report_date,
                    )
                    await progress_ui.set_step(1, complete=True)
                    await progress_ui.set_step(2)
                    updated_record = create_history_record(
                        trainee_id=str(member.get("id", "")),
                        instructor_id=instructor.value or "",
                        report_date=selected_report_date,
                        report_path=str(output_path),
                        training_summary=training_summary.value or "",
                        instructor_comments=instructor_comments.value or "",
                    )
                    if editing:
                        updated_record["id"] = record.get("id", updated_record["id"])
                        history_records[history_records.index(record)] = updated_record
                    else:
                        history_records.append(updated_record)
                    await asyncio.to_thread(
                        save_records, "training_history", history_records
                    )
                    await progress_ui.set_step(2, complete=True)
                except ModuleNotFoundError as error:
                    if error.name != "pypdf":
                        raise
                    progress_ui.show_error(
                        "PDF support is not installed. Run: "
                        "python -m pip install -r requirements.txt"
                    )
                    return
                except (FileNotFoundError, OSError, ValueError) as error:
                    progress_ui.show_error(error)
                    return
                else:
                    await progress_ui.set_step(3)
                    render_history()
                    details.update()
                    await progress_ui.set_step(3, complete=True)
                    progress_ui.close()
                    return

            generate_button = ft.FilledButton(
                "Save report" if editing else "Create report",
                icon=ft.Icons.PICTURE_AS_PDF,
                on_click=create_report,
            )
            dialog = ft.AlertDialog(
                modal=True,
                title=ft.Text(
                    "Edit daily training report"
                    if editing
                    else "Add daily training report"
                ),
                content=ft.Container(
                    content=ft.Column(
                        [
                            report_date_field,
                            instructor,
                            training_summary,
                            instructor_comments,
                        ],
                        tight=True,
                        spacing=14,
                        scroll=ft.ScrollMode.AUTO,
                    ),
                    width=580,
                ),
                actions=[
                    ft.TextButton("Close", on_click=lambda _: page.pop_dialog()),
                    generate_button,
                ],
            )
            page.show_dialog(dialog)

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
                                ft.Text(
                                    "Start date", color=ft.Colors.ON_SURFACE_VARIANT
                                ),
                                ft.Text(
                                    format_start_date(selected_start_date)
                                    or "Not assigned",
                                    size=17,
                                    weight=ft.FontWeight.W_500,
                                ),
                            ],
                            width=260,
                        ),
                        ft.Column(
                            [
                                ft.Text(
                                    "Training Phase", color=ft.Colors.ON_SURFACE_VARIANT
                                ),
                                ft.Text(
                                    str(
                                        profile.get(
                                            "training_phase", TRAINING_PHASES[0]
                                        )
                                    ),
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
                    color=ft.Colors.PRIMARY,
                ),
                ft.Row(
                    [
                        ft.Column(
                            [
                                ft.Text(
                                    "Primary instructor",
                                    color=ft.Colors.ON_SURFACE_VARIANT,
                                ),
                                ft.Text(assigned_name(primary_value), size=16),
                            ],
                            width=280,
                        ),
                        ft.Column(
                            [
                                ft.Text(
                                    "Secondary instructor",
                                    color=ft.Colors.ON_SURFACE_VARIANT,
                                ),
                                ft.Text(assigned_name(secondary_value), size=16),
                            ],
                            width=280,
                        ),
                        ft.Column(
                            [
                                ft.Text(
                                    "Assigned manager",
                                    color=ft.Colors.ON_SURFACE_VARIANT,
                                ),
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
                    color=ft.Colors.PRIMARY,
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
            details.update()

        async def build_history_report(_: ft.ControlEvent) -> None:
            history_report_button.disabled = True
            progress_ui = FileProgressDialog(
                page,
                "Creating training history report",
                ["Collect training entries", "Write Excel workbook", "Open report"],
            )
            progress_ui.show()
            try:
                await progress_ui.set_step(0)
                await progress_ui.set_step(1)
                output_path = await asyncio.to_thread(
                    generate_history_report, member, profile, members, history_records
                )
                await progress_ui.set_step(1, complete=True)
                await progress_ui.set_step(2)
                open_report_file({"report_path": str(output_path)})
                await progress_ui.set_step(2, complete=True)
            except ModuleNotFoundError as error:
                if error.name != "openpyxl":
                    raise
                progress_ui.show_error(
                    "Excel support is not installed. Run: "
                    "python -m pip install -r requirements.txt"
                )
                return
            except (FileNotFoundError, OSError, ValueError) as error:
                progress_ui.show_error(error)
                return
            else:
                message.value = f"History report created and opened: {output_path}"
                message.color = ft.Colors.GREEN_700
            history_report_button.disabled = not trainee_directory_exists(member)
            details.update()
            progress_ui.close()

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

        information_menu = ft.ContextMenu(
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
                                bgcolor=ft.Colors.PRIMARY_CONTAINER,
                                color=ft.Colors.ON_PRIMARY_CONTAINER,
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
                                        color=ft.Colors.ON_SURFACE_VARIANT,
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
                ],
                spacing=18,
            ),
            secondary_items=[
                ft.PopupMenuItem(
                    content="Edit training information",
                    icon=ft.Icons.EDIT,
                    on_click=begin_edit,
                )
            ],
        )

        details.controls = [
            ft.Container(
                content=ft.Column(
                    [
                        information_menu,
                        ft.Row(
                            [
                                create_directory_button,
                                open_guide_button,
                                daily_report_button,
                                history_report_button,
                                upload_files_button,
                                view_uploads_button,
                                message,
                            ],
                            wrap=True,
                        ),
                        ft.Divider(height=28),
                        ft.Text(
                            "Training History",
                            size=20,
                            weight=ft.FontWeight.BOLD,
                            color=ft.Colors.PRIMARY,
                        ),
                        history_empty,
                        history_list,
                    ],
                    spacing=18,
                ),
                bgcolor=ft.Colors.SURFACE_CONTAINER_LOW,
                border=ft.Border.all(1, ft.Colors.OUTLINE_VARIANT),
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
            page.show_dialog(
                ft.SnackBar(
                    ft.Text("All team members are already assigned as trainees.")
                )
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

        async def add_trainee(_: ft.ControlEvent) -> None:
            member = next(
                (item for item in available if item.get("id") == selection.value), None
            )
            if member is None:
                error.visible = True
                dialog.update()
                return
            progress_ui = FileProgressDialog(
                page,
                "Assigning trainee",
                ["Create trainee profile", "Save trainee files"],
            )
            progress_ui.show(replace_current=True)
            await progress_ui.set_step(0)
            member["is_trainee"] = True
            ensure_profile(profiles, member["id"])
            await progress_ui.set_step(1)
            await asyncio.to_thread(save_all)
            await progress_ui.set_step(1, complete=True)
            refresh_selector(member["id"])
            progress_ui.close()
            page.update()

        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Add trainee"),
            content=ft.Column([selection, error], tight=True),
            actions=[
                ft.TextButton("Cancel", on_click=lambda _: page.pop_dialog()),
                ft.FilledButton("Add", icon=ft.Icons.PERSON_ADD, on_click=add_trainee),
            ],
        )
        page.show_dialog(dialog)

    trainee_selector.on_select = lambda _: (render_details(), page.update())
    refresh_selector()
    return ft.View(
        route="/trainees",
        bgcolor=ft.Colors.SURFACE,
        appbar=ft.AppBar(
            leading=ft.IconButton(
                icon=ft.Icons.ARROW_BACK,
                tooltip="Back to home",
                on_click=navigate_home,
            ),
            title=ft.Text("Trainees"),
            bgcolor=ft.Colors.SURFACE_CONTAINER_LOW,
        ),
        controls=[
            ft.Container(
                content=ft.Column(
                    [
                        ft.Row(
                            [
                                ft.Column(
                                    [
                                        ft.Text(
                                            "Trainees",
                                            size=30,
                                            weight=ft.FontWeight.BOLD,
                                        ),
                                        ft.Text(
                                            "Select a trainee to review or update their training.",
                                            color=ft.Colors.ON_SURFACE_VARIANT,
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
