<script setup>
import { computed, onMounted, onUnmounted, ref } from "vue";

const session = ref(null), username = ref(""), password = ref("");
const busy = ref(false), error = ref(""), notice = ref("");
const config = ref(null), conversations = ref([]), conversationId = ref("");
const revisions = ref([]), revisionId = ref(""), decisions = ref([]), selected = ref(null), current = ref(null);
const label = ref("unknown"), rationale = ref(""), evidence = ref([]), dirty = ref(false), editing = ref(false), confirmed = ref(false);
const taxonomy = ref(null), training = ref(null), taxonomyNote = ref(""), taxonomyConfirmed = ref(false), reviewNote = ref("");
const revision = computed(() => revisions.value.find(r => r.id === revisionId.value));
const labels = computed(() => config.value?.labels || []);
const turns = computed(() => selected.value?.utterances || revision.value?.utterances || []);
const labelInfo = code => labels.value.find(item => item.code === code);
const statusName = value => value === "confirmed" ? "Đã xác nhận" : "Bản nháp";
const sourceName = value => ({ manual: "Thủ công", model: "ViDeBERTa", rules: "Quy tắc" })[value] || value;
const time = value => new Date(value).toLocaleString("vi-VN", { timeZone: "Asia/Ho_Chi_Minh" });
const canConfirm = computed(() => selected.value && selected.value.source !== "model" && !editing.value && !selected.value.stale && selected.value.status === "draft" && (selected.value.author_id === session.value?.user_id || session.value?.can_review));
const canReviewLabel = computed(() => session.value?.can_review && selected.value?.source === "manual" && selected.value.status === "confirmed" && !selected.value.stale && !selected.value.training_review && selected.value.author_id !== session.value.user_id && taxonomy.value?.approval && !editing.value);

