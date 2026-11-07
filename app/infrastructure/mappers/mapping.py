from typing import TypeVar, cast

from app.db.models import (
    ChampionshipModel, ChampionshipParticipationModel, CoachModel, FootballTeamModel,
    NationalTeamModel, PersonModel, PlayerModel, SquadPlayerModel,
)
from app.domain.championship import Championship, ChampionshipParticipation
from app.domain.coach import Coach
from app.domain.football_team import FootballTeam
from app.domain.national_team import NationalTeam
from app.domain.person import Person
from app.domain.player import Player

T = TypeVar("T")


class IdentityMap:
    """Share objects within one mapped graph, including transient entities."""

    def __init__(self) -> None:
        self._objects: dict[tuple[type, str, int], object] = {}

    @staticmethod
    def _key(source: object, entity_id: int | None) -> tuple[type, str, int]:
        return (type(source), "new", id(source)) if entity_id is None else (
            type(source), "saved", entity_id
        )

    def get(self, source: object, entity_id: int | None, kind: type[T]) -> T | None:
        value = self._objects.get(self._key(source, entity_id))
        return cast(T, value) if isinstance(value, kind) else None

    def put(self, source: object, entity_id: int | None, target: object) -> None:
        self._objects[self._key(source, entity_id)] = target


class PersonMapper:
    @staticmethod
    def to_domain(model: PersonModel, identities: IdentityMap | None = None) -> Person:
        identities = identities or IdentityMap()
        existing = identities.get(model, model.id, Person)
        if existing is not None:
            return existing
        args = (model.first_name, model.last_name, model.date_of_birth)
        person: Person
        if isinstance(model, PlayerModel):
            person = Player(*args, model.position, model.shirt_number, id=model.id)
        elif isinstance(model, CoachModel):
            person = Coach(*args, model.experience_years, id=model.id)
        else:
            person = Person(*args, id=model.id)
        identities.put(model, model.id, person)
        return person

    @staticmethod
    def to_model(person: Person, identities: IdentityMap | None = None) -> PersonModel:
        identities = identities or IdentityMap()
        existing = identities.get(person, person.id, PersonModel)
        if existing is not None:
            return existing
        if isinstance(person, Player):
            model: PersonModel = PlayerModel()
        elif isinstance(person, Coach):
            model = CoachModel()
        else:
            model = PersonModel()
        if person.id is not None:
            model.id = person.id
        PersonMapper.copy_fields(person, model)
        identities.put(person, person.id, model)
        return model

    @staticmethod
    def copy_fields(person: Person, model: PersonModel) -> None:
        model.first_name = person.first_name
        model.last_name = person.last_name
        model.date_of_birth = person.date_of_birth
        if isinstance(person, Player) and isinstance(model, PlayerModel):
            model.position = person.position
            model.shirt_number = person.shirt_number
        if isinstance(person, Coach) and isinstance(model, CoachModel):
            model.experience_years = person.experience_years


class TeamMapper:
    @staticmethod
    def to_domain(
        model: FootballTeamModel, identities: IdentityMap | None = None
    ) -> FootballTeam:
        identities = identities or IdentityMap()
        existing = identities.get(model, model.id, FootballTeam)
        if existing is not None:
            return existing
        coach = cast(Coach, PersonMapper.to_domain(model.coach, identities))
        if isinstance(model, NationalTeamModel):
            team: FootballTeam = NationalTeam(
                model.name, model.city, coach, model.country, id=model.id
            )
        else:
            team = FootballTeam(model.name, model.city, coach, id=model.id)
        if model.squad is not None:
            for membership in model.squad.memberships:
                player = cast(Player, PersonMapper.to_domain(membership.player, identities))
                team.add_player(player, membership.shirt_number)
        identities.put(model, model.id, team)
        return team

    @staticmethod
    def to_model(team: FootballTeam, identities: IdentityMap | None = None) -> FootballTeamModel:
        identities = identities or IdentityMap()
        existing = identities.get(team, team.id, FootballTeamModel)
        if existing is not None:
            return existing
        model = NationalTeamModel() if isinstance(team, NationalTeam) else FootballTeamModel()
        if team.id is not None:
            model.id = team.id
        TeamMapper.copy_fields(team, model, identities)
        model.squad.memberships = [
            SquadPlayerModel(
                player=PersonMapper.to_model(membership.player, identities),
                shirt_number=membership.shirt_number,
            )
            for membership in team.squad.memberships
        ]
        identities.put(team, team.id, model)
        return model

    @staticmethod
    def copy_fields(team: FootballTeam, model: FootballTeamModel, identities: IdentityMap) -> None:
        model.name = team.name
        model.city = team.city
        model.coach = cast(CoachModel, PersonMapper.to_model(team.coach, identities))
        if isinstance(team, NationalTeam) and isinstance(model, NationalTeamModel):
            model.country = team.country


class ChampionshipMapper:
    @staticmethod
    def to_domain(model: ChampionshipModel, identities: IdentityMap | None = None) -> Championship:
        identities = identities or IdentityMap()
        championship = Championship(model.name, model.country, model.season, id=model.id)
        for entry in model.participations:
            team = TeamMapper.to_domain(entry.team, identities)
            participation = championship.add_team(team, entry.position)
            participation.id = entry.id
        return championship

    @staticmethod
    def to_model(
        championship: Championship, identities: IdentityMap | None = None
    ) -> ChampionshipModel:
        identities = identities or IdentityMap()
        model = ChampionshipModel(name=championship.name, country=championship.country,
                                  season=championship.season)
        if championship.id is not None:
            model.id = championship.id
        model.participations = [
            ChampionshipMapper.participation_to_model(entry, identities)
            for entry in championship.participations
        ]
        return model

    @staticmethod
    def participation_to_model(
        entry: ChampionshipParticipation, identities: IdentityMap
    ) -> ChampionshipParticipationModel:
        model = ChampionshipParticipationModel(
            team=TeamMapper.to_model(entry.team, identities), position=entry.position
        )
        if entry.id is not None:
            model.id = entry.id
        return model
