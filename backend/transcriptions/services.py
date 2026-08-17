import json
import os
import sys
import tempfile
import time
from pathlib import Path
from urllib.parse import urlparse

from django.conf import settings
import requests


PROJECT_ROOT = Path(settings.PROJECT_ROOT)
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

os.environ.setdefault("HF_HOME", str(settings.HUGGINGFACE_CACHE_DIR))
os.environ.setdefault("HF_HUB_CACHE", str(settings.HUGGINGFACE_CACHE_DIR / "hub"))

SUPPORTED_AUDIO = {".mp3", ".wav", ".m4a", ".ogg", ".flac", ".mp4", ".webm", ".aac"}

_MODEL_CACHE = {}


def looks_repetitive(text):
    words = text.split()
    if len(words) < 10:
        return False

    unique_ratio = len(set(words)) / len(words)
    if unique_ratio < 0.18:
        return True

    lowered = text.lower()
    repeated_phrases = ["ơn ơn", "bác khá hả", "các ơn"]
    return any(lowered.count(phrase) >= 6 for phrase in repeated_phrases)


def fmt_time(seconds):
    return f"{int(seconds // 3600):02}:{int((seconds % 3600) // 60):02}:{int(seconds % 60):02}"


def fmt_srt(seconds):
    return (
        f"{int(seconds // 3600):02}:"
        f"{int((seconds % 3600) // 60):02}:"
        f"{int(seconds % 60):02},"
        f"{int((seconds % 1) * 1000):03}"
    )


def build_dialogue_text(segments):
    lines = []
    for index, segment in enumerate(segments, 1):
        start = float(segment.get("start", 0))
        end = float(segment.get("end", 0))
        text = str(segment.get("text", "")).strip()
        if text:
            lines.append(f"{index}. [{start:.1f}s - {end:.1f}s]\n{text}")
    return "\n\n".join(lines)


def normalize_result(result, source_name, model_name, elapsed, engine):
    segments = []
    for index, segment in enumerate(result.get("segments", []), 1):
        text = str(segment.get("text", "")).strip()
        if not text:
            continue
        segments.append(
            {
                "id": int(segment.get("id", index)),
                "start": round(float(segment.get("start", 0)), 3),
                "end": round(float(segment.get("end", 0)), 3),
                "text": text,
            }
        )

    full_text = result.get("full_text") or " ".join(item["text"] for item in segments)
    language_prob = result.get("language_prob", 0)
    if language_prob is None:
        language_prob = 0

    return {
        "file": source_name,
        "engine": engine,
        "model": result.get("model", model_name),
        "language": result.get("language", ""),
        "language_prob": round(float(language_prob), 4),
        "duration_seconds": round(float(result.get("duration_seconds", 0)), 2),
        "process_time_sec": round(float(result.get("process_time_sec", elapsed)), 2),
        "preprocessed": bool(result.get("preprocessed", False)),
        "total_segments": int(result.get("total_segments", len(segments))),
        "total_words": int(result.get("total_words", sum(len(item["text"].split()) for item in segments))),
        "full_text": full_text,
        "dialogue_text": result.get("dialogue_text") or build_dialogue_text(segments),
        "segments": segments,
    }


def validate_colab_url(url):
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("URL Colab không hợp lệ.")
    if not parsed.path or parsed.path == "/":
        return url.rstrip("/") + "/transcribe"
    return url


def colab_health_url(url):
    endpoint = validate_colab_url(url)
    if endpoint.rstrip("/").endswith("/transcribe"):
        return endpoint.rstrip("/")[: -len("/transcribe")] + "/health"
    return endpoint.rstrip("/") + "/health"


def check_colab_health(url):
    endpoint = colab_health_url(url)
    response = requests.get(endpoint, timeout=(10, 20))
    if not response.ok:
        raise RuntimeError(f"Colab health trả lỗi {response.status_code}: {response.text[:300]}")
    try:
        return response.json()
    except ValueError as exc:
        raise RuntimeError(f"Colab health không trả JSON: {response.text[:300]}") from exc


def get_model(model_size):
    try:
        from faster_whisper import WhisperModel
    except ImportError as exc:
        raise RuntimeError(
            "Chưa cài faster-whisper. Hãy chạy: pip install faster-whisper"
        ) from exc

    if model_size not in _MODEL_CACHE:
        _MODEL_CACHE[model_size] = WhisperModel(
            model_size,
            device=settings.WHISPER_DEVICE,
            compute_type=settings.WHISPER_COMPUTE_TYPE,
            cpu_threads=settings.WHISPER_CPU_THREADS,
            num_workers=2 if model_size != "large-v3" else 1,
        )
    return _MODEL_CACHE[model_size]


def maybe_preprocess(audio_path, enabled):
    if not enabled:
        return audio_path, None

    try:
        from audio_preprocess import DEFAULT_CONFIG, preprocess_audio
    except ImportError as exc:
        raise RuntimeError(
            "Chưa cài đủ thư viện tiền xử lý audio. Hãy cài noisereduce, librosa, soundfile, numpy, scipy."
        ) from exc

    temp_path = Path(tempfile.mktemp(suffix=".wav"))
    config = {
        **DEFAULT_CONFIG,
        "noise_reduce": True,
        "bandpass_filter": True,
        "normalize_volume": True,
        "trim_silence": True,
    }
    return preprocess_audio(audio_path, temp_path, config), temp_path


