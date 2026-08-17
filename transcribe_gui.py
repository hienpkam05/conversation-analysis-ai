"""
=============================================================
  Audio → Text  |  faster-whisper + Tiền xử lý Audio
  Máy: HP ZBook Firefly i7-1185G7 | 16GB RAM | Intel Iris Xe
=============================================================
Cài đặt (chạy 1 lần):
    pip install faster-whisper pydub noisereduce librosa soundfile numpy scipy

Chạy:
    python transcribe_gui.py

Đặt cả 2 file trong cùng thư mục:
    transcribe_gui.py
    audio_preprocess.py
"""

import json, os, sys, threading, time, tkinter as tk, tempfile
from pathlib import Path
from tkinter import filedialog, messagebox, scrolledtext, ttk

try:
    from faster_whisper import WhisperModel
except ImportError:
    root = tk.Tk(); root.withdraw()
    messagebox.showerror("Thiếu thư viện", "Chưa cài faster-whisper!\n\npip install faster-whisper")
    sys.exit(1)

try:
    from audio_preprocess import preprocess_audio, DEFAULT_CONFIG
    HAS_PREPROCESS = True
except ImportError:
    HAS_PREPROCESS = False

SUPPORTED = {".mp3", ".wav", ".m4a", ".ogg", ".flac", ".mp4", ".webm", ".aac"}

def fmt_time(s):
    return f"{int(s//3600):02}:{int((s%3600)//60):02}:{int(s%60):02}"

def fmt_srt(s):
    return f"{int(s//3600):02}:{int((s%3600)//60):02}:{int(s%60):02},{int((s%1)*1000):03}"

def fmt_size(p):
    b = Path(p).stat().st_size
    return f"{b/1024/1024:.1f} MB" if b >= 1024*1024 else f"{b/1024:.1f} KB"


