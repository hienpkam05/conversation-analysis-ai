<script setup>
import { computed, onMounted, onUnmounted, ref, toRaw } from "vue";

const session = ref(null), username = ref(""), password = ref(""), busy = ref(false), error = ref(""), notice = ref("");
const conversations = ref([]), conversationId = ref(""), revisions = ref([]), revisionId = ref("");
const summaries = ref([]), summary = ref(null), sections = ref([]), dirty = ref(false), contentConfirmed = ref(false);
const appointments = ref([]), selectedAppointment = ref(null), appointmentDirty = ref(false), participantsConfirmed = ref(false);
const allSchedules = ref(false);
const categories = {context:"Ngữ cảnh",needs:"Nhu cầu ứng viên",job:"Thông tin công việc",questions:"Câu hỏi cần đối chiếu",next_steps:"Lời nhắc về bước tiếp theo"};
const revision = computed(() => revisions.value.find(r => r.id === revisionId.value));
const editable = computed(() => summary.value?.source === 'manual' && summary.value.status === 'draft' && (summary.value.author_id === session.value?.user_id || session.value?.can_review));
const emptyForm = () => ({title:"",participant:"",responsible:"",channel:"phone",location:"",starts_at:"",ends_at:"",evidence_ids:[]});
const form = ref(emptyForm()); let requestKey = crypto.randomUUID();
const statusLabel = s => ({draft:"Bản nháp",approved:"Đã duyệt",confirmed:"Đã xác nhận",cancelled:"Đã hủy"})[s] || s;
const sourceLabel = s => s === 'manual' ? 'Thủ công' : 'Trích dẫn theo quy tắc';
const timeLabel = v => v ? new Date(v).toLocaleString('vi-VN',{timeZone:'Asia/Ho_Chi_Minh'}) : 'Chưa xác định';
const localTime = v => v ? new Date(new Date(v).getTime()+7*3600000).toISOString().slice(0,16) : '';
const isoTime = v => v ? `${v}:00+07:00` : null;

