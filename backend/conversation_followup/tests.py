import uuid
from copy import deepcopy
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.exceptions import ValidationError
from django.test import Client, TestCase
from django.utils import timezone

from consultation_quality.models import AudioSample, Conversation, Revision
from .models import Appointment, AppointmentEvent, Summary
from .services import extract


class FollowupTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user("followup-owner")
        self.other = get_user_model().objects.create_user("followup-other")
        self.reviewer = get_user_model().objects.create_user("followup-reviewer", is_superuser=True)
        for u in [self.user, self.other]:
            u.user_permissions.add(Permission.objects.get(codename="annotate_quality"))
        self.client.force_login(self.user)
        self.conversation = Conversation.objects.create(title="Hội thoại tổng hợp kiểm thử", owner=self.user)
        self.turns = [
            {"id":"one","position":1,"role":"consultant","text":"Chào chị, vị trí lắp ráp có lương và phụ cấp theo ca.","start_seconds":None,"end_seconds":None},
            {"id":"two","position":2,"role":"candidate","text":"Chị muốn làm ca ngày gần nhà.","start_seconds":None,"end_seconds":None},
            {"id":"three","position":3,"role":"consultant","text":"Em hẹn gọi lại chị ngày mai để xác nhận công việc nhé?","start_seconds":None,"end_seconds":None},
            {"id":"four","position":4,"role":"candidate","text":"Vâng, em gọi lại lúc sáng cho chị.","start_seconds":None,"end_seconds":None},
        ]
        self.revision = Revision.objects.create(conversation=self.conversation, utterances=self.turns, roles_confirmed=True, transcript_reviewed=True)

    def post(self, path, data, status=201):
        r = self.client.post("/api/followup/"+path,data,content_type="application/json")
        self.assertEqual(r.status_code,status,r.content)
        return r.json()

    def summary(self, approved=False):
        value = self.post(f"revisions/{self.revision.pk}/summaries/",{})
        if approved:
            value = self.post(f"summaries/{value['id']}/approve/",{"confirmed_content":True,"expected_version":value["version"]},200)
        return value

    def appointment_data(self, summary):
        start=timezone.now()+timedelta(days=2)
        return {"summary_id":summary["id"],"request_key":str(uuid.uuid4()),"title":"Gọi lại xác nhận", "participant":"Ứng viên kiểm thử", "responsible":"Tư vấn kiểm thử", "channel":"phone", "location":"Kênh điện thoại đã xác nhận", "starts_at":start.isoformat(),"ends_at":(start+timedelta(minutes=30)).isoformat(),"evidence_ids":["three","four"]}

    def test_extractive_summary_has_only_original_quotes_and_does_not_schedule(self):
        value=self.summary()
        quotes={t["id"]:t["text"] for t in self.turns}
        for section in value["sections"]:
            for item in section["items"]:
                self.assertEqual(item["text"],quotes[item["utterance_ids"][0]])
        self.assertEqual(value["source"],"extractive_rules")
        self.assertEqual(value["status"],"draft")
        self.assertFalse(Appointment.objects.exists())

    def test_unreviewed_transcript_can_preview_but_not_approve(self):
        Revision.objects.filter(pk=self.revision.pk).update(transcript_reviewed=False)
        value=self.summary()
        self.post(f"summaries/{value['id']}/approve/",{"confirmed_content":True,"expected_version":1},422)

    def test_negative_appointment_sentence_is_quoted_not_an_agreement(self):
        self.revision.utterances[3]["text"]="Chị không đồng ý phỏng vấn ngày mai."
        self.revision.save()
        value=self.summary()
        self.assertFalse(value["metadata"]["automatic_appointment"])
        self.assertFalse(Appointment.objects.exists())

    def test_manual_copy_edit_stale_version_and_foreign_evidence(self):
        original=self.summary()
        copied=self.post(f"summaries/{original['id']}/copy/",{})
        sections=deepcopy(copied["sections"])
        sections[0]["items"][0]["text"]="Bản ghi có trao đổi về công việc."
        path=f"/api/followup/summaries/{copied['id']}/"
        body={"expected_version":copied["version"],"sections":sections}
        self.assertEqual(self.client.put(path,body,content_type="application/json").status_code,200)
        self.assertEqual(self.client.put(path,body,content_type="application/json").status_code,409)
        sections[0]["items"][0]["utterance_ids"]=["foreign"]
        self.assertEqual(self.client.put(path,{"expected_version":2,"sections":sections},content_type="application/json").status_code,422)
        self.assertEqual(Summary.objects.get(pk=original["id"]).sections,original["sections"])

    def test_approved_summary_is_immutable_and_seals_revision(self):
        value=self.summary(approved=True)
        self.revision.refresh_from_db()
        self.assertEqual(self.revision.status,"sealed")
        obj=Summary.objects.get(pk=value["id"])
        obj.sections=[]
        with self.assertRaises(ValidationError):obj.save()
        self.assertEqual(self.client.put(f"/api/followup/summaries/{value['id']}/",{},content_type="application/json").status_code,409)

    def test_revised_transcript_requires_new_summary(self):
        value=self.summary()
        Revision.objects.create(conversation=self.conversation,utterances=self.turns,roles_confirmed=True,transcript_reviewed=True)
        self.post(f"summaries/{value['id']}/approve/",{"confirmed_content":True,"expected_version":1},409)
        self.assertTrue(self.client.get(f"/api/followup/summaries/{value['id']}/").json()["stale"])

    def test_in_place_draft_changes_mark_summary_stale(self):
        value=self.summary()
        self.revision.utterances[0]["text"]="Nội dung mới"
        self.revision.save()
        self.post(f"summaries/{value['id']}/approve/",{"confirmed_content":True,"expected_version":1},409)

    def test_confirmation_requires_approved_summary_human_consent_and_both_roles(self):
        summary=self.summary()
        data=self.appointment_data(summary)
        appointment=self.post("appointments/",data)
        path=f"appointments/{appointment['id']}/confirm/"
        self.post(path,{"expected_version":1},422)
        self.post(path,{"expected_version":1,"confirmed_with_participants":True},422)
        self.post(f"summaries/{summary['id']}/approve/",{"expected_version":1,"confirmed_content":True},200)
        Appointment.objects.filter(pk=appointment["id"]).update(evidence_ids=["three"])
        self.post(path,{"expected_version":1,"confirmed_with_participants":True},422)

    def test_confirm_cancel_and_idempotent_audit(self):
        summary=self.summary(approved=True)
        data=self.appointment_data(summary)
        value=self.post("appointments/",data)
        self.assertEqual(self.post("appointments/",data,200)["id"],value["id"])
        payload={"expected_version":value["version"],"confirmed_with_participants":True}
        confirmed=self.post(f"appointments/{value['id']}/confirm/",payload,200)
        self.assertEqual(confirmed["status"],"confirmed")
        self.post(f"appointments/{value['id']}/confirm/",payload,200)
        self.assertEqual(AppointmentEvent.objects.count(),2)
        cancelled=self.post(f"appointments/{value['id']}/cancel/",{},200)
        self.assertEqual(cancelled["status"],"cancelled")
        self.post(f"appointments/{value['id']}/cancel/",{},200)
        self.assertEqual(AppointmentEvent.objects.count(),3)
        self.post(f"appointments/{value['id']}/confirm/",{"confirmed_with_participants":True,"expected_version":cancelled["version"]},409)

    def test_timezone_duration_past_time_and_duplicate_key_conflicts(self):
        summary=self.summary(approved=True)
        data=self.appointment_data(summary)
        for bad in [{"starts_at":"2026-10-20T09:00:00","ends_at":"2026-10-20T10:00:00"},{"starts_at":False,"ends_at":False},{"evidence_ids":["foreign"]}]:
            self.post("appointments/",dict(data,**bad),422)
        past=timezone.now()-timedelta(days=2)
        old=self.post("appointments/",dict(data,starts_at=past.isoformat(),ends_at=(past+timedelta(minutes=30)).isoformat()))
        self.post(f"appointments/{old['id']}/confirm/",{"expected_version":1,"confirmed_with_participants":True},422)
        self.post("appointments/",dict(data,title="Changed content"),409)

    def test_overlap_conflicts_and_cancel_releases_slot(self):
        summary=self.summary(approved=True)
        data=self.appointment_data(summary)
        first=self.post("appointments/",data)
        self.post(f"appointments/{first['id']}/confirm/",{"expected_version":1,"confirmed_with_participants":True},200)
        second=self.post("appointments/",dict(data,request_key=str(uuid.uuid4())))
        self.post(f"appointments/{second['id']}/confirm/",{"expected_version":1,"confirmed_with_participants":True},409)
        self.post(f"appointments/{first['id']}/cancel/",{},200)
        self.post(f"appointments/{second['id']}/confirm/",{"expected_version":1,"confirmed_with_participants":True},200)

    def test_draft_update_and_no_edit_after_confirmation(self):
        summary=self.summary(approved=True)
        data=self.appointment_data(summary)
        value=self.post("appointments/",data)
        path=f"/api/followup/appointments/{value['id']}/"
        response=self.client.put(path,dict(data,title="Tiêu đề đã sửa",expected_version=1),content_type="application/json")
        self.assertEqual(response.status_code,200)
        self.assertEqual(self.client.put(path,dict(data,expected_version=1),content_type="application/json").status_code,409)
        self.post(f"appointments/{value['id']}/confirm/",{"expected_version":2,"confirmed_with_participants":True},200)
        self.assertEqual(self.client.put(path,dict(data,expected_version=3),content_type="application/json").status_code,409)

    def test_permissions_authentication_and_shared_read_without_edit(self):
        summary=self.summary()
        appointment=self.post("appointments/",self.appointment_data(summary))
        self.client.logout()
        self.assertEqual(self.client.get("/api/followup/appointments/").status_code,401)
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(f"/api/followup/summaries/{summary['id']}/").status_code,404)
        self.conversation.members.add(self.other)
        self.assertEqual(self.client.get(f"/api/followup/summaries/{summary['id']}/").status_code,200)
        self.post(f"summaries/{summary['id']}/approve/",{"confirmed_content":True,"expected_version":1},403)
        self.post(f"appointments/{appointment['id']}/cancel/",{},403)

    def test_csrf_is_required(self):
        client=Client(enforce_csrf_checks=True)
        client.force_login(self.user)
        response=client.post(f"/api/followup/revisions/{self.revision.pk}/summaries/",{},content_type="application/json")
        self.assertEqual(response.status_code,403)

    def test_extraction_keeps_tail_matches_without_invented_date(self):
        turns=[dict(self.turns[0],id=str(i),position=i+1,text=f"Công việc đoạn {i}") for i in range(10)]
        turns[-1]["text"]="Hẹn gọi lại vào ngày mai."
        sections,meta=extract(turns)
        self.assertIn("Hẹn gọi lại vào ngày mai.",[i["text"] for s in sections for i in s["items"]])
        self.assertGreater(meta["omitted_matches"]["job"],0)
        self.assertFalse(meta["automatic_appointment"])
