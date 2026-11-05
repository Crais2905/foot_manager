from __future__ import annotations

from collections.abc import Iterator

from app.common.shell_sorter import ShellSorter
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
            raise TypeError("Назва, країна та сезон повинні бути рядками.")

        name, country, season = (value.strip() for value in values)
        if not name or not country or not season:
            raise ValueError("Назва, країна та сезон не можуть бути порожніми.")
        if id is not None and (type(id) is not int or id < 1):
            raise ValueError("ID повинен бути додатним цілим числом або None.")

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
            raise TypeError("Учасником чемпіонату повинна бути команда FootballTeam.")
        ChampionshipParticipation._validate_position(position)

        if any(item.team is team for item in self._participations):
            raise ValueError("Команда вже бере участь у цьому чемпіонаті.")
        if any(item.position == position for item in self._participations):
            raise ValueError("Це місце вже зайняте іншою командою.")

        participation = ChampionshipParticipation(team, self, position)
        self._participations.append(participation)
        return participation

    def remove_team(self, team: FootballTeam) -> None:
        participation = next(
            (item for item in self._participations if item.team is team),
            None,
        )
        if participation is None:
            raise ValueError("Команда не бере участі в цьому чемпіонаті.")
        self._participations.remove(participation)

    def sort_by_position(self) -> list[FootballTeam]:
        participations = ShellSorter.sort(
            self._participations,
            key=lambda participation: participation.position,
        )
        return [participation.team for participation in participations]

    def sort_by_coach(self) -> list[FootballTeam]:
        alphabet = "абвгґдеєжзиіїйклмнопрстуфхцчшщьюя"

        def name_key(name: str) -> tuple[int, ...]:
            return tuple(alphabet.index(char) if char in alphabet else len(alphabet) + ord(char)
                         for char in name.casefold())

        return sorted(
            (participation.team for participation in self._participations),
            key=lambda team: (
                name_key(team.coach.last_name),
                name_key(team.coach.first_name),
            ),
        )

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
            raise TypeError("Межі діапазону повинні бути цілими числами.")
        if start < 1 or end < 1:
            raise ValueError("Межі діапазону повинні бути додатними.")
        if start > end:
            raise ValueError("Початок діапазону не може бути більшим за кінець.")
        return [
            item.team
            for item in sorted(self._participations, key=lambda item: item.position)
            if start <= item.position <= end
        ]

    def find_team_by_name(self, name: str) -> list[FootballTeam]:
        if not isinstance(name, str):
            raise TypeError("Назва повинна бути рядком.")
        search_name = name.strip().casefold()
        return [
            item.team for item in self._participations
            if search_name in item.team.name.casefold()
        ]

    def find_team_by_city(self, city: str) -> list[FootballTeam]:
        if not isinstance(city, str):
            raise TypeError("Місто повинно бути рядком.")
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
            raise ValueError("Участь не належить цьому чемпіонату.")
        if any(
            item is not participation and item.position == position
            for item in self._participations
        ):
            raise ValueError("Це місце вже зайняте іншою командою.")
        participation._position = position

    def __iter__(self) -> Iterator[ChampionshipParticipation]:
        return iter(self._participations.copy())

    def __len__(self) -> int:
        return len(self._participations)

    def __str__(self) -> str:
        return f"{self.name}, {self.country}, сезон {self.season}"

    def __repr__(self) -> str:
        return (
            f"Championship(name={self.name!r}, country={self.country!r}, "
            f"season={self.season!r}, id={self.id!r})"
        )


class ChampionshipParticipation:
    def __init__(
        self,
        team: FootballTeam,
        championship: Championship,
        position: int,
        id: int | None = None,
    ) -> None:
        if not isinstance(team, FootballTeam):
            raise TypeError("Participant must be a FootballTeam.")
        if not isinstance(championship, Championship):
            raise TypeError("Championship must be a Championship object.")
        if id is not None and (type(id) is not int or id < 1):
            raise ValueError("ID must be a positive integer or None.")
        self._validate_position(position)

        self.id = id
        self.team = team
        self.championship = championship
        self._position = position

    @staticmethod
    def _validate_position(position: int) -> None:
        if type(position) is not int or position < 1:
            raise ValueError("Position must be a positive integer.")

    @property
    def position(self) -> int:
        return self._position

    @position.setter
    def position(self, position: int) -> None:
        self._validate_position(position)
        self.championship._update_position(self, position)

    def set_position(self, position: int) -> None:
        self.position = position

    def is_in_position_range(self, start: int, end: int) -> bool:
        if type(start) is not int or type(end) is not int:
            raise TypeError("Range boundaries must be integers.")
        if start > end:
            raise ValueError("Start of range cannot be greater than end.")
        return start <= self.position <= end

    def __str__(self) -> str:
        return f"{self.team.name}: {self.position} place"

    def __repr__(self) -> str:
        return (
            f"ChampionshipParticipation(team={self.team!r}, "
            f"position={self.position!r}, id={self.id!r})"
        )
