from enum import Enum


class PlayerPosition(Enum):
    GOALKEEPER = "Goalkeeper"
    DEFENDER = "Defender"
    MIDFIELDER = "Midfielder"
    FORWARD = "Forward"

    def display_name(self) -> str:
        return self.value

    def __str__(self) -> str:
        return self.display_name()
