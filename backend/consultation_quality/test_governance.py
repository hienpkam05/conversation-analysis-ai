from copy import deepcopy
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.exceptions import ValidationError
from django.test import Client, TestCase, override_settings

from .models import Assessment, AudioSample, Conversation, Evidence, PilotResolution, Revision, RubricVersion
from .rubric import RUBRIC


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class GovernanceTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.reviewer = User.objects.create_user("reviewer", password="test-password")
        self.a = User.objects.create_user("annotator-a", password="test-password")
        self.b = User.objects.create_user("annotator-b", password="test-password")
        self.outsider = User.objects.create_user("outsider", password="test-password")
        annotate = Permission.objects.get(codename="annotate_quality")
        review = Permission.objects.get(codename="review_quality")
        for user in [self.a, self.b, self.outsider]:
            user.user_permissions.add(annotate)
        self.reviewer.user_permissions.add(review)
        self.client.force_login(self.reviewer)
        self.rubric = RubricVersion.objects.get(version=RUBRIC["version"])
        self.turns = [{"id": "one", "position": 1, "role": "consultant", "text": "Xin chào, em gọi tư vấn công việc.", "start_seconds": None, "end_seconds": None}]

    def post(self, url, data, expected=201):
        response = self.client.post("/api/quality/" + url, data, content_type="application/json")
        self.assertEqual(response.status_code, expected, response.content)
        return response.json()

    def sample(self, title="pilot"):
        conversation = Conversation.objects.create(title=title, owner=self.a)
        conversation.members.add(self.b)
        revision = Revision.objects.create(conversation=conversation, utterances=self.turns, roles_confirmed=True, transcript_reviewed=True)
        AudioSample.objects.create(conversation=conversation, call_id=title, source_path="private.mp3", duration_seconds=60, status="ready", review_disposition="usable")
        return revision

    def ratings(self, score=2):
        return [{"criterion_code": c["code"], "score": score, "comment": "Đã đối chiếu trong tình huống kiểm thử.",
                 "evidence": {"kind": "quote", "utterance_ids": ["one"]}} for c in RUBRIC["criteria"]]

    def pair(self, revision):
        ids = []
        for user, score in [(self.a, 2), (self.b, 1)]:
            self.client.force_login(user)
            result = self.post(f"revisions/{revision.id}/assessments/", {"rubric_version": RUBRIC["version"], "ratings": self.ratings(score), "status": "needs_review"})
            ids.append(result["id"])
        self.client.force_login(self.reviewer)
        return ids

    def test_authentication_permissions_and_audio_access(self):
        revision = self.sample()
        sample = revision.conversation.audio_sample
        self.client.logout()
        for path in ["conversations/", "samples/", "rubrics/", f"samples/{sample.id}/audio/"]:
            self.assertEqual(self.client.get("/api/quality/" + path).status_code, 401)
        self.client.force_login(self.outsider)
        self.assertEqual(self.client.get(f"/api/quality/conversations/{revision.conversation_id}/").status_code, 404)
        self.assertEqual(self.client.get(f"/api/quality/samples/{sample.id}/audio/").status_code, 404)
        self.assertEqual(self.client.get("/api/quality/samples/").json()["items"], [])
        self.post("rubrics/", deepcopy(RUBRIC), 403)
        plain = get_user_model().objects.create_user("plain")
        self.client.force_login(plain)
        self.assertEqual(self.client.get("/api/quality/samples/").status_code, 403)

    def test_session_csrf_login_logout(self):
        client = Client(enforce_csrf_checks=True)
        token = client.get("/api/quality/session/").json()["csrf_token"]
        self.assertEqual(client.post("/api/quality/session/", {}).status_code, 403)
        response = client.post("/api/quality/session/", {"username": "annotator-a", "password": "test-password"},
            content_type="application/json", HTTP_X_CSRFTOKEN=token, HTTP_ORIGIN="http://127.0.0.1:5173")
        self.assertEqual(response.status_code, 200)
        token = response.json()["csrf_token"]
        self.assertFalse(response.json()["can_review"])
        self.assertEqual(client.delete("/api/quality/session/", "{}", content_type="application/json", HTTP_X_CSRFTOKEN=token).status_code, 200)
        self.assertEqual(client.get("/api/quality/samples/").status_code, 401)

    def test_blind_annotation_and_reviewer_history(self):
        revision = self.sample()
        pair = self.pair(revision)
        self.client.force_login(self.a)
        path = f"/api/quality/revisions/{revision.id}/assessments/"
        self.assertEqual(len(self.client.get(path).json()["items"]), 1)
        self.assertEqual(self.client.get(f"/api/quality/assessments/{pair[1]}/").status_code, 404)
        self.client.force_login(self.reviewer)
        self.assertEqual(len(self.client.get(path).json()["items"]), 2)

    def test_draft_edit_seal_and_copy_new_ids(self):
        revision = self.sample()
        path = f"/api/quality/revisions/{revision.id}/"
        payload = {"expected_content_hash": revision.content_hash, "utterances": [{"text": "Đã sửa", "role": "consultant"}]}
        self.assertEqual(self.client.put(path, payload, content_type="application/json").status_code, 200)
        self.assertEqual(self.client.put(path, payload, content_type="application/json").status_code, 409)
        self.post(f"revisions/{revision.id}/seal/", {}, 200)
        revision.refresh_from_db()
        self.assertEqual(revision.status, "sealed")
        self.assertEqual(self.client.put(path, payload, content_type="application/json").status_code, 409)
        revision.utterances = self.turns
        with self.assertRaises(ValidationError):
            revision.save()
        copied = self.post(f"conversations/{revision.conversation_id}/revisions/", {
            "expected_revision_id": str(revision.id), "utterances": self.turns})
        self.assertEqual(copied["revision_number"], 2)
        self.assertNotEqual(copied["utterances"][0]["id"], "one")
        self.assertEqual(Revision.objects.get(id=copied["id"]).turn_rows.count(), 1)

    def test_normalized_ratings_and_immutable_snapshot(self):
        revision = self.sample()
        a, _ = self.pair(revision)
        row = Assessment.objects.get(id=a)
        self.assertEqual(row.rating_rows.count(), 5)
        self.assertEqual(Evidence.objects.filter(rating__assessment=row).count(), 5)
        self.assertEqual(row.rubric_version_id, self.rubric.id)
        revision.refresh_from_db()
        self.assertEqual(revision.status, "sealed")
        row.ratings = self.ratings(0)
        with self.assertRaises(ValidationError):
            row.save()

    def test_rubric_validation_weighted_total_and_lock_after_use(self):
        data = deepcopy(RUBRIC)
        data["version"] = "weighted-v1"
        data["criteria"][0]["weight"] = 0.4
        data["criteria"][1]["weight"] = 0.2
        for c in data["criteria"][2:]:
            c["weight"] = 0.4 / 3
        new = self.post("rubrics/", data)
        revision = self.sample()
        rows = self.ratings(0)
        rows[0]["score"] = 2
        assessed = self.post(f"revisions/{revision.id}/assessments/", {"rubric_version": data["version"], "ratings": rows, "status": "needs_review"})
        self.assertEqual(assessed["total_score"], 40)
        path = f"/api/quality/rubrics/{new['id']}/"
        self.assertEqual(self.client.put(path, data, content_type="application/json").status_code, 409)
        data["version"] = "bad-weight"
        data["criteria"][0]["weight"] = 0.7
        self.post("rubrics/", data, 422)

    def test_pilot_requires_distinct_annotators_and_independent_adjudicator(self):
        revision = self.sample()
        pair = self.pair(revision)
        payload = {"assessment_ids": pair, "ratings": self.ratings(), "rationale": "Đã đối chiếu cả hai bản."}
        self.client.force_login(self.a)
        self.post("pilot-resolutions/", payload, 403)
        self.a.user_permissions.add(Permission.objects.get(codename="review_quality"))
        self.client.force_login(self.a)
        self.post("pilot-resolutions/", payload, 403)
        self.client.force_login(self.reviewer)
        self.post("pilot-resolutions/", dict(payload, assessment_ids=[pair[0], pair[0]]), 422)
        self.post("pilot-resolutions/", payload)
        self.post("pilot-resolutions/", payload, 409)
        self.assertEqual(PilotResolution.objects.count(), 1)

    def test_rubric_approval_requires_three_calls_not_three_revisions(self):
        payload = {"confirm_business_rules": True, "note": "Xác nhận trong kiểm thử, không phải dữ liệu thật."}
        path = f"rubrics/{self.rubric.id}/approve/"
        self.post(path, payload, 422)
        for i in range(3):
            revision = self.sample(f"pilot-{i}")
            ids = self.pair(revision)
            self.post("pilot-resolutions/", {"assessment_ids": ids, "ratings": self.ratings(), "rationale": "Giải thích từng điểm theo bằng chứng kiểm thử."})
            if i < 2:
                self.post(path, payload, 422)
        self.post(path, dict(payload, confirm_business_rules=False), 422)
        result = self.post(path, payload, 200)
        self.assertEqual(result["status"], "approved")
        self.assertEqual(result["approved_by"], "reviewer")
        self.assertFalse(Assessment.objects.filter(status="approved").exists())
        resolved = PilotResolution.objects.first().resolved_assessment
        self.post(f"assessments/{resolved.id}/approve/", {"note": "Đã xác nhận nhãn sau khi chốt rubric."}, 200)
        self.assertEqual(Assessment.objects.filter(status="approved").count(), 1)

    def test_review_requires_approved_rubric_and_no_self_approval(self):
        revision = self.sample()
        ids = self.pair(revision)
        self.post(f"assessments/{ids[0]}/approve/", {"note": "kiểm thử"}, 422)
        self.rubric.status = "approved"
        self.rubric.save()
        self.post(f"assessments/{ids[0]}/approve/", {"note": "kiểm thử"}, 200)
        self.post(f"assessments/{ids[0]}/approve/", {"note": "lặp"}, 422)
        self.client.force_login(self.reviewer)
        own = self.post(f"revisions/{revision.id}/assessments/", {"rubric_version": RUBRIC["version"], "ratings": self.ratings(), "status": "needs_review"})
        self.post(f"assessments/{own['id']}/approve/", {"note": "tự duyệt"}, 403)

    def test_revision_and_rubric_mismatch_rejected(self):
        first, second = self.sample("pilot-one"), self.sample("pilot-two")
        a, _ = self.pair(first)
        b, _ = self.pair(second)
        self.post("pilot-resolutions/", {"assessment_ids": [a, b], "ratings": self.ratings(), "rationale": "khác revision"}, 422)
        self.assertFalse(PilotResolution.objects.exists())

    def test_pagination_and_bad_uuid_are_json_errors(self):
        self.sample()
        self.assertEqual(self.client.get("/api/quality/conversations/?offset=-1").status_code, 422)
        response = self.client.get("/api/quality/pilot-resolutions/?rubric_id=not-uuid")
        self.assertEqual(response.status_code, 422)
        self.assertIn("error", response.json())
