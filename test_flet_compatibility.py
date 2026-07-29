"""Compatibility checks for the Flet 0.86.3 user interface."""

import ast
import asyncio
import inspect
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

import flet as ft

import main as application
from landing_page import (
    APP_VERSION,
    build_landing_view,
    launch_installer,
    update_is_available,
)
from monthly_training_page import build_monthly_training_view
from team_members_page import build_team_members_view
from trainees_page import build_trainees_view

UI_FILES = (
    "main.py",
    "landing_page.py",
    "monthly_training_page.py",
    "team_members_page.py",
    "trainees_page.py",
)


class FletCompatibilityTests(unittest.TestCase):
    def test_installed_flet_version_and_async_routing_api(self) -> None:
        self.assertEqual(ft.__version__, "0.86.3")
        self.assertTrue(inspect.iscoroutinefunction(ft.Page.push_route))

    def test_every_push_route_call_is_awaited(self) -> None:
        for filename in UI_FILES:
            tree = ast.parse(Path(filename).read_text(encoding="utf-8"), filename)
            parents = {
                child: parent
                for parent in ast.walk(tree)
                for child in ast.iter_child_nodes(parent)
            }
            route_calls = [
                node
                for node in ast.walk(tree)
                if isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "push_route"
            ]
            self.assertTrue(route_calls, f"Expected a route call in {filename}")
            for call in route_calls:
                self.assertIsInstance(
                    parents[call], ast.Await, f"Unawaited push_route in {filename}"
                )

    def test_dialogs_use_supported_page_api(self) -> None:
        for filename in UI_FILES:
            tree = ast.parse(Path(filename).read_text(encoding="utf-8"), filename)
            unsupported_calls = [
                node.func.attr
                for node in ast.walk(tree)
                if isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and isinstance(node.func.value, ast.Name)
                and node.func.value.id == "page"
                and node.func.attr in {"open", "close"}
            ]
            self.assertEqual(
                unsupported_calls,
                [],
                f"Unsupported dialog API used in {filename}",
            )

    def test_all_views_build_with_flet_0863(self) -> None:
        page = Mock(spec=ft.Page)
        with (
            patch("team_members_page.load_records", return_value=[]),
            patch("trainees_page.load_records", return_value=[]),
            patch("monthly_training_page.load_records", return_value=[]),
        ):
            views = [
                build_landing_view(page),
                build_monthly_training_view(page),
                build_team_members_view(page),
                build_trainees_view(page),
            ]

        self.assertTrue(all(isinstance(view, ft.View) for view in views))

    def test_landing_brand_and_navigation_loading_dialog(self) -> None:
        page = Mock(spec=ft.Page)
        page.push_route = AsyncMock()
        with patch("landing_page.update_is_available", return_value=False):
            view = build_landing_view(page)

        navigation = view.controls[0].content

        self.assertIsNone(view.appbar)
        self.assertEqual(navigation.controls[0].value, "ATLAS")
        self.assertEqual(
            navigation.controls[1].value, "Choose an area to get started"
        )
        self.assertEqual(view.controls[1].controls[0].value, f"Version {APP_VERSION}")

        first_button = navigation.controls[3].controls[0].content.controls[3]
        with patch("landing_page.asyncio.sleep", new=AsyncMock()) as sleep:
            asyncio.run(first_button.on_click(Mock(spec=ft.ControlEvent)))

        page.show_dialog.assert_called_once()
        dialog = page.show_dialog.call_args.args[0]
        self.assertIsInstance(dialog.content.controls[0], ft.ProgressRing)
        self.assertEqual(dialog.content.controls[1].value, "Connecting to Network")
        sleep.assert_awaited_once_with(0.1)
        page.push_route.assert_awaited_once_with("/team-members")
        page.pop_dialog.assert_called_once_with()

    def test_landing_offers_update_when_published_version_differs(self) -> None:
        page = Mock(spec=ft.Page)
        with patch("landing_page.update_is_available", return_value=True):
            view = build_landing_view(page)

        update_button, version = view.controls[1].controls
        self.assertEqual(update_button.content, "Update Available")
        self.assertEqual(version.value, "Version 1.2.1")

        with patch("landing_page.launch_installer") as installer:
            update_button.on_click(Mock(spec=ft.ControlEvent))
        installer.assert_called_once_with()

    def test_version_check_handles_matching_different_and_missing_files(self) -> None:
        with self.subTest("matching"):
            version_file = Mock(spec=Path)
            version_file.read_text.return_value = "1.2.1\n"
            self.assertFalse(update_is_available(version_file))

        with self.subTest("different"):
            version_file.read_text.return_value = "1.2.2"
            self.assertTrue(update_is_available(version_file))

        with self.subTest("inaccessible"):
            version_file.read_text.side_effect = OSError
            self.assertTrue(update_is_available(version_file))

    @patch("landing_page.subprocess.Popen")
    def test_installer_is_launched_through_windows_command_shell(self, popen: Mock) -> None:
        installer = Path(r"T:\BAE\Training\App\install.bat")
        launch_installer(installer)
        command = popen.call_args.args[0]
        self.assertEqual(command, ["cmd.exe", "/c", "start", "", str(installer)])

    def test_monthly_training_button_opens_entry_dialog(self) -> None:
        page = Mock(spec=ft.Page)
        members = [
            {
                "id": "member-1",
                "first_name": "Jamie",
                "last_name": "Rivera",
                "operating_initials": "JR",
                "is_manager": True,
            }
        ]
        with patch("monthly_training_page.load_records", side_effect=[members, []]):
            view = build_monthly_training_view(page)

        self.assertEqual(len(view.controls), 1)
        action_buttons = view.controls[0].content.controls[0].controls[1]
        report_button, submit_button = action_buttons.controls
        self.assertIsInstance(report_button, ft.OutlinedButton)
        self.assertEqual(report_button.content, "Generate report")
        self.assertIsInstance(submit_button, ft.FilledButton)
        self.assertEqual(submit_button.content, "Track training")
        self.assertFalse(submit_button.disabled)

        report_path = Path("Monthly Training History.xlsx")
        with (
            patch(
                "monthly_training_page.generate_monthly_history_report",
                return_value=report_path,
            ) as generate_report,
            patch("monthly_training_page.open_monthly_history_report") as open_report,
            patch("monthly_training_page.FileProgressDialog") as progress_class,
        ):
            progress = progress_class.return_value
            progress.set_step = AsyncMock()
            asyncio.run(report_button.on_click(Mock(spec=ft.ControlEvent)))

        generate_report.assert_called_once_with([], members)
        open_report.assert_called_once_with(report_path)

        submit_button.on_click(Mock(spec=ft.ControlEvent))

        page.show_dialog.assert_called_once()
        dialog = page.show_dialog.call_args.args[0]
        self.assertIsInstance(dialog, ft.AlertDialog)
        self.assertEqual(dialog.title.value, "Track monthly training")
        labels = [
            control.value
            for control in dialog.content.content.controls
            if isinstance(control, ft.Text)
            and control.value.startswith(("1.", "2.", "3.", "4."))
        ]
        self.assertEqual(
            labels,
            ["1. Presented file", "2. Instructor", "3. Training date", "4. Attendance"],
        )
        self.assertEqual(dialog.actions[1].content, "Submit")
        instructor = dialog.content.content.controls[3]
        attendance = dialog.content.content.controls[7].content.controls
        attendance[0].update = Mock()
        instructor.value = "member-1"
        instructor.on_select(Mock(spec=ft.ControlEvent))
        self.assertTrue(attendance[0].value)

    def test_monthly_training_history_uses_openable_slideshow_and_initials(
        self,
    ) -> None:
        page = Mock(spec=ft.Page)
        members = [
            {
                "id": "member-1",
                "first_name": "Jamie",
                "last_name": "Rivera",
                "operating_initials": "JR",
            }
        ]
        sessions = [
            {
                "date": "2026-07-27",
                "file_name": "Lesson.pptx",
                "presentation_path": r"T:\BAE\Training\Monthly\2026\Lesson.pptx",
                "instructor_id": "member-1",
                "attendee_ids": ["member-1"],
            }
        ]
        with patch(
            "monthly_training_page.load_records", side_effect=[members, sessions]
        ):
            view = build_monthly_training_view(page)

        history = view.controls[0].content.controls[3]
        context_menu = history.controls[0]
        card_row = context_menu.content.content
        presentation_button = card_row.controls[0].content
        attendee_text = card_row.controls[1].controls[2]

        self.assertIsInstance(context_menu, ft.ContextMenu)
        self.assertEqual(
            [item.content for item in context_menu.secondary_items], ["Edit", "Delete"]
        )
        self.assertIsInstance(presentation_button, ft.IconButton)
        self.assertEqual(presentation_button.icon, ft.Icons.SLIDESHOW)
        self.assertTrue(callable(presentation_button.on_click))
        self.assertEqual(attendee_text.value, "Attendees: JR")

        page.reset_mock()
        context_menu.secondary_items[0].on_click(Mock(spec=ft.ControlEvent))
        edit_dialog = page.show_dialog.call_args.args[0]
        self.assertEqual(edit_dialog.title.value, "Edit monthly training")
        self.assertEqual(edit_dialog.actions[1].content, "Save")

        page.reset_mock()
        context_menu.secondary_items[1].on_click(Mock(spec=ft.ControlEvent))
        delete_dialog = page.show_dialog.call_args.args[0]
        self.assertEqual(delete_dialog.title.value, "Delete training entry?")

    def test_team_members_use_right_click_edit_and_delete_menu(self) -> None:
        page = Mock(spec=ft.Page)
        members = [
            {
                "id": "member-1",
                "first_name": "Jamie",
                "last_name": "Rivera",
                "operating_initials": "JR",
                "email": "jamie@example.com",
            }
        ]
        with patch("team_members_page.load_records", return_value=members):
            view = build_team_members_view(page)

        member_list = view.controls[0].content.controls[3]
        context_menu = member_list.controls[0]
        self.assertIsInstance(context_menu, ft.ContextMenu)
        self.assertEqual(
            [item.content for item in context_menu.secondary_items], ["Edit", "Delete"]
        )
        self.assertIsNone(context_menu.tooltip)
        self.assertEqual(len(context_menu.content.content.controls), 3)

        context_menu.secondary_items[0].on_click(Mock(spec=ft.ControlEvent))
        edit_dialog = page.show_dialog.call_args.args[0]
        self.assertEqual(edit_dialog.title.value, "Edit team member")

        page.reset_mock()
        context_menu.secondary_items[1].on_click(Mock(spec=ft.ControlEvent))
        delete_dialog = page.show_dialog.call_args.args[0]
        self.assertEqual(delete_dialog.title.value, "Remove team member?")

    def test_trainee_information_uses_edit_only_context_menu(self) -> None:
        page = Mock(spec=ft.Page)
        member = {
            "id": "trainee-1",
            "first_name": "Alex",
            "last_name": "Morgan",
            "operating_initials": "AM",
            "is_trainee": True,
        }
        with (
            patch("trainees_page.load_records", side_effect=[[member], [], []]),
            patch("trainees_page.trainee_directory_exists", return_value=False),
        ):
            view = build_trainees_view(page)

        selector = view.controls[0].content.controls[1]
        selector.value = "trainee-1"
        selector.on_select(Mock(spec=ft.ControlEvent))
        details = view.controls[0].content.controls[2]
        context_menu = details.controls[0]

        self.assertIsInstance(context_menu, ft.ContextMenu)
        self.assertEqual(
            [item.content for item in context_menu.secondary_items],
            ["Edit training information"],
        )
        self.assertIsNone(context_menu.tooltip)
        details.update = Mock()
        context_menu.secondary_items[0].on_click(Mock(spec=ft.ControlEvent))
        content_column = context_menu.content.content
        self.assertFalse(content_column.controls[2].visible)
        self.assertTrue(content_column.controls[3].visible)


