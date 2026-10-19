import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from consultation_quality.services import InputError
from consultation_quality.training_metrics import evaluate, majority_baseline, validate_bundle


class Command(BaseCommand):
    help = "Fit baseline nhãn phổ biến chỉ trên train và báo cáo riêng validation/test; không phải ViDeBERTa."

    def add_arguments(self, parser):
        parser.add_argument("bundle", type=Path)
        parser.add_argument("output", type=Path)

    def handle(self, *args, **options):
        if options["output"].exists():
            raise CommandError("File đích đã tồn tại; không ghi đè báo cáo cũ.")
        try:
            bundle = json.loads(options["bundle"].read_text(encoding="utf-8"))
            splits = validate_bundle(bundle)
            codes = [c["code"] for c in bundle["rubric"]["criteria"]]
            baseline = majority_baseline(splits["train"], codes)
            report = {"model": "majority-per-criterion-v1", "bundle_sha256": bundle["bundle_sha256"],
                "rubric_hash": bundle["rubric_hash"], "fitted_on": "train_only", "release_approved": False,
                "baseline": baseline, "warnings": bundle["report"]["warnings"],
                "evaluation": {name: evaluate(splits[name], [{c: baseline[c]["score"] for c in codes} for _ in splits[name]], bundle["rubric"]) for name in ("validation", "test")}}
        except (InputError, OSError, ValueError) as exc:
            raise CommandError(f"Không chạy baseline: {exc}") from exc
        options["output"].parent.mkdir(parents=True, exist_ok=True)
        with options["output"].open("x", encoding="utf-8") as stream:
            json.dump(report, stream, ensure_ascii=False, indent=2, allow_nan=False)
        self.stdout.write("Baseline report saved; trained on train only; release_approved=false. No ViDeBERTa checkpoint created.")
