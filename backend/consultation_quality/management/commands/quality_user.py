from getpass import getpass

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from consultation_quality.models import Conversation


class Command(BaseCommand):
    help = "Tạo/cấp quyền tài khoản chấm hoặc duyệt; mật khẩu được nhập ẩn, không lưu trong tài liệu."

    def add_arguments(self, parser):
        parser.add_argument("username")
        parser.add_argument("--reviewer", action="store_true")
        parser.add_argument("--assign-pilot", action="store_true")
        parser.add_argument("--reset-password", action="store_true")

    @transaction.atomic
    def handle(self, *args, **options):
        User = get_user_model()
        username = options["username"]
        if not username.strip() or len(username) > 150:
            raise CommandError("Tên tài khoản không hợp lệ.")
        user, created = User.objects.get_or_create(username=username)
        if created or options["reset_password"]:
            password = getpass("Mật khẩu (ít nhất 12 ký tự): ")
            if len(password) < 12 or password != getpass("Nhập lại mật khẩu: "):
                raise CommandError("Mật khẩu quá ngắn hoặc không trùng nhau.")
            user.set_password(password)
            user.save()
        name = "quality-reviewers" if options["reviewer"] else "quality-annotators"
        group, _ = Group.objects.get_or_create(name=name)
        codes = ["annotate_quality"] + (["review_quality"] if options["reviewer"] else [])
        group.permissions.set(Permission.objects.filter(content_type__app_label="consultation_quality", codename__in=codes))
        user.groups.add(group)
        if options["assign_pilot"]:
            for conversation in Conversation.objects.filter(audio_sample__isnull=False):
                conversation.members.add(user)
        self.stdout.write(self.style.SUCCESS(f"Đã cấp quyền {name} cho {username}. Không có nhãn nào được tạo/duyệt."))
