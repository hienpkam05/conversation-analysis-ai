from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.exceptions import ValidationError
from django.test import Client, TestCase

from consultation_quality.models import AudioSample, Conversation, Revision
from conversation_followup.models import Appointment
from .models import StatusDecision
from .services import suggest


def turn(text, role="candidate", key="candidate", **kwargs):
    return {"id": key, "position": 1, "role": role, "text": text, "start_seconds": None, "end_seconds": None, **kwargs}


class StatusRulesTests(TestCase):
    def test_five_explicit_labels(self):
        samples = {
            "Tôi quan tâm công việc này.": "interested",
            "Cho chị hỏi mức lương thế nào?": "needs_information",
            "Em gọi lại cho chị sau nhé.": "callback_requested",
            "Tôi đồng ý tham gia phỏng vấn.": "interview_agreed",
            "Chị không có nhu cầu nữa.": "declined",
            "Em không đồng ý phỏng vấn.": "declined",
        }
        for text, expected in samples.items():
            with self.subTest(text=text):
                value = suggest([turn(text)])
                self.assertEqual(value["label"], expected)
                self.assertEqual(value["evidence_ids"], ["candidate"])
                self.assertIsNone(value["metadata"]["confidence"])

    def test_never_treats_questions_negation_uncertainty_or_reported_speech_as_agreement(self):
        for text in ["Vâng.", "Dạ.", "Nếu tôi đồng ý phỏng vấn thì sao?", "Tôi chưa đồng ý phỏng vấn.",
                "Tôi không chắc tôi đồng ý phỏng vấn.", "Tôi đồng ý phỏng vấn được không?",
                'Tư vấn nói rằng "tôi đồng ý phỏng vấn".', "Tôi đồng ý phỏng vấn nhưng cần hỏi lại gia đình."]:
            with self.subTest(text=text):
                self.assertEqual(suggest([turn(text)])["label"], "unknown")

    def test_only_clear_candidate_speech_counts(self):
        for row in [turn("Tôi đồng ý phỏng vấn.", role="consultant"), turn("Tôi đồng ý phỏng vấn.", role="unknown"), turn("Tôi đồng ý phỏng vấn.", unclear=True)]:
            self.assertEqual(suggest([row])["label"], "unknown")

    def test_conflicting_statements_abstain_instead_of_picking_last_keyword(self):
        value = suggest([turn("Tôi đồng ý phỏng vấn.", key="a"), turn("Tôi không có nhu cầu nữa.", key="b")])
        self.assertEqual(value["label"], "unknown")
        self.assertEqual(value["evidence_ids"], ["a", "b"])
        value = suggest([turn("Tôi đồng ý phỏng vấn.", key="a"), turn("Nhưng tôi chưa chắc có đi phỏng vấn.", key="b")])
        self.assertEqual(value["label"], "unknown")

    def test_large_transcript_caps_evidence_without_fake_probability(self):
        value = suggest([turn("Tôi quan tâm công việc này.", key=str(i)) for i in range(205)])
        self.assertEqual(len(value["evidence_ids"]), 200)
        self.assertFalse(value["metadata"]["model_available"])


