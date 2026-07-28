"""Team Members management page."""

import asyncio

import flet as ft

from data_store import load_records, save_records
from progress_dialog import FileProgressDialog
from team_member_service import display_name, role_sort_key, upsert_member


def build_team_members_view(page: ft.Page) -> ft.View:
    """Build the team-member list and its add/edit/delete interactions."""

    async def navigate_home(_: ft.ControlEvent) -> None:
        await page.push_route("/")

    members = load_records("team_members")
    member_list = ft.Column(spacing=10)
    empty_message = ft.Text(
        "No team members yet. Select Add team member to create the first one.",
        color=ft.Colors.GREY_600,
        italic=True,
        text_align=ft.TextAlign.CENTER,
    )

    def open_member_dialog(member: dict | None = None) -> None:
        editing = member is not None
        first_name = ft.TextField(
            label="First name", value=member.get("first_name", "") if member else ""
        )
        last_name = ft.TextField(
            label="Last name", value=member.get("last_name", "") if member else ""
        )
        operating_initials = ft.TextField(
            label="Operating initials",
            value=member.get("operating_initials", "") if member else "",
            max_length=6,
            capitalization=ft.TextCapitalization.CHARACTERS,
        )
        email = ft.TextField(
            label="Email address (optional)",
            value=member.get("email", "") if member else "",
            keyboard_type=ft.KeyboardType.EMAIL,
            prefix_icon=ft.Icons.EMAIL_OUTLINED,
        )
        manager = ft.Checkbox(
            label="Manager", value=bool(member and member.get("is_manager"))
        )
        training_lead = ft.Checkbox(
            label="Training Lead",
            value=bool(member and member.get("is_training_lead")),
        )
        trainee = ft.Checkbox(
            label="Trainee", value=bool(member and member.get("is_trainee"))
        )
        error_text = ft.Text(color=ft.Colors.RED_700, visible=False)

        def close_dialog(_: ft.ControlEvent | None = None) -> None:
            page.pop_dialog()

        async def save_member(_: ft.ControlEvent) -> None:
            try:
                upsert_member(
                    members,
                    first_name=first_name.value or "",
                    last_name=last_name.value or "",
                    operating_initials=operating_initials.value or "",
                    email=email.value or "",
                    is_manager=bool(manager.value),
                    is_training_lead=bool(training_lead.value),
                    is_trainee=bool(trainee.value),
                    member_id=member.get("id") if member else None,
                )
            except ValueError as error:
                error_text.value = str(error)
                error_text.visible = True
                dialog.update()
                return
            progress_ui = FileProgressDialog(
                page,
                "Updating team member" if editing else "Adding team member",
                ["Validate team member", "Save team member file"],
            )
            progress_ui.show(replace_current=True)
            await progress_ui.set_step(0, complete=True)
            await progress_ui.set_step(1)
            await asyncio.to_thread(save_records, "team_members", members)
            await progress_ui.set_step(1, complete=True)
            render_members()
            page.update()
            progress_ui.close()

        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Edit team member" if editing else "Add team member"),
            content=ft.Container(
                content=ft.Column(
                    [
                        first_name,
                        last_name,
                        operating_initials,
                        email,
                        ft.Row([manager, training_lead, trainee], wrap=True),
                        error_text,
                    ],
                    tight=True,
                    spacing=12,
                ),
                width=430,
            ),
            actions=[
                ft.TextButton("Cancel", on_click=close_dialog),
                ft.FilledButton("Save", icon=ft.Icons.SAVE, on_click=save_member),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        page.show_dialog(dialog)

    def confirm_delete(member: dict) -> None:
        async def delete_member(_: ft.ControlEvent) -> None:
            progress_ui = FileProgressDialog(
                page,
                "Removing team member",
                ["Remove team member", "Save team member file"],
            )
            progress_ui.show(replace_current=True)
            await progress_ui.set_step(0)
            members.remove(member)
            await progress_ui.set_step(1)
            await asyncio.to_thread(save_records, "team_members", members)
            await progress_ui.set_step(1, complete=True)
            render_members()
            page.update()
            progress_ui.close()

        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Remove team member?"),
            content=ft.Text(
                f"Remove {member.get('first_name', '')} {member.get('last_name', '')} "
                "from the team?"
            ),
            actions=[
                ft.TextButton("Cancel", on_click=lambda _: page.pop_dialog()),
                ft.FilledButton(
                    "Remove",
                    icon=ft.Icons.DELETE,
                    style=ft.ButtonStyle(bgcolor=ft.Colors.RED_600),
                    on_click=delete_member,
                ),
            ],
        )
        page.show_dialog(dialog)

    def member_row(member: dict) -> ft.ContextMenu:
        roles: list[ft.Control] = []
        if member.get("is_manager"):
            roles.append(
                ft.Chip(label=ft.Text("Manager"), leading=ft.Icon(ft.Icons.BADGE))
            )
        if member.get("is_training_lead"):
            roles.append(
                ft.Chip(
                    label=ft.Text("Training Lead"),
                    leading=ft.Icon(ft.Icons.STAR, color=ft.Colors.AMBER_700),
                )
            )
        if member.get("is_trainee"):
            roles.append(
                ft.Chip(label=ft.Text("Trainee"), leading=ft.Icon(ft.Icons.SCHOOL))
            )
        if not roles:
            roles.append(ft.Text("Team member", color=ft.Colors.GREY_600))

        card = ft.Container(
            content=ft.Row(
                [
                    ft.CircleAvatar(
                        content=ft.Text(
                            str(member.get("operating_initials", "")).upper(),
                            weight=ft.FontWeight.BOLD,
                        ),
                        bgcolor=ft.Colors.INDIGO_100,
                        color=ft.Colors.INDIGO_900,
                    ),
                    ft.Column(
                        [
                            ft.Text(
                                f"{display_name(member)} "
                                f"({member.get('operating_initials', '')})",
                                size=18,
                                weight=ft.FontWeight.BOLD,
                            ),
                            ft.Text(
                                member.get("email") or "No email address provided",
                                color=ft.Colors.GREY_700,
                            ),
                        ],
                        spacing=2,
                        expand=True,
                    ),
                    ft.Row(roles, spacing=6, wrap=True),
                ]
            ),
            bgcolor=ft.Colors.WHITE,
            border=ft.Border.all(1, ft.Colors.INDIGO_100),
            border_radius=12,
            padding=16,
        )
        return ft.ContextMenu(
            content=card,
            secondary_items=[
                ft.PopupMenuItem(
                    content="Edit",
                    icon=ft.Icons.EDIT,
                    on_click=lambda _, selected=member: open_member_dialog(selected),
                ),
                ft.PopupMenuItem(
                    content="Delete",
                    icon=ft.Icons.DELETE_OUTLINE,
                    on_click=lambda _, selected=member: confirm_delete(selected),
                ),
            ],
            tooltip="Right-click to edit or delete",
        )

    def render_members() -> None:
        member_list.controls = [
            member_row(member) for member in sorted(members, key=role_sort_key)
        ]
        empty_message.visible = not members

    render_members()
    return ft.View(
        route="/team-members",
        bgcolor=ft.Colors.INDIGO_50,
        appbar=ft.AppBar(
            leading=ft.IconButton(
                icon=ft.Icons.ARROW_BACK,
                tooltip="Back to home",
                on_click=navigate_home,
            ),
            title=ft.Text("Team Members"),
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
                                            "Team Members",
                                            size=30,
                                            weight=ft.FontWeight.BOLD,
                                            color=ft.Colors.INDIGO_900,
                                        ),
                                        ft.Text(
                                            "Manage team members and role assignments.",
                                            color=ft.Colors.GREY_700,
                                        ),
                                    ],
                                    spacing=2,
                                    expand=True,
                                ),
                                ft.FilledButton(
                                    "Add team member",
                                    icon=ft.Icons.PERSON_ADD,
                                    on_click=lambda _: open_member_dialog(),
                                ),
                            ]
                        ),
                        ft.Divider(height=24, color=ft.Colors.INDIGO_100),
                        empty_message,
                        member_list,
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
