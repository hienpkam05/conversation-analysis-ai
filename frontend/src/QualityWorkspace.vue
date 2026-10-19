<script setup>
import { computed, onMounted, onUnmounted, ref, toRaw } from "vue";
import QualityGovernance from "./QualityGovernance.vue";
import QualityAiPanel from "./QualityAiPanel.vue";

const props = defineProps({ transcript: Object, audioUrl: String });
const title = ref("Hội thoại mới"), text = ref("");
const turns = ref([]), confirmed = ref(false), rubric = ref(null), ratings = ref([]);
const conversations = ref([]), history = ref([]), revision = ref(null);
const error = ref(""), notice = ref(""), busy = ref(false), selectedCriterion = ref(0);
const session = ref(null), username = ref(""), password = ref("");
const rubrics = ref([]);
const baseAssessment = ref(null);
const source = ref("text");
const samples = ref([]), selectedSample = ref(""), conversationId = ref(null);
const revisions = ref([]);
const reviewFlags = ref([]);
const disposition = ref("unreviewed"), reviewNote = ref(""), reviewDirty = ref(false);
const processedSamples = computed(() => samples.value.filter(s => ["ready", "no_speech"].includes(s.status)).length);
const dirty = ref(false), ratingDirty = ref(false), transcriptReviewed = ref(false);
const audioPlayer = ref(null);
const playbackUrl = computed(() => revision.value?.audio_url || selectedSample.value && samples.value.find(s => s.id === selectedSample.value)?.audio_url || (!conversationId.value && source.value === 'stt' ? props.audioUrl : null));
let refreshTimer;
function preventUnsavedClose(event) {
  if (dirty.value || ratingDirty.value || reviewDirty.value) { event.preventDefault(); event.returnValue = ""; }
}

async function refreshSamples() { samples.value = (await api("samples/")).items; }
function canLeave() { return !(reviewDirty.value || turns.value.length && (dirty.value || ratingDirty.value)) || window.confirm("Bản đang sửa chưa lưu. Bỏ thay đổi để mở hội thoại khác?"); }
async function openSample(id) {
  if (!canLeave()) return;
  const sample = samples.value.find(s => s.id === id);
  await openConversation(sample.conversation_id);
  selectedSample.value = id;
  disposition.value = sample.review_disposition || "unreviewed"; reviewNote.value = sample.review_note || ""; reviewDirty.value = false;
}
async function saveSampleReview() {
  await api(`samples/${selectedSample.value}/review/`, {disposition: disposition.value, note: reviewNote.value});
  reviewDirty.value = false; await refreshSamples(); notice.value = "Đã lưu tình trạng bản ghi, chưa duyệt để huấn luyện.";
}
function seek(seconds) {
  if (audioPlayer.value && seconds !== null) { audioPlayer.value.currentTime = seconds; audioPlayer.value.play().catch(() => {}); }
}
function newConversation() {
  if (!canLeave()) return;
  selectedSample.value = ""; conversationId.value = null; revision.value = null;
  revisions.value = [];
  reviewFlags.value = [];
  reviewDirty.value = false;
  turns.value = []; history.value = []; title.value = "Hội thoại mới";
  confirmed.value = false; transcriptReviewed.value = false; dirty.value = false; ratingDirty.value = false; resetRatings();
  source.value = "text";
}
function statusLabel(status) {
  return ({pending: "Chờ nhận dạng", running: "Đang nhận dạng", ready: "Có transcript nháp", no_speech: "Chưa phát hiện lời nói", failed: "Lỗi nhận dạng", needs_review: "Chờ duyệt", draft: "Bản nháp", approved: "Đã duyệt", retired: "Ngừng sử dụng"})[status] || status;
}

