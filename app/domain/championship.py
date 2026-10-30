from collections.abc import Iterator

from app.domain.championship_participation import ChampionshipParticipation
from app.domain.football_team import FootballTeam


class Championship:
    def __init__(
        self,
        name: str,
        country: str,
        season: str,
        id: int | None = None,
    ) -> None:
        values = (name, country, season)
        if not all(isinstance(value, str) for value in values):
            raise TypeError("Name, country and season must be a string.")

        name, country, season = (value.strip() for value in values)

        if not name or not country or not season:
            raise ValueError("Name, country and season cant be empty.")
        if id is not None and (type(id) is not int or id < 1):
            raise ValueError("ID must be positive integer or None.")

        self.id = id
        self.name = name
        self.country = country
        self.season = season
        self._participations: list[ChampionshipParticipation] = []

    @property
    def participations(self) -> list[ChampionshipParticipation]:
        return self._participations.copy()

    def add_team(
        self,
        team: FootballTeam,
        position: int,
    ) -> ChampionshipParticipation:
        if not isinstance(team, FootballTeam):
            raise TypeError("Team must be a FootballTeam.")

        ChampionshipParticipation._validate_position(position)

        if any(item.team is team for item in self._participations):
            raise ValueError("Team has already exist.")
        if any(item.position == position for item in self._participations):
            raise ValueError("This position is already taken.")

        participation = ChampionshipParticipation(team, self, position)
        self._participations.append(participation)
        return participation

    def remove_team(self, team: FootballTeam) -> None:
        participation = next(
            (item for item in self._participations if item.team is team),
            None,
        )
        if participation is None:
            raise ValueError("Participation does not belong to this championship.")
        self._participations.remove(participation)

    def get_teams(self) -> list[FootballTeam]:
        ordered = sorted(self._participations, key=lambda item: item.position)
        return [item.team for item in ordered]

    def get_team_position(self, team: FootballTeam) -> int | None:
        participation = next(
            (item for item in self._participations if item.team is team),
            None,
        )
        return participation.position if participation else None

    def get_teams_by_position_range(self, start: int, end: int) -> list[FootballTeam]:
        if type(start) is not int or type(end) is not int:
            raise TypeError("Range boundaries must be integers.")
        if start < 1 or end < 1:
            raise ValueError("Range boundaries must be positive.")
        if start > end:
            raise ValueError("Start of range cannot be greater than end.")
        return [
            item.team
            for item in sorted(self._participations, key=lambda item: item.position)
            if start <= item.position <= end
        ]

    def find_team_by_name(self, name: str) -> list[FootballTeam]:
        if not isinstance(name, str):
            raise TypeError("Name must be a string.")
        search_name = name.strip().casefold()
        return [
            item.team for item in self._participations
            if search_name in item.team.name.casefold()
        ]

    def find_team_by_city(self, city: str) -> list[FootballTeam]:
        if not isinstance(city, str):
            raise TypeError("City must be a string.")
        search_city = city.strip().casefold()
        return [
            item.team for item in self._participations
            if search_city in item.team.city.casefold()
        ]

    def _update_position(
            self,
            participation: ChampionshipParticipation,
            position: int,
    ) -> None:
        if participation not in self._participations:
            raise ValueError("Participation does not belong to this championship.")
        if any(
                item is not participation and item.position == position
                for item in self._participations
        ):
            raise ValueError("This position is already taken")
        participation._position = position

    def __iter__(self) -> Iterator[ChampionshipParticipation]:
        return iter(self._participations.copy())

    def __len__(self) -> int:
        return len(self._participations)

    def __str__(self) -> str:
        return f"{self.name}, {self.country}, season {self.season}"

    def __repr__(self) -> str:
        return (
            f"Championship(name={self.name!r}, country={self.country!r}, "
            f"season={self.season!r}, id={self.id!r})"
        )
