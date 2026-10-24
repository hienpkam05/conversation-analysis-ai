<script setup>
import { computed, onMounted, onUnmounted, ref, toRaw } from "vue";

const session = ref(null), username = ref(""), password = ref(""), busy = ref(false), error = ref(""), notice = ref("");
const config = ref(null), conversations = ref([]), conversationId = ref(""), revisions = ref([]), revisionId = ref("");
const profiles = ref([]), profile = ref(null), fields = ref([]), editing = ref(false), dirty = ref(false), contentConfirmed = ref(false);
const searches = ref([]), selectedSearch = ref(null), topK = ref(3), strictSalary = ref(false), shareConfirmed = ref(false);
const revision = computed(() => revisions.value.find(row => row.id === revisionId.value));
const turns = computed(() => profile.value?.utterances || revision.value?.utterances || []);
const specs = computed(() => config.value?.fields || []);
const spec = code => specs.value.find(item => item.code === code);
const conflicts = computed(() => fields.value.some(f => f.conflict));
const statusLabel = status => status === "confirmed" ? "Đã xác nhận" : "Bản nháp";
const sourceLabel = source => source === "manual" ? "Thủ công" : "Quy tắc";
const time = value => new Date(value).toLocaleString("vi-VN", { timeZone: "Asia/Ho_Chi_Minh" });
const currency = value => value == null ? "Chưa có" : new Intl.NumberFormat("vi-VN").format(value) + " VND";
const regionLabel = value => ({north:"Miền Bắc",central:"Miền Trung",south:"Miền Nam"})[value] || "Chưa có";
const canConfirm = computed(() => profile.value?.source === "manual" && profile.value.status === "draft" && !profile.value.stale && !editing.value && (profile.value.author_id === session.value?.user_id || session.value?.can_review));

