from datetime import date
from typing import Optional, List

from sqlalchemy import Integer, String, ForeignKey, Date
from sqlalchemy.orm import declarative_base, Mapped, mapped_column, relationship

Base = declarative_base()


class PlayerModel(Base):
    __tablename__ = 'player'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    firstname: Mapped[str] = mapped_column(String(256), nullable=False)
    lastname: Mapped[str] = mapped_column(String(256), nullable=False)
    date_of_birth: Mapped[date] = mapped_column(Date)
    position: Mapped[str] = mapped_column(String(32), nullable=False)
    shirt_number: Mapped[int] = mapped_column(Integer, nullable=False)  # Додано Mapped[int]

    club_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey('football_team.id'))
    national_team_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey('nation_team.id'))

    club: Mapped[Optional["FootballTeamModel"]] = relationship("FootballTeamModel", back_populates="players")
    national_team: Mapped[Optional["NationalTeamModel"]] = relationship("NationalTeamModel", back_populates="players")


class CoachModel(Base):
    __tablename__ = 'coach'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    firstname: Mapped[str] = mapped_column(String(256), nullable=False)
    lastname: Mapped[str] = mapped_column(String(256), nullable=False)
    date_of_birth: Mapped[date] = mapped_column(Date)
    experience_years: Mapped[int] = mapped_column(Integer, nullable=False)

    club_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey('football_team.id'), unique=True)
    national_team_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey('nation_team.id'))

    club: Mapped[Optional["FootballTeamModel"]] = relationship("FootballTeamModel", back_populates="coach")
    national_team: Mapped[Optional["NationalTeamModel"]] = relationship("NationalTeamModel", back_populates="coach")


class BaseTeamModel(Base):
    __abstract__ = True

    id: Mapped[int] = mapped_column(Integer, primary_key=True)


class FootballTeamModel(BaseTeamModel):
    __tablename__ = 'football_team'

    name: Mapped[str] = mapped_column(String(256), nullable=False)
    city: Mapped[str] = mapped_column(String(256), nullable=False)

    coach: Mapped[Optional["CoachModel"]] = relationship("CoachModel", back_populates="club")
    players: Mapped[List["PlayerModel"]] = relationship("PlayerModel", back_populates="club", lazy="selectin")
    participations: Mapped[List["ChampionshipParticipationModel"]] = relationship(
        "ChampionshipParticipationModel", back_populates="football_team", lazy="selectin"
    )


class NationalTeamModel(BaseTeamModel):
    __tablename__ = 'nation_team'

    country: Mapped[str] = mapped_column(String(256), nullable=False)

    coach: Mapped[Optional["CoachModel"]] = relationship("CoachModel", back_populates="national_team")
    players: Mapped[List["PlayerModel"]] = relationship("PlayerModel", back_populates="national_team", lazy="selectin")
    participations: Mapped[List["ChampionshipParticipationModel"]] = relationship(
        "ChampionshipParticipationModel", back_populates="national_team", lazy="selectin"
    )


class ChampionshipModel(Base):
    __tablename__ = 'championship'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    country: Mapped[str] = mapped_column(String(256), nullable=False)
    season: Mapped[str] = mapped_column(String(32), nullable=False)

    participations: Mapped[List["ChampionshipParticipationModel"]] = relationship(
        "ChampionshipParticipationModel", back_populates="championship", lazy="selectin"
    )


class ChampionshipParticipationModel(Base):
    __tablename__ = 'championship_participation'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    championship_id: Mapped[int] = mapped_column(Integer, ForeignKey('championship.id'))
    championship: Mapped["ChampionshipModel"] = relationship(
        "ChampionshipModel", back_populates="participations"
    )

    football_team_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey('football_team.id'))
    football_team: Mapped[Optional["FootballTeamModel"]] = relationship(
        "FootballTeamModel", back_populates="participations"
    )

    national_team_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey('nation_team.id'))
    national_team: Mapped[Optional["NationalTeamModel"]] = relationship(
        "NationalTeamModel", back_populates="participations"
    )