import json
from pathlib import Path

from django.core.management.base import BaseCommand

from consultation_quality.models import AudioSample
from consultation_quality.services import transcript_review_flags


class Command(BaseCommand):
    help = "Export local transcript snapshots for human review, without training labels or source paths."

    def add_arguments(self, parser):
        parser.add_argument("output", type=Path)

    def handle(self, *args, **options):
        rows = []
        for sample in AudioSample.objects.select_related("conversation").order_by("call_id"):
            revision = sample.conversation.revisions.order_by("-created_at").first()
            rows.append({"call_id": sample.call_id, "status": sample.status,
                "duration_seconds": sample.duration_seconds, "model_version": sample.model_version,
                "review_disposition": sample.review_disposition,
                "revision_id": str(revision.id) if revision else None,
                "roles_confirmed": revision.roles_confirmed if revision else False,
                "transcript_reviewed": revision.transcript_reviewed if revision else False,
                "utterances": revision.utterances if revision else [],
                "review_flags": transcript_review_flags(revision.utterances, sample.transcript_metadata.get("raw_segments", [])) if revision else [],
                "error_code": sample.error_code})
        payload = {"schema_version": 1, "purpose": "human_review_only", "approved_for_training": False, "items": rows}
        output = options["output"]
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        self.stdout.write(f"Exported {len(rows)} transcript snapshots for human review; no training labels")
