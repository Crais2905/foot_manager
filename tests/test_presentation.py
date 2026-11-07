import asyncio

import pytest
from datetime import date
from unittest.mock import AsyncMock

from tests.gui_helpers import press, until

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QMessageBox
from qasync import QEventLoop

from app.application.exceptions import ApplicationValidationError
from app.domain.coach import Coach
from app.presentation.app import run_window
from app.presentation.dialogs import NationalTeamDialog
from app.presentation.error_handler import ErrorDialog
from app.presentation.main_window import ApplicationContainer, MainWindow
from app.presentation.widgets import ConfirmationDialog, DataTable, Page, TaskRunner

pytestmark = pytest.mark.filterwarnings('ignore:.*iscoroutinefunction.*:DeprecationWarning:qasync')


def run_qt(qapp, scenario):
    previous = qapp.quitOnLastWindowClosed()
    qapp.setQuitOnLastWindowClosed(False)
    loop = QEventLoop(qapp)
    asyncio.set_event_loop(loop)
    try:
        with loop:
            loop.run_until_complete(scenario())
    finally:
        asyncio.set_event_loop(None)
        qapp.setQuitOnLastWindowClosed(previous)


def test_table_model_shows_values_and_preserves_selection(qtbot):
    table = DataTable(("ID", "Назва"))
    qtbot.addWidget(table)
    table.set_rows([(7, (7, "Динамо")), (9, (9, "Шахтар"))])
    table.view.selectRow(1)
    table.set_rows([(9, (9, "Шахтар")), (7, (7, "Динамо"))])
    assert table.selected_id() == 9
    assert table.model.data(table.model.index(0, 1)) == "Шахтар"
    assert table.model.data(table.model.index(0, 0), Qt.ItemDataRole.UserRole) == 9
    table.set_rows([])
    assert table.selected_id() is None and not table.empty.isHidden()


def test_form_retains_fields_and_guards_duplicate_submit(qapp, qtbot):
    async def scenario():
        window = MainWindow(ApplicationContainer())
        qtbot.addWidget(window)
        window.show()
        coach = Coach("Олег", "Петров", date(1980, 1, 1), 2, id=1)
        form = NationalTeamDialog(window, [coach])
        attempts = 0

        async def save():
            nonlocal attempts
            attempts += 1
            form.values()
            await asyncio.sleep(0.03)
            if attempts == 2:
                raise ApplicationValidationError("Виправте введені дані.")

        task = asyncio.create_task(form.execute(save))
        await until(form.isVisible)
        form.save_button.click()
        await until(lambda: "Заповніть" in form.notice.text())
        form.name.setText("Україна")
        form.city.setText("Київ")
        form.coach.setCurrentIndex(1)
        form.save_button.click()
        form.save_button.click()
        await until(lambda: "Виправте" in form.notice.text())
        assert attempts == 2 and form.name.text() == "Україна" and form.isVisible()
        form.save_button.click()
        assert await task
        assert attempts == 3
        window.close()

    run_qt(qapp, scenario)


def test_qasync_navigation_dashboard_and_orderly_shutdown(qapp, monkeypatch):
    async def scenario():
        services = ApplicationContainer()
        release = asyncio.Event()
        entered = asyncio.Event()
        finished = asyncio.Event()
        original = MainWindow

        async def slow_load():
            entered.set()
            await release.wait()
            finished.set()
            return []

        services.teams.get_all_teams = AsyncMock(return_value=[])
        services.players.get_all_players = AsyncMock(return_value=[])
        services.coaches.get_all_coaches = AsyncMock(
            return_value=[Coach("Олег", "Петров", date(1980, 1, 1), 2, id=1)]
        )
        services.championships.get_all_championships = AsyncMock(return_value=[])
        services.national.get_all_national_teams = AsyncMock(return_value=[])
        windows = []

        def capture(container):
            window = original(container)
            windows.append(window)
            return window

        monkeypatch.setattr("app.presentation.app.MainWindow", capture)
        cleanup = AsyncMock()
        task = asyncio.create_task(run_window(services, cleanup))
        await until(lambda: bool(windows) and not windows[0].pages[0].busy)
        window = windows[0]
        assert window.stack.count() == 6
        assert [label.text() for label in window.pages[0].counts] == ["0", "0", "1", "0"]
        for index in (2, 3, 4, 5):
            window.navigation.items.setCurrentRow(index)
            assert window.stack.currentIndex() == index
            await until(lambda: not window.pages[index].busy)
        services.teams.get_all_teams = slow_load
        window.navigation.items.setCurrentRow(1)
        await entered.wait()
        assert window.pages[1].busy
        window.close()
        assert window.isVisible() and not cleanup.called
        release.set()
        async with asyncio.timeout(5):
            await task
        assert finished.is_set()
        cleanup.assert_awaited_once()

    run_qt(qapp, scenario)


