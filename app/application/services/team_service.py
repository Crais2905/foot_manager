from app.application.exceptions import ApplicationValidationError
from app.application.services._base import Service, logged_operation, require, validated
from app.domain.football_team import FootballTeam
from app.domain.national_team import NationalTeam


class TeamService(Service):
    @logged_operation
    async def create_team(self, name: str, city: str, coach_id: int) -> FootballTeam:
        async with self._uow() as work:
            coach = require(await work.coaches.get_by_id(coach_id), "Coach", coach_id)
            team = await work.teams.add(validated(FootballTeam, name, city, coach))
            await work.commit()
            return team

    async def get_team(self, team_id: int) -> FootballTeam | None:
        async with self._uow() as work:
            return await work.teams.get_by_id(team_id)

    async def get_all_teams(self) -> list[FootballTeam]:
        async with self._uow() as work:
            return await work.teams.get_all()

    async def search_by_name(self, name: str) -> list[FootballTeam]:
        async with self._uow() as work:
            return await work.teams.get_by_name(name)

    async def search_by_city(self, city: str) -> list[FootballTeam]:
        async with self._uow() as work:
            return await work.teams.get_by_city(city)

    @logged_operation
    async def update_team(
        self, team_id: int, name: str | None = None, city: str | None = None,
        coach_id: int | None = None,
    ) -> FootballTeam:
        async with self._uow() as work:
            team = require(await work.teams.get_by_id(team_id, for_update=True), "Team", team_id)
            coach = team.coach if coach_id is None else require(
                await work.coaches.get_by_id(coach_id), "Coach", coach_id
            )
            details = validated(
                FootballTeam, team.name if name is None else name,
                team.city if city is None else city, coach,
            )
            team.name, team.city = details.name, details.city
            team.set_coach(coach)
            saved = await work.teams.update(team)
            await work.commit()
            return saved

    @logged_operation
    async def add_player(
        self, team_id: int, player_id: int, shirt_number: int | None = None,
    ) -> FootballTeam:
        async with self._uow() as work:
            team = require(await work.teams.get_by_id(team_id, for_update=True), "Team", team_id)
            if isinstance(team, NationalTeam):
                raise ApplicationValidationError("Use NationalTeamService.update_squad for a national roster.")
            player = require(await work.players.get_by_id(player_id), "Player", player_id)
            validated(team.add_player, player, shirt_number)
            saved = await work.teams.update(team)
            await work.commit()
            return saved

    @logged_operation
    async def remove_player(self, team_id: int, player_id: int) -> FootballTeam:
        async with self._uow() as work:
            team = require(await work.teams.get_by_id(team_id, for_update=True), "Team", team_id)
            if isinstance(team, NationalTeam):
                raise ApplicationValidationError("Use NationalTeamService.update_squad for a national roster.")
            player = require(team.find_player(player_id), "Squad player", player_id)
            team.remove_player(player)
            saved = await work.teams.update(team)
            await work.commit()
            return saved

    @logged_operation
    async def delete_team(self, team_id: int) -> None:
        async with self._uow() as work:
            require(True if await work.teams.delete(team_id) else None, "Team", team_id)
            await work.commit()
