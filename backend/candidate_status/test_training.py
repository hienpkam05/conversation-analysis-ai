from copy import deepcopy
from io import StringIO
import json
from pathlib import Path
import tempfile
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings

from consultation_quality.models import Conversation, Revision
from consultation_quality.services import InputError
from consultation_quality.training_data import digest, fingerprint
from .dataset import SCHEMA, PREPROCESSING, eligible, export_dataset, split_dataset, validate_bundle
from .inference import model_status, read_manifest
from .metrics import CODES, probability_label, scores, select_threshold
from .ml import FORMAT, WINDOWING, file_hash, text_for, windows_for
from .models import LabelReview, StatusDecision, TaxonomyApproval
from .review import definitions
from . import tests as base_tests
from .tests import turn


class GovernanceTests(TestCase):
    setUp = base_tests.StatusAPITests.setUp
    create = base_tests.StatusAPITests.create
    confirm = base_tests.StatusAPITests.confirm

    def approve_taxonomy(self):
        self.client.force_login(self.reviewer)
        response = self.client.post("/api/candidate-status/taxonomy/approve/", {"definition_hash": digest(definitions()), "confirmed_definitions": True, "note": "Đã kiểm tra định nghĩa và ranh giới trên dữ liệu thử."}, content_type="application/json")
        self.assertEqual(response.status_code, 200, response.content)
        self.client.force_login(self.user)

    def manual(self, label="interested", supersedes=None):
        row = self.create({"source": "manual", "label": label, "evidence_ids": ["candidate"], "rationale": "Đối chiếu với lời ứng viên.", "supersedes_id": supersedes})
        return self.confirm(row)

    def review(self, row, status=201, verdict="approved"):
        response = self.client.post(f"/api/candidate-status/decisions/{row['id']}/review/", {"expected_version": row["version"], "verdict": verdict, "note": "Đã đọc nguồn và kiểm tra nhãn độc lập."}, content_type="application/json")
        self.assertEqual(response.status_code, status, response.content)
        return response.json()

    def test_taxonomy_never_auto_approved_and_reviewer_consent_hash_required(self):
        self.assertIsNone(self.client.get("/api/candidate-status/taxonomy/").json()["approval"])
        self.assertEqual(self.client.post("/api/candidate-status/taxonomy/approve/", {}, content_type="application/json").status_code, 403)
        self.client.force_login(self.reviewer)
        self.assertEqual(self.client.post("/api/candidate-status/taxonomy/approve/", {"note": "x"}, content_type="application/json").status_code, 422)
        self.approve_taxonomy()
        row = TaxonomyApproval.objects.get()
        row.note = "Không ghi đè"
        with self.assertRaises(ValidationError):
            row.save()

    def test_independent_review_required_and_rules_not_gold(self):
        self.approve_taxonomy()
        manual = self.manual()
        self.review(manual, 403)
        self.client.force_login(self.reviewer)
        self.review(manual)
        self.review(manual, 409)
        self.client.force_login(self.user)
        rules = self.confirm(self.create())
        self.client.force_login(self.reviewer)
        self.review(rules, 422)
        self.assertEqual(len(eligible()[0]), 1)

    def test_cannot_review_before_taxonomy_approval(self):
        manual = self.manual()
        self.client.force_login(self.reviewer)
        self.review(manual, 422)
        with self.assertRaises(InputError):
            export_dataset({str(self.conversation.pk): "group1"})

    def test_rejected_review_is_immutable_and_excluded(self):
        self.approve_taxonomy()
        manual = self.manual()
        self.client.force_login(self.reviewer)
        self.review(manual, verdict="rejected")
        row = LabelReview.objects.get()
        row.verdict = "approved"
        with self.assertRaises(ValidationError):
            row.save()
        self.assertEqual(eligible()[0], [])

    def test_conflicting_approved_labels_are_excluded_until_explicit_replacement(self):
        self.approve_taxonomy()
        first = self.manual()
        self.client.force_login(self.reviewer)
        self.review(first)
        self.client.force_login(self.user)
        second = self.manual("declined")
        self.assertEqual(eligible()[1].get("pending_conflicting_manual_label"), 1)
        self.client.force_login(self.reviewer)
        self.review(second)
        entries, excluded = eligible()
        self.assertEqual(entries, [])
        self.assertEqual(excluded["conflicting_approved_labels"], 1)
        self.client.force_login(self.user)
        replacement = self.manual("interested", second["id"])
        self.client.force_login(self.reviewer)
        self.review(replacement)
        self.assertEqual(len(eligible()[0]), 1)

    def test_export_requires_groups_redacts_and_does_not_include_authors(self):
        self.approve_taxonomy()
        manual = self.manual()
        self.client.force_login(self.reviewer)
        self.review(manual)
        with self.assertRaises(InputError):
            export_dataset({})
        payload = export_dataset({str(self.conversation.pk): "candidate-group"})
        self.assertEqual(payload["items"][0]["label"], "interested")
        self.assertNotIn(self.user.username, json.dumps(payload))
        self.assertTrue(payload["privacy_review_required"])

    def test_training_report_restricted(self):
        self.assertEqual(self.client.get("/api/candidate-status/training-status/").status_code, 403)
        self.client.force_login(self.reviewer)
        payload = self.client.get("/api/candidate-status/training-status/").json()
        self.assertEqual(payload["eligible"], 0)
        self.assertFalse(payload["taxonomy_approved"])

    def test_stale_review_and_changed_taxonomy_hash_rejected(self):
        self.approve_taxonomy()
        manual = self.manual()
        Revision.objects.create(conversation=self.conversation, utterances=self.turns, roles_confirmed=True, transcript_reviewed=True)
        self.client.force_login(self.reviewer)
        self.review(manual, 409)
        self.client.force_login(self.user)
        fresh = self.create()
        StatusDecision.objects.filter(pk=fresh["id"]).update(taxonomy_hash="0" * 64)
        self.confirm(fresh, 409)

    def test_model_unavailable_does_not_create_decision(self):
        with override_settings(STATUS_MODEL_DIR=""):
            payload = self.create({"source": "model"}, 422)
            self.assertEqual(payload["error"]["code"], "STATUS_MODEL_UNAVAILABLE")
        self.assertFalse(StatusDecision.objects.exists())

    def test_model_snapshot_changed_during_inference_not_saved(self):
        def fake_predict(turns):
            revision = Revision.objects.get(pk=self.revision.pk)
            revision.utterances[1]["text"] = "Đã thay đổi nguồn"
            revision.save()
            return {"label": "interested", "evidence_ids": [], "rationale": "Chưa có bằng chứng.", "metadata": {}}
        with patch("candidate_status.inference.predict", side_effect=fake_predict):
            self.create({"source": "model"}, 409)
        self.assertFalse(StatusDecision.objects.exists())

    def test_mock_model_prediction_is_draft_and_cannot_be_directly_confirmed(self):
        with patch("candidate_status.inference.predict", return_value={"label": "unknown", "evidence_ids": [], "rationale": "Chưa có bằng chứng.", "metadata": {"review_required": True}}):
            row = self.create({"source": "model"})
        self.assertEqual(row["source"], "model")
        self.assertEqual(row["status"], "draft")
        self.confirm(row, 422)


