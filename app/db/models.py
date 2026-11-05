from __future__ import annotations

from datetime import date
from typing import Any

from sqlalchemy import CheckConstraint, Date, Enum, ForeignKey, String, UniqueConstraint
from sqlalchemy.ext.associationproxy import AssociationProxy, association_proxy
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.enums import PlayerPositionEnum


class PersonModel(Base):
    __tablename__ = "persons"

    id: Mapped[int] = mapped_column(primary_key=True)
    first_name: Mapped[str] = mapped_column(String(100))
    last_name: Mapped[str] = mapped_column(String(100))
    date_of_birth: Mapped[date] = mapped_column(Date)
    person_type: Mapped[str] = mapped_column(String(20))

    __mapper_args__ = {"polymorphic_on": person_type, "polymorphic_identity": "person",
                       "with_polymorphic": "*"}


class PlayerModel(PersonModel):
    __tablename__ = "players"
    __table_args__ = (CheckConstraint("shirt_number BETWEEN 1 AND 99", name="shirt_number"),)

    id: Mapped[int] = mapped_column(ForeignKey("persons.id", ondelete="CASCADE"), primary_key=True)
    position: Mapped[PlayerPositionEnum] = mapped_column(Enum(
        PlayerPositionEnum, name="player_position", validate_strings=True,
        values_callable=lambda enum: [item.value for item in enum],
        create_constraint=False,
    ))
    # Default number for a player without a squad. Actual squad numbers are in squad_players.
    shirt_number: Mapped[int]
    squad_memberships: Mapped[list[SquadPlayerModel]] = relationship(
        back_populates="player", cascade="all, delete-orphan", passive_deletes=True,
        lazy="selectin",
    )
    squads: AssociationProxy[list[TeamSquadModel]] = association_proxy("squad_memberships", "squad")

    __mapper_args__ = {"polymorphic_identity": "player"}


class CoachModel(PersonModel):
    __tablename__ = "coaches"
    __table_args__ = (CheckConstraint("experience_years >= 0", name="experience_years"),)

    id: Mapped[int] = mapped_column(ForeignKey("persons.id", ondelete="CASCADE"), primary_key=True)
    experience_years: Mapped[int]
    teams: Mapped[list[FootballTeamModel]] = relationship(
        back_populates="coach", passive_deletes="all", lazy="selectin",
    )

    __mapper_args__ = {"polymorphic_identity": "coach"}


class FootballTeamModel(Base):
    __tablename__ = "football_teams"
    __table_args__: tuple[CheckConstraint, ...] = (
        CheckConstraint("length(trim(name)) > 0", name="name_nonempty"),
        CheckConstraint("length(trim(city)) > 0", name="city_nonempty"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(150))
    city: Mapped[str] = mapped_column(String(100))
    coach_id: Mapped[int] = mapped_column(ForeignKey("coaches.id", ondelete="RESTRICT"), index=True)
    team_type: Mapped[str] = mapped_column(String(30))
    coach: Mapped[CoachModel] = relationship(back_populates="teams", lazy="selectin")
    squad: Mapped[TeamSquadModel] = relationship(
        back_populates="team", cascade="all, delete-orphan", single_parent=True,
        passive_deletes=True, lazy="selectin",
    )
    participations: Mapped[list[ChampionshipParticipationModel]] = relationship(
        back_populates="team", cascade="all, delete-orphan", passive_deletes=True,
        lazy="selectin",
    )

    __mapper_args__ = {"polymorphic_on": team_type, "polymorphic_identity": "football_team",
                       "with_polymorphic": "*"}

    def __init__(self, **kwargs: Any) -> None:
        # Composition: even an empty team starts with its own squad.
        kwargs.setdefault("squad", TeamSquadModel())
        super().__init__(**kwargs)


class NationalTeamModel(FootballTeamModel):
    __tablename__ = "national_teams"
    __table_args__ = (CheckConstraint("length(trim(country)) > 0", name="country_nonempty"),)

    id: Mapped[int] = mapped_column(ForeignKey("football_teams.id", ondelete="CASCADE"), primary_key=True)
    country: Mapped[str] = mapped_column(String(100))

    __mapper_args__ = {"polymorphic_identity": "national_team"}


class TeamSquadModel(Base):
    __tablename__ = "team_squads"

    id: Mapped[int] = mapped_column(primary_key=True)
    team_id: Mapped[int] = mapped_column(
        ForeignKey("football_teams.id", ondelete="CASCADE"), unique=True,
    )
    team: Mapped[FootballTeamModel] = relationship(back_populates="squad")
    memberships: Mapped[list[SquadPlayerModel]] = relationship(
        back_populates="squad", cascade="all, delete-orphan", passive_deletes=True,
        lazy="selectin",
    )
    players: AssociationProxy[list[PlayerModel]] = association_proxy(
        "memberships", "player",
        creator=lambda player: SquadPlayerModel(player=player, shirt_number=player.shirt_number),
    )


class SquadPlayerModel(Base):
    __tablename__ = "squad_players"
    __table_args__ = (
        UniqueConstraint("squad_id", "shirt_number"),
        CheckConstraint("shirt_number BETWEEN 1 AND 99", name="shirt_number"),
    )

    squad_id: Mapped[int] = mapped_column(ForeignKey("team_squads.id", ondelete="CASCADE"), primary_key=True)
    player_id: Mapped[int] = mapped_column(ForeignKey("players.id", ondelete="CASCADE"), primary_key=True, index=True)
    shirt_number: Mapped[int]
    squad: Mapped[TeamSquadModel] = relationship(back_populates="memberships")
    player: Mapped[PlayerModel] = relationship(back_populates="squad_memberships", lazy="selectin")


class ChampionshipModel(Base):
    __tablename__ = "championships"
    __table_args__ = (UniqueConstraint("name", "country", "season"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(150))
    country: Mapped[str] = mapped_column(String(100))
    season: Mapped[str] = mapped_column(String(20))
    participations: Mapped[list[ChampionshipParticipationModel]] = relationship(
        back_populates="championship", cascade="all, delete-orphan", passive_deletes=True,
        lazy="selectin",
    )


class ChampionshipParticipationModel(Base):
    __tablename__ = "championship_participations"
    __table_args__ = (
        UniqueConstraint("team_id", "championship_id"),
        UniqueConstraint("championship_id", "position"),
        CheckConstraint("position > 0", name="position_positive"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    team_id: Mapped[int] = mapped_column(ForeignKey("football_teams.id", ondelete="CASCADE"), index=True)
    championship_id: Mapped[int] = mapped_column(ForeignKey("championships.id", ondelete="CASCADE"))
    position: Mapped[int]
    team: Mapped[FootballTeamModel] = relationship(back_populates="participations")
    championship: Mapped[ChampionshipModel] = relationship(back_populates="participations")