@pytest.mark.parametrize("leave_by_navigation", [True, False])
def test_dirty_form_can_continue_or_discard(qapp, qtbot, leave_by_navigation):
    async def scenario():
        services = ApplicationContainer()
        services.coaches.get_all_coaches = AsyncMock(return_value=[])
        services.teams.get_all_teams = AsyncMock(return_value=[])
        window = MainWindow(services)
        qtbot.addWidget(window)
        window.show()
        coach = Coach("Олег", "Петров", date(1980, 1, 1), 2, id=1)
        form = NationalTeamDialog(window, [coach])
        form.name.setText("Початкова назва")
        save = AsyncMock()
        task = asyncio.create_task(form.execute(save, allow_navigation=leave_by_navigation))
        await until(form.isVisible)
        form.name.setText("Нова назва")

        def attempt_leave():
            if leave_by_navigation:
                nav = window.navigation.items
                rect = nav.visualItemRect(nav.item(3))
                qtbot.mouseClick(nav.viewport(), Qt.MouseButton.LeftButton, pos=rect.center())
            else:
                form.close()

        attempt_leave()
        await until(lambda: isinstance(qapp.activeModalWidget(), QMessageBox))
        prompt = qapp.activeModalWidget()
        assert prompt.standardButtons() == (
            QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel
        )
        prompt.close()
        assert form.isVisible() and form.name.text() == "Нова назва" and not save.called
        assert window.stack.currentIndex() == window.navigation.items.currentRow() == 0
        attempt_leave()
        await until(lambda: isinstance(qapp.activeModalWidget(), QMessageBox))
        press(qapp.activeModalWidget(), "Вийти без збереження")
        assert not await task
        assert not save.called
        if leave_by_navigation:
            await until(lambda: window.stack.currentIndex() == 3 and not window.pages[3].busy)
            assert window.navigation.items.currentRow() == 3
        window.close()

    run_qt(qapp, scenario)


@pytest.mark.parametrize("action, expected", [("confirm", True), ("cancel", False), ("close", False)])
def test_delete_confirmation_requires_explicit_yes(qapp, qtbot, action, expected):
    async def scenario():
        window = MainWindow(ApplicationContainer())
        qtbot.addWidget(window)
        window.show()
        prompt = ConfirmationDialog("Видалити", window, object_name="Динамо")
        task = asyncio.create_task(prompt.confirmed())
        await until(prompt.isVisible)
        assert "Динамо" in prompt.text()
        if action == "close":
            prompt.close()
        else:
            press(prompt, "Видалити" if action == "confirm" else "Скасувати")
        assert await task is expected
        window.close()

    run_qt(qapp, scenario)


def test_unexpected_error_opens_safe_dialog_and_page_remains_usable(qapp, qtbot, caplog):
    async def scenario():
        page = Page("Перевірка", TaskRunner())
        qtbot.addWidget(page)
        page.show()

        async def fail():
            raise RuntimeError("secret driver payload")

        page.perform(fail)
        await until(lambda: isinstance(qapp.activeModalWidget(), ErrorDialog))
        prompt = qapp.activeModalWidget()
        assert "неочікувана" in prompt.text()
        assert "secret" not in prompt.text()
        assert not page.busy and page.body.isEnabled()
        assert any(record.exc_info for record in caplog.records)
        press(prompt, "Закрити")
        operation = AsyncMock()
        page.perform(operation)
        await page.runner.drain()
        operation.assert_awaited_once()
        page.close()

    run_qt(qapp, scenario)
