<script setup>
import { computed, onMounted, ref } from "vue";

const candidates = ref([]);
const selectedCandidateId = ref("");
const health = ref("checking");
const isLoading = ref(false);
const isRebuilding = ref(false);
const error = ref("");
const result = ref(null);

const selectedCandidate = computed(() =>
  candidates.value.find((candidate) => candidate.id === selectedCandidateId.value) || null
);

function currency(value) {
  return value ? `${new Intl.NumberFormat("vi-VN").format(value)} VND` : "Chưa có";
}

function percent(value) {
  return `${Math.round(value * 100)}%`;
}

async function request(path, options = {}) {
  const response = await fetch(`/matching-api${path}`, options);
  const payload = await response.json();
  if (!response.ok) {
    const detail = payload.detail || {};
    throw new Error(detail.message || payload.message || "Không thể kết nối Matching Service.");
  }
  return payload;
}

async function loadWorkspace() {
  try {
    const [candidatePayload, healthPayload] = await Promise.all([
      request("/api/v1/candidates"),
      request("/api/v1/health"),
    ]);
    candidates.value = candidatePayload.candidates;
    selectedCandidateId.value ||= candidates.value[0]?.id || "";
    health.value = healthPayload.status === "ok" ? "ready" : "error";
  } catch (err) {
    health.value = "error";
    error.value = err.message;
  }
}

async function runMatching() {
  if (!selectedCandidateId.value || isLoading.value) return;
  isLoading.value = true;
  error.value = "";
  result.value = null;
  try {
    result.value = await request(`/api/v1/matching/candidates/${selectedCandidateId.value}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ top_k: 3 }),
    });
  } catch (err) {
    error.value = err.message;
  } finally {
    isLoading.value = false;
  }
}

async function rebuildRecruiters() {
  if (isRebuilding.value) return;
  isRebuilding.value = true;
  error.value = "";
  try {
    await request("/api/v1/embeddings/recruiters/rebuild", { method: "POST" });
    await request("/api/v1/embeddings/campaigns/rebuild", { method: "POST" });
  } catch (err) {
    error.value = err.message;
  } finally {
    isRebuilding.value = false;
  }
}

onMounted(loadWorkspace);
</script>

<template>
  <section class="matching-workspace">
    <header class="matching-header">
      <div>
        <p class="eyebrow matching-eyebrow">Candidate Matching</p>
        <h2>Ghép ứng viên với recruiter</h2>
        <p>Đề xuất được xếp hạng theo chuyên môn, chiến dịch, hiệu suất và sức chứa hiện tại.</p>
      </div>
      <div class="service-state" :class="health">
        <span class="status-dot"></span>
        {{ health === "ready" ? "Matching service sẵn sàng" : health === "checking" ? "Đang kiểm tra dịch vụ" : "Không kết nối được dịch vụ" }}
      </div>
    </header>

    <div class="matching-layout">
      <section class="candidate-tool" aria-label="Chọn ứng viên">
        <label for="candidate-select">Ứng viên</label>
        <select id="candidate-select" v-model="selectedCandidateId" :disabled="!candidates.length || isLoading">
          <option v-for="candidate in candidates" :key="candidate.id" :value="candidate.id">
            {{ candidate.desired_job || "Chưa có vị trí" }} · {{ candidate.province || "Chưa có địa điểm" }}
          </option>
        </select>

        <dl v-if="selectedCandidate" class="candidate-details">
          <div><dt>Vị trí mong muốn</dt><dd>{{ selectedCandidate.desired_job || "Chưa có" }}</dd></div>
          <div><dt>Khu vực</dt><dd>{{ selectedCandidate.province || "Chưa có" }} · {{ selectedCandidate.region || "--" }}</dd></div>
          <div><dt>Kinh nghiệm</dt><dd>{{ selectedCandidate.experience || "Chưa có" }}</dd></div>
          <div><dt>Lương kỳ vọng</dt><dd>{{ currency(selectedCandidate.expected_salary) }}</dd></div>
        </dl>

        <button class="match-button" :disabled="!selectedCandidateId || isLoading || health !== 'ready'" @click="runMatching">
          {{ isLoading ? "Đang tìm recruiter..." : "Tìm recruiter phù hợp" }}
        </button>
        <button class="rebuild-button" :disabled="isRebuilding" @click="rebuildRecruiters">
          {{ isRebuilding ? "Đang cập nhật vector..." : "Cập nhật dữ liệu matching" }}
        </button>
      </section>

      <section class="matching-results" aria-live="polite">
        <div class="results-heading">
          <div>
            <p class="eyebrow">Kết quả đề xuất</p>
            <h3>{{ result ? `${result.top_k} recruiter phù hợp nhất` : "Sẵn sàng phân tích" }}</h3>
          </div>
          <div v-if="result" class="result-counts">
            <span>{{ result.eligible_recruiters }} hợp lệ</span>
            <span>{{ result.retrieved_recruiters }} semantic hits</span>
          </div>
        </div>

        <p v-if="error" class="matching-alert">{{ error }}</p>

        <div v-if="result?.recommendations?.length" class="recommendation-list">
          <article v-for="item in result.recommendations" :key="item.recruiter_id" class="recommendation">
            <div class="rank-badge">{{ item.rank }}</div>
            <div class="recommendation-main">
              <div class="recommendation-title">
                <div>
                  <h4>{{ item.specialty || "Recruiter chưa có chuyên môn" }}</h4>
                  <p>{{ item.active_campaigns.join(" · ") || "Chưa có chiến dịch active" }}</p>
                </div>
                <strong>{{ percent(item.final_score) }}</strong>
              </div>
              <div class="score-grid">
                <span>Ngữ nghĩa <b>{{ percent(item.semantic_score) }}</b></span>
                <span>Chiến dịch <b>{{ percent(item.campaign_fit_score) }}</b></span>
                <span>Hiệu suất <b>{{ percent(item.performance_score) }}</b></span>
                <span>Workload <b>{{ percent(item.workload_score) }}</b></span>
              </div>
              <div class="workload-line">
                <span>{{ item.current_workload }} / {{ item.max_workload }} hồ sơ đang xử lý</span>
                <div class="workload-bar"><i :style="{ width: `${Math.min(100, item.current_workload / item.max_workload * 100)}%` }"></i></div>
              </div>
              <ul class="reason-list">
                <li v-for="reason in item.reasons" :key="reason">{{ reason }}</li>
              </ul>
            </div>
          </article>
        </div>

        <div v-else class="empty-results">
          <strong>{{ result?.message || "Chọn ứng viên để bắt đầu" }}</strong>
          <span>Kết quả sẽ xuất hiện ở đây khi dữ liệu vector đã sẵn sàng.</span>
        </div>
      </section>
    </div>
  </section>
</template>
