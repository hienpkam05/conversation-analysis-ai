from django.urls import path
from . import views
from . import review

urlpatterns = [
    path("config/", views.config),
    path("revisions/<uuid:id>/decisions/", views.decisions),
    path("decisions/<uuid:id>/confirm/", views.confirm),
    path("taxonomy/", review.taxonomy),
    path("taxonomy/approve/", review.approve_taxonomy),
    path("decisions/<uuid:id>/review/", review.review_label),
    path("training-status/", review.training_report),
]