async function api(path, data, method = "POST", quality = false) {
  let response;
  try { response = await fetch(`/api/${quality ? "quality" : "candidate-info"}/${path}`, data === undefined ? {} : {method,headers:{"Content-Type":"application/json","X-CSRFToken":session.value?.csrf_token || ""},body:JSON.stringify(data)}); }
  catch { throw new Error("Không kết nối được Django. Kiểm tra backend và proxy /api."); }
  let payload;
  try { payload = await response.json(); } catch { throw new Error("API chưa sẵn sàng hoặc trả dữ liệu không hợp lệ."); }
  if (!response.ok) {
    if(response.status===401&&session.value?.authenticated){session.value={authenticated:false};clearPrivate();authChanged();}
    throw new Error(payload.error?.message || "Không thực hiện được yêu cầu.");
  }
  return payload;
}
async function action(fn) { if(busy.value)return;busy.value=true;error.value="";notice.value="";try{await fn();}catch(e){error.value=e.message;}finally{busy.value=false;} }
function authChanged(){window.dispatchEvent(new Event("recruitment-session-changed"));}
function canLeave(){return !dirty.value || window.confirm("Bỏ các thay đổi chưa lưu?");}
function beforeClose(e){if(dirty.value){e.preventDefault();e.returnValue="";}}
async function load(){config.value=await api("config/");const items=[];let offset=0;while(true){const page=await api(`conversations/?offset=${offset}&limit=100`,undefined,"GET",true);items.push(...page.items);offset+=page.items.length;if(!page.items.length||offset>=page.count)break;}conversations.value=items;}
async function login(){try{session.value=await api("session/",{username:username.value,password:password.value},"POST",true);}finally{password.value="";}authChanged();await load();}
function clearPrivate(){conversations.value=[];conversationId.value="";revisions.value=[];revisionId.value="";profiles.value=[];choose(null);dirty.value=false;}
async function logout(){if(!canLeave())return;session.value=await api("session/",{},"DELETE",true);clearPrivate();authChanged();}
function choose(value){profile.value=value;fields.value=value?structuredClone(toRaw(value.fields)):specs.value.map(f=>({code:f.code,value:null,evidence:[],options:[],conflict:false,note:""}));editing.value=false;dirty.value=false;contentConfirmed.value=false;shareConfirmed.value=false;searches.value=[];selectedSearch.value=null;}
async function openConversation(id){if(!canLeave())return;conversationId.value=id;revisionId.value="";revisions.value=[];profiles.value=[];choose(null);if(!id)return;revisions.value=(await api(`conversations/${id}/`,undefined,"GET",true)).revisions;await openRevision(revisions.value[0]?.id || "");}
async function openRevision(id){revisionId.value=id;profiles.value=[];choose(null);if(id){profiles.value=(await api(`revisions/${id}/profiles/`)).items;choose(profiles.value[0] || null);await loadSearches();}}
async function chooseRevision(id){if(canLeave())await openRevision(id);}
async function chooseProfile(id){if(!canLeave())return;choose(profiles.value.find(row=>row.id===id));await loadSearches();}
async function generate(){if(!canLeave())return;const row=await api(`revisions/${revisionId.value}/profiles/`,{source:"rules"});profiles.value.unshift(row);choose(row);}
function manual(){if(profile.value?.stale){error.value="Chọn transcript hiện hành để tạo bản sửa.";return;}editing.value=true;dirty.value=false;contentConfirmed.value=false;selectedSearch.value=null;}
async function cancelManual(){if(!canLeave())return;choose(profile.value);await loadSearches();}
function resolve(field, option){field.value=option.value;field.evidence=structuredClone(toRaw(option.evidence));field.options=[];field.conflict=false;dirty.value=true;}
function clearField(field){field.value=null;field.evidence=[];field.options=[];field.conflict=false;dirty.value=true;}
function setEvidence(field,event){const ids=Array.from(event.target.selectedOptions).map(option=>option.value);field.evidence=turns.value.filter(t=>ids.includes(t.id)).map(t=>({utterance_id:t.id,start:0,end:Array.from(t.text).length,quote:t.text}));dirty.value=true;}
async function save(){const row=await api(`revisions/${revisionId.value}/profiles/`,{source:"manual",fields:fields.value,supersedes_id:profile.value?.id || null});profiles.value.unshift(row);choose(row);notice.value="Đã lưu bản thông tin thủ công riêng. Chưa tạo hồ sơ PostgreSQL.";}
async function confirm(){const row=await api(`profiles/${profile.value.id}/confirm/`,{expected_version:profile.value.version,confirmed_content:contentConfirmed.value});profiles.value=profiles.value.map(p=>p.id===row.id?row:p);choose(row);notice.value="Đã xác nhận bản thông tin, chưa gửi tìm kiếm hoặc gán chiến dịch.";}
async function loadSearches(){searches.value=profile.value?(await api(`profiles/${profile.value.id}/searches/`)).items:[];selectedSearch.value=searches.value[0] || null;}
async function search(){selectedSearch.value=null;const row=await api(`profiles/${profile.value.id}/searches/`,{top_k:topK.value,strict_salary:strictSalary.value,confirmed_share:shareConfirmed.value});searches.value.unshift(row);selectedSearch.value=row;notice.value="Đã lưu kết quả gợi ý. Chưa gán ứng viên vào chiến dịch.";}
onMounted(()=>{window.addEventListener("beforeunload",beforeClose);action(async()=>{session.value=await api("session/",undefined,"GET",true);if(session.value.authenticated)await load();});});
onUnmounted(()=>window.removeEventListener("beforeunload",beforeClose));
</script>

