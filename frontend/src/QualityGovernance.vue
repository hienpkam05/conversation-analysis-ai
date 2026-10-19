<script setup>
import { computed, ref, toRaw, watch } from "vue";

const props = defineProps({api: Function, rubric: Object, history: Array, ratings: Array, revision: Object, dirty: Boolean});
const emit = defineEmits(["changed"]);
const editor = ref(null), rulesText = ref(""), busy = ref(false), error = ref(""), notice = ref("");
const selection = ref([]), rationale = ref(""), approvalNote = ref(""), confirmed = ref(false), records = ref(null);
const reviewNotes = ref({});
const candidates = computed(() => props.history.filter(x => x.status === "needs_review" && x.rubric.version === props.rubric.version && x.author));
const pair = computed(() => candidates.value.filter(x => selection.value.includes(x.id)));
const different = computed(() => props.rubric.criteria.map(c => ({...c, values: pair.value.map(a => a.ratings.find(r => r.criterion_code === c.code)?.score ?? null)})));
async function run(fn) {
  busy.value = true; error.value = ""; notice.value = "";
  try { await fn(); } catch (e) { error.value = e.message; } finally { busy.value = false; }
}
async function refresh() { records.value = await props.api(`pilot-resolutions/?rubric_id=${props.rubric.id}`); }
watch(() => props.rubric.id, () => { editor.value = null; records.value = null; selection.value = []; run(refresh); }, {immediate: true});
watch(() => props.revision?.id, () => {selection.value = []; rationale.value = "";});
function edit(clone) {
  editor.value = structuredClone(toRaw(props.rubric));
  if (clone) { editor.value.version = ""; editor.value.id = null; }
  rulesText.value = editor.value.general_rules.join("\n");
}
async function saveRubric() {
  editor.value.general_rules = rulesText.value.split("\n").map(x => x.trim()).filter(Boolean);
  await props.api(editor.value.id ? `rubrics/${editor.value.id}/` : "rubrics/", editor.value, editor.value.id ? "PUT" : "POST");
  editor.value = null; notice.value = "Đã lưu bộ tiêu chí nháp; chưa phê duyệt nghiệp vụ."; emit("changed");
}
async function resolve() {
  if (props.dirty) throw new Error("Lưu bản hội thoại, bản chấm và tình trạng audio trước khi lập biên bản.");
  await props.api("pilot-resolutions/", {assessment_ids: selection.value, ratings: props.ratings, rationale: rationale.value});
  await refresh(); notice.value = "Đã lưu kết luận thống nhất. Nhãn chưa được duyệt để huấn luyện."; emit("changed");
}
async function approveRubric() {
  await props.api(`rubrics/${props.rubric.id}/approve/`, {confirm_business_rules: confirmed.value, note: approvalNote.value});
  notice.value = "Đã chốt rubric và lưu người duyệt, thời điểm, kết luận."; emit("changed");
}
async function approveAssessment(item) {
  await props.api(`assessments/${item.id}/approve/`, {note: reviewNotes.value[item.id] || ""});
  emit("changed"); notice.value = "Đã duyệt bản chấm. Không tự động chạy huấn luyện.";
}
</script>

