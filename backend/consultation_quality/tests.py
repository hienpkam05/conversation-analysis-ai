from django.test import TestCase
from tempfile import TemporaryDirectory
from pathlib import Path

from .models import Assessment, AudioSample, Conversation, Revision
from .services import InputError, RUBRIC, transcript_review_flags, validate_ratings, validate_utterances


class QualityTests(TestCase):
    def setUp(self):
        from django.contrib.auth import get_user_model
        self.user = get_user_model().objects.create_superuser(username="test-reviewer", password="test-only-password")
        self.client.force_login(self.user)
        self.turns = validate_utterances([
            {"id": "one", "role": "consultant", "text": "Chào chị, em tư vấn công việc."},
            {"id": "two", "role": "candidate", "text": "Chị tìm việc gần nhà."},
        ])

    def ratings(self, score=2):
        return [{"criterion_code": x["code"], "score": score,
                 "evidence": {"kind": "quote", "utterance_ids": ["one"]}}
                for x in RUBRIC["criteria"]]

    def test_total_and_missing_data(self):
        self.assertEqual(validate_ratings(self.ratings(), self.turns)[1], 100)
        self.assertEqual(validate_ratings(self.ratings(0), self.turns)[1], 0)
        rows = self.ratings()
        rows[0].update(score=None, not_assessable_reason="Bản ghi bị cắt.")
        self.assertIsNone(validate_ratings(rows, self.turns)[1])

    def test_suspicious_asr_is_flagged_not_deleted(self):
        turns = validate_utterances([{"id": "suspect", "text": "Hãy đăng ký kênh lalaschool"}])
        flags = transcript_review_flags(turns, [])
        self.assertEqual(flags[0]["utterance_id"], "suspect")
        self.assertEqual(turns[0]["text"], "Hãy đăng ký kênh lalaschool")
        corrected = validate_utterances([{"id": "suspect", "text": "Chào chị, em gọi tư vấn."}])
        self.assertEqual(transcript_review_flags(corrected, [{"id": "suspect", "text": "lời cũ", "avg_logprob": -2}]), [])

    def test_reject_foreign_evidence_and_wrong_role(self):
        for key in ("foreign", "two"):
            rows = self.ratings()
            rows[0]["evidence"]["utterance_ids"] = [key]
            with self.assertRaises(InputError):
                validate_ratings(rows, self.turns)

    def test_absence_requires_explanation_and_zero(self):
        rows = self.ratings()
        rows[0]["evidence"]["kind"] = "absence"
        with self.assertRaises(InputError):
            validate_ratings(rows, self.turns)
        rows[0].update(score=0, comment="Không thấy giới thiệu trong toàn bộ bản ghi.")
        self.assertEqual(validate_ratings(rows, self.turns)[1], 80)

    def test_reject_boolean_score_and_missing_reason(self):
        for value in (True, None, 3):
            rows = self.ratings()
            rows[0]["score"] = value
            with self.assertRaises(InputError):
                validate_ratings(rows, self.turns)

    def test_invalid_turns(self):
        with self.assertRaises(InputError):
            validate_utterances([{"id": "a", "text": "A"}, {"id": "a", "text": "B"}])
        with self.assertRaises(InputError):
            validate_utterances([{"text": "A", "start_seconds": 10, "end_seconds": 1}])

    def create_conversation(self):
        response = self.client.post("/api/quality/conversations/", {
            "title": "Cuộc gọi thử", "utterances": self.turns, "roles_confirmed": True,
        }, content_type="application/json")
        self.assertEqual(response.status_code, 201)
        return response.json()

    def test_save_and_reopen_preserves_snapshot(self):
        revision = self.create_conversation()
        path = f"/api/quality/revisions/{revision['id']}/assessments/"
        saved = self.client.post(path, {"rubric_version": RUBRIC["version"], "ratings": self.ratings()}, content_type="application/json")
        self.assertEqual(saved.status_code, 201)
        self.assertEqual(saved.json()["total_score"], 100)
        self.assertEqual(self.client.get(path).json()["items"][0]["revision"]["utterances"], self.turns)
        self.assertEqual(self.client.put(path, {}, content_type="application/json").status_code, 405)
        self.assertEqual(Assessment.objects.count(), 1)

    def test_rubric_change_preserves_old_assessment_and_rejects_stale_submission(self):
        from copy import deepcopy
        revision = self.create_conversation()
        old_rubric = deepcopy(RUBRIC)
        old_rubric["version"] = "quality-draft-v1"
        old = Assessment.objects.create(revision_id=revision["id"], rubric=old_rubric,
            ratings=self.ratings(), total_score=100)
        old.rubric_version.status = "retired"
        old.rubric_version.save()
        path = f"/api/quality/revisions/{revision['id']}/assessments/"
        response = self.client.post(path, {"rubric_version": "quality-draft-v1", "ratings": self.ratings()}, content_type="application/json")
        self.assertEqual(response.status_code, 422)
        response = self.client.post(path, {"rubric_version": RUBRIC["version"], "ratings": self.ratings()}, content_type="application/json")
        self.assertEqual(response.status_code, 201)
        old.refresh_from_db()
        self.assertEqual(old.rubric["version"], "quality-draft-v1")
        versions = {item["rubric"]["version"] for item in self.client.get(path).json()["items"]}
        self.assertEqual(versions, {"quality-draft-v1", RUBRIC["version"]})

    def test_unknown_roles_cannot_be_confirmed(self):
        self.turns[0]["role"] = "unknown"
        response = self.client.post("/api/quality/conversations/", {"utterances": self.turns, "roles_confirmed": True}, content_type="application/json")
        self.assertEqual(response.status_code, 422)

    def test_missing_model_never_creates_assessment(self):
        revision = self.create_conversation()
        response = self.client.post(f"/api/quality/revisions/{revision['id']}/assessment-jobs/", {}, content_type="application/json")
        self.assertEqual(response.status_code, 503)
        self.assertEqual(Assessment.objects.count(), 0)

    def test_bad_json(self):
        for value in ("[]", "{oops"):
            self.assertEqual(self.client.post("/api/quality/conversations/", value, content_type="application/json").status_code, 422)

    def test_revision_keeps_history_and_detects_conflict(self):
        original = self.create_conversation()
        path = f"/api/quality/conversations/{original['conversation_id']}/revisions/"
        modified = [dict(t) for t in self.turns]
        modified[0]["text"] = "Bản đã sửa"
        payload = {"utterances": modified, "expected_revision_id": original["id"]}
        response = self.client.post(path, payload, content_type="application/json")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(Revision.objects.get(id=original["id"]).utterances[0]["text"], self.turns[0]["text"])
        self.assertEqual(self.client.post(path, payload, content_type="application/json").status_code, 409)
        self.assertEqual(Conversation.objects.count(), 1)

    def test_partial_draft_allowed_but_completion_requires_review(self):
        revision = self.create_conversation()
        path = f"/api/quality/revisions/{revision['id']}/assessments/"
        rows = self.ratings()
        rows[0]["score"] = None
        response = self.client.post(path, {"rubric_version": RUBRIC["version"], "ratings": rows, "status": "draft"}, content_type="application/json")
        self.assertEqual(response.status_code, 201)
        self.assertIsNone(response.json()["total_score"])
        response = self.client.post(path, {"rubric_version": RUBRIC["version"], "ratings": self.ratings(), "status": "needs_review"}, content_type="application/json")
        self.assertEqual(response.status_code, 422)
        Revision.objects.filter(id=revision["id"]).update(transcript_reviewed=True)
        response = self.client.post(path, {"rubric_version": RUBRIC["version"], "ratings": self.ratings(), "status": "needs_review"}, content_type="application/json")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["status"], "needs_review")

    def test_draft_keeps_scores_while_evidence_is_being_corrected(self):
        rows = self.ratings()
        rows[0]["evidence"]["utterance_ids"] = []
        result, total = validate_ratings(rows, self.turns, allow_incomplete=True)
        self.assertEqual(result[0]["score"], 2)
        self.assertIsNone(total)
        with self.assertRaises(InputError):
            validate_ratings(rows, self.turns)
        rows[0]["evidence"]["utterance_ids"] = ["foreign"]
        with self.assertRaises(InputError):
            validate_ratings(rows, self.turns, allow_incomplete=True)

    def test_cannot_approve_from_client(self):
        revision = self.create_conversation()
        response = self.client.post(f"/api/quality/revisions/{revision['id']}/assessments/", {
            "rubric_version": RUBRIC["version"], "ratings": self.ratings(), "status": "approved"}, content_type="application/json")
        self.assertEqual(response.status_code, 422)
        self.assertFalse(Assessment.objects.exists())

    def test_audio_range_and_manifest_does_not_expose_path(self):
        revision = self.create_conversation()
        with TemporaryDirectory() as folder:
            path = Path(folder) / "audio.mp3"
            path.write_bytes(b"0123456789")
            sample = AudioSample.objects.create(call_id="pilot_1", source_path=str(path), duration_seconds=1,
                conversation_id=revision["conversation_id"])
            payload = self.client.get("/api/quality/samples/").json()
            self.assertNotIn("source_path", payload["items"][0])
            url = f"/api/quality/samples/{sample.id}/audio/"
            response = self.client.get(url, HTTP_RANGE="bytes=2-5")
            self.assertEqual(response.status_code, 206)
            self.assertEqual(b"".join(response.streaming_content), b"2345")
            self.assertEqual(response["Content-Range"], "bytes 2-5/10")
            self.assertEqual(self.client.get(url, HTTP_RANGE="bytes=100-").status_code, 416)
            response = self.client.get(url, HTTP_RANGE="bytes=-3")
            self.assertEqual(b"".join(response.streaming_content), b"789")

    def test_register_manifest_is_idempotent(self):
        from django.core.management import call_command
        import json
        with TemporaryDirectory() as folder:
            path = Path(folder) / "audio.mp3"
            path.write_bytes(b"audio")
            manifest = Path(folder) / "pilot.json"
            manifest.write_text(json.dumps([{"call_id": "pilot_1", "source_path": str(path), "duration_seconds": 1}]))
            call_command("prepare_quality_pilot", str(manifest), register_only=True)
            call_command("prepare_quality_pilot", str(manifest), register_only=True)
            self.assertEqual(AudioSample.objects.count(), 1)
            self.assertEqual(Conversation.objects.count(), 1)

    def test_sample_disposition_is_human_review_not_training_approval(self):
        revision = self.create_conversation()
        sample = AudioSample.objects.create(call_id="pilot_1", source_path="unused.mp3", duration_seconds=1,
            conversation_id=revision["conversation_id"])
        url = f"/api/quality/samples/{sample.id}/review/"
        self.assertEqual(self.client.post(url, {"disposition": "no_speech"}, content_type="application/json").status_code, 422)
        response = self.client.post(url, {"disposition": "no_speech", "note": "Đã nghe, không có lời."}, content_type="application/json")
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["approved_for_training"])
        self.assertFalse(Assessment.objects.exists())
        Revision.objects.filter(id=revision["id"]).update(transcript_reviewed=True)
        response = self.client.post(f"/api/quality/revisions/{revision['id']}/assessments/", {
            "rubric_version": RUBRIC["version"], "ratings": self.ratings(), "status": "needs_review"}, content_type="application/json")
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json()["error"]["code"], "AUDIO_NOT_ASSESSABLE")

    def test_transcript_export_does_not_export_training_labels_or_paths(self):
        from django.core.management import call_command
        import json
        revision = self.create_conversation()
        AudioSample.objects.create(call_id="pilot_1", source_path="private-source.mp3", duration_seconds=1,
            conversation_id=revision["conversation_id"])
        with TemporaryDirectory() as folder:
            output = Path(folder) / "review.json"
            call_command("export_quality_transcripts", str(output))
            data = json.loads(output.read_text(encoding="utf-8"))
            self.assertFalse(data["approved_for_training"])
            self.assertEqual(data["purpose"], "human_review_only")
            self.assertNotIn("source_path", data["items"][0])
            self.assertNotIn("ratings", data["items"][0])
            self.assertEqual(data["items"][0]["utterances"], self.turns)