async function api(path, data, method = "POST", quality = false) {
  let response;
  try {
    response = await fetch(`/api/${quality ? "quality" : "candidate-status"}/${path}`, data === undefined ? {} : {
      method, headers: { "Content-Type": "application/json", "X-CSRFToken": session.value?.csrf_token || "" }, body: JSON.stringify(data)
    });
  } catch { throw new Error("Không kết nối được Django. Kiểm tra backend và proxy /api."); }
  let result;
  try { result = await response.json(); } catch { throw new Error("API chưa sẵn sàng hoặc trả dữ liệu không hợp lệ."); }
  if (!response.ok) {
    if (response.status === 401 && session.value?.authenticated) { session.value = { authenticated: false }; clear(); authChanged(); }
    throw new Error(result.error?.message || "Không thực hiện được yêu cầu.");
  }
  return result;
}
async function action(fn) {
  if (busy.value) return;
  busy.value = true; error.value = ""; notice.value = "";
  try { await fn(); } catch (e) { error.value = e.message; } finally { busy.value = false; }
}
function authChanged() { window.dispatchEvent(new Event("recruitment-session-changed")); }
function canLeave() { return !dirty.value || window.confirm("Bỏ các thay đổi chưa lưu?"); }
function beforeClose(event) { if (dirty.value) { event.preventDefault(); event.returnValue = ""; } }
function clear() {
  conversations.value = []; conversationId.value = ""; revisions.value = []; revisionId.value = "";
  decisions.value = []; current.value = null; select(null);
  training.value = null; taxonomy.value = null; taxonomyNote.value = ""; taxonomyConfirmed.value = false;
}
async function loadGovernance() {
  taxonomy.value = await api("taxonomy/");
  if (session.value?.can_review) training.value = await api("training-status/");
}
async function load() {
  config.value = await api("config/");
  await loadGovernance();
  const items = []; let offset = 0;
  while (true) {
    const page = await api(`conversations/?offset=${offset}&limit=100`, undefined, "GET", true);
    items.push(...page.items); offset += page.items.length;
    if (!page.items.length || offset >= page.count) break;
  }
  conversations.value = items;
}
async function login() {
  try { session.value = await api("session/", { username: username.value, password: password.value }, "POST", true); }
  finally { password.value = ""; }
  authChanged(); await load();
}
async function logout() {
  if (!canLeave()) return;
  session.value = await api("session/", {}, "DELETE", true); clear(); authChanged();
}
function select(row) {
  selected.value = row; label.value = row?.label || "unknown"; rationale.value = row?.rationale || "";
  evidence.value = [...(row?.evidence_ids || [])]; editing.value = false; dirty.value = false; confirmed.value = false;
  reviewNote.value = "";
}
async function openConversation(id) {
  if (!canLeave()) return;
  // Clear the old context before fetching so a failed request cannot retain another conversation's draft.
  conversationId.value = id; revisions.value = []; revisionId.value = ""; decisions.value = []; current.value = null; select(null);
  if (!id) return;
  revisions.value = (await api(`conversations/${id}/`, undefined, "GET", true)).revisions;
  await openRevision(revisions.value[0]?.id || "");
}
async function openRevision(id) {
  revisionId.value = id; decisions.value = []; current.value = null; select(null);
  if (id) await refresh();
}
async function chooseRevision(id) { if (canLeave()) await openRevision(id); }
async function refresh(selectedId) {
  const payload = await api(`revisions/${revisionId.value}/decisions/`);
  decisions.value = payload.items; current.value = payload.current_confirmed;
  select(payload.items.find(row => row.id === selectedId) || payload.items[0] || null);
}
async function generate(source = "rules") {
  if (!canLeave()) return;
  const row = await api(`revisions/${revisionId.value}/decisions/`, { source });
  await refresh(row.id); notice.value = source === "model" ? "Đã lưu dự đoán AI chưa kiểm chứng; cần bản thủ công có dẫn chứng." : "Đã lưu gợi ý theo quy tắc; chưa xác nhận trạng thái.";
}
async function approveTaxonomy() {
  taxonomy.value = await api("taxonomy/approve/", { definition_hash: taxonomy.value.definition_hash, confirmed_definitions: taxonomyConfirmed.value, note: taxonomyNote.value });
  config.value = await api("config/"); await loadGovernance(); notice.value = "Đã lưu phê duyệt bộ nhãn. Chưa có nhãn hoặc model nào được duyệt tự động.";
}
async function reviewLabel(verdict) {
  const id = selected.value.id;
  await api(`decisions/${id}/review/`, { expected_version: selected.value.version, verdict, note: reviewNote.value });
  await refresh(id); await loadGovernance(); notice.value = verdict === "approved" ? "Đã duyệt nhãn để xét điều kiện xuất train." : "Đã từ chối nhãn; giữ audit, cần bản sửa mới để duyệt lại.";
}
function startManual() {
  if (selected.value?.stale) { error.value = "Chọn phiên bản transcript hiện hành trước khi tạo bản sửa."; return; }
  editing.value = true; dirty.value = false; confirmed.value = false;
}
async function saveManual() {
  const row = await api(`revisions/${revisionId.value}/decisions/`, {
    source: "manual", label: label.value, evidence_ids: evidence.value, rationale: rationale.value,
    supersedes_id: selected.value?.id || null
  });
  dirty.value = false; await refresh(row.id); notice.value = "Đã lưu bản thủ công riêng, giữ nguyên bản trước.";
}
async function confirm() {
  const row = await api(`decisions/${selected.value.id}/confirm/`, { expected_version: selected.value.version, confirmed_content: confirmed.value });
  await refresh(row.id); notice.value = "Đã xác nhận trạng thái. Không có lịch hoặc quyết định loại ứng viên nào được tạo tự động.";
}
onMounted(() => {
  window.addEventListener("beforeunload", beforeClose);
  action(async () => { session.value = await api("session/", undefined, "GET", true); if (session.value.authenticated) await load(); });
});
onUnmounted(() => window.removeEventListener("beforeunload", beforeClose));
</script>

