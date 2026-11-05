from app.domain.coach import Coach
from app.domain.football_team import FootballTeam
from app.domain.team_squad import TeamSquad


class NationalTeam(FootballTeam):
    MIN_SQUAD_SIZE = 11
    _exclusive_club_membership = False

    def __init__(
        self,
        name: str,
        city: str,
        coach: Coach,
        country: str,
        id: int | None = None,
        squad: TeamSquad | None = None,
    ) -> None:
        if not isinstance(country, str):
            raise TypeError("Country name must be a string.")
        country = country.strip()
        if not country:
            raise ValueError("Country name cannot be empty.")

        super().__init__(name, city, coach, id, squad)
        self.country = country

    def get_country(self) -> str:
        return self.country

    def validate_squad(self) -> bool:
        return self.players_count() >= self.MIN_SQUAD_SIZE

    def __str__(self) -> str:
        return f"National team {self.country}, players: {len(self)}"