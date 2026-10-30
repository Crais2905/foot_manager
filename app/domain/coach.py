from datetime import date

from app.domain.person import Person


class Coach(Person):
    def __init__(
        self,
        first_name: str,
        last_name: str,
        date_of_birth: date,
        experience_years: int,
        id: int | None = None,
    ) -> None:
        super().__init__(first_name, last_name, date_of_birth, id)
        if type(experience_years) is not int or experience_years < 0:
            raise ValueError("experience_years must be a positive integer.")
        self.experience_years = experience_years

    def __str__(self) -> str:
        return f"{self.full_name()}, experience: {self.experience_years} р."

    def __repr__(self) -> str:
        return (
            f"Coach(first_name={self.first_name!r}, last_name={self.last_name!r}, "
            f"date_of_birth={self.date_of_birth!r}, "
            f"experience_years={self.experience_years!r}, id={self.id!r})"
        )
