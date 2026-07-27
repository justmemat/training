"""Trainees page."""

import flet as ft

from placeholder_page import build_placeholder_view


def build_trainees_view(page: ft.Page) -> ft.View:
    return build_placeholder_view(page, "/trainees", "Trainees", ft.Icons.SCHOOL)
