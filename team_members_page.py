"""Team Members page."""

import flet as ft

from placeholder_page import build_placeholder_view


def build_team_members_view(page: ft.Page) -> ft.View:
    return build_placeholder_view(
        page, "/team-members", "Team Members", ft.Icons.GROUP
    )
