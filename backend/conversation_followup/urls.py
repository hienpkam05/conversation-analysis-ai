from django.urls import path
from . import views

urlpatterns = [
    path("revisions/<uuid:id>/summaries/", views.summaries),
    path("summaries/<uuid:id>/", views.summary_detail),
    path("summaries/<uuid:id>/copy/", views.copy_summary),
    path("summaries/<uuid:id>/approve/", views.approve_summary),
    path("appointments/", views.appointments),
    path("appointments/<uuid:id>/", views.edit_appointment),
    path("appointments/<uuid:id>/confirm/", views.confirm_appointment),
    path("appointments/<uuid:id>/cancel/", views.cancel_appointment),
]
