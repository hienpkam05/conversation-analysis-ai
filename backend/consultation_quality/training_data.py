"""Approved-label export and conversation-level splits. No model downloads or training."""

import hashlib
import json
import math
import random
import re
import unicodedata
from collections import Counter, defaultdict

from django.db.models import Count

from .models import Assessment, AudioSample, Conversation, RubricVersion
from .services import InputError, validate_ratings, validate_utterances

SCHEMA = "consultation-quality-dataset-v1"
PREPROCESSING = "roles-redaction-v1"


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")).hexdigest()


def definitions(rubric):
    return {key: rubric.get(key) for key in ("version", "criteria", "general_rules")}


def redact(text, terms=()):
    text = unicodedata.normalize("NFC", text)
    for term in sorted(terms, key=len, reverse=True):
        term = unicodedata.normalize("NFC", term)
        pattern = (r"(?<!\w)" if term[0].isalnum() else "") + re.escape(term) + (r"(?!\w)" if term[-1].isalnum() else "")
        text = re.sub(pattern, "[REDACTED]", text, flags=re.IGNORECASE)
    text = re.sub(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", "[EMAIL]", text, flags=re.IGNORECASE)
    text = re.sub(r"(?:https?://|www\.)\S+", "[URL]", text, flags=re.IGNORECASE)
    text = re.sub(r"(?<!\w)(?:\+84|84|0)(?:[ .()-]*\d){8,10}(?![ .()-]*\d)(?!\w)", "[PHONE]", text)
    text = re.sub(r"(?<!\d)\d{12}(?!\d)", "[IDENTIFIER]", text)
    return text


def fingerprint(turns):
    # Conservative duplicate detection after redaction, without timestamps or turn IDs.
    return digest(" ".join(re.findall(r"\w+", unicodedata.normalize("NFC", " ".join(t["text"] for t in turns)).casefold())))


def training_status():
    return {"database": "Django configured database", "rubrics": list(RubricVersion.objects.values("version", "status")),
        "assessments": list(Assessment.objects.values("status", "source").annotate(count=Count("id"))),
        "approved_manual": Assessment.objects.filter(status="approved", source="manual").count(),
        "note": "Transcript, bản chờ duyệt và nhãn thiếu danh tính duyệt không phải nhãn train."}


def approved_examples(version):
    rubric = RubricVersion.objects.get(version=version)
    if rubric.status != "approved" or not rubric.approved_by_id or not rubric.approved_at:
        raise InputError("Rubric chưa được người phụ trách duyệt đầy đủ. Không xuất nhãn train.")
    stats = Counter()
    result = []
    for conversation in Conversation.objects.order_by("id").iterator():
        revision = conversation.revisions.order_by("-revision_number").first()
        if not revision:
            stats["no_revision"] += 1
            continue
        if revision.status != "sealed" or not revision.roles_confirmed or not revision.transcript_reviewed:
            stats["transcript_unreviewed"] += 1
            continue
        sample = AudioSample.objects.filter(conversation=conversation).first()
        if sample and sample.review_disposition not in ("usable", "incomplete"):
            stats["audio_unreviewed_or_excluded"] += 1
            continue
        rows = list(revision.assessments.filter(status="approved", source="manual", rubric_version=rubric,
            author__isnull=False, reviewer__isnull=False, reviewed_at__isnull=False).order_by("-reviewed_at", "-created_at"))
        replaced = set(Assessment.objects.filter(status="approved", supersedes_id__in=[x.pk for x in rows]).values_list("supersedes_id", flat=True))
        rows = [x for x in rows if x.pk not in replaced]
        # An approved adjudication takes precedence over the two independent input labels.
        resolutions = [x for x in rows if hasattr(x, "resolution")]
        if resolutions:
            rows = resolutions
        valid = []
        for item in rows:
            try:
                if item.author_id == item.reviewer_id and not hasattr(item, "resolution"):
                    raise InputError("Bản chấm độc lập không được tự duyệt.")
                turns = validate_utterances(revision.utterances)
                if any(t["role"] == "unknown" for t in turns):
                    raise InputError("Vai trò chưa xác nhận.")
                if definitions(item.rubric) != definitions(rubric.criteria_json):
                    raise InputError("Snapshot rubric không khớp.")
                ratings, total = validate_ratings(item.ratings, turns, rubric=item.rubric)
                if total != item.total_score:
                    raise InputError("Tổng điểm không khớp.")
                if all(r["score"] is None for r in ratings):
                    stats["all_labels_masked"] += 1
                    continue
                valid.append((item, turns, ratings))
            except InputError:
                stats["invalid_approved_snapshot"] += 1
        if not valid:
            stats["no_eligible_approved_label"] += 1
            continue
        signatures = {digest({r["criterion_code"]: r["score"] for r in entry[2]}) for entry in valid}
        if len(signatures) != 1:
            stats["conflicting_approved_labels"] += 1
            continue
        result.append(valid[0])
    return rubric, result, dict(stats)


def export_dataset(version, groups=None, terms=None):
    groups = {} if groups is None else groups
    terms = [] if terms is None else terms
    if not isinstance(groups, dict) or any(not isinstance(k, str) or not isinstance(v, str) or not v.strip() for k, v in groups.items()):
        raise InputError("Group map phải là JSON object conversation UUID → mã nhóm ứng viên/chuỗi liên hệ.")
    if not isinstance(terms, list) or any(not isinstance(t, str) or not t.strip() for t in terms):
        raise InputError("Danh sách cần che phải là JSON array các chuỗi không trống.")
    rubric, entries, excluded = approved_examples(version)
    if not entries:
        raise InputError("Không có nhãn thủ công đã duyệt đủ điều kiện. Không tạo tập train rỗng hoặc dùng nhãn nháp.")
    examples = []
    groups_complete = True
    for item, turns, ratings in entries:
        key = str(item.revision.conversation_id)
        group = groups.get(key)
        groups_complete = groups_complete and bool(group)
        id_map = {t["id"]: f"u{i:04}" for i, t in enumerate(turns, 1)}
        clean_turns = [{"id": id_map[t["id"]], "role": t["role"], "text": redact(t["text"], terms),
            "unclear": t.get("unclear", False)} for t in turns]
        examples.append({"conversation_id": digest(key), "revision_id": digest(str(item.revision_id)),
            "assessment_id": digest(str(item.pk)), "group_id": digest(group or key),
            "utterances": clean_turns, "content_hash": fingerprint(clean_turns),
            "labels": {r["criterion_code"]: r["score"] for r in ratings},
            "evidence": {r["criterion_code"]: {"kind": r["evidence"]["kind"],
                "utterance_ids": [id_map[i] for i in r["evidence"]["utterance_ids"]]} for r in ratings}})
    payload = {"schema_version": SCHEMA, "preprocessing_version": PREPROCESSING,
        "purpose": "approved_labels_privacy_review", "rubric": definitions(rubric.criteria_json),
        "rubric_hash": digest(definitions(rubric.criteria_json)), "grouping_verified": groups_complete,
        "privacy_review_required": True, "excluded_counts": excluded, "items": examples}
    payload["dataset_sha256"] = digest(payload)
    return payload


def validate_dataset(payload):
    if not isinstance(payload, dict) or payload.get("schema_version") != SCHEMA:
        raise InputError("Schema tập dữ liệu không hợp lệ.")
    if payload.get("preprocessing_version") != PREPROCESSING or payload.get("purpose") != "approved_labels_privacy_review":
        raise InputError("Phiên bản tiền xử lý hoặc mục đích bản xuất không hợp lệ.")
    if payload.get("dataset_sha256") != digest({k: v for k, v in payload.items() if k != "dataset_sha256"}):
        raise InputError("Tập dữ liệu đã đổi hoặc checksum không khớp; xuất lại từ nhãn đã duyệt.")
    items = payload.get("items")
    if not isinstance(items, list) or not items:
        raise InputError("Tập dữ liệu rỗng.")
    rubric = payload.get("rubric", {})
    if not isinstance(rubric, dict) or not isinstance(rubric.get("criteria"), list) or any(not isinstance(c, dict) for c in rubric["criteria"]):
        raise InputError("Cấu trúc rubric không hợp lệ.")
    if payload.get("rubric_hash") != digest(rubric):
        raise InputError("Checksum rubric không khớp.")
    codes = [c.get("code") for c in rubric.get("criteria", [])]
    weights = [c.get("weight") for c in rubric["criteria"]]
    if any(not isinstance(c, str) for c in codes) or len(codes) != 5 or len(set(codes)) != 5:
        raise InputError("Cần đúng năm tiêu chí.")
    if any(type(w) not in (int, float) or not math.isfinite(w) or not 0 < w <= 1 for w in weights) or not math.isclose(sum(weights), 1):
        raise InputError("Trọng số rubric không hợp lệ.")
    seen = set()
    for item in items:
        if not isinstance(item, dict):
            raise InputError("Bản ghi dữ liệu không hợp lệ.")
        for field in ("conversation_id", "revision_id", "assessment_id", "group_id", "content_hash"):
            if not isinstance(item.get(field), str) or not re.fullmatch(r"[0-9a-f]{64}", item[field]):
                raise InputError("ID đã mã hóa không hợp lệ.")
        if item["conversation_id"] in seen:
            raise InputError("Một cuộc gọi chỉ được có một nhãn kết luận trong tập dữ liệu.")
        seen.add(item["conversation_id"])
        turns = validate_utterances(item.get("utterances"))
        if any(t["role"] == "unknown" for t in turns) or fingerprint(turns) != item["content_hash"]:
            raise InputError("Nội dung hoặc vai trò hội thoại không hợp lệ.")
        labels = item.get("labels")
        if not isinstance(labels, dict) or set(labels) != set(codes) or any(v is not None and (type(v) is not int or v not in (0, 1, 2)) for v in labels.values()):
            raise InputError("Nhãn phải là 0/1/2 hoặc null để mask loss.")
        if all(v is None for v in labels.values()):
            raise InputError("Bản ghi không có nhãn quan sát được.")
    return items


def make_splits(payload, privacy_sha256, reviewer, seed=42, ratios=(0.7, 0.15, 0.15)):
    items = validate_dataset(payload)
    if payload.get("grouping_verified") is not True:
        raise InputError("Thiếu group map đã kiểm tra cho ứng viên/chuỗi liên hệ; không chia ngẫu nhiên từng cuộc gọi.")
    if privacy_sha256 != payload["dataset_sha256"] or not isinstance(reviewer, str) or not reviewer.strip():
        raise InputError("Cần người kiểm tra riêng tư xác nhận đúng SHA256 của bản xuất đã đọc.")
    if len(ratios) != 3 or any(type(r) not in (int, float) or not math.isfinite(r) or r <= 0 for r in ratios) or not math.isclose(sum(ratios), 1):
        raise InputError("Ba tỷ lệ train/validation/test phải dương và có tổng bằng 1.")
    # Connected components keep both known contact groups and normalized duplicates together.
    parent = list(range(len(items)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    seen = {}
    for i, item in enumerate(items):
        for field in ("conversation_id", "group_id", "content_hash"):
            key = (field, item[field])
            if key in seen:
                parent[find(i)] = find(seen[key])
            seen[key] = i
    components = defaultdict(list)
    for i, item in enumerate(items):
        components[find(i)].append(item)
    groups = sorted(components.values(), key=lambda rows: min(x["conversation_id"] for x in rows))
    if len(groups) < 3:
        raise InputError("Cần ít nhất ba nhóm độc lập sau khi gộp bản trùng để tạo ba tập không rò rỉ.")
    random.Random(seed).shuffle(groups)
    train_count = max(1, min(len(groups) - 2, int(len(groups) * ratios[0])))
    val_count = max(1, min(len(groups) - train_count - 1, int(len(groups) * ratios[1])))
    sets = {"train": groups[:train_count], "validation": groups[train_count:train_count + val_count], "test": groups[train_count + val_count:]}
    split_items = {name: sorted([x for group in rows for x in group], key=lambda x: x["conversation_id"]) for name, rows in sets.items()}
    report = {"seed": seed, "requested_ratios": list(ratios), "independent_groups": len(groups),
        "privacy_review": {"reviewer": reviewer.strip(), "dataset_sha256": privacy_sha256},
        "split_counts": {k: len(v) for k, v in split_items.items()}, "label_counts": {}, "warnings": [],
        "duplicate_policy": "known contact groups and exact normalized redacted transcript; semantic near-duplicates require human review"}
    for name, rows in split_items.items():
        report["label_counts"][name] = {code: {str(label): sum(x["labels"][code] == label for x in rows) for label in (0, 1, 2, None)} for code in items[0]["labels"]}
        for code, counts in report["label_counts"][name].items():
            if any(counts[str(i)] == 0 for i in (0, 1, 2)):
                report["warnings"].append(f"{name}/{code}: thiếu ít nhất một lớp 0/1/2; không đủ cơ sở nghiệm thu model.")
    for field in ("conversation_id", "group_id", "content_hash"):
        names = list(split_items)
        for i, a in enumerate(names):
            for b in names[i + 1:]:
                if {x[field] for x in split_items[a]} & {x[field] for x in split_items[b]}:
                    raise InputError("Phát hiện rò rỉ tập dữ liệu.")
    bundle = {"schema_version": SCHEMA, "purpose": "research_training_only", "dataset_sha256": payload["dataset_sha256"],
        "rubric": payload["rubric"], "rubric_hash": payload["rubric_hash"], "preprocessing_version": PREPROCESSING,
        "release_approved": False, "report": report, "splits": split_items}
    bundle["bundle_sha256"] = digest(bundle)
    return bundle
