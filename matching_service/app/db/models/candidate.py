from sqlalchemy import BigInteger, Boolean, Enum, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import CandidateStatus, Region, enum_values
from app.db.base import Base
from app.db.models.mixins import TimestampMixin, UuidPrimaryKeyMixin


class Candidate(UuidPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "candidates"

    full_name: Mapped[str | None] = mapped_column(String(150))
    phone: Mapped[str | None] = mapped_column(String(30), unique=True)
    province: Mapped[str | None] = mapped_column(String(100))
    region: Mapped[Region | None] = mapped_column(
        Enum(Region, name="region_enum", values_callable=enum_values)
    )
    experience: Mapped[str | None] = mapped_column(Text)
    expected_salary: Mapped[int | None] = mapped_column(BigInteger)
    desired_job: Mapped[str | None] = mapped_column(Text)
    current_status: Mapped[CandidateStatus] = mapped_column(
        Enum(CandidateStatus, name="candidate_status_enum", values_callable=enum_values),
        nullable=False,
        default=CandidateStatus.NEW,
        server_default=CandidateStatus.NEW.value,
    )
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")

    matching_runs: Mapped[list["MatchingRun"]] = relationship(back_populates="candidate")
