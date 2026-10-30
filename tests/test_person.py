from datetime import date

import pytest

from app.domain.person import Person

def test_person_strips_names_and_builds_full_name() -> None:
    person = Person("  Іван ", " Петренко  ", date(2000, 6, 10))
    assert person.full_name() == "Іван Петренко"


def test_age_before_birthday() -> None:
    person = Person("Іван", "Петренко", date(2000, 12, 10))
    assert person.age(date(2024, 6, 1)) == 23


def test_age_after_birthday() -> None:
    person = Person("Іван", "Петренко", date(2000, 3, 10))
    assert person.age(date(2024, 6, 1)) == 24


@pytest.mark.parametrize(
    "first_name,last_name",
    [("", "Петренко"), ("   ", "Петренко"), ("Іван", " ")],
)
def test_empty_names_are_rejected(first_name: str, last_name: str) -> None:
    with pytest.raises(ValueError):
        Person(first_name, last_name, date(2000, 1, 1))


def test_future_birth_date_is_rejected() -> None:
    with pytest.raises(ValueError):
        Person("Іван", "Петренко", date(2999, 1, 1))
