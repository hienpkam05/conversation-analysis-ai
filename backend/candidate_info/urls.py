from django.urls import path
from . import views

urlpatterns = [
    path("config/", views.config),
    path("revisions/<uuid:id>/profiles/", views.profiles),
    path("profiles/<uuid:id>/confirm/", views.confirm),
    path("profiles/<uuid:id>/searches/", views.searches),
]