<template>
  <section class="governance" aria-label="Duyệt nghiệp vụ">
    <h3>Duyệt nghiệp vụ</h3>
    <p v-if="error" role="alert" class="alert">{{ error }}</p><p v-if="notice" role="status">{{ notice }}</p>
    <fieldset :disabled="busy">
      <details><summary>Quản lý bộ tiêu chí</summary>
        <p>{{ rubric.version }} · {{ rubric.status === 'approved' ? 'Đã duyệt' : 'Bản nháp' }}</p>
        <p v-if="rubric.approved_by">{{ rubric.approved_by }} · {{ new Date(rubric.approved_at).toLocaleString('vi-VN') }} · {{ rubric.approval_note }}</p>
        <div class="actions"><button type="button" v-if="rubric.status === 'draft'" @click="edit(false)">Sửa nháp</button><button type="button" @click="edit(true)">Tạo phiên bản mới</button></div>
        <form v-if="editor" @submit.prevent="run(saveRubric)">
          <label>Mã phiên bản<input v-model="editor.version" :readonly="!!editor.id" maxlength="80" required /></label>
          <label>Quy tắc chung<textarea v-model="rulesText" rows="5" required /></label>
          <section v-for="c in editor.criteria" :key="c.code" class="criterion">
            <h4>{{ c.code }}</h4><label>Tên<input v-model="c.name" required maxlength="5000" /></label>
            <label>Trọng số<input v-model.number="c.weight" type="number" min="0.001" max="1" step="0.001" required /></label>
            <label>Mô tả<textarea v-model="c.description" required maxlength="5000" /></label>
            <label v-for="s in ['0','1','2']" :key="s">Mức {{ s }}<textarea v-model="c.levels[s]" required maxlength="5000" /></label>
            <label>Không đủ dữ liệu<textarea v-model="c.not_assessable" required maxlength="5000" /></label>
            <label>Ranh giới chấm<textarea v-model="c.boundary" required maxlength="5000" /></label>
            <label>Ví dụ giả định<textarea v-model="c.example" required maxlength="5000" /></label>
          </section>
          <div class="actions"><button type="submit">Lưu tiêu chí</button><button type="button" @click="editor = null">Hủy</button></div>
        </form>
      </details>
      <details><summary>Chấm kép và giải quyết bất đồng</summary>
        <div v-if="candidates.length" class="choices"><label v-for="a in candidates" :key="a.id"><input type="checkbox" v-model="selection" :value="a.id" />{{ a.author }} · {{ a.id }}</label></div>
        <p v-else>Chưa có hai bản chấm hoàn tất trên transcript đang mở.</p>
        <div v-if="pair.length === 2" class="table-scroll"><table><thead><tr><th>Tiêu chí</th><th v-for="a in pair" :key="a.id">{{ a.author }}</th><th>Đối chiếu</th></tr></thead><tbody><tr v-for="c in different" :key="c.code"><th>{{ c.name }}</th><td v-for="(v,i) in c.values" :key="i">{{ v ?? 'Không đủ dữ liệu' }}</td><td>{{ c.values[0] === c.values[1] ? 'Cùng mức' : 'Khác mức' }}</td></tr></tbody></table></div>
        <label>Kết luận thống nhất<textarea v-model="rationale" rows="3" maxlength="5000" /></label>
        <button type="button" :disabled="selection.length !== 2 || !revision || dirty" @click="run(resolve)">Lập biên bản theo điểm và dẫn chứng đang chọn</button>
      </details>
      <details><summary>Chốt rubric · {{ records?.distinct_calls || 0 }}/3 cuộc gọi</summary>
        <ul><li v-for="r in records?.items || []" :key="r.id">{{ r.title }} · {{ r.annotators.join(' / ') }} · {{ r.adjudicator }}<p>{{ r.rationale }}</p></li></ul>
        <template v-if="rubric.status === 'draft'">
          <label class="check"><input type="checkbox" v-model="confirmed" />Tôi xác nhận năm tiêu chí, các mức 0/1/2, trọng số và quy tắc không đủ dữ liệu.</label>
          <label>Kết luận nghiệp vụ<textarea v-model="approvalNote" maxlength="5000" rows="3" /></label>
          <button type="button" :disabled="!confirmed || !approvalNote.trim() || (records?.distinct_calls || 0) < 3" @click="run(approveRubric)">Duyệt bộ tiêu chí</button>
        </template>
      </details>
      <details><summary>Duyệt bản chấm</summary>
        <section v-for="a in candidates" :key="a.id" class="criterion"><p>{{ a.author }} · {{ a.id }}</p><label>Nhận xét duyệt<textarea v-model="reviewNotes[a.id]" maxlength="5000" rows="2" /></label><button type="button" :disabled="rubric.status !== 'approved'" @click="run(() => approveAssessment(a))">Duyệt nhãn</button></section>
      </details>
    </fieldset>
  </section>
</template>

<style scoped>
.governance{margin-top:28px;border-top:1px solid #b7c4cb;padding-top:16px}h3{font-size:18px}h4{font-size:16px}fieldset{border:0;padding:0;min-width:0}details{border-bottom:1px solid #ccd6db;padding:12px 0}summary{cursor:pointer;font-weight:600}form,.criterion{display:grid;gap:12px;margin:16px 0}.criterion{border-bottom:1px solid #ccd6db;padding-bottom:16px}label{display:grid;gap:6px;font-size:14px;color:#24343d}input,textarea{width:100%;min-width:0;box-sizing:border-box;padding:10px;border:1px solid #b7c4cb;border-radius:4px;font:inherit;background:white;color:#17202a}textarea{resize:vertical}.actions{display:flex;gap:10px;flex-wrap:wrap;margin:12px 0}button{font-size:14px;padding:10px 14px;white-space:normal;max-width:100%}.check,.choices label{display:flex;align-items:center;gap:8px;margin:12px 0;overflow-wrap:anywhere}.check input,.choices input{width:18px;height:18px;flex-shrink:0}.table-scroll{overflow:auto}table{border-collapse:collapse;width:100%;font-size:14px}th,td{text-align:left;border-bottom:1px solid #ccd6db;padding:10px;min-width:100px}p,li{font-size:14px;overflow-wrap:anywhere;line-height:1.5}
</style>
