"""Compatibility checks for the Flet 0.86.3 user interface."""

import ast
import inspect
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import flet as ft

import main as application
from landing_page import build_landing_view
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

    def test_all_views_build_with_flet_0863(self) -> None:
        page = Mock(spec=ft.Page)
        with (
            patch("team_members_page.load_records", return_value=[]),
            patch("trainees_page.load_records", return_value=[]),
        ):
            views = [
                build_landing_view(page),
                build_monthly_training_view(page),
                build_team_members_view(page),
                build_trainees_view(page),
            ]

        self.assertTrue(all(isinstance(view, ft.View) for view in views))

    def test_monthly_training_button_opens_success_dialog(self) -> None:
        page = Mock()
        view = build_monthly_training_view(page)

        self.assertEqual(len(view.controls), 1)
        submit_button = view.controls[0]
        self.assertIsInstance(submit_button, ft.FilledButton)
        self.assertEqual(submit_button.content, "Submit Training Record")

        submit_button.on_click(Mock(spec=ft.ControlEvent))

        page.open.assert_called_once()
        dialog = page.open.call_args.args[0]
        self.assertIsInstance(dialog, ft.AlertDialog)
        self.assertEqual(dialog.title.value, "Success")
        self.assertEqual(dialog.content.value, "The change was successful.")


class FletStartupTests(unittest.IsolatedAsyncioTestCase):
    async def test_startup_renders_initial_route_without_client_event(self) -> None:
        page = SimpleNamespace(
            route="/",
            window=SimpleNamespace(min_width=None, min_height=None),
            views=[],
            update=Mock(),
        )

        with patch.object(application, "initialize_data_files"):
            await application.main(page)

        self.assertEqual(len(page.views), 1)
        self.assertEqual(page.views[0].route, "/")
        page.update.assert_called_once_with()
        self.assertTrue(callable(page.on_route_change))
        self.assertTrue(callable(page.on_view_pop))

    async def test_route_change_renders_requested_view(self) -> None:
        page = SimpleNamespace(
            route="/",
            window=SimpleNamespace(min_width=None, min_height=None),
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
