from PySide6.QtWidgets import QGridLayout, QLabel, QLineEdit, QMessageBox, QPushButton, QWidget

from app.application.services import CoachService, NationalTeamService
from app.application.services.national_team_service import RosterCandidate
from app.domain.national_team import NationalTeam
from app.domain.player import Player
from app.presentation.dialogs import NationalTeamDialog, position_combo
from app.presentation.pages.management import roster_rows
from app.presentation.widgets import (
    ConfirmationDialog, DataTable, FormDialog, Page, SearchBar, TaskRunner, required, toolbar,
)


class NationalTeamBuilderDialog(FormDialog):
    def __init__(
        self, parent: QWidget, candidates: list[RosterCandidate], team: NationalTeam | None = None,
    ) -> None:
        super().__init__("Формування складу збірної", parent)
        self.resize(1040, 610)
        self.people: dict[int, Player] = {}
        self.clubs: dict[int, str] = {}
        for candidate in candidates:
            key = candidate.player.id
            if key is not None:
                self.people[key] = candidate.player
                self.clubs[key] = candidate.club_name
        self.numbers: dict[int, int] = {}
        if team is not None:
            for member in team.squad.memberships:
                key = member.player.id
                if key is not None:
                    self.people.setdefault(key, member.player)
                    self.numbers[key] = member.shirt_number
        self.search = SearchBar("Ім’я або прізвище")
        self.position = position_combo(all_positions=True)
        self.available = DataTable(("Гравець", "Клуб", "Позиція"), "Немає доступних кандидатів.")
        self.selected = DataTable(("Номер", "Гравець", "Клуб", "Позиція"), "Склад ще порожній.")
        self.number = QLineEdit("1")
        self.number.setPlaceholderText("1–99")
        self.number.setAccessibleName("Номер у збірній")
        self.count = QLabel()
        self.add_button = QPushButton("Додати")
        self.remove_button = QPushButton("Вилучити")
        self.change_button = QPushButton("Змінити номер")
        self.add_button.clicked.connect(self.add_player)
        self.remove_button.clicked.connect(self.remove_player)
        self.change_button.clicked.connect(self.change_number)
        self.available.selection_changed.connect(self.update_actions)
        self.selected.selection_changed.connect(self.update_actions)
        self.search.textChanged.connect(self.populate)
        self.position.currentIndexChanged.connect(self.populate)
        panel = QWidget()
        layout = QGridLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(QLabel("Доступні гравці"), 0, 0)
        layout.addWidget(self.count, 0, 1)
        layout.addWidget(toolbar(self.search, self.position), 1, 0)
        layout.addWidget(toolbar(QLabel("Номер у збірній"), self.number), 1, 1)
        layout.addWidget(self.available, 2, 0)
        layout.addWidget(self.selected, 2, 1)
        layout.addWidget(toolbar(self.add_button), 3, 0)
        layout.addWidget(toolbar(self.remove_button, self.change_button), 3, 1)
        layout.setColumnStretch(0, 1)
        layout.setColumnStretch(1, 1)
        layout.setRowStretch(2, 1)
        self.form.addRow(panel)
        self.populate()

    def update_actions(self) -> None:
        self.add_button.setEnabled(self.available.selected_id() is not None)
        selected = self.selected.selected_id() is not None
        self.remove_button.setEnabled(selected)
        self.change_button.setEnabled(selected)

    def populate(self, *_args: object) -> None:
        search = self.search.text().strip().casefold()
        position = self.position.currentData()
        self.available.set_rows([
            (key, (player.full_name(), self.clubs[key], player.position.display_name()))
            for key, player in self.people.items()
            if key in self.clubs and key not in self.numbers and search in player.full_name().casefold()
            and (position is None or position == player.position)
        ])
        self.selected.set_rows([
            (key, (number, self.people[key].full_name(), self.clubs.get(key, "Поза пулом"),
                   self.people[key].position.display_name()))
            for key, number in self.numbers.items()
        ])
        self.count.setText(f"Склад збірної · вибрано {len(self.numbers)}")

    def assign_number(self, player_id: int) -> None:
        text = self.number.text().strip()
        digits = text.lstrip("0")
        if not text.isascii() or not text.isdecimal() or not 1 <= len(digits) <= 2:
            self.notice.show_message("Введіть цілий номер від 1 до 99.", error=True)
            self.number.setFocus()
            return
        number = int(digits)
        if any(key != player_id and used == number for key, used in self.numbers.items()):
            self.notice.show_message(f"Номер {number} уже використовується у збірній.", error=True)
            self.number.setFocus()
            return
        self.numbers[player_id] = number
        self.notice.hide()
        self.populate()

    def add_player(self) -> None:
        key = self.available.selected_id()
        if key is not None:
            self.assign_number(key)

    def form_state(self) -> tuple[object, ...]:
        return tuple(sorted(self.numbers.items()))

    def remove_player(self) -> None:
        key = self.selected.selected_id()
        if key is None:
            return
        prompt = ConfirmationDialog(
            "Вилучити зі складу збірної", self, object_name=self.people[key].full_name(),
            confirm_text="Вилучити",
        )

        def finish(result: int) -> None:
            if result == QMessageBox.StandardButton.Yes:
                del self.numbers[key]
                self.notice.hide()
                self.populate()
            prompt.deleteLater()

        prompt.finished.connect(finish)
        prompt.open()

    def change_number(self) -> None:
        key = self.selected.selected_id()
        if key is not None:
            self.assign_number(key)


