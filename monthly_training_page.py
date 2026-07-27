"""Monthly Training page."""

import flet as ft

from placeholder_page import build_placeholder_view


def build_monthly_training_view(page: ft.Page) -> ft.View:
    return build_placeholder_view(
        page, "/monthly-training", "Monthly Training", ft.Icons.CALENDAR_MONTH
    )
