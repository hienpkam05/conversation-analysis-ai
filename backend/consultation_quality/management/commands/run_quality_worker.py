import multiprocessing
import time

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import close_old_connections
from django.utils import timezone

from consultation_quality.jobs import claim_job, fail_job
from consultation_quality.models import AssessmentJob, QualityWorkerSlot
from consultation_quality.worker_runner import run_job


class Command(BaseCommand):
    help = "Worker chất lượng tư vấn một slot, chạy model trong process con có timeout; không tự train/tải model."

    def add_arguments(self, parser):
        parser.add_argument("--once", action="store_true")
        parser.add_argument("--poll-seconds", type=float, default=2)

    def handle(self, *args, **options):
        if not 0.2 <= options["poll_seconds"] <= 60:
            raise CommandError("poll-seconds phải từ 0.2 đến 60.")
        process, claimed = None, None
        try:
            while True:
                close_old_connections()
                claimed = claim_job()
                if claimed:
                    job_id, token = claimed
                    process = multiprocessing.get_context("spawn").Process(target=run_job, args=(job_id, token), daemon=True)
                    process.start()
                    process.join(settings.QUALITY_JOB_TIMEOUT)
                    if process.is_alive():
                        process.terminate()
                        process.join(10)
                        if process.is_alive():
                            process.kill()
                            process.join()
                        fail_job(job_id, token, "JOB_TIMEOUT")
                    elif AssessmentJob.objects.filter(pk=job_id, status="running").exists():
                        fail_job(job_id, token, "WORKER_INTERRUPTED")
                    self.stdout.write(f"Job {job_id}: {AssessmentJob.objects.get(pk=job_id).status}")
                    process, claimed = None, None
                else:
                    QualityWorkerSlot.objects.filter(pk=1, token__isnull=True).update(last_seen=timezone.now())
                if options["once"]:
                    return
                time.sleep(options["poll_seconds"])
        except KeyboardInterrupt:
            if process and process.is_alive():
                process.terminate()
                process.join()
            if claimed:
                fail_job(*claimed, "WORKER_INTERRUPTED")
            self.stdout.write("Worker stopped; unfinished job is failed, not automatically retried.")
        except Exception:
            if process and process.is_alive():
                process.terminate()
                process.join()
            if claimed:
                fail_job(*claimed, "WORKER_INTERRUPTED")
            raise CommandError("Worker không khởi chạy hoặc truy cập được database. Tác vụ chưa hoàn tất không được tự chạy lại.") from None
