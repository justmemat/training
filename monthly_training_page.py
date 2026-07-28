"""Monthly training entry page."""

import flet as ft


def build_monthly_training_view(page: ft.Page) -> ft.View:
    """Build the placeholder monthly training submission screen."""

    async def navigate_home(_: ft.ControlEvent) -> None:
        await page.push_route("/")

    def show_success(_: ft.ControlEvent) -> None:
        success_dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Success"),
            content=ft.Text("The change was successful."),
            actions=[
                ft.FilledButton(
                    "OK",
                    on_click=lambda _: page.pop_dialog(),
                )
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        page.show_dialog(success_dialog)

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
            ft.FilledButton(
                "Submit Training Record",
                icon=ft.Icons.ADD,
                on_click=show_success,
            )
        ],
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        vertical_alignment=ft.MainAxisAlignment.CENTER,
    )
