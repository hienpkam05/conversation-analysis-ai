import uuid
from decimal import Decimal

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Index, Integer, Numeric, String, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.models.mixins import TimestampMixin, UuidPrimaryKeyMixin


class MatchingRun(UuidPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "matching_runs"
    __table_args__ = (Index("ix_matching_runs_candidate_created", "candidate_id", "created_at"),)

    candidate_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("candidates.id"), nullable=False)
    model_version_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("model_versions.id"))
    experiment_tag: Mapped[str | None] = mapped_column(String(100))
    normalized_profile_hash: Mapped[str | None] = mapped_column(String(64))
    weights_json: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    filter_snapshot: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    candidate: Mapped["Candidate"] = relationship(back_populates="matching_runs")
    model_version: Mapped["ModelVersion | None"] = relationship(back_populates="matching_runs")
    results: Mapped[list["MatchingResult"]] = relationship(
        back_populates="run", cascade="all, delete-orphan"
    )


class MatchingResult(UuidPrimaryKeyMixin, Base):
    __tablename__ = "matching_results"
    __table_args__ = (
        CheckConstraint("rank > 0", name="ck_matching_results_rank_positive"),
        CheckConstraint("semantic_score BETWEEN 0 AND 1", name="ck_matching_results_semantic_range"),
        CheckConstraint("campaign_fit_score BETWEEN 0 AND 1", name="ck_matching_results_campaign_range"),
        CheckConstraint("performance_score BETWEEN 0 AND 1", name="ck_matching_results_performance_range"),
        CheckConstraint("workload_score BETWEEN 0 AND 1", name="ck_matching_results_workload_range"),
        CheckConstraint("final_score BETWEEN 0 AND 1", name="ck_matching_results_final_range"),
        Index("uq_matching_results_run_recruiter", "run_id", "recruiter_id", unique=True),
        Index("uq_matching_results_run_rank", "run_id", "rank", unique=True),
    )

    run_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("matching_runs.id", ondelete="CASCADE"), nullable=False
    )
    recruiter_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("recruiters.id"), nullable=False)
    rank: Mapped[int] = mapped_column(Integer, nullable=False)
    semantic_score: Mapped[Decimal] = mapped_column(Numeric(6, 5), nullable=False)
    campaign_fit_score: Mapped[Decimal] = mapped_column(Numeric(6, 5), nullable=False)
    performance_score: Mapped[Decimal] = mapped_column(Numeric(6, 5), nullable=False)
    workload_score: Mapped[Decimal] = mapped_column(Numeric(6, 5), nullable=False)
    final_score: Mapped[Decimal] = mapped_column(Numeric(6, 5), nullable=False)
    reasons_json: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    selected: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")

    run: Mapped[MatchingRun] = relationship(back_populates="results")
    recruiter: Mapped["Recruiter"] = relationship(back_populates="matching_results")
