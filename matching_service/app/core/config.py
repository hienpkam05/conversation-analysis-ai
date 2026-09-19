from functools import lru_cache

from typing import Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "candidate-recruiter-matching"
    app_env: str = "development"
    api_v1_prefix: str = "/api/v1"
    log_level: str = "INFO"

    database_url: str = "postgresql+asyncpg://recruitment_user:recruitment_dev_password@localhost:5432/recruitment_ai"
    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: str | None = None

    embedding_provider: Literal["phobert", "sentence_transformer"] = "phobert"
    embedding_model: str = "vinai/phobert-base-v2"
    embedding_model_version: str = "meanpool-v1"
    embedding_device: str = "cpu"
    embedding_max_length: int = Field(default=256, ge=8, le=512)
    embedding_batch_size: int = Field(default=16, ge=1, le=256)

    matching_top_k: int = Field(default=3, ge=1)
    retrieval_top_n: int = Field(default=10, ge=1)
    strict_region: bool = True
    require_active_campaign: bool = True
    default_cold_start_performance: float = Field(default=0.5, ge=0, le=1)
    weight_semantic: float = Field(default=0.55, ge=0, le=1)
    weight_campaign: float = Field(default=0.20, ge=0, le=1)
    weight_performance: float = Field(default=0.15, ge=0, le=1)
    weight_workload: float = Field(default=0.10, ge=0, le=1)

    @model_validator(mode="after")
    def validate_score_weights(self) -> "Settings":
        total = (
            self.weight_semantic
            + self.weight_campaign
            + self.weight_performance
            + self.weight_workload
        )
        if abs(total - 1.0) > 0.0001:
            raise ValueError("Tổng các trọng số matching phải bằng 1.0.")
        if self.retrieval_top_n < self.matching_top_k:
            raise ValueError("RETRIEVAL_TOP_N phải lớn hơn hoặc bằng MATCHING_TOP_K.")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
