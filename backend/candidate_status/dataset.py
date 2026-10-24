"""Export reviewed labels only; keep contact groups and duplicate calls in one split."""
from collections import Counter, defaultdict
import random
import re

from consultation_quality.models import AudioSample, Conversation
from consultation_quality.services import InputError, validate_utterances
from consultation_quality.training_data import digest, fingerprint, redact
from .models import StatusDecision
from .review import approval, definitions
from .services import LABEL_MAP, TAXONOMY_VERSION, check_confirmable

SCHEMA = "candidate-status-dataset-v1"
PREPROCESSING = "status-roles-redaction-v1"


def eligible(require_approval=True):
    if not approval():
        if require_approval:
            raise InputError("Bộ nhãn chưa được duyệt; chưa xuất dữ liệu train.")
        return [], {"taxonomy_unapproved": 1}
    entries, excluded = [], Counter()
    for conversation in Conversation.objects.order_by("pk"):
        revision = conversation.revisions.order_by("-revision_number").first()
        sample = AudioSample.objects.filter(conversation=conversation).first()
        if not revision or not revision.transcript_reviewed or not revision.roles_confirmed:
            excluded["transcript_unreviewed"] += 1
            continue
        if sample and sample.review_disposition != "usable":
            excluded["audio_not_approved_usable"] += 1
            continue
        all_rows = list(StatusDecision.objects.filter(revision=revision).select_related("revision__conversation", "training_review"))
        candidates = [row for row in all_rows if row.source == "manual" and row.status == "confirmed"
            and row.taxonomy_version == TAXONOMY_VERSION and hasattr(row, "training_review")
            and row.training_review.verdict == "approved" and row.training_review.reviewer_id != row.author_id]
        by_id = {row.pk: row for row in all_rows}
        replaced = set()
        for row in candidates:
            ancestor = row.supersedes_id
            while ancestor and ancestor not in replaced:
                replaced.add(ancestor)
                ancestor = by_id[ancestor].supersedes_id if ancestor in by_id else None
        valid = []
        for row in candidates:
            if row.pk in replaced:
                continue
            try:
                check_confirmable(row)
                valid.append(row)
            except InputError:
                excluded["invalid_or_stale_snapshot"] += 1
        if not valid:
            excluded["no_independently_approved_manual_label"] += 1
        elif len({row.label for row in valid}) > 1:
            excluded["conflicting_approved_labels"] += 1
        elif any(row.source == "manual" and row.status == "confirmed" and row.label != valid[0].label
                and not hasattr(row, "training_review") for row in all_rows):
            excluded["pending_conflicting_manual_label"] += 1
        else:
            entries.append(max(valid, key=lambda row: (row.training_review.created_at, str(row.pk))))
    return entries, dict(excluded)


def export_dataset(groups, terms=None):
    if not isinstance(groups, dict) or any(not isinstance(k, str) or not isinstance(v, str) or not v.strip() for k, v in groups.items()):
        raise InputError("Group map phải là object conversation UUID → mã nhóm ứng viên/chuỗi liên hệ.")
    terms = [] if terms is None else terms
    if not isinstance(terms, list) or any(not isinstance(t, str) or not t.strip() for t in terms):
        raise InputError("Danh sách che thông tin phải là array chuỗi không trống.")
    entries, excluded = eligible()
    if not entries:
        raise InputError("Chưa có nhãn thủ công được duyệt độc lập đủ điều kiện; không tạo tập train rỗng.")
    items = []
    for row in entries:
        key = str(row.revision.conversation_id)
        if not groups.get(key):
            raise InputError("Thiếu nhóm liên hệ đã kiểm tra cho ít nhất một hội thoại.")
        ids = {t["id"]: f"u{i:04}" for i, t in enumerate(row.utterances, 1)}
        turns = [{"id": ids[t["id"]], "role": t["role"], "text": redact(t["text"], terms), "unclear": t.get("unclear", False)} for t in row.utterances]
        items.append({"conversation_id": digest(key), "group_id": digest(groups[key]), "decision_id": digest(str(row.pk)),
            "content_hash": fingerprint(turns), "utterances": turns, "label": row.label,
            "evidence_ids": [ids[i] for i in row.evidence_ids]})
    payload = {"schema": SCHEMA, "preprocessing": PREPROCESSING, "definitions": definitions(), "definition_hash": digest(definitions()),
        "excluded_counts": excluded, "privacy_review_required": True, "items": items}
    payload["dataset_sha256"] = digest(payload)
    return payload


def checksum(payload, field):
    if not isinstance(payload, dict) or payload.get(field) != digest({k: v for k, v in payload.items() if k != field}):
        raise InputError("Checksum dữ liệu không khớp.")


