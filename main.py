"""Entry point for the OSF Training application."""

import flet as ft

from data_store import initialize_data_files
from landing_page import build_landing_view
from monthly_training_page import build_monthly_training_view
from team_members_page import build_team_members_view
from trainees_page import build_trainees_view


def main(page: ft.Page) -> None:
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

    def route_change(event: ft.RouteChangeEvent) -> None:
        view_builder = routes.get(event.route, build_landing_view)
        page.views.clear()
        page.views.append(view_builder(page))
        page.update()

    def view_pop(_: ft.ViewPopEvent) -> None:
        page.go("/")

    page.on_route_change = route_change
    page.on_view_pop = view_pop
    page.go(page.route or "/")


if __name__ == "__main__":
    ft.app(target=main)
