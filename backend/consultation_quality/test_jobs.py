import json
import uuid
from copy import deepcopy
from datetime import timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import TestCase, override_settings
from django.utils import timezone
from django.core.management import call_command
from io import StringIO

from .inference import FORMAT, PREPROCESSING, InferenceError, normalize_output, read_spec, status, token_windows
from .jobs import claim_job, execute_job, fail_job
from .models import Assessment, AssessmentJob, Conversation, QualityWorkerSlot, Revision, RubricVersion
from .rubric import RUBRIC
from .training_data import definitions, digest


class JobTests(TestCase):
    def setUp(self):
        self.folder = TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.root = Path(self.folder.name)
        self.settings_override = override_settings(QUALITY_MODEL_DIR=str(self.root))
        self.settings_override.enable()
        self.addCleanup(self.settings_override.disable)
        User = get_user_model()
        self.user = User.objects.create_user("job-owner")
        self.other = User.objects.create_user("job-other")
        self.reviewer = User.objects.create_user("job-reviewer", is_superuser=True)
        for user in (self.user, self.other):
            user.user_permissions.add(Permission.objects.get(codename="annotate_quality"))
        self.client.force_login(self.user)
        self.rubric = RubricVersion.objects.get(version=RUBRIC["version"])
        self.rubric.status, self.rubric.approved_by, self.rubric.approved_at = "approved", self.reviewer, timezone.now()
        self.rubric.save()
        self.conversation = Conversation.objects.create(title="Synthetic job fixture", owner=self.user)
        self.turns = [{"id": "one", "position": 1, "role": "consultant", "text": "Xin chào, em tư vấn công việc.", "start_seconds": None, "end_seconds": None}]
        self.revision = self.make_revision()
        codes = [c["code"] for c in RUBRIC["criteria"]]
        for name in ("tokenizer.json", "quality.safetensors"):
            (self.root / name).write_text("test-fixture-not-a-real-model", encoding="utf-8")
        (self.root / "config.json").write_text(json.dumps({"model_type": "deberta-v2", "hidden_size": 8, "max_position_embeddings": 32}), encoding="utf-8")
        self.spec = {"format": FORMAT, "preprocessing_version": PREPROCESSING, "model_version": "test-only-five-head-v1",
            "rubric_version": self.rubric.version, "rubric_hash": digest(definitions(self.rubric.criteria_json)),
            "approved_for_use": True, "approved_by": "test-fixture", "approved_at": "2026-10-19T00:00:00Z", "evaluation_sha256": "a" * 64,
            "criteria": codes, "confidence_thresholds": {c: .7 for c in codes}, "max_length": 32, "overlap_tokens": 4, "max_windows": 20,
            "files": {"config.json": "a" * 64, "tokenizer.json": "b" * 64, "quality.safetensors": "c" * 64}}
        self.write_spec()
        self.result = {"probabilities": {c: [.05, .15, .8] for c in codes}, "windows": 2}

    def write_spec(self):
        (self.root / "quality-manifest.json").write_text(json.dumps(self.spec), encoding="utf-8")

    def make_revision(self):
        return Revision.objects.create(conversation=self.conversation, utterances=self.turns,
            roles_confirmed=True, transcript_reviewed=True, status="sealed")

    def post(self, path, data, expected=202):
        response = self.client.post("/api/quality/" + path, data, content_type="application/json")
        self.assertEqual(response.status_code, expected, response.content)
        return response.json()

    def enqueue(self, revision=None, key=None, expected=202):
        with patch("consultation_quality.job_views.status", return_value={"available": True}), patch("consultation_quality.inference.status", return_value={"available": True}):
            return self.post(f"revisions/{(revision or self.revision).pk}/assessment-jobs/", {"rubric_id": str(self.rubric.pk), "request_key": key or str(uuid.uuid4())}, expected)

    def run_job(self, result=None, error=None):
        claimed = claim_job()
        self.assertIsNotNone(claimed)
        with patch("consultation_quality.jobs.LocalProvider.predict", return_value=result or self.result, side_effect=error):
            execute_job(*claimed)
        return AssessmentJob.objects.get(pk=claimed[0])

    def test_status_missing_model_does_not_load_ml(self):
        with override_settings(QUALITY_MODEL_DIR=""):
            with patch("consultation_quality.inference.LocalProvider.predict", side_effect=AssertionError("must not load")):
                response = self.client.get("/api/quality/model-status/")
            self.assertFalse(response.json()["available"])
            self.assertEqual(response.json()["code"], "QUALITY_MODEL_UNAVAILABLE")
            self.post(f"revisions/{self.revision.pk}/assessment-jobs/", {}, 503)
        self.assertFalse(AssessmentJob.objects.exists())
        self.assertFalse(Assessment.objects.exists())

    def test_status_metadata_only_and_dependencies_missing(self):
        with patch("consultation_quality.inference.importlib.util.find_spec", return_value=None):
            self.assertEqual(status()["code"], "MODEL_DEPENDENCIES_MISSING")
        with patch("consultation_quality.inference.importlib.util.find_spec", return_value=object()), patch("consultation_quality.inference.LocalProvider.predict", side_effect=AssertionError("must not load")):
            self.assertTrue(status()["available"])

    def test_manifest_rejects_traversal_unapproved_and_missing_files(self):
        self.spec["approved_for_use"] = False
        self.write_spec()
        self.assertEqual(status()["code"], "MODEL_NOT_APPROVED")
        self.spec["approved_for_use"] = True
        self.spec["files"]["../private"] = "a" * 64
        self.write_spec()
        self.assertEqual(status()["code"], "MODEL_MANIFEST_INVALID")
        del self.spec["files"]["../private"]
        self.write_spec()
        (self.root / "quality.safetensors").unlink()
        self.assertEqual(status()["code"], "MODEL_MANIFEST_INVALID")

    def test_duplicate_requests_reuse_one_job(self):
        key = str(uuid.uuid4())
        first, second = self.enqueue(key=key), self.enqueue(key=key)
        third = self.enqueue()
        self.assertEqual(first["id"], second["id"])
        self.assertEqual(first["id"], third["id"])
        self.assertEqual(AssessmentJob.objects.count(), 1)
        self.assertFalse(Assessment.objects.exists())

    def test_reusing_key_for_other_revision_conflicts(self):
        key = str(uuid.uuid4())
        self.enqueue(key=key)
        self.enqueue(self.make_revision(), key, 409)

    def test_permissions_and_shared_conversation_do_not_expose_other_jobs(self):
        first = self.enqueue()
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(f"/api/quality/assessment-jobs/{first['id']}/").status_code, 404)
        self.conversation.members.add(self.other)
        payload = self.client.get(f"/api/quality/revisions/{self.revision.pk}/assessment-jobs/").json()
        self.assertEqual(payload["items"], [])
        self.client.force_login(self.reviewer)
        self.assertEqual(self.client.get(f"/api/quality/assessment-jobs/{first['id']}/").status_code, 200)

    def test_enqueue_requires_sealed_reviewed_revision_and_approved_matching_rubric(self):
        Revision.objects.filter(pk=self.revision.pk).update(status="draft")
        self.enqueue(expected=409)
        Revision.objects.filter(pk=self.revision.pk).update(status="sealed", roles_confirmed=False)
        self.enqueue(expected=422)
        Revision.objects.filter(pk=self.revision.pk).update(roles_confirmed=True)
        self.spec["rubric_hash"] = "d" * 64
        self.write_spec()
        self.enqueue(expected=409)
        self.spec["rubric_hash"] = digest(definitions(self.rubric.criteria_json))
        self.write_spec()
        self.rubric.status = "draft"
        self.rubric.save()
        self.enqueue(expected=422)
        self.assertFalse(AssessmentJob.objects.exists())

    @override_settings(QUALITY_QUEUE_LIMIT=1)
    def test_queue_limit(self):
        self.enqueue()
        self.enqueue(self.make_revision(), expected=429)

    def test_worker_slot_limits_concurrency_and_progress(self):
        self.enqueue()
        self.enqueue(self.make_revision())
        first = claim_job()
        self.assertIsNotNone(first)
        self.assertIsNone(claim_job())
        fail_job(*first, "JOB_TIMEOUT")
        self.assertIsNotNone(claim_job())

    def test_worker_persists_only_reviewable_model_snapshot(self):
        self.enqueue()
        job = self.run_job()
        self.assertEqual(job.status, "succeeded")
        item = job.assessment
        self.assertEqual(item.source, "model")
        self.assertEqual(item.status, "needs_review")
        self.assertIsNone(item.total_score)
        self.assertIsNone(item.author)
        self.assertFalse(item.inference_metadata["evidence_verified"])
        self.assertEqual(item.rating_rows.count(), 5)
        self.assertAlmostEqual(item.rating_rows.first().confidence, .8)
        self.assertEqual(job.total_windows, 2)
        self.assertIsNone(QualityWorkerSlot.objects.get(pk=1).token)
        self.assertEqual(self.client.get(f"/api/quality/assessments/{item.pk}/").status_code, 200)
        self.assertEqual(len(self.client.get(f"/api/quality/revisions/{self.revision.pk}/assessments/").json()["items"]), 1)

    def test_low_confidence_mask_and_no_generated_evidence(self):
        result = deepcopy(self.result)
        result["probabilities"]["opening"] = [.3, .35, .35]
        ratings, metadata = normalize_output(result, self.spec, self.turns, self.rubric.criteria_json)
        self.assertIsNone(ratings[0]["score"])
        self.assertTrue(ratings[0]["not_assessable_reason"])
        self.assertTrue(metadata["review_required"])
        result["evidence"] = {"opening": ["foreign"]}
        with self.assertRaises(InferenceError):
            normalize_output(result, self.spec, self.turns, self.rubric.criteria_json)

    def test_invalid_probabilities_do_not_create_assessment(self):
        self.enqueue()
        bad = deepcopy(self.result)
        bad["probabilities"]["opening"] = [float("nan"), 0, 1]
        job = self.run_job(bad)
        self.assertEqual(job.error_code, "MODEL_OUTPUT_INVALID")
        self.assertEqual(job.status, "failed")
        self.assertFalse(Assessment.objects.exists())

    def test_inference_load_failure_and_unknown_exception_are_sanitized(self):
        self.enqueue()
        job = self.run_job(error=InferenceError("MODEL_LOAD_FAILED"))
        self.assertEqual(job.error_code, "MODEL_LOAD_FAILED")
        self.enqueue()
        job = self.run_job(error=RuntimeError("SECRET TRANSCRIPT AND PRIVATE PATH"))
        response = self.client.get(f"/api/quality/assessment-jobs/{job.pk}/")
        self.assertNotIn("SECRET", str(response.content))
        self.assertEqual(job.error_code, "MODEL_INFERENCE_FAILED")
        self.assertFalse(Assessment.objects.exists())

    def test_changed_manifest_and_revoked_access_fail_before_inference(self):
        self.enqueue()
        self.spec["model_version"] = "changed"
        self.write_spec()
        self.assertEqual(self.run_job().error_code, "MODEL_CHANGED")
        self.enqueue()
        get_user_model().objects.filter(pk=self.user.pk).update(is_active=False)
        self.assertEqual(self.run_job().error_code, "ACCESS_REVOKED")

    def test_lease_recovery_and_stale_worker_cannot_publish(self):
        self.enqueue()
        old = claim_job()
        QualityWorkerSlot.objects.filter(pk=1).update(lease_until=timezone.now() - timedelta(seconds=1))
        self.assertIsNone(claim_job())
        job = AssessmentJob.objects.get(pk=old[0])
        self.assertEqual(job.status, "failed")
        self.assertEqual(job.error_code, "WORKER_INTERRUPTED")
        execute_job(*old)
        self.assertFalse(Assessment.objects.exists())

    def test_full_tail_coverage_and_limit_no_silent_truncation(self):
        ids = list(range(101))
        windows = token_windows(ids, 24, 6, 20)
        self.assertEqual(windows[-1][-1], 100)
        self.assertEqual(set(x for window in windows for x in window), set(ids))
        with self.assertRaises(InferenceError) as raised:
            token_windows(ids, 24, 6, 2)
        self.assertEqual(raised.exception.code, "INPUT_TOO_LARGE")

    def test_large_revision_rejected_before_queueing(self):
        turns = [{"id": str(i), "role": "consultant", "text": "x" * 10000} for i in range(21)]
        revision = Revision.objects.create(conversation=self.conversation, utterances=turns, roles_confirmed=True, transcript_reviewed=True, status="sealed")
        self.enqueue(revision, expected=413)
        self.assertFalse(AssessmentJob.objects.exists())

    def test_worker_timeout_terminates_process_and_marks_failed(self):
        self.enqueue()
        with patch("consultation_quality.management.commands.run_quality_worker.multiprocessing.get_context") as context:
            process = context.return_value.Process.return_value
            process.is_alive.side_effect = [True, False]
            call_command("run_quality_worker", once=True, stdout=StringIO())
            process.terminate.assert_called_once()
        job = AssessmentJob.objects.get()
        self.assertEqual(job.error_code, "JOB_TIMEOUT")
        self.assertEqual(job.status, "failed")
        self.assertFalse(Assessment.objects.exists())

    def test_progress_counts_are_saved_before_completion(self):
        self.enqueue()
        claimed = claim_job()

        def predict(turns, progress):
            progress(0, 2)
            progress(1, 2)
            running = AssessmentJob.objects.get(pk=claimed[0])
            self.assertEqual(running.status, "running")
            self.assertEqual((running.completed_windows, running.total_windows), (1, 2))
            return self.result

        with patch("consultation_quality.jobs.LocalProvider.predict", side_effect=predict):
            execute_job(*claimed)
        self.assertEqual(AssessmentJob.objects.get(pk=claimed[0]).status, "succeeded")

    def test_access_revoked_during_inference_prevents_publication(self):
        self.enqueue()
        claimed = claim_job()

        def predict(turns, progress):
            get_user_model().objects.filter(pk=self.user.pk).update(is_active=False)
            return self.result

        with patch("consultation_quality.jobs.LocalProvider.predict", side_effect=predict):
            execute_job(*claimed)
        job = AssessmentJob.objects.get(pk=claimed[0])
        self.assertEqual(job.status, "failed")
        self.assertEqual(job.error_code, "ACCESS_REVOKED")
        self.assertFalse(Assessment.objects.exists())

    def test_manual_copy_and_completion_preserve_ai_original(self):
        self.enqueue()
        item = self.run_job().assessment
        original = deepcopy(item.ratings)
        copied = self.post(f"assessments/{item.pk}/manual-copy/", {}, 201)
        self.assertEqual(copied["source"], "manual")
        self.assertEqual(copied["supersedes_id"], str(item.pk))
        self.assertEqual(copied["inference_metadata"], {})
        rows = copied["ratings"]
        for r in rows:
            r["evidence"]["utterance_ids"] = ["one"]
        completed = self.post(f"revisions/{self.revision.pk}/assessments/", {"rubric_id": str(self.rubric.pk), "status": "needs_review", "ratings": rows, "supersedes_id": copied["id"]}, 201)
        self.assertEqual(completed["total_score"], 100)
        item.refresh_from_db()
        self.assertEqual(item.ratings, original)
        self.assertEqual(item.status, "needs_review")
        self.client.force_login(self.reviewer)
        self.post(f"assessments/{item.pk}/approve/", {"note": "Do not approve AI directly"}, 422)
        self.post(f"assessments/{completed['id']}/approve/", {"note": "Fixture reviewed manually"}, 200)
