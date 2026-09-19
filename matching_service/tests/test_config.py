import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_settings_accept_matching_weights_that_total_one():
    settings = Settings(
        weight_semantic=0.5,
        weight_campaign=0.2,
        weight_performance=0.1,
        weight_workload=0.2,
    )

    assert settings.matching_top_k == 3


def test_settings_reject_matching_weights_that_do_not_total_one():
    with pytest.raises(ValidationError, match="Tổng các trọng số"):
        Settings(
            weight_semantic=0.5,
            weight_campaign=0.3,
            weight_performance=0.1,
            weight_workload=0.3,
        )


def test_settings_reject_retrieval_smaller_than_top_k():
    with pytest.raises(ValidationError, match="RETRIEVAL_TOP_N"):
        Settings(matching_top_k=3, retrieval_top_n=2)
