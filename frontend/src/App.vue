<script setup>
import { computed, ref } from "vue";
import MatchingWorkspace from "./MatchingWorkspace.vue";

const selectedFile = ref(null);
const isDragging = ref(false);
const isLoading = ref(false);
const isCheckingColab = ref(false);
const error = ref("");
const errorDetail = ref("");
const colabStatus = ref("");
const result = ref(null);
const activeView = ref("transcribe");

const savedColabUrl = localStorage.getItem("colab_api_url") || "";
const form = ref({
  engine: "local",
  colabUrl: savedColabUrl,
  model: "tiny",
  language: "vi",
  beamSize: 1,
  preprocess: false
});

const fileSize = computed(() => {
  if (!selectedFile.value) return "";
  const mb = selectedFile.value.size / 1024 / 1024;
  return mb >= 1 ? `${mb.toFixed(1)} MB` : `${(selectedFile.value.size / 1024).toFixed(1)} KB`;
});

const duration = computed(() => {
  const seconds = result.value?.duration_seconds;
  if (!seconds && seconds !== 0) return "--:--";
  const m = Math.floor(seconds / 60).toString().padStart(2, "0");
  const s = Math.floor(seconds % 60).toString().padStart(2, "0");
  return `${m}:${s}`;
});

function colabEndpoint(path) {
  const raw = form.value.colabUrl.trim().replace(/\/$/, "");
  if (!raw) return "";
  if (raw.endsWith("/transcribe")) {
    return raw.slice(0, -"/transcribe".length) + path;
  }
  return raw + path;
}

function pickFile(event) {
  const file = event.target.files?.[0];
  if (file) setFile(file);
}

function dropFile(event) {
  isDragging.value = false;
  const file = event.dataTransfer.files?.[0];
  if (file) setFile(file);
}

function setFile(file) {
  selectedFile.value = file;
  result.value = null;
  error.value = "";
  errorDetail.value = "";
}

async function checkColab() {
  if (!form.value.colabUrl.trim() || isCheckingColab.value) return;

  isCheckingColab.value = true;
  error.value = "";
  errorDetail.value = "";
  colabStatus.value = "";

  try {
    const response = await fetch(colabEndpoint("/health"));
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.error || "Không kiểm tra được Colab API.");
    }
    colabStatus.value = "Colab API OK";
  } catch (err) {
    error.value = err.message;
  } finally {
    isCheckingColab.value = false;
  }
}

async function submit() {
  if (!selectedFile.value || isLoading.value) return;
  if (form.value.engine === "colab" && !form.value.colabUrl.trim()) {
    error.value = "Vui lòng dán Colab API URL trước khi xử lý bằng Colab GPU.";
    return;
  }

  isLoading.value = true;
  error.value = "";
  errorDetail.value = "";
  colabStatus.value = "";
  result.value = null;

  const body = new FormData();
  body.append("audio", selectedFile.value);
  body.append("language", form.value.language);
  body.append("beam_size", String(form.value.beamSize));
  if (form.value.colabUrl.trim()) {
    localStorage.setItem("colab_api_url", form.value.colabUrl.trim());
  }
  if (form.value.engine === "local") {
    body.append("engine", form.value.engine);
    body.append("model", form.value.model);
    body.append("preprocess", String(form.value.preprocess));
  }

  try {
    const response = await fetch(
      form.value.engine === "colab" ? colabEndpoint("/transcribe") : "/api/transcribe/",
      {
      method: "POST",
      body
      }
    );
    const payload = await response.json();

    if (!response.ok) {
      errorDetail.value = payload.detail || "";
      throw new Error(payload.error || "Không thể chuyển audio thành văn bản.");
    }

    result.value = payload;
  } catch (err) {
    error.value = err.message;
  } finally {
    isLoading.value = false;
  }
}
</script>

