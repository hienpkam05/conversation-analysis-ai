from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("transcriptions.urls")),
    path("api/quality/", include("consultation_quality.urls")),
    path("api/followup/", include("conversation_followup.urls")),
    path("api/candidate-status/", include("candidate_status.urls")),
    path("api/candidate-info/", include("candidate_info.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
