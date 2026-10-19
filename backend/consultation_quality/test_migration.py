from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase


class QualityMigrationTests(TransactionTestCase):
    def test_upgrade_preserves_snapshots_and_numbers_multiple_revisions(self):
        before = [("consultation_quality", "0004_audiosample_review_disposition_and_more")]
        after = [("consultation_quality", "0007_qualityworkerslot_assessment_inference_metadata_and_more")]
        executor = MigrationExecutor(connection)
        executor.migrate(before)
        try:
            apps = executor.loader.project_state(before).apps
            Conversation = apps.get_model("consultation_quality", "Conversation")
            Revision = apps.get_model("consultation_quality", "Revision")
            Assessment = apps.get_model("consultation_quality", "Assessment")
            conversation = Conversation.objects.create(title="migration-fixture")
            turns = [{"id": "legacy", "position": 1, "role": "unknown", "text": "Snapshot cũ", "start_seconds": None, "end_seconds": None}]
            first = Revision.objects.create(conversation=conversation, utterances=turns)
            second = Revision.objects.create(conversation=conversation, utterances=turns)
            rubric = {"version": "legacy-v1", "criteria": [{"code": "opening", "weight": 1}]}
            ratings = [{"criterion_code": "opening", "score": None, "not_assessable_reason": "Chưa kiểm tra", "evidence": {"kind": "quote", "utterance_ids": []}}]
            old = Assessment.objects.create(revision=first, rubric=rubric, ratings=ratings, total_score=None)
            executor = MigrationExecutor(connection)
            executor.migrate(after)
            apps = executor.loader.project_state(after).apps
            Revision = apps.get_model("consultation_quality", "Revision")
            Assessment = apps.get_model("consultation_quality", "Assessment")
            first = Revision.objects.get(pk=first.pk)
            self.assertEqual(first.status, "sealed")
            self.assertEqual(first.revision_number, 1)
            self.assertEqual(Revision.objects.get(pk=second.pk).revision_number, 2)
            self.assertEqual(first.utterances, turns)
            self.assertEqual(first.turn_rows.count(), 1)
            migrated = Assessment.objects.get(pk=old.pk)
            self.assertEqual(migrated.ratings, ratings)
            self.assertEqual(migrated.rubric, rubric)
            self.assertEqual(migrated.rubric_version.version, "legacy-v1")
            self.assertEqual(migrated.rating_rows.count(), 1)
            self.assertIsNone(migrated.author_id)
            self.assertIsNone(migrated.reviewer_id)
        finally:
            MigrationExecutor(connection).migrate(after)