<template>
  <section class="workspace candidate-status" aria-label="Trạng thái ứng viên">
    <header class="status-header"><h2>Trạng thái ứng viên</h2><span v-if="session?.authenticated">{{ session.username }}</span><button v-if="session?.authenticated" :disabled="busy" @click="action(logout)">Đăng xuất</button></header>
    <p v-if="error" class="alert" role="alert">{{ error }}</p>
    <p v-if="notice" class="notice" role="status">{{ notice }}</p>
    <form v-if="session && !session.authenticated" class="status-login" @submit.prevent="action(login)">
      <h3>Đăng nhập phân loại trạng thái</h3>
      <label>Tài khoản<input v-model="username" autocomplete="username" required /></label>
      <label>Mật khẩu<input v-model="password" type="password" autocomplete="current-password" required /></label>
      <button type="submit" :disabled="busy">Đăng nhập</button>
    </form>
    <template v-if="session?.authenticated">
      <p class="provider">{{ config?.model?.message }} · {{ taxonomy?.approval ? 'Bộ nhãn đã được duyệt' : 'Bộ nhãn chờ duyệt' }}</p>
      <details class="governance"><summary>Bộ nhãn và dữ liệu huấn luyện</summary>
        <dl><template v-for="item in labels" :key="item.code"><dt>{{ item.title }}</dt><dd>{{ item.description }}</dd></template></dl>
        <p v-if="taxonomy?.approval">{{ taxonomy.approval.reviewer }} đã duyệt · {{ time(taxonomy.approval.created_at) }}</p>
        <fieldset v-if="session.can_review && !taxonomy?.approval" :disabled="busy" class="decision-form"><label>Ghi chú duyệt bộ nhãn<textarea v-model="taxonomyNote" rows="2" maxlength="5000" /></label><label class="check"><input v-model="taxonomyConfirmed" type="checkbox" />Đã kiểm tra định nghĩa và ranh giới các trạng thái</label><button :disabled="!taxonomyConfirmed || !taxonomyNote.trim()" @click="action(approveTaxonomy)">Duyệt bộ nhãn</button></fieldset>
        <section v-if="training" class="training-report"><h3>Dữ liệu huấn luyện</h3><p>{{ training.eligible }} nhãn đủ điều kiện · {{ training.confirmed }} bản xác nhận · {{ training.unreviewed_transcripts }} transcript chưa kiểm tra</p><p class="muted">{{ training.note }}</p><ul><li v-for="(count, code) in training.label_counts" :key="code">{{ labelInfo(code)?.title }}: {{ count }}</li></ul><button :disabled="busy" class="secondary-button" @click="action(loadGovernance)">Làm mới báo cáo</button></section>
      </details>
      <p v-if="!busy && !conversations.length" class="muted">Chưa có hội thoại trong phạm vi được cấp quyền.</p>
      <fieldset :disabled="busy" class="context-controls">
        <label>Hội thoại<select aria-label="Hội thoại trạng thái" :value="conversationId" @change="action(() => openConversation($event.target.value))"><option disabled value="">Chọn hội thoại</option><option v-for="c in conversations" :key="c.id" :value="c.id">{{ c.title }}</option></select></label>
        <label v-if="revisions.length">Phiên bản transcript<select aria-label="Phiên bản trạng thái" :value="revisionId" @change="action(() => chooseRevision($event.target.value))"><option v-for="r in revisions" :key="r.id" :value="r.id">Bản {{ r.revision_number }} · {{ r.transcript_reviewed && r.roles_confirmed ? 'Đã đối chiếu' : 'Chưa đối chiếu' }}</option></select></label>
      </fieldset>
      <template v-if="revision">
        <audio v-if="revision.audio_url" :src="revision.audio_url" aria-label="Audio hội thoại" controls preload="metadata" />
        <p v-if="!revision.transcript_reviewed || !revision.roles_confirmed" class="warning">Transcript hoặc vai người nói chưa được xác nhận. Chưa thể xác nhận trạng thái.</p>
        <div class="current-state"><span>Trạng thái đã xác nhận hiện hành</span><strong>{{ current ? labelInfo(current.label)?.title : 'Chưa có' }}</strong><small v-if="current">{{ current.confirmed_by }} · {{ time(current.confirmed_at) }}</small></div>
        <div class="status-actions"><button :disabled="busy" @click="action(() => generate())">Phân loại theo quy tắc</button><button :disabled="busy || !config?.model_available" :title="config?.model?.message" @click="action(() => generate('model'))">Phân loại ViDeBERTa</button><button :disabled="busy || editing || selected?.stale" class="secondary-button" @click="startManual">{{ selected ? 'Tạo bản sửa thủ công' : 'Gán trạng thái thủ công' }}</button></div>
        <label v-if="decisions.length">Lịch sử phân loại<select aria-label="Lịch sử phân loại" :value="selected?.id" :disabled="busy" @change="canLeave() && select(decisions.find(d => d.id === $event.target.value))"><option v-for="d in decisions" :key="d.id" :value="d.id">{{ labelInfo(d.label)?.title }} · {{ sourceName(d.source) }} · {{ statusName(d.status) }} · {{ time(d.created_at) }}</option></select></label>
        <div class="status-layout">
          <section class="decision-area">
            <template v-if="selected || editing">
              <h3>{{ editing ? 'Bản sửa mới' : `${labelInfo(selected.label)?.title} · ${statusName(selected.status)}` }}</h3>
              <p v-if="selected?.stale" class="warning">Nguồn đã thay đổi. Bản này chỉ để xem lịch sử.</p>
              <fieldset :disabled="busy || !editing" class="decision-form" @input="dirty = true" @change="dirty = true">
                <label>Trạng thái<select v-model="label" aria-label="Chọn trạng thái"><option v-for="item in labels" :key="item.code" :value="item.code">{{ item.title }}</option></select></label>
                <p class="muted">{{ labelInfo(label)?.description }}</p>
                <label>Nhận định / lý do<textarea v-model="rationale" aria-label="Lý do trạng thái" rows="4" maxlength="5000" /></label>
              </fieldset>
              <div v-if="editing" class="status-actions"><button :disabled="busy" @click="action(saveManual)">Lưu bản thủ công</button><button :disabled="busy" class="secondary-button" @click="canLeave() && select(selected)">Bỏ sửa</button></div>
              <section v-if="!editing" class="next-step"><h4>Bước xử lý đề xuất</h4><p>{{ selected.suggested_next_step }}</p><p v-if="selected.confirmed_by" class="muted">{{ selected.confirmed_by }} xác nhận · {{ time(selected.confirmed_at) }}</p></section>
              <div v-if="canConfirm" class="confirm-area"><label class="check"><input v-model="confirmed" type="checkbox" :disabled="busy" />Đã đối chiếu trạng thái và dẫn chứng với hội thoại</label><button :disabled="busy || !confirmed || !revision.transcript_reviewed || !revision.roles_confirmed" @click="action(confirm)">Xác nhận trạng thái</button></div>
              <p class="muted">Dẫn chứng đã chọn: {{ evidence.length }} lượt</p>
              <p v-if="selected?.training_review" class="review-audit">Duyệt nhãn: {{ selected.training_review.verdict === 'approved' ? 'Đã duyệt' : 'Từ chối' }} · {{ selected.training_review.reviewer }}<br />{{ selected.training_review.note }}</p>
              <fieldset v-if="canReviewLabel" :disabled="busy" class="label-review"><h4>Duyệt nhãn độc lập</h4><label>Ghi chú duyệt nhãn<textarea v-model="reviewNote" rows="3" maxlength="5000" /></label><div class="status-actions"><button :disabled="!reviewNote.trim()" @click="action(() => reviewLabel('approved'))">Duyệt nhãn train</button><button :disabled="!reviewNote.trim()" class="secondary-button" @click="action(() => reviewLabel('rejected'))">Từ chối nhãn</button></div></fieldset>
            </template>
            <p v-else class="muted">Chưa có bản phân loại cho phiên bản này.</p>
          </section>
          <section class="source-area"><h3>Lời thoại nguồn</h3>
            <ol class="turns"><li v-for="t in turns" :key="t.id" :class="{ chosen: evidence.includes(t.id) }">
              <div class="turn-heading"><label v-if="editing && t.role === 'candidate' && !t.unclear" class="check"><input v-model="evidence" type="checkbox" :value="t.id" :aria-label="`Dẫn chứng lượt ${t.position}`" :disabled="busy" @change="dirty = true" />Dẫn chứng</label><span>{{ t.position }} · {{ t.role === 'candidate' ? 'Ứng viên' : t.role === 'consultant' ? 'Tư vấn viên' : 'Chưa rõ' }}</span><small v-if="t.unclear">Khó nghe</small><small v-if="t.start_seconds != null">{{ t.start_seconds.toFixed(1) }}s</small></div>
              <p>{{ t.text }}</p>
            </li></ol>
          </section>
        </div>
      </template>
    </template>
  </section>
