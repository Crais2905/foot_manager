from __future__ import annotations

from typing import TYPE_CHECKING

from app.domain.football_team import FootballTeam

if TYPE_CHECKING:
    from app.domain.championship import Championship


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
