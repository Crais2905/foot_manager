from datetime import date

import pytest

from app.domain.team_squad import TeamSquad
from app.domain.player import Player
from app.domain.enums import PlayerPosition


def make_player(first: str, number: int, position: PlayerPosition = PlayerPosition.DEFENDER) -> Player:
    return Player(first, "Тест", date(2001, 1, 1), position, number)


def test_add_remove_and_count_players(player: Player) -> None:
    squad = TeamSquad()
    squad.add_player(player)
    assert len(squad) == 1
    assert squad.contains(player)
    squad.remove_player(player)
    assert len(squad) == 0


def test_duplicate_player_is_rejected(player: Player) -> None:
    squad = TeamSquad()
    squad.add_player(player)
    with pytest.raises(ValueError):
        squad.add_player(player)


def test_duplicate_shirt_number_is_rejected(player: Player) -> None:
    squad = TeamSquad()
    squad.add_player(player)
    other = make_player("Інший", player.shirt_number)
    with pytest.raises(ValueError):
        squad.add_player(other)


def test_same_shirt_number_allowed_in_different_squads(player: Player) -> None:
    first = TeamSquad()
    second = TeamSquad()
    first.add_player(player)
    second.add_player(make_player("Інший", player.shirt_number))
    assert len(first) == len(second) == 1


def test_get_players_returns_copy(player: Player) -> None:
    squad = TeamSquad()
    squad.add_player(player)
    result = squad.get_players()
    result.clear()
    assert len(squad) == 1


def test_find_player_by_id(player: Player) -> None:
    squad = TeamSquad()
    squad.add_player(player)
    assert squad.find_player(1) is player
    assert squad.find_player(999) is None


def test_filter_by_position(player: Player) -> None:
    squad = TeamSquad()
    squad.add_player(player)
    squad.add_player(make_player("Захисник", 4))
    assert squad.count_by_position(PlayerPosition.FORWARD) == 1
    assert len(squad.get_by_position(PlayerPosition.DEFENDER)) == 1