</template>

<style scoped>
.candidate-status { min-width: 0; }
.status-header, .status-actions, .turn-heading { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; }
.status-header { justify-content: space-between; margin-bottom: 20px; }
h2, h3, h4 { margin: 0; } h2 { font-size: 24px; } h3 { font-size: 18px; } h4 { font-size: 15px; }
label { display: grid; gap: 8px; font-weight: 600; font-size: 14px; min-width: 0; color: #182e3c; }
input:not([type=checkbox]), select, textarea { box-sizing: border-box; width: 100%; min-width: 0; border: 1px solid #b9c9d3; border-radius: 4px; padding: 11px; color: #182e3c; background: white; font: inherit; }
select { text-overflow: ellipsis; } textarea { resize: vertical; line-height: 1.6; }
input[type=checkbox] { width: 18px; height: 18px; flex: 0 0 18px; accent-color: #0b806c; }
fieldset { border: 0; padding: 0; margin: 0; min-width: 0; }
.status-login { max-width: 420px; display: grid; gap: 18px; }
.context-controls { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 16px; }
audio { display: block; width: 100%; margin-top: 16px; }
.provider, .muted, small { color: #526879; font-size: 13px; line-height: 1.6; }
.provider { margin: 0 0 20px; }
.governance { margin-bottom: 20px; border-block: 1px solid #cbd7df; padding: 14px 0; }
.governance summary { cursor: pointer; font-weight: 600; } dt { font-weight: 600; margin-top: 12px; } dd { margin: 6px 0; line-height: 1.6; }
.governance .decision-form { display: grid; gap: 14px; max-width: 650px; }
.training-report, .label-review, .review-audit { margin-top: 20px; padding-top: 16px; border-top: 1px solid #cbd7df; }
.label-review label { margin-top: 12px; }
.current-state { display: grid; gap: 8px; padding: 20px 0; border-block: 1px solid #cbd7df; margin: 20px 0; }
.current-state span { font-size: 13px; color: #526879; } .current-state strong { font-size: 21px; color: #086b59; }
.status-actions { margin: 16px 0; } button { min-height: 42px; }
.status-layout { display: grid; grid-template-columns: minmax(0, 2fr) minmax(0, 3fr); gap: 28px; margin-top: 24px; }
.decision-area, .source-area { min-width: 0; border-top: 1px solid #cbd7df; padding-top: 20px; }
.decision-form { margin-top: 20px; } .next-step, .confirm-area { padding-top: 20px; border-top: 1px solid #cbd7df; margin-top: 20px; }
.check { display: flex; align-items: center; gap: 8px; font-size: 13px; line-height: 1.5; }
.confirm-area button { margin-top: 12px; }
.turns { margin: 16px 0 0; padding: 0; list-style: none; }
.turns li { border-bottom: 1px solid #cbd7df; padding: 16px 12px; border-left: 3px solid transparent; }
.turns li.chosen { border-left-color: #0b806c; background: #e0f1e9; }
.turn-heading { font-size: 12px; color: #526879; } .turns p { margin: 10px 0 0; white-space: pre-wrap; line-height: 1.7; overflow-wrap: anywhere; }
.notice { padding: 14px; color: #086346; background: #e0f1e9; border: 1px solid #9ccfb8; border-radius: 4px; }
.warning { padding: 12px; color: #714e10; background: #fff5d8; border-left: 3px solid #b8871a; }
@media (max-width: 900px) { .status-layout, .context-controls { grid-template-columns: minmax(0, 1fr); } }
</style>
