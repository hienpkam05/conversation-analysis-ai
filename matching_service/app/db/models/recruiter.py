import uuid
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    Uuid,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import EntityStatus, Region, enum_values
from app.db.base import Base
from app.db.models.mixins import TimestampMixin, UuidPrimaryKeyMixin


class Recruiter(UuidPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "recruiters"
    __table_args__ = (
        CheckConstraint("current_workload >= 0", name="ck_recruiters_current_workload_nonnegative"),
        CheckConstraint("max_workload > 0", name="ck_recruiters_max_workload_positive"),
        CheckConstraint("conversion_rate IS NULL OR conversion_rate BETWEEN 0 AND 1", name="ck_recruiters_conversion_rate_range"),
        Index("ix_recruiters_status_active", "status", postgresql_where=text("is_deleted = false")),
    )

    full_name: Mapped[str] = mapped_column(String(150), nullable=False)
    specialty: Mapped[str | None] = mapped_column(Text)
    current_workload: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    max_workload: Mapped[int] = mapped_column(Integer, nullable=False, default=50, server_default="50")
    conversion_rate: Mapped[Decimal | None] = mapped_column(Numeric(5, 4))
    status: Mapped[EntityStatus] = mapped_column(
        Enum(EntityStatus, name="entity_status_enum", values_callable=enum_values),
        nullable=False,
        default=EntityStatus.ACTIVE,
        server_default=EntityStatus.ACTIVE.value,
    )
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")

    regions: Mapped[list["RecruiterRegion"]] = relationship(back_populates="recruiter", cascade="all, delete-orphan")
    campaign_links: Mapped[list["RecruiterCampaign"]] = relationship(back_populates="recruiter", cascade="all, delete-orphan")
    matching_results: Mapped[list["MatchingResult"]] = relationship(back_populates="recruiter")


class RecruiterRegion(UuidPrimaryKeyMixin, Base):
    __tablename__ = "recruiter_regions"
    __table_args__ = (
        Index("ix_recruiter_regions_region_recruiter", "region", "recruiter_id"),
        Index("uq_recruiter_regions_scope", "recruiter_id", "region", "province", unique=True),
    )

    recruiter_id: Mapped["uuid.UUID"] = mapped_column(
        Uuid, ForeignKey("recruiters.id", ondelete="CASCADE"), nullable=False
    )
    region: Mapped[Region] = mapped_column(
        Enum(Region, name="region_enum", values_callable=enum_values), nullable=False
    )
    province: Mapped[str | None] = mapped_column(String(100))

    recruiter: Mapped[Recruiter] = relationship(back_populates="regions")
