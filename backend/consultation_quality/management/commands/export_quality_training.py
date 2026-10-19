import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from consultation_quality.models import RubricVersion
from consultation_quality.services import InputError
from consultation_quality.training_data import export_dataset


class Command(BaseCommand):
    help = "Xuất nhãn thủ công đã duyệt để kiểm tra riêng tư; không dùng nháp hoặc tải model."

    def add_arguments(self, parser):
        parser.add_argument("output", type=Path)
        parser.add_argument("--rubric-version", required=True)
        parser.add_argument("--group-map", type=Path)
        parser.add_argument("--redact-terms", type=Path)

    def handle(self, *args, **options):
        output = options["output"]
        if output.exists():
            raise CommandError("File đích đã tồn tại; chọn tên mới để giữ bản xuất cũ.")
        try:
            groups = json.loads(options["group_map"].read_text(encoding="utf-8")) if options["group_map"] else None
            terms = json.loads(options["redact_terms"].read_text(encoding="utf-8")) if options["redact_terms"] else None
            payload = export_dataset(options["rubric_version"], groups, terms)
        except (InputError, RubricVersion.DoesNotExist, OSError, ValueError) as exc:
            raise CommandError(f"Không xuất dữ liệu: {exc}") from exc
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open("x", encoding="utf-8") as stream:
            json.dump(payload, stream, ensure_ascii=False, indent=2, allow_nan=False)
        self.stdout.write(f"Exported {len(payload['items'])} approved labels; privacy review REQUIRED.")
        self.stdout.write(f"SHA256: {payload['dataset_sha256']}")
        self.stdout.write(f"Grouping verified: {payload['grouping_verified']}. Không coi che bằng regex là ẩn danh hoàn chỉnh.")
