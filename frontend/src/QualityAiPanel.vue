<script setup>
import { computed, onActivated, onDeactivated, onMounted, onUnmounted, ref, watch } from "vue";

const props = defineProps({api: Function, revision: Object, rubric: Object, dirty: Boolean});
const emit = defineEmits(["assessment-ready", "sealed"]);
const model = ref(null), jobs = ref([]), job = ref(null), error = ref(""), busy = ref(false);
const requestKey = ref(null);
let active = false, generation = 0, timer, controller;
const notified = new Set();
const matchingModel = computed(() => model.value?.available && model.value.rubric_version === props.rubric?.version);
const inProgress = computed(() => ["queued", "running"].includes(job.value?.status));
const canStart = computed(() => matchingModel.value && props.rubric?.status === "approved" && props.revision?.roles_confirmed && props.revision?.transcript_reviewed && !props.dirty && !busy.value && !inProgress.value);
const labels = {queued: "Chờ worker", running: "Đang chấm AI", succeeded: "Đã có bản AI · Chờ duyệt", failed: "Không hoàn tất"};

function stop() {
  generation++; clearTimeout(timer); controller?.abort(); controller = null;
}
function notify(value) {
  if (value.status === "succeeded" && !notified.has(value.id)) { notified.add(value.id); emit("assessment-ready"); }
}
function schedule(version) {
  clearTimeout(timer);
  if (active && version === generation && inProgress.value) timer = setTimeout(() => poll(version), 1500);
}
async function poll(version) {
  if (!active || version !== generation || !job.value) return;
  try {
    const value = await props.api(`assessment-jobs/${job.value.id}/`, undefined, "GET", {signal: controller.signal});
    if (!active || version !== generation) return;
    job.value = value;
    jobs.value = jobs.value.map(j => j.id === value.id ? value : j);
    notify(value); schedule(version);
  } catch (e) {
    if (version === generation && e.name !== "AbortError") error.value = `Theo dõi bị gián đoạn: ${e.message}`;
  }
}
async function refresh() {
  if (!active) return;
  stop(); controller = new AbortController();
  const version = generation;
  busy.value = true; error.value = "";
  try {
    const options = {signal: controller.signal};
    const state = await props.api("model-status/", undefined, "GET", options);
    const rows = props.revision ? (await props.api(`revisions/${props.revision.id}/assessment-jobs/`, undefined, "GET", options)).items : [];
    if (!active || version !== generation) return;
    model.value = state;
    jobs.value = rows.filter(j => j.rubric_id === props.rubric?.id);
    job.value = jobs.value.find(j => ["queued", "running"].includes(j.status)) || jobs.value[0] || null;
    if (job.value) notify(job.value);
    schedule(version);
  } catch (e) {
    if (version === generation && e.name !== "AbortError") { model.value = null; error.value = e.message; }
  } finally { if (version === generation) busy.value = false; }
}
async function start() {
  if (!canStart.value) return;
  busy.value = true; error.value = "";
  const version = generation;
  try {
    if (props.revision.status !== "sealed") {
      const sealed = await props.api(`revisions/${props.revision.id}/seal/`, {}, "POST", {signal: controller.signal});
      if (version !== generation) return;
      emit("sealed", sealed);
    }
    requestKey.value ||= crypto.randomUUID();
    const value = await props.api(`revisions/${props.revision.id}/assessment-jobs/`, {rubric_id: props.rubric.id, request_key: requestKey.value}, "POST", {signal: controller.signal});
    if (!active || version !== generation) return;
    job.value = value; jobs.value = [value, ...jobs.value.filter(j => j.id !== value.id)];
    notify(value); schedule(version);
  } catch (e) {
    if (version === generation && e.name !== "AbortError") error.value = e.message;
  } finally { if (version === generation) busy.value = false; }
}
function activate() { if (!active) { active = true; refresh(); } }
function deactivate() { active = false; stop(); busy.value = false; }
watch([() => props.revision?.id, () => props.rubric?.id], () => { requestKey.value = null; job.value = null; jobs.value = []; refresh(); });
watch(() => job.value?.status, value => { if (["succeeded", "failed"].includes(value)) requestKey.value = null; });
onMounted(activate); onActivated(activate); onDeactivated(deactivate); onUnmounted(deactivate);
</script>

<template>
  <section class="quality-ai" aria-label="Chấm AI">
    <header><h3>Chấm AI</h3><button type="button" :disabled="busy" @click="refresh">Cập nhật trạng thái AI</button></header>
    <p v-if="model">{{ model.message }}</p>
    <p v-if="model?.available && !matchingModel" class="warning">Checkpoint không khớp bộ tiêu chí đang chọn.</p>
    <p v-if="model?.available && matchingModel && rubric?.status !== 'approved'" class="warning">Bộ tiêu chí chưa được duyệt để chấm AI.</p>
    <p v-if="error" class="alert" role="alert">{{ error }}</p>
    <button type="button" :disabled="!canStart" @click="start">{{ revision?.status === 'sealed' ? 'Gửi chấm AI' : 'Khóa bản và chấm AI' }}</button>
    <div v-if="job" class="job-state" role="status">
      <strong>{{ labels[job.status] }}</strong>
      <p>{{ job.model_version }} · {{ job.completed_windows }}/{{ job.total_windows || '…' }} cửa sổ</p>
      <progress v-if="job.status === 'running'" :value="job.total_windows ? job.completed_windows : undefined" :max="job.total_windows || 1" aria-label="Tiến độ chấm AI" />
      <p v-if="job.error" class="warning">{{ job.error.message }} · {{ job.error.code }}</p>
    </div>
    <details v-if="jobs.length > 1"><summary>Lịch sử tác vụ · {{ jobs.length }}</summary><p v-for="item in jobs" :key="item.id">{{ new Date(item.created_at).toLocaleString('vi-VN') }} · {{ labels[item.status] }} · {{ item.model_version }}</p></details>
  </section>
</template>

<style scoped>
.quality-ai{padding:16px 0;border-top:1px solid #ccd6db;border-bottom:1px solid #ccd6db;margin:16px 0;overflow-wrap:anywhere}header{display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap}h3{font-size:18px;margin:0}p{font-size:14px;line-height:1.5;color:#435b64}button{font-size:14px;padding:10px 14px;max-width:100%;white-space:normal}.job-state{margin-top:16px}.warning{color:#804700}progress{max-width:100%;width:360px;height:10px}summary{cursor:pointer;font-size:14px;padding:10px 0}
</style>
