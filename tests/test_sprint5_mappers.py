from datetime import date

from app.application.national_team_builder import NationalTeamBuilder
from app.db.models import NationalTeamModel, PlayerModel
from app.domain.championship import Championship
from app.domain.coach import Coach
from app.domain.enums import PlayerPosition
from app.domain.football_team import FootballTeam
from app.domain.national_team import NationalTeam
from app.domain.player import Player
from app.infrastructure.mappers import ChampionshipMapper, PersonMapper, TeamMapper


def test_transient_graph_round_trip_preserves_identity_and_squad_numbers():
    coach = Coach("John", "Smith", date(1980, 1, 1), 10)
    player = Player("Sam", "Jones", date(2000, 1, 1), PlayerPosition.GOALKEEPER, 8)
    club = FootballTeam("Club", "Kyiv", coach)
    national = NationalTeam("National", "Kyiv", coach, "Ukraine")
    club.add_player(player, 10)
    national.add_player(player, 15)
    championship = Championship("Cup", "Ukraine", "2026")
    championship.add_team(club, 1)
    championship.add_team(national, 2)

    model = ChampionshipMapper.to_model(championship)
    club_model, national_model = [entry.team for entry in model.participations]
    assert isinstance(national_model, NationalTeamModel)
    assert club_model.coach is national_model.coach
    assert club_model.squad.players[0] is national_model.squad.players[0]
    assert isinstance(club_model.squad.players[0], PlayerModel)
    assert isinstance(PersonMapper.to_domain(club_model.squad.players[0]), Player)
    assert isinstance(TeamMapper.to_domain(national_model), NationalTeam)

    restored = ChampionshipMapper.to_domain(model)
    a, b = restored.sort_by_position()
    assert isinstance(b, NationalTeam)
    assert a.coach is b.coach and a[0] is b[0]
    assert a[0].shirt_number == 8
    assert a.squad.memberships[0].shirt_number == 10
    assert b.squad.memberships[0].shirt_number == 15


def test_builder_checks_distinct_clubs_and_numbers_in_the_selected_roster():
    coach = Coach("John", "Smith", date(1980, 1, 1), 10)
    club = FootballTeam("Club", "Kyiv", coach, id=3)
    same_club = FootballTeam("Club", "Kyiv", coach, id=3)
    other_club = FootballTeam("Other", "Lviv", coach, id=4)
    players = [
        Player("Sam", str(index), date(2000, 1, 1),
               PlayerPosition.GOALKEEPER if index == 0 else PlayerPosition.DEFENDER, 1)
        for index in range(11)
    ]
    single_club = {player: club for player in players}
    single_club[players[-1]] = same_club
    mixed_clubs = {**single_club, players[-1]: other_club}
    for origins, expected in ((single_club, False), (mixed_clubs, True)):
        builder = NationalTeamBuilder(players, origins)
        for number, player in enumerate(players, 1):
            builder.add_player(player, number)
        assert builder.validate_squad() is expected
        if expected:
            team = builder.build("Ukraine", "National", "Kyiv", coach)
            assert [member.shirt_number for member in team.squad.memberships] == list(range(1, 12))
            assert all(player.shirt_number == 1 for player in team)
