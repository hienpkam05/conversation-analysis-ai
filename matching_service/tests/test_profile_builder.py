import uuid
from types import SimpleNamespace

from app.core.enums import EntityStatus, Region
from app.services.profile_builder import (
    build_candidate_profile,
    build_recruiter_profile,
    normalize_profile_text,
)


def test_candidate_profile_is_deterministic_and_excludes_pii():
    candidate = SimpleNamespace(
        full_name="Nguyen Van A",
        phone="0900000000",
        province=" Bắc Ninh ",
        region=Region.NORTH,
        desired_job=" Công nhân điện tử ",
        experience="1 năm lắp ráp linh kiện.",
        expected_salary=9_000_000,
    )
    model_version_id = uuid.uuid4()

    first = build_candidate_profile(candidate, model_version_id)
    second = build_candidate_profile(candidate, model_version_id)

    assert first == second
    assert "Nguyen Van A" not in first.text
    assert "0900000000" not in first.text
    assert "Công nhân điện tử" in first.text


def test_recruiter_profile_sorts_regions_and_campaigns_and_excludes_name():
    active_campaign = SimpleNamespace(
        job_title="Công nhân điện tử",
        status=EntityStatus.ACTIVE,
        is_deleted=False,
    )
    recruiter = SimpleNamespace(
        full_name="Le Thi B",
        specialty="Lắp ráp linh kiện",
        regions=[
            SimpleNamespace(region=Region.NORTH, province="Bắc Ninh"),
            SimpleNamespace(region=Region.NORTH, province=None),
        ],
        campaign_links=[SimpleNamespace(active=True, campaign=active_campaign)],
    )

    profile = build_recruiter_profile(recruiter, uuid.uuid4())

    assert "Le Thi B" not in profile.text
    assert "north:Bắc Ninh, north:toàn vùng" in profile.text
    assert "Công nhân điện tử" in profile.text


def test_normalize_profile_text_collapses_whitespace():
    assert normalize_profile_text("  Công   nhân\n điện tử ") == "Công nhân điện tử"