def validate_items(items):
    if not isinstance(items, list) or not items:
        raise InputError("Tập dữ liệu không có bản ghi.")
    seen = set()
    for row in items:
        if not isinstance(row, dict):
            raise InputError("Bản ghi không hợp lệ.")
        for key in ("conversation_id", "group_id", "decision_id", "content_hash"):
            if not isinstance(row.get(key), str) or not re.fullmatch("[0-9a-f]{64}", row[key]):
                raise InputError("Thiếu ID/hash dữ liệu hợp lệ.")
        if row["conversation_id"] in seen:
            raise InputError("Trùng hội thoại trong tập dữ liệu.")
        seen.add(row["conversation_id"])
        turns = validate_utterances(row.get("utterances"))
        if any(t["role"] == "unknown" for t in turns) or fingerprint(turns) != row["content_hash"]:
            raise InputError("Snapshot hoặc vai người nói không khớp.")
        if not isinstance(row.get("label"), str) or row["label"] not in LABEL_MAP:
            raise InputError("Nhãn dữ liệu không hợp lệ.")
        ids = row.get("evidence_ids")
        valid_ids = {t["id"] for t in turns if t["role"] == "candidate" and not t.get("unclear")}
        if not isinstance(ids, list) or any(not isinstance(i, str) or i not in valid_ids for i in ids) or (row["label"] != "unknown" and not ids):
            raise InputError("Dẫn chứng train không hợp lệ.")


def split_dataset(payload, privacy_sha, reviewer, seed=42):
    checksum(payload, "dataset_sha256")
    if payload.get("schema") != SCHEMA or payload.get("preprocessing") != PREPROCESSING or payload.get("definitions") != definitions() or payload.get("definition_hash") != digest(definitions()):
        raise InputError("Schema/bộ nhãn/tiền xử lý không khớp.")
    validate_items(payload.get("items"))
    if privacy_sha != payload["dataset_sha256"] or not isinstance(reviewer, str) or not reviewer.strip():
        raise InputError("Cần xác nhận riêng tư đúng SHA256 và người đã kiểm tra bản xuất.")
    items = payload["items"]
    parent = list(range(len(items)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    seen = {}
    for i, row in enumerate(items):
        for field in ("group_id", "content_hash"):
            key = (field, row[field])
            if key in seen:
                parent[find(i)] = find(seen[key])
            seen[key] = i
    components = defaultdict(list)
    for i, row in enumerate(items):
        components[find(i)].append(row)
    groups = sorted(components.values(), key=lambda rows: min(row["conversation_id"] for row in rows))
    if len(groups) < 3:
        raise InputError("Cần ít nhất 3 nhóm độc lập sau khi gộp cuộc trùng.")
    random.Random(seed).shuffle(groups)
    train_end = max(1, min(len(groups) - 2, int(len(groups) * .7)))
    val_end = train_end + max(1, min(len(groups) - train_end - 1, int(len(groups) * .15)))
    splits = {"train": sum(groups[:train_end], []), "validation": sum(groups[train_end:val_end], []), "test": sum(groups[val_end:], [])}
    counts = {name: {code: sum(row["label"] == code for row in rows) for code in LABEL_MAP} for name, rows in splits.items()}
    result = {"schema": SCHEMA, "preprocessing": PREPROCESSING, "definitions": definitions(), "definition_hash": digest(definitions()),
        "dataset_sha256": payload["dataset_sha256"], "privacy_review": {"reviewer": reviewer.strip(), "dataset_sha256": privacy_sha},
        "seed": seed, "splits": splits, "counts": counts, "release_approved": False,
        "warnings": [f"{name}: thiếu nhãn {code}" for name, labels in counts.items() for code, count in labels.items() if not count]}
    result["bundle_sha256"] = digest(result)
    return result


def validate_bundle(bundle):
    checksum(bundle, "bundle_sha256")
    if bundle.get("schema") != SCHEMA or bundle.get("preprocessing") != PREPROCESSING or bundle.get("definitions") != definitions() or bundle.get("definition_hash") != digest(definitions()):
        raise InputError("Tập chia không tương thích bộ nhãn/tiền xử lý.")
    privacy = bundle.get("privacy_review", {})
    if not isinstance(privacy, dict) or not privacy.get("reviewer") or privacy.get("dataset_sha256") != bundle.get("dataset_sha256"):
        raise InputError("Thiếu audit kiểm tra riêng tư.")
    splits = bundle.get("splits")
    if not isinstance(splits, dict) or set(splits) != {"train", "validation", "test"}:
        raise InputError("Thiếu ba tập train/validation/test.")
    validate_items([row for rows in splits.values() for row in rows] if all(isinstance(rows, list) for rows in splits.values()) else None)
    seen = {}
    for name, rows in splits.items():
        validate_items(rows)
        for row in rows:
            for field in ("group_id", "content_hash"):
                key = (field, row[field])
                if key in seen and seen[key] != name:
                    raise InputError("Rò rỉ nhóm hoặc nội dung giữa các tập.")
                seen[key] = name
    return splits
