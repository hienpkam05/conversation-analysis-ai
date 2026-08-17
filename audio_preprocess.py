"""
=============================================================
  Tiền xử lý Audio  |  Tăng độ chính xác Whisper
  - Khử nhiễu nền (noise reduction)
  - Chuẩn hóa âm lượng (normalize volume)
  - Chuyển về 16kHz mono (chuẩn Whisper)
  - Lọc tần số giọng người (bandpass filter)
=============================================================
Cài đặt (chạy 1 lần):
    pip install pydub noisereduce librosa soundfile numpy scipy

Cần thêm ffmpeg:
    Windows: tải tại https://ffmpeg.org/download.html
             giải nén, thêm thư mục bin vào PATH
    Hoặc dùng: pip install ffmpeg-python imageio-ffmpeg
"""

import os
import shutil
import tempfile
import time
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")

# ─── Kiểm tra thư viện ───────────────────────────────────────────────────────
MISSING = []
try:
    import numpy as np
except ImportError:
    MISSING.append("numpy")

try:
    import librosa
    import soundfile as sf
except ImportError:
    MISSING.append("librosa soundfile")

try:
    import noisereduce as nr
except ImportError:
    MISSING.append("noisereduce")

try:
    from scipy import signal
except ImportError:
    MISSING.append("scipy")

if MISSING:
    print("[LỖI] Chưa cài đủ thư viện. Chạy lệnh:")
    print(f"      pip install {' '.join(MISSING)}")
    raise ImportError(f"Thiếu: {MISSING}")


# ─── Cấu hình mặc định ───────────────────────────────────────────────────────
DEFAULT_CONFIG = {
    # Tần số mẫu chuẩn Whisper
    "target_sr": 16000,

    # Khử nhiễu
    "noise_reduce":        True,
    "noise_reduce_strength": 0.75,   # 0.0–1.0 (cao hơn = mạnh hơn, nhưng có thể làm mất tiếng)
    "stationary_noise":    True,     # True nếu nhiễu nền ổn định (tiếng quạt, máy lạnh...)

    # Chuẩn hóa âm lượng
    "normalize_volume":    True,
    "target_lufs":         -16.0,    # Loudness chuẩn cho speech (LUFS)
    "headroom_db":          1.0,     # Để lại headroom tránh clipping

    # Lọc tần số giọng người
    "bandpass_filter":     True,
    "freq_low":            80,       # Hz — loại bỏ rumble thấp
    "freq_high":           8000,     # Hz — giọng người tập trung 80–8000 Hz

    # Loại bỏ khoảng lặng quá dài
    "trim_silence":        True,
    "silence_threshold":   -40,      # dB
    "min_silence_len":     1000,     # ms — khoảng lặng dài hơn này sẽ bị cắt ngắn
    "keep_silence":        300,      # ms — giữ lại bao nhiêu ms silence ở mỗi đầu

    # Tăng tốc độ xử lý
    "chunk_size_sec":      30,       # Xử lý từng đoạn 30 giây (tiết kiệm RAM)
}


# ─── Tiện ích ────────────────────────────────────────────────────────────────
def fmt_duration(s: float) -> str:
    return f"{s:.1f}s" if s < 60 else f"{s/60:.1f} phút"

def fmt_size(path: Path) -> str:
    size = path.stat().st_size
    return f"{size/1024/1024:.1f} MB"

def db_to_linear(db: float) -> float:
    return 10 ** (db / 20)


# ─── Bước 1: Đọc & chuyển về 16kHz mono ─────────────────────────────────────
def load_audio(audio_path: Path, target_sr: int = 16000) -> tuple:
    """
    Đọc file audio bất kỳ định dạng, chuyển về mono 16kHz.
    Trả về (numpy array float32, sample_rate)
    """
    # Dùng librosa để load — hỗ trợ mp3, wav, m4a, ogg, flac...
    y, sr = librosa.load(str(audio_path), sr=target_sr, mono=True)
    return y.astype(np.float32), sr


