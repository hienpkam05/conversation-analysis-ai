# Web app chuyển audio tư vấn tuyển dụng thành văn bản

Ứng dụng gồm:

- `backend/`: Django API nhận file audio và gọi `faster-whisper`.
- `frontend/`: Vue 3 + Vite cho màn hình upload audio và xem transcript.

## Cài backend

```powershell
cd D:\NCKH
.\venv\Scripts\python.exe -m pip install -r backend\requirements.txt
cd backend
..\venv\Scripts\python.exe manage.py migrate
..\venv\Scripts\python.exe manage.py runserver 127.0.0.1:8000
```

## Cài frontend

Do PowerShell trên máy có thể chặn `npm.ps1`, dùng `npm.cmd`:

```powershell
cd D:\NCKH\frontend
npm.cmd install
npm.cmd run dev
```

Mở trình duyệt tại:

```text
http://127.0.0.1:5173
```

## API chính

```text
POST http://127.0.0.1:8000/api/transcribe/
```

Form data:

- `audio`: file audio
- `model`: `tiny`, `base`, `small`, `medium`, `large-v3`
- `language`: `vi`, `en`, hoặc rỗng để tự phát hiện
- `beam_size`: 1-10
- `preprocess`: `true` hoặc `false`

Kết quả transcript cũng được lưu vào thư mục `output/` ở dạng `.txt`, `.srt`, `.json`.

## Dùng Colab GPU

Xem [COLAB_GPU_API.md](COLAB_GPU_API.md). Sau khi Colab in ra URL public, chọn `Colab GPU` trên giao diện web và dán URL đó vào ô `Colab API URL`.
