from dataclasses import dataclass

from app.domain.player import Player


@dataclass(frozen=True)
class SquadMembership:
    player: Player
    shirt_number: int

    def __post_init__(self) -> None:
        if not isinstance(self.player, Player):
            raise TypeError("Membership requires a Player.")
        if type(self.shirt_number) is not int or not 1 <= self.shirt_number <= 99:
            raise ValueError("Shirt number must be an integer from 1 to 99.")
