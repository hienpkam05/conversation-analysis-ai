"""Tạo schema nền tảng cho Candidate Recruiter Matching.

Revision ID: 20260919_0001
Revises:
Create Date: 2026-09-19
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20260919_0001"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


region_enum = postgresql.ENUM("north", "central", "south", name="region_enum", create_type=False)
entity_status_enum = postgresql.ENUM("active", "inactive", name="entity_status_enum", create_type=False)
candidate_status_enum = postgresql.ENUM("new", "contacted", "closed", name="candidate_status_enum", create_type=False)


def upgrade() -> None:
    bind = op.get_bind()
    region_enum.create(bind, checkfirst=True)
    entity_status_enum.create(bind, checkfirst=True)
    candidate_status_enum.create(bind, checkfirst=True)

    op.create_table(
        "candidates",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("full_name", sa.String(length=150), nullable=True),
        sa.Column("phone", sa.String(length=30), nullable=True),
        sa.Column("province", sa.String(length=100), nullable=True),
        sa.Column("region", region_enum, nullable=True),
        sa.Column("experience", sa.Text(), nullable=True),
        sa.Column("expected_salary", sa.BigInteger(), nullable=True),
        sa.Column("desired_job", sa.Text(), nullable=True),
        sa.Column("current_status", candidate_status_enum, server_default="new", nullable=False),
        sa.Column("is_deleted", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("phone"),
    )

    op.create_table(
        "recruiters",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("full_name", sa.String(length=150), nullable=False),
        sa.Column("specialty", sa.Text(), nullable=True),
        sa.Column("current_workload", sa.Integer(), server_default="0", nullable=False),
        sa.Column("max_workload", sa.Integer(), server_default="50", nullable=False),
        sa.Column("conversion_rate", sa.Numeric(precision=5, scale=4), nullable=True),
        sa.Column("status", entity_status_enum, server_default="active", nullable=False),
        sa.Column("is_deleted", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("current_workload >= 0", name="ck_recruiters_current_workload_nonnegative"),
        sa.CheckConstraint("max_workload > 0", name="ck_recruiters_max_workload_positive"),
        sa.CheckConstraint(
            "conversion_rate IS NULL OR conversion_rate BETWEEN 0 AND 1",
            name="ck_recruiters_conversion_rate_range",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_recruiters_status_active",
        "recruiters",
        ["status"],
        unique=False,
        postgresql_where=sa.text("is_deleted = false"),
    )

    op.create_table(
        "campaigns",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("job_title", sa.String(length=200), nullable=False),
        sa.Column("location", sa.String(length=150), nullable=True),
        sa.Column("region", region_enum, nullable=True),
        sa.Column("salary_min", sa.BigInteger(), nullable=True),
        sa.Column("salary_max", sa.BigInteger(), nullable=True),
        sa.Column("requirements", sa.Text(), nullable=True),
        sa.Column("benefits", sa.Text(), nullable=True),
        sa.Column("status", entity_status_enum, server_default="active", nullable=False),
        sa.Column("is_deleted", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "salary_min IS NULL OR salary_max IS NULL OR salary_min <= salary_max",
            name="ck_campaigns_salary_range",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_campaigns_status", "campaigns", ["status"], unique=False)

    op.create_table(
        "model_versions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("model_name", sa.String(length=200), nullable=False),
        sa.Column("version", sa.String(length=100), nullable=False),
        sa.Column("task", sa.String(length=100), nullable=False),
        sa.Column("dimension", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("performance_metrics", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("deployed_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("model_name", "version", "task", name="uq_model_versions_name_version_task"),
    )

    op.create_table(
        "recruiter_regions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("recruiter_id", sa.Uuid(), nullable=False),
        sa.Column("region", region_enum, nullable=False),
        sa.Column("province", sa.String(length=100), nullable=True),
        sa.ForeignKeyConstraint(["recruiter_id"], ["recruiters.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_recruiter_regions_region_recruiter", "recruiter_regions", ["region", "recruiter_id"], unique=False)
    op.create_index("uq_recruiter_regions_scope", "recruiter_regions", ["recruiter_id", "region", "province"], unique=True)

    op.create_table(
        "recruiter_campaigns",
        sa.Column("recruiter_id", sa.Uuid(), nullable=False),
        sa.Column("campaign_id", sa.Uuid(), nullable=False),
        sa.Column("active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.ForeignKeyConstraint(["campaign_id"], ["campaigns.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["recruiter_id"], ["recruiters.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("recruiter_id", "campaign_id"),
    )
    op.create_index("ix_recruiter_campaigns_recruiter", "recruiter_campaigns", ["recruiter_id"], unique=False)

    op.create_table(
        "embedding_refs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("object_type", sa.String(length=50), nullable=False),
        sa.Column("object_id", sa.Uuid(), nullable=False),
        sa.Column("embedding_type", sa.String(length=50), nullable=False),
        sa.Column("model_version_id", sa.Uuid(), nullable=False),
        sa.Column("qdrant_collection", sa.String(length=200), nullable=False),
        sa.Column("point_id", sa.Uuid(), nullable=False),
        sa.Column("profile_hash", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["model_version_id"], ["model_versions.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("point_id"),
    )
    op.create_index(
        "uq_embedding_refs_object_model_type",
        "embedding_refs",
        ["object_type", "object_id", "model_version_id", "embedding_type"],
        unique=True,
    )

    op.create_table(
        "matching_runs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("candidate_id", sa.Uuid(), nullable=False),
        sa.Column("model_version_id", sa.Uuid(), nullable=True),
        sa.Column("experiment_tag", sa.String(length=100), nullable=True),
        sa.Column("normalized_profile_hash", sa.String(length=64), nullable=True),
        sa.Column("weights_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("filter_snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["candidate_id"], ["candidates.id"]),
        sa.ForeignKeyConstraint(["model_version_id"], ["model_versions.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_matching_runs_candidate_created", "matching_runs", ["candidate_id", "created_at"], unique=False)

    op.create_table(
        "matching_results",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("run_id", sa.Uuid(), nullable=False),
        sa.Column("recruiter_id", sa.Uuid(), nullable=False),
        sa.Column("rank", sa.Integer(), nullable=False),
        sa.Column("semantic_score", sa.Numeric(precision=6, scale=5), nullable=False),
        sa.Column("campaign_fit_score", sa.Numeric(precision=6, scale=5), nullable=False),
        sa.Column("performance_score", sa.Numeric(precision=6, scale=5), nullable=False),
        sa.Column("workload_score", sa.Numeric(precision=6, scale=5), nullable=False),
        sa.Column("final_score", sa.Numeric(precision=6, scale=5), nullable=False),
        sa.Column("reasons_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("selected", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.CheckConstraint("rank > 0", name="ck_matching_results_rank_positive"),
        sa.CheckConstraint("semantic_score BETWEEN 0 AND 1", name="ck_matching_results_semantic_range"),
        sa.CheckConstraint("campaign_fit_score BETWEEN 0 AND 1", name="ck_matching_results_campaign_range"),
        sa.CheckConstraint("performance_score BETWEEN 0 AND 1", name="ck_matching_results_performance_range"),
        sa.CheckConstraint("workload_score BETWEEN 0 AND 1", name="ck_matching_results_workload_range"),
        sa.CheckConstraint("final_score BETWEEN 0 AND 1", name="ck_matching_results_final_range"),
        sa.ForeignKeyConstraint(["recruiter_id"], ["recruiters.id"]),
        sa.ForeignKeyConstraint(["run_id"], ["matching_runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("uq_matching_results_run_recruiter", "matching_results", ["run_id", "recruiter_id"], unique=True)
    op.create_index("uq_matching_results_run_rank", "matching_results", ["run_id", "rank"], unique=True)


def downgrade() -> None:
    op.drop_index("uq_matching_results_run_rank", table_name="matching_results")
    op.drop_index("uq_matching_results_run_recruiter", table_name="matching_results")
    op.drop_table("matching_results")
    op.drop_index("ix_matching_runs_candidate_created", table_name="matching_runs")
    op.drop_table("matching_runs")
    op.drop_index("uq_embedding_refs_object_model_type", table_name="embedding_refs")
    op.drop_table("embedding_refs")
    op.drop_index("ix_recruiter_campaigns_recruiter", table_name="recruiter_campaigns")
    op.drop_table("recruiter_campaigns")
    op.drop_index("uq_recruiter_regions_scope", table_name="recruiter_regions")
    op.drop_index("ix_recruiter_regions_region_recruiter", table_name="recruiter_regions")
    op.drop_table("recruiter_regions")
    op.drop_table("model_versions")
    op.drop_index("ix_campaigns_status", table_name="campaigns")
    op.drop_table("campaigns")
    op.drop_index("ix_recruiters_status_active", table_name="recruiters")
    op.drop_table("recruiters")
    op.drop_table("candidates")

    bind = op.get_bind()
    candidate_status_enum.drop(bind, checkfirst=True)
    entity_status_enum.drop(bind, checkfirst=True)
    region_enum.drop(bind, checkfirst=True)
