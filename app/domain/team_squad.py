from collections.abc import Iterator

from app.domain.enums import PlayerPosition
from app.domain.player import Player


class TeamSquad:
    def __init__(self) -> None:
        self._players: list[Player] = []

    def add_player(self, player: Player) -> None:
        if not isinstance(player, Player):
            raise TypeError("Only Player objects can be added to the squad.")
        if player in self._players:
            raise ValueError("This player is already in the squad.")
        if any(item.shirt_number == player.shirt_number for item in self._players):
            raise ValueError("Shirt number is already taken in this squad.")
        self._players.append(player)

    def remove_player(self, player: Player) -> None:
        if not isinstance(player, Player):
            raise TypeError("A Player object must be provided.")
        if player not in self._players:
            raise ValueError("Player is not in the squad.")
        self._players.remove(player)

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
