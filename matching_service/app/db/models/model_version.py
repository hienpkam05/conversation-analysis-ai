from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.models.mixins import UuidPrimaryKeyMixin


class ModelVersion(UuidPrimaryKeyMixin, Base):
    __tablename__ = "model_versions"
    __table_args__ = (UniqueConstraint("model_name", "version", "task", name="uq_model_versions_name_version_task"),)

    model_name: Mapped[str] = mapped_column(String(200), nullable=False)
    version: Mapped[str] = mapped_column(String(100), nullable=False)
    task: Mapped[str] = mapped_column(String(100), nullable=False)
    dimension: Mapped[int] = mapped_column(Integer, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    performance_metrics: Mapped[dict | None] = mapped_column(JSONB)
    notes: Mapped[str | None] = mapped_column(Text)
    deployed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    embedding_refs: Mapped[list["EmbeddingRef"]] = relationship(back_populates="model_version")
    matching_runs: Mapped[list["MatchingRun"]] = relationship(back_populates="model_version")
