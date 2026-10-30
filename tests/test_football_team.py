from datetime import date

import pytest

from app.domain.coach import Coach
from app.domain.football_team import FootballTeam
from app.domain.player import Player
from app.domain.enums import PlayerPosition

def test_team_delegates_squad_methods(coach: Coach, player: Player) -> None:
    team = FootballTeam("Динамо", "Київ", coach)
    team.add_player(player)
    assert team.players_count() == 1
    assert team.has_player(player)
    assert player in team
    assert len(team) == 1
    assert team[0] is player


def test_team_can_change_coach(coach: Coach) -> None:
    team = FootballTeam("Динамо", "Київ", coach)
    new_coach = Coach("Ігор", "Тест", date(1975, 2, 1), 20)
    team.set_coach(new_coach)
    assert team.get_coach() is new_coach


def test_team_rejects_blank_name(coach: Coach) -> None:
    with pytest.raises(ValueError):
        FootballTeam(" ", "Київ", coach)


def test_team_remove_player(coach: Coach, player: Player) -> None:
    team = FootballTeam("Динамо", "Київ", coach)
    team.add_player(player)
    team.remove_player(player)
    assert len(team) == 0
