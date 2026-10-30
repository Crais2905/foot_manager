from datetime import date

import pytest

from app.domain.coach import Coach
from app.domain.player import Player
from app.domain.enums import PlayerPosition

@pytest.fixture
def coach() -> Coach:
    return Coach("Олег", "Шевченко", date(1980, 5, 12), 12)


@pytest.fixture
def player() -> Player:
    return Player("Андрій", "Коваленко", date(2000, 3, 20), PlayerPosition.FORWARD, 9, 1)
