from datetime import date

import pytest

from app.domain.coach import Coach
from app.domain.player import Player
from app.domain.enums import PlayerPosition


def test_player_position_helpers(player: Player) -> None:
    assert player.is_forward()
    assert not player.is_goalkeeper()
    assert not player.is_defender()
    assert not player.is_midfielder()


@pytest.mark.parametrize("number", [0, 100, True, 4.5])
def test_invalid_shirt_number_is_rejected(number: int) -> None:
    with pytest.raises(ValueError):
        Player("Іван", "Тест", date(2001, 1, 1), PlayerPosition.DEFENDER, number)


def test_invalid_position_is_rejected() -> None:
    with pytest.raises(TypeError):
        Player("Іван", "Тест", date(2001, 1, 1), "воротар", 1)


def test_coach_rejects_negative_experience() -> None:
    with pytest.raises(ValueError):
        Coach("Олег", "Тест", date(1980, 1, 1), -1)