class FletStartupTests(unittest.IsolatedAsyncioTestCase):
    async def test_startup_renders_initial_route_without_client_event(self) -> None:
        page = SimpleNamespace(
            route="/trainees",
            window=SimpleNamespace(
                min_width=None, min_height=None, icon=None, center=AsyncMock()
            ),
            views=[],
            update=Mock(),
        )

        with patch.object(application, "initialize_data_files"):
            await application.main(page)

        self.assertEqual(len(page.views), 1)
        self.assertEqual(page.views[0].route, "/")
        self.assertEqual(
            page.title, "Assessment, Training, Logging, and Analytics System"
        )
        page.window.center.assert_awaited_once_with()
        page.update.assert_called_once_with()
        self.assertTrue(callable(page.on_route_change))
        self.assertTrue(callable(page.on_view_pop))

    async def test_route_change_renders_requested_view(self) -> None:
        page = SimpleNamespace(
            route="/",
            window=SimpleNamespace(
                min_width=None, min_height=None, icon=None, center=AsyncMock()
            ),
            views=[],
            update=Mock(),
        )

        with (
            patch.object(application, "initialize_data_files"),
            patch.object(
                application,
                "build_team_members_view",
                return_value=ft.View(route="/team-members"),
            ),
        ):
            await application.main(page)
            page.on_route_change(SimpleNamespace(route="/team-members"))

        self.assertEqual(page.views[0].route, "/team-members")


if __name__ == "__main__":
    unittest.main()