async function api(path, data, method = "POST", options = {}) {
  let response;
  try {
    response = await fetch(`/api/quality/${path}`, data === undefined ? options : { ...options,
      method, headers: { "Content-Type": "application/json", "X-CSRFToken": session.value?.csrf_token || "" }, body: JSON.stringify(data)
    });
  } catch (e) {
    if (e.name === "AbortError") throw e;
    throw new Error("Không kết nối được API đánh giá. Kiểm tra Django đang chạy.");
  }
  let payload;
  try { payload = await response.json(); } catch { throw new Error("API chưa sẵn sàng. Kiểm tra Django và proxy /api."); }
  if (!response.ok) throw new Error(payload.error?.message || "Không thể tải dữ liệu.");
  return payload;
}
async function loadWorkspace() {
  rubrics.value = (await api("rubrics/")).rubrics;
  rubric.value = rubrics.value.find(r => r.status !== "retired") || rubrics.value[0]; resetRatings();
  conversations.value = (await api("conversations/")).items;
  await refreshSamples();
}
async function signIn() {
  try { session.value = await api("session/", {username: username.value, password: password.value}); }
  finally { password.value = ""; }
  await loadWorkspace();
}
async function signOut() {
  if (!canLeave()) return;
  session.value = await api("session/", {}, "DELETE");
  dirty.value = false; ratingDirty.value = false; reviewDirty.value = false;
  newConversation(); samples.value = []; conversations.value = [];
}
async function reloadGovernance() {
  const version = rubric.value.version;
  rubrics.value = (await api("rubrics/")).rubrics;
  rubric.value = rubrics.value.find(r => r.version === version) || rubrics.value[0];
  if (revision.value) history.value = (await api(`revisions/${revision.value.id}/assessments/`)).items;
  await refreshSamples();
}
async function changeRubric(id) {
  if (ratingDirty.value && !window.confirm("Bỏ bản chấm chưa lưu để đổi bộ tiêu chí?")) return;
  rubric.value = rubrics.value.find(r => r.id === id); resetRatings(); ratingDirty.value = false;
}
async function action(fn) {
  busy.value = true; error.value = ""; notice.value = "";
  try { await fn(); } catch (e) { error.value = e.message; } finally { busy.value = false; }
}
function resetRatings() {
  baseAssessment.value = null;
  ratings.value = (rubric.value?.criteria || []).map(c => ({ criterion_code: c.code, score: null,
    not_assessable_reason: "", comment: "", evidence: { kind: "quote", utterance_ids: [] } }));
}
function makeTurn(value) {
  return { id: crypto.randomUUID(), role: "unknown", text: value, start_seconds: null, end_seconds: null };
}
function edited() {
  dirty.value = true; confirmed.value = false; transcriptReviewed.value = false;
}
function remapEvidence(removedIds, replacements = []) {
  for (const rating of ratings.value) {
    const ids = rating.evidence.utterance_ids;
    if (ids.some(id => removedIds.includes(id))) {
      rating.evidence.utterance_ids = [...new Set(ids.flatMap(id => removedIds.includes(id) ? replacements : [id]))];
      ratingDirty.value = true;
    }
  }
}
function removeTurn(index) {
  remapEvidence([turns.value[index].id]); edited(); turns.value.splice(index, 1);
}
function importText() {
  if (!text.value.trim()) return;
  if (!canLeave()) return;
  conversationId.value = null; selectedSample.value = ""; revision.value = null; history.value = []; resetRatings();
  revisions.value = [];
  reviewFlags.value = [];
  edited(); source.value = "text";
  turns.value = text.value.split(/\n+/).map(x => x.trim()).filter(Boolean).map(makeTurn);
}
function importTranscript() {
  if (!props.transcript) return;
  if (!canLeave()) return;
  conversationId.value = null; selectedSample.value = ""; revision.value = null; history.value = []; resetRatings();
  revisions.value = [];
  reviewFlags.value = [];
  edited(); source.value = "stt";
  const segments = props.transcript.segments || [];
  turns.value = segments.length ? segments.map(s => ({ ...makeTurn(s.text), start_seconds: s.start ?? null, end_seconds: s.end ?? null }))
    : (props.transcript.full_text || props.transcript.dialogue_text || "").split(/\n+/).filter(Boolean).map(makeTurn);
  title.value = props.transcript.original_name || "Hội thoại từ audio";
}
function splitTurn(index) {
  const turn = turns.value[index], separator = turn.text.indexOf("\n");
  if (separator < 0) { error.value = "Đặt xuống dòng tại vị trí cần tách lượt nói."; return; }
  const first = turn.text.slice(0, separator).trim(), second = turn.text.slice(separator + 1).trim();
  if (!first || !second) { error.value = "Hai phần của lượt nói cần có nội dung."; return; }
  const newTurns = [makeTurn(first), makeTurn(second)];
  remapEvidence([turn.id], newTurns.map(t => t.id));
  edited(); turns.value.splice(index, 1, ...newTurns);
}
function mergeTurn(index) {
  const first = turns.value[index], second = turns.value[index + 1];
  const merged = makeTurn(`${first.text} ${second.text}`);
  remapEvidence([first.id, second.id], [merged.id]);
  edited(); turns.value.splice(index, 2, merged);
}
function chooseEvidence(id) {
  ratingDirty.value = true;
  const ids = ratings.value[selectedCriterion.value].evidence.utterance_ids;
  const index = ids.indexOf(id);
  if (index < 0) ids.push(id); else ids.splice(index, 1);
}
async function saveConversation() {
  if (revision.value && !dirty.value) return;
  revision.value = await api(conversationId.value ? `conversations/${conversationId.value}/revisions/` : "conversations/", { title: title.value, source_type: source.value,
    expected_revision_id: revision.value?.id,
    roles_confirmed: confirmed.value, transcript_reviewed: transcriptReviewed.value, utterances: turns.value });
  conversationId.value = revision.value.conversation_id; dirty.value = false;
  baseAssessment.value = null;
  const idMap = revision.value.utterance_id_map || {};
  for (const rating of ratings.value) rating.evidence.utterance_ids = rating.evidence.utterance_ids.map(id => idMap[id] || id);
  reviewFlags.value = revision.value.review_flags || [];
  history.value = [];
  revisions.value = (await api(`conversations/${conversationId.value}/`)).revisions;
  turns.value = revision.value.utterances;
  conversations.value = (await api("conversations/")).items;
  notice.value = "Đã lưu bản hội thoại. Các chỉnh sửa tiếp theo được lưu thành bản riêng.";
}
async function saveAssessment(status = "draft") {
  if (!revision.value || dirty.value) await saveConversation();
  const saved = await api(`revisions/${revision.value.id}/assessments/`, {
    rubric_version: rubric.value.version, ratings: ratings.value, status, supersedes_id: baseAssessment.value
  });
  history.value.unshift(saved);
  revision.value = saved.revision;
  baseAssessment.value = saved.id;
  ratingDirty.value = false;
  await refreshSamples();
  notice.value = status === "draft" ? "Đã lưu nháp. Dữ liệu chưa được duyệt để huấn luyện." : "Đã hoàn tất bản chấm, đang chờ duyệt. Chưa đưa vào train.";
}
async function openConversation(id) {
  const data = await api(`conversations/${id}/`);
  conversationId.value = id;
  revisions.value = data.revisions; title.value = data.title;
  await loadRevision(data.revisions[0]);
}
async function loadRevision(value) {
  revision.value = value;
  reviewFlags.value = value?.review_flags || [];
  turns.value = revision.value ? structuredClone(toRaw(revision.value.utterances)) : [];
  confirmed.value = revision.value?.roles_confirmed || false;
  transcriptReviewed.value = revision.value?.transcript_reviewed || false;
  source.value = revision.value?.source_type || "stt"; resetRatings();
  history.value = revision.value ? (await api(`revisions/${revision.value.id}/assessments/`)).items : [];
  const compatible = history.value.find(item => item.rubric.version === rubric.value.version && item.author_id === session.value.user_id);
  if (compatible) { ratings.value = structuredClone(toRaw(compatible.ratings)); baseAssessment.value = compatible.id; }
  else if (history.value.some(item => item.rubric.version !== rubric.value.version)) notice.value = "Bản chấm cũ dùng bộ tiêu chí khác, được giữ trong lịch sử. Bản chấm mới cần chấm lại theo tiêu chí hiện tại.";
  dirty.value = false; ratingDirty.value = false;
}
function quote(item, ids) {
  return item.revision.utterances.filter(t => ids.includes(t.id)).map(t => `${t.position}. ${t.text}`).join("\n");
}
async function reloadAiHistory() {
  if (revision.value) history.value = (await api(`revisions/${revision.value.id}/assessments/`)).items;
  await refreshSamples();
}
async function copyModel(item) {
  if (dirty.value || ratingDirty.value || reviewDirty.value) throw new Error("Lưu các thay đổi đang sửa trước khi mở bản AI để kiểm tra.");
  const copied = await api(`assessments/${item.id}/manual-copy/`, {});
  rubric.value = rubrics.value.find(r => r.version === copied.rubric.version);
  ratings.value = structuredClone(copied.ratings); baseAssessment.value = copied.id;
  history.value.unshift(copied); ratingDirty.value = false;
  notice.value = "Đã tạo bản thủ công riêng. Kết quả AI gốc không thay đổi.";
}
onMounted(() => action(async () => {
  window.addEventListener("beforeunload", preventUnsavedClose);
  session.value = await api("session/");
  if (session.value.authenticated) await loadWorkspace();
  refreshTimer = setInterval(() => { if (session.value?.authenticated && samples.value.some(s => ["pending", "running"].includes(s.status))) refreshSamples().catch(() => {}); }, 5000);
}));
onUnmounted(() => { clearInterval(refreshTimer); window.removeEventListener("beforeunload", preventUnsavedClose); });
</script>