async function api(path, data, method="POST", quality=false) {
  let response;
  try { response = await fetch(`/api/${quality ? 'quality' : 'followup'}/${path}`, data === undefined ? {} : {method,headers:{'Content-Type':'application/json','X-CSRFToken':session.value?.csrf_token || ''},body:JSON.stringify(data)}); }
  catch { throw new Error('Không kết nối được Django. Kiểm tra backend và proxy /api.'); }
  let payload;
  try { payload=await response.json(); } catch { throw new Error('API chưa sẵn sàng hoặc trả dữ liệu không hợp lệ.'); }
  if(!response.ok) throw new Error(payload.error?.message || 'Không thực hiện được yêu cầu.');
  return payload;
}
async function action(fn) {busy.value=true;error.value='';notice.value='';try{await fn();}catch(e){error.value=e.message;}finally{busy.value=false;}}
function canLeave(){return !(dirty.value||appointmentDirty.value)||window.confirm('Có thay đổi chưa lưu. Bỏ thay đổi để chuyển bản?');}
function beforeClose(e){if(dirty.value||appointmentDirty.value){e.preventDefault();e.returnValue='';}}
function authChanged(){window.dispatchEvent(new Event('recruitment-session-changed'));}
async function load(){conversations.value=(await api('conversations/',undefined,'GET',true)).items;await loadAppointments();}
async function login(){try{session.value=await api('session/',{username:username.value,password:password.value},'POST',true);}finally{password.value='';}await load();authChanged();}
async function logout(){if(!canLeave())return;session.value=await api('session/',{},'DELETE',true);conversations.value=[];revisions.value=[];summaries.value=[];summary.value=null;appointments.value=[];dirty.value=false;appointmentDirty.value=false;authChanged();}
async function openConversation(id){if(!canLeave())return;conversationId.value=id;revisions.value=(await api(`conversations/${id}/`,undefined,'GET',true)).revisions;await openRevision(revisions.value[0]?.id || '');}
async function openRevision(id){revisionId.value=id;summaries.value=id?(await api(`revisions/${id}/summaries/`)).items:[];setSummary(summaries.value[0]||null);await loadAppointments();}
function setSummary(value){summary.value=value;sections.value=value?structuredClone(toRaw(value.sections)):[];dirty.value=false;contentConfirmed.value=false;resetAppointment();}
async function chooseRevision(id){if(canLeave())await openRevision(id);}
async function chooseSummary(id){if(!canLeave())return;setSummary(summaries.value.find(s=>s.id===id));await loadAppointments();}
async function generate(){if(!canLeave())return;const value=await api(`revisions/${revisionId.value}/summaries/`,{});summaries.value.unshift(value);setSummary(value);await loadAppointments();}
async function copy(){if(!canLeave())return;const value=await api(`summaries/${summary.value.id}/copy/`,{});summaries.value.unshift(value);setSummary(value);await loadAppointments();}
function updateSummary(value){summary.value=value;summaries.value=summaries.value.map(s=>s.id===value.id?value:s);}
async function saveSummary(){const value=await api(`summaries/${summary.value.id}/`,{expected_version:summary.value.version,sections:sections.value},'PUT');updateSummary(value);dirty.value=false;notice.value='Đã lưu bản tóm tắt thủ công.';}
async function approve(){if(dirty.value)await saveSummary();updateSummary(await api(`summaries/${summary.value.id}/approve/`,{confirmed_content:contentConfirmed.value,expected_version:summary.value.version}));notice.value='Đã xác nhận nội dung tóm tắt; chưa có lịch nào được xác nhận tự động.';}
function quote(ids){return summary.value?.utterances.filter(t=>ids.includes(t.id)).map(t=>`${t.position}. ${t.role==='consultant'?'Tư vấn viên':t.role==='candidate'?'Ứng viên':'Chưa rõ'}: ${t.text}`).join('\n')||'';}
async function loadAppointments(){appointments.value=(await api(`appointments/${!allSchedules.value && summary.value ? '?summary_id='+summary.value.id : ''}`)).items;}
function resetAppointment(){selectedAppointment.value=null;form.value=emptyForm();requestKey=crypto.randomUUID();appointmentDirty.value=false;participantsConfirmed.value=false;}
function editAppointment(item){if(appointmentDirty.value&&!window.confirm('Bỏ lịch đang sửa?'))return;selectedAppointment.value=item;form.value={...item,starts_at:localTime(item.starts_at),ends_at:localTime(item.ends_at),evidence_ids:[...item.evidence_ids]};appointmentDirty.value=false;participantsConfirmed.value=false;}
async function saveAppointment(){const data={...form.value,starts_at:isoTime(form.value.starts_at),ends_at:isoTime(form.value.ends_at)};const value=selectedAppointment.value?await api(`appointments/${selectedAppointment.value.id}/`,{...data,expected_version:selectedAppointment.value.version},'PUT'):await api('appointments/',{...data,summary_id:summary.value.id,request_key:requestKey});selectedAppointment.value=value;appointmentDirty.value=false;await loadAppointments();notice.value='Đã lưu lịch nháp, chưa xác nhận và chưa gửi lời mời.';}
async function confirmAppointment(){if(appointmentDirty.value)await saveAppointment();selectedAppointment.value=await api(`appointments/${selectedAppointment.value.id}/confirm/`,{expected_version:selectedAppointment.value.version,confirmed_with_participants:participantsConfirmed.value});await loadAppointments();notice.value='Đã xác nhận lịch nội bộ. Chưa gửi email/SMS hoặc đồng bộ lịch ngoài.';}
async function cancel(item){if(!window.confirm(`Hủy lịch "${item.title}"?`))return;await api(`appointments/${item.id}/cancel/`,{});if(selectedAppointment.value?.id===item.id)resetAppointment();await loadAppointments();}
onMounted(()=>{window.addEventListener('beforeunload',beforeClose);action(async()=>{session.value=await api('session/',undefined,'GET',true);if(session.value.authenticated)await load();});});
onUnmounted(()=>window.removeEventListener('beforeunload',beforeClose));
</script>

