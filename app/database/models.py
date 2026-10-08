from datetime import UTC, datetime, time
from uuid import UUID, uuid4

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    SmallInteger,
    String,
    Text,
    Time,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.database.base import Base

JSONType = JSON().with_variant(JSONB, "postgresql")


class City(Base):
    __tablename__ = "cities"
    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid4
    )
    name: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    country: Mapped[str] = mapped_column(String(80), default="Colombia", nullable=False)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    timezone: Mapped[str] = mapped_column(
        String(64), default="America/Bogota", nullable=False
    )
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class User(Base):
    __tablename__ = "users"
    telegram_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    username: Mapped[str | None] = mapped_column(String(64))
    first_name: Mapped[str] = mapped_column(String(128), nullable=False)
    last_name: Mapped[str | None] = mapped_column(String(128))
    city: Mapped[str] = mapped_column(String(120), default="Bogotá", nullable=False)
    timezone: Mapped[str] = mapped_column(
        String(64), default="America/Bogota", nullable=False
    )
    preferred_style: Mapped[str] = mapped_column(
        String(40), default="CASUAL", nullable=False
    )
    daily_recommendation_enabled: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    daily_recommendation_time: Mapped[time] = mapped_column(
        Time, default=time(7, 0), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )


class ClothingItem(Base):
    __tablename__ = "clothing_items"
    __table_args__ = (
        CheckConstraint("formality between 1 and 5"),
        CheckConstraint("warmth between 1 and 5"),
        CheckConstraint("water_resistance between 0 and 5"),
        CheckConstraint("confidence between 0 and 1"),
    )
    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid4
    )
    user_telegram_id: Mapped[int] = mapped_column(
        ForeignKey("users.telegram_id", ondelete="CASCADE"), nullable=False, index=True
    )
    image_path: Mapped[str] = mapped_column(Text, nullable=False)
    name: Mapped[str | None] = mapped_column(String(100))
    category: Mapped[str] = mapped_column(String(32), nullable=False)
    subcategory: Mapped[str | None] = mapped_column(String(40))
    garment_type: Mapped[str] = mapped_column(String(80), nullable=False)
    color: Mapped[str] = mapped_column(String(60), nullable=False)
    secondary_color: Mapped[str | None] = mapped_column(String(60))
    pattern: Mapped[str | None] = mapped_column(String(40))
    material: Mapped[str | None] = mapped_column(String(60))
    style: Mapped[str] = mapped_column(String(60), nullable=False)
    fit: Mapped[str | None] = mapped_column(String(40))
    season: Mapped[str | None] = mapped_column(String(40))
    formality: Mapped[int] = mapped_column(SmallInteger, default=2, nullable=False)
    warmth: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    water_resistance: Mapped[int] = mapped_column(
        SmallInteger, default=0, nullable=False
    )
    description: Mapped[str | None] = mapped_column(Text)
    confidence: Mapped[float] = mapped_column(Float, default=0.7, nullable=False)
    is_favorite: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_available: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )


class WeatherSnapshot(Base):
    __tablename__ = "weather_snapshots"
    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid4
    )
    user_telegram_id: Mapped[int] = mapped_column(
        ForeignKey("users.telegram_id", ondelete="CASCADE"), nullable=False, index=True
    )
    temperature: Mapped[float] = mapped_column(Float, nullable=False)
    feels_like: Mapped[float] = mapped_column(Float, nullable=False)
    min_temperature: Mapped[float] = mapped_column(Float, nullable=False)
    max_temperature: Mapped[float] = mapped_column(Float, nullable=False)
    humidity: Mapped[int] = mapped_column(SmallInteger, default=0, nullable=False)
    rain_probability: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    precipitation: Mapped[float] = mapped_column(Float, nullable=False)
    wind_speed: Mapped[float] = mapped_column(Float, nullable=False)
    uv_index: Mapped[float] = mapped_column(Float, default=0, nullable=False)
    weather_code: Mapped[int] = mapped_column(Integer, nullable=False)
    captured_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )


class Outfit(Base):
    __tablename__ = "outfits"
    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid4
    )
    user_telegram_id: Mapped[int] = mapped_column(
        ForeignKey("users.telegram_id", ondelete="CASCADE"), nullable=False, index=True
    )
    score: Mapped[float] = mapped_column(Float, nullable=False)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    weather_snapshot: Mapped[dict] = mapped_column(JSONType, nullable=False)
    weather_snapshot_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("weather_snapshots.id")
    )
    item_ids: Mapped[list] = mapped_column(JSONType, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )


class OutfitItem(Base):
    __tablename__ = "outfit_items"
    outfit_id: Mapped[UUID] = mapped_column(
        ForeignKey("outfits.id", ondelete="CASCADE"), primary_key=True
    )
    clothing_item_id: Mapped[UUID] = mapped_column(
        ForeignKey("clothing_items.id", ondelete="CASCADE"), primary_key=True
    )


class OutfitHistory(Base):
    __tablename__ = "outfit_history"
    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid4
    )
    user_telegram_id: Mapped[int] = mapped_column(
        ForeignKey("users.telegram_id", ondelete="CASCADE"), nullable=False, index=True
    )
    outfit_id: Mapped[UUID] = mapped_column(
        ForeignKey("outfits.id", ondelete="CASCADE"), nullable=False
    )
    recommended_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    was_used: Mapped[bool | None] = mapped_column(Boolean)
    rating: Mapped[int | None] = mapped_column(SmallInteger)


class UserPreference(Base):
    __tablename__ = "user_preferences"
    user_telegram_id: Mapped[int] = mapped_column(
        ForeignKey("users.telegram_id", ondelete="CASCADE"), primary_key=True
    )
    style_weights: Mapped[dict] = mapped_column(JSONType, default=dict, nullable=False)
    category_weights: Mapped[dict] = mapped_column(
        JSONType, default=dict, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )


class Feedback(Base):
    __tablename__ = "feedback"
    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid4
    )
    user_telegram_id: Mapped[int] = mapped_column(
        ForeignKey("users.telegram_id", ondelete="CASCADE"), nullable=False, index=True
    )
    outfit_id: Mapped[UUID] = mapped_column(
        ForeignKey("outfits.id", ondelete="CASCADE"), nullable=False
    )
    rating: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
