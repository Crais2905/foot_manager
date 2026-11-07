from typing import Literal

from PySide6.QtWidgets import QComboBox, QLabel, QWidget

from app.application.exceptions import ApplicationValidationError
from app.application.services import ChampionshipService, TeamService
from app.domain.championship import Championship
from app.domain.football_team import FootballTeam
from app.presentation.dialogs import DetailsDialog, number_field, selected_id
from app.presentation.pages.management import RecordsPage
from app.presentation.widgets import (
    ConfirmationDialog, DataTable, FormDialog, Page, TaskRunner, toolbar,
)


class ChampionshipsPage(RecordsPage):
    def __init__(self, runner: TaskRunner, championships: ChampionshipService, teams: TeamService) -> None:
        super().__init__("Чемпіонати", runner, "Сезони, учасники та турнірні таблиці")
        self.championships, self.teams = championships, teams
        self.items: dict[int, Championship] = {}
        self.setup_table(
            ("ID", "Назва", "Країна", "Сезон", "Команд"),
            detail=("Турнірна таблиця", self.details),
        )

    async def load(self) -> None:
        items = await self.championships.get_all_championships()
        self.items = {c.id: c for c in items if c.id is not None}
        self.table.set_rows([
            (key, (key, cup.name, cup.country, cup.season, len(cup)))
            for key, cup in self.items.items()
        ])

    async def details(self) -> None:
        key = self.table.selected_id()
        if key is not None:
            cup = self.items[key]
            page = ChampionshipTablePage(self.runner, self.championships, self.teams, key, cup.name)
            dialog = DetailsDialog(
                "Турнірна таблиця", page, self.window(), section="Чемпіонати", item_name=cup.name,
            )
            if await dialog.show_page():
                self.home_requested.emit()
            else:
                await self.load()


class AddTeamToChampionshipDialog(FormDialog):
    def __init__(self, parent: QWidget, teams: list[FootballTeam]) -> None:
        super().__init__("Додати команду до чемпіонату", parent, "Додати")
        self.team = QComboBox()
        self.team.addItem("Виберіть команду", None)
        for team in teams:
            self.team.addItem(f"{team.name} · {team.city}", team.id)
        self.position = number_field(maximum=2_147_483_647)
        self.form.addRow("Команда", self.team)
        self.form.addRow("Місце", self.position)
        if not teams:
            self.save_button.setEnabled(False)
            self.notice.show_message("Немає команд, які можна додати.")


class ChampionshipTablePage(Page):
    def __init__(
        self, runner: TaskRunner, championships: ChampionshipService, teams: TeamService,
        key: int, name: str,
    ) -> None:
        super().__init__("Турнірна таблиця", runner, name)
        self.championships, self.teams, self.key = championships, teams, key
        self.positions: dict[int, int] = {}
        self.order: Literal["position", "coach"] = "position"
        self.position_range: tuple[int, int] | None = None
        self.table = DataTable(("Місце", "Команда", "Місто", "Тренер"), "Немає команд у вибірці.")
        self.start = number_field(maximum=1)
        self.end = number_field(maximum=1)
        self._participant_count = 0
        self.range_button = self.button("Застосувати діапазон", self.filter_range)
        self.start.valueChanged.connect(lambda value: self.end.setValue(max(value, self.end.value())))
        self.end.valueChanged.connect(lambda value: self.start.setValue(min(value, self.start.value())))
        self.update_range_limits(0)
        self.content.addWidget(toolbar(
            self.button("Сортувати за місцем", self.by_position),
            self.button("Сортувати за тренером", self.by_coach),
        ))
        self.content.addWidget(toolbar(
            QLabel("Від"), self.start, QLabel("До"), self.end,
            self.range_button,
        ))
        self.edit_button = self.button("Змінити місце", self.edit_position)
        self.delete_button = self.button("Вилучити команду", self.remove)
        self.edit_button.setEnabled(False)
        self.delete_button.setEnabled(False)
        self.table.selection_changed.connect(self.update_actions)
        self.content.addWidget(toolbar(
            self.button("Додати команду", self.add), self.edit_button, self.delete_button,
        ))
        self.content.addWidget(self.table, 1)

    def update_actions(self) -> None:
        selected = self.table.selected_id() is not None
        self.edit_button.setEnabled(selected)
        self.delete_button.setEnabled(selected)

    def update_range_limits(self, count: int) -> None:
        previous_count = self._participant_count
        self._participant_count = count
        for field in (self.start, self.end):
            field.setMaximum(max(1, count))
            field.setEnabled(count > 0)
        if count and not previous_count:
            self.end.setValue(count)
        self.range_button.setEnabled(count > 0)
        if self.position_range is not None:
            start, end = self.position_range
            self.position_range = (min(start, count), min(end, count)) if count else None

    async def load(self) -> None:
        order = "position" if self.position_range is not None else self.order
        rows = await self.championships.get_standings(self.key, order=order)
        self.update_range_limits(len(rows))
        if self.position_range is not None:
            start, end = self.position_range
            rows = [row for row in rows if start <= row.position <= end]
        self.positions = {row.team.id: row.position for row in rows if row.team.id is not None}
        self.table.set_rows([
            (row.team.id, (row.position, row.team.name, row.team.city, row.team.coach.full_name()))
            for row in rows if row.team.id is not None
        ])

    async def by_position(self) -> None:
        self.order, self.position_range = "position", None
        await self.load()

    async def by_coach(self) -> None:
        self.order, self.position_range = "coach", None
        await self.load()

    async def filter_range(self) -> None:
        start, end = self.start.value(), self.end.value()
        if start > end:
            raise ApplicationValidationError("Початкове місце має бути не більшим за кінцеве.")
        self.position_range = start, end
        await self.load()

    async def add(self) -> None:
        current = {row.team.id for row in await self.championships.get_standings(self.key)}
        available = [t for t in await self.teams.get_all_teams() if t.id not in current]
        form = AddTeamToChampionshipDialog(self.window(), available)

        async def save() -> None:
            await self.championships.add_team(
                self.key, selected_id(form.team, "команду"), form.position.value(),
            )

        if await form.execute(save):
            await self.load()
            self.notice.show_message("Команду додано до чемпіонату.")

    async def edit_position(self) -> None:
        key = self.table.selected_id()
        if key is None:
            return
        form = FormDialog("Змінити місце", self.window())
        position = number_field(self.positions[key], maximum=2_147_483_647)
        form.form.addRow("Нове місце", position)

        async def save() -> None:
            await self.championships.update_team_position(self.key, key, position.value())

        if await form.execute(save):
            await self.load()
            self.notice.show_message("Місце команди збережено.")

    async def remove(self) -> None:
        key = self.table.selected_id()
        if key is not None and await ConfirmationDialog(
            "Вилучити команду з чемпіонату?", self.window(),
        ).confirmed():
            await self.championships.remove_team(self.key, key)
            await self.load()
            self.notice.show_message("Команду вилучено з чемпіонату.")