class StatusAPITests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user("status-owner")
        self.other = get_user_model().objects.create_user("status-other")
        self.reviewer = get_user_model().objects.create_superuser("status-reviewer")
        for user in [self.user, self.other]:
            user.user_permissions.add(Permission.objects.get(codename="annotate_quality"))
        self.client.force_login(self.user)
        self.conversation = Conversation.objects.create(title="Status test", owner=self.user)
        self.turns = [turn("Em có thể tham gia phỏng vấn chứ?", role="consultant", key="consultant"), turn("Tôi đồng ý phỏng vấn.")]
        self.revision = Revision.objects.create(conversation=self.conversation, utterances=self.turns, roles_confirmed=True, transcript_reviewed=True)
        self.base = f"/api/candidate-status/revisions/{self.revision.pk}/decisions/"

    def create(self, data=None, status=201):
        response = self.client.post(self.base, data or {"source": "rules"}, content_type="application/json")
        self.assertEqual(response.status_code, status, response.content)
        return response.json()

    def confirm(self, row, status=200, **kwargs):
        response = self.client.post(f"/api/candidate-status/decisions/{row['id']}/confirm/",
            {"expected_version": row["version"], "confirmed_content": True, **kwargs}, content_type="application/json")
        self.assertEqual(response.status_code, status, response.content)
        return response.json()

    def test_config_and_rules_snapshot_no_side_effects(self):
        config = self.client.get("/api/candidate-status/config/").json()
        self.assertFalse(config["model_available"])
        self.assertEqual(len(config["labels"]), 6)
        row = self.create()
        self.assertEqual(row["source"], "rules")
        self.assertEqual(row["label"], "interview_agreed")
        self.assertEqual(row["utterances"], self.turns)
        self.assertIsNone(self.client.get(self.base).json()["current_confirmed"])
        self.assertFalse(Appointment.objects.exists())

    def test_manual_copy_is_separate_immutable_record(self):
        original = self.create()
        manual = self.create({"source": "manual", "label": "unknown", "evidence_ids": ["candidate"], "rationale": "Cần đối chiếu audio.", "supersedes_id": original["id"]})
        self.assertEqual(manual["supersedes_id"], original["id"])
        old = StatusDecision.objects.get(pk=original["id"])
        self.assertEqual(old.label, "interview_agreed")
        old.label = "declined"
        with self.assertRaises(ValidationError):
            old.save()
        self.assertEqual(self.client.put(self.base, {}, content_type="application/json").status_code, 405)

    def test_manual_validation_and_evidence(self):
        payload = {"source": "manual", "label": "interested", "evidence_ids": ["candidate"], "rationale": "Đối chiếu."}
        for changes in [{"label": []}, {"label": "fake"}, {"evidence_ids": []}, {"evidence_ids": ["consultant"]},
                {"evidence_ids": ["foreign"]}, {"evidence_ids": ["candidate", "candidate"]}, {"rationale": "x" * 5001},
                {"source": "model"}, {"evidence_ids": [False]}]:
            self.create(dict(payload, **changes), 422)
        self.create({"source": "manual", "label": "unknown", "evidence_ids": [], "rationale": ""}, 422)
        self.create({"source": "manual", "label": "unknown", "evidence_ids": [], "rationale": "Chưa có lời nói đủ rõ."})

    def test_confirmation_requires_consent_and_strict_version(self):
        row = self.create()
        self.confirm(row, 422, confirmed_content=False)
        self.confirm(row, 409, expected_version=True)
        confirmed = self.confirm(row)
        self.assertEqual(confirmed["status"], "confirmed")
        self.confirm(row, 409)
        self.assertEqual(self.confirm(confirmed)["version"], 2)
        self.revision.refresh_from_db()
        self.assertEqual(self.revision.status, "sealed")
        self.assertEqual(self.client.get(self.base).json()["current_confirmed"]["id"], row["id"])

    def test_unreviewed_transcript_and_roles_block_confirmation(self):
        for field in ["transcript_reviewed", "roles_confirmed"]:
            Revision.objects.filter(pk=self.revision.pk).update(**{field: False})
            row = self.create()
            self.confirm(row, 422)
            Revision.objects.filter(pk=self.revision.pk).update(**{field: True})

    def test_unknown_role_blocks_confirmation_even_when_flags_true(self):
        self.revision.utterances[0]["role"] = "unknown"
        self.revision.save()
        self.confirm(self.create(), 422)

    def test_no_speech_audio_blocks_confirmation(self):
        AudioSample.objects.create(call_id="status-test-audio", source_path="unused.mp3", duration_seconds=1, conversation=self.conversation, review_disposition="no_speech")
        self.confirm(self.create(), 422)

    def test_new_revision_and_inplace_edit_make_snapshot_stale(self):
        row = self.create()
        self.revision.utterances[1]["text"] = "Tôi không có nhu cầu nữa."
        self.revision.save()
        self.confirm(row, 409)
        self.assertTrue(self.client.get(self.base).json()["items"][0]["stale"])
        fresh = self.create()
        Revision.objects.create(conversation=self.conversation, utterances=self.turns, roles_confirmed=True, transcript_reviewed=True)
        self.confirm(fresh, 409)

    def test_new_draft_does_not_replace_confirmed_state(self):
        original = self.confirm(self.create())
        draft = self.create({"source": "manual", "label": "unknown", "evidence_ids": [], "rationale": "Cần nghe lại.", "supersedes_id": original["id"]})
        self.assertEqual(self.client.get(self.base).json()["current_confirmed"]["id"], original["id"])
        self.confirm(draft)
        self.assertEqual(self.client.get(self.base).json()["current_confirmed"]["id"], draft["id"])
        old = StatusDecision.objects.get(pk=original["id"])
        old.status = "draft"
        with self.assertRaises(ValidationError):
            old.save()

    def test_current_state_is_absent_when_new_revision_created(self):
        self.confirm(self.create())
        Revision.objects.create(conversation=self.conversation, utterances=self.turns)
        self.assertIsNone(self.client.get(self.base).json()["current_confirmed"])

    def test_auth_scope_shared_read_and_confirmation_permission(self):
        row = self.create()
        self.client.logout()
        self.assertEqual(self.client.get(self.base).status_code, 401)
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(self.base).status_code, 404)
        self.confirm(row, 404)
        self.conversation.members.add(self.other)
        self.assertEqual(self.client.get(self.base).status_code, 200)
        self.confirm(row, 403)
        self.client.force_login(self.reviewer)
        self.confirm(row)

    def test_unprivileged_user_cannot_access(self):
        user = get_user_model().objects.create_user("status-no-permission")
        self.client.force_login(user)
        self.assertEqual(self.client.get("/api/candidate-status/config/").status_code, 403)

    def test_supersedes_must_belong_to_same_revision(self):
        row = self.create()
        revision = Revision.objects.create(conversation=self.conversation, utterances=self.turns)
        response = self.client.post(f"/api/candidate-status/revisions/{revision.pk}/decisions/", {
            "source": "manual", "label": "unknown", "evidence_ids": [], "rationale": "Chưa rõ.", "supersedes_id": row["id"]}, content_type="application/json")
        self.assertEqual(response.status_code, 404)

    def test_csrf_required_for_creation_and_confirmation(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.user)
        self.assertEqual(client.post(self.base, {"source": "rules"}, content_type="application/json").status_code, 403)
        row = self.create()
        self.assertEqual(client.post(f"/api/candidate-status/decisions/{row['id']}/confirm/", {}, content_type="application/json").status_code, 403)
