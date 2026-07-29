"""Reusable modal progress display for operations that write shared files."""

import asyncio

import flet as ft


class FileProgressDialog:
    """Show a prominent progress bar and live checklist for a file operation."""

    def __init__(self, page: ft.Page, title: str, steps: list[str]) -> None:
        self.page = page
        self.steps = steps
        self.step_texts = [
            ft.Text(f"○ {label}", color=ft.Colors.ON_SURFACE_VARIANT) for label in steps
        ]
        self.progress = ft.ProgressBar(
            value=0,
            height=12,
            color=ft.Colors.PRIMARY,
            bgcolor=ft.Colors.PRIMARY_CONTAINER,
            border_radius=6,
        )
        self.message = ft.Text(
            "Preparing...",
            weight=ft.FontWeight.BOLD,
            color=ft.Colors.PRIMARY,
        )
        self.dialog = ft.AlertDialog(
            modal=True,
            title=ft.Row(
                [
                    ft.ProgressRing(width=28, height=28, stroke_width=4),
                    ft.Text(title),
                ],
                spacing=14,
            ),
            content=ft.Container(
                content=ft.Column(
                    [self.message, self.progress, *self.step_texts],
                    tight=True,
                    spacing=12,
                ),
                width=500,
                padding=8,
            ),
        )

    def show(self, *, replace_current: bool = False) -> None:
        if replace_current:
            self.page.pop_dialog()
        self.page.show_dialog(self.dialog)

    async def set_step(self, index: int, *, complete: bool = False) -> None:
        for step_index, (control, label) in enumerate(zip(self.step_texts, self.steps)):
            if step_index < index or (complete and step_index == index):
                control.value = f"✓ {label}"
                control.color = ft.Colors.GREEN_700
                control.weight = ft.FontWeight.W_600
            elif step_index == index:
                control.value = f"● {label}"
                control.color = ft.Colors.PRIMARY
                control.weight = ft.FontWeight.W_600
        self.progress.value = (index + (1 if complete else 0)) / len(self.steps)
        self.message.value = (
            "Complete."
            if complete and index == len(self.steps) - 1
            else self.steps[index] + "..."
        )
        self.dialog.update()
        await asyncio.sleep(0)

    def close(self) -> None:
        self.page.pop_dialog()

    def show_error(self, error: Exception | str) -> None:
        self.message.value = str(error)
        self.message.color = ft.Colors.RED_700
        self.progress.value = None
        self.dialog.actions = [
            ft.TextButton("Close", on_click=lambda _: self.page.pop_dialog())
        ]
        self.dialog.update()