# ─── Bước 2: Lọc tần số giọng người (bandpass) ───────────────────────────────
def apply_bandpass(y: np.ndarray, sr: int, low: int = 80, high: int = 8000) -> np.ndarray:
    """
    Lọc giữ lại dải tần số giọng người (80–8000 Hz).
    Loại bỏ tiếng ồn rất thấp (rumble) và rất cao (hiss).
    """
    nyquist = sr / 2
    low_norm  = low  / nyquist
    high_norm = high / nyquist

    # Clamp để tránh lỗi
    low_norm  = max(0.001, min(low_norm,  0.999))
    high_norm = max(0.001, min(high_norm, 0.999))
    if low_norm >= high_norm:
        return y

    b, a = signal.butter(4, [low_norm, high_norm], btype="band")
    return signal.filtfilt(b, a, y).astype(np.float32)


# ─── Bước 3: Khử nhiễu ───────────────────────────────────────────────────────
def apply_noise_reduction(
    y: np.ndarray, sr: int,
    strength: float = 0.75,
    stationary: bool = True,
) -> np.ndarray:
    """
    Khử nhiễu nền bằng noisereduce.
    stationary=True  : nhiễu ổn định (tiếng quạt, máy lạnh)
    stationary=False : nhiễu thay đổi (tiếng xe, gió)
    """
    reduced = nr.reduce_noise(
        y=y,
        sr=sr,
        prop_decrease=strength,
        stationary=stationary,
        n_std_thresh_stationary=1.5,
    )
    return reduced.astype(np.float32)


# ─── Bước 4: Chuẩn hóa âm lượng ─────────────────────────────────────────────
def apply_normalization(y: np.ndarray, target_lufs: float = -16.0, headroom_db: float = 1.0) -> np.ndarray:
    """
    Chuẩn hóa âm lượng về mức chuẩn.
    Tránh quá nhỏ (Whisper bỏ sót) hoặc quá to (clipping).
    """
    # Peak normalization với headroom
    peak = np.max(np.abs(y))
    if peak > 0:
        max_linear = db_to_linear(-headroom_db)
        y = y * (max_linear / peak)

    # RMS-based loudness normalization
    rms = np.sqrt(np.mean(y ** 2))
    if rms > 0:
        target_rms = db_to_linear(target_lufs)
        gain = min(target_rms / rms, db_to_linear(-headroom_db) / np.max(np.abs(y) + 1e-9))
        y = y * gain

    return np.clip(y, -1.0, 1.0).astype(np.float32)


# ─── Bước 5: Cắt khoảng lặng ─────────────────────────────────────────────────
def apply_trim_silence(y: np.ndarray, sr: int, top_db: float = 40) -> np.ndarray:
    """
    Cắt bỏ khoảng lặng ở đầu và cuối file.
    """
    y_trimmed, _ = librosa.effects.trim(y, top_db=top_db)
    return y_trimmed.astype(np.float32)


