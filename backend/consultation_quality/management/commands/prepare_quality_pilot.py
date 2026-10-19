import json
import time
import uuid
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from consultation_quality.models import AudioSample, Conversation, Revision
from consultation_quality.services import validate_utterances


class Command(BaseCommand):
    help = "Register local pilot audio and transcribe with an existing local Whisper checkpoint; never train."

    def add_arguments(self, parser):
        parser.add_argument("manifest", type=Path)
        parser.add_argument("--model-path", type=Path)
        parser.add_argument("--register-only", action="store_true")
        parser.add_argument("--threads", type=int, default=8)
        parser.add_argument("--batch-size", type=int, default=1)

    def handle(self, *args, **options):
        entries = json.loads(options["manifest"].read_text(encoding="utf-8"))
        if not isinstance(entries, list) or len({x["call_id"] for x in entries}) != len(entries):
            raise CommandError("Invalid or duplicate manifest")
        samples = []
        for entry in entries:
            path = Path(entry["source_path"]).resolve(strict=True)
            if not path.is_file() or path.suffix.lower() != ".mp3":
                raise CommandError("Manifest must contain existing MP3 files")
            with transaction.atomic():
                sample = AudioSample.objects.filter(call_id=entry["call_id"]).first()
                if sample is None:
                    conversation = Conversation.objects.create(title=entry["call_id"], source_type="stt", source_reference=entry["call_id"])
                    sample = AudioSample.objects.create(call_id=entry["call_id"], source_path=str(path),
                        duration_seconds=entry["duration_seconds"], conversation=conversation)
                elif Path(sample.source_path) != path:
                    raise CommandError("Existing call ID has a different source")
            samples.append(sample)
        self.stdout.write(f"Registered {len(samples)} samples", ending="\n")
        if options["register_only"]:
            return
        model_path = options["model_path"]
        if model_path is None or not (model_path / "model.bin").is_file():
            raise CommandError("Provide --model-path pointing to an existing complete checkpoint")
        from faster_whisper import BatchedInferencePipeline, WhisperModel
        model = WhisperModel(str(model_path), device="cpu", compute_type="int8",
            cpu_threads=options["threads"], num_workers=1, local_files_only=True)
        inference = BatchedInferencePipeline(model) if options["batch_size"] > 1 else model
        failures = 0
        for index, sample in enumerate(samples, 1):
            if sample.status in {"ready", "no_speech"}:
                self.stdout.write(f"{index}/{len(samples)} {sample.call_id} already processed")
                continue
            sample.status, sample.error_code = "running", ""
            sample.save()
            started = time.monotonic()
            self.stdout.write(f"{index}/{len(samples)} {sample.call_id} processing ({sample.duration_seconds:.1f}s)")
            self.stdout.flush()
            try:
                batch_options = {"batch_size": options["batch_size"]} if options["batch_size"] > 1 else {}
                generator, info = inference.transcribe(sample.source_path, language="vi", beam_size=1,
                    temperature=0, condition_on_previous_text=False, vad_filter=True,
                    vad_parameters={"min_silence_duration_ms": 500, "speech_pad_ms": 200},
                    word_timestamps=False, **batch_options)
                segments = []
                for segment in generator:
                    if segment.text.strip():
                        segments.append({"id": str(uuid.uuid4()), "role": "unknown", "text": segment.text.strip(),
                            "start_seconds": segment.start, "end_seconds": segment.end,
                            "avg_logprob": segment.avg_logprob, "no_speech_prob": segment.no_speech_prob})
                    if len(segments) and len(segments) % 10 == 0:
                        self.stdout.write(f"{sample.call_id}: {segment.end:.0f}s decoded")
                        self.stdout.flush()
                turns = validate_utterances(segments) if segments else []
                with transaction.atomic():
                    # A rerun must never replace human corrections or duplicate a completed import.
                    if not sample.conversation.revisions.exists():
                        Revision.objects.create(conversation=sample.conversation, utterances=turns,
                            source_type="stt", roles_confirmed=False)
                    sample.status = "ready" if turns else "no_speech"
                    sample.model_version = model_path.name
                    sample.transcript_metadata = {"model": "faster-whisper-large-v3", "checkpoint": model_path.name,
                        "beam_size": 1, "language": "vi", "duration_seconds": info.duration,
                        "batch_size": options["batch_size"],
                        "elapsed_seconds": round(time.monotonic() - started, 2),
                        "raw_segments": segments, "reviewed": False}
                    sample.save()
                self.stdout.write(f"{sample.call_id}: {sample.status}, {len(turns)} segments, {time.monotonic()-started:.1f}s")
                self.stdout.flush()
            except Exception as exc:
                sample.status, sample.error_code = "failed", type(exc).__name__
                sample.save()
                failures += 1
                self.stderr.write(f"{sample.call_id}: {type(exc).__name__}")
        if failures:
            raise CommandError(f"{failures} samples failed; successful results retained for resume")
