def run_job(job_id, token):
    import os
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "recruitment_ai.settings")
    import django
    django.setup()
    from django.db import connections
    from .jobs import execute_job
    try:
        execute_job(job_id, token)
    finally:
        connections.close_all()
