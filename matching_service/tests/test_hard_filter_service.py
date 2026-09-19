import uuid
from types import SimpleNamespace

import pytest

from app.core.config import Settings
from app.services.hard_filter_service import (
    CandidateNotFoundError,
    CandidateRegionRequiredError,
    HardFilterService,
)


class FakeCandidateRepository:
    def __init__(self, candidate):
        self.candidate = candidate

    async def get_active_by_id(self, candidate_id):
        return self.candidate


class FakeRecruiterRepository:
    def __init__(self, recruiters):
        self.recruiters = recruiters
        self.arguments = None

    async def find_eligible(self, candidate, *, strict_region, require_active_campaign):
        self.arguments = (candidate, strict_region, require_active_campaign)
        return self.recruiters


@pytest.mark.anyio
async def test_hard_filter_applies_configured_business_rules():
    candidate = SimpleNamespace(id=uuid.uuid4(), region="north")
    recruiter = SimpleNamespace(id=uuid.uuid4())
    recruiter_repository = FakeRecruiterRepository([recruiter])
    settings = Settings(strict_region=True, require_active_campaign=True)
    service = HardFilterService(
        None,
        settings=settings,
        candidate_repository=FakeCandidateRepository(candidate),
        recruiter_repository=recruiter_repository,
    )

    result = await service.eligible_recruiters(candidate.id)

    assert result.recruiters == [recruiter]
    assert recruiter_repository.arguments == (candidate, True, True)


@pytest.mark.anyio
async def test_hard_filter_rejects_missing_candidate():
    service = HardFilterService(
        None,
        candidate_repository=FakeCandidateRepository(None),
        recruiter_repository=FakeRecruiterRepository([]),
    )

    with pytest.raises(CandidateNotFoundError):
        await service.eligible_recruiters(uuid.uuid4())


@pytest.mark.anyio
async def test_hard_filter_requires_region_when_strict_region_is_enabled():
    candidate = SimpleNamespace(id=uuid.uuid4(), region=None)
    service = HardFilterService(
        None,
        settings=Settings(strict_region=True),
        candidate_repository=FakeCandidateRepository(candidate),
        recruiter_repository=FakeRecruiterRepository([]),
    )

    with pytest.raises(CandidateRegionRequiredError):
        await service.eligible_recruiters(candidate.id)
