from enum import Enum


class PlayerPosition(Enum):
    GOALKEEPER = "goalkeeper"
    DEFENDER = "defender"
    MIDFIELDER = "midfielder"
    FORWARD = "forward"

    def display_name(self) -> str:
        return {
            self.GOALKEEPER: "Воротар",
            self.DEFENDER: "Захисник",
            self.MIDFIELDER: "Півзахисник",
            self.FORWARD: "Нападник",
        }[self]

    def __str__(self) -> str:
        return self.display_name()
