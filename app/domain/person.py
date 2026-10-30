from datetime import date


class Person:
    def __init__(
        self,
        first_name: str,
        last_name: str,
        date_of_birth: date,
        id: int | None = None,
    ) -> None:
        if not isinstance(first_name, str) or not isinstance(last_name, str):
            raise TypeError("First name and last name must be strings.")
        if not isinstance(date_of_birth, date):
            raise TypeError("Date of birth must be of type date.")
        if id is not None and (type(id) is not int or id < 1):
            raise ValueError("ID must be a positive integer or None.")

        first_name = first_name.strip()
        last_name = last_name.strip()
        if not first_name or not last_name:
            raise ValueError("First name and last name cannot be empty.")
        if date_of_birth > date.today():
            raise ValueError("Date of birth cannot be in the future.")

        self.id = id
        self.first_name = first_name
        self.last_name = last_name
        self.date_of_birth = date_of_birth

    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"

    def age(self, as_of: date | None = None) -> int:
        current_date = as_of or date.today()
        if not isinstance(current_date, date):
            raise TypeError("Age calculation date must be of type date.")
        if current_date < self.date_of_birth:
            raise ValueError("Age calculation date precedes date of birth.")

        years = current_date.year - self.date_of_birth.year
        if (current_date.month, current_date.day) < (
            self.date_of_birth.month,
            self.date_of_birth.day,
        ):
            years -= 1
        return years

    def __str__(self) -> str:
        return f"{self.full_name()}, {self.age()} y.o."

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}(first_name={self.first_name!r}, "
            f"last_name={self.last_name!r}, "
            f"date_of_birth={self.date_of_birth!r}, id={self.id!r})"
        )