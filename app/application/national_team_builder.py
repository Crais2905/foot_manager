from app.domain.coach import Coach
from app.domain.football_team import FootballTeam
from app.domain.national_team import NationalTeam
from app.domain.player import Player
from app.domain.squad_membership import SquadMembership
from app.domain.enums import PlayerPosition


class NationalTeamBuilder:
    def __init__(
        self,
        available_players: list[Player],
        player_teams: dict[Player, FootballTeam] | None = None,
    ) -> None:
        if not isinstance(available_players, list):
            raise TypeError("Список доступних гравців повинен бути list.")
        if any(not isinstance(player, Player) for player in available_players):
            raise TypeError("Список доступних гравців може містити лише Player.")
        if len(set(available_players)) != len(available_players):
            raise ValueError("Список доступних гравців не повинен містити повторів.")
        if player_teams is not None:
            if not isinstance(player_teams, dict):
                raise TypeError("Відображення гравців на клуби повинно бути словником.")
            for player, team in player_teams.items():
                if not isinstance(player, Player) or player not in available_players:
                    raise ValueError("Клуб можна вказати лише для доступного гравця.")
                if not isinstance(team, FootballTeam):
                    raise TypeError("Клуб повинен бути об'єктом FootballTeam.")

        self._available_players = available_players.copy()
        self._selected_players: list[Player] = []
        self._shirt_numbers: dict[Player, int] = {}
        self._check_clubs = player_teams is not None
        self._player_teams = player_teams.copy() if player_teams is not None else {}

    @property
    def player_teams(self) -> dict[Player, FootballTeam]:
        return self._player_teams.copy()

    @property
    def available_players(self) -> list[Player]:
        return self._available_players.copy()

    @property
    def selected_players(self) -> list[Player]:
        return self._selected_players.copy()

    def add_player(self, player: Player, shirt_number: int | None = None) -> None:
        if not isinstance(player, Player):
            raise TypeError("Можна вибирати лише об'єкти Player.")
        if player not in self.available_players:
            raise ValueError("Цього гравця немає серед доступних.")
        if player in self.selected_players:
            raise ValueError("Цей гравець уже вибраний.")
        membership = SquadMembership(
            player, player.shirt_number if shirt_number is None else shirt_number
        )
        self._shirt_numbers[player] = membership.shirt_number
        self._selected_players.append(player)

    def remove_player(self, player: Player) -> None:
        if not isinstance(player, Player):
            raise TypeError("Потрібно передати об'єкт Player.")
        if player not in self.selected_players:
            raise ValueError("Цього гравця немає серед вибраних.")
        self._selected_players.remove(player)
        del self._shirt_numbers[player]

    def get_selected_players(self) -> list[Player]:
        return self.selected_players.copy()

    def has_multiple_clubs(self) -> bool:
        clubs = {
            club.id if club.id is not None else club
            for player in self._selected_players
            if (club := self._player_teams.get(player)) is not None
            and not isinstance(club, NationalTeam)
        }
        return len(clubs) >= 2

    def validation_errors(self) -> list[str]:
        players = self._selected_players
        errors: list[str] = []
        if len(players) < NationalTeam.MIN_SQUAD_SIZE:
            errors.append(
                f"Вибрано {len(players)} гравців. Потрібно щонайменше {NationalTeam.MIN_SQUAD_SIZE}."
            )
        if not any(player.position is PlayerPosition.GOALKEEPER for player in players):
            errors.append("У складі має бути хоча б один воротар.")
        if len({self._shirt_numbers[player] for player in players}) != len(players):
            errors.append("Номери футболок у збірній мають бути унікальними.")
        if self._check_clubs and not self.has_multiple_clubs():
            errors.append("The squad must represent at least two clubs.")
        return errors

    def validate_squad(self) -> bool:
        return not self.validation_errors()

    def build(
        self,
        country: str,
        name: str,
        city: str,
        coach: Coach,
    ) -> NationalTeam:
        if not isinstance(coach, Coach):
            raise TypeError("Тренер повинен бути об'єктом Coach.")
        if not isinstance(country, str) or not country.strip():
            raise ValueError("Назва країни не може бути порожньою.")
        if not isinstance(name, str) or not name.strip():
            raise ValueError("Назва збірної не може бути порожньою.")
        if not isinstance(city, str) or not city.strip():
            raise ValueError("Місто не може бути порожнім.")
        errors = self.validation_errors()
        if errors:
            raise ValueError("\n".join(errors))

        national_team = NationalTeam(name, city, coach, country)
        for player in self.selected_players:
            national_team.add_player(player, self._shirt_numbers[player])
        return national_team

    def clear(self) -> None:
        self._selected_players.clear()
        self._shirt_numbers.clear()
