"""
=============================================================
  Audio → Text  |  faster-whisper  |  Tối ưu cho CPU
  Máy: HP ZBook Firefly i7-1185G7 | 16GB RAM | Intel Iris Xe
=============================================================
Cài đặt (chạy 1 lần trong terminal VSCode):
    pip install faster-whisper tqdm colorama

Cách dùng:
    python transcribe.py                        # dùng file mặc định
    python transcribe.py --audio audio.mp3      # chỉ định file
    python transcribe.py --audio audio.mp3 --model large-v3
    python transcribe.py --folder ./audio_files # xử lý cả thư mục
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path

# ─── Kiểm tra thư viện ────────────────────────────────────────────────────────
try:
    from faster_whisper import WhisperModel
except ImportError:
    print("[LỖI] Chưa cài faster-whisper. Chạy lệnh:")
    print("      pip install faster-whisper")
    sys.exit(1)

try:
    from tqdm import tqdm
    HAS_TQDM = True
except ImportError:
    HAS_TQDM = False

try:
    from colorama import Fore, Style, init
    init(autoreset=True)
    HAS_COLOR = True
except ImportError:
    HAS_COLOR = False
    class Fore:
        GREEN = YELLOW = RED = CYAN = WHITE = RESET = ""
    class Style:
        BRIGHT = RESET_ALL = ""


# ─── Tiện ích in màu ─────────────────────────────────────────────────────────
def ok(msg):   print(f"{Fore.GREEN}[OK]{Style.RESET_ALL}  {msg}")
def info(msg): print(f"{Fore.CYAN}[INFO]{Style.RESET_ALL} {msg}")
def warn(msg): print(f"{Fore.YELLOW}[WARN]{Style.RESET_ALL} {msg}")
def err(msg):  print(f"{Fore.RED}[LỖI]{Style.RESET_ALL} {msg}")


# ─── Định dạng thời gian ─────────────────────────────────────────────────────
def fmt_time(seconds: float) -> str:
    """Chuyển giây → HH:MM:SS"""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    return f"{h:02}:{m:02}:{s:02}"


def fmt_srt(seconds: float) -> str:
    """Chuyển giây → HH:MM:SS,mmm (định dạng SRT)"""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds % 1) * 1000)
    return f"{h:02}:{m:02}:{s:02},{ms:03}"


def fmt_duration(seconds: float) -> str:
    """Hiển thị thời gian xử lý"""
    if seconds < 60:
        return f"{seconds:.1f} giây"
    return f"{seconds/60:.1f} phút"


# ─── Tải model ───────────────────────────────────────────────────────────────
def load_model(model_size: str, device: str, compute_type: str, threads: int):
    info(f"Đang tải model '{model_size}'...")
    info(f"Device: {device} | Compute: {compute_type} | Threads: {threads}")
    if model_size == "large-v3":
        warn("large-v3 lần đầu tải ~3GB, có thể mất vài phút...")
    elif model_size == "medium":
        warn("medium lần đầu tải ~1.5GB...")

    t0 = time.time()
    model = WhisperModel(
        model_size,
        device=device,
        compute_type=compute_type,
        cpu_threads=threads,
        num_workers=2 if model_size != "large-v3" else 1,
    )
    ok(f"Model tải xong ({fmt_duration(time.time() - t0)})")
    return model


# ─── Chuyển 1 file audio ─────────────────────────────────────────────────────
def transcribe_file(
    model,
    audio_path: Path,
    output_dir: Path,
    language: str = "vi",
    beam_size: int = 5,
) -> dict:
    """
    Transcribe 1 file audio, trả về dict kết quả.
    Lưu ra: .txt, .srt, .json trong output_dir.
    """
    if not audio_path.exists():
        err(f"Không tìm thấy file: {audio_path}")
        return {}

    info(f"Xử lý: {audio_path.name}")
    t0 = time.time()

    # Chạy transcribe
    segments_gen, audio_info = model.transcribe(
        str(audio_path),
        language=language,
        beam_size=beam_size,
        vad_filter=True,                          # Lọc khoảng im lặng
        vad_parameters=dict(
            min_silence_duration_ms=500,
            speech_pad_ms=200,
        ),
        word_timestamps=True,                     # Timestamp từng từ
        condition_on_previous_text=True,          # Cải thiện độ liền mạch
    )

    # Thu thập segments (generator → list)
    segments = []
    print()
    for seg in segments_gen:
        text = seg.text.strip()
        if not text:
            continue
        segments.append({
            "id":    len(segments) + 1,
            "start": round(seg.start, 3),
            "end":   round(seg.end, 3),
            "text":  text,
        })
        # In realtime từng đoạn
        ts = f"{Fore.CYAN}[{fmt_time(seg.start)} → {fmt_time(seg.end)}]{Style.RESET_ALL}"
        print(f"  {ts}  {text}")

    elapsed = time.time() - t0
    print()

    if not segments:
        warn("Không nhận diện được nội dung trong file audio này.")
        return {}

    # ── Lưu kết quả ──────────────────────────────────────────────────────────
    output_dir.mkdir(parents=True, exist_ok=True)
    stem = audio_path.stem  # tên file không có đuôi

    # 1. TXT — dễ đọc
    txt_path = output_dir / f"{stem}_transcript.txt"
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(f"File: {audio_path.name}\n")
        f.write(f"Ngôn ngữ: {audio_info.language} ({audio_info.language_probability:.0%})\n")
        f.write(f"Tổng thời gian: {fmt_time(audio_info.duration)}\n")
        f.write("=" * 60 + "\n\n")
        for seg in segments:
            f.write(f"[{fmt_time(seg['start'])} → {fmt_time(seg['end'])}]\n")
            f.write(f"{seg['text']}\n\n")
        f.write("=" * 60 + "\n")
        f.write("TOÀN VĂN:\n")
        f.write(" ".join(s["text"] for s in segments))

    # 2. SRT — phụ đề
    srt_path = output_dir / f"{stem}_transcript.srt"
    with open(srt_path, "w", encoding="utf-8") as f:
        for seg in segments:
            f.write(f"{seg['id']}\n")
            f.write(f"{fmt_srt(seg['start'])} --> {fmt_srt(seg['end'])}\n")
            f.write(f"{seg['text']}\n\n")

    # 3. JSON — để xử lý NLP tiếp theo
    result = {
        "file":              audio_path.name,
        "language":          audio_info.language,
        "language_prob":     round(audio_info.language_probability, 4),
        "duration_seconds":  round(audio_info.duration, 2),
        "process_time_sec":  round(elapsed, 2),
        "total_segments":    len(segments),
        "total_words":       sum(len(s["text"].split()) for s in segments),
        "full_text":         " ".join(s["text"] for s in segments),
        "segments":          segments,
    }
    json_path = output_dir / f"{stem}_transcript.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    # ── Tóm tắt ──────────────────────────────────────────────────────────────
    ok(f"Hoàn thành trong {fmt_duration(elapsed)}")
    info(f"Ngôn ngữ phát hiện : {audio_info.language} ({audio_info.language_probability:.0%})")
    info(f"Thời lượng audio   : {fmt_time(audio_info.duration)}")
    info(f"Tổng đoạn          : {len(segments)}")
    info(f"Tổng từ            : {sum(len(s['text'].split()) for s in segments)}")
    info(f"Tốc độ xử lý       : {audio_info.duration / elapsed:.1f}× realtime")
    print()
    ok(f"Đã lưu:")
    print(f"     {Fore.WHITE}{txt_path}{Style.RESET_ALL}")
    print(f"     {Fore.WHITE}{srt_path}{Style.RESET_ALL}")
    print(f"     {Fore.WHITE}{json_path}{Style.RESET_ALL}")

    return result


# ─── Xử lý cả thư mục ────────────────────────────────────────────────────────
SUPPORTED_FORMATS = {".mp3", ".wav", ".m4a", ".ogg", ".flac", ".mp4", ".webm", ".aac"}

def transcribe_folder(model, folder: Path, output_dir: Path, language: str, beam_size: int):
    audio_files = [f for f in folder.iterdir() if f.suffix.lower() in SUPPORTED_FORMATS]
    if not audio_files:
        err(f"Không tìm thấy file audio nào trong: {folder}")
        return

    info(f"Tìm thấy {len(audio_files)} file audio trong '{folder}'")
    summary = []

    for i, audio_path in enumerate(sorted(audio_files), 1):
        print()
        print(f"{Fore.YELLOW}{'─'*60}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}[{i}/{len(audio_files)}] {audio_path.name}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}{'─'*60}{Style.RESET_ALL}")
        result = transcribe_file(model, audio_path, output_dir, language, beam_size)
        if result:
            summary.append({
                "file":   result["file"],
                "words":  result["total_words"],
                "duration": result["duration_seconds"],
                "time":   result["process_time_sec"],
            })

    # Lưu summary toàn bộ
    if summary:
        summary_path = output_dir / "summary.json"
        with open(summary_path, "w", encoding="utf-8") as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
        print()
        ok(f"Tổng kết: {len(summary)} file | Đã lưu summary → {summary_path}")


# ─── Main ─────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description="Chuyển audio tiếng Việt sang text bằng faster-whisper"
    )
    parser.add_argument("--audio",   type=str, default="audio.mp3",
                        help="Đường dẫn file audio (mặc định: audio.mp3)")
    parser.add_argument("--folder",  type=str, default=None,
                        help="Xử lý cả thư mục audio (bỏ qua --audio)")
    parser.add_argument("--model",   type=str, default="medium",
                        choices=["tiny", "base", "small", "medium", "large-v2", "large-v3"],
                        help="Kích thước model (mặc định: medium)")
    parser.add_argument("--output",  type=str, default="output",
                        help="Thư mục lưu kết quả (mặc định: output/)")
    parser.add_argument("--language",type=str, default="vi",
                        help="Ngôn ngữ (mặc định: vi)")
    parser.add_argument("--threads", type=int, default=8,
                        help="Số luồng CPU (mặc định: 8)")
    parser.add_argument("--beam",    type=int, default=5,
                        help="Beam size (mặc định: 5, tăng để chính xác hơn)")
    parser.add_argument("--large",   action="store_true",
                        help="Dùng nhanh: tự động chọn large-v3")
    args = parser.parse_args()

    # Banner
    print()
    print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}  Audio → Text  |  faster-whisper  |  CPU mode{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
    print()

    # Nếu --large thì override model
    model_size = "large-v3" if args.large else args.model

    # Tải model (dùng CPU vì máy không có GPU NVIDIA)
    model = load_model(
        model_size  = model_size,
        device      = "cpu",
        compute_type= "int8",
        threads     = args.threads,
    )

    output_dir = Path(args.output)

    # Xử lý thư mục hoặc 1 file
    if args.folder:
        transcribe_folder(model, Path(args.folder), output_dir, args.language, args.beam)
    else:
        audio_path = Path(args.audio)
        transcribe_file(model, audio_path, output_dir, args.language, args.beam)

    print()
    print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
    ok("Tất cả hoàn thành!")
    print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}")


if __name__ == "__main__":
    main()
    
