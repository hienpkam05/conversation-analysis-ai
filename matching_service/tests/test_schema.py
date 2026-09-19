from app.db.base import Base
import app.db.models  # noqa: F401


def test_matching_schema_registers_all_required_tables():
    assert {
        "candidates",
        "recruiters",
        "recruiter_regions",
        "campaigns",
        "recruiter_campaigns",
        "model_versions",
        "embedding_refs",
        "matching_runs",
        "matching_results",
    } <= set(Base.metadata.tables)
