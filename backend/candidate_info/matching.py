import math
from urllib.parse import urlsplit
import uuid

from django.conf import settings
import requests

from consultation_quality.services import InputError
from consultation_quality.training_data import redact


class MatchingUnavailable(InputError):
    def __init__(self, message="Không kết nối được dịch vụ tìm chiến dịch. Kiểm tra Matching Service và thử lại."):
        super().__init__(message, "CAMPAIGN_SERVICE_UNAVAILABLE")


def make_query(profile, top_k, strict_salary):
    if type(top_k) is not int or not 1 <= top_k <= 10 or type(strict_salary) is not bool:
        raise InputError("Số chiến dịch từ 1 đến 10 và tùy chọn lương phải hợp lệ.")
    values = {field["code"]: field["value"] for field in profile.fields}
    if not values["desired_job"]:
        raise InputError("Cần công việc mong muốn đã đối chiếu trước khi tìm chiến dịch.")
    if strict_salary and values["expected_salary"] is None:
        raise InputError("Cần mức lương mong muốn để bật bộ lọc lương cứng.")
    terms = [values[code] for code in ("full_name", "phone", "residence") if values[code]]
    query = {key: redact(values[key], terms) if values[key] else None for key in ("desired_job", "experience", "desired_location")}
    query.update(region=values["region"], shift=values["shift"], expected_salary=values["expected_salary"], top_k=top_k, strict_salary=strict_salary)
    return query


def validate_result(result, top_k):
    if not isinstance(result, dict) or not isinstance(result.get("recommendations"), list) or len(result["recommendations"]) > top_k:
        raise MatchingUnavailable("Matching trả cấu trúc kết quả không hợp lệ.")
    for key in ("eligible_campaigns", "indexed_campaigns"):
        if type(result.get(key)) is not int or result[key] < 0:
            raise MatchingUnavailable("Matching trả thống kê không hợp lệ.")
    ids = set()
    for item in result["recommendations"]:
        try:
            key = str(uuid.UUID(item["campaign_id"]))
            if key in ids or item.get("status") != "active":
                raise ValueError()
            ids.add(key)
            if type(item.get("semantic_score")) not in (float, int) or not math.isfinite(item["semantic_score"]) or not -1 <= item["semantic_score"] <= 1:
                raise ValueError()
            for field, limit in (("job_title", 500), ("location", 500), ("requirements", 10000), ("benefits", 10000)):
                value = item.get(field)
                if value is not None and (not isinstance(value, str) or len(value) > limit):
                    raise ValueError()
            if not item.get("job_title") or item.get("region") not in (None, "north", "central", "south"):
                raise ValueError()
            for field in ("salary_min", "salary_max"):
                if item.get(field) is not None and (type(item[field]) is not int or item[field] < 0):
                    raise ValueError()
            if not isinstance(item.get("warnings"), list) or len(item["warnings"]) > 10 or any(not isinstance(w, str) or len(w) > 1000 for w in item["warnings"]):
                raise ValueError()
        except (ValueError, TypeError, KeyError, AttributeError):
            raise MatchingUnavailable("Matching trả chiến dịch không hợp lệ; chưa lưu kết quả.") from None
    if not len(result["recommendations"]) <= result["indexed_campaigns"] <= result["eligible_campaigns"]:
        raise MatchingUnavailable("Thống kê chiến dịch không khớp kết quả.")
    if result["eligible_campaigns"] and not result["recommendations"]:
        raise MatchingUnavailable("Có chiến dịch đủ bộ lọc nhưng chưa có kết quả vector hợp lệ.")
    if result["recommendations"] and (not isinstance(result.get("model_name"), str) or not result["model_name"] or len(result["model_name"]) > 200):
        raise MatchingUnavailable("Thiếu thông tin model tìm chiến dịch.")
    if result["recommendations"]:
        try:
            uuid.UUID(result["model_version_id"])
        except (ValueError, TypeError, KeyError, AttributeError):
            raise MatchingUnavailable("Thiếu phiên bản model tìm chiến dịch.") from None
    if result.get("message") is not None and (not isinstance(result["message"], str) or len(result["message"]) > 2000):
        raise MatchingUnavailable("Thông báo Matching không hợp lệ.")
    safe = {key: result.get(key) for key in ("model_version_id", "model_name", "eligible_campaigns", "indexed_campaigns", "message")}
    keys = ("campaign_id", "job_title", "location", "region", "salary_min", "salary_max", "requirements", "benefits", "status", "semantic_score", "warnings")
    safe["recommendations"] = [{key: item.get(key) for key in keys} for item in result["recommendations"]]
    return safe


def search(query):
    base = getattr(settings, "MATCHING_API_URL", "http://127.0.0.1:8001").rstrip("/")
    parsed = urlsplit(base)
    if parsed.scheme not in ("http", "https") or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise MatchingUnavailable("Cấu hình MATCHING_API_URL không hợp lệ.")
    try:
        with requests.Session() as session:
            session.trust_env = False
            with session.post(base + "/api/v1/campaigns/search", json=query, timeout=(3.05, 30), allow_redirects=False, stream=True) as response:
                if response.status_code != 200:
                    raise MatchingUnavailable("Matching chưa tìm được chiến dịch. Kiểm tra log dịch vụ, model/vector và phiên bản API mới.")
                content = bytearray()
                for chunk in response.iter_content(8192):
                    content.extend(chunk)
                    if len(content) > 512000:
                        raise MatchingUnavailable("Kết quả Matching vượt giới hạn an toàn.")
                import json
                result = json.loads(content)
        result = validate_result(result, query["top_k"])
        if any(query.get("region") and item["region"] != query["region"] or query.get("strict_salary") and (item["salary_max"] is None or item["salary_max"] < query["expected_salary"]) for item in result["recommendations"]):
            raise MatchingUnavailable("Kết quả Matching không khớp bộ lọc đã xác nhận.")
        return result
    except (requests.RequestException, ValueError, UnicodeDecodeError):
        raise MatchingUnavailable() from None
