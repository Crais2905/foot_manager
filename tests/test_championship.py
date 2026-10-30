from datetime import date

import pytest

from app.domain.coach import Coach
from app.domain.championship import Championship
from app.domain.football_team import FootballTeam

def make_team(name: str, city: str = "Київ") -> FootballTeam:
    coach = Coach("Олег", "Тест", date(1980, 1, 1), 10)
    return FootballTeam(name, city, coach)


def test_add_team_and_get_position() -> None:
    championship = Championship("Прем'єр-ліга", "Україна", "2025/2026")
    team = make_team("Динамо")
    participation = championship.add_team(team, 1)
    assert len(championship) == 1
    assert championship.get_team_position(team) == 1
    assert participation.position == 1


def test_duplicate_team_and_position_are_rejected() -> None:
    championship = Championship("Ліга", "Україна", "2025")
    first = make_team("Динамо")
    second = make_team("Шахтар", "Донецьк")
    championship.add_team(first, 1)
    with pytest.raises(ValueError):
        championship.add_team(first, 2)
    with pytest.raises(ValueError):
        championship.add_team(second, 1)
    assert len(championship) == 1


def test_change_position_keeps_positions_unique() -> None:
    championship = Championship("Ліга", "Україна", "2025")
    first = make_team("Динамо")
    second = make_team("Шахтар", "Донецьк")
    participation = championship.add_team(first, 1)
    championship.add_team(second, 2)

    with pytest.raises(ValueError):
        participation.position = 2
    assert participation.position == 1

    participation.position = 3
    assert participation.position == 3


def test_teams_are_sorted_by_position() -> None:
    championship = Championship("Ліга", "Україна", "2025")
    first = make_team("Динамо")
    second = make_team("Шахтар", "Донецьк")
    championship.add_team(first, 2)
    championship.add_team(second, 1)
    assert championship.get_teams() == [second, first]
    assert championship.get_teams_by_position_range(1, 1) == [second]


def test_search_is_case_insensitive_and_returns_multiple_results() -> None:
    championship = Championship("Ліга", "Україна", "2025")
    first = make_team("Динамо Київ", "Київ")
    second = make_team("Динамо-2", "Київ")
    championship.add_team(first, 1)
    championship.add_team(second, 2)
    assert championship.find_team_by_name("ДИНАМО") == [first, second]
    assert championship.find_team_by_city("київ") == [first, second]


def test_remove_team() -> None:
    championship = Championship("Ліга", "Україна", "2025")
    team = make_team("Динамо")
    championship.add_team(team, 1)
    championship.remove_team(team)
    assert len(championship) == 0
    assert championship.get_team_position(team) is None


def test_invalid_position_range_is_rejected() -> None:
    championship = Championship("Ліга", "Україна", "2025")
    with pytest.raises(ValueError):
        championship.get_teams_by_position_range(4, 2)
