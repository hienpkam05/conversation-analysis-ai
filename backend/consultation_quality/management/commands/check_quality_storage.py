import shutil
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction

from consultation_quality.models import Assessment, Conversation, Revision


class Command(BaseCommand):
    help = "Kiểm tra đọc/ghi database chất lượng; bản ghi thử luôn được rollback."

    def handle(self, *args, **options):
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            if cursor.fetchone()[0] != 1:
                raise CommandError("Không đọc được database.")
        with transaction.atomic():
            probe = Conversation.objects.create(title="storage-probe-rollback")
            Revision.objects.create(conversation=probe, utterances=[])
            transaction.set_rollback(True)
        for revision in Revision.objects.iterator():
            if revision.turn_rows.count() != len(revision.utterances):
                raise CommandError(f"Revision {revision.pk} không khớp dữ liệu chuẩn hóa.")
        for assessment in Assessment.objects.iterator():
            if assessment.rating_rows.count() != len(assessment.ratings):
                raise CommandError(f"Assessment {assessment.pk} không khớp dữ liệu chuẩn hóa.")
        self.stdout.write(f"Database: {connection.vendor}; đọc/ghi và rollback: OK; dữ liệu chuẩn hóa: OK")
        if connection.vendor == "sqlite":
            free = shutil.disk_usage(Path(connection.settings_dict["NAME"]).parent).free / 1024**3
            self.stdout.write(f"Dung lượng trống ổ lưu database: {free:.2f} GB")
        self.stdout.write("Không tạo nhãn hoặc phê duyệt; không kiểm tra tính đúng của nội dung transcript.")
