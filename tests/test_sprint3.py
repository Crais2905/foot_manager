from datetime import date

import pytest

from app.application import NationalTeamBuilder
from app.application.sorting import ShellSorter
from app.domain.championship import Championship
from app.domain.championship_participation import ChampionshipParticipation
from app.domain.coach import Coach
from app.domain.enums import PlayerPosition
from app.domain.football_team import FootballTeam
from app.domain.player import Player


@pytest.fixture
def players():
    return [Player(f"Player{i}", "Test", date(2000, 1, 1),
                   PlayerPosition.GOALKEEPER if i == 1 else PlayerPosition.DEFENDER,
                   i, i) for i in range(1, 13)]


@pytest.fixture
def league(coach):
    result = Championship("League", "Ukraine", "2026")
    for number in [3, 1, 4, 2]:
        result.add_team(FootballTeam(f"Team {number}", "Kyiv", coach), number)
    return result


@pytest.mark.parametrize("items", [[], [1], [5, 2, 4, 1, 3], [1, 2, 3], [3, 2, 1], [2, 1, 2, 1]])
def test_shell_sort(items):
    original = items.copy()
    result = ShellSorter.sort(items, key=lambda n: n)
    assert result == sorted(original)
    assert items == original
    assert result is not items


def test_shell_sort_arbitrary_objects():
    items = [{"rank": n} for n in [3, 1, 2, 1]]
    result = ShellSorter.sort(items, key=lambda item: item["rank"])
    assert [item["rank"] for item in result] == [1, 1, 2, 3]
    assert {id(item) for item in result} == {id(item) for item in items}


def test_championship_calls_shell_sort_and_keeps_state(league, monkeypatch):
    before = league.participations
    positions = [p.position for p in before]
    called = []
    original = ShellSorter.sort
    def spy(items, key):
        called.append(True)
        return original(items, key)
    monkeypatch.setattr(ShellSorter, "sort", spy)
    assert [league.get_team_position(t) for t in league.sort_by_position()] == [1, 2, 3, 4]
    assert called
    assert league.participations == before
    assert [p.position for p in before] == positions


@pytest.mark.parametrize("start,end,positions", [(2, 3, [2, 3]), (5, 6, []), (1, 9, [1, 2, 3, 4]), (2, 2, [2]), (3, 99, [3, 4])])
def test_range(league, start, end, positions):
    assert [league.get_team_position(t) for t in league.get_teams_by_position_range(start, end)] == positions


@pytest.mark.parametrize("start,end,error", [(0, 2, ValueError), (-1, 2, ValueError), (2, 0, ValueError), (3, 2, ValueError), (True, 2, TypeError), (1, 2.5, TypeError)])
def test_invalid_range(league, start, end, error):
    with pytest.raises(error):
        league.get_teams_by_position_range(start, end)


def test_empty_and_single_championship(coach):
    league = Championship("League", "Ukraine", "2026")
    assert league.sort_by_position() == league.sort_by_coach() == []
    team = FootballTeam("Team", "Kyiv", coach)
    participation = league.add_team(team, 1)
    assert league.sort_by_position() == [team]
    participation.set_position(5)
    assert participation.is_in_position_range(4, 5)
    with pytest.raises(ValueError):
        participation.is_in_position_range(6, 4)
    with pytest.raises(TypeError):
        ChampionshipParticipation(team, object(), 1)


def test_coach_sort_case_and_first_name():
    league = Championship("League", "Ukraine", "2026")
    names = [("Oleh", "Zulu"), ("Bohdan", "smith"), ("Anna", "SMITH")]
    teams = [FootballTeam(str(i), "Kyiv", Coach(first, last, date(1980, 1, 1), 1))
             for i, (first, last) in enumerate(names)]
    for i, team in enumerate(teams, 1):
        league.add_team(team, i)
    before = league.participations
    assert league.sort_by_coach() == [teams[2], teams[1], teams[0]]
    assert league.participations == before
    league.participations.clear()
    assert len(league) == 3


def test_builder_success_and_copies(players, coach):
    source = players.copy()
    builder = NationalTeamBuilder(source)
    source.clear()
    for player in players[:11]:
        builder.add_player(player)
    assert builder.validate_squad()
    builder.get_selected_players().clear()
    builder.selected_players.clear()
    builder.available_players.clear()
    assert len(builder.selected_players) == 11
    team = builder.build("Ukraine", "National", "Kyiv", coach)
    assert team.get_players() == players[:11]
    assert len(builder.selected_players) == 11
    builder.clear()
    assert builder.get_selected_players() == []
    assert len(team) == 11
    assert NationalTeamBuilder(players).selected_players == []


