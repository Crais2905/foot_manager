from PySide6.QtWidgets import QFrame, QGridLayout, QLabel, QVBoxLayout

from app.application.services import ChampionshipService, CoachService, PlayerService, TeamService
from app.presentation.widgets import DataTable, Page, TaskRunner, toolbar


class DashboardPage(Page):
    def __init__(
        self, runner: TaskRunner, teams: TeamService, players: PlayerService,
        coaches: CoachService, championships: ChampionshipService,
    ) -> None:
        super().__init__("Головна", runner, "Огляд клубів, складів і змагань")
        self.teams, self.players, self.coaches, self.championships = teams, players, coaches, championships
        self.content.addWidget(toolbar(self.button("Оновити", self.load)))
        cards = QGridLayout()
        cards.setSpacing(12)
        self.counts = []
        for index, title in enumerate(("Команди", "Гравці", "Тренери", "Чемпіонати")):
            card = QFrame()
            card.setObjectName("card")
            layout = QVBoxLayout(card)
            label = QLabel(title)
            label.setObjectName("muted")
            value = QLabel("—")
            value.setObjectName("metric")
            layout.addWidget(label)
            layout.addWidget(value)
            self.counts.append(value)
            cards.addWidget(card, 0, index)
            cards.setColumnStretch(index, 1)
        self.content.addLayout(cards)
        self.recent = DataTable(("Команда", "Місто", "Тренер"), "Команди ще не створено.")
        self.seasons = DataTable(("Чемпіонат", "Країна", "Сезон"), "Чемпіонати ще не створено.")
        self.content.addWidget(QLabel("Останні додані команди"))
        self.content.addWidget(self.recent, 1)
        self.content.addWidget(QLabel("Доступні чемпіонати"))
        self.content.addWidget(self.seasons, 1)

    async def load(self) -> None:
        teams = await self.teams.get_all_teams()
        players = await self.players.get_all_players()
        coaches = await self.coaches.get_all_coaches()
        championships = await self.championships.get_all_championships()
        for label, count in zip(
            self.counts, (len(teams), len(players), len(coaches), len(championships)), strict=True,
        ):
            label.setText(str(count))
        recent = sorted(teams, key=lambda team: team.id or 0, reverse=True)[:5]
        self.recent.set_rows([
            (t.id, (t.name, t.city, t.coach.full_name())) for t in recent if t.id is not None
        ])
        self.seasons.set_rows([
            (c.id, (c.name, c.country, c.season)) for c in championships if c.id is not None
        ])