class NationalTeamPage(Page):
    def __init__(self, runner: TaskRunner, national: NationalTeamService, coaches: CoachService) -> None:
        super().__init__("Національні збірні", runner, "Клубні кандидати й номери у збірній")
        self.national, self.coaches = national, coaches
        self.items: dict[int, NationalTeam] = {}
        self.teams = DataTable(("Назва", "Країна", "Місто", "Тренер", "Гравців"))
        self.roster = DataTable(("Номер", "Гравець", "Позиція", "Дата народження"), "Виберіть збірну.")
        self.edit_button = self.button("Редагувати склад", self.edit_squad)
        self.delete_button = self.button("Видалити збірну", self.delete_record)
        self.content.addWidget(toolbar(
            self.button("Створити збірну", self.create_record), self.edit_button, self.delete_button,
            self.button("Оновити", self.load),
        ))
        self.content.addWidget(self.teams, 1)
        self.content.addWidget(QLabel("Склад вибраної збірної"))
        self.content.addWidget(self.roster, 2)
        self.teams.selection_changed.connect(self.show_roster)
        self.teams.activated.connect(lambda: self.perform(self.edit_squad))
        self.show_roster()

    async def load(self) -> None:
        teams = await self.national.get_all_national_teams()
        self.items = {team.id: team for team in teams if team.id is not None}
        self.teams.set_rows([
            (key, (team.name, team.country, team.city, team.coach.full_name(), len(team)))
            for key, team in self.items.items()
        ])
        if self.teams.selected_id() is None and self.items:
            self.teams.view.selectRow(0)

    def show_roster(self) -> None:
        key = self.teams.selected_id()
        team = self.items.get(key) if key is not None else None
        self.edit_button.setEnabled(team is not None)
        self.delete_button.setEnabled(team is not None)
        self.roster.set_rows(roster_rows(team) if team is not None else [])

    async def create_record(self) -> None:
        metadata = NationalTeamDialog(self.window(), await self.coaches.get_all_coaches())
        details: tuple[str, str, str, int] | None = None

        async def read_form() -> None:
            nonlocal details
            name, city, coach_id = metadata.values()
            details = required(metadata.country, "Країна"), name, city, coach_id

        if not await metadata.execute(read_form, allow_navigation=True) or details is None:
            return
        country, name, city, coach_id = details
        candidates = await self.national.get_roster_candidates(country)
        form = NationalTeamBuilderDialog(self.window(), candidates)

        async def save() -> None:
            await self.national.create_national_team(
                country, name, city, coach_id, list(form.numbers), form.numbers,
            )

        if await form.execute(save, allow_navigation=True):
            await self.load()
            self.notice.show_message("Збірну створено.")

    async def edit_squad(self) -> None:
        key = self.teams.selected_id()
        if key is None:
            return
        current = await self.national.get_national_team(key)
        if current is None:
            self.notice.show_message("Збірну не знайдено.", error=True)
            return
        form = NationalTeamBuilderDialog(
            self.window(), await self.national.get_roster_candidates(current.country), current,
        )

        async def save() -> None:
            await self.national.update_squad(key, list(form.numbers), form.numbers)

        if await form.execute(save, allow_navigation=True):
            await self.load()
            self.notice.show_message("Склад збірної збережено.")


    async def delete_record(self) -> None:
        key = self.teams.selected_id()
        if key is None:
            return
        if await ConfirmationDialog(
            "Видалити збірну та її склад", self.window(), object_name=self.items[key].name,
        ).confirmed():
            await self.national.delete_national_team(key)
            await self.load()
            self.notice.show_message("Збірну видалено.")