def payload_fixture():
    items = []
    for i in range(30):
        turns = [turn(f"Tôi đang trao đổi về công việc mã {i}.")]
        items.append({"conversation_id": digest(f"c{i}"), "group_id": digest(f"g{i}"), "decision_id": digest(f"d{i}"),
            "content_hash": fingerprint(turns), "utterances": turns, "label": CODES[i % len(CODES)], "evidence_ids": ["candidate"]})
    payload = {"schema": SCHEMA, "preprocessing": PREPROCESSING, "definitions": definitions(), "definition_hash": digest(definitions()), "items": items}
    payload["dataset_sha256"] = digest(payload)
    return payload


class TrainingToolsTests(TestCase):
    def split(self, payload=None):
        payload = payload or payload_fixture()
        return split_dataset(payload, payload["dataset_sha256"], "privacy-reviewer")

    def test_split_checksum_and_group_leakage_guards(self):
        bundle = self.split()
        self.assertEqual(sum(len(rows) for rows in validate_bundle(bundle).values()), 30)
        modified = deepcopy(bundle)
        modified["splits"]["test"][0]["group_id"] = modified["splits"]["train"][0]["group_id"]
        modified["bundle_sha256"] = digest({k: v for k, v in modified.items() if k != "bundle_sha256"})
        with self.assertRaises(InputError):
            validate_bundle(modified)
        with self.assertRaises(InputError):
            split_dataset(payload_fixture(), "bad", "reviewer")

    def test_duplicates_and_groups_are_joined_transitively(self):
        payload = payload_fixture()
        payload["items"][1]["group_id"] = payload["items"][0]["group_id"]
        payload["items"][2]["utterances"] = deepcopy(payload["items"][1]["utterances"])
        payload["items"][2]["content_hash"] = payload["items"][1]["content_hash"]
        payload["dataset_sha256"] = digest({k: v for k, v in payload.items() if k != "dataset_sha256"})
        bundle = self.split(payload)
        indexes = [name for name, rows in bundle["splits"].items() for row in rows if row["conversation_id"] in {digest("c0"), digest("c1"), digest("c2")}]
        self.assertEqual(len(set(indexes)), 1)

    def test_metrics_fixed_label_space_threshold_validation_and_nan(self):
        report = scores(["interested", "declined"], ["interested", "interested"])
        self.assertEqual(report["per_class"]["declined"]["support"], 1)
        self.assertEqual(len(report["confusion_matrix"]), 6)
        probabilities = [[.4, .12, .12, .12, .12, .12]]
        self.assertEqual(probability_label(probabilities[0], .5), "unknown")
        self.assertIn(select_threshold(["interested"], probabilities), (0, .4, .5, .6, .7, .8, .9))
        with self.assertRaises(InputError):
            probability_label([float("nan")] * 6, .5)

    def test_text_redaction_and_full_tail_window_limit(self):
        self.assertNotIn("0987654321", text_for([turn("Số điện thoại 0987654321")]))
        class Tokenizer:
            def encode(self, *args, **kwargs): return list(range(25))
            def num_special_tokens_to_add(self, **kwargs): return 2
        windows = windows_for(Tokenizer(), [turn("Test")], 16, 2)
        self.assertEqual(windows[-1][-1], 24)
        with self.assertRaises(InputError):
            windows_for(Tokenizer(), [turn("Test")], 16, 1)

    def test_train_refuses_missing_classes_before_importing_ml_or_writing_output(self):
        bundle = self.split()
        for row in bundle["splits"]["train"]:
            row["label"] = "interested"
        bundle["bundle_sha256"] = digest({k: v for k, v in bundle.items() if k != "bundle_sha256"})
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bundle.json"
            path.write_text(json.dumps(bundle), encoding="utf-8")
            output = Path(directory) / "trained"
            with self.assertRaisesMessage(CommandError, "chưa có đủ"):
                call_command("train_candidate_status", str(path), base_model=Path(directory), output=output, license_reviewed=True, stdout=StringIO())
            self.assertFalse(output.exists())

    def test_status_command_reports_blockers_and_export_creates_nothing(self):
        output = StringIO()
        call_command("status_training", "status", stdout=output)
        self.assertEqual(json.loads(output.getvalue())["eligible"], 0)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "export.json"
            groups = Path(directory) / "groups.json"
            groups.write_text("{}", encoding="utf-8")
            with self.assertRaises(CommandError):
                call_command("status_training", "export", output=path, group_map=groups)
            self.assertFalse(path.exists())

    def test_manifest_missing_invalid_and_unapproved_are_unavailable(self):
        with override_settings(STATUS_MODEL_DIR=""):
            self.assertFalse(model_status()["available"])
        with tempfile.TemporaryDirectory() as directory, override_settings(STATUS_MODEL_DIR=directory):
            Path(directory, "status-manifest.json").write_text("{}", encoding="utf-8")
            self.assertEqual(model_status()["code"], "STATUS_MANIFEST_INVALID")

    def test_manifest_checks_pinned_files_and_approval_command_gate(self):
        reviewer = get_user_model().objects.create_superuser("release-reviewer")
        TaxonomyApproval.objects.create(version=definitions()["version"], definition_hash=digest(definitions()), definitions=definitions(), reviewer=reviewer, note="Kiểm tra fixture, không phải nghiệm thu thật.")
        with tempfile.TemporaryDirectory() as directory, override_settings(STATUS_MODEL_DIR=directory):
            root = Path(directory)
            evaluation = {"definition_hash": digest(definitions()), "bundle_sha256": "0" * 64, "threshold": .5, "threshold_selected_on": "validation", "reports": {"test": scores(CODES, CODES)}, "baseline": {"test": scores(CODES, ["interested"] * 6)}}
            for name in ("config.json", "tokenizer.json", "tokenizer_config.json", "model.safetensors"):
                (root / name).write_bytes(b"test fixture only")
            (root / "evaluation.json").write_text(json.dumps(evaluation), encoding="utf-8")
            files = {path.name: file_hash(path) for path in root.iterdir()}
            manifest = {"format": FORMAT, "preprocessing": WINDOWING, "labels": CODES, "definition_hash": digest(definitions()), "model_version": "fixture-only", "max_length": 256, "max_windows": 2, "threshold": .5, "files": files, "approved_for_use": False, "bundle_sha256": "0" * 64}
            (root / "status-manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
            self.assertEqual(model_status()["code"], "STATUS_MODEL_UNAPPROVED")
            with self.assertRaises(CommandError):
                call_command("approve_status_model", directory, reviewer=reviewer.username, evaluation_sha256=files["evaluation.json"], note="fixture", stdout=StringIO())
            call_command("approve_status_model", directory, reviewer=reviewer.username, evaluation_sha256=files["evaluation.json"], note="Fixture kỹ thuật, không phải model thật.", confirm_evaluation=True, license_reviewed=True, stdout=StringIO())
            self.assertTrue(read_manifest()[1]["approved_for_use"])
            (root / "untracked.json").write_text("{}", encoding="utf-8")
            self.assertEqual(model_status()["code"], "STATUS_MANIFEST_INVALID")
