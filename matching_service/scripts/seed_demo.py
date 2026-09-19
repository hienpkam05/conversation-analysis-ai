import asyncio
import uuid
from decimal import Decimal

from sqlalchemy import select

from app.core.enums import EntityStatus, Region
from app.db.models import Campaign, Candidate, ModelVersion, Recruiter, RecruiterCampaign, RecruiterRegion
from app.db.session import AsyncSessionLocal, dispose_database_engine


def demo_id(name: str) -> uuid.UUID:
    return uuid.uuid5(uuid.NAMESPACE_URL, f"candidate-recruiter-matching/{name}")


RECRUITERS = [
    {
        "id": demo_id("recruiter-r1"),
        "full_name": "Nguyễn Minh An",
        "specialty": "Tuyển công nhân điện tử, lắp ráp và kiểm tra linh kiện.",
        "current_workload": 10,
        "max_workload": 50,
        "conversion_rate": Decimal("0.7200"),
        "region": Region.NORTH,
        "province": "Bắc Ninh",
    },
    {
        "id": demo_id("recruiter-r2"),
        "full_name": "Trần Thu Hà",
        "specialty": "Tuyển lao động may mặc và đóng gói.",
        "current_workload": 15,
        "max_workload": 40,
        "conversion_rate": Decimal("0.6100"),
        "region": Region.NORTH,
        "province": "Bắc Giang",
    },
    {
        "id": demo_id("recruiter-r3"),
        "full_name": "Lê Quốc Việt",
        "specialty": "Tuyển công nhân điện tử và vận hành dây chuyền.",
        "current_workload": 39,
        "max_workload": 40,
        "conversion_rate": Decimal("0.8000"),
        "region": Region.NORTH,
        "province": "Bắc Ninh",
    },
    {
        "id": demo_id("recruiter-r4"),
        "full_name": "Phạm Gia Linh",
        "specialty": "Tuyển công nhân điện tử tại khu vực miền Nam.",
        "current_workload": 5,
        "max_workload": 50,
        "conversion_rate": Decimal("0.9000"),
        "region": Region.SOUTH,
        "province": "TP. Hồ Chí Minh",
    },
    {
        "id": demo_id("recruiter-r5"),
        "full_name": "Đỗ Mai Phương",
        "specialty": "Tuyển lao động sản xuất phổ thông.",
        "current_workload": 50,
        "max_workload": 50,
        "conversion_rate": Decimal("0.8500"),
        "region": Region.NORTH,
        "province": "Hà Nội",
    },
]

CAMPAIGNS = [
    {
        "id": demo_id("campaign-c1"),
        "job_title": "Công nhân điện tử",
        "location": "Bắc Ninh",
        "region": Region.NORTH,
        "salary_min": 8_000_000,
        "salary_max": 12_000_000,
        "requirements": "Lắp ráp linh kiện, làm ca, sức khỏe tốt.",
        "benefits": "Hỗ trợ nhà ở và tăng ca theo quy định.",
    },
    {
        "id": demo_id("campaign-c2"),
        "job_title": "Công nhân may mặc",
        "location": "Bắc Giang",
        "region": Region.NORTH,
        "salary_min": 7_500_000,
        "salary_max": 11_000_000,
        "requirements": "Có thể học nghề may công nghiệp.",
        "benefits": "Đào tạo đầu vào và thưởng chuyên cần.",
    },
    {
        "id": demo_id("campaign-c3"),
        "job_title": "Công nhân vận hành dây chuyền điện tử",
        "location": "Hà Nội",
        "region": Region.NORTH,
        "salary_min": 9_000_000,
        "salary_max": 13_000_000,
        "requirements": "Tuân thủ quy trình sản xuất và làm ca.",
        "benefits": "Có xe đưa đón theo tuyến.",
    },
    {
        "id": demo_id("campaign-c4"),
        "job_title": "Công nhân điện tử",
        "location": "TP. Hồ Chí Minh",
        "region": Region.SOUTH,
        "salary_min": 8_500_000,
        "salary_max": 13_500_000,
        "requirements": "Lắp ráp và kiểm tra sản phẩm điện tử.",
        "benefits": "Phụ cấp ca và bảo hiểm đầy đủ.",
    },
    {
        "id": demo_id("campaign-c5"),
        "job_title": "Công nhân sản xuất phổ thông",
        "location": "Hà Nội",
        "region": Region.NORTH,
        "salary_min": 7_000_000,
        "salary_max": 10_000_000,
        "requirements": "Có thể làm theo ca sản xuất.",
        "benefits": "Hỗ trợ bữa ăn ca.",
    },
]

