import json
import math
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.test.utils import override_settings
from django.utils import timezone

from consultation_quality.access import can_review
from consultation_quality.services import InputError
from candidate_status.inference import read_manifest
from candidate_status.metrics import CODES
from candidate_status.ml import file_hash, write_json


class Command(BaseCommand):
    help = "Duyệt checkpoint sau khi người phụ trách đọc đánh giá và kiểm tra giấy phép; không train hay tự suy diễn phê duyệt."

    def add_arguments(self, parser):
        parser.add_argument("directory", type=Path)
        parser.add_argument("--reviewer", required=True)
        parser.add_argument("--evaluation-sha256", required=True)
        parser.add_argument("--note", required=True)
        parser.add_argument("--license-reviewed", action="store_true")
        parser.add_argument("--confirm-evaluation", action="store_true")
        parser.add_argument("--minimum-macro-f1", type=float, default=.6)

    def handle(self, *args, **options):
        try:
            user = get_user_model().objects.filter(username=options["reviewer"], is_active=True).first()
            if user is None or not can_review(user) or not options["license_reviewed"] or not options["confirm_evaluation"] or not options["note"].strip():
                raise InputError("Cần reviewer có quyền, ghi chú, xác nhận đánh giá và giấy phép thật.")
            minimum = options["minimum_macro_f1"]
            if not .6 <= minimum <= 1:
                raise InputError("Ngưỡng phát hành tối thiểu phải từ 0.6 đến 1; không phải bảo đảm chất lượng nghiệp vụ.")
            with override_settings(STATUS_MODEL_DIR=str(options["directory"])):
                root, spec = read_manifest(require_approved=False)
            if spec.get("approved_for_use"):
                raise InputError("Checkpoint đã có audit duyệt; không ghi đè.")
            if any(file_hash(root / name) != expected for name, expected in spec["files"].items()):
                raise InputError("Checkpoint/evaluation đã thay đổi.")
            if file_hash(root / "evaluation.json") != options["evaluation_sha256"]:
                raise InputError("SHA256 evaluation không khớp bản người phụ trách đã đọc.")
            evaluation = json.loads((root / "evaluation.json").read_text(encoding="utf-8"))
            test = evaluation["reports"]["test"]
            values = [test["macro_f1"], evaluation["baseline"]["test"]["macro_f1"]]
            if any(type(value) not in (int, float) or not math.isfinite(value) or not 0 <= value <= 1 for value in values):
                raise InputError("Báo cáo đánh giá có chỉ số không hợp lệ.")
            if (evaluation.get("definition_hash") != spec["definition_hash"] or evaluation.get("bundle_sha256") != spec.get("bundle_sha256")
                    or evaluation.get("threshold") != spec["threshold"] or evaluation.get("threshold_selected_on") != "validation"
                    or test["macro_f1"] < minimum or test["macro_f1"] <= evaluation["baseline"]["test"]["macro_f1"]
                    or any(type(test["per_class"][code]["support"]) is not int or test["per_class"][code]["support"] < 1 for code in CODES)):
                raise InputError("Chưa đạt cổng phát hành: cần đủ support test, vượt baseline và ngưỡng macro-F1; kiểm tra riêng lỗi nghiệp vụ.")
            spec.update(approved_for_use=True, approved_by=user.get_username(), approved_at=timezone.now().isoformat(),
                approval_note=options["note"].strip(), evaluation_review_sha256=options["evaluation_sha256"], license_reviewed_for_release=True)
            temporary = root / "status-manifest.pending"
            write_json(temporary, spec)
            temporary.replace(root / "status-manifest.json")
            self.stdout.write("Đã ghi audit phê duyệt checkpoint. Đặt STATUS_MODEL_DIR và restart Django trước khi sử dụng.")
        except (InputError, OSError, ValueError, TypeError, KeyError) as exc:
            raise CommandError(str(exc)) from exc