def test_builder_add_remove_errors_preserve_state(players, coach):
    builder = NationalTeamBuilder(players[:11])
    builder.add_player(players[0])
    for value, error in [(players[0], ValueError), (players[11], ValueError), (object(), TypeError)]:
        with pytest.raises(error):
            builder.add_player(value)
        assert builder.selected_players == [players[0]]
    with pytest.raises(ValueError):
        builder.remove_player(players[1])
    with pytest.raises(TypeError):
        builder.remove_player(object())
    with pytest.raises(ValueError):
        builder.build("Ukraine", "National", "Kyiv", coach)
    assert builder.selected_players == [players[0]]
    builder.remove_player(players[0])
    assert not builder.validate_squad()


def test_builder_requires_goalkeeper(players):
    builder = NationalTeamBuilder(players)
    for player in players[1:]:
        builder.add_player(player)
    assert not builder.validate_squad()


@pytest.mark.parametrize("field,value,error", [("country", " ", ValueError), ("name", "", ValueError), ("city", " ", ValueError), ("coach", None, TypeError)])
def test_builder_invalid_build_is_atomic(players, coach, field, value, error):
    builder = NationalTeamBuilder(players)
    for player in players[:11]:
        builder.add_player(player)
    kwargs = dict(country="Ukraine", name="National", city="Kyiv", coach=coach)
    kwargs[field] = value
    with pytest.raises(error):
        builder.build(**kwargs)
    assert builder.selected_players == players[:11]


@pytest.mark.parametrize("value,error", [(None, TypeError), ([object()], TypeError)])
def test_builder_invalid_available(value, error):
    with pytest.raises(error):
        NationalTeamBuilder(value)


def test_builder_duplicate_available(players):
    with pytest.raises(ValueError):
        NationalTeamBuilder([players[0], players[0]])


def test_full_scenario(players, coach):
    clubs = [FootballTeam("A", "Kyiv", coach), FootballTeam("B", "Lviv", coach)]
    origins = {}
    for i, player in enumerate(players):
        club = clubs[i % 2]
        club.add_player(player)
        origins[player] = club
    league = Championship("League", "Ukraine", "2026")
    league.add_team(clubs[0], 2)
    league.add_team(clubs[1], 1)
    assert league.sort_by_position() == clubs[::-1]
    assert league.get_teams_by_position_range(1, 1) == [clubs[1]]
    builder = NationalTeamBuilder(players, origins)
    for player in players[:11]:
        builder.add_player(player)
    national = builder.build("Ukraine", "National", "Kyiv", coach)
    assert national.validate_squad()
    assert len(national) == 11
    assert all(player in origins[player] for player in national)


@pytest.mark.parametrize("position,label", [(PlayerPosition.GOALKEEPER, "Воротар"), (PlayerPosition.DEFENDER, "Захисник"), (PlayerPosition.MIDFIELDER, "Півзахисник"), (PlayerPosition.FORWARD, "Нападник")])
def test_position_ukrainian_labels(position, label):
    assert position.display_name() == str(position) == label


def test_player_cannot_join_two_clubs_but_can_join_national(players, coach):
    first = FootballTeam("A", "Kyiv", coach)
    second = FootballTeam("B", "Lviv", coach)
    first.add_player(players[0])
    with pytest.raises(ValueError):
        second.add_player(players[0])
    assert first.get_players() == [players[0]]
    assert second.get_players() == []
    first.remove_player(players[0])
    second.add_player(players[0])
    assert players[0] in second


def test_squad_composition_is_exclusive(coach, players):
    from app.domain.team_squad import TeamSquad
    first = FootballTeam("A", "Kyiv", coach)
    first.add_player(players[0])
    with pytest.raises(ValueError):
        FootballTeam("B", "Lviv", coach, squad=first.squad)
    unowned = TeamSquad()
    unowned.add_player(players[0])
    with pytest.raises(ValueError):
        FootballTeam("B", "Lviv", coach, squad=unowned)
    assert players[0] in first


def test_invalid_as_of_is_not_silently_ignored(player):
    with pytest.raises(TypeError):
        player.age(False)
