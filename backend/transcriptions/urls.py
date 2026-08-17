from django.urls import path

from .views import colab_health_check, health_check, transcribe_audio


urlpatterns = [
    path("health/", health_check, name="health_check"),
    path("colab-health/", colab_health_check, name="colab_health_check"),
    path("transcribe/", transcribe_audio, name="transcribe_audio"),
]