<template>
  <section class="workspace followup" aria-label="Tóm tắt và lịch hẹn">
    <header><h2>Tóm tắt và lịch hẹn</h2><span v-if="session?.authenticated">{{session.username}}</span><button v-if="session?.authenticated" :disabled="busy" @click="action(logout)">Đăng xuất</button></header>
    <p v-if="error" class="alert" role="alert">{{error}}</p><p v-if="notice" class="notice" role="status">{{notice}}</p>
    <form v-if="session&&!session.authenticated" class="login" @submit.prevent="action(login)"><h3>Đăng nhập</h3><label>Tài khoản<input v-model="username" autocomplete="username" required /></label><label>Mật khẩu<input v-model="password" type="password" autocomplete="current-password" required /></label><button :disabled="busy" type="submit">Đăng nhập</button></form>
    <template v-if="session?.authenticated">
      <fieldset :disabled="busy" class="controls"><label>Hội thoại<select aria-label="Hội thoại" :value="conversationId" @change="action(()=>openConversation($event.target.value))"><option disabled value="">Chọn hội thoại đã lưu</option><option v-for="c in conversations" :key="c.id" :value="c.id">{{c.title}}</option></select></label><label v-if="revisions.length">Phiên bản transcript<select aria-label="Phiên bản transcript" :value="revisionId" @change="action(()=>chooseRevision($event.target.value))"><option v-for="r in revisions" :key="r.id" :value="r.id">Bản {{r.revision_number}} · {{r.transcript_reviewed?'Đã đối chiếu':'Chưa đối chiếu'}}</option></select></label><button v-if="revisionId" type="button" @click="action(generate)">Tạo tóm tắt trích dẫn</button></fieldset>
      <audio v-if="revision?.audio_url" :src="revision.audio_url" controls preload="metadata" aria-label="Nghe hội thoại nguồn" />
      <p v-if="revision&&!revision.transcript_reviewed" class="warning">Transcript chưa được nghe đối chiếu. Tóm tắt chỉ là bản nháp.</p>
      <label v-if="summaries.length">Bản tóm tắt<select aria-label="Bản tóm tắt" :value="summary?.id" :disabled="busy" @change="action(()=>chooseSummary($event.target.value))"><option v-for="s in summaries" :key="s.id" :value="s.id">{{sourceLabel(s.source)}} · {{statusLabel(s.status)}} · {{new Date(s.created_at).toLocaleString('vi-VN')}}</option></select></label>
      <section v-if="summary" class="summary-area">
        <div class="section-heading"><h3>{{sourceLabel(summary.source)}} · {{statusLabel(summary.status)}}</h3><button :disabled="busy" @click="action(copy)">Tạo bản sửa thủ công</button></div>
        <p v-if="summary.stale" class="warning">Transcript đã thay đổi. Bản này chỉ để đối chiếu lịch sử.</p>
        <p v-if="summary.reviewed_by">Đã duyệt bởi {{summary.reviewed_by}} · {{timeLabel(summary.reviewed_at)}}</p>
        <fieldset :disabled="busy||!editable" class="sections" @input="dirty=true;contentConfirmed=false" @change="dirty=true;contentConfirmed=false">
          <section v-for="section in sections" :key="section.code" class="summary-section"><h4>{{categories[section.code]}}</h4>
            <p v-if="!section.items.length" class="muted">Chưa có nội dung.</p>
            <article v-for="(item,i) in section.items" :key="i" class="summary-item">
              <textarea v-if="editable" v-model="item.text" :aria-label="`Nội dung ${section.code} ${i+1}`" rows="3" maxlength="10000" /><p v-else class="content">{{item.text}}</p>
              <label v-if="editable">Dẫn chứng<select v-model="item.utterance_ids" multiple :aria-label="`Dẫn chứng ${section.code} ${i+1}`"><option v-for="t in summary.utterances" :key="t.id" :value="t.id">{{t.position}} · {{t.role==='candidate'?'Ứng viên':t.role==='consultant'?'Tư vấn viên':'Chưa rõ'}} · {{t.text.slice(0,100)}}</option></select></label>
              <details><summary>Nguồn · {{item.utterance_ids.length}} lượt</summary><blockquote>{{quote(item.utterance_ids)}}</blockquote></details>
              <button v-if="editable" @click="section.items.splice(i,1);dirty=true">Xóa ý</button>
            </article>
            <button v-if="editable" @click="section.items.push({text:'',utterance_ids:[]});dirty=true">Thêm ý</button>
            <small v-if="summary.metadata.omitted_matches?.[section.code]">{{summary.metadata.omitted_matches[section.code]}} câu cùng nhóm không đưa vào bản trích chọn.</small>
          </section>
        </fieldset>
        <div class="actions"><button v-if="editable" :disabled="busy||!dirty" @click="action(saveSummary)">Lưu tóm tắt</button><label v-if="summary.status==='draft'" class="check"><input v-model="contentConfirmed" type="checkbox" />Đã đối chiếu nội dung với lời thoại</label><button v-if="summary.status==='draft'" :disabled="busy||!contentConfirmed||summary.stale" @click="action(approve)">Duyệt tóm tắt</button></div>
        <section class="appointment-form"><h3>{{selectedAppointment?'Lịch đang chọn':'Lịch hẹn nháp'}}</h3><fieldset :disabled="busy||selectedAppointment&&selectedAppointment.status!=='draft'" @input="appointmentDirty=true;participantsConfirmed=false" @change="appointmentDirty=true;participantsConfirmed=false">
          <div class="form-grid"><label>Tiêu đề<input v-model="form.title" maxlength="200" /></label><label>Ứng viên / người tham gia<input v-model="form.participant" maxlength="200" /></label><label>Người phụ trách<input v-model="form.responsible" maxlength="200" /></label><label>Hình thức<select v-model="form.channel"><option value="phone">Điện thoại</option><option value="online">Trực tuyến</option><option value="onsite">Trực tiếp</option></select></label><label>Bắt đầu · Giờ Việt Nam<input v-model="form.starts_at" type="datetime-local" /></label><label>Kết thúc · Giờ Việt Nam<input v-model="form.ends_at" type="datetime-local" /></label></div>
          <label>Địa điểm / kênh liên hệ<input v-model="form.location" maxlength="500" /></label>
          <details><summary>Lời thoại đối chiếu lịch · {{form.evidence_ids.length}} lượt</summary><label v-for="t in summary.utterances" :key="t.id" class="evidence"><input v-model="form.evidence_ids" type="checkbox" :value="t.id" /><span>{{t.position}} · {{t.role==='candidate'?'Ứng viên':t.role==='consultant'?'Tư vấn viên':'Chưa rõ'}}: {{t.text}}</span></label></details>
        </fieldset>
        <div class="actions"><button :disabled="busy||selectedAppointment&&selectedAppointment.status!=='draft'" @click="action(saveAppointment)">Lưu lịch nháp</button><button :disabled="busy" @click="()=>{if(canLeave())resetAppointment()}">Lịch mới</button></div>
        <div v-if="selectedAppointment?.status==='draft'" class="actions"><label class="check"><input v-model="participantsConfirmed" type="checkbox" />Đã thống nhất lịch với người tham gia</label><button :disabled="busy||!participantsConfirmed||summary.status!=='approved'||summary.stale" @click="action(confirmAppointment)">Xác nhận lịch</button></div>
        </section>
      </section>
      <section class="schedule-list"><div class="section-heading"><h3>Lịch hẹn nội bộ</h3><label class="check"><input v-model="allSchedules" type="checkbox" @change="action(loadAppointments)" />Tất cả hội thoại</label></div><p v-if="!appointments.length" class="muted">Chưa có lịch hẹn.</p>
        <article v-for="a in appointments" :key="a.id" class="schedule-item"><div class="section-heading"><h4>{{a.title}}</h4><strong>{{statusLabel(a.status)}}</strong></div><p>{{a.participant||'Chưa có người tham gia'}} · {{a.responsible||'Chưa có người phụ trách'}}</p><p>{{timeLabel(a.starts_at)}} → {{timeLabel(a.ends_at)}} · Giờ Việt Nam</p><p>{{a.location}}</p><div class="actions"><button v-if="summary?.id===a.summary_id" :disabled="busy" @click="editAppointment(a)">Mở lịch</button><button v-if="a.status!=='cancelled'" :disabled="busy" @click="action(()=>cancel(a))">Hủy lịch</button></div><details><summary>Lịch sử · {{a.events.length}}</summary><p v-for="(e,i) in a.events" :key="i">{{({created:'Tạo nháp',updated:'Sửa nháp',confirmed:'Xác nhận',cancelled:'Hủy'})[e.action]}} · {{e.actor}} · {{timeLabel(e.created_at)}}</p></details></article>
      </section>
    </template>
  </section>