# ─── Pipeline chính ──────────────────────────────────────────────────────────
def preprocess_audio(
    audio_path: Path,
    output_path: Path = None,
    config: dict = None,
    progress_callback=None,   # callback(step: str, pct: int)
) -> Path:
    """
    Pipeline tiền xử lý đầy đủ cho 1 file audio.
    Trả về đường dẫn file wav đã xử lý.
    """
    cfg = {**DEFAULT_CONFIG, **(config or {})}

    def _progress(msg, pct=0):
        if progress_callback:
            progress_callback(msg, pct)
        else:
            print(f"  [{pct:3d}%] {msg}")

    t_start = time.time()
    audio_path = Path(audio_path)

    # Xác định output path
    if output_path is None:
        output_path = audio_path.parent / f"{audio_path.stem}_preprocessed.wav"
    output_path = Path(output_path)

    _progress(f"Đọc file: {audio_path.name}", 5)
    y, sr = load_audio(audio_path, cfg["target_sr"])
    duration = len(y) / sr
    _progress(f"Thời lượng: {fmt_duration(duration)} | SR: {sr}Hz | Samples: {len(y):,}", 15)

    # Bước 2: Bandpass filter
    if cfg["bandpass_filter"]:
        _progress("Lọc tần số giọng người (bandpass)...", 25)
        y = apply_bandpass(y, sr, cfg["freq_low"], cfg["freq_high"])

    # Bước 3: Khử nhiễu
    if cfg["noise_reduce"]:
        _progress("Khử nhiễu nền...", 40)
        y = apply_noise_reduction(
            y, sr,
            strength=cfg["noise_reduce_strength"],
            stationary=cfg["stationary_noise"],
        )

    # Bước 4: Chuẩn hóa âm lượng
    if cfg["normalize_volume"]:
        _progress("Chuẩn hóa âm lượng...", 65)
        y = apply_normalization(y, cfg["target_lufs"], cfg["headroom_db"])

    # Bước 5: Trim silence
    if cfg["trim_silence"]:
        _progress("Cắt khoảng lặng...", 80)
        y = apply_trim_silence(y, sr, top_db=abs(cfg["silence_threshold"]))

    # Lưu file wav 16kHz mono
    _progress("Lưu file đã xử lý...", 90)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    sf.write(str(output_path), y, sr, subtype="PCM_16")

    elapsed = time.time() - t_start
    size_in  = fmt_size(audio_path)
    size_out = fmt_size(output_path)
    _progress(f"Hoàn thành! {size_in} → {size_out} | {fmt_duration(elapsed)}", 100)

    return output_path


# ─── Tiện ích batch ───────────────────────────────────────────────────────────
def preprocess_batch(
    audio_paths: list,
    output_dir: Path,
    config: dict = None,
    progress_callback=None,
) -> list:
    """Tiền xử lý nhiều file, trả về list các file wav đã xử lý."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    results = []
    for i, p in enumerate(audio_paths):
        p = Path(p)
        out = output_dir / f"{p.stem}_preprocessed.wav"
        def _cb(msg, pct, i=i, name=p.name):
            if progress_callback:
                progress_callback(f"[{i+1}/{len(audio_paths)}] {name}: {msg}", pct)
        try:
            result = preprocess_audio(p, out, config, _cb)
            results.append(result)
        except Exception as e:
            print(f"[LỖI] {p.name}: {e}")
    return results


# ─── Chạy độc lập (CLI) ───────────────────────────────────────────────────────
if __name__ == "__main__":
    import argparse, sys

    parser = argparse.ArgumentParser(description="Tiền xử lý audio cho Whisper")
    parser.add_argument("--audio",  required=True, help="File audio đầu vào")
    parser.add_argument("--output", default=None,  help="File wav đầu ra")
    parser.add_argument("--no-denoise",   action="store_true", help="Tắt khử nhiễu")
    parser.add_argument("--no-normalize", action="store_true", help="Tắt chuẩn hóa")
    parser.add_argument("--no-bandpass",  action="store_true", help="Tắt lọc tần số")
    parser.add_argument("--strength", type=float, default=0.75, help="Cường độ khử nhiễu 0.0–1.0")
    args = parser.parse_args()

    config = {
        "noise_reduce":          not args.no_denoise,
        "normalize_volume":      not args.no_normalize,
        "bandpass_filter":       not args.no_bandpass,
        "noise_reduce_strength": args.strength,
    }

    print("\n" + "="*55)
    print("  Tiền xử lý Audio  |  Tăng độ chính xác Whisper")
    print("="*55 + "\n")

    out = preprocess_audio(Path(args.audio), Path(args.output) if args.output else None, config)
    print(f"\n[OK] File đầu ra: {out}")
    print("\nChạy Whisper với file đã xử lý:")
    print(f"  python transcribe.py --audio {out}")