<template>
  <section class="workspace quality-workspace" aria-label="Đánh giá tư vấn">
    <header class="quality-header"><h2>Đánh giá tư vấn</h2><span v-if="session?.authenticated">{{ session.username }} · {{ session.can_review ? 'Người phụ trách' : 'Người chấm' }}</span><button v-if="session?.authenticated" :disabled="busy" @click="action(signOut)">Đăng xuất</button></header>
    <p v-if="error" class="alert" role="alert">{{ error }}</p>
    <p v-if="notice" class="quality-notice" role="status">{{ notice }}</p>
    <form v-if="session && !session.authenticated" class="quality-login" @submit.prevent="action(signIn)">
      <h3>Đăng nhập chấm tư vấn</h3>
      <label>Tài khoản<input v-model="username" autocomplete="username" maxlength="150" required /></label>
      <label>Mật khẩu<input v-model="password" type="password" autocomplete="current-password" required /></label>
      <button :disabled="busy" type="submit">Đăng nhập</button>
    </form>
    <template v-if="session?.authenticated">
    <label v-if="rubric">Bộ tiêu chí<select :value="rubric.id" :disabled="busy" @change="action(() => changeRubric($event.target.value))"><option v-for="r in rubrics" :key="r.id" :value="r.id">{{ r.version }} · {{ statusLabel(r.status) }}</option></select></label>
    <details v-if="rubric" class="quality-guide"><summary>Quy tắc chấm · {{ rubric.version }}</summary><ul><li v-for="rule in rubric.general_rules" :key="rule">{{ rule }}</li></ul></details>
    <QualityAiPanel :api="api" :revision="revision" :rubric="rubric" :dirty="dirty || ratingDirty || reviewDirty" @assessment-ready="action(reloadAiHistory)" @sealed="revision = $event" />
    <audio v-if="playbackUrl" ref="audioPlayer" :src="playbackUrl" controls preload="metadata" aria-label="Nghe lại bản ghi đang chọn" />
    <fieldset :disabled="busy || !rubric" class="quality-fields">
      <section v-if="samples.length" class="quality-pilot"><h3>Đợt audio mẫu · {{ samples.length }} cuộc gọi</h3>
        <p>{{ processedSamples }}/{{ samples.length }} đã nhận dạng · {{ samples.filter(s => s.label_status === 'needs_review').length }} bản chấm chờ duyệt</p>
        <progress :value="processedSamples" :max="samples.length" aria-label="Tiến độ nhận dạng audio mẫu" />
        <div class="quality-actions"><label>Audio gán nhãn<select :value="selectedSample" @change="action(() => openSample($event.target.value))">
          <option value="" disabled>Chọn mẫu để nghe và chấm</option>
          <option v-for="s in samples" :key="s.id" :value="s.id" :disabled="['pending', 'running', 'failed'].includes(s.status)">{{ s.call_id }} · {{ Math.round(s.duration_seconds) }}s · {{ statusLabel(s.label_status || s.status) }}</option>
        </select></label><button type="button" @click="action(refreshSamples)">Cập nhật danh sách</button></div>
        <p v-if="selectedSample && !turns.length">Chưa có lời thoại nhận dạng được. Bạn có thể nghe lại và thêm lượt nói thủ công.</p>
        <div v-if="selectedSample" class="quality-actions">
          <label>Tình trạng bản ghi<select v-model="disposition" @change="reviewDirty = true"><option value="unreviewed">Chưa kiểm tra</option><option value="usable">Có thể chấm</option><option value="no_speech">Không có lời nói</option><option value="unclear">Khó nghe</option><option value="incomplete">Bản ghi bị cắt</option></select></label>
          <label>Ghi chú bản ghi<input v-model="reviewNote" maxlength="5000" @input="reviewDirty = true" /></label>
          <button type="button" @click="action(saveSampleReview)">Lưu tình trạng bản ghi</button>
        </div>
      </section>
      <div class="quality-actions">
        <label>Hội thoại đã lưu<select :value="conversationId || ''" @change="action(async () => { if (canLeave()) { selectedSample = ''; await openConversation($event.target.value); } })">
          <option value="" disabled>Chọn hội thoại</option>
          <option v-for="c in conversations" :key="c.id" :value="c.id">{{ c.title }} · {{ new Date(c.created_at).toLocaleString('vi-VN') }}</option>
        </select></label>
        <button v-if="transcript" type="button" @click="importTranscript">Lấy hội thoại từ audio</button>
        <button type="button" @click="newConversation">Hội thoại mới</button>
      </div>
      <label v-if="revisions.length > 1">Phiên bản transcript<select :value="revision?.id" @change="action(async () => { if (canLeave()) await loadRevision(revisions.find(r => r.id === $event.target.value)); })"><option v-for="(r, i) in revisions" :key="r.id" :value="r.id">{{ i === 0 ? 'Mới nhất' : `Bản trước ${i}` }} · {{ r.id.slice(0, 8) }}</option></select></label>
      <p v-if="revision && revisions.length && revision.id !== revisions[0].id" class="quality-model">Đang xem phiên bản cũ. Mở phiên bản mới nhất trước khi lưu chỉnh sửa.</p>
      <p v-if="reviewFlags.length" class="quality-warning" role="status">{{ reviewFlags.length }} đoạn nhận dạng cần nghe kiểm tra. Chưa xác nhận đây là lời nói thật.</p>
      <label v-if="!conversationId">Tên hội thoại<input v-model="title" maxlength="200" @input="edited" /></label>
      <details :open="!conversationId" class="quality-import">
        <summary>Nhập hội thoại từ văn bản</summary>
        <label>Văn bản hội thoại<textarea v-model="text" rows="4" placeholder="Dán nội dung hội thoại" /></label>
        <div class="quality-actions"><button type="button" @click="importText">Nhập hội thoại</button></div>
      </details>
      <div class="quality-actions"><button type="button" @click="edited(); turns.push(makeTurn(''))">Thêm lượt nói</button></div>
      <div v-if="turns.length" class="quality-columns">
        <section class="quality-turns"><h3>Lời thoại</h3>
          <article v-for="(turn, index) in turns" :key="turn.id" class="quality-turn">
            <p v-for="flag in reviewFlags.filter(f => f.utterance_id === turn.id)" :key="flag.utterance_id" class="quality-warning">{{ flag.reasons.join(' ') }}</p>
            <div class="quality-turn-heading"><strong>{{ index + 1 }}</strong>
              <select v-model="turn.role" :aria-label="`Người nói lượt ${index + 1}`" @change="edited">
                <option value="unknown">Chưa xác định</option><option value="consultant">Tư vấn viên</option><option value="candidate">Ứng viên</option>
              </select>
              <label v-if="ratings.length" class="quality-check"><input type="checkbox" :checked="ratings[selectedCriterion].evidence.utterance_ids.includes(turn.id)" @change="chooseEvidence(turn.id)" />Dẫn chứng</label>
            </div>
            <textarea v-model="turn.text" rows="3" :aria-label="`Nội dung lượt ${index + 1}`" @input="edited" />
            <div class="quality-actions"><button v-if="turn.start_seconds !== null" type="button" @click="seek(turn.start_seconds)">Nghe từ {{ Number(turn.start_seconds).toFixed(1) }}s</button><button type="button" @click="splitTurn(index)">Tách lượt</button><button v-if="index < turns.length - 1" type="button" @click="mergeTurn(index)">Gộp lượt sau</button><button type="button" @click="removeTurn(index)">Xóa lượt</button></div>
          </article>
          <label class="quality-check"><input v-model="confirmed" type="checkbox" @change="dirty = true" />Đã kiểm tra vai trò người nói</label>
          <label class="quality-check"><input v-model="transcriptReviewed" type="checkbox" @change="dirty = true" />Đã nghe đối chiếu và sửa transcript</label>
          <button type="button" @click="action(saveConversation)">{{ busy ? 'Đang lưu…' : 'Lưu hội thoại' }}</button>
        </section>
        <section class="quality-ratings" @input="ratingDirty = true" @change="ratingDirty = true"><h3>Chấm điểm</h3>
          <article v-for="(criterion, i) in rubric.criteria" :key="criterion.code" class="quality-rating" :class="{selected: selectedCriterion === i}">
            <label class="quality-check"><input v-model="selectedCriterion" type="radio" :value="i" name="criterion" /><strong>{{ criterion.name }}</strong></label>
            <p>{{ criterion.description }}</p>
            <details v-if="criterion.levels" class="quality-guide">
              <summary>Mức điểm và ví dụ</summary>
              <dl><template v-for="(description, score) in criterion.levels" :key="score"><dt>{{ score }} điểm</dt><dd>{{ description }}</dd></template><dt>Không đủ dữ liệu</dt><dd>{{ criterion.not_assessable }}</dd></dl>
              <p>{{ criterion.boundary }}</p><p class="quality-example">Ví dụ giả định: {{ criterion.example }}</p>
            </details>
            <select v-model="ratings[i].score" :aria-label="`Điểm ${criterion.name}`"><option :value="null">Không đủ dữ liệu</option><option :value="0">0 · Chưa đạt</option><option :value="1">1 · Đạt một phần</option><option :value="2">2 · Đạt</option></select>
            <label v-if="ratings[i].score === null">Lý do<input v-model="ratings[i].not_assessable_reason" maxlength="5000" /></label>
            <template v-else><label>Loại bằng chứng<select v-model="ratings[i].evidence.kind"><option value="quote">Lời thoại</option><option v-if="ratings[i].score === 0" value="absence">Hành vi không xuất hiện</option></select></label><small>{{ ratings[i].evidence.utterance_ids.length }} lượt đã chọn</small></template>
            <label>Nhận xét<textarea v-model="ratings[i].comment" rows="2" maxlength="5000" /></label>
          </article>
          <div class="quality-actions"><button type="button" @click="action(() => saveAssessment('draft'))">Lưu nháp</button><button type="button" @click="action(() => saveAssessment('needs_review'))">Hoàn tất · Chờ duyệt</button></div>
        </section>
      </div>
    </fieldset>
    <section v-if="history.length" class="quality-history"><h3>Lịch sử đánh giá</h3>
      <article v-for="item in history" :key="item.id" class="quality-history-item">
        <h4>{{ item.total_score === null ? 'Chưa đủ dữ liệu' : `${item.total_score}/100` }} · {{ item.source === 'model' ? 'AI' : 'Thủ công' }} · {{ statusLabel(item.status) }}</h4>
        <small>{{ new Date(item.created_at).toLocaleString('vi-VN') }} · {{ item.rubric.version }} · {{ item.source === 'model' ? item.model_version : `Người chấm: ${item.author || 'Bản cũ chưa có tài khoản'}` }}</small>
        <p v-if="item.source === 'model'" class="quality-warning">Cần người kiểm tra · Dẫn chứng chưa xác nhận</p>
        <button v-if="item.source === 'model'" type="button" :disabled="busy || dirty || ratingDirty || reviewDirty" @click="action(() => copyModel(item))">Tạo bản thủ công từ AI</button>
        <p v-if="item.supersedes_id" class="quality-record-id">Dựa trên bản chấm: {{ item.supersedes_id }}</p>
        <p v-if="item.reviewer">Người duyệt: {{ item.reviewer }} · {{ item.review_note }}</p>
        <p class="quality-record-id">Mã bản chấm: {{ item.id }} · Transcript: {{ item.revision.id }}</p>
        <div v-for="rating in item.ratings" :key="rating.criterion_code">
          <p><strong>{{ item.rubric.criteria.find(c => c.code === rating.criterion_code)?.name }}</strong>: {{ rating.score ?? 'Không đủ dữ liệu' }}</p>
          <p>{{ rating.comment || rating.not_assessable_reason }}</p>
          <p v-if="rating.evidence.kind === 'absence'">Phạm vi đã xem xét:</p>
          <blockquote v-if="rating.evidence.utterance_ids.length">{{ quote(item, rating.evidence.utterance_ids) }}</blockquote>
        </div>
      </article>
    </section>
    <QualityGovernance v-if="rubric && session.can_review" :api="api" :rubric="rubric" :history="history" :ratings="ratings" :revision="revision" :dirty="dirty || ratingDirty || reviewDirty" @changed="action(reloadGovernance)" />
    </template>
  </section>
