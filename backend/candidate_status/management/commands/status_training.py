import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from consultation_quality.services import InputError
from candidate_status.dataset import export_dataset, split_dataset
from candidate_status.review import training_status


class Command(BaseCommand):
    help = "Kiểm tra nhãn, xuất bản cần kiểm tra riêng tư, chia tập; không tự duyệt hoặc train."

    def add_arguments(self, parser):
        parser.add_argument("operation", choices=["status", "export", "split"])
        parser.add_argument("--output", type=Path)
        parser.add_argument("--input", type=Path)
        parser.add_argument("--group-map", type=Path)
        parser.add_argument("--redact-terms", type=Path)
        parser.add_argument("--privacy-sha256")
        parser.add_argument("--reviewer")
        parser.add_argument("--seed", type=int, default=42)

    def handle(self, *args, **options):
        try:
            operation = options["operation"]
            if operation == "status":
                self.stdout.write(json.dumps(training_status(), ensure_ascii=False, indent=2))
                return
            output = options["output"]
            if not output or output.exists():
                raise InputError("Chọn --output mới, không ghi đè bản xuất cũ.")
            if operation == "export":
                if not options["group_map"]:
                    raise InputError("Cần --group-map đã đối chiếu nhóm ứng viên/chuỗi liên hệ.")
                groups = json.loads(options["group_map"].read_text(encoding="utf-8"))
                terms = json.loads(options["redact_terms"].read_text(encoding="utf-8")) if options["redact_terms"] else []
                payload = export_dataset(groups, terms)
            else:
                if not options["input"]:
                    raise InputError("Cần --input là bản xuất đã đọc kiểm tra riêng tư.")
                payload = split_dataset(json.loads(options["input"].read_text(encoding="utf-8")), options["privacy_sha256"], options["reviewer"], options["seed"])
            output.parent.mkdir(parents=True, exist_ok=True)
            with output.open("x", encoding="utf-8") as stream:
                json.dump(payload, stream, ensure_ascii=False, indent=2, allow_nan=False)
            self.stdout.write(f"Đã ghi {output}. SHA256: {payload.get('bundle_sha256', payload.get('dataset_sha256'))}")
            if operation == "export":
                self.stdout.write("Phải kiểm tra riêng tư; regex không bảo đảm ẩn danh hoàn chỉnh.")
        except (InputError, OSError, ValueError) as exc:
            raise CommandError(str(exc)) from exc
