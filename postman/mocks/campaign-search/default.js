// Contract fixture only. This is not a real campaign database or embedding model.
const http = require("http");
let mode = "ok";
const campaignId = "00000000-0000-4000-8000-000000000010";
const modelId = "00000000-0000-4000-8000-000000000011";
const send = (res, status, body) => { res.writeHead(status, { "Content-Type": "application/json" }); res.end(JSON.stringify(body)); };
http.createServer(async (req, res) => {
  const path = new URL(req.url, "http://localhost").pathname;
  let raw = "";
  for await (const chunk of req) { raw += chunk; if (raw.length > 10000) { send(res, 413, {}); return; } }
  let body;
  try { body = raw ? JSON.parse(raw) : {}; } catch { send(res, 422, {detail:{code:"INVALID_INPUT",message:"JSON required"}}); return; }
  // Local test runner changes fault mode here; application code never calls this route.
  if (req.method === "PUT" && path === "/__test_mode") {
    if (!["ok", "unavailable", "html"].includes(body.mode)) { send(res, 422, {}); return; }
    mode = body.mode; send(res, 200, {mode}); return;
  }
  if (req.method !== "POST" || path !== "/api/v1/campaigns/search") { send(res, 501, {error:"Endpoint not defined by this contract fixture"}); return; }
  const allowed = ["desired_job", "experience", "desired_location", "region", "expected_salary", "strict_salary", "shift", "top_k"];
  if (Object.keys(body).some(key => !allowed.includes(key)) || typeof body.desired_job !== "string" || !body.desired_job.trim() || !Number.isInteger(body.top_k) || body.top_k < 1 || body.top_k > 10) {
    send(res, 422, {detail:{code:"INVALID_INPUT",message:"Query does not match campaign-search contract"}}); return;
  }
  if (mode === "unavailable") { send(res, 503, {detail:{code:"CAMPAIGN_SEARCH_UNAVAILABLE",message:"Model/vector/database unavailable (fixture)"}}); return; }
  if (mode === "html") { res.writeHead(200, {"Content-Type":"text/html"}); res.end("<html>Upstream proxy error fixture</html>"); return; }
  const rows = body.region && body.region !== "north" || body.strict_salary && body.expected_salary > 12000000 ? [] : [{
    campaign_id:campaignId, job_title:"Chiến dịch kiểm thử lắp ráp", location:"Hà Nội", region:"north", salary_min:8000000, salary_max:12000000,
    requirements:"Dữ liệu fixture kiểm thử hợp đồng API", benefits:"Không phải chiến dịch thật", status:"active", semantic_score:0.8,
    warnings:["Ca làm và ngày bắt đầu cần đối chiếu; đây là dữ liệu kiểm thử."]
  }];
  send(res, 200, {model_version_id:rows.length?modelId:null,model_name:rows.length?"fixture-contract-not-real-model":null,eligible_campaigns:rows.length,indexed_campaigns:rows.length,recommendations:rows,message:rows.length?null:"Không có chiến dịch đủ bộ lọc (fixture)."});
}).listen(process.env.PORT || 4930, "127.0.0.1");
