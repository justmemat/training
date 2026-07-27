"""Trainee assignment and training-information page."""

import flet as ft

from data_store import load_records, save_records
from team_member_service import display_name
from trainee_service import TRAINING_PHASES, ensure_profile, get_profile, update_profile


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
        start_date = ft.TextField(
            label="Start date",
            value=profile.get("start_date", ""),
            hint_text="YYYY-MM-DD",
            prefix_icon=ft.Icons.CALENDAR_MONTH,
            width=260,
        )
        phase = ft.Dropdown(
            label="Training Phase",
            value=profile.get("training_phase", TRAINING_PHASES[0]),
            options=[ft.dropdown.Option(value) for value in TRAINING_PHASES],
            width=260,
        )
        message = ft.Text(visible=False)

        def save_training(_: ft.ControlEvent) -> None:
            try:
                update_profile(
                    profile,
                    start_date=start_date.value or "",
                    training_phase=phase.value or "",
                )
            except ValueError as error:
                message.value = str(error)
                message.color = ft.Colors.RED_700
                message.visible = True
                details.update()
                return
            save_all()
            message.value = "Training information saved."
            message.color = ft.Colors.GREEN_700
            message.visible = True
            details.update()

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
                        ft.Row(
                            [
                                ft.FilledButton(
                                    "Save training information",
                                    icon=ft.Icons.SAVE,
                                    on_click=save_training,
                                ),
                                message,
                            ],
                            wrap=True,
                        ),
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
