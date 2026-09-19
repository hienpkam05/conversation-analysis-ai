import uuid
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.db.models import Candidate, Recruiter
from app.repositories.candidate_repository import CandidateRepository
from app.repositories.recruiter_repository import RecruiterRepository


class CandidateNotFoundError(Exception):
    pass


class CandidateRegionRequiredError(Exception):
    pass


@dataclass(frozen=True)
class HardFilterResult:
    candidate: Candidate
    recruiters: list[Recruiter]


class HardFilterService:
    def __init__(
        self,
        session: AsyncSession,
        *,
        settings: Settings | None = None,
        candidate_repository: CandidateRepository | None = None,
        recruiter_repository: RecruiterRepository | None = None,
    ):
        self.settings = settings or get_settings()
        self.candidates = candidate_repository or CandidateRepository(session)
        self.recruiters = recruiter_repository or RecruiterRepository(session)

    async def eligible_recruiters(self, candidate_id: uuid.UUID) -> HardFilterResult:
        candidate = await self.candidates.get_active_by_id(candidate_id)
        if candidate is None:
            raise CandidateNotFoundError
        if self.settings.strict_region and candidate.region is None:
            raise CandidateRegionRequiredError

        recruiters = list(
            await self.recruiters.find_eligible(
                candidate,
                strict_region=self.settings.strict_region,
                require_active_campaign=self.settings.require_active_campaign,
            )
        )
        return HardFilterResult(candidate=candidate, recruiters=recruiters)