<template>
  <section class="workspace candidate-info" aria-label="Thông tin và chiến dịch">
    <header class="info-header"><h2>Thông tin &amp; chiến dịch</h2><span v-if="session?.authenticated">{{session.username}}</span><button v-if="session?.authenticated" :disabled="busy" @click="action(logout)">Đăng xuất</button></header>
    <p v-if="error" role="alert" class="alert">{{error}}</p><p v-if="notice" role="status" class="notice">{{notice}}</p>
    <form v-if="session&&!session.authenticated" class="login" @submit.prevent="action(login)"><h3>Đăng nhập thông tin ứng viên</h3><label>Tài khoản<input v-model="username" autocomplete="username" required /></label><label>Mật khẩu<input v-model="password" type="password" autocomplete="current-password" required /></label><button :disabled="busy" type="submit">Đăng nhập</button></form>
    <template v-if="session?.authenticated">
      <p class="muted">Trích xuất theo quy tắc · Chưa có PhoBERT NER đã huấn luyện</p>
      <p v-if="!busy&&!conversations.length" class="muted">Chưa có hội thoại trong phạm vi được cấp quyền.</p>
      <fieldset :disabled="busy" class="context-grid"><label>Hội thoại<select aria-label="Hội thoại thông tin" :value="conversationId" @change="action(()=>openConversation($event.target.value))"><option disabled value="">Chọn hội thoại</option><option v-for="c in conversations" :key="c.id" :value="c.id">{{c.title}}</option></select></label><label v-if="revisions.length">Phiên bản transcript<select aria-label="Phiên bản thông tin" :value="revisionId" @change="action(()=>chooseRevision($event.target.value))"><option v-for="r in revisions" :key="r.id" :value="r.id">Bản {{r.revision_number}} · {{r.transcript_reviewed&&r.roles_confirmed?'Đã đối chiếu':'Chưa đối chiếu'}}</option></select></label></fieldset>
      <template v-if="revision">
        <audio v-if="revision.audio_url" :src="revision.audio_url" controls preload="metadata" aria-label="Audio nguồn thông tin" />
        <p v-if="!revision.transcript_reviewed||!revision.roles_confirmed" class="warning">Transcript hoặc vai người nói chưa được xác nhận. Kết quả chỉ là bản nháp.</p>
        <div class="actions"><button :disabled="busy" @click="action(generate)">Trích xuất thông tin</button><button :disabled="busy||editing||profile?.stale" class="secondary-button" @click="manual">{{profile?'Tạo bản sửa thủ công':'Nhập thông tin thủ công'}}</button></div>
        <label v-if="profiles.length">Lịch sử thông tin<select aria-label="Lịch sử thông tin" :value="profile?.id" :disabled="busy" @change="action(()=>chooseProfile($event.target.value))"><option v-for="p in profiles" :key="p.id" :value="p.id">{{sourceLabel(p.source)}} · {{statusLabel(p.status)}} · {{time(p.created_at)}}</option></select></label>
        <p v-if="profile?.stale" class="warning">Transcript đã đổi. Bản này chỉ để xem lịch sử, chưa thể gửi tìm kiếm.</p>
        <div v-if="profile||editing" class="info-layout">
          <section class="fields-area"><h3>{{editing?'Bản sửa mới':`${sourceLabel(profile.source)} · ${statusLabel(profile.status)}`}}</h3>
            <fieldset :disabled="busy||!editing" @input="dirty=true;contentConfirmed=false" @change="dirty=true;contentConfirmed=false">
              <section v-for="field in fields" :key="field.code" class="info-field">
                <label :for="`info-${field.code}`">{{spec(field.code)?.title}}</label>
                <select v-if="spec(field.code)?.type==='choice'" :id="`info-${field.code}`" v-model="field.value"><option :value="null">Chưa có thông tin</option><option v-for="(title,value) in spec(field.code).choices" :key="value" :value="value">{{title}}</option></select>
                <input v-else-if="spec(field.code)?.type==='number'" :id="`info-${field.code}`" v-model.number="field.value" type="number" min="1" max="1000000000" step="100000" />
                <input v-else :id="`info-${field.code}`" v-model="field.value" :maxlength="spec(field.code)?.limit" :type="field.code==='phone'?'tel':'text'" />
                <div v-if="field.conflict" class="warning"><strong>Cần chọn lại giá trị</strong><div v-for="(option,i) in field.options" :key="i" class="conflict-option"><span>{{spec(field.code)?.choices?.[option.value]||option.value}}</span><button v-if="editing" type="button" @click="resolve(field,option)">Chọn giá trị này</button></div></div>
                <label v-if="editing">Lời ứng viên làm căn cứ<select multiple :aria-label="`Dẫn chứng ${field.code}`" @change="setEvidence(field,$event)"><option v-for="t in turns.filter(t=>t.role==='candidate'&&!t.unclear)" :key="t.id" :value="t.id" :selected="field.evidence.some(e=>e.utterance_id===t.id)">{{t.position}} · {{t.text.slice(0,100)}}</option></select></label>
                <details v-if="field.evidence.length"><summary>Nguồn · {{field.evidence.length}} đoạn</summary><blockquote v-for="(e,i) in field.evidence" :key="i">{{e.quote}}</blockquote></details>
                <label v-if="editing">Ghi chú<input v-model="field.note" :aria-label="`Ghi chú ${field.code}`" maxlength="2000" /></label><button v-if="editing" class="secondary-button" type="button" @click="clearField(field)">Để trống trường</button>
              </section>
            </fieldset>
            <div v-if="editing" class="actions"><button :disabled="busy||conflicts" @click="action(save)">Lưu bản thông tin</button><button class="secondary-button" :disabled="busy" @click="action(cancelManual)">Bỏ sửa</button></div>
            <div v-if="canConfirm" class="confirm"><label class="check"><input v-model="contentConfirmed" type="checkbox" />Đã đối chiếu thông tin và dẫn chứng với hội thoại</label><button :disabled="busy||!contentConfirmed||!revision.roles_confirmed||!revision.transcript_reviewed" @click="action(confirm)">Xác nhận thông tin</button></div>
            <p v-if="profile?.confirmed_by" class="muted">{{profile.confirmed_by}} xác nhận · {{time(profile.confirmed_at)}}</p>
          </section>
          <section class="source-area"><h3>Hội thoại nguồn</h3><ol><li v-for="t in turns" :key="t.id"><small>{{t.position}} · {{t.role==='candidate'?'Ứng viên':t.role==='consultant'?'Tư vấn viên':'Chưa rõ'}}{{t.unclear?' · Khó nghe':''}}</small><p>{{t.text}}</p></li></ol></section>
        </div>
        <section v-if="profile" class="campaign-area"><h3>Chiến dịch gợi ý</h3>
          <fieldset :disabled="busy||editing||profile.status!=='confirmed'||profile.stale" class="search-controls"><label>Số kết quả<input v-model.number="topK" type="number" min="1" max="10" step="1" /></label><label class="check"><input v-model="strictSalary" type="checkbox" />Lọc cứng theo mức lương mong muốn</label><label class="check"><input v-model="shareConfirmed" type="checkbox" />Đồng ý gửi thông tin nghề nghiệp để tìm chiến dịch</label><button :disabled="!shareConfirmed" @click="action(search)">{{busy?'Đang tìm...':'Tìm chiến dịch phù hợp'}}</button></fieldset>
          <p class="muted">Không gửi các trường tên, điện thoại, nơi ở hoặc toàn transcript. Nội dung nghề nghiệp vẫn cần kiểm tra riêng tư. Ca làm/ngày bắt đầu cần đối chiếu riêng.</p>
          <label v-if="searches.length">Lịch sử tìm kiếm<select aria-label="Lịch sử chiến dịch" :value="selectedSearch?.id" @change="selectedSearch=searches.find(s=>s.id===$event.target.value)"><option v-for="s in searches" :key="s.id" :value="s.id">{{time(s.created_at)}} · {{s.result.recommendations.length}} kết quả</option></select></label>
          <template v-if="selectedSearch"><p class="muted">{{selectedSearch.result.eligible_campaigns}} chiến dịch đủ bộ lọc · {{selectedSearch.result.indexed_campaigns}} có vector hiện hành · {{selectedSearch.result.model_name||'Chưa dùng model'}} · {{time(selectedSearch.created_at)}}</p><p v-if="selectedSearch.result.message" class="warning">{{selectedSearch.result.message}}</p><p v-if="!selectedSearch.result.recommendations.length">Chưa có chiến dịch phù hợp với bộ lọc.</p>
            <article v-for="(item,i) in selectedSearch.result.recommendations" :key="item.campaign_id" class="campaign-result"><header><h4>{{i+1}}. {{item.job_title}}</h4><span>Cosine {{item.semantic_score.toFixed(3)}}</span></header><p>{{item.location||'Chưa có địa điểm'}} · {{regionLabel(item.region)}}</p><p>Lương: {{currency(item.salary_min)}} – {{currency(item.salary_max)}}</p><p v-if="item.requirements">{{item.requirements}}</p><p v-if="item.benefits">{{item.benefits}}</p><ul><li v-for="warning in item.warnings" :key="warning">{{warning}}</li></ul></article>
          </template>
        </section>
      </template>
    </template>
  </section>
