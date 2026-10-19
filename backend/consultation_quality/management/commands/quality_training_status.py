import json
from django.core.management.base import BaseCommand
from consultation_quality.training_data import training_status


class Command(BaseCommand):
    help = "Kiểm tra nhãn trong database trước khi chuẩn bị huấn luyện; không tự duyệt hoặc train."

    def handle(self, *args, **options):
        self.stdout.write(json.dumps(training_status(), ensure_ascii=False, indent=2))
