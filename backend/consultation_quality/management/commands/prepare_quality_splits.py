import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from consultation_quality.services import InputError
from consultation_quality.training_data import make_splits


class Command(BaseCommand):
    help = "Chia nhóm train/validation/test sau khi con người kiểm tra riêng tư, không train."

    def add_arguments(self, parser):
        parser.add_argument("dataset", type=Path)
        parser.add_argument("output", type=Path)
        parser.add_argument("--privacy-reviewed-sha256", required=True)
        parser.add_argument("--privacy-reviewer", required=True)
        parser.add_argument("--seed", type=int, default=42)

    def handle(self, *args, **options):
        if options["output"].exists():
            raise CommandError("File đích đã tồn tại; không ghi đè tập chia đã đóng băng.")
        try:
            data = json.loads(options["dataset"].read_text(encoding="utf-8"))
            bundle = make_splits(data, options["privacy_reviewed_sha256"], options["privacy_reviewer"], options["seed"])
        except (InputError, OSError, ValueError) as exc:
            raise CommandError(f"Không chia dữ liệu: {exc}") from exc
        options["output"].parent.mkdir(parents=True, exist_ok=True)
        with options["output"].open("x", encoding="utf-8") as stream:
            json.dump(bundle, stream, ensure_ascii=False, indent=2, allow_nan=False)
        self.stdout.write(json.dumps(bundle["report"], ensure_ascii=False, indent=2))
        self.stdout.write(f"Bundle SHA256: {bundle['bundle_sha256']}; release_approved=false")
