from collections.abc import Awaitable, Callable
from typing import TypeVar

from PySide6.QtWidgets import QComboBox, QLabel, QWidget

from app.application.services import CoachService, PlayerService, TeamService
from app.domain.football_team import FootballTeam
from app.domain.national_team import NationalTeam
from app.domain.player import Player
from app.presentation.dialogs import (
    DetailsDialog, number_field, position_combo, selected_id,
)
from app.presentation.widgets import (
    ConfirmationDialog, DataTable, FormDialog, Page, SearchBar, TaskRunner, toolbar,
)

T = TypeVar("T")


async def matching(
    first: list[T], second: Callable[[], Awaitable[list[T]]], key: Callable[[T], int | None],
) -> list[T]:
    ids = {key(item) for item in await second()}
    return [item for item in first if key(item) in ids]


class RecordsPage(Page):
    def setup_table(
        self, headers: tuple[str, ...], *filters: SearchBar | QComboBox,
        detail: tuple[str, Callable[[], Awaitable[None]]] | None = None,
    ) -> None:
        self.table = DataTable(headers, "Записів за поточними умовами немає.")
        actions: list[QWidget] = [*filters, self.button("Застосувати" if filters else "Оновити", self.load)]
        if detail is not None:
            title, show_details = detail
            button = self.button(title, show_details)
            button.setEnabled(False)
            self.table.selection_changed.connect(
                lambda: button.setEnabled(self.table.selected_id() is not None)
            )
            self.table.activated.connect(lambda: self.perform(show_details))
            actions.append(button)
        self.content.addWidget(toolbar(*actions))
        self.content.addWidget(self.table, 1)
        for field in filters:
            if isinstance(field, SearchBar):
                field.returnPressed.connect(self.refresh)
                field.textChanged.connect(lambda text: self.refresh() if not text else None)
            else:
                field.currentIndexChanged.connect(lambda _: self.refresh())


class TeamsPage(RecordsPage):
    def __init__(self, runner: TaskRunner, teams: TeamService, players: PlayerService) -> None:
        super().__init__("Команди", runner, "Клуби, тренери та заявки гравців")
        self.teams, self.players = teams, players
        self.items: dict[int, FootballTeam] = {}
        self.name = SearchBar("Назва команди")
        self.city = SearchBar("Місто")
        self.setup_table(
            ("ID", "Назва", "Місто", "Тренер", "Гравців"), self.name, self.city,
            detail=("Склад команди", self.details),
        )

    async def load(self) -> None:
        name, city = self.name.text().strip(), self.city.text().strip()
        if name:
            teams = await self.teams.search_by_name(name)
            if city:
                teams = await matching(teams, lambda: self.teams.search_by_city(city), lambda t: t.id)
        elif city:
            teams = await self.teams.search_by_city(city)
        else:
            teams = await self.teams.get_all_teams()
        self.items = {t.id: t for t in teams if t.id is not None and not isinstance(t, NationalTeam)}
        self.table.set_rows([
            (key, (key, team.name, team.city, team.coach.full_name(), len(team)))
            for key, team in self.items.items()
        ])

    async def details(self) -> None:
        key = self.table.selected_id()
        if key is not None:
            page = TeamDetailsPage(self.runner, self.teams, self.players, key)
            dialog = DetailsDialog(
                "Склад команди", page, self.window(), section="Команди", item_name=self.items[key].name,
            )
            if await dialog.show_page():
                self.home_requested.emit()
            else:
                await self.load()


def roster_rows(team: FootballTeam) -> list[tuple[int, tuple[object, ...]]]:
    return [
        (member.player.id, (member.shirt_number, member.player.full_name(),
                            member.player.position.display_name(), member.player.date_of_birth))
        for member in sorted(team.squad.memberships, key=lambda item: item.shirt_number)
        if member.player.id is not None
    ]


