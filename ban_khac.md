# from google.colab import drive

import os
import time
import json
import shutil
import subprocess
import torch
from faster_whisper import WhisperModel

# ================== 1. MOUNT DRIVE ==================

# drive.mount('/content/drive')

# ================== 2. CẤU HÌNH ==================

DRIVE_MEDIA = "/content/drive/MyDrive/17.55, 17 thg 9​_1.mp3" # audio hoặc video đều được
OUTPUT_DIR = "/content/drive/MyDrive/transcripts"
os.makedirs(OUTPUT_DIR, exist_ok=True)

HALLUCINATION_PATTERNS = [
"subscribe", "cảm ơn đã xem", "cảm ơn các bạn đã xem",
"đăng ký kênh", "like và chia sẻ", "hẹn gặp lại",
"nhớ đăng ký", "chia sẻ video", "ghiền mì gõ",
"phụ đề được thực hiện", "vietsub", "biên dịch",
]

# ================== 3. LOAD MODEL (chỉ 1 lần) ==================

if torch.cuda.is_available():
device, compute_type, model_size = "cuda", "float16", "large-v3"
else:
device, compute_type, model_size = "cpu", "int8", "medium"

print(f"⚙️ Đang load model ({model_size}, {device})...")
model = WhisperModel(model_size, device=device, compute_type=compute_type)
print("✅ Load model thành công")

def is_hallucination(text: str) -> bool:
t = text.lower().strip()
if not t:
return True
return any(p in t for p in HALLUCINATION_PATTERNS)

def format_timestamp(seconds: float) -> str:
h, m, s = int(seconds // 3600), int((seconds % 3600) // 60), int(seconds % 60)
ms = int((seconds - int(seconds)) \* 1000)
return f"{h:02}:{m:02}:{s:02},{ms:03}"

def transcribe_media(drive_media_path: str) -> dict:
"""Nhận đường dẫn audio/video trên Drive -> trả về transcript + lưu file kết quả."""

    if not os.path.exists(drive_media_path):
        raise FileNotFoundError(f"❌ Không tìm thấy file: {drive_media_path}")

    base_name = os.path.splitext(os.path.basename(drive_media_path))[0]
    local_media = "/content/local_input" + os.path.splitext(drive_media_path)[1]
    clean_audio = "/content/clean_audio.wav"

    try:
        # ---- 3a. Copy về local disk (đọc local nhanh hơn nhiều so với Drive mount) ----
        print(f"📥 [{base_name}] Đang copy về local disk...")
        t0 = time.time()
        shutil.copy(drive_media_path, local_media)
        print(f"✅ Copy xong: {os.path.getsize(local_media)/1e6:.0f} MB trong {time.time()-t0:.1f}s")

        # ---- 3b. Tách audio (-vn) + chuẩn hóa cho giọng nói qua điện thoại ----
        print("🔄 Đang tách audio & chuẩn hóa...")
        ffmpeg_cmd = [
            "ffmpeg",
            "-i", local_media,
            "-vn",                       # bỏ qua video, chỉ decode audio -> nhanh hơn nhiều với file video nặng
            "-map", "0:a:0",             # chỉ định rõ track audio đầu tiên, tránh nhầm track
            "-ar", "16000",
            "-ac", "1",
            "-af", "highpass=f=100,lowpass=f=8000,afftdn=nf=-25,loudnorm",
            clean_audio,
            "-y", "-loglevel", "error"
        ]
        result = subprocess.run(ffmpeg_cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"❌ ffmpeg lỗi:\n{result.stderr}")
        print("✅ Tách audio xong")

        # ---- 4. Transcribe ----
        print("🎤 Bắt đầu nhận diện...")
        t1 = time.time()

        segments, info = model.transcribe(
            clean_audio,
            language="vi",
            beam_size=5,
            best_of=5,
            temperature=0.0,
            condition_on_previous_text=False,
            repetition_penalty=1.2,
            vad_filter=True,
            vad_parameters=dict(min_silence_duration_ms=400, speech_pad_ms=200),
            no_speech_threshold=0.6,
            word_timestamps=True,
            initial_prompt="Đây là cuộc hội thoại tư vấn tuyển dụng lao động tại Việt Nam, sử dụng tiếng Việt rõ ràng, có hai người nói."
        )
        print(f"🌐 Ngôn ngữ: {info.language} (độ tin cậy: {info.language_probability:.2%})")

        # ---- 5. Lọc hallucination & gộp kết quả ----
        results = []
        for seg in segments:
            text = seg.text.strip()
            if is_hallucination(text):
                continue
            results.append({"start": round(seg.start, 2), "end": round(seg.end, 2), "text": text})
            print(f"[{seg.start:.2f}s → {seg.end:.2f}s] {text}")

        print(f"⏱️ Thời gian nhận diện: {time.time() - t1:.2f}s")
        full_text = " ".join(r["text"] for r in results)

        # ---- 6. Lưu kết quả ----
        txt_path  = os.path.join(OUTPUT_DIR, f"{base_name}.txt")
        json_path = os.path.join(OUTPUT_DIR, f"{base_name}.json")
        srt_path  = os.path.join(OUTPUT_DIR, f"{base_name}.srt")

        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(full_text)

        with open(json_path, "w", encoding="utf-8") as f:
            json.dump({
                "media_file": drive_media_path,
                "language": info.language,
                "language_probability": info.language_probability,
                "duration": info.duration,
                "segments": results
            }, f, ensure_ascii=False, indent=2)

        with open(srt_path, "w", encoding="utf-8") as f:
            for i, r in enumerate(results, start=1):
                f.write(f"{i}\n{format_timestamp(r['start'])} --> {format_timestamp(r['end'])}\n{r['text']}\n\n")

        print(f"💾 Đã lưu:\n- {txt_path}\n- {json_path}\n- {srt_path}")
        return {"text": full_text, "segments": results, "info": info}

    finally:
        # ---- 7. Dọn dẹp ổ đĩa local, tránh đầy dung lượng Colab ----
        for f in (local_media, clean_audio):
            if os.path.exists(f):
                os.remove(f)

# ================== CHẠY ==================

result = transcribe_media(DRIVE_MEDIA)
print("\n📌 Toàn bộ nội dung:")
print(result["text"])
