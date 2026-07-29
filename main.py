"""Entry point for the ATLAS application."""

import sys
from pathlib import Path

import flet as ft

from data_store import initialize_data_files
from landing_page import APP_VERSION, build_landing_view
from monthly_training_page import build_monthly_training_view
from team_members_page import build_team_members_view
from trainees_page import build_trainees_view

# PyInstaller extracts bundled data into ``_MEIPASS``. During development the
# assets directory sits beside this file, so the same reference works in both.
APP_DIR = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
ASSETS_DIR = APP_DIR / "assets"


async def main(page: ft.Page) -> None:
    """Configure the window and display the view for the current route."""
    # Display the expanded acronym in the native window title bar.
    page.title = (
        f"Assessment, Training, Logging, and Analytics System - v{APP_VERSION}"
    )
    # Follow the operating-system preference while keeping both variants in the
    # familiar Microsoft Teams purple palette.
    page.theme_mode = ft.ThemeMode.SYSTEM
    page.theme = ft.Theme(color_scheme_seed="#6264A7")
    page.dark_theme = ft.Theme(
        color_scheme_seed="#7F85F5",
        color_scheme=ft.ColorScheme(
            primary="#A6A7FF",
            secondary="#C4C2FF",
            surface="#1F1F1F",
            surface_container="#292929",
        ),
    )
    page.padding = 0
    page.window.min_width = 700
    page.window.min_height = 520
    icon_path = ASSETS_DIR / "icon.ico"
    if icon_path.is_file():
        page.window.icon = str(icon_path)
    await page.window.center()

    initialize_data_files()

    routes = {
        "/": build_landing_view,
        "/team-members": build_team_members_view,
        "/trainees": build_trainees_view,
        "/monthly-training": build_monthly_training_view,
    }

    async def navigate_home(_: ft.ControlEvent) -> None:
        await page.push_route("/")

    def route_change(event: ft.RouteChangeEvent | None = None) -> None:
        # Render once directly during startup.  ``push_route()`` only asks the
        # client to change its route; when the client is already at "/" it may
        # not send a route-change event back, which would leave ``page.views``
        # empty and display a blank window.
        route = event.route if event is not None else "/"
        view_builder = routes.get(route, build_landing_view)
        page.views.clear()
        try:
            page.views.append(view_builder(page))
        except Exception as error:
            # Keep navigation failures visible instead of leaving an empty grey page.
            page.views.append(
                ft.View(
                    route=route,
                    bgcolor=ft.Colors.SURFACE,
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
    route_change()


if __name__ == "__main__":
    ft.run(main, assets_dir=str(ASSETS_DIR))
