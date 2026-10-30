from datetime import date

from app.domain.coach import Coach
from app.domain.national_team import NationalTeam
from app.domain.player import Player
from app.domain.enums import PlayerPosition


def test_national_team_requires_minimum_squad(coach: Coach) -> None:
    team = NationalTeam("Збірна України", "Київ", coach, "Україна")
    assert not team.validate_squad()

    for number in range(1, 12):
        team.add_player(
            Player(
                f"Гравець{number}",
                "Тест",
                date(2000, 1, 1),
                PlayerPosition.DEFENDER,
                number,
            )
        )

    assert team.validate_squad()
    assert team.get_country() == "Україна"
