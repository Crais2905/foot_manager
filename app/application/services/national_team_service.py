from dataclasses import dataclass

from app.application.exceptions import ApplicationValidationError
from app.application.national_team_builder import NationalTeamBuilder
from app.application.services._base import Service, logged_operation, require, validated
from app.domain.coach import Coach
from app.domain.national_team import NationalTeam
from app.domain.player import Player
from app.infrastructure.unit_of_work import UnitOfWork


@dataclass(frozen=True)
class RosterCandidate:
    player: Player
    club_name: str


class NationalTeamService(Service):
    async def get_available_players(self, country: str) -> list[Player]:
        return [candidate.player for candidate in await self.get_roster_candidates(country)]

    async def get_roster_candidates(self, country: str) -> list[RosterCandidate]:
        if not isinstance(country, str) or not country.strip():
            raise ApplicationValidationError("Вкажіть країну збірної.")
        async with self._uow() as work:
            clubs = await work.teams.get_player_clubs()
            return [
                RosterCandidate(player, clubs[player.id].name)
                for player in await work.players.get_by_ids(list(clubs))
                if player.id is not None and player.id in clubs
            ]

    async def get_all_national_teams(self) -> list[NationalTeam]:
        async with self._uow() as work:
            return [team for team in await work.teams.get_all() if isinstance(team, NationalTeam)]

    async def _build(
        self, work: UnitOfWork, country: str, name: str, city: str, coach: Coach,
        player_ids: list[int], shirt_numbers: dict[int, int],
    ) -> NationalTeam:
        if any(type(player_id) is not int or player_id <= 0 for player_id in player_ids):
            raise ApplicationValidationError("Player IDs must be positive integers.")
        if len(set(player_ids)) != len(player_ids):
            raise ApplicationValidationError("A player can only be selected once.")
        if shirt_numbers.keys() - set(player_ids):
            raise ApplicationValidationError("Shirt numbers must belong to selected players.")

        players = {player.id: player for player in await work.players.get_by_ids(player_ids)}
        selected = [require(players.get(player_id), "Player", player_id) for player_id in player_ids]
        clubs = await work.teams.get_player_clubs(player_ids)
        origins = {player: clubs[player.id] for player in selected
                   if player.id is not None and player.id in clubs}
        errors = []
        if len(origins) != len(selected):
            errors.append("Усі вибрані гравці мають належати до клубів.")

        builder = NationalTeamBuilder(selected, origins)
        for player_id, player in zip(player_ids, selected, strict=True):
            number = shirt_numbers.get(player_id, player.shirt_number)
            if type(number) is not int or not 1 <= number <= 99:
                raise ApplicationValidationError("Shirt numbers must be integers from 1 to 99.")
            validated(builder.add_player, player, number)
        errors.extend(builder.validation_errors())
        if errors:
            raise ApplicationValidationError("\n".join(errors))
        return validated(builder.build, country, name, city, coach)

    @logged_operation
    async def create_national_team(
        self, country: str, name: str, city: str, coach_id: int,
        player_ids: list[int], shirt_numbers: dict[int, int],
    ) -> NationalTeam:
        async with self._uow() as work:
            coach = require(await work.coaches.get_by_id(coach_id), "Coach", coach_id)
            team = await self._build(work, country, name, city, coach, player_ids, shirt_numbers)
            saved = await work.teams.add(team)
            assert isinstance(saved, NationalTeam)
            await work.commit()
            return saved

    async def get_national_team(self, team_id: int) -> NationalTeam | None:
        async with self._uow() as work:
            team = await work.teams.get_by_id(team_id)
            return team if isinstance(team, NationalTeam) else None

    @logged_operation
    async def update_squad(
        self, team_id: int, player_ids: list[int], shirt_numbers: dict[int, int] | None = None,
    ) -> NationalTeam:
        async with self._uow() as work:
            team = await work.teams.get_by_id(team_id, for_update=True)
            current = require(team if isinstance(team, NationalTeam) else None, "National team", team_id)
            numbers = {entry.player.id: entry.shirt_number for entry in current.squad.memberships
                       if entry.player.id is not None and entry.player.id in player_ids}
            numbers.update(shirt_numbers or {})
            replacement = await self._build(
                work, current.country, current.name, current.city, current.coach, player_ids, numbers,
            )
            replacement.id = current.id
            saved = await work.teams.update(replacement)
            assert isinstance(saved, NationalTeam)
            await work.commit()
            return saved


    @logged_operation
    async def delete_national_team(self, team_id: int) -> None:
        async with self._uow() as work:
            team = await work.teams.get_by_id(team_id, for_update=True)
            require(team if isinstance(team, NationalTeam) else None, "Збірну", team_id)
            await work.teams.delete(team_id)
            await work.commit()