</template>

<style scoped>
.candidate-info { min-width: 0; } h2,h3,h4 { margin: 0; } h2 { font-size: 24px; } h3 { font-size: 18px; } h4 { font-size: 16px; }
.info-header,.actions,.campaign-result header { display:flex;align-items:center;gap:12px;flex-wrap:wrap; }.info-header { justify-content:space-between;margin-bottom:20px; }.actions { margin:18px 0; }
label { display:grid;gap:8px;min-width:0;color:#182e3c;font-size:14px;font-weight:600; }
input:not([type=checkbox]),select { width:100%;min-width:0;box-sizing:border-box;border:1px solid #b9c9d3;border-radius:4px;padding:11px;background:white;color:#182e3c;font:inherit; } select { text-overflow:ellipsis; }
input[type=checkbox] { width:18px;height:18px;flex:0 0 18px;accent-color:#0b806c; }.check { display:flex;align-items:center;gap:8px;line-height:1.6; }
fieldset { border:0;padding:0;margin:0;min-width:0; }.login { display:grid;gap:18px;max-width:420px; }.context-grid { display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:16px; }
audio { width:100%;display:block;margin:16px 0; }.muted,small { color:#526879;font-size:13px;line-height:1.6; }.notice { color:#086346;background:#e0f1e9;border:1px solid #9ccfb8;padding:14px;border-radius:4px; }.warning { color:#714e10;background:#fff5d8;padding:12px;border-left:3px solid #b8871a; }
.info-layout { display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:28px;margin-top:24px; }.fields-area,.source-area,.campaign-area { min-width:0;border-top:1px solid #cbd7df;padding-top:20px; }.info-field { display:grid;gap:10px;padding:18px 0;border-bottom:1px solid #cbd7df; }
.conflict-option { display:flex;gap:8px;align-items:center;justify-content:space-between;margin-top:10px;flex-wrap:wrap; } blockquote { margin:10px 0;padding-left:12px;border-left:3px solid #0b806c;white-space:pre-wrap;overflow-wrap:anywhere;line-height:1.7; }
.source-area ol { list-style:none;margin:16px 0 0;padding:0; }.source-area li { padding:14px 0;border-bottom:1px solid #cbd7df; }.source-area p { margin:8px 0;line-height:1.7;white-space:pre-wrap;overflow-wrap:anywhere; }
.confirm { display:grid;gap:12px;margin:20px 0; }.campaign-area { margin-top:28px; }.search-controls { display:flex;align-items:end;gap:16px;flex-wrap:wrap;margin-top:20px; }.search-controls>label:first-child { width:110px; }.campaign-result { padding:20px 0;border-bottom:1px solid #cbd7df; }.campaign-result header { justify-content:space-between; }.campaign-result p { margin:12px 0;line-height:1.6;overflow-wrap:anywhere; }.campaign-result ul { padding-left:20px;font-size:13px;color:#526879;line-height:1.7; } button { min-height:42px; }
@media(max-width:900px) { .info-layout,.context-grid { grid-template-columns:minmax(0,1fr); } }
</style>
