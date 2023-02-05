from typing import List, Optional
from sqlalchemy import ForeignKey, String, Float, Integer, DateTime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from datetime import datetime

class Base(DeclarativeBase):
    pass

class SnotelStation(Base):
    __tablename__ = "snotel_stations"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    lat: Mapped[float]
    long: Mapped[float]


class SnotelObservation(Base):
    __tablename__ = "snotel_observations"

    id: Mapped[int] = mapped_column(primary_key = True)
    station_id: Mapped[int] = mapped_column(ForeignKey("snotel_stations.id"))
    datetime: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    air_temp: Mapped[float]
    snow_depth: Mapped[float]
    snow_water_eq: Mapped[float]


class WxStation(Base):
    __tablename__ = "wx_stations"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    lat: Mapped[float]
    long: Mapped[float]


class WxObservation(Base):
    __tablename__ = "wx_observations"

    id: Mapped[int] = mapped_column(primary_key=True)
    station_id: Mapped[int] = mapped_column(ForeignKey("snotel_stations.id"))
    datetime: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    air_temp: Mapped[float]
    wind_gust: Mapped[float]
    wind_direction: Mapped[float]
    relative_humidity: Mapped[float]
    wind_speed: Mapped[float]
    solar_radiation: Mapped[float]
    