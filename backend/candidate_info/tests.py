from copy import deepcopy
from unittest.mock import patch
import uuid
import requests

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.exceptions import ValidationError
from django.test import Client, TestCase

from consultation_quality.models import AudioSample, Conversation, Revision
from .models import CandidateProfile, CampaignSearch
from .services import extract, validate_fields
from .matching import MatchingUnavailable, make_query, validate_result, search


def turn(text, key="one", role="candidate", **extra):
    return {"id":key,"position":1,"role":role,"text":text,"start_seconds":None,"end_seconds":None,**extra}


def matching_result():
    return {"model_version_id":str(uuid.uuid4()),"model_name":"fixture-embedding-not-real","eligible_campaigns":1,"indexed_campaigns":1,"message":None,
        "recommendations":[{"campaign_id":str(uuid.uuid4()),"job_title":"Công nhân điện tử","location":"Hà Nội","region":"north","salary_min":8000000,"salary_max":12000000,
            "requirements":"Kinh nghiệm lắp ráp","benefits":"Ăn ca","status":"active","semantic_score":.8,"warnings":["Ca làm cần đối chiếu."]}]}


class ExtractionTests(TestCase):
    def test_only_candidate_explicit_facts_have_exact_spans(self):
        turns=[turn("Tôi tên là Nhân Viên. Tôi muốn lương 30 triệu/tháng.","consultant","consultant"),
            turn("Tôi tên là Nguyễn Văn An.","name"),turn("Số điện thoại của tôi là 0987654321.","phone"),
            turn("Tôi đang ở Bắc Ninh.","home"),turn("Tôi muốn làm ở Hà Nội.","place"),turn("Tôi muốn làm lắp ráp.","job"),
            turn("Tôi đã từng làm lắp ráp điện tử.","exp"),turn("Tôi muốn ca ngày.","shift"),
            turn("Tôi mong muốn mức lương 10,5 triệu/tháng.","salary"),turn("Tôi có thể đi làm tuần sau.","date")]
        fields={f["code"]:f for f in extract(turns)}
        self.assertEqual(fields["full_name"]["value"],"Nguyễn Văn An")
        self.assertEqual(fields["phone"]["value"],"0987654321")
        self.assertEqual(fields["residence"]["value"],"Bắc Ninh")
        self.assertEqual(fields["desired_location"]["value"],"Hà Nội")
        self.assertEqual(fields["desired_job"]["value"],"lắp ráp")
        self.assertEqual(fields["expected_salary"]["value"],10500000)
        self.assertEqual(fields["availability"]["value"],"tuần sau")
        self.assertIsNone(fields["region"]["value"])
        by_id={t["id"]:t for t in turns}
        for field in fields.values():
            for e in field["evidence"]:
                self.assertEqual(e["quote"],by_id[e["utterance_id"]]["text"][e["start"]:e["end"]])

    def test_conflicting_values_do_not_choose_last(self):
        fields={f["code"]:f for f in extract([turn("Số điện thoại của tôi là 0987654321.","a"),turn("Số điện thoại của tôi là 0912345678.","b")])}
        self.assertTrue(fields["phone"]["conflict"])
        self.assertIsNone(fields["phone"]["value"])
        self.assertEqual(len(fields["phone"]["options"]),2)

    def test_negation_unclear_conditional_and_salary_without_month_are_not_guessed(self):
        for row in [turn("Tôi không muốn làm ca đêm."),turn("Nếu tôi muốn làm lắp ráp thì sao?"),turn("Tôi muốn làm lắp ráp.",unclear=True),turn("Tôi mong muốn lương 10 triệu."),turn("Bạn tôi muốn làm lắp ráp.")]:
            self.assertTrue(all(f["value"] is None for f in extract([row])))

    def test_residence_not_work_location_and_vague_salary_range_not_normalized(self):
        fields={f["code"]:f for f in extract([turn("Tôi đang ở Bắc Ninh. Tôi mong muốn lương từ 10 đến 12 triệu/tháng.")])}
        self.assertIsNone(fields["desired_location"]["value"])
        self.assertIsNone(fields["expected_salary"]["value"])

    def test_overflow_abstains_even_when_first_twenty_values_are_identical(self):
        field=next(f for f in extract([turn("Tôi muốn ca ngày.",str(i)) for i in range(21)]) if f["code"]=="shift")
        self.assertTrue(field["conflict"])


class InfoAPITests(TestCase):
    def setUp(self):
        self.user=get_user_model().objects.create_user("info-owner")
        self.other=get_user_model().objects.create_user("info-other")
        self.reviewer=get_user_model().objects.create_superuser("info-reviewer")
        for u in (self.user,self.other):u.user_permissions.add(Permission.objects.get(codename="annotate_quality"))
        self.client.force_login(self.user)
        self.conversation=Conversation.objects.create(title="Info test",owner=self.user)
        self.turns=[turn("Tôi muốn làm lắp ráp.","job"),turn("Tôi mong muốn lương 10 triệu/tháng.","salary"),turn("Lương bên em là 15 triệu/tháng.","consultant","consultant")]
        self.revision=Revision.objects.create(conversation=self.conversation,utterances=self.turns,roles_confirmed=True,transcript_reviewed=True)
        self.base=f"/api/candidate-info/revisions/{self.revision.pk}/profiles/"

    def create(self,data=None,status=201):
        r=self.client.post(self.base,data or {"source":"rules"},content_type="application/json")
        self.assertEqual(r.status_code,status,r.content)
        return r.json()

    def manual(self):
        original=self.create()
        return self.create({"source":"manual","fields":original["fields"],"supersedes_id":original["id"]})

    def confirm(self,row,status=200,**changes):
        r=self.client.post(f"/api/candidate-info/profiles/{row['id']}/confirm/",{"expected_version":row["version"],"confirmed_content":True,**changes},content_type="application/json")
        self.assertEqual(r.status_code,status,r.content)
        return r.json()

    def search(self,row,status=201,**changes):
        r=self.client.post(f"/api/candidate-info/profiles/{row['id']}/searches/",{"top_k":3,"strict_salary":False,"confirmed_share":True,**changes},content_type="application/json")
        self.assertEqual(r.status_code,status,r.content)
        return r.json()

    def test_manual_copy_confirmation_history_and_immutable_source(self):
        row=self.manual()
        result=self.confirm(row)
        self.assertEqual(result["status"],"confirmed")
        self.revision.refresh_from_db()
        self.assertEqual(self.revision.status,"sealed")
        self.assertEqual(len(self.client.get(self.base).json()["items"]),2)
        obj=CandidateProfile.objects.get(pk=row["id"])
        obj.fields=[]
        with self.assertRaises(ValidationError):obj.save()

    def test_confirmation_requires_manual_reviewed_source_consent_and_version(self):
        self.confirm(self.create(),422)
        row=self.manual()
        self.confirm(row,422,confirmed_content=False)
        self.confirm(row,409,expected_version=True)
        self.revision.transcript_reviewed=False
        self.revision.save()
        self.confirm(row,409)

    def test_unreviewed_source_and_audio_no_speech_block(self):
        self.revision.transcript_reviewed=False
        self.revision.save()
        self.confirm(self.manual(),422)
        self.revision.transcript_reviewed=True
        self.revision.save()
        AudioSample.objects.create(call_id="info-audio",source_path="unused",duration_seconds=1,conversation=self.conversation,review_disposition="no_speech")
        self.confirm(self.manual(),422)

    def test_evidence_and_field_values_validation(self):
        fields=self.create()["fields"]
        for change in ("quote","foreign","consultant","bool","conflict"):
            changed=deepcopy(fields)
            field=next(f for f in changed if f["code"]=="desired_job")
            if change=="quote":field["evidence"][0]["quote"]="Bịa"
            elif change=="foreign":field["evidence"][0]["utterance_id"]="foreign"
            elif change=="consultant":field["evidence"][0]["utterance_id"]="consultant"
            elif change=="bool":field["evidence"][0]["start"]=False
            else:field["conflict"]=True
            self.create({"source":"manual","fields":changed},422)
        changed=deepcopy(fields)
        next(f for f in changed if f["code"]=="expected_salary")["value"]=True
        self.create({"source":"manual","fields":changed},422)

    def test_stale_source_and_search_cannot_be_used(self):
        row=self.confirm(self.manual())
        Revision.objects.create(conversation=self.conversation,utterances=self.turns,roles_confirmed=True,transcript_reviewed=True)
        with patch("candidate_info.matching.search") as mocked:self.search(row,409)
        mocked.assert_not_called()
        self.assertTrue(self.client.get(self.base).json()["items"][0]["stale"])

    def test_search_requires_confirmation_consent_and_valid_top_k(self):
        row=self.manual()
        self.search(row,422)
        row=self.confirm(row)
        with patch("candidate_info.matching.search") as mocked:
            self.search(row,422,confirmed_share=False)
            self.search(row,422,top_k=True)
            self.search(row,422,top_k=11)
        mocked.assert_not_called()

    def test_search_stores_audit_and_minimal_query_not_profile_identifiers(self):
        row=self.confirm(self.manual())
        with patch("candidate_info.matching.search",return_value=matching_result()) as mocked:result=self.search(row)
        self.assertEqual(result["query"]["desired_job"],"lắp ráp")
        self.assertTrue(set(result["query"]).isdisjoint({"full_name","phone","residence","utterances"}))
        mocked.assert_called_once()
        self.assertEqual(CampaignSearch.objects.count(),1)
        self.assertEqual(self.client.get(f"/api/candidate-info/profiles/{row['id']}/searches/").json()["items"][0]["id"],result["id"])

    def test_network_error_and_changed_revision_do_not_save_results(self):
        row=self.confirm(self.manual())
        with patch("candidate_info.matching.search",side_effect=MatchingUnavailable()):self.search(row,503)
        self.assertFalse(CampaignSearch.objects.exists())
        def changed(query):
            Revision.objects.create(conversation=self.conversation,utterances=self.turns)
            return matching_result()
        with patch("candidate_info.matching.search",side_effect=changed):self.search(row,409)
        self.assertFalse(CampaignSearch.objects.exists())

    def test_auth_scope_shared_read_confirmation_reviewer_and_csrf(self):
        row=self.manual()
        self.client.logout()
        self.assertEqual(self.client.get(self.base).status_code,401)
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(self.base).status_code,404)
        self.conversation.members.add(self.other)
        self.assertEqual(self.client.get(self.base).status_code,200)
        self.confirm(row,403)
        self.client.force_login(self.reviewer)
        self.confirm(row)
        client=Client(enforce_csrf_checks=True);client.force_login(self.user)
        self.assertEqual(client.post(self.base,{"source":"rules"},content_type="application/json").status_code,403)

    def test_response_validation_rejects_inactive_duplicates_nan_and_wrong_shape(self):
        for bad in (None,{},dict(matching_result(),recommendations=[{"status":"inactive"}])):
            with self.assertRaises(MatchingUnavailable):validate_result(bad,3)
        result=matching_result();result["recommendations"][0]["semantic_score"]=float("nan")
        with self.assertRaises(MatchingUnavailable):validate_result(result,3)

    def test_automatic_ner_model_not_claimed_and_unknown_source_rejected(self):
        self.assertFalse(self.client.get("/api/candidate-info/config/").json()["ner_model_available"])
        self.create({"source":"model"},422)

    def test_timeout_is_bounded_and_mapped_to_matching_unavailable(self):
        with patch("candidate_info.matching.requests.Session.post",side_effect=requests.Timeout()) as mocked:
            with self.assertRaises(MatchingUnavailable):search({"desired_job":"lắp ráp","top_k":3})
        self.assertEqual(mocked.call_args.kwargs["timeout"],(3.05,30))

    def test_emoji_evidence_uses_codepoints_and_query_redacts_embedded_identifiers(self):
        turns=[turn("🙂 Tôi muốn làm lắp ráp, liên hệ 0987654321.")]
        fields=extract(turns)
        clean=validate_fields(fields,turns)
        query=make_query(type("Profile",(),{"fields":clean})(),3,False)
        self.assertNotIn("0987654321",str(query))

    def test_response_drops_unknown_extra_fields(self):
        result=matching_result();result["private_transcript"]="Not part of campaign contract"
        result["recommendations"][0]["private_phone"]="0987654321"
        safe=validate_result(result,3)
        self.assertNotIn("private_transcript",safe)
        self.assertNotIn("private_phone",safe["recommendations"][0])

    def test_eligible_but_no_vectors_is_not_successful_empty_result(self):
        result=matching_result();result["recommendations"]=[];result["indexed_campaigns"]=0
        with self.assertRaises(MatchingUnavailable):validate_result(result,3)
