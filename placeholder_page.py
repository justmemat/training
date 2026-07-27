"""Shared layout used by pages that will be implemented in a later phase."""

import flet as ft


def build_placeholder_view(
    page: ft.Page, route: str, title: str, icon: str
) -> ft.View:
    """Build a placeholder with a reliable route back to the landing page."""
    return ft.View(
        route=route,
        bgcolor=ft.Colors.INDIGO_50,
        appbar=ft.AppBar(
            leading=ft.IconButton(
                icon=ft.Icons.ARROW_BACK,
                tooltip="Back to home",
                on_click=lambda _: page.go("/"),
            ),
            title=ft.Text(title),
            bgcolor=ft.Colors.WHITE,
        ),
        controls=[
            ft.Container(
                content=ft.Column(
                    controls=[
                        ft.Icon(icon, size=72, color=ft.Colors.INDIGO_400),
                        ft.Text(title, size=32, weight=ft.FontWeight.BOLD),
                        ft.Text(
                            "This page is ready for the next phase of development.",
                            size=17,
                            color=ft.Colors.GREY_700,
                            text_align=ft.TextAlign.CENTER,
                        ),
                        ft.OutlinedButton(
                            "Back to home",
                            icon=ft.Icons.HOME,
                            on_click=lambda _: page.go("/"),
                        ),
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=20,
                ),
                padding=50,
            )
        ],
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        vertical_alignment=ft.MainAxisAlignment.CENTER,
    )
