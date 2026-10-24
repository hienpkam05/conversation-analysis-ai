import uuid

from sqlalchemy import ForeignKey, Index, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.models.mixins import TimestampMixin, UuidPrimaryKeyMixin


class EmbeddingRef(UuidPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "embedding_refs"
    __table_args__ = (
        Index(
            "uq_embedding_refs_object_model_type",
            "object_type",
            "object_id",
            "model_version_id",
            "embedding_type",
            unique=True,
        ),
    )

    object_type: Mapped[str] = mapped_column(String(50), nullable=False)
    object_id: Mapped["uuid.UUID"] = mapped_column(Uuid, nullable=False)
    embedding_type: Mapped[str] = mapped_column(String(50), nullable=False)
    model_version_id: Mapped["uuid.UUID"] = mapped_column(
        Uuid, ForeignKey("model_versions.id"), nullable=False
    )
    qdrant_collection: Mapped[str] = mapped_column(String(200), nullable=False)
    point_id: Mapped["uuid.UUID"] = mapped_column(Uuid, nullable=False, unique=True)
    profile_hash: Mapped[str] = mapped_column(String(64), nullable=False)

    model_version: Mapped["ModelVersion"] = relationship(back_populates="embedding_refs")