CANDIDATES = [
    {
        "id": demo_id("candidate-test-01"),
        "full_name": "Ứng viên thử nghiệm Bắc Ninh",
        "phone": "0900000001",
        "province": "Bắc Ninh",
        "region": Region.NORTH,
        "experience": "1 năm lắp ráp linh kiện điện tử.",
        "expected_salary": 9_000_000,
        "desired_job": "Công nhân điện tử",
    },
    {
        "id": demo_id("candidate-test-02"),
        "full_name": "Ứng viên thử nghiệm Bắc Giang",
        "phone": "0900000002",
        "province": "Bắc Giang",
        "region": Region.NORTH,
        "experience": "Chưa có kinh nghiệm, có thể học may công nghiệp.",
        "expected_salary": 8_000_000,
        "desired_job": "Công nhân may mặc",
    },
    {
        "id": demo_id("candidate-test-03"),
        "full_name": "Ứng viên thử nghiệm TP HCM",
        "phone": "0900000003",
        "province": "TP. Hồ Chí Minh",
        "region": Region.SOUTH,
        "experience": "6 tháng kiểm tra sản phẩm điện tử.",
        "expected_salary": 10_000_000,
        "desired_job": "Công nhân điện tử",
    },
]


async def add_if_missing(session, model, values: dict) -> None:
    if await session.get(model, values["id"]) is None:
        session.add(model(**values))


async def add_or_update_model_version(session, values: dict) -> None:
    model_version = await session.get(ModelVersion, values["id"])
    if model_version is None:
        session.add(ModelVersion(**values))
        return
    for field, value in values.items():
        if field != "id":
            setattr(model_version, field, value)


async def seed() -> None:
    async with AsyncSessionLocal() as session:
        async with session.begin():
            for recruiter in RECRUITERS:
                await add_if_missing(
                    session,
                    Recruiter,
                    {
                        "id": recruiter["id"],
                        "full_name": recruiter["full_name"],
                        "specialty": recruiter["specialty"],
                        "current_workload": recruiter["current_workload"],
                        "max_workload": recruiter["max_workload"],
                        "conversion_rate": recruiter["conversion_rate"],
                        "status": EntityStatus.ACTIVE,
                    },
                )
                region_exists = await session.scalar(
                    select(RecruiterRegion.id).where(
                        RecruiterRegion.recruiter_id == recruiter["id"],
                        RecruiterRegion.region == recruiter["region"],
                        RecruiterRegion.province == recruiter["province"],
                    )
                )
                if region_exists is None:
                    session.add(
                        RecruiterRegion(
                            recruiter_id=recruiter["id"],
                            region=recruiter["region"],
                            province=recruiter["province"],
                        )
                    )

            for campaign in CAMPAIGNS:
                await add_if_missing(session, Campaign, {**campaign, "status": EntityStatus.ACTIVE})

            for candidate in CANDIDATES:
                await add_if_missing(session, Candidate, candidate)

            await add_or_update_model_version(
                session,
                {
                    "id": demo_id("model-sentence-transformer-v1"),
                    "model_name": "vinai/phobert-base-v2",
                    "version": "meanpool-v1",
                    "task": "recruiter_matching_embedding",
                    "dimension": 768,
                    "is_active": True,
                    "performance_metrics": {"source": "seed_only"},
                },
            )

            assignments = [("recruiter-r1", "campaign-c1"), ("recruiter-r2", "campaign-c2"), ("recruiter-r3", "campaign-c1"), ("recruiter-r3", "campaign-c3"), ("recruiter-r4", "campaign-c4"), ("recruiter-r5", "campaign-c5")]
            for recruiter_name, campaign_name in assignments:
                recruiter_id = demo_id(recruiter_name)
                campaign_id = demo_id(campaign_name)
                exists = await session.scalar(
                    select(RecruiterCampaign.recruiter_id).where(
                        RecruiterCampaign.recruiter_id == recruiter_id,
                        RecruiterCampaign.campaign_id == campaign_id,
                    )
                )
                if exists is None:
                    session.add(RecruiterCampaign(recruiter_id=recruiter_id, campaign_id=campaign_id, active=True))

    print("Seed hoàn tất: 5 recruiter, 5 campaign, 3 candidate, 1 model version.")


async def main() -> None:
    try:
        await seed()
    finally:
        await dispose_database_engine()


if __name__ == "__main__":
    asyncio.run(main())
