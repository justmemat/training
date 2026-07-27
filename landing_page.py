"""Landing page for the OSF Training application."""

import flet as ft


def _navigation_card(
    page: ft.Page, icon: str, title: str, description: str, route: str
) -> ft.Container:
    return ft.Container(
        content=ft.Column(
            controls=[
                ft.Icon(icon, size=46, color=ft.Colors.INDIGO_600),
                ft.Text(title, size=22, weight=ft.FontWeight.BOLD),
                ft.Text(
                    description,
                    size=14,
                    color=ft.Colors.GREY_700,
                    text_align=ft.TextAlign.CENTER,
                ),
                ft.FilledButton(
                    "Open",
                    icon=ft.Icons.ARROW_FORWARD,
                    on_click=lambda _, destination=route: page.push_route(destination),
                ),
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=16,
        ),
        bgcolor=ft.Colors.WHITE,
        border=ft.border.all(1, ft.Colors.INDIGO_100),
        border_radius=18,
        padding=28,
        width=270,
        shadow=ft.BoxShadow(
            blur_radius=18,
            color=ft.Colors.with_opacity(0.10, ft.Colors.BLACK),
            offset=ft.Offset(0, 6),
        ),
    )


def build_landing_view(page: ft.Page) -> ft.View:
    """Build the application's main navigation screen."""
    return ft.View(
        route="/",
        bgcolor=ft.Colors.INDIGO_50,
        padding=40,
        controls=[
            ft.Column(
                controls=[
                    ft.Text(
                        "OSF Training",
                        size=38,
                        weight=ft.FontWeight.BOLD,
                        color=ft.Colors.INDIGO_900,
                    ),
                    ft.Text(
                        "Choose an area to get started",
                        size=18,
                        color=ft.Colors.GREY_700,
                    ),
                    ft.Container(height=14),
                    ft.Row(
                        controls=[
                            _navigation_card(
                                page,
                                ft.Icons.GROUP,
                                "Team Members",
                                "Manage trainers and other team members.",
                                "/team-members",
                            ),
                            _navigation_card(
                                page,
                                ft.Icons.SCHOOL,
                                "Trainees",
                                "View and maintain trainee information.",
                                "/trainees",
                            ),
                            _navigation_card(
                                page,
                                ft.Icons.CALENDAR_MONTH,
                                "Monthly Training",
                                "Organize monthly training activities.",
                                "/monthly-training",
                            ),
                        ],
                        alignment=ft.MainAxisAlignment.CENTER,
                        spacing=24,
                        wrap=True,
                    ),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=8,
            )
        ],
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        vertical_alignment=ft.MainAxisAlignment.CENTER,
        scroll=ft.ScrollMode.AUTO,
    )
