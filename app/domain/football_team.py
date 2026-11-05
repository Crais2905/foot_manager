from collections.abc import Iterator

from app.domain.coach import Coach
from app.domain.player import Player
from app.domain.team_squad import TeamSquad


class FootballTeam:
    _exclusive_club_membership = True

    def __init__(
        self,
        name: str,
        city: str,
        coach: Coach,
        id: int | None = None,
        squad: TeamSquad | None = None,
    ) -> None:
        if not isinstance(name, str) or not isinstance(city, str):
            raise TypeError("Team name and city must be strings.")
        name = name.strip()
        city = city.strip()
        if not name or not city:
            raise ValueError("Team name and city cannot be empty.")
        if not isinstance(coach, Coach):
            raise TypeError("Coach must be a Coach object.")
        if id is not None and (type(id) is not int or id < 1):
            raise ValueError("ID must be a positive integer or None.")
        if squad is not None and not isinstance(squad, TeamSquad):
            raise TypeError("Squad must be a TeamSquad object.")

        self.id = id
        self.name = name
        self.city = city
        self.coach = coach
        self.squad = squad if squad is not None else TeamSquad()
        self.squad._bind_team(
            self, exclusive_club_membership=self._exclusive_club_membership
        )

    def add_player(self, player: Player) -> None:
        self.squad.add_player(player)

    def remove_player(self, player: Player) -> None:
        self.squad.remove_player(player)

    def has_player(self, player: Player) -> bool:
        return self.squad.contains(player)

    def find_player(self, player_id: int) -> Player | None:
        return self.squad.find_player(player_id)

    def get_players(self) -> list[Player]:
        return self.squad.get_players()

    def players_count(self) -> int:
        return self.squad.players_count()

    def set_coach(self, coach: Coach) -> None:
        if not isinstance(coach, Coach):
            raise TypeError("Coach must be a Coach object.")
        self.coach = coach

    def get_coach(self) -> Coach:
        return self.coach

    def __iter__(self) -> Iterator[Player]:
        return iter(self.squad)

    def __len__(self) -> int:
        return len(self.squad)

    def __contains__(self, player: object) -> bool:
        return player in self.squad

    def __getitem__(self, index: int) -> Player:
        return self.squad[index]

    def __str__(self) -> str:
        return f"{self.name} ({self.city}), players: {len(self)}"

    def __repr__(self) -> str:
        return (
            f"FootballTeam(name={self.name!r}, city={self.city!r}, "
            f"coach={self.coach!r}, id={self.id!r})"
        )
