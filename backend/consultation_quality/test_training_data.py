import json
from copy import deepcopy
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase
from django.utils import timezone

from .models import Assessment, AudioSample, Conversation, Revision, RubricVersion
from .rubric import RUBRIC
from .services import InputError
from .training_data import digest, export_dataset, fingerprint, make_splits, redact, validate_dataset
from .training_metrics import evaluate, majority_baseline, validate_bundle


class TrainingDataTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.author = User.objects.create_user("fixture-annotator")
        self.reviewer = User.objects.create_user("fixture-reviewer")
        self.rubric = RubricVersion.objects.get(version=RUBRIC["version"])
        self.rubric.status, self.rubric.approved_by, self.rubric.approved_at = "approved", self.reviewer, timezone.now()
        self.rubric.save()
        self.groups = {}

    def label(self, word="alpha", score=2, status="approved", group=None):
        conversation = Conversation.objects.create(title="PRIVATE_TITLE", owner=self.author, source_reference="PRIVATE_REFERENCE")
        self.groups[str(conversation.pk)] = group or f"private-group-{word}"
        revision = Revision.objects.create(conversation=conversation, utterances=[{
            "id": "source-turn", "position": 1, "role": "consultant", "text": f"Chào PRIVATE_NAME, nội dung {word}. Liên hệ 0912 345 678 hoặc contact@example.com, lương 10 triệu.",
            "start_seconds": None, "end_seconds": None}], roles_confirmed=True, transcript_reviewed=True)
        ratings = [{"criterion_code": c["code"], "score": score, "comment": "PRIVATE_COMMENT",
            "not_assessable_reason": "PRIVATE_REASON" if score is None else "",
            "evidence": {"kind": "quote", "utterance_ids": ["source-turn"]}} for c in RUBRIC["criteria"]]
        item = Assessment.objects.create(revision=revision, rubric=deepcopy(RUBRIC), rubric_version=self.rubric,
            ratings=ratings, total_score=None if score is None else score * 50, status=status,
            author=self.author, reviewer=self.reviewer if status == "approved" else None,
            reviewed_at=timezone.now() if status == "approved" else None)
        return item

    def dataset(self, count=9):
        for i in range(count):
            self.label(f"sample-{chr(97+i)}", i % 3)
        return export_dataset(RUBRIC["version"], self.groups, ["PRIVATE_NAME"])

    def test_only_approved_labels_and_approved_rubric(self):
        self.label(status="needs_review")
        with self.assertRaises(InputError):
            export_dataset(RUBRIC["version"])
        self.rubric.status = "draft"
        self.rubric.save()
        with self.assertRaises(InputError):
            export_dataset(RUBRIC["version"])

    def test_privacy_snapshot_and_evidence_remap(self):
        item = self.label()
        original = deepcopy(item.revision.utterances)
        payload = export_dataset(RUBRIC["version"], self.groups, ["PRIVATE_NAME"])
        serial = json.dumps(payload, ensure_ascii=False)
        for private in ["PRIVATE_NAME", "PRIVATE_COMMENT", "PRIVATE_REASON", "PRIVATE_TITLE", "PRIVATE_REFERENCE", "contact@example.com", "0912 345 678", str(item.pk), str(item.revision_id), str(item.revision.conversation_id), "private-group-alpha", "fixture-annotator"]:
            self.assertNotIn(private, serial)
        self.assertIn("10 triệu", serial)
        self.assertTrue(payload["privacy_review_required"])
        self.assertEqual(payload["items"][0]["evidence"]["opening"]["utterance_ids"], ["u0001"])
        item.revision.refresh_from_db()
        self.assertEqual(item.revision.utterances, original)
        validate_dataset(payload)

    def test_redaction_limits_and_duplicates_ignore_segmentation(self):
        self.assertEqual(redact("Anh An đang làm", ["An"]), "Anh [REDACTED] đang làm")
        result = redact("+84 912 345 678, 0912345678; a@example.com https://example.com 012345678901 lương 10 triệu")
        self.assertNotIn("912", result)
        self.assertNotIn("012345678901", result)
        self.assertIn("10 triệu", result)
        one = [{"role": "consultant", "text": "Chào chị, công việc gần nhà."}]
        two = [{"role": "candidate", "text": "CHÀO CHỊ"}, {"role": "consultant", "text": "công việc gần nhà"}]
        self.assertEqual(fingerprint(one), fingerprint(two))

    def test_malformed_dataset_fails_with_controlled_error(self):
        data = self.dataset()
        for field, value in [("rubric", []), ("items", [None]), ("preprocessing_version", "unknown")]:
            changed = deepcopy(data)
            changed[field] = value
            changed["dataset_sha256"] = digest({k: v for k, v in changed.items() if k != "dataset_sha256"})
            with self.assertRaises(InputError):
                validate_dataset(changed)

    def test_latest_unreviewed_revision_excludes_old_label(self):
        item = self.label()
        Revision.objects.create(conversation=item.revision.conversation, utterances=item.revision.utterances)
        with self.assertRaises(InputError):
            export_dataset(RUBRIC["version"])

    def test_conflicting_approved_labels_excluded_until_resolved(self):
        item = self.label()
        rows = deepcopy(item.ratings)
        for r in rows:
            r["score"] = 1
        Assessment.objects.create(revision=item.revision, rubric=item.rubric, rubric_version=self.rubric,
            ratings=rows, total_score=50, status="approved", author=self.author, reviewer=self.reviewer, reviewed_at=timezone.now())
        with self.assertRaises(InputError):
            export_dataset(RUBRIC["version"])

    def test_superseded_label_not_used(self):
        item = self.label()
        rows = deepcopy(item.ratings)
        for r in rows:
            r["score"] = 1
        replacement = Assessment.objects.create(revision=item.revision, rubric=item.rubric, rubric_version=self.rubric,
            ratings=rows, total_score=50, status="approved", supersedes=item, author=self.author, reviewer=self.reviewer, reviewed_at=timezone.now())
        payload = export_dataset(RUBRIC["version"])
        self.assertEqual(payload["items"][0]["assessment_id"], digest(str(replacement.pk)))
        self.assertEqual(payload["items"][0]["labels"]["opening"], 1)

    def test_unreviewed_audio_missing_reviewer_and_all_na_excluded(self):
        item = self.label("alpha")
        AudioSample.objects.create(call_id="private-call", conversation=item.revision.conversation, source_path="private-path", duration_seconds=60)
        second = self.label("beta")
        Assessment.objects.filter(pk=second.pk).update(reviewer=None)
        self.label("gamma", score=None)
        with self.assertRaises(InputError):
            export_dataset(RUBRIC["version"])

    def test_independent_self_approval_cannot_enter_training(self):
        item = self.label()
        Assessment.objects.filter(pk=item.pk).update(reviewer=self.author)
        with self.assertRaises(InputError):
            export_dataset(RUBRIC["version"])

    def test_splits_are_deterministic_and_grouped(self):
        data = self.dataset()
        bundle = make_splits(data, data["dataset_sha256"], "privacy-reviewer")
        again = make_splits(data, data["dataset_sha256"], "privacy-reviewer")
        self.assertEqual(bundle, again)
        self.assertFalse(bundle["release_approved"])
        self.assertEqual(sum(bundle["report"]["split_counts"].values()), 9)
        self.assertTrue(all(bundle["report"]["split_counts"].values()))
        validate_bundle(bundle)

    def test_contact_groups_and_duplicate_calls_never_cross_splits(self):
        self.label("same words", group="candidate-one")
        self.label("other words", group="candidate-one")
        self.label("same words", group="candidate-two")
        self.label("independent-alpha")
        self.label("independent-beta")
        data = export_dataset(RUBRIC["version"], self.groups)
        bundle = make_splits(data, data["dataset_sha256"], "reviewer")
        self.assertEqual(bundle["report"]["independent_groups"], 3)
        grouped = {name for name, rows in bundle["splits"].items() if len(rows) == 3}
        self.assertEqual(len(grouped), 1)
        validate_bundle(bundle)

    def test_privacy_confirmation_and_group_map_required(self):
        self.label()
        no_groups = export_dataset(RUBRIC["version"])
        with self.assertRaises(InputError):
            make_splits(no_groups, no_groups["dataset_sha256"], "reviewer")
        data = export_dataset(RUBRIC["version"], self.groups)
        for checksum, reviewer in [("wrong", "reviewer"), (data["dataset_sha256"], "")]:
            with self.assertRaises(InputError):
                make_splits(data, checksum, reviewer)
        with self.assertRaises(InputError):
            make_splits(data, data["dataset_sha256"], "reviewer")

    def test_tamper_and_overlap_rejected(self):
        data = self.dataset()
        changed = deepcopy(data)
        changed["items"][0]["labels"]["opening"] = 0
        changed["items"][0]["labels"]["needs"] = 1
        with self.assertRaises(InputError):
            validate_dataset(changed)
        bundle = make_splits(data, data["dataset_sha256"], "reviewer")
        bundle["splits"]["test"].append(bundle["splits"]["train"][0])
        bundle["bundle_sha256"] = digest({k: v for k, v in bundle.items() if k != "bundle_sha256"})
        with self.assertRaises(InputError):
            validate_bundle(bundle)

    def test_baseline_uses_train_only_and_masks_na(self):
        train = [{"labels": {"opening": 1}}, {"labels": {"opening": 1}}, {"labels": {"opening": None}}, {"labels": {"opening": 2}}]
        base = majority_baseline(train, ["opening"])
        self.assertEqual(base["opening"]["score"], 1)
        self.assertAlmostEqual(base["opening"]["class_frequencies"][1], 2 / 3)
        with self.assertRaises(InputError):
            majority_baseline([{"labels": {"opening": None}}], ["opening"])

    def test_metrics_fixed_classes_masked_support_and_total_mae(self):
        rubric = {"criteria": [{"code": "opening", "weight": 1.0}]}
        rows = [{"labels": {"opening": 2}}, {"labels": {"opening": None}}]
        report = evaluate(rows, [{"opening": 2}, {"opening": 0}], rubric)
        self.assertEqual(report["criteria"]["opening"]["macro_f1"], 1 / 3)
        self.assertEqual(report["criteria"]["opening"]["masked_count"], 1)
        self.assertEqual(report["total_eligible_count"], 1)
        self.assertEqual(report["total_mae"], 0)
        self.assertEqual(report["review_required_rate"], 1)

    def test_commands_export_split_baseline_and_refuse_overwrite(self):
        self.dataset()
        with TemporaryDirectory() as folder:
            folder = Path(folder)
            groups, terms = folder / "groups.json", folder / "terms.json"
            groups.write_text(json.dumps(self.groups), encoding="utf-8")
            terms.write_text(json.dumps(["PRIVATE_NAME"]), encoding="utf-8")
            output, splits, report = folder / "approved.json", folder / "splits.json", folder / "baseline.json"
            call_command("export_quality_training", str(output), rubric_version=RUBRIC["version"], group_map=groups, redact_terms=terms, stdout=StringIO())
            exported = json.loads(output.read_text(encoding="utf-8"))
            call_command("prepare_quality_splits", str(output), str(splits), privacy_reviewed_sha256=exported["dataset_sha256"], privacy_reviewer="fixture-reviewer", stdout=StringIO())
            call_command("train_quality_baseline", str(splits), str(report), stdout=StringIO())
            data = json.loads(report.read_text(encoding="utf-8"))
            self.assertEqual(data["fitted_on"], "train_only")
            self.assertFalse(data["release_approved"])
            self.assertEqual(set(data["evaluation"]), {"validation", "test"})
            with self.assertRaises(CommandError):
                call_command("train_quality_baseline", str(splits), str(report))
