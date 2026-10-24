# Hợp đồng 010

## Django /api/candidate-info/

Dùng session/CSRF và quyền/phạm vi hội thoại của Spec 007. Lỗi JSON theo error.code/message, 401/403/404/409/422 và 503 khi matching lỗi.

- GET config/: fields (code/title/type/limit/choices), extraction_provider=rules, ner_model_available=false.
- GET/POST revisions/{uuid}/profiles/: GET items; POST {source:rules} tạo draft; hoặc {source:manual,fields,supersedes_id?} tạo bản riêng. Đủ mã trường, null nếu thiếu, evidence đúng substring/code point của lời ứng viên rõ vai/nghe rõ. Bản manual không có options/conflict chưa giải quyết.
- POST profiles/{uuid}/confirm/: {expected_version,confirmed_content:true}, chỉ tác giả/reviewer. Cần manual, nguồn mới nhất/đã kiểm tra, không xung đột. Trả confirmed, tăng version và khóa revision.
- GET/POST profiles/{uuid}/searches/: GET lịch sử; POST {top_k:3,strict_salary:false,confirmed_share:true} chỉ với manual confirmed, nguồn hiện hành. Gửi query nghề nghiệp tối thiểu tới URL server cấu hình, không nhận URL từ client. Kiểm lại snapshot/quyền sau network trước khi lưu.

Profile trả id/revision_id/utterances/fields/source/status/version/author_id/confirmed_by/at/supersedes_id/stale/created_at. Field: {code,value,evidence:[{utterance_id,start,end,quote}],options:[],conflict:false,note:""}. API không sửa bản đã lưu; tạo bản manual mới để sửa.

## Matching /api/v1/campaigns/search

POST body: {desired_job:string(1..500),experience:string|null,desired_location:string|null,region:north|central|south|null,expected_salary:int|null,strict_salary:bool=false,shift:string|null,top_k:int(1..10)=3}. Không chấp nhận extra fields, tên/điện thoại/transcript.

200: {model_version_id:string|null,model_name:string|null,eligible_campaigns:int,indexed_campaigns:int,recommendations:[{campaign_id:uuid,job_title,location,region,salary_min,salary_max,requirements,benefits,status:"active",semantic_score:float[-1,1],warnings:[string]}],message:string|null}. Chỉ active/nondeleted, đúng embedding ref/profile hash/model version. Thiếu vector đúng phiên bản trong nhóm đủ điều kiện: 409 CAMPAIGN_VECTORS_NOT_READY. DB/vector/model lỗi: 503; cấu hình version không khớp: 409; input: 422. Không ghi database hoặc rebuild vector trong request tìm.

Vùng được lọc cứng khi có region; NULL vùng chiến dịch không xem là đủ điều kiện. Khi strict_salary=true, cần expected_salary và salary_max chiến dịch đã biết >= kỳ vọng; NULL không được coi là đạt. Khi false, chỉ là thông tin tham khảo, không lọc lương. Ca làm/ngày bắt đầu luôn cần kiểm tra riêng.
