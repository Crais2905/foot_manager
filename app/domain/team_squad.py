from __future__ import annotations

from collections.abc import Iterator
from typing import TYPE_CHECKING
from weakref import ReferenceType, ref

from app.domain.enums import PlayerPosition
from app.domain.player import Player


if TYPE_CHECKING:
    from app.domain.football_team import FootballTeam


class TeamSquad:
    def __init__(self) -> None:
        self._players: list[Player] = []
        self._owner: ReferenceType[FootballTeam] | None = None
        self._exclusive_club_membership = False

    def _is_club(self) -> bool:
        owner = self._owner() if self._owner is not None else None
        return owner is not None and self._exclusive_club_membership

    def _bind_team(
        self, team: FootballTeam, *, exclusive_club_membership: bool
    ) -> None:

        owner = self._owner() if self._owner is not None else None
        if owner is not None and owner is not team:
            raise ValueError("A squad cannot belong to two teams.")
        if exclusive_club_membership:
            for player in self._players:
                self._validate_club_membership(player)
        self._owner = ref(team)
        self._exclusive_club_membership = exclusive_club_membership
        if exclusive_club_membership:
            for player in self._players:
                player._club_squad = ref(self)

    def _validate_club_membership(self, player: Player) -> None:
        club_squad = player._club_squad() if player._club_squad is not None else None
        if club_squad is not None and club_squad is not self:
            if club_squad._is_club():
                raise ValueError("Player already belongs to another club squad.")

    def add_player(self, player: Player) -> None:
        if not isinstance(player, Player):
            raise TypeError("Only Player objects can be added to the squad.")
        if player in self._players:
            raise ValueError("This player is already in the squad.")
        if any(item.shirt_number == player.shirt_number for item in self._players):
            raise ValueError("Shirt number is already taken in this squad.")
        if self._is_club():
            self._validate_club_membership(player)
        self._players.append(player)
        if self._is_club():
            player._club_squad = ref(self)

    def remove_player(self, player: Player) -> None:
        if not isinstance(player, Player):
            raise TypeError("A Player object must be provided.")
        if player not in self._players:
            raise ValueError("Player is not in the squad.")
        self._players.remove(player)
        if player._club_squad is not None and player._club_squad() is self:
            player._club_squad = None

    def contains(self, player: Player) -> bool:
        return player in self._players

    def find_player(self, player_id: int) -> Player | None:
        if type(player_id) is not int:
            raise TypeError("Player ID must be an integer.")
        return next(
            (player for player in self._players if player.id == player_id),
            None,
        )

    def get_by_position(self, position: PlayerPosition) -> list[Player]:
        if not isinstance(position, PlayerPosition):
            raise TypeError("Position must be a PlayerPosition value.")
        return [player for player in self._players if player.position is position]

    def count_by_position(self, position: PlayerPosition) -> int:
        return len(self.get_by_position(position))

    def get_players(self) -> list[Player]:
        return self._players.copy()

    def players_count(self) -> int:
        return len(self._players)

    def __iter__(self) -> Iterator[Player]:
        return iter(self._players.copy())

    def __len__(self) -> int:
        return len(self._players)

    def __contains__(self, player: object) -> bool:
        return player in self._players

    def __getitem__(self, index: int) -> Player:
        return self._players[index]