</template>

<style scoped>
.quality-header,.quality-actions,.quality-turn-heading{display:flex;align-items:center;gap:12px;flex-wrap:wrap}
.quality-header{justify-content:space-between}.quality-header h2{font-size:24px}.quality-header span,.quality-model{color:#53636a;font-size:14px}
.quality-fields{border:0;padding:0;margin:0;min-width:0;display:grid;gap:16px}
label{display:grid;gap:7px;font-size:14px;color:#24343d}input,select,textarea{width:100%;min-width:0;padding:10px;border:1px solid #b7c4cb;border-radius:4px;background:white;color:#17202a;font:inherit}
textarea{resize:vertical}button{font-size:14px;padding:9px 14px;max-width:100%;white-space:normal}
.quality-actions{margin:8px 0}.quality-actions label{flex:1;min-width:180px}.quality-columns{display:grid;grid-template-columns:minmax(0,1.2fr) minmax(0,1fr);gap:24px;align-items:start}
.quality-turn,.quality-rating{padding:14px 0;border-bottom:1px solid #ccd6db;display:grid;gap:10px}.quality-turn-heading select{width:auto;max-width:180px}
.quality-check{display:flex;align-items:center;gap:8px}.quality-check input{width:18px;height:18px;flex-shrink:0}.quality-rating.selected{border-left:3px solid #0c8069;padding-left:12px}
.quality-rating p{font-size:14px;margin:0;color:#53636a}.quality-notice{color:#08664e}.quality-history{margin-top:30px}.quality-history-item{border-top:1px solid #b7c4cb;padding:14px 0}
blockquote{white-space:pre-wrap;overflow-wrap:anywhere;margin:8px 0;padding:10px 14px;border-left:3px solid #0c8069;background:#e8f3ef}
.quality-workspace{overflow-wrap:anywhere}h3{font-size:18px}h4{font-size:16px}
.quality-login{max-width:400px;display:grid;gap:16px;padding:24px 0}
.quality-warning{font-size:14px;color:#804700;background:#fff1cb;padding:10px;border-left:3px solid #b77300}
audio{width:100%;max-width:640px;margin:12px 0}
.quality-import summary{cursor:pointer;font-size:14px;color:#435b64;padding:8px 0}.quality-import label{margin-top:12px}
.quality-guide{font-size:14px;color:#24343d}.quality-guide summary{cursor:pointer;padding:8px 0;font-weight:600}.quality-guide li{margin:8px 0;line-height:1.5}.quality-guide dl{margin:8px 0}.quality-guide dt{font-weight:700;margin-top:12px}.quality-guide dd{margin:4px 0 0;line-height:1.5}.quality-guide .quality-example{margin-top:10px;padding:10px;background:#e5efea}.quality-record-id{font-size:12px;color:#53636a;overflow-wrap:anywhere}
@media(max-width:1000px){.quality-columns{grid-template-columns:minmax(0,1fr)}}
</style>
