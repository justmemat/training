"""Entry point for the OSF Training application."""

import flet as ft

from data_store import initialize_data_files
from landing_page import build_landing_view
from monthly_training_page import build_monthly_training_view
from team_members_page import build_team_members_view
from trainees_page import build_trainees_view


async def main(page: ft.Page) -> None:
    """Configure the window and display the view for the current route."""
    page.title = "OSF Training"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.theme = ft.Theme(color_scheme_seed=ft.Colors.INDIGO)
    page.padding = 0
    page.window.min_width = 700
    page.window.min_height = 520

    initialize_data_files()

    routes = {
        "/": build_landing_view,
        "/team-members": build_team_members_view,
        "/trainees": build_trainees_view,
        "/monthly-training": build_monthly_training_view,
    }

    async def navigate_home(_: ft.ControlEvent) -> None:
        await page.push_route("/")

    def route_change(event: ft.RouteChangeEvent) -> None:
        view_builder = routes.get(event.route, build_landing_view)
        page.views.clear()
        try:
            page.views.append(view_builder(page))
        except Exception as error:
            # Keep navigation failures visible instead of leaving an empty grey page.
            page.views.append(
                ft.View(
                    route=event.route,
                    bgcolor=ft.Colors.INDIGO_50,
                    appbar=ft.AppBar(
                        leading=ft.IconButton(
                            icon=ft.Icons.ARROW_BACK,
                            on_click=navigate_home,
                        ),
                        title=ft.Text("Unable to open page"),
                    ),
                    controls=[
                        ft.Container(
                            content=ft.Column(
                                [
                                    ft.Icon(
                                        ft.Icons.ERROR_OUTLINE,
                                        size=54,
                                        color=ft.Colors.RED_600,
                                    ),
                                    ft.Text(
                                        "The page could not be loaded.",
                                        size=24,
                                        weight=ft.FontWeight.BOLD,
                                    ),
                                    ft.Text(str(error), selectable=True),
                                    ft.FilledButton(
                                        "Back to home",
                                        icon=ft.Icons.HOME,
                                        on_click=navigate_home,
                                    ),
                                ],
                                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                                spacing=16,
                            ),
                            alignment=ft.Alignment.CENTER,
                            padding=40,
                        )
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    vertical_alignment=ft.MainAxisAlignment.CENTER,
                )
            )
        page.update()

    async def view_pop(_: ft.ViewPopEvent) -> None:
        await page.push_route("/")

    page.on_route_change = route_change
    page.on_view_pop = view_pop
    await page.push_route(page.route or "/")


if __name__ == "__main__":
    ft.run(main)