<template>
  <main class="shell">
    <aside class="sidebar">
      <div>
        <p class="eyebrow">AI Recruitment Lab</p>
        <h1>{{ activeView === "transcribe" ? "Chuyển hội thoại tư vấn tuyển dụng thành văn bản" : "Ghép ứng viên với recruiter" }}</h1>
      </div>

      <nav class="workspace-tabs" aria-label="Không gian làm việc">
        <button :class="{ active: activeView === 'transcribe' }" @click="activeView = 'transcribe'">Hội thoại</button>
        <button :class="{ active: activeView === 'matching' }" @click="activeView = 'matching'">Ghép ứng viên</button>
      </nav>

      <section v-if="activeView === 'transcribe'" class="control-group">
        <label>
          Chế độ xử lý
          <select v-model="form.engine">
            <option value="local">Local CPU</option>
            <option value="colab">Colab GPU</option>
          </select>
          <small class="field-help">
            Local chạy trên máy này. Colab gửi audio lên notebook GPU của bạn rồi nhận kết quả trả về.
          </small>
        </label>

        <label v-if="form.engine === 'colab'">
          Colab API URL
          <div class="url-row">
            <input
              v-model="form.colabUrl"
              class="text-input"
              placeholder="https://...trycloudflare.com"
              type="url"
            />
            <button class="secondary-button" :disabled="isCheckingColab || !form.colabUrl.trim()" @click="checkColab">
              {{ isCheckingColab ? "..." : "Kiểm tra" }}
            </button>
          </div>
          <small class="field-help">
            Dán URL FastAPI trên Colab. Trình duyệt sẽ gọi trực tiếp /health và /transcribe.
          </small>
          <small v-if="colabStatus" class="ok-help">{{ colabStatus }}</small>
        </label>

        <label>
          Model
          <select v-model="form.model" :disabled="form.engine === 'colab'">
            <option value="tiny">tiny - rất nhanh</option>
            <option value="base">base - nhanh</option>
            <option value="small">small - cân bằng nhẹ</option>
            <option value="medium">medium - khuyến nghị</option>
            <option value="large-v3">large-v3 - chính xác hơn, cần tải model lớn</option>
          </select>
          <small class="field-help">
            large-v3 chậm hơn và lần đầu cần tải model từ Hugging Face.
          </small>
        </label>

        <label>
          Ngôn ngữ
          <select v-model="form.language">
            <option value="vi">Tiếng Việt</option>
            <option value="">Tự phát hiện</option>
            <option value="en">English</option>
          </select>
        </label>

        <label>
          Độ dò kết quả
          <input v-model.number="form.beamSize" type="range" min="1" max="5" />
          <span class="range-value">{{ form.beamSize }}</span>
          <small class="field-help">
            1 = khuyến nghị cho cuộc gọi. 3 = cân bằng. 5 = chậm hơn và có thể bị lọc mất đoạn nếu audio yếu.
          </small>
        </label>

        <label class="check-row">
          <input v-model="form.preprocess" :disabled="form.engine === 'colab'" type="checkbox" />
          <span>Tiền xử lý audio trước khi nhận dạng</span>
        </label>
      </section>
    </aside>

    <section v-if="activeView === 'transcribe'" class="workspace">
      <div class="topbar">
        <div>
          <h2>Upload audio</h2>
          <p>Hỗ trợ mp3, wav, m4a, ogg, flac, mp4, webm, aac.</p>
        </div>
        <button :disabled="!selectedFile || isLoading" @click="submit">
          {{ isLoading ? "Đang xử lý..." : "Bắt đầu chuyển đổi" }}
        </button>
      </div>

      <label
        class="dropzone"
        :class="{ active: isDragging }"
        @dragover.prevent="isDragging = true"
        @dragleave.prevent="isDragging = false"
        @drop.prevent="dropFile"
      >
        <input type="file" accept="audio/*,video/mp4,video/webm" @change="pickFile" />
        <span class="upload-icon">↑</span>
        <strong>{{ selectedFile ? selectedFile.name : "Chọn hoặc kéo thả file audio" }}</strong>
        <small>{{ selectedFile ? fileSize : "File sẽ được gửi tới Django API để transcribe bằng faster-whisper." }}</small>
      </label>

      <p v-if="error" class="alert">
        {{ error }}
        <small v-if="errorDetail">{{ errorDetail }}</small>
      </p>

      <section v-if="result" class="result-layout">
        <div class="metrics">
          <div>
            <span>Thời lượng</span>
            <strong>{{ duration }}</strong>
          </div>
          <div>
            <span>Ngôn ngữ</span>
            <strong>{{ result.language }} · {{ Math.round(result.language_prob * 100) }}%</strong>
          </div>
          <div>
            <span>Số đoạn</span>
            <strong>{{ result.total_segments }}</strong>
          </div>
          <div>
            <span>Số từ</span>
            <strong>{{ result.total_words }}</strong>
          </div>
        </div>

        <article class="transcript">
          <div class="section-title">
            <h2>Văn bản hội thoại</h2>
            <span>{{ result.process_time_sec }}s xử lý</span>
          </div>
          <p>{{ result.dialogue_text || result.full_text }}</p>
        </article>

        <article class="segments">
          <div class="section-title">
            <h2>Các đoạn nhận dạng</h2>
            <span>{{ result.original_name }}</span>
          </div>
          <ul>
            <li v-for="segment in result.segments" :key="segment.id">
              <time>{{ segment.start.toFixed(1) }}s - {{ segment.end.toFixed(1) }}s</time>
              <p>{{ segment.text }}</p>
            </li>
          </ul>
        </article>
      </section>
    </section>
    <MatchingWorkspace v-else />
  </main>
</template>