</template>

<style scoped>
.followup{min-width:0;overflow-wrap:anywhere}header,.section-heading,.actions{display:flex;gap:12px;align-items:center;flex-wrap:wrap}header,.section-heading{justify-content:space-between}h2{font-size:24px}h3{font-size:18px}h4{font-size:16px}label{display:grid;gap:7px;color:#24343d;font-size:14px}input,select,textarea{width:100%;min-width:0;padding:10px;border:1px solid #b7c4cb;border-radius:4px;background:#fff;color:#17202a;font:inherit;box-sizing:border-box}textarea{resize:vertical}button{max-width:100%;font-size:14px;padding:10px 14px;white-space:normal}.controls,.form-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:14px}.controls{margin:18px 0;align-items:end}fieldset{border:0;padding:0;min-width:0}.sections{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:22px}.summary-area,.appointment-form,.schedule-list{margin-top:24px;border-top:1px solid #ccd6db;padding-top:16px}.summary-section,.summary-item,.schedule-item{border-bottom:1px solid #ccd6db;padding:12px 0}.summary-section h4{margin:0 0 10px}.content,blockquote{white-space:pre-wrap;line-height:1.6;margin:8px 0}blockquote{padding:10px 12px;border-left:3px solid #0c8069;background:#e8f3ef;font-size:14px}details summary{cursor:pointer;font-size:14px;padding:8px 0}.check,.evidence{display:flex;gap:8px;align-items:center}.check input,.evidence input{width:18px;height:18px;flex-shrink:0}.evidence{align-items:start;margin:12px 0;line-height:1.5}.actions{margin:14px 0}.form-grid{margin-bottom:14px}.notice{color:#08664e}.warning{padding:10px;border-left:3px solid #b77300;background:#fff1cb;color:#804700;font-size:14px}.muted,small{color:#53636a;font-size:14px}audio{width:100%;max-width:640px}.login{max-width:400px;display:grid;gap:14px}@media(max-width:850px){.controls,.sections,.form-grid{grid-template-columns:minmax(0,1fr)}}
</style>
