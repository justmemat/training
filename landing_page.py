"""Landing page for the ATLAS application."""

import asyncio
import subprocess
from pathlib import Path

import flet as ft

APP_VERSION = "1.2.1"
VERSION_FILE = Path(r"T:\BAE\Training\App\Assets\verchek.txt")
INSTALLER_FILE = Path(r"T:\BAE\Training\App\install.bat")


def update_is_available(version_file: Path = VERSION_FILE) -> bool:
    """Return whether the published version differs from this application."""
    try:
        published_version = version_file.read_text(encoding="utf-8-sig").strip()
    except OSError:
        # An inaccessible network location must not make a possibly stale client
        # appear current.
        return True
    return published_version != APP_VERSION


def launch_installer(installer_file: Path = INSTALLER_FILE) -> None:
    """Start the Windows updater independently of the running application."""
    creation_flags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0) | getattr(
        subprocess, "DETACHED_PROCESS", 0
    )
    subprocess.Popen(  # noqa: S603 - the executable is a fixed, trusted network path
        ["cmd.exe", "/c", "start", "", str(installer_file)],
        creationflags=creation_flags,
    )


def _navigation_card(
    page: ft.Page, icon: str, title: str, description: str, route: str
) -> ft.Container:
    async def navigate(_: ft.ControlEvent) -> None:
        connecting = ft.AlertDialog(
            modal=True,
            content=ft.Row(
                controls=[
                    ft.ProgressRing(width=28, height=28),
                    ft.Text("Connecting to Network", size=16),
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                spacing=18,
            ),
        )
        page.show_dialog(connecting)
        page.update()
        # Give the desktop client an opportunity to paint the progress dialog
        # before the destination view performs its network-backed file reads.
        await asyncio.sleep(0.1)
        await page.push_route(route)
        page.pop_dialog()

    return ft.Container(
        content=ft.Column(
            controls=[
                ft.Icon(icon, size=46, color=ft.Colors.PRIMARY),
                ft.Text(title, size=22, weight=ft.FontWeight.BOLD),
                ft.Text(
                    description,
                    size=14,
                    color=ft.Colors.ON_SURFACE_VARIANT,
                    text_align=ft.TextAlign.CENTER,
                ),
                ft.FilledButton(
                    "Open",
                    icon=ft.Icons.ARROW_FORWARD,
                    on_click=navigate,
                ),
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=16,
        ),
        bgcolor=ft.Colors.SURFACE_CONTAINER_LOW,
        border=ft.Border.all(1, ft.Colors.OUTLINE_VARIANT),
        border_radius=18,
        padding=28,
        width=270,
        shadow=ft.BoxShadow(
            blur_radius=18,
            color=ft.Colors.with_opacity(0.18, ft.Colors.SHADOW),
            offset=ft.Offset(0, 6),
        ),
    )


def build_landing_view(page: ft.Page) -> ft.View:
    """Build the application's main navigation screen."""
    def install_update(_: ft.ControlEvent) -> None:
        launch_installer()

    update_controls: list[ft.Control] = []
    if update_is_available():
        update_controls.append(
            ft.FilledButton(
                "Update Available",
                icon=ft.Icons.SYSTEM_UPDATE_ALT,
                on_click=install_update,
            )
        )

    navigation = ft.Column(
        controls=[
            ft.Text(
                "ATLAS",
                size=38,
                weight=ft.FontWeight.BOLD,
                color=ft.Colors.PRIMARY,
            ),
            ft.Text(
                "Choose an area to get started",
                size=18,
                color=ft.Colors.ON_SURFACE_VARIANT,
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
            *update_controls,
        ],
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        spacing=8,
    )

    return ft.View(
        route="/",
        bgcolor=ft.Colors.SURFACE,
        padding=40,
        controls=[
            ft.Container(
                content=navigation,
                alignment=ft.Alignment.CENTER,
                expand=True,
            ),
        ],
        horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
        vertical_alignment=ft.MainAxisAlignment.START,
        scroll=ft.ScrollMode.AUTO,
    )