class App:
    def __init__(self, root):
        self.root = root
        self.root.title("Audio → Text  |  faster-whisper")
        self.root.geometry("860x720")
        self.root.configure(bg="#1e1e2e")
        self.model = None
        self.model_size_loaded = None
        self.is_running = False
        self.selected_files = []
        self.BG = "#1e1e2e"; self.SURF = "#2a2a3e"; self.BORDER = "#3d3d5c"
        self.ACCENT = "#7c6af7"; self.GREEN = "#50fa7b"; self.YELLOW = "#f1fa8c"
        self.RED = "#ff5555"; self.CYAN = "#8be9fd"; self.FG = "#f8f8f2"; self.MUTED = "#6272a4"
        self._build()

    def _build(self):
        hdr = tk.Frame(self.root, bg=self.ACCENT, height=50)
        hdr.pack(fill="x"); hdr.pack_propagate(False)
        tk.Label(hdr, text="  Audio → Text  |  faster-whisper  |  CPU mode",
                 bg=self.ACCENT, fg="white", font=("Segoe UI", 13, "bold")).pack(side="left", padx=16)

        style = ttk.Style(); style.theme_use("clam")
        style.configure("Dark.TNotebook", background=self.BG, borderwidth=0)
        style.configure("Dark.TNotebook.Tab", background=self.SURF, foreground=self.MUTED,
                        padding=[14,6], font=("Segoe UI", 10))
        style.map("Dark.TNotebook.Tab", background=[("selected", self.BG)],
                  foreground=[("selected", self.FG)])
        style.configure("P.Horizontal.TProgressbar", troughcolor=self.SURF,
                        background=self.ACCENT, bordercolor=self.BG,
                        lightcolor=self.ACCENT, darkcolor=self.ACCENT)

        nb = ttk.Notebook(self.root, style="Dark.TNotebook")
        nb.pack(fill="both", expand=True, padx=12, pady=10)
        t1 = tk.Frame(nb, bg=self.BG); nb.add(t1, text="  Chuyển đổi  ")
        t2 = tk.Frame(nb, bg=self.BG); nb.add(t2, text="  Tiền xử lý Audio  ")
        t3 = tk.Frame(nb, bg=self.BG); nb.add(t3, text="  Cài đặt nâng cao  ")
        self._tab_main(t1); self._tab_preprocess(t2); self._tab_settings(t3)

    def _tab_main(self, p):
        left = tk.Frame(p, bg=self.BG, width=235)
        left.pack(side="left", fill="y", padx=(0,10), pady=8); left.pack_propagate(False)

        self._sec(left, "Model")
        self.model_var = tk.StringVar(value="medium")
        for txt, val in [("tiny   — rất nhanh", "tiny"), ("base   — nhanh", "base"),
                         ("small  — nhẹ", "small"), ("medium — khuyến nghị ✓", "medium"),
                         ("large-v3 — chính xác nhất", "large-v3")]:
            tk.Radiobutton(left, text=txt, variable=self.model_var, value=val,
                           bg=self.BG, fg=self.FG, selectcolor=self.SURF,
                           activebackground=self.BG, font=("Consolas", 9)).pack(anchor="w", pady=1)

        self._sec(left, "Ngôn ngữ")
        self.lang_var = tk.StringVar(value="vi")
        for txt, val in [("Tiếng Việt", "vi"), ("Tự phát hiện", ""), ("English", "en")]:
            tk.Radiobutton(left, text=txt, variable=self.lang_var, value=val,
                           bg=self.BG, fg=self.FG, selectcolor=self.SURF,
                           activebackground=self.BG, font=("Segoe UI", 10)).pack(anchor="w", pady=1)

        self._sec(left, "Tùy chọn")
        self.vad_var = tk.BooleanVar(value=True)
        self.word_ts_var = tk.BooleanVar(value=True)
        self.preproc_var = tk.BooleanVar(value=HAS_PREPROCESS)
        for txt, var in [("Lọc khoảng im lặng (VAD)", self.vad_var),
                         ("Timestamp từng từ", self.word_ts_var),
                         ("Tiền xử lý audio (khử nhiễu...)", self.preproc_var)]:
            state = "normal" if HAS_PREPROCESS or "Tiền" not in txt else "disabled"
            tk.Checkbutton(left, text=txt, variable=var, state=state,
                           bg=self.BG, fg=self.FG, selectcolor=self.SURF,
                           activebackground=self.BG, font=("Segoe UI", 10)).pack(anchor="w")

        if not HAS_PREPROCESS:
            tk.Label(left, text="(Cài thêm ở tab Tiền xử lý)", bg=self.BG,
                     fg=self.MUTED, font=("Segoe UI", 8)).pack(anchor="w")

        self._sec(left, "Thư mục lưu")
        self.output_var = tk.StringVar(value=str(Path.cwd() / "output"))
        fr = tk.Frame(left, bg=self.BG); fr.pack(fill="x")
        tk.Entry(fr, textvariable=self.output_var, bg=self.SURF, fg=self.FG,
                 insertbackground=self.FG, relief="flat", font=("Consolas", 8)
                 ).pack(side="left", fill="x", expand=True)
        tk.Button(fr, text="...", command=self._choose_out, bg=self.BORDER,
                  fg=self.FG, relief="flat", padx=4).pack(side="right")

        right = tk.Frame(p, bg=self.BG)
        right.pack(side="left", fill="both", expand=True, pady=8)

        fpf = tk.Frame(right, bg=self.SURF); fpf.pack(fill="x", pady=(0,8))
        br = tk.Frame(fpf, bg=self.SURF); br.pack(fill="x", padx=10, pady=8)
        self._btn(br, "Chọn file audio", self._pick_files, self.ACCENT).pack(side="left", padx=(0,6))
        self._btn(br, "Chọn thư mục", self._pick_folder, self.BORDER).pack(side="left", padx=(0,6))
        self._btn(br, "Xóa danh sách", self._clear_files, self.BORDER).pack(side="left")
        tk.Label(fpf, text="Danh sách file:", bg=self.SURF, fg=self.MUTED,
                 font=("Segoe UI", 9)).pack(anchor="w", padx=10)
        self.listbox = tk.Listbox(fpf, height=4, bg=self.BG, fg=self.FG,
                                  selectbackground=self.ACCENT, relief="flat",
                                  font=("Consolas", 9), activestyle="none")
        self.listbox.pack(fill="x", padx=10, pady=(2,4))
        self.count_lbl = tk.Label(fpf, text="Chưa chọn file nào", bg=self.SURF,
                                  fg=self.MUTED, font=("Segoe UI", 9))
        self.count_lbl.pack(anchor="w", padx=10, pady=(0,6))

        rf = tk.Frame(right, bg=self.BG); rf.pack(fill="x", pady=(0,8))
        self.run_btn = self._btn(rf, "  Bắt đầu chuyển đổi  ", self._start,
                                 self.GREEN, fg="#1e1e2e", font=("Segoe UI", 11, "bold"))
        self.run_btn.pack(side="left")
        self.stop_btn = self._btn(rf, "Dừng", self._stop, self.RED)
        self.stop_btn.pack(side="left", padx=(8,0))
        self.stop_btn.config(state="disabled")

        self.prog_lbl = tk.Label(right, text="Sẵn sàng", bg=self.BG, fg=self.MUTED,
                                 font=("Segoe UI", 9))
        self.prog_lbl.pack(anchor="w")
        self.progress = ttk.Progressbar(right, style="P.Horizontal.TProgressbar",
                                        mode="indeterminate")
        self.progress.pack(fill="x", pady=(0,8))

        tk.Label(right, text="Nhật ký:", bg=self.BG, fg=self.MUTED,
                 font=("Segoe UI", 9)).pack(anchor="w")
        self.log = scrolledtext.ScrolledText(right, height=16, bg=self.SURF, fg=self.FG,
                                             insertbackground=self.FG, relief="flat",
                                             font=("Consolas", 9), state="disabled")
        self.log.pack(fill="both", expand=True)
        for tag, color in [("ok", self.GREEN), ("info", self.CYAN), ("warn", self.YELLOW),
                           ("err", self.RED), ("ts", self.ACCENT), ("muted", self.MUTED), ("seg", self.FG)]:
            self.log.tag_config(tag, foreground=color)

        bf = tk.Frame(right, bg=self.BG); bf.pack(fill="x", pady=(6,0))
        self._btn(bf, "Mở thư mục output", self._open_out, self.BORDER).pack(side="right")
        self._logln("Chào mừng! Chọn file audio và nhấn 'Bắt đầu chuyển đổi'.\n", "info")

    def _tab_preprocess(self, p):
        if not HAS_PREPROCESS:
            tk.Label(p, text=(
                "Để bật tính năng tiền xử lý audio, chạy lệnh sau trong terminal VSCode:\n\n"
                "pip install pydub noisereduce librosa soundfile numpy scipy\n\n"
                "Sau đó đặt file audio_preprocess.py cùng thư mục với transcribe_gui.py\n"
                "và khởi động lại chương trình."),
                bg=self.BG, fg=self.YELLOW, font=("Consolas", 11), justify="left"
            ).pack(padx=24, pady=24, anchor="w")
            return

        pad = dict(padx=16, pady=5)
        tk.Label(p, text="Cài đặt tiền xử lý Audio — chạy trước khi transcribe",
                 bg=self.BG, fg=self.ACCENT, font=("Segoe UI", 11, "bold")
                 ).pack(anchor="w", padx=16, pady=(14,8))

        # Khử nhiễu
        nrf = tk.LabelFrame(p, text="  Khử nhiễu (Noise Reduction)  ",
                            bg=self.BG, fg=self.CYAN, font=("Segoe UI", 10))
        nrf.pack(fill="x", **pad)
        self.nr_var = tk.BooleanVar(value=True)
        tk.Checkbutton(nrf, text="Bật khử nhiễu nền",
                       variable=self.nr_var, bg=self.BG, fg=self.FG,
                       selectcolor=self.SURF, activebackground=self.BG,
                       font=("Segoe UI", 10)).pack(anchor="w", padx=10, pady=4)
        sr_row = tk.Frame(nrf, bg=self.BG); sr_row.pack(fill="x", padx=10, pady=(0,4))
        tk.Label(sr_row, text="Cường độ:", bg=self.BG, fg=self.MUTED,
                 font=("Segoe UI", 9), width=12, anchor="w").pack(side="left")
        self.nr_strength = tk.DoubleVar(value=0.75)
        tk.Scale(sr_row, from_=0.1, to=1.0, resolution=0.05, variable=self.nr_strength,
                 orient="horizontal", bg=self.BG, fg=self.FG, highlightthickness=0,
                 troughcolor=self.SURF, activebackground=self.ACCENT, length=180
                 ).pack(side="left")
        tk.Label(sr_row, textvariable=self.nr_strength, bg=self.BG, fg=self.CYAN,
                 font=("Consolas", 9), width=4).pack(side="left")
        tk.Label(sr_row, text="← 0.5 nhẹ  |  0.75 cân bằng  |  1.0 mạnh →",
                 bg=self.BG, fg=self.MUTED, font=("Segoe UI", 8)).pack(side="left", padx=6)
        self.stationary_var = tk.BooleanVar(value=True)
        tk.Checkbutton(nrf, text="Nhiễu ổn định (quạt, máy lạnh, điều hoà)  — bỏ tick nếu nhiễu thay đổi (gió, xe...)",
                       variable=self.stationary_var, bg=self.BG, fg=self.FG,
                       selectcolor=self.SURF, activebackground=self.BG,
                       font=("Segoe UI", 9)).pack(anchor="w", padx=10, pady=(0,8))

        # Bandpass
        bpf = tk.LabelFrame(p, text="  Lọc tần số giọng người (Bandpass 80–8000 Hz)  ",
                            bg=self.BG, fg=self.CYAN, font=("Segoe UI", 10))
        bpf.pack(fill="x", **pad)
        self.bp_var = tk.BooleanVar(value=True)
        tk.Checkbutton(bpf, text="Bật lọc tần số — loại bỏ tiếng ù thấp và hiss cao, giữ lại giọng người",
                       variable=self.bp_var, bg=self.BG, fg=self.FG,
                       selectcolor=self.SURF, activebackground=self.BG,
                       font=("Segoe UI", 10)).pack(anchor="w", padx=10, pady=8)

        # Chuẩn hóa
        nvf = tk.LabelFrame(p, text="  Chuẩn hóa âm lượng  ",
                            bg=self.BG, fg=self.CYAN, font=("Segoe UI", 10))
        nvf.pack(fill="x", **pad)
        self.nv_var = tk.BooleanVar(value=True)
        tk.Checkbutton(nvf, text="Chuẩn hóa về -16 LUFS — tránh quá nhỏ (Whisper bỏ sót) hoặc quá to (clipping)",
                       variable=self.nv_var, bg=self.BG, fg=self.FG,
                       selectcolor=self.SURF, activebackground=self.BG,
                       font=("Segoe UI", 10)).pack(anchor="w", padx=10, pady=8)

        # Test
        tef = tk.LabelFrame(p, text="  Thử nghiệm trên 1 file  ",
                            bg=self.BG, fg=self.CYAN, font=("Segoe UI", 10))
        tef.pack(fill="x", **pad)
        r = tk.Frame(tef, bg=self.BG); r.pack(fill="x", padx=10, pady=6)
        self.test_file_var = tk.StringVar(value="Chưa chọn file")
        tk.Entry(r, textvariable=self.test_file_var, bg=self.SURF, fg=self.FG,
                 insertbackground=self.FG, relief="flat", font=("Consolas", 9)
                 ).pack(side="left", fill="x", expand=True)
        self._btn(r, "Chọn file", self._pick_test_file, self.BORDER).pack(side="left", padx=(6,0))
        self._btn(tef, "  Chạy tiền xử lý & lưu file _preprocessed.wav  ",
                  self._run_test_preprocess, self.ACCENT).pack(pady=(0,10))

        tk.Label(p, text="Nhật ký tiền xử lý:", bg=self.BG, fg=self.MUTED,
                 font=("Segoe UI", 9)).pack(anchor="w", padx=16)
        self.pp_log = scrolledtext.ScrolledText(p, height=7, bg=self.SURF, fg=self.FG,
                                                insertbackground=self.FG, relief="flat",
                                                font=("Consolas", 9), state="disabled")
        self.pp_log.pack(fill="both", expand=True, padx=16, pady=(2,10))
        self.pp_log.tag_config("ok", foreground=self.GREEN)
        self.pp_log.tag_config("info", foreground=self.CYAN)
        self.pp_log.tag_config("warn", foreground=self.YELLOW)

    def _tab_settings(self, p):
        pad = dict(padx=16, pady=6)
        tk.Label(p, text="Tham số Whisper nâng cao", bg=self.BG, fg=self.ACCENT,
                 font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=16, pady=(14,8))

        bf = tk.Frame(p, bg=self.BG); bf.pack(fill="x", **pad)
        tk.Label(bf, text="Beam size:", bg=self.BG, fg=self.MUTED,
                 font=("Segoe UI", 10), width=16, anchor="w").pack(side="left")
        self.beam_var = tk.IntVar(value=5)
        tk.Scale(bf, from_=1, to=10, resolution=1, variable=self.beam_var,
                 orient="horizontal", bg=self.BG, fg=self.FG, highlightthickness=0,
                 troughcolor=self.SURF, activebackground=self.ACCENT, length=180
                 ).pack(side="left")
        tk.Label(bf, textvariable=self.beam_var, bg=self.BG, fg=self.CYAN,
                 font=("Consolas", 10), width=3).pack(side="left")
        tk.Label(bf, text="(5 = mặc định  |  10 = chính xác hơn, chậm hơn ~20%)",
                 bg=self.BG, fg=self.MUTED, font=("Segoe UI", 8)).pack(side="left", padx=6)

        tk.Label(p, text="initial_prompt — gợi ý ngữ cảnh domain cho Whisper:",
                 bg=self.BG, fg=self.ACCENT, font=("Segoe UI", 10, "bold")
                 ).pack(anchor="w", padx=16, pady=(14,4))
        tk.Label(p, text="Mô tả bên dưới giúp Whisper nhận dạng đúng từ chuyên ngành tuyển dụng:",
                 bg=self.BG, fg=self.MUTED, font=("Segoe UI", 9)).pack(anchor="w", padx=16)
        self.prompt_var = tk.Text(p, height=5, bg=self.SURF, fg=self.FG,
                                  insertbackground=self.FG, relief="flat",
                                  font=("Consolas", 9), wrap="word")
        self.prompt_var.pack(fill="x", padx=16, pady=4)
        self.prompt_var.insert("1.0",
            "Đây là cuộc tư vấn tuyển dụng lao động Việt Nam. Các từ thường gặp: "
            "mức lương, ca làm việc, khu công nghiệp, KCN, xuất khẩu lao động, "
            "hợp đồng lao động, bảo hiểm xã hội, tăng ca, phụ cấp, ký túc xá, "
            "nhà máy, xí nghiệp, tuyển dụng, ứng viên, nhân viên tư vấn, "
            "lao động phổ thông, công nhân, giờ làm việc, ngày nghỉ.")

        tk.Label(p, text="Thông tin máy (cố định):", bg=self.BG, fg=self.ACCENT,
                 font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=16, pady=(14,4))
        for n in ["• Device: cpu  (Intel i7-1185G7 — không có GPU NVIDIA)",
                  "• Compute type: int8  (tối ưu cho CPU)",
                  "• CPU threads: 8  (khớp với i7-1185G7 8 CPUs)",
                  "• Model cache: C:\\Users\\<tên>\\.cache\\huggingface\\"]:
            tk.Label(p, text=n, bg=self.BG, fg=self.MUTED,
                     font=("Consolas", 9), anchor="w").pack(anchor="w", padx=16, pady=1)

    # ── Helpers ───────────────────────────────────────────────────────────────
    def _sec(self, p, t):
        tk.Label(p, text=t, bg=self.BG, fg=self.ACCENT,
                 font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(10,2))

    def _btn(self, p, t, cmd, bg, fg=None, font=None):
        return tk.Button(p, text=t, command=cmd, bg=bg, fg=fg or self.FG,
                         relief="flat", padx=10, pady=5,
                         font=font or ("Segoe UI", 10),
                         activebackground=bg, cursor="hand2")

    def _log(self, msg, tag="seg"):
        self.log.config(state="normal")
        self.log.insert("end", msg, tag)
        self.log.see("end"); self.log.config(state="disabled")

    def _logln(self, msg, tag="seg"): self._log(msg+"\n", tag)

    def _pplog(self, msg, tag="info"):
        self.pp_log.config(state="normal")
        self.pp_log.insert("end", msg+"\n", tag)
        self.pp_log.see("end"); self.pp_log.config(state="disabled")

    def _set_prog(self, msg):
        self.root.after(0, lambda: self.prog_lbl.config(text=msg))

    def _pick_files(self):
        files = filedialog.askopenfilenames(
            title="Chọn file audio",
            filetypes=[("Audio", "*.mp3 *.wav *.m4a *.ogg *.flac *.mp4 *.webm *.aac"), ("All","*.*")])
        for f in files:
            p = Path(f)
            if p not in self.selected_files and p.suffix.lower() in SUPPORTED:
                self.selected_files.append(p)
        self._refresh()

    def _pick_folder(self):
        d = filedialog.askdirectory(title="Chọn thư mục audio")
        if d:
            for f in Path(d).iterdir():
                if f.suffix.lower() in SUPPORTED and f not in self.selected_files:
                    self.selected_files.append(f)
        self._refresh()

    def _clear_files(self):
        self.selected_files.clear(); self._refresh()

    def _refresh(self):
        self.listbox.delete(0, "end")
        for p in self.selected_files:
            self.listbox.insert("end", f"  {p.name}  ({fmt_size(p)})")
        n = len(self.selected_files)
        self.count_lbl.config(text=f"{n} file được chọn" if n else "Chưa chọn file nào")

    def _choose_out(self):
        d = filedialog.askdirectory(title="Thư mục lưu kết quả")
        if d: self.output_var.set(d)

    def _open_out(self):
        p = Path(self.output_var.get()); p.mkdir(parents=True, exist_ok=True); os.startfile(str(p))

    def _pick_test_file(self):
        f = filedialog.askopenfilename(title="Chọn file audio để thử",
            filetypes=[("Audio","*.mp3 *.wav *.m4a *.ogg *.flac"),("All","*.*")])
        if f: self.test_file_var.set(f)

    def _get_pp_config(self):
        cfg = dict(DEFAULT_CONFIG)
        if HAS_PREPROCESS:
            cfg["noise_reduce"]          = self.nr_var.get()
            cfg["noise_reduce_strength"] = self.nr_strength.get()
            cfg["stationary_noise"]      = self.stationary_var.get()
            cfg["bandpass_filter"]       = self.bp_var.get()
            cfg["normalize_volume"]      = self.nv_var.get()
        return cfg

    def _run_test_preprocess(self):
        if not HAS_PREPROCESS: return
        src = self.test_file_var.get()
        if not src or src == "Chưa chọn file":
            messagebox.showwarning("Chưa chọn file", "Vui lòng chọn file audio!"); return
        src = Path(src)
        out = src.parent / f"{src.stem}_preprocessed.wav"
        def _w():
            cfg = self._get_pp_config()
            def _cb(msg, pct):
                self.root.after(0, lambda m=msg, pct=pct: self._pplog(f"[{pct:3d}%] {m}", "info"))
            try:
                self._pplog(f"\nBắt đầu xử lý: {src.name}", "info")
                r = preprocess_audio(src, out, cfg, _cb)
                self.root.after(0, lambda: self._pplog(f"[OK] Lưu tại: {r}", "ok"))
            except Exception as e:
                self.root.after(0, lambda: self._pplog(f"[LỖI] {e}", "warn"))
        threading.Thread(target=_w, daemon=True).start()

    def _start(self):
        if not self.selected_files:
            messagebox.showwarning("Chưa chọn file", "Vui lòng chọn ít nhất 1 file audio!"); return
        if self.is_running: return
        self.is_running = True
        self.run_btn.config(state="disabled"); self.stop_btn.config(state="normal")
        self.progress.start(12)
        threading.Thread(target=self._worker, daemon=True).start()

    def _stop(self):
        self.is_running = False; self._logln("\n[Dừng lại]", "warn"); self._finish()

    def _finish(self):
        self.is_running = False
        self.root.after(0, lambda: [self.progress.stop(),
                                    self.run_btn.config(state="normal"),
                                    self.stop_btn.config(state="disabled")])

    def _worker(self):
        try:
            model_size = self.model_var.get()
            if self.model is None or self.model_size_loaded != model_size:
                self._set_prog(f"Đang tải model '{model_size}'...")
                self._logln(f"\n{'='*50}", "muted")
                self._logln(f"  Tải model: {model_size}", "info")
                t0 = time.time()
                self.model = WhisperModel(model_size, device="cpu", compute_type="int8",
                                          cpu_threads=8,
                                          num_workers=2 if model_size != "large-v3" else 1)
                self.model_size_loaded = model_size
                self._logln(f"[OK] Model tải xong ({time.time()-t0:.1f}s)\n", "ok")

            output_dir = Path(self.output_var.get()); output_dir.mkdir(parents=True, exist_ok=True)
            total = len(self.selected_files)
            prompt = self.prompt_var.get("1.0", "end").strip() or None
            beam   = self.beam_var.get()
            lang   = self.lang_var.get() or None
            do_pp  = self.preproc_var.get() and HAS_PREPROCESS
            pp_cfg = self._get_pp_config() if do_pp else None

            for idx, audio_path in enumerate(self.selected_files, 1):
                if not self.is_running: break
                self._set_prog(f"[{idx}/{total}] {audio_path.name}")
                self._logln(f"\n{'─'*50}", "muted")
                self._logln(f"  [{idx}/{total}]  {audio_path.name}", "info")

                actual_path = audio_path
                if do_pp:
                    self._logln("  Tiền xử lý audio...", "info")
                    tmp = Path(tempfile.mktemp(suffix=".wav"))
                    try:
                        actual_path = preprocess_audio(audio_path, tmp, pp_cfg,
                                         lambda m, pct: self._set_prog(f"Tiền xử lý: {m}"))
                        self._logln("  [OK] Tiền xử lý xong", "ok")
                    except Exception as e:
                        self._logln(f"  [WARN] Tiền xử lý lỗi, dùng file gốc: {e}", "warn")
                        actual_path = audio_path

                t0 = time.time()
                segs_gen, info = self.model.transcribe(
                    str(actual_path), language=lang, beam_size=beam, best_of=beam,
                    temperature=0.0, vad_filter=self.vad_var.get(),
                    vad_parameters=dict(min_silence_duration_ms=500, speech_pad_ms=200),
                    word_timestamps=self.word_ts_var.get(),
                    condition_on_previous_text=True, initial_prompt=prompt)

                segments = []
                for seg in segs_gen:
                    if not self.is_running: break
                    text = seg.text.strip()
                    if not text: continue
                    segments.append({"id": len(segments)+1, "start": round(seg.start,3),
                                     "end": round(seg.end,3), "text": text})
                    self._log("  ", "muted")
                    self._log(f"[{fmt_time(seg.start)}→{fmt_time(seg.end)}]", "ts")
                    self._log(f"  {text}\n", "seg")

                if not segments:
                    self._logln("  [WARN] Không nhận dạng được nội dung!", "warn"); continue

                elapsed = time.time() - t0; stem = audio_path.stem

                with open(output_dir/f"{stem}_transcript.txt","w",encoding="utf-8") as f:
                    f.write(f"File    : {audio_path.name}\nNgôn ngữ: {info.language} ({info.language_probability:.0%})\n")
                    f.write(f"Thời lượng: {fmt_time(info.duration)}\nTiền xử lý: {'Có' if do_pp else 'Không'}\n")
                    f.write("="*60+"\n\n")
                    for s in segments: f.write(f"[{fmt_time(s['start'])} → {fmt_time(s['end'])}]\n{s['text']}\n\n")
                    f.write("="*60+"\nTOÀN VĂN:\n"+" ".join(s["text"] for s in segments))

                with open(output_dir/f"{stem}_transcript.srt","w",encoding="utf-8") as f:
                    for s in segments: f.write(f"{s['id']}\n{fmt_srt(s['start'])} --> {fmt_srt(s['end'])}\n{s['text']}\n\n")

                result = {"file": audio_path.name, "language": info.language,
                          "preprocessed": do_pp,
                          "language_prob": round(info.language_probability,4),
                          "duration_seconds": round(info.duration,2),
                          "process_time_sec": round(elapsed,2),
                          "total_segments": len(segments),
                          "total_words": sum(len(s["text"].split()) for s in segments),
                          "full_text": " ".join(s["text"] for s in segments),
                          "segments": segments}
                with open(output_dir/f"{stem}_transcript.json","w",encoding="utf-8") as f:
                    json.dump(result, f, ensure_ascii=False, indent=2)

                if do_pp and actual_path != audio_path:
                    try: actual_path.unlink()
                    except: pass

                self._logln(f"\n[OK] Hoàn thành {audio_path.name}", "ok")
                self._logln(f"     Ngôn ngữ  : {info.language} ({info.language_probability:.0%})", "info")
                self._logln(f"     Thời lượng: {fmt_time(info.duration)}", "info")
                self._logln(f"     Tốc độ    : {info.duration/elapsed:.1f}× realtime", "info")
                self._logln(f"     Tiền xử lý: {'Có' if do_pp else 'Không'}", "info")
                self._logln(f"     Đã lưu → {output_dir}/", "info")

            self._logln(f"\n{'='*50}\n  Tất cả hoàn thành!\n  Kết quả: {Path(self.output_var.get())}\n{'='*50}\n", "ok")
            self._set_prog("Hoàn thành!")
        except Exception as e:
            self._logln(f"\n[LỖI] {e}", "err"); self._set_prog("Có lỗi!")
        finally:
            self.root.after(0, self._finish)


if __name__ == "__main__":
    root = tk.Tk()
    App(root)
    root.mainloop()