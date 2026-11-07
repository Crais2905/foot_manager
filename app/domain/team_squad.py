from __future__ import annotations

from collections.abc import Iterator
from typing import TYPE_CHECKING
from weakref import ReferenceType, ref

from app.domain.errors import DomainConflictError
from app.domain.enums import PlayerPosition
from app.domain.player import Player
from app.domain.squad_membership import SquadMembership


if TYPE_CHECKING:
    from app.domain.football_team import FootballTeam


class TeamSquad:
    def __init__(self) -> None:
        self._memberships: list[SquadMembership] = []
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
            raise DomainConflictError("A squad cannot belong to two teams.")
        if exclusive_club_membership:
            for player in self:
                self._validate_club_membership(player)
        self._owner = ref(team)
        self._exclusive_club_membership = exclusive_club_membership
        if exclusive_club_membership:
            for player in self:
                player._club_squad = ref(self)

    def _validate_club_membership(self, player: Player) -> None:
        club_squad = player._club_squad() if player._club_squad is not None else None
        if club_squad is not None and club_squad is not self:
            if club_squad._is_club():
                raise DomainConflictError("Player already belongs to another club squad.")

    def add_player(self, player: Player, shirt_number: int | None = None) -> None:
        if not isinstance(player, Player):
            raise TypeError("Only Player objects can be added to the squad.")
        if player in self:
            raise DomainConflictError("Цей гравець уже є у складі.")
        membership = SquadMembership(
            player, player.shirt_number if shirt_number is None else shirt_number
        )
        if any(item.shirt_number == membership.shirt_number for item in self._memberships):
            raise DomainConflictError(f"Номер {membership.shirt_number} уже використовується у складі.")
        if self._is_club():
            self._validate_club_membership(player)
            player._club_squad = ref(self)
        self._memberships.append(membership)

    def remove_player(self, player: Player) -> None:
        if not isinstance(player, Player):
            raise TypeError("A Player object must be provided.")
        membership = next((item for item in self._memberships
                           if self._same_player(item.player, player)), None)
        if membership is None:
            raise ValueError("Player is not in the squad.")
        self._memberships.remove(membership)
        member = membership.player
        if member._club_squad is not None and member._club_squad() is self:
            member._club_squad = None

    @staticmethod
    def _same_player(first: Player, second: Player) -> bool:
        return first is second or (first.id is not None and first.id == second.id)

    def contains(self, player: Player) -> bool:
        return player in self

    @property
    def memberships(self) -> tuple[SquadMembership, ...]:
        return tuple(self._memberships)

    def find_player(self, player_id: int) -> Player | None:
        if type(player_id) is not int:
            raise TypeError("Player ID must be an integer.")
        return next(
            (player for player in self if player.id == player_id),
            None,
        )

    def get_by_position(self, position: PlayerPosition) -> list[Player]:
        if not isinstance(position, PlayerPosition):
            raise TypeError("Position must be a PlayerPosition value.")
        return [player for player in self if player.position is position]

    def count_by_position(self, position: PlayerPosition) -> int:
        return len(self.get_by_position(position))

    def get_players(self) -> list[Player]:
        return [item.player for item in self._memberships]

    def players_count(self) -> int:
        return len(self._memberships)

    def __iter__(self) -> Iterator[Player]:
        return iter(self.get_players())

    def __len__(self) -> int:
        return len(self._memberships)

    def __contains__(self, player: object) -> bool:
        return isinstance(player, Player) and any(
            self._same_player(member.player, player) for member in self._memberships
        )

    def __getitem__(self, index: int) -> Player:
        return self._memberships[index].player