def save_outputs(source_path, output_dir, result):
    output_dir.mkdir(parents=True, exist_ok=True)
    stem = source_path.stem

    txt_path = output_dir / f"{stem}_transcript.txt"
    srt_path = output_dir / f"{stem}_transcript.srt"
    json_path = output_dir / f"{stem}_transcript.json"

    with txt_path.open("w", encoding="utf-8") as file:
        file.write(f"File: {source_path.name}\n")
        file.write(f"Ngôn ngữ: {result['language']} ({result['language_prob']:.0%})\n")
        file.write(f"Thời lượng: {fmt_time(result['duration_seconds'])}\n")
        file.write("=" * 60 + "\n\n")
        for segment in result["segments"]:
            file.write(f"[{fmt_time(segment['start'])} -> {fmt_time(segment['end'])}]\n")
            file.write(f"{segment['text']}\n\n")
        file.write("=" * 60 + "\nTOÀN VĂN:\n")
        file.write(result["full_text"])

    with srt_path.open("w", encoding="utf-8") as file:
        for segment in result["segments"]:
            file.write(f"{segment['id']}\n")
            file.write(f"{fmt_srt(segment['start'])} --> {fmt_srt(segment['end'])}\n")
            file.write(f"{segment['text']}\n\n")

    with json_path.open("w", encoding="utf-8") as file:
        json.dump(result, file, ensure_ascii=False, indent=2)

    return {
        "txt": str(txt_path),
        "srt": str(srt_path),
        "json": str(json_path),
    }


def transcribe_file(audio_path, model_size, language, beam_size, preprocess):
    audio_path = Path(audio_path)
    if audio_path.suffix.lower() not in SUPPORTED_AUDIO:
        raise ValueError("Định dạng audio chưa được hỗ trợ.")

    actual_path, temp_path = maybe_preprocess(audio_path, preprocess)
    started_at = time.time()

    try:
        model = get_model(model_size)
        segments_gen, audio_info = model.transcribe(
            str(actual_path),
            language=language or None,
            beam_size=beam_size,
            best_of=beam_size,
            temperature=0.0,
            vad_filter=True,
            vad_parameters={
                "threshold": 0.5,
                "min_speech_duration_ms": 250,
                "min_silence_duration_ms": 700,
                "speech_pad_ms": 120,
            },
            word_timestamps=True,
            condition_on_previous_text=False,
            compression_ratio_threshold=2.2,
            log_prob_threshold=-0.8,
            no_speech_threshold=0.65,
            repetition_penalty=1.15,
            initial_prompt=(
                "Đây là cuộc tư vấn tuyển dụng lao động Việt Nam. Các từ thường gặp: "
                "mức lương, ca làm việc, khu công nghiệp, hợp đồng lao động, bảo hiểm xã hội, "
                "tăng ca, phụ cấp, ký túc xá, nhà máy, công nhân, ứng viên, nhân viên tư vấn."
            ),
        )

        segments = []
        for segment in segments_gen:
            text = segment.text.strip()
            if text and not looks_repetitive(text):
                segments.append(
                    {
                        "id": len(segments) + 1,
                        "start": round(segment.start, 3),
                        "end": round(segment.end, 3),
                        "text": text,
                    }
                )

        elapsed = time.time() - started_at
        result = normalize_result(
            {
                "language": audio_info.language,
                "language_prob": round(audio_info.language_probability, 4),
                "duration_seconds": round(audio_info.duration, 2),
                "preprocessed": bool(preprocess),
                "segments": segments,
            },
            source_name=audio_path.name,
            model_name=model_size,
            elapsed=elapsed,
            engine="local",
        )
        result.update({
            "file": audio_path.name,
            "model": model_size,
            "process_time_sec": round(elapsed, 2),
        })
        result["outputs"] = save_outputs(audio_path, Path(settings.WHISPER_OUTPUT_DIR), result)
        return result
    finally:
        if temp_path and temp_path.exists():
            temp_path.unlink(missing_ok=True)


def transcribe_with_colab(audio_path, colab_url, language, beam_size):
    audio_path = Path(audio_path)
    endpoint = validate_colab_url(colab_url)
    started_at = time.time()

    with audio_path.open("rb") as file:
        response = requests.post(
            endpoint,
            files={"audio": (audio_path.name, file, "application/octet-stream")},
            data={"language": language or "vi", "beam_size": str(beam_size)},
            timeout=(20, 60 * 60),
        )

    if not response.ok:
        raise RuntimeError(f"Colab trả lỗi {response.status_code}: {response.text[:500]}")

    try:
        payload = response.json()
    except ValueError as exc:
        raise RuntimeError("Colab không trả về JSON hợp lệ. Hãy kiểm tra endpoint /transcribe.") from exc

    if isinstance(payload, dict) and payload.get("error"):
        raise RuntimeError(f"Colab báo lỗi: {payload['error']}")

    result = normalize_result(
        payload,
        source_name=audio_path.name,
        model_name=payload.get("model", "colab"),
        elapsed=time.time() - started_at,
        engine="colab",
    )
    result["outputs"] = save_outputs(audio_path, Path(settings.WHISPER_OUTPUT_DIR), result)
    return result
