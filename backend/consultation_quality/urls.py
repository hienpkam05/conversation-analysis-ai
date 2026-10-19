from django.urls import path
from . import views
from . import review_views as review
from . import job_views

urlpatterns = [
    path("samples/", views.samples),
    path("samples/<uuid:id>/audio/", views.audio),
    path("samples/<uuid:id>/review/", views.review_sample),
    path("session/", review.session),
    path("rubrics/", review.rubrics),
    path("rubrics/<uuid:id>/", review.rubric_detail),
    path("rubrics/<uuid:id>/approve/", review.approve_rubric),
    path("pilot-resolutions/", review.pilot),
    path("revisions/<uuid:id>/", review.revision_detail),
    path("revisions/<uuid:id>/seal/", review.seal),
    path("assessments/<uuid:id>/", review.assessment_detail),
    path("assessments/<uuid:id>/approve/", review.approve_assessment),
    path("model-status/", views.model_status),
    path("conversations/", views.conversations),
    path("conversations/<uuid:id>/", views.conversation_detail),
    path("conversations/<uuid:id>/revisions/", views.new_revision),
    path("revisions/<uuid:id>/assessments/", views.assessments),
    path("revisions/<uuid:id>/assessment-jobs/", job_views.jobs),
    path("assessment-jobs/<uuid:id>/", job_views.job_detail),
    path("assessments/<uuid:id>/manual-copy/", job_views.manual_copy),
]
