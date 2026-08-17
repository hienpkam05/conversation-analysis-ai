from pathlib import Path
from uuid import uuid4

from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

from .services import SUPPORTED_AUDIO, check_colab_health, transcribe_file, transcribe_with_colab


def friendly_error(exc, engine="local"):
    message = str(exc)
    if engine == "colab":
        if "Colab" in message:
            return message
        if "WinError 10013" in message or "trying to locate the files on the Hub" in message:
            return (
                "Colab API đang lỗi khi tải hoặc mở model Whisper. "
                "Hãy chạy lại cell tạo app.py và cell tunnel trong Colab, chờ model load xong rồi thử lại."
            )
        if "Failed to establish a new connection" in message or "Max retries exceeded" in message:
            return "Không kết nối được tới Colab API. Hãy kiểm tra URL Colab còn sống và có dạng .../transcribe."
        return f"Lỗi từ Colab API: {message}"

    if "not enough space on the disk" in message or "os error 112" in message:
        return (
            "Không đủ dung lượng ổ đĩa để tải hoặc ghép model. "
            "Hãy chọn tiny/medium, hoặc dùng cache model trên ổ D rồi tải lại large-v3."
        )
    if "WinError 10013" in message or "trying to locate the files on the Hub" in message:
        return (
            "Model bạn chọn chưa có sẵn trong máy và hệ thống đang bị chặn tải từ Hugging Face. "
            "Hãy chọn tiny/medium đã tải sẵn, hoặc tải model đó trước rồi chạy lại."
        )
    if "Failed to establish a new connection" in message or "Max retries exceeded" in message:
        return "Không kết nối được tới Colab API. Hãy kiểm tra URL Colab còn sống và có dạng .../transcribe."
    return message


def health_check(_request):
    return JsonResponse({"status": "ok"})


def colab_health_check(request):
    url = request.GET.get("url", "")
    try:
        payload = check_colab_health(url)
        return JsonResponse({"status": "ok", "colab": payload}, json_dumps_params={"ensure_ascii": False})
    except Exception as exc:
        return JsonResponse({"status": "error", "error": friendly_error(exc, "colab"), "detail": str(exc)}, status=500)


@csrf_exempt
def transcribe_audio(request):
    if request.method == "OPTIONS":
        return JsonResponse({})

    if request.method != "POST":
        return JsonResponse({"error": "Chỉ hỗ trợ POST."}, status=405)

    uploaded = request.FILES.get("audio")
    if not uploaded:
        return JsonResponse({"error": "Vui lòng chọn file audio."}, status=400)

    suffix = Path(uploaded.name).suffix.lower()
    if suffix not in SUPPORTED_AUDIO:
        return JsonResponse({"error": "Định dạng audio chưa được hỗ trợ."}, status=400)

    upload_dir = Path(settings.MEDIA_ROOT) / "uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)
    saved_path = upload_dir / f"{uuid4().hex}{suffix}"

    with saved_path.open("wb+") as destination:
        for chunk in uploaded.chunks():
            destination.write(chunk)

    engine = request.POST.get("engine", "local")
    try:
        beam_size = max(1, min(5, int(request.POST.get("beam_size", "1"))))
        if engine == "colab":
            result = transcribe_with_colab(
                saved_path,
                colab_url=request.POST.get("colab_url", ""),
                language=request.POST.get("language", "vi"),
                beam_size=beam_size,
            )
        else:
            result = transcribe_file(
                saved_path,
                model_size=request.POST.get("model", settings.WHISPER_DEFAULT_MODEL),
                language=request.POST.get("language", "vi"),
                beam_size=beam_size,
                preprocess=request.POST.get("preprocess", "false").lower() == "true",
            )
        result["original_name"] = uploaded.name
        return JsonResponse(result, json_dumps_params={"ensure_ascii": False})
    except Exception as exc:
        return JsonResponse(
            {"engine": engine, "error": friendly_error(exc, engine), "detail": str(exc)},
            status=500,
            json_dumps_params={"ensure_ascii": False},
        )
