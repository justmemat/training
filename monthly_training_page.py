"""Monthly training entry and history page."""

import asyncio
from datetime import date, datetime
import flet as ft

from data_store import load_records, save_records
from monthly_training_service import (
    create_session_record,
    generate_monthly_history_report,
    open_monthly_history_report,
    open_presentation_file,
    sorted_sessions,
)
from team_member_service import role_sort_key
from training_directory_service import full_name
from progress_dialog import FileProgressDialog


def build_monthly_training_view(page: ft.Page) -> ft.View:
    """Build the monthly-training history and submission interactions."""

    async def navigate_home(_: ft.ControlEvent) -> None:
        await page.push_route("/")

    members = load_records("team_members")
    sessions = load_records("monthly_training")
    ordered_members = sorted(members, key=role_sort_key)
    members_by_id = {str(member.get("id", "")): member for member in members}
    session_list = ft.Column(spacing=10)
    empty_message = ft.Text(
        "No monthly training has been tracked yet.",
        color=ft.Colors.GREY_600,
        italic=True,
        text_align=ft.TextAlign.CENTER,
    )

    def member_name(member: dict | None) -> str:
        if not member:
            return "Unknown team member"
        name = full_name(member)
        initials = str(member.get("operating_initials", "")).strip()
        return f"{name} ({initials})" if initials else name

    def session_card(record: dict) -> ft.Control:
        try:
            displayed_date = date.fromisoformat(str(record.get("date", ""))).strftime(
                "%d %b %Y"
            )
        except ValueError:
            displayed_date = "Unknown date"
        attendees = []
        for member_id in record.get("attendee_ids", []):
            member = members_by_id.get(str(member_id))
            initials = (
                str(member.get("operating_initials", "")).strip().upper()
                if member
                else ""
            )
            attendees.append(initials or "Unknown")

        def open_presentation(_: ft.ControlEvent) -> None:
            try:
                open_presentation_file(record)
            except (FileNotFoundError, OSError) as error:
                page.show_dialog(ft.SnackBar(ft.Text(str(error))))

        def confirm_delete(_: ft.ControlEvent) -> None:
            async def delete_record(_: ft.ControlEvent) -> None:
                progress_ui = FileProgressDialog(
                    page,
                    "Deleting monthly training entry",
                    ["Remove training entry", "Save monthly training history"],
                )
                progress_ui.show(replace_current=True)
                await progress_ui.set_step(0)
                sessions.remove(record)
                await progress_ui.set_step(1)
                await asyncio.to_thread(save_records, "monthly_training", sessions)
                await progress_ui.set_step(1, complete=True)
                render_sessions()
                page.update()
                progress_ui.close()

            page.show_dialog(
                ft.AlertDialog(
                    modal=True,
                    title=ft.Text("Delete training entry?"),
                    content=ft.Text(
                        f"Delete {record.get('file_name', 'this training entry')}?"
                    ),
                    actions=[
                        ft.TextButton("Cancel", on_click=lambda _: page.pop_dialog()),
                        ft.FilledButton(
                            "Delete",
                            icon=ft.Icons.DELETE,
                            style=ft.ButtonStyle(bgcolor=ft.Colors.RED_600),
                            on_click=delete_record,
                        ),
                    ],
                )
            )

        card = ft.Container(
            content=ft.Row(
                [
                    ft.Container(
                        content=ft.IconButton(
                            icon=ft.Icons.SLIDESHOW,
                            icon_color=ft.Colors.INDIGO_700,
                            tooltip=f"Open {record.get('file_name', 'training presentation')}",
                            on_click=open_presentation,
                        ),
                        bgcolor=ft.Colors.INDIGO_50,
                        border_radius=10,
                        padding=12,
                    ),
                    ft.Column(
                        [
                            ft.Text(
                                str(record.get("file_name", "Training file")),
                                size=18,
                                weight=ft.FontWeight.BOLD,
                            ),
                            ft.Text(
                                f"{displayed_date}  •  Instructor: "
                                f"{member_name(members_by_id.get(str(record.get('instructor_id', ''))))}",
                                color=ft.Colors.GREY_700,
                            ),
                            ft.Text(
                                "Attendees: "
                                + (", ".join(attendees) or "None recorded"),
                                color=ft.Colors.GREY_700,
                            ),
                        ],
                        spacing=4,
                        expand=True,
                    ),
                ]
            ),
            bgcolor=ft.Colors.WHITE,
            border=ft.Border.all(1, ft.Colors.INDIGO_100),
            border_radius=12,
            padding=16,
            tooltip=str(record.get("presentation_path", "")),
        )
        return ft.ContextMenu(
            content=card,
            secondary_items=[
                ft.PopupMenuItem(
                    content="Edit",
                    icon=ft.Icons.EDIT,
                    on_click=lambda _: open_training_dialog(record),
                ),
                ft.PopupMenuItem(
                    content="Delete",
                    icon=ft.Icons.DELETE_OUTLINE,
                    on_click=confirm_delete,
                ),
            ],
            tooltip="Right-click to edit or delete",
        )

    def render_sessions() -> None:
        session_list.controls = [
            session_card(record) for record in sorted_sessions(sessions)
        ]
        empty_message.visible = not sessions

    def open_training_dialog(record: dict | None = None) -> None:
        editing = record is not None
        selected_path = str(record.get("presentation_path", "")) if record else ""
        selected_date = (
            date.fromisoformat(str(record.get("date", ""))) if record else date.today()
        )
        file_field = ft.TextField(
            label="Training file",
            hint_text="Select the file that was presented",
            value=selected_path,
            read_only=True,
            expand=True,
        )
        instructor = ft.Dropdown(
            label="Instructor",
            hint_text="Select one instructor",
            options=[
                ft.dropdown.Option(
                    key=str(member.get("id", "")), text=member_name(member)
                )
                for member in ordered_members
            ],
            value=str(record.get("instructor_id", "")) if record else None,
            width=450,
        )
        date_field = ft.TextField(
            label="Training date",
            value=selected_date.strftime("%d %b %Y"),
            read_only=True,
            prefix_icon=ft.Icons.CALENDAR_MONTH,
            width=450,
        )
        attendance = [
            (
                str(member.get("id", "")),
                ft.Checkbox(
                    label=member_name(member),
                    value=bool(
                        record and member.get("id") in record.get("attendee_ids", [])
                    ),
                ),
            )
            for member in ordered_members
        ]
        error_text = ft.Text(color=ft.Colors.RED_700, visible=False)

        def instructor_selected(_: ft.ControlEvent) -> None:
            for member_id, checkbox in attendance:
                if member_id == instructor.value:
                    checkbox.value = True
                    checkbox.update()
                    break

        instructor.on_select = instructor_selected

        async def choose_file(_: ft.ControlEvent) -> None:
            nonlocal selected_path
            files = await ft.FilePicker().pick_files(
                dialog_title="Select monthly training file",
                initial_directory=rf"T:\BAE\Training\Monthly\{date.today().year}",
                allow_multiple=False,
            )
            if files:
                selected_path = files[0].path or ""
                file_field.value = selected_path
                file_field.update()

        def date_selected(_: ft.ControlEvent) -> None:
            nonlocal selected_date
            if date_picker.value is None:
                return
            selected_date = (
                date_picker.value.date()
                if isinstance(date_picker.value, datetime)
                else date_picker.value
            )
            date_field.value = selected_date.strftime("%d %b %Y")
            date_field.update()

        date_picker = ft.DatePicker(
            value=selected_date,
            first_date=date(2000, 1, 1),
            last_date=date(2100, 12, 31),
            help_text="Select training date",
            on_change=date_selected,
        )
        date_field.on_click = lambda _: page.show_dialog(date_picker)

        async def submit(_: ft.ControlEvent) -> None:
            try:
                created_record = create_session_record(
                    presentation_date=selected_date,
                    instructor_id=instructor.value or "",
                    attendee_ids=[
                        member_id for member_id, control in attendance if control.value
                    ],
                    presentation_path=selected_path,
                    team_members=members,
                )
            except ValueError as error:
                error_text.value = str(error)
                error_text.visible = True
                dialog.update()
                return
            if editing:
                created_record["id"] = record.get("id", created_record["id"])
                sessions[sessions.index(record)] = created_record
            else:
                sessions.append(created_record)
            progress_ui = FileProgressDialog(
                page,
                "Updating monthly training" if editing else "Saving monthly training",
                ["Validate training details", "Save monthly training history"],
            )
            progress_ui.show(replace_current=True)
            await progress_ui.set_step(0, complete=True)
            await progress_ui.set_step(1)
            await asyncio.to_thread(save_records, "monthly_training", sessions)
            await progress_ui.set_step(1, complete=True)
            render_sessions()
            page.update()
            progress_ui.close()

        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text(
                "Edit monthly training" if editing else "Track monthly training"
            ),
            content=ft.Container(
                content=ft.Column(
                    [
                        ft.Text("1. Presented file", weight=ft.FontWeight.BOLD),
                        ft.Row(
                            [
                                file_field,
                                ft.OutlinedButton(
                                    "Browse",
                                    icon=ft.Icons.FOLDER_OPEN,
                                    on_click=choose_file,
                                ),
                            ]
                        ),
                        ft.Text("2. Instructor", weight=ft.FontWeight.BOLD),
                        instructor,
                        ft.Text("3. Training date", weight=ft.FontWeight.BOLD),
                        date_field,
                        ft.Text("4. Attendance", weight=ft.FontWeight.BOLD),
                        ft.Container(
                            content=ft.Column(
                                [control for _, control in attendance],
                                spacing=2,
                                scroll=ft.ScrollMode.AUTO,
                            ),
                            border=ft.Border.all(1, ft.Colors.GREY_300),
                            border_radius=8,
                            padding=8,
                            height=180,
                        ),
                        error_text,
                    ],
                    tight=True,
                    spacing=10,
                    scroll=ft.ScrollMode.AUTO,
                ),
                width=520,
                height=620,
            ),
            actions=[
                ft.TextButton("Cancel", on_click=lambda _: page.pop_dialog()),
                ft.FilledButton(
                    "Save" if editing else "Submit", icon=ft.Icons.SAVE, on_click=submit
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        page.show_dialog(dialog)

    async def generate_report(_: ft.ControlEvent) -> None:
        progress_ui = FileProgressDialog(
            page,
            "Creating monthly training report",
            ["Collect monthly training", "Write Excel workbook", "Open report"],
        )
        progress_ui.show()
        try:
            await progress_ui.set_step(0)
            await progress_ui.set_step(1)
            report_path = await asyncio.to_thread(
                generate_monthly_history_report, sessions, members
            )
            await progress_ui.set_step(1, complete=True)
            await progress_ui.set_step(2)
            open_monthly_history_report(report_path)
            await progress_ui.set_step(2, complete=True)
        except (FileNotFoundError, OSError, PermissionError) as error:
            progress_ui.show_error(error)
            return
        progress_ui.close()

    render_sessions()
    return ft.View(
        route="/monthly-training",
        bgcolor=ft.Colors.INDIGO_50,
        appbar=ft.AppBar(
            leading=ft.IconButton(
                icon=ft.Icons.ARROW_BACK,
                tooltip="Back to home",
                on_click=navigate_home,
            ),
            title=ft.Text("Monthly Training"),
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
                                        ft.Text(
                                            "Monthly Training",
                                            size=30,
                                            weight=ft.FontWeight.BOLD,
                                            color=ft.Colors.INDIGO_900,
                                        ),
                                        ft.Text(
                                            "Track presentations and team attendance.",
                                            color=ft.Colors.GREY_700,
                                        ),
                                    ],
                                    spacing=2,
                                    expand=True,
                                ),
                                ft.Row(
                                    [
                                        ft.OutlinedButton(
                                            "Generate report",
                                            icon=ft.Icons.TABLE_VIEW,
                                            on_click=generate_report,
                                        ),
                                        ft.FilledButton(
                                            "Track training",
                                            icon=ft.Icons.ADD,
                                            on_click=lambda _: open_training_dialog(),
                                            disabled=not ordered_members,
                                            tooltip=(
                                                "Add a team member before tracking training"
                                                if not ordered_members
                                                else None
                                            ),
                                        ),
                                    ],
                                    spacing=10,
                                ),
                            ]
                        ),
                        ft.Divider(height=24, color=ft.Colors.INDIGO_100),
                        empty_message,
                        session_list,
                    ],
                    spacing=14,
                ),
                padding=32,
                width=1050,
            )
        ],
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        scroll=ft.ScrollMode.AUTO,
    )
