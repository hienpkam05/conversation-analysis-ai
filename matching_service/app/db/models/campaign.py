import uuid

from sqlalchemy import BigInteger, Boolean, CheckConstraint, Enum, ForeignKey, Index, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import EntityStatus, Region, enum_values
from app.db.base import Base
from app.db.models.mixins import TimestampMixin, UuidPrimaryKeyMixin


class Campaign(UuidPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "campaigns"
    __table_args__ = (
        CheckConstraint(
            "salary_min IS NULL OR salary_max IS NULL OR salary_min <= salary_max",
            name="ck_campaigns_salary_range",
        ),
        Index("ix_campaigns_status", "status"),
    )

    job_title: Mapped[str] = mapped_column(String(200), nullable=False)
    location: Mapped[str | None] = mapped_column(String(150))
    region: Mapped[Region | None] = mapped_column(
        Enum(Region, name="region_enum", values_callable=enum_values)
    )
    salary_min: Mapped[int | None] = mapped_column(BigInteger)
    salary_max: Mapped[int | None] = mapped_column(BigInteger)
    requirements: Mapped[str | None] = mapped_column(Text)
    benefits: Mapped[str | None] = mapped_column(Text)
    status: Mapped[EntityStatus] = mapped_column(
        Enum(EntityStatus, name="entity_status_enum", values_callable=enum_values),
        nullable=False,
        default=EntityStatus.ACTIVE,
        server_default=EntityStatus.ACTIVE.value,
    )
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")

    recruiter_links: Mapped[list["RecruiterCampaign"]] = relationship(
        back_populates="campaign", cascade="all, delete-orphan"
    )


class RecruiterCampaign(Base):
    __tablename__ = "recruiter_campaigns"
    __table_args__ = (Index("ix_recruiter_campaigns_recruiter", "recruiter_id"),)

    recruiter_id: Mapped["uuid.UUID"] = mapped_column(
        Uuid, ForeignKey("recruiters.id", ondelete="CASCADE"), primary_key=True
    )
    campaign_id: Mapped["uuid.UUID"] = mapped_column(
        Uuid, ForeignKey("campaigns.id", ondelete="CASCADE"), primary_key=True
    )
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")

    recruiter: Mapped["Recruiter"] = relationship(back_populates="campaign_links")
    campaign: Mapped[Campaign] = relationship(back_populates="recruiter_links")
