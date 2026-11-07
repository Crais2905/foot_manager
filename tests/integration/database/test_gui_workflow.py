from datetime import date

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker
from PySide6.QtWidgets import QPushButton, QSpinBox

from tests.gui_helpers import dialog_of, press, until

from app.application.services import (
    ChampionshipService, CoachService, NationalTeamService, PlayerService, TeamService,
)
from app.domain.enums import PlayerPosition
from app.infrastructure.unit_of_work import UnitOfWork
from app.presentation.dialogs import DetailsDialog, NationalTeamDialog
from app.presentation.main_window import ApplicationContainer, MainWindow
from app.presentation.pages.championships import AddTeamToChampionshipDialog
from app.presentation.pages.management import AddPlayerToTeamDialog
from app.presentation.pages.national import NationalTeamBuilderDialog
from app.presentation.widgets import ConfirmationDialog, FormDialog

pytestmark = pytest.mark.integration
DOB = date(2000, 1, 1)


async def test_desktop_workflows_persist_across_sessions(db_connection, qapp, qtbot):
    sessions = async_sessionmaker(bind=db_connection, expire_on_commit=False)

    def factory():
        return UnitOfWork(sessions)

    services = ApplicationContainer(
        TeamService(factory), PlayerService(factory), CoachService(factory),
        ChampionshipService(factory), NationalTeamService(factory),
    )
    window = MainWindow(services)
    qtbot.addWidget(window)
    window.show()

    async def page(index):
        window.navigation.items.setCurrentRow(index)
        view = window.pages[index]
        await until(lambda: not view.busy, qapp)
        return view

    async def saved(view, dialog):
        dialog.save_button.click()
        await until(lambda: not view.busy, qapp)
        assert view.notice.objectName() != "error", view.notice.text()

    first_coach = (await services.coaches.create_coach("Олег", "Тренер", DOB, 5)).id
    second_coach = await services.coaches.create_coach("Анна", "Абетка", DOB, 3)
    await services.teams.create_team("Альфа", "Київ", first_coach)
    await services.teams.create_team("Бета", "Львів", second_coach.id)
    goalkeeper = (await services.players.create_player(
        "Іван", "Воротар", DOB, PlayerPosition.GOALKEEPER, 1,
    )).id
    cup_id = (await services.championships.create_championship("Кубок", "Україна", "2026/2027")).id
    for index in (1, 2, 3, 4):
        records = await page(index)
        buttons = {button.text() for button in records.findChildren(QPushButton)}
        assert not buttons.intersection({"Створити", "Редагувати", "Видалити", "Переглянути"})

    teams = await page(1)
    a, b = teams.items
    teams.name.setText("АЛЬ")
    teams.city.setText("КИЇВ")
    press(teams, "Застосувати")
    await until(lambda: not teams.busy, qapp)
    assert list(teams.items) == [a]
    teams.name.clear()
    await until(lambda: not teams.busy, qapp)
    teams.city.clear()
    await until(lambda: not teams.busy, qapp)
    assert list(teams.items) == [a, b]

    players = await page(2)
    players.position.setCurrentIndex(players.position.findData(PlayerPosition.FORWARD))
    await until(lambda: not players.busy, qapp)
    assert players.table.model.rowCount() == 0
    players.position.setCurrentIndex(0)
    await until(lambda: not players.busy, qapp)
    assert [key for key, _ in players.table.model.rows] == [goalkeeper]

    teams = await page(1)
    teams.table.view.selectRow(0)
    press(teams, "Склад команди")
    details = await dialog_of(DetailsDialog, qapp)
    roster = details.page
    await until(lambda: not roster.busy, qapp)
    press(roster, "Додати гравця")
    form = await dialog_of(AddPlayerToTeamDialog, qapp)
    form.search.setText("Іван")
    form.number.setValue(37)
    await saved(roster, form)
    assert roster.table.model.rows[0][1][0] == 37
    roster.table.view.selectRow(0)
    press(roster, "Вилучити зі складу")
    confirmation = await dialog_of(ConfirmationDialog, qapp)
    press(confirmation, "Видалити")
    await until(lambda: not roster.busy, qapp)
    assert roster.table.model.rowCount() == 0
    assert await services.players.get_player(goalkeeper) is not None
    press(details, "Команди")
    await until(lambda: not teams.busy, qapp)
    assert window.navigation.items.currentRow() == 1
    await services.teams.add_player(a, goalkeeper, 37)

    cups = await page(4)
    cups.table.view.selectRow(0)
    press(cups, "Турнірна таблиця")
    details = await dialog_of(DetailsDialog, qapp)
    standings = details.page
    await until(lambda: not standings.busy, qapp)

    assert not standings.start.isEnabled() and not standings.range_button.isEnabled()
    for count, (team_id, position) in enumerate(((a, 1), (b, 3)), start=1):
        press(standings, "Додати команду")
        form = await dialog_of(AddTeamToChampionshipDialog, qapp)
        form.team.setCurrentIndex(form.team.findData(team_id))
        form.position.setValue(position)
        await saved(standings, form)
        assert standings.start.maximum() == standings.end.maximum() == count

    assert [row[0] for row in standings.table.model.rows] == [a, b]
    press(standings, "Сортувати за тренером")
    await until(lambda: not standings.busy, qapp)
    assert [row[0] for row in standings.table.model.rows] == [b, a]
    standings.table.view.selectRow(0)
    press(standings, "Змінити місце")
    form = await dialog_of(FormDialog, qapp)
    position = form.findChild(QSpinBox)
    position.setValue(1)
    form.save_button.click()
    await until(lambda: form.notice.objectName() == "error", qapp)
    assert form.isVisible() and position.value() == 1
    position.setValue(2)
    await saved(standings, form)
    standings.start.setValue(2)
    assert standings.end.value() == 2
    standings.end.setValue(1)
    assert standings.start.value() == 1
    standings.start.setValue(2)
    assert standings.start.minimum() == standings.end.minimum() == 1
    press(standings, "Застосувати діапазон")
    await until(lambda: not standings.busy, qapp)
    assert [row[0] for row in standings.table.model.rows] == [b]
    standings.table.view.selectRow(0)
    press(standings, "Вилучити команду")
    confirmation = await dialog_of(ConfirmationDialog, qapp)
    press(confirmation, "Видалити")
    await until(lambda: not standings.busy, qapp)
    assert standings.start.maximum() == standings.end.maximum() == 1
    assert standings.start.value() == standings.end.value() == 1
    press(details, "Головна")
    await until(lambda: not cups.busy and not window.pages[0].busy, qapp)
    assert window.navigation.items.currentRow() == 0 and window.stack.currentIndex() == 0
    assert [entry.position for entry in await services.championships.get_standings(cup_id)] == [1]

    for number in range(2, 12):
        player = await services.players.create_player(
            "Гравець", str(number), DOB, PlayerPosition.DEFENDER, 1,
        )
        await services.teams.add_player(a if number < 8 else b, player.id, number)

    national = await page(5)
    press(national, "Створити збірну")
    form = await dialog_of(NationalTeamDialog, qapp)
    form.name.setText("Збірна")
    form.country.setText("Україна")
    form.city.setText("Київ")
    form.coach.setCurrentIndex(form.coach.findData(first_coach))
    form.save_button.click()
    builder = await dialog_of(NationalTeamBuilderDialog, qapp)
    builder.save_button.click()
    await until(lambda: builder.notice.objectName() == "error", qapp)
    assert "11" in builder.notice.text() and "воротар" in builder.notice.text()
    builder.available.view.selectRow(0)
    for invalid in ("0", "100", "-5", "1.5", "abc", ""):
        builder.number.setText(invalid)
        builder.add_button.click()
        assert not builder.numbers and "від 1 до 99" in builder.notice.text()
    for number in range(1, 12):
        builder.available.view.selectRow(0)
        builder.number.setText(str(number))
        builder.add_button.click()
        if number == 1:
            builder.available.view.selectRow(0)
            builder.add_button.click()
            assert len(builder.numbers) == 1 and "уже використовується" in builder.notice.text()
    await saved(national, builder)
    team_id = next(iter(national.items))
    assert national.roster.model.rowCount() == 11
    press(national, "Редагувати склад")
    builder = await dialog_of(NationalTeamBuilderDialog, qapp)
    index = next(i for i, row in enumerate(builder.selected.model.rows) if row[0] == goalkeeper)
    builder.selected.view.selectRow(index)
    press(builder, "Вилучити")
    confirmation = await dialog_of(ConfirmationDialog, qapp)
    press(confirmation, "Скасувати")
    assert goalkeeper in builder.numbers
    old_number = builder.numbers[goalkeeper]
    taken = next(number for key, number in builder.numbers.items() if key != goalkeeper)
    builder.number.setText(str(taken))
    builder.change_button.click()
    assert builder.numbers[goalkeeper] == old_number and "уже використовується" in builder.notice.text()
    builder.number.setText("89")
    builder.change_button.click()
    await saved(national, builder)

    persisted = await services.national.get_national_team(team_id)
    assert next(member for member in persisted.squad.memberships
                if member.player.id == goalkeeper).shirt_number == 89
    club = await services.teams.get_team(a)
    assert next(member for member in club.squad.memberships
                if member.player.id == goalkeeper).shirt_number == 37
    press(national, "Видалити збірну")
    confirmation = await dialog_of(ConfirmationDialog, qapp)
    press(confirmation, "Скасувати")
    await until(lambda: not national.busy, qapp)
    assert team_id in national.items
    press(national, "Видалити збірну")
    confirmation = await dialog_of(ConfirmationDialog, qapp)
    press(confirmation, "Видалити")
    await until(lambda: not national.busy, qapp)
    assert await services.national.get_national_team(team_id) is None
    assert await services.players.get_player(goalkeeper) is not None
    window.close()
