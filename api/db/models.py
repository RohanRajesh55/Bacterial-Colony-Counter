"""SQLAlchemy ORM models for CFU-Counter API."""

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, Integer, String, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.db.base import Base


class User(Base):
    """Model for user authentication."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    predictions: Mapped[list["Prediction"]] = relationship(
        "Prediction", back_populates="user"
    )
    api_keys: Mapped[list["APIKey"]] = relationship(
        "APIKey", back_populates="user", cascade="all, delete-orphan"
    )

    __table_args__ = (Index("ix_users_email", "email"),)


class APIKey(Base):
    """Model for API key management."""

    __tablename__ = "api_keys"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    key_hash: Mapped[str] = mapped_column(
        String(64), unique=True, index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    prefix: Mapped[str] = mapped_column(String(20), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # Relationship to user
    user: Mapped["User"] = relationship("User", back_populates="api_keys")

    __table_args__ = (
        Index("ix_api_keys_user_id", "user_id"),
        Index("ix_api_keys_key_hash", "key_hash"),
    )


class Prediction(Base):
    """Model for storing prediction metadata."""

    __tablename__ = "predictions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    image_hash: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    colony_count: Mapped[int] = mapped_column(Integer, nullable=False)
    confidence_threshold: Mapped[float] = mapped_column(Float, nullable=False)
    model_used: Mapped[str] = mapped_column(String(50), nullable=False)
    original_image_key: Mapped[str] = mapped_column(String(255), nullable=False)
    annotated_image_key: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # Relationship to user
    user: Mapped["User"] = relationship("User", back_populates="predictions")

    # Relationship to feedback
    feedback: Mapped[list["Feedback"]] = relationship(
        "Feedback", back_populates="prediction", cascade="all, delete-orphan"
    )

    # Relationship to corrections
    corrections: Mapped[list["Correction"]] = relationship(
        "Correction", back_populates="prediction", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_predictions_image_hash", "image_hash"),
        Index("ix_predictions_user_id", "user_id"),
    )


class Feedback(Base):
    """Model for storing user feedback on predictions."""

    __tablename__ = "feedback"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    prediction_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("predictions.id", ondelete="CASCADE"), nullable=False
    )
    actual_count: Mapped[int] = mapped_column(Integer, nullable=False)
    comments: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # Relationship to prediction
    prediction: Mapped["Prediction"] = relationship(
        "Prediction", back_populates="feedback"
    )


class Correction(Base):
    """Model for storing user corrections on individual detections."""

    __tablename__ = "corrections"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    prediction_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("predictions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    action_type: Mapped[str] = mapped_column(
        String(20), nullable=False  # "add", "remove", "adjust", "split"
    )
    box: Mapped[dict | None] = mapped_column(
        JSON, nullable=True  # [x1, y1, x2, y2] for corrected box (null for "remove")
    )
    original_box: Mapped[dict | None] = mapped_column(
        JSON, nullable=True  # Original box before adjustment (null for "add")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default="(CURRENT_TIMESTAMP)",
    )

    # Relationship to prediction
    prediction: Mapped["Prediction"] = relationship(
        "Prediction", back_populates="corrections"
    )

    __table_args__ = (Index("ix_corrections_prediction_id", "prediction_id"),)