class TeamDetailsPage(Page):
    def __init__(self, runner: TaskRunner, teams: TeamService, players: PlayerService, key: int) -> None:
        super().__init__("Склад команди", runner)
        self.teams, self.players, self.key = teams, players, key
        self.summary = QLabel()
        self.summary.setWordWrap(True)
        self.content.addWidget(self.summary)
        self.table = DataTable(("Номер", "Гравець", "Позиція", "Дата народження"))
        self.remove_button = self.button("Вилучити зі складу", self.remove)
        self.remove_button.setEnabled(False)
        self.table.selection_changed.connect(
            lambda: self.remove_button.setEnabled(self.table.selected_id() is not None)
        )
        self.content.addWidget(toolbar(self.button("Додати гравця", self.add), self.remove_button))
        self.content.addWidget(self.table, 1)

    async def load(self) -> None:
        team = await self.teams.get_team(self.key)
        if team is None:
            self.summary.setText("Команду не знайдено.")
            self.table.set_rows([])
            return
        self.summary.setText(f"{team.name} · {team.city} · {team.coach.full_name()} · Гравців: {len(team)}")
        self.table.set_rows(roster_rows(team))

    async def add(self) -> None:
        existing = {key for key, _ in self.table.model.rows}
        form = AddPlayerToTeamDialog(self.window(), await self.players.get_unassigned_players(), existing)

        async def save() -> None:
            await self.teams.add_player(self.key, selected_id(form.player, "гравця"), form.number.value())

        if await form.execute(save):
            await self.load()
            self.notice.show_message("Гравця додано до складу.")

    async def remove(self) -> None:
        key = self.table.selected_id()
        if key is not None and await ConfirmationDialog(
            "Вилучити гравця зі складу команди?", self.window()
        ).confirmed():
            await self.teams.remove_player(self.key, key)
            await self.load()
            self.notice.show_message("Гравця вилучено зі складу.")


class AddPlayerToTeamDialog(FormDialog):
    def __init__(self, parent: QWidget, players: list[Player], existing: set[int]) -> None:
        super().__init__("Додати гравця до складу", parent, "Додати")
        self.search = SearchBar("Ім’я або прізвище")
        self.player = QComboBox()
        self.number = number_field()
        available = [p for p in players if p.id is not None and p.id not in existing]
        self.form.addRow("Пошук", self.search)
        self.form.addRow("Гравець", self.player)
        self.form.addRow("Номер у складі", self.number)

        def populate(query: str) -> None:
            self.player.clear()
            for player in available:
                if query.strip().casefold() in player.full_name().casefold():
                    self.player.addItem(player.full_name(), player.id)
            self.save_button.setEnabled(self.player.count() > 0)

        self.search.textChanged.connect(populate)
        populate("")
        if not available:
            self.notice.show_message("Немає гравців для додавання.")


class PlayersPage(RecordsPage):
    def __init__(self, runner: TaskRunner, players: PlayerService, teams: TeamService) -> None:
        super().__init__("Гравці", runner, "Профілі, позиції та клуби")
        self.players, self.teams = players, teams
        self.search = SearchBar("Ім’я або прізвище")
        self.position = position_combo(all_positions=True)
        self.setup_table(("ID", "Ім’я", "Прізвище", "Народження", "Позиція", "Клуби"),
                         self.search, self.position)

    async def load(self) -> None:
        query = self.search.text().strip()
        position = self.position.currentData()
        if query:
            players = await self.players.search_by_name(query)
            if position is not None:
                players = await matching(
                    players, lambda: self.players.get_by_position(position), lambda p: p.id,
                )
        elif position is not None:
            players = await self.players.get_by_position(position)
        else:
            players = await self.players.get_all_players()
        clubs: dict[int, list[str]] = {}
        for team in await self.teams.get_all_teams():
            if not isinstance(team, NationalTeam):
                for player in team:
                    if player.id is not None:
                        clubs.setdefault(player.id, []).append(team.name)
        self.table.set_rows([
            (p.id, (p.id, p.first_name, p.last_name, p.date_of_birth, p.position.display_name(),
                   ", ".join(clubs.get(p.id, [])) or "—"))
            for p in players if p.id is not None
        ])

class CoachesPage(RecordsPage):
    def __init__(self, runner: TaskRunner, coaches: CoachService, teams: TeamService) -> None:
        super().__init__("Тренери", runner, "Профілі та призначення")
        self.coaches, self.teams = coaches, teams
        self.search = SearchBar("Прізвище тренера")
        self.setup_table(("ID", "Ім’я", "Прізвище", "Народження", "Досвід, р.", "Команди"), self.search)

    async def load(self) -> None:
        query = self.search.text().strip()
        coaches = await self.coaches.search_by_last_name(query) if query else await self.coaches.get_all_coaches()
        assignments: dict[int, list[str]] = {}
        for team in await self.teams.get_all_teams():
            if team.coach.id is not None:
                assignments.setdefault(team.coach.id, []).append(team.name)
        self.table.set_rows([
            (c.id, (c.id, c.first_name, c.last_name, c.date_of_birth, c.experience_years,
                   ", ".join(assignments.get(c.id, [])) or "—"))
            for c in coaches if c.id is not None
        ])
