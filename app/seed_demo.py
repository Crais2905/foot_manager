"""Populate the configured database with a fictional demo league."""

import asyncio
from collections.abc import Callable
from datetime import date

from app.application.national_team_builder import NationalTeamBuilder
from app.db.session import close_database
from app.domain.championship import Championship
from app.domain.coach import Coach
from app.domain.enums import PlayerPosition
from app.domain.football_team import FootballTeam
from app.domain.player import Player
from app.infrastructure.unit_of_work import UnitOfWork

DEMO_NAME = "Демо-ліга України"
DEMO_COUNTRY = "Україна"
DEMO_SEASON = "2026/2027"
CLUBS = (
    ("Демо: Північ", "Київ", "Олег", "Гайдук"),
    ("Демо: Карпати", "Ужгород", "Марія", "Левицька"),
    ("Демо: Маяк", "Одеса", "Денис", "Вітренко"),
    ("Демо: Степ", "Дніпро", "Ірина", "Коваленко"),
)
FIRST_NAMES = (
    "Андрій", "Богдан", "Вадим", "Данило", "Євген", "Іван",
    "Максим", "Назар", "Олексій", "Павло", "Роман", "Тарас",
)
LAST_NAMES = (
    "Бондар", "Буряк", "Гончар", "Гриценко", "Кравець", "Литвин",
    "Мельник", "Олійник", "Паламар", "Савчук", "Ткач", "Шевчук",
)
POSITIONS = (
    (PlayerPosition.GOALKEEPER,) * 2
    + (PlayerPosition.DEFENDER,) * 4
    + (PlayerPosition.MIDFIELDER,) * 4
    + (PlayerPosition.FORWARD,) * 2
)


async def seed_demo(uow_factory: Callable[[], UnitOfWork] = UnitOfWork) -> bool:
    async with uow_factory() as work:
        championships = await work.championships.get_by_season(DEMO_SEASON)
        if any(c.name == DEMO_NAME and c.country == DEMO_COUNTRY for c in championships):
            return False

        championship = Championship(DEMO_NAME, DEMO_COUNTRY, DEMO_SEASON)
        player_clubs: dict[Player, FootballTeam] = {}
        squad: list[Player] = []
        for index, (name, city, first_name, last_name) in enumerate(CLUBS):
            coach = Coach(first_name, last_name, date(1978 + index, 4, 12), 9 + index)
            club = FootballTeam(name, city, coach)
            for number, position in enumerate(POSITIONS, start=1):
                player = Player(
                    FIRST_NAMES[(number - 1 + index) % len(FIRST_NAMES)],
                    LAST_NAMES[number - 1],
                    date(1998 + (number + index) % 8, index + 1, number + 1),
                    position, number,
                )
                club.add_player(player)

            club = await work.teams.add(club)
            player_clubs.update((player, club) for player in club)
            # One goalkeeper, four defenders, four midfielders and two forwards.
            numbers = ((1, 3, 7), (4, 8, 11), (5, 9, 12), (6, 10))[index]
            by_number = {member.shirt_number: member.player for member in club.squad.memberships}
            squad.extend(by_number[number] for number in numbers)
            championship.add_team(club, index + 1)

        builder = NationalTeamBuilder(list(player_clubs), player_clubs)
        for number, player in enumerate(squad, start=20):
            builder.add_player(player, number)
        national_coach = Coach("Сергій", "Остапенко", date(1976, 8, 21), 17)
        national = builder.build(DEMO_COUNTRY, "Демо: Збірна України", "Київ", national_coach)

        await work.championships.add(championship)
        await work.teams.add(national)
        await work.commit()
        return True


async def _run() -> None:
    try:
        created = await seed_demo()
        if created:
            print("Додано 5 тренерів, 48 гравців, 4 клуби, 1 чемпіонат і 1 збірну.")
        else:
            print("Демо-ліга вже існує. Нових записів не додано.")
    finally:
        await close_database()


if __name__ == "__main__":
    asyncio.run(_run())
