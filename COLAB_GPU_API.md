# Colab GPU API cho transcribe audio

File này dùng khi muốn web Django/Vue ở máy local gửi audio lên Google Colab để xử lý bằng GPU.

## 1. Bật GPU trong Colab

Vào:

```text
Runtime -> Change runtime type -> T4 GPU
```

Kiểm tra:

```python
!nvidia-smi
```

## 2. Cài thư viện

```python
!pip install faster-whisper fastapi uvicorn python-multipart
```

## 3. Tạo API FastAPI

```python
%%writefile app.py
import tempfile
import time
from pathlib import Path

from fastapi import FastAPI, File, Form, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from faster_whisper import WhisperModel

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

BAD_PHRASES = [
    "hãy subscribe",
    "ghiền mì gõ",
    "lalaschool",
    "không bỏ lỡ những video hấp dẫn",
    "subscribe cho kênh",
]


def is_bad_segment(text, seg=None):
    lower = text.lower()
    if any(phrase in lower for phrase in BAD_PHRASES):
        return True

    words = lower.split()
    if len(words) >= 12 and len(set(words)) / len(words) < 0.2:
        return True

    if seg is not None:
        if getattr(seg, "no_speech_prob", 0) > 0.65:
            return True
        if getattr(seg, "avg_logprob", 0) < -0.9:
            return True
        if getattr(seg, "compression_ratio", 0) > 2.2:
            return True

    return False


def dialogue_text(segments):
    lines = []
    for index, segment in enumerate(segments, 1):
        lines.append(
            f"{index}. [{segment['start']:.1f}s - {segment['end']:.1f}s]\n{segment['text']}"
        )
    return "\n\n".join(lines)


model = WhisperModel(
    "large-v3-turbo",
    device="cuda",
    compute_type="float16",
)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/transcribe")
async def transcribe(
    audio: UploadFile = File(...),
    language: str = Form("vi"),
    beam_size: int = Form(1),
):
    started_at = time.time()
    beam_size = max(1, min(5, int(beam_size)))
    suffix = Path(audio.filename).suffix or ".mp3"

    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp:
        temp.write(await audio.read())
        audio_path = temp.name

    segments_gen, info = model.transcribe(
        audio_path,
        language=language or None,
        beam_size=int(beam_size),
        best_of=int(beam_size),
        temperature=0.0,
        vad_filter=True,
        vad_parameters={
            "threshold": 0.45,
            "min_speech_duration_ms": 200,
            "min_silence_duration_ms": 600,
            "speech_pad_ms": 120,
        },
        condition_on_previous_text=False,
        compression_ratio_threshold=2.2,
        log_prob_threshold=-1.2,
        no_speech_threshold=0.8,
        repetition_penalty=1.15,
    )

    segments = []
    for segment in segments_gen:
        text = segment.text.strip()
        if text and not is_bad_segment(text, segment):
            segments.append(
                {
                    "id": len(segments) + 1,
                    "start": round(segment.start, 3),
                    "end": round(segment.end, 3),
                    "text": text,
                }
            )

    return {
        "engine": "colab",
        "model": "large-v3-turbo",
        "language": info.language,
        "language_prob": round(info.language_probability, 4),
        "duration_seconds": round(info.duration, 2),
        "process_time_sec": round(time.time() - started_at, 2),
        "total_segments": len(segments),
        "total_words": sum(len(item["text"].split()) for item in segments),
        "full_text": " ".join(item["text"] for item in segments),
        "dialogue_text": dialogue_text(segments),
        "segments": segments,
    }
```

## 4. Chạy API và mở public URL

Trong web, `Độ dò kết quả` nên để `1` cho cuộc gọi. Nếu audio rõ có thể thử `3`. Không nên kéo cao vì chạy chậm hơn và bộ lọc có thể loại bớt đoạn không chắc chắn.

### Cách A: Cloudflare Tunnel, không cần tài khoản

```python
!wget -q https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 -O cloudflared
!chmod +x cloudflared
```

```python
import subprocess
import time

api = subprocess.Popen([
    "uvicorn", "app:app",
    "--host", "0.0.0.0",
    "--port", "8000",
])

time.sleep(3)

tunnel = subprocess.Popen(
    ["./cloudflared", "tunnel", "--url", "http://127.0.0.1:8000"],
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True,
)

for line in tunnel.stdout:
    print(line, end="")
    if "trycloudflare.com" in line:
        print("\nDán URL dạng https://xxx.trycloudflare.com vào ô Colab API URL trong web.")
```

### Cách B: ngrok

Ngrok cần token tại `https://dashboard.ngrok.com/get-started/your-authtoken`.

```python
!pip install pyngrok
```

```python
from pyngrok import ngrok
import subprocess
import time

ngrok.set_auth_token("DAN_TOKEN_NGROK_VAO_DAY")

api = subprocess.Popen([
    "uvicorn", "app:app",
    "--host", "0.0.0.0",
    "--port", "8000",
])

time.sleep(3)
public_url = ngrok.connect(8000)
print("Dán URL này vào web:", public_url)
```

Nếu URL in ra là:

```text
https://abc.trycloudflare.com
```

thì trong web có thể dán nguyên URL đó. Backend sẽ tự gọi:

```text
https://abc.trycloudflare.com/transcribe
```
