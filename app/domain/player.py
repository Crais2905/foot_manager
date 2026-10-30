from datetime import date

from app.domain.enums import PlayerPosition
from app.domain.person import Person


class Player(Person):
    def __init__(
        self,
        first_name: str,
        last_name: str,
        date_of_birth: date,
        position: PlayerPosition,
        shirt_number: int,
        id: int | None = None,
    ) -> None:
        super().__init__(first_name, last_name, date_of_birth, id)

        if not isinstance(position, PlayerPosition):
            raise TypeError("Position must be a PlayerPosition value.")
        if type(shirt_number) is not int or not 1 <= shirt_number <= 99:
            raise ValueError("Shirt number must be an integer from 1 to 99.")

        self.position = position
        self.shirt_number = shirt_number

    def is_goalkeeper(self) -> bool:
        return self.position is PlayerPosition.GOALKEEPER

    def is_defender(self) -> bool:
        return self.position is PlayerPosition.DEFENDER

    def is_midfielder(self) -> bool:
        return self.position is PlayerPosition.MIDFIELDER

    def is_forward(self) -> bool:
        return self.position is PlayerPosition.FORWARD

    def __str__(self) -> str:
        return f"{self.full_name()} — {self.position}, #{self.shirt_number}"

    def __repr__(self) -> str:
        return (
            f"Player(first_name={self.first_name!r}, last_name={self.last_name!r}, "
            f"date_of_birth={self.date_of_birth!r}, position={self.position!r}, "
            f"shirt_number={self.shirt_number!r}, id={self.id!r})"
        )