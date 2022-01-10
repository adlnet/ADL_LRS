import json
import base64
import uuid
import urllib.request, urllib.parse, urllib.error
import hashlib
from datetime import datetime, timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils.timezone import utc
from django.conf import settings

from ..models import Statement, Agent, Verb, Activity, SubStatement
from ..utils import retrieve_statement

from adl_lrs.views import register


class AuthTests(TestCase):
    # Want to test no auth, so have to disable both auths

    @classmethod
    def setUpClass(cls):
        print("\n%s" % __name__)
        super(AuthTests, cls).setUpClass()

    def setUp(self):
        if not settings.ALLOW_EMPTY_HTTP_AUTH:
            settings.ALLOW_EMPTY_HTTP_AUTH = True

        if settings.OAUTH_ENABLED:
            settings.OAUTH_ENABLED = False

        self.auth = "Basic %s" % base64.b64encode("%s:%s" % ('', ''))

        self.guid1 = str(uuid.uuid1())
        self.guid2 = str(uuid.uuid1())
        self.guid3 = str(uuid.uuid1())
        self.guid4 = str(uuid.uuid1())
        self.guid5 = str(uuid.uuid1())
        self.guid6 = str(uuid.uuid1())
        self.guid7 = str(uuid.uuid1())
        self.guid8 = str(uuid.uuid1())
        self.guid9 = str(uuid.uuid1())
        self.guid10 = str(uuid.uuid1())
        self.cguid1 = str(uuid.uuid1())
        self.cguid2 = str(uuid.uuid1())
        self.cguid3 = str(uuid.uuid1())
        self.cguid4 = str(uuid.uuid1())
        self.cguid5 = str(uuid.uuid1())
        self.cguid6 = str(uuid.uuid1())
        self.cguid7 = str(uuid.uuid1())
        self.cguid8 = str(uuid.uuid1())

        stmt = json.dumps({"verb": {"id": "http://example.com/verbs/created",
                                    "display": {"en-US": "created"}}, "object": {"id": "act:activity"},
                           "actor": {"objectType": "Agent", "mbox": "mailto:s@s.com"}})
        exist_stmt_response = self.client.post(reverse('lrs:statements'), stmt, content_type="application/json",
                                               Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(exist_stmt_response.status_code, 200)
        self.exist_stmt_id = json.loads(exist_stmt_response.content)[0]

        self.firstTime = str(datetime.utcnow().replace(tzinfo=utc).isoformat())
        self.existStmt1 = json.dumps({"verb": {"id": "http://example.com/verbs/created",
                                               "display": {"en-US": "created"}}, "actor": {"objectType": "Agent", "mbox": "mailto:s@s.com"},
                                      "object": {"objectType": "Activity", "id": "act:foogie",
                                                 "definition": {"name": {"en-US": "testname2", "en-GB": "altname"},
                                                                "description": {"en-US": "testdesc2", "en-GB": "altdesc"},
                                                                "type": "http://adlnet.gov/expapi/activities/cmi.interaction",
                                                                "interactionType": "fill-in", "correctResponsesPattern": ["answer"],
                                                                "extensions": {"ext:key1": "value1", "ext:key2": "value2", "ext:key3": "value3"}}},
                                      "result": {"score": {"scaled": .85}, "completion": True, "success": True, "response": "kicked",
                                                 "duration": "P3Y6M4DT12H30M5S", "extensions": {"ext:key1": "value1", "ext:key2": "value2"}},
                                      "context": {"registration": self.cguid1, "contextActivities": {"other": {"id": "act:NewActivityID2"}},
                                                  "revision": "food", "platform": "bard", "language": "en-US", "extensions": {"ext:ckey1": "cval1",
                                                                                                                              "ext:ckey2": "cval2"}}})

        self.existStmt2 = json.dumps({"verb": {"id": "http://example.com/verbs/created",
                                               "display": {"en-US": "created"}}, "actor": {"objectType": "Agent", "mbox": "mailto:s@t.com"},
                                      "object": {"objectType": "Activity", "id": "act:foogie",
                                                 "definition": {"name": {"en-US": "testname3", "en-GB": "altname"},
                                                                "description": {"en-US": "testdesc3", "en-GB": "altdesc"},
                                                                "type": "http://adlnet.gov/expapi/activities/cmi.interaction",
                                                                "interactionType": "fill-in", "correctResponsesPattern": ["answers"],
                                                                "extensions": {"ext:key11": "value11", "ext:key22": "value22", "ext:key33": "value33"}}},
                                      "result": {"score": {"scaled": .75}, "completion": True, "success": True, "response": "shouted",
                                                 "duration": "P3Y6M4DT12H30M5S", "extensions": {"ext:dkey1": "dvalue1", "ext:dkey2": "dvalue2"}},
                                      "context": {"registration": self.cguid2, "contextActivities": {"other": {"id": "act:NewActivityID22"}},
                                                  "revision": "food", "platform": "bard", "language": "en-US", "extensions": {"ext:ckey11": "cval11",
                                                                                                                              "ext:ckey22": "cval22"}}})

        self.existStmt3 = json.dumps({"verb": {"id": "http://example.com/verbs/created",
                                               "display": {"en-US": "created"}}, "actor": {"objectType": "Agent", "mbox": "mailto:s@s.com"},
                                      "object": {"objectType": "Activity", "id": "act:act:foogals",
                                                 "definition": {"name": {"en-US": "testname3"}, "description": {"en-US": "testdesc3"},
                                                                "type": "http://adlnet.gov/expapi/activities/cmi.interaction",
                                                                "interactionType": "fill-in", "correctResponsesPattern": ["answers"],
                                                                "extensions": {"ext:key111": "value111", "ext:key222": "value222", "ext:key333": "value333"}}},
                                      "result": {"score": {"scaled": .79}, "completion": True, "success": True, "response": "shouted",
                                                 "duration": "P3Y6M4DT12H30M5S", "extensions": {"ext:dkey1": "dvalue1", "ext:dkey2": "dvalue2"}},
                                      "context": {"registration": self.cguid3, "contextActivities": {"other": {"id": "act:NewActivityID22"}},
                                                  "revision": "food", "platform": "bard", "language": "en-US",
                                                  "instructor": {"objectType": "Agent", "name": "bob", "mbox": "mailto:bob@bob.com"},
                                                  "extensions": {"ext:ckey111": "cval111", "ext:ckey222": "cval222"}}})

        self.existStmt4 = json.dumps({"verb": {"id": "http://example.com/verbs/created",
                                               "display": {"en-US": "created"}}, "actor": {"objectType": "Agent", "mbox": "mailto:s@s.com"},
                                      "object": {"objectType": "Activity", "id": "act:foogal",
                                                 "definition": {"name": {"en-US": "testname3"}, "description": {"en-US": "testdesc3"},
                                                                "type": "http://adlnet.gov/expapi/activities/cmi.interaction",
                                                                "interactionType": "fill-in", "correctResponsesPattern": ["answers"],
                                                                "extensions": {"ext:key111": "value111", "ext:key222": "value222", "ext:key333": "value333"}}},
                                      "result": {"score": {"scaled": .79}, "completion": True, "success": True, "response": "shouted",
                                                 "duration": "P3Y6M4DT12H30M5S", "extensions": {"ext:dkey1": "dvalue1", "ext:dkey2": "dvalue2"}},
                                      "context": {"registration": self.cguid4, "contextActivities": {"other": {"id": "act:NewActivityID22"}},
                                                  "revision": "food", "platform": "bard", "language": "en-US",
                                                  "instructor": {"name": "bill", "mbox": "mailto:bill@bill.com"},
                                                  "extensions": {"ext:ckey111": "cval111", "ext:ckey222": "cval222"}}})

        self.existStmt5 = json.dumps({"object": {"objectType": "Agent", "name": "jon", "mbox": "mailto:jon@jon.com"},
                                      "verb": {"id": "http://example.com/verbs/created", "display": {"en-US": "created"}},
                                      "actor": {"objectType": "Agent", "mbox": "mailto:s@s.com"}})

        self.existStmt6 = json.dumps({"actor": {"objectType": "Agent", "name": "max", "mbox": "mailto:max@max.com"},
                                      "object": {"id": "act:test_activity"}, "verb": {"id": "http://example.com/verbs/created",
                                                                                      "display": {"en-US": "created"}}})

        self.existStmt7 = json.dumps({"object": {"objectType": "Agent", "name": "max", "mbox": "mailto:max@max.com"},
                                      "verb": {"id": "http://example.com/verbs/created", "display": {"en-US": "created"}},
                                      "actor": {"objectType": "Agent", "mbox": "mailto:s@s.com"}})

        self.existStmt8 = json.dumps({"object": {"objectType": "Agent", "name": "john", "mbox": "mailto:john@john.com"},
                                      "verb": {"id": "http://example.com/verbs/missed", "display": {"en-US": "missed"}},
                                      "actor": {"objectType": "Agent", "mbox": "mailto:s@s.com"}})

        self.existStmt9 = json.dumps({"actor": {"objectType": "Agent", "mbox": "mailto:sub@sub.com"},
                                      "verb": {"id": "http://example.com/verbs/missed"},
                                      "object": {"objectType": "SubStatement",
                                                 "actor": {"objectType": "Agent", "mbox": "mailto:ss@ss.com"},
                                                 "verb": {"id": "nested:verb/url/nested"},
                                                 "object": {"objectType": "Activity", "id": "act:testex.com"},
                                                 "result": {"completion": True, "success": True, "response": "kicked"},
                                                 "context": {"registration": self.cguid6,
                                                             "contextActivities": {"other": {"id": "act:NewActivityID"}},
                                                             "revision": "foo",
                                                             "platform": "bar",
                                                             "language": "en-US",
                                                             "extensions": {"ext:k1": "v1", "ext:k2": "v2"}}}})

        self.existStmt10 = json.dumps({"actor": {"objectType": "Agent", "mbox": "mailto:ref@ref.com"},
                                       "verb": {"id": "http://example.com/verbs/missed"}, "object": {"objectType": "StatementRef",
                                                                                                     "id": str(self.exist_stmt_id)}})

        # Put statements
        param = {"statementId": self.guid1}
        path = "%s?%s" % (reverse('lrs:statements'), urllib.parse.urlencode(param))
        stmt_payload = self.existStmt1
        self.putresponse1 = self.client.put(path, stmt_payload, content_type="application/json",
                                            Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(self.putresponse1.status_code, 204)
        time = retrieve_statement.convert_to_datetime_object(
            str((datetime.utcnow() + timedelta(seconds=2)).replace(tzinfo=utc).isoformat()))
        stmt = Statement.objects.filter(
            statement_id=self.guid1).update(stored=time)

        param = {"statementId": self.guid3}
        path = "%s?%s" % (reverse('lrs:statements'), urllib.parse.urlencode(param))
        stmt_payload = self.existStmt3
        self.putresponse3 = self.client.put(path, stmt_payload, content_type="application/json",
                                            Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(self.putresponse3.status_code, 204)
        time = retrieve_statement.convert_to_datetime_object(
            str((datetime.utcnow() + timedelta(seconds=3)).replace(tzinfo=utc).isoformat()))
        stmt = Statement.objects.filter(
            statement_id=self.guid3).update(stored=time)

        param = {"statementId": self.guid4}
        path = "%s?%s" % (reverse('lrs:statements'), urllib.parse.urlencode(param))
        stmt_payload = self.existStmt4
        self.putresponse4 = self.client.put(path, stmt_payload, content_type="application/json",
                                            Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(self.putresponse4.status_code, 204)
        time = retrieve_statement.convert_to_datetime_object(
            str((datetime.utcnow() + timedelta(seconds=4)).replace(tzinfo=utc).isoformat()))
        stmt = Statement.objects.filter(
            statement_id=self.guid4).update(stored=time)

        self.secondTime = str(
            (datetime.utcnow() + timedelta(seconds=4)).replace(tzinfo=utc).isoformat())

        param = {"statementId": self.guid2}
        path = "%s?%s" % (reverse('lrs:statements'), urllib.parse.urlencode(param))
        stmt_payload = self.existStmt2
        self.putresponse2 = self.client.put(path, stmt_payload, content_type="application/json",
                                            Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(self.putresponse2.status_code, 204)
        time = retrieve_statement.convert_to_datetime_object(
            str((datetime.utcnow() + timedelta(seconds=6)).replace(tzinfo=utc).isoformat()))
        stmt = Statement.objects.filter(
            statement_id=self.guid2).update(stored=time)

        param = {"statementId": self.guid5}
        path = "%s?%s" % (reverse('lrs:statements'), urllib.parse.urlencode(param))
        stmt_payload = self.existStmt5
        self.putresponse5 = self.client.put(path, stmt_payload, content_type="application/json",
                                            Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(self.putresponse5.status_code, 204)
        time = retrieve_statement.convert_to_datetime_object(
            str((datetime.utcnow() + timedelta(seconds=7)).replace(tzinfo=utc).isoformat()))
        stmt = Statement.objects.filter(
            statement_id=self.guid5).update(stored=time)

        param = {"statementId": self.guid6}
        path = "%s?%s" % (reverse('lrs:statements'), urllib.parse.urlencode(param))
        stmt_payload = self.existStmt6
        self.putresponse6 = self.client.put(path, stmt_payload, content_type="application/json",
                                            Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(self.putresponse6.status_code, 204)
        time = retrieve_statement.convert_to_datetime_object(
            str((datetime.utcnow() + timedelta(seconds=8)).replace(tzinfo=utc).isoformat()))
        stmt = Statement.objects.filter(
            statement_id=self.guid6).update(stored=time)

        param = {"statementId": self.guid7}
        path = "%s?%s" % (reverse('lrs:statements'), urllib.parse.urlencode(param))
        stmt_payload = self.existStmt7
        self.putresponse7 = self.client.put(path, stmt_payload, content_type="application/json",
                                            Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(self.putresponse7.status_code, 204)
        time = retrieve_statement.convert_to_datetime_object(
            str((datetime.utcnow() + timedelta(seconds=9)).replace(tzinfo=utc).isoformat()))
        stmt = Statement.objects.filter(
            statement_id=self.guid7).update(stored=time)

        param = {"statementId": self.guid8}
        path = "%s?%s" % (reverse('lrs:statements'), urllib.parse.urlencode(param))
        stmt_payload = self.existStmt8
        self.putresponse8 = self.client.put(path, stmt_payload, content_type="application/json",
                                            Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(self.putresponse8.status_code, 204)
        time = retrieve_statement.convert_to_datetime_object(
            str((datetime.utcnow() + timedelta(seconds=10)).replace(tzinfo=utc).isoformat()))
        stmt = Statement.objects.filter(
            statement_id=self.guid8).update(stored=time)

        param = {"statementId": self.guid9}
        path = "%s?%s" % (reverse('lrs:statements'), urllib.parse.urlencode(param))
        stmt_payload = self.existStmt9
        self.putresponse9 = self.client.put(path, stmt_payload, content_type="application/json",
                                            Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(self.putresponse9.status_code, 204)
        time = retrieve_statement.convert_to_datetime_object(
            str((datetime.utcnow() + timedelta(seconds=11)).replace(tzinfo=utc).isoformat()))
        stmt = Statement.objects.filter(
            statement_id=self.guid9).update(stored=time)

        param = {"statementId": self.guid10}
        path = "%s?%s" % (reverse('lrs:statements'), urllib.parse.urlencode(param))
        stmt_payload = self.existStmt10
        self.putresponse10 = self.client.put(path, stmt_payload, content_type="application/json",
                                             Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(self.putresponse10.status_code, 204)
        time = retrieve_statement.convert_to_datetime_object(
            str((datetime.utcnow() + timedelta(seconds=11)).replace(tzinfo=utc).isoformat()))
        stmt = Statement.objects.filter(
            statement_id=self.guid10).update(stored=time)

    def tearDown(self):
        if settings.ALLOW_EMPTY_HTTP_AUTH:
            settings.ALLOW_EMPTY_HTTP_AUTH = False
        if not settings.OAUTH_ENABLED:
            settings.OAUTH_ENABLED = True

    def test_post_with_no_valid_params(self):
        # Error will be thrown in statements class
        resp = self.client.post(reverse('lrs:statements'), {"feet": "yes", "hands": {"id": "http://example.com/test_post"}},
                                Authorization=self.auth, content_type="application/json", X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(resp.status_code, 400)

    def test_post(self):
        stmt = json.dumps({"actor": {"objectType": "Agent", "mbox": "mailto:t@t.com", "name": "bob"},
                           "verb": {"id": "http://example.com/verbs/passed", "display": {"en-US": "passed"}},
                           "object": {"id": "act:test_post"}})

        response = self.client.post(reverse('lrs:statements'), stmt, content_type="application/json",
                                    Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)

        self.assertEqual(response.status_code, 200)
        act = Activity.objects.get(activity_id="act:test_post")
        self.assertEqual(act.activity_id, "act:test_post")
        agent = Agent.objects.get(mbox="mailto:t@t.com")
        self.assertEqual(agent.name, "bob")

    def test_post_stmt_ref_no_existing_stmt(self):
        stmt = json.dumps({"actor": {"objectType": "Agent", "mbox": "mailto:ref@ref.com"},
                           "verb": {"id": "http://example.com/verbs/missed"}, "object": {"objectType": "StatementRef",
                                                                                         "id": "12345678-1234-5678-1234-567812345678"}})
        response = self.client.post(reverse('lrs:statements'), stmt, content_type="application/json",
                                    Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(response.status_code, 200)

    def test_post_with_actor(self):
        stmt = json.dumps({"actor": {"mbox": "mailto:mr.t@example.com"},
                           "verb": {"id": "http://example.com/verbs/passed", "display": {"en-US": "passed"}},
                           "object": {"id": "act:i.pity.the.fool"}})

        response = self.client.post(reverse('lrs:statements'), stmt, content_type="application/json",
                                    Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(response.status_code, 200)
        Agent.objects.get(mbox="mailto:mr.t@example.com")

    def test_list_post(self):
        stmts = json.dumps([{"verb": {"id": "http://example.com/verbs/passed", "display": {"en-US": "passed"}},
                             "object": {"id": "act:test_list_post"}, "actor": {"objectType": "Agent", "mbox": "mailto:t@t.com"}},
                            {"verb": {"id": "http://example.com/verbs/failed", "display": {"en-GB": "failed"}},
                             "object": {"id": "act:test_list_post1"}, "actor": {"objectType": "Agent", "mbox": "mailto:t@t.com"}}])

        response = self.client.post(reverse('lrs:statements'), stmts, content_type="application/json",
                                    Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(response.status_code, 200)
        activity1 = Activity.objects.get(activity_id="act:test_list_post")
        activity2 = Activity.objects.get(activity_id="act:test_list_post1")
        stmt1 = Statement.objects.get(object_activity=activity1)
        stmt2 = Statement.objects.get(object_activity=activity2)
        verb1 = Verb.objects.get(id=stmt1.verb.id)
        verb2 = Verb.objects.get(id=stmt2.verb.id)
        lang_map1 = verb1.canonical_data['display']
        lang_map2 = verb2.canonical_data['display']

        self.assertEqual(response.status_code, 200)
        self.assertEqual(stmt1.verb.verb_id, "http://example.com/verbs/passed")
        self.assertEqual(stmt2.verb.verb_id, "http://example.com/verbs/failed")

        self.assertEqual(list(lang_map1.keys())[0], "en-US")
        self.assertEqual(list(lang_map1.values())[0], "passed")
        self.assertEqual(list(lang_map2.keys())[0], "en-GB")
        self.assertEqual(list(lang_map2.values())[0], "failed")

    def test_put(self):
        guid = str(uuid.uuid1())

        param = {"statementId": guid}
        path = "%s?%s" % (reverse('lrs:statements'), urllib.parse.urlencode(param))
        stmt = json.dumps({"verb": {"id": "http://example.com/verbs/passed", "display": {"en-US": "passed"}},
                           "object": {"id": "act:test_put"}, "actor": {"objectType": "Agent", "mbox": "mailto:t@t.com"}})

        putResponse = self.client.put(path, stmt, content_type="application/json",
                                      Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(putResponse.status_code, 204)
        stmt = Statement.objects.get(statement_id=guid)

        act = Activity.objects.get(activity_id="act:test_put")
        self.assertEqual(act.activity_id, "act:test_put")

        self.assertEqual(stmt.actor.mbox, "mailto:t@t.com")

        self.assertEqual(stmt.verb.verb_id, "http://example.com/verbs/passed")

    def test_put_with_substatement(self):
        con_guid = str(uuid.uuid1())
        st_guid = str(uuid.uuid1())

        param = {"statementId": st_guid}
        path = "%s?%s" % (reverse('lrs:statements'), urllib.parse.urlencode(param))
        stmt = json.dumps({"actor": {"objectType": "Agent", "mbox": "mailto:sass@sass.com"},
                           "verb": {"id": "verb:verb/url/tested"},
                           "object": {"objectType": "SubStatement",
                                      "actor": {"objectType": "Agent", "mbox": "mailto:ss@ss.com"},
                                      "verb": {"id": "verb:verb/url/nested"},
                                      "object": {"objectType": "Activity", "id": "act:testex.com"},
                                      "result": {"completion": True, "success": True, "response": "kicked"},
                                      "context": {"registration": con_guid,
                                                  "contextActivities": {"other": {"id": "act:NewActivityID"}},
                                                  "revision": "foo",
                                                  "platform": "bar",
                                                  "language": "en-US",
                                                  "extensions": {"ext:k1": "v1", "ext:k2": "v2"}}}})

        response = self.client.put(path, stmt, content_type="application/json",
                                   Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(response.status_code, 204)

        path = "%s?%s" % (reverse('lrs:statements'), urllib.parse.urlencode(param))
        get_response = self.client.get(
            path, X_Experience_API_Version=settings.XAPI_VERSION, Authorization=self.auth)
        self.assertEqual(get_response.status_code, 200)
        rsp = get_response.content
        self.assertIn("objectType", rsp)
        self.assertIn("SubStatement", rsp)
        self.assertIn("actor", rsp)
        self.assertIn("mailto:ss@ss.com", rsp)
        self.assertIn("verb", rsp)
        self.assertIn("verb:verb/url/nested", rsp)
        self.assertIn("Activity", rsp)
        self.assertIn("act:testex.com", rsp)
        self.assertIn("result", rsp)
        self.assertIn("completion", rsp)
        self.assertIn("success", rsp)
        self.assertIn("response", rsp)
        self.assertIn("kicked", rsp)
        self.assertIn("context", rsp)
        self.assertIn(con_guid, rsp)
        self.assertIn("contextActivities", rsp)
        self.assertIn("other", rsp)
        self.assertIn("revision", rsp)
        self.assertIn("foo", rsp)
        self.assertIn("platform", rsp)
        self.assertIn("bar", rsp)
        self.assertIn("language", rsp)
        self.assertIn("en-US", rsp)
        self.assertIn("extensions", rsp)
        self.assertIn("ext:k1", rsp)
        self.assertIn("v1", rsp)
        self.assertIn("ext:k2", rsp)
        self.assertIn("v2", rsp)

    def test_no_content_put(self):
        guid = str(uuid.uuid1())

        param = {"statementId": guid}
        path = "%s?%s" % (reverse('lrs:statements'), urllib.parse.urlencode(param))
        stmt = json.dumps({})

        putResponse = self.client.put(path, stmt, content_type="application/json",
                                      Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(putResponse.status_code, 400)

    def test_existing_stmtID_put_put(self):
        guid = str(uuid.uuid1())

        param = {"statementId": guid}
        path = "%s?%s" % (reverse('lrs:statements'), urllib.parse.urlencode(param))
        exist_stmt = json.dumps({"verb": {"id": "http://example.com/verbs/passed", "display": {"en-US": "passed"}},
                                 "object": {"id": "act:activity"}, "actor": {"objectType": "Agent", "mbox": "mailto:t@t.com"}})
        first_put = self.client.put(path, exist_stmt, content_type="application/json",
                                    Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(first_put.status_code, 204)

        stmt = json.dumps({"verb": {"id": "http://example.com/verbs/passed", "display": {"en-US": "passed"}},
                           "object": {"id": "act:test_existing_put"}, "actor": {"objectType": "Agent", "mbox": "mailto:t@t.com"}})
        putResponse = self.client.put(path, stmt, content_type="application/json",
                                      Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(putResponse.status_code, 409)

    def test_existing_stmtID_put_post(self):
        guid = str(uuid.uuid1())

        exist_stmt = json.dumps({"id": guid, "verb": {"id": "http://example.com/verbs/passed", "display": {"en-US": "passed"}},
                                 "object": {"id": "act:activity"}, "actor": {"objectType": "Agent", "mbox": "mailto:t@t.com"}})
        post = self.client.post(reverse('lrs:statements'), exist_stmt, content_type="application/json",
                                Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(post.status_code, 200)

        param = {"statementId": guid}
        path = "%s?%s" % (reverse('lrs:statements'), urllib.parse.urlencode(param))
        stmt = json.dumps({"verb": {"id": "http://example.com/verbs/passed", "display": {"en-US": "passed"}},
                           "object": {"id": "act:test_existing_put"}, "actor": {"objectType": "Agent", "mbox": "mailto:t@t.com"}})

        putResponse = self.client.put(path, stmt, content_type="application/json",
                                      Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(putResponse.status_code, 409)

    def test_missing_stmtID_put(self):
        stmt = json.dumps({"verb": {"id": "http://example.com/verbs/passed", "display": {"en-US": "passed"}},
                           "object": {"id": "act:act:test_put"}, "actor": {"objectType": "Agent", "mbox": "mailto:t@t.com"}})
        response = self.client.put(reverse('lrs:statements'), stmt, content_type="application/json",
                                   Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(response.status_code, 400)
        self.assertIn(
            response.content, "Error -- statements - method = PUT, but no statementId parameter or ID given in statement")

    def test_get(self):
        param = {"statementId": self.guid1}
        path = "%s?%s" % (reverse('lrs:statements'), urllib.parse.urlencode(param))
        getResponse = self.client.get(
            path, X_Experience_API_Version=settings.XAPI_VERSION, Authorization=self.auth)
        self.assertEqual(getResponse.status_code, 200)
        rsp = getResponse.content
        self.assertIn(self.guid1, rsp)

    def test_get_no_existing_ID(self):
        param = {"statementId": "aaaaaa"}
        path = "%s?%s" % (reverse('lrs:statements'), urllib.parse.urlencode(param))
        getResponse = self.client.get(
            path, X_Experience_API_Version=settings.XAPI_VERSION, Authorization=self.auth)
        self.assertEqual(getResponse.status_code, 400)

    def test_get_no_statementid(self):
        getResponse = self.client.get(reverse(
            'lrs:statements'), X_Experience_API_Version=settings.XAPI_VERSION, Authorization=self.auth)
        self.assertEqual(getResponse.status_code, 200)
        jsn = json.loads(getResponse.content)
        self.assertEqual(len(jsn["statements"]), 11)

    # Sever activities are PUT-contextActivites create 3 more
    def test_number_of_activities(self):
        acts = len(Activity.objects.all())
        self.assertEqual(9, acts)

    def test_update_activity_correct_auth(self):
        stmt = json.dumps({"verb": {"id": "verb:verb/url/changed-act"}, "actor": {"objectType": "Agent", "mbox": "mailto:l@l.com"},
                           "object": {"objectType": "Activity", "id": "act:foogie",
                                      "definition": {"name": {"en-US": "testname3"}, "description": {"en-US": "testdesc3"},
                                                     "type": "http://adlnet.gov/expapi/activities/cmi.interaction", "interactionType": "fill-in", "correctResponsesPattern": ["answer"],
                                                     "extensions": {"ext:key1": "value1", "ext:key2": "value2", "ext:key3": "value3"}}},
                           "result": {"score": {"scaled": .85}, "completion": True, "success": True, "response": "kicked",
                                      "duration": "P3Y6M4DT12H30M5S", "extensions": {"ext:key1": "value1", "ext:key2": "value2"}},
                           "context": {"registration": self.cguid8, "contextActivities": {"other": {"id": "act:NewActivityID2"}},
                                       "revision": "food", "platform": "bard", "language": "en-US", "extensions": {"ext:ckey1": "cval1",
                                                                                                                   "ext:ckey2": "cval2"}}})

        post_response = self.client.post(reverse('lrs:statements'), stmt, content_type="application/json",
                                         Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(post_response.status_code, 200)

        act = Activity.objects.get(activity_id="act:foogie")

        name_set = act.canonical_data['definition']['name']
        desc_set = act.canonical_data['definition']['description']

        self.assertEqual(list(name_set.keys())[1], "en-US")
        self.assertEqual(list(name_set.values())[1], "testname3")
        self.assertEqual(list(name_set.keys())[0], "en-GB")
        self.assertEqual(list(name_set.values())[0], "altname")

        self.assertEqual(list(desc_set.keys())[1], "en-US")
        self.assertEqual(list(desc_set.values())[1], "testdesc3")
        self.assertEqual(list(desc_set.keys())[0], "en-GB")
        self.assertEqual(list(desc_set.values())[0], "altdesc")

    def test_cors_post_put(self):
        st_id = str(uuid.uuid1())
        content = {"verb": {"id": "verb:verb/url"}, "actor": {"objectType": "Agent", "mbox": "mailto:r@r.com"},
                   "object": {"id": "act:test_cors_post_put"}}

        bdy = "statementId=%s&content=%s&Content-Type=application/json&X-Experience-API-Version=1.0.0" % (
            st_id, urllib.parse.quote(str(content)))
        path = "%s?%s" % (reverse('lrs:statements'),
                          urllib.parse.urlencode({"method": "PUT"}))
        response = self.client.post(
            path, bdy, content_type="application/x-www-form-urlencoded", Authorization=self.auth)
        self.assertEqual(response.status_code, 204)

        act = Activity.objects.get(activity_id="act:test_cors_post_put")
        self.assertEqual(act.activity_id, "act:test_cors_post_put")

    def test_issue_put(self):
        stmt_id = "33f60b35-e1b2-4ddc-9c6f-7b3f65244430"
        stmt = json.dumps({"verb": {"id": "verb:verb/iri"}, "object": {"id": "act:scorm.com/JsTetris_TCAPI", "definition": {"type": "type:media",
                                                                                                                            "name": {"en-US": "Js Tetris - Tin Can Prototype"}, "description": {"en-US": "A game of tetris."}}},
                           "context": {"contextActivities": {"grouping": {"id": "act:scorm.com/JsTetris_TCAPI"}},
                                       "registration": "6b1091be-2833-4886-b4a6-59e5e0b3c3f4"},
                           "actor": {"mbox": "mailto:tom.creighton.ctr@adlnet.gov", "name": "Tom Creighton"}})

        path = "%s?%s" % (reverse('lrs:statements'),
                          urllib.parse.urlencode({"statementId": stmt_id}))
        put_stmt = self.client.put(path, stmt, content_type="application/json",
                                   X_Experience_API_Version=settings.XAPI_VERSION, Authorization=self.auth)
        self.assertEqual(put_stmt.status_code, 204)

    def test_post_with_group(self):
        ot = "Group"
        name = "the group ST"
        mbox = "mailto:the.groupST@example.com"

        stmt = json.dumps({"actor": {"objectType": ot, "name": name, "mbox": mbox, "member": [{"name": "agentA", "mbox": "mailto:agentA@example.com"},
                                                                                              {"name": "agentB", "mbox": "mailto:agentB@example.com"}]}, "verb": {"id": "http://verb/iri/created", "display": {"en-US": "created"}},
                           "object": {"id": "act:i.pity.the.fool"}})
        response = self.client.post(reverse('lrs:statements'), stmt, content_type="application/json",
                                    Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(response.status_code, 200)
        g = Agent.objects.get(mbox="mailto:the.groupST@example.com")
        self.assertEqual(g.name, name)
        self.assertEqual(g.mbox, mbox)
        mems = g.member.values_list("name", flat=True)
        self.assertEqual(len(mems), 2)
        self.assertIn("agentA", mems)
        self.assertIn("agentB", mems)

    def test_issue_put_no_version_header(self):
        stmt_id = '33f60b35-e1b2-4ddc-9c6f-7b3f65244431'
        stmt = json.dumps({"verb": "verb:completed", "object": {"id": "act:scorm.com/JsTetris_TCAPI/level2",
                                                                "definition": {"type": "media", "name": {"en-US": "Js Tetris Level2"},
                                                                               "description": {"en-US": "Starting at 1, the higher the level, the harder the game."}}},
                           "result": {"extensions": {"ext:time": 104, "ext:apm": 229, "ext:lines": 5}, "score": {"raw": 9911, "min": 0}},
                           "context": {"contextActivities": {"grouping": {"id": "act:scorm.com/JsTetris_TCAPI"}},
                                       "registration": "b7be7d9d-bfe2-4917-8ccd-41a0d18dd953"},
                           "actor": {"name": "tom creighton", "mbox": "mailto:tom@example.com"}})

        path = '%s?%s' % (reverse('lrs:statements'),
                          urllib.parse.urlencode({"statementId": stmt_id}))
        put_stmt = self.client.put(
            path, stmt, content_type="application/json", Authorization=self.auth)
        self.assertEqual(put_stmt.status_code, 400)

    def test_issue_put_wrong_version_header(self):
        stmt_id = '33f60b35-e1b2-4ddc-9c6f-7b3f65244432'
        stmt = json.dumps({"verb": "verb:completed", "object": {"id": "act:scorm.com/JsTetris_TCAPI/level2",
                                                                "definition": {"type": "media", "name": {"en-US": "Js Tetris Level2"},
                                                                               "description": {"en-US": "Starting at 1, the higher the level, the harder the game."}}},
                           "result": {"extensions": {"ext:time": 104, "ext:apm": 229, "ext:lines": 5}, "score": {"raw": 9911, "min": 0}},
                           "context": {"contextActivities": {"grouping": {"id": "act:scorm.com/JsTetris_TCAPI"}},
                                       "registration": "b7be7d9d-bfe2-4917-8ccd-41a0d18dd953"},
                           "actor": {"name": "tom creighton", "mbox": "mailto:tom@example.com"}})

        path = '%s?%s' % (reverse('lrs:statements'),
                          urllib.parse.urlencode({"statementId": stmt_id}))
        put_stmt = self.client.put(path, stmt, content_type="application/json",
                                   Authorization=self.auth, X_Experience_API_Version="0.90")
        self.assertEqual(put_stmt.status_code, 400)

    # Use this test to make sure stmts are being returned correctly with all
    # data - doesn't check timestamp and stored fields
    def test_all_fields_activity_as_object(self):
        nested_st_id = str(uuid.uuid1())
        nest_param = {"statementId": nested_st_id}
        nest_path = "%s?%s" % (reverse('lrs:statements'),
                               urllib.parse.urlencode(nest_param))
        nested_stmt = json.dumps({"actor": {"objectType": "Agent", "mbox": "mailto:tincan@adlnet.gov"},
                                  "verb": {"id": "http://example.com/verbs/assess", "display": {"en-US": "assessed"}},
                                  "object": {"id": "http://example.adlnet.gov/tincan/example/simplestatement"}})
        put_sub_stmt = self.client.put(nest_path, nested_stmt, content_type="application/json",
                                       Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(put_sub_stmt.status_code, 204)

        stmt_id = str(uuid.uuid1())
        context_id = str(uuid.uuid1())
        param = {"statementId": stmt_id}
        path = "%s?%s" % (reverse('lrs:statements'), urllib.parse.urlencode(param))
        stmt = json.dumps({"actor": {"objectType": "Agent", "name": "Lou Wolford", "account": {"homePage": "http://example.com", "name": "uniqueName"}},
                           "verb": {"id": "http://example.com/verbs/created", "display": {"en-US": "created", "en-GB": "made"}},
                           "object": {"objectType": "Activity", "id": "http:adlnet.gov/my/Activity/URL",
                                      "definition": {"name": {"en-US": "actName", "en-GB": "anotherActName"},
                                                     "description": {"en-US": "This is my activity description.", "en-GB": "This is another activity description."},
                                                     "type": "http://www.adlnet.gov/experienceapi/activity-types/http://adlnet.gov/expapi/activities/cmi.interaction",
                                                     "interactionType": "choice",
                                                     "correctResponsesPattern": ["golf", "tetris"],
                                                     "choices": [{"id": "golf", "description": {"en-US": "Golf Example", "en-GB": "GOLF"}},
                                                                 {"id": "tetris", "description": {
                                                                     "en-US": "Tetris Example", "en-GB": "TETRIS"}},
                                                                 {"id": "facebook", "description": {
                                                                     "en-US": "Facebook App", "en-GB": "FACEBOOK"}},
                                                                 {"id": "scrabble", "description": {"en-US": "Scrabble Example", "en-GB": "SCRABBLE"}}],
                                                     "extensions": {"ext:key1": "value1", "ext:key2": "value2", "ext:key3": "value3"}}},
                           "result": {"score": {"scaled": .85, "raw": 85, "min": 0, "max": 100}, "completion": True, "success": True, "response": "Well done",
                                      "duration": "P3Y6M4DT12H30M5S", "extensions": {"ext:resultKey1": "resultValue1", "ext:resultKey2": "resultValue2"}},
                           "context": {"registration": context_id, "contextActivities": {"other": {"id": "http://example.adlnet.gov/tincan/example/test"},
                                                                                         "grouping": {"id": "http://groupingID"}},
                                       "revision": "Spelling error in choices.", "platform": "Platform is web browser.", "language": "en-US",
                                       "statement": {"objectType": "StatementRef", "id": str(nested_st_id)},
                                       "extensions": {"ext:contextKey1": "contextVal1", "ext:contextKey2": "contextVal2"}},
                           "timestamp": self.firstTime})

        put_stmt = self.client.put(path, stmt, content_type="application/json",
                                   Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(put_stmt.status_code, 204)
        get_response = self.client.get(
            path, X_Experience_API_Version=settings.XAPI_VERSION, Authorization=self.auth)

        the_returned = json.loads(get_response.content)
        self.assertEqual(the_returned['id'], stmt_id)
        self.assertEqual(the_returned['actor']['objectType'], 'Agent')
        self.assertEqual(the_returned['actor']['name'], 'Lou Wolford')
        self.assertEqual(the_returned['actor'][
                         'account']['name'], 'uniqueName')
        self.assertEqual(the_returned['actor']['account'][
                         'homePage'], 'http://example.com')

        self.assertEqual(the_returned['verb']['id'],
                         'http://example.com/verbs/created')
        self.assertEqual(the_returned['verb']['display']['en-GB'], 'made')
        self.assertEqual(the_returned['verb']['display']['en-US'], 'created')

        self.assertEqual(the_returned['result']['completion'], True)
        self.assertEqual(the_returned['result'][
                         'duration'], 'P3Y6M4DT12H30M5S')
        self.assertEqual(the_returned['result']['extensions'][
                         'ext:resultKey1'], 'resultValue1')
        self.assertEqual(the_returned['result']['extensions'][
                         'ext:resultKey2'], 'resultValue2')
        self.assertEqual(the_returned['result']['response'], 'Well done')
        self.assertEqual(the_returned['result']['score']['max'], 100)
        self.assertEqual(the_returned['result']['score']['min'], 0)
        self.assertEqual(the_returned['result']['score']['raw'], 85)
        self.assertEqual(the_returned['result']['score']['scaled'], 0.85)
        self.assertEqual(the_returned['result']['success'], True)

        self.assertEqual(the_returned['context']['contextActivities']['other'][0][
                         'id'], 'http://example.adlnet.gov/tincan/example/test')
        self.assertEqual(the_returned['context']['extensions'][
                         'ext:contextKey1'], 'contextVal1')
        self.assertEqual(the_returned['context']['extensions'][
                         'ext:contextKey2'], 'contextVal2')
        self.assertEqual(the_returned['context']['language'], 'en-US')
        self.assertEqual(the_returned['context'][
                         'platform'], 'Platform is web browser.')
        self.assertEqual(the_returned['context']['registration'], context_id)
        self.assertEqual(the_returned['context'][
                         'revision'], 'Spelling error in choices.')
        self.assertEqual(the_returned['context']['statement'][
                         'id'], str(nested_st_id))
        self.assertEqual(the_returned['context']['statement'][
                         'objectType'], 'StatementRef')

    # Use this test to make sure stmts are being returned correctly with all
    # data - doesn't check timestamp, stored fields
    def test_all_fields_agent_as_object(self):
        nested_st_id = str(uuid.uuid1())
        nest_param = {"statementId": nested_st_id}
        nest_path = "%s?%s" % (reverse('lrs:statements'),
                               urllib.parse.urlencode(nest_param))
        nested_stmt = json.dumps({"actor": {"objectType": "Agent", "mbox": "mailto:tincan@adlnet.gov"},
                                  "verb": {"id": "http://example.com/verbs/assess", "display": {"en-US": "assessed"}},
                                  "object": {"id": "http://example.adlnet.gov/tincan/example/simplestatement"}})
        put_sub_stmt = self.client.put(nest_path, nested_stmt, content_type="application/json",
                                       Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(put_sub_stmt.status_code, 204)

        stmt_id = str(uuid.uuid1())
        context_id = str(uuid.uuid1())
        param = {"statementId": stmt_id}
        path = "%s?%s" % (reverse('lrs:statements'), urllib.parse.urlencode(param))
        msha = hashlib.sha1("tom@example.com").hexdigest()
        stmt = json.dumps({"actor": {"objectType": "Agent", "name": "Lou Wolford", "account": {"homePage": "http://example.com", "name": "louUniqueName"}},
                           "verb": {"id": "http://example.com/verbs/helped", "display": {"en-US": "helped", "en-GB": "assisted"}},
                           "object": {"objectType": "Agent", "name": "Tom Creighton", "mbox_sha1sum": msha},
                           "result": {"score": {"scaled": .85, "raw": 85, "min": 0, "max": 100}, "completion": True, "success": True, "response": "Well done",
                                      "duration": "P3Y6M4DT12H30M5S", "extensions": {"ext:resultKey1": "resultValue1", "ext:resultKey2": "resultValue2"}},
                           "context": {"registration": context_id, "contextActivities": {"other": {"id": "http://example.adlnet.gov/tincan/example/test"}},
                                       "language": "en-US",
                                       "statement": {"objectType": "StatementRef", "id": str(nested_st_id)},
                                       "extensions": {"ext:contextKey1": "contextVal1", "ext:contextKey2": "contextVal2"}},
                           "timestamp": self.firstTime})

        put_stmt = self.client.put(path, stmt, content_type="application/json",
                                   Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(put_stmt.status_code, 204)
        get_response = self.client.get(
            path, X_Experience_API_Version=settings.XAPI_VERSION, Authorization=self.auth)

        the_returned = json.loads(get_response.content)
        self.assertEqual(the_returned['id'], stmt_id)
        self.assertEqual(the_returned['actor']['objectType'], 'Agent')
        self.assertEqual(the_returned['actor']['name'], 'Lou Wolford')
        self.assertEqual(the_returned['actor']['account'][
                         'name'], 'louUniqueName')
        self.assertEqual(the_returned['actor']['account'][
                         'homePage'], 'http://example.com')

        self.assertEqual(the_returned['verb']['id'],
                         'http://example.com/verbs/helped')
        self.assertEqual(the_returned['verb']['display']['en-GB'], 'assisted')
        self.assertEqual(the_returned['verb']['display']['en-US'], 'helped')

        self.assertEqual(the_returned['result']['completion'], True)
        self.assertEqual(the_returned['result'][
                         'duration'], 'P3Y6M4DT12H30M5S')
        self.assertEqual(the_returned['result']['extensions'][
                         'ext:resultKey1'], 'resultValue1')
        self.assertEqual(the_returned['result']['extensions'][
                         'ext:resultKey2'], 'resultValue2')
        self.assertEqual(the_returned['result']['response'], 'Well done')
        self.assertEqual(the_returned['result']['score']['max'], 100)
        self.assertEqual(the_returned['result']['score']['min'], 0)
        self.assertEqual(the_returned['result']['score']['raw'], 85)
        self.assertEqual(the_returned['result']['score']['scaled'], 0.85)
        self.assertEqual(the_returned['result']['success'], True)

        self.assertEqual(the_returned['context']['contextActivities']['other'][0][
                         'id'], 'http://example.adlnet.gov/tincan/example/test')
        self.assertEqual(the_returned['context']['extensions'][
                         'ext:contextKey1'], 'contextVal1')
        self.assertEqual(the_returned['context']['extensions'][
                         'ext:contextKey2'], 'contextVal2')
        self.assertEqual(the_returned['context']['language'], 'en-US')
        self.assertEqual(the_returned['context']['registration'], context_id)
        self.assertEqual(the_returned['context']['statement'][
                         'id'], str(nested_st_id))
        self.assertEqual(the_returned['context']['statement'][
                         'objectType'], 'StatementRef')
        self.assertEqual(the_returned['object']['objectType'], 'Agent')
        self.assertEqual(the_returned['object']['name'], 'Tom Creighton')
        self.assertEqual(the_returned['object'][
                         'mbox_sha1sum'], 'edb97c2848fc47bdd2091028de8a3b1b24933752')

    # Use this test to make sure stmts are being returned correctly with all
    # data - doesn't check timestamps or stored fields
    def test_all_fields_substatement_as_object(self):
        nested_st_id = str(uuid.uuid1())
        nest_param = {"statementId": nested_st_id}
        nest_path = "%s?%s" % (reverse('lrs:statements'),
                               urllib.parse.urlencode(nest_param))
        nested_stmt = json.dumps({"actor": {"objectType": "Agent", "mbox": "mailto:tincannest@adlnet.gov"},
                                  "verb": {"id": "http://example.com/verbs/assess", "display": {"en-US": "assessed", "en-GB": "graded"}},
                                  "object": {"id": "http://example.adlnet.gov/tincan/example/simplestatement"}})
        put_sub_stmt = self.client.put(nest_path, nested_stmt, content_type="application/json",
                                       Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(put_sub_stmt.status_code, 204)

        nested_sub_st_id = str(uuid.uuid1())
        nest_sub_param = {"statementId": nested_sub_st_id}
        nest_sub_path = "%s?%s" % (
            reverse('lrs:statements'), urllib.parse.urlencode(nest_sub_param))
        nested_sub_stmt = json.dumps({"actor": {"objectType": "Agent", "mbox": "mailto:tincannestsub@adlnet.gov"},
                                      "verb": {"id": "http://example.com/verbs/verb", "display": {"en-US": "verb", "en-GB": "altVerb"}},
                                      "object": {"id": "http://example.adlnet.gov/tincan/example/simplenestedsubstatement"}})
        put_nest_sub_stmt = self.client.put(nest_sub_path, nested_sub_stmt, content_type="application/json",
                                            Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(put_nest_sub_stmt.status_code, 204)

        stmt_id = str(uuid.uuid1())
        context_id = str(uuid.uuid1())
        sub_context_id = str(uuid.uuid1())
        param = {"statementId": stmt_id}
        path = "%s?%s" % (reverse('lrs:statements'), urllib.parse.urlencode(param))

        stmt = json.dumps({"actor": {"objectType": "Agent", "name": "Lou Wolford", "account": {"homePage": "http://example.com", "name": "louUniqueName"}},
                           "verb": {"id": "http://example.com/verbs/said", "display": {"en-US": "said", "en-GB": "talked"}},
                           "object": {"objectType": "SubStatement", "actor": {"objectType": "Agent", "name": "Tom Creighton", "mbox": "mailto:tom@adlnet.gov"},
                                      "verb": {"id": "http://example.com/verbs/assess", "display": {"en-US": "assessed", "en-GB": "Graded"}},
                                      "object": {"id": "http://example.adlnet.gov/tincan/example/simplestatement",
                                                 'definition': {'name': {'en-US': 'SubStatement name'},
                                                                'description': {'en-US': 'SubStatement description'},
                                                                'type': 'http://adlnet.gov/expapi/activities/cmi.interaction', 'interactionType': 'matching',
                                                                'correctResponsesPattern': ['lou.3,tom.2,andy.1'], 'source': [{'id': 'lou',
                                                                                                                               'description': {'en-US': 'Lou', 'it': 'Luigi'}}, {'id': 'tom', 'description': {'en-US': 'Tom', 'it': 'Tim'}},
                                                                                                                              {'id': 'andy', 'description': {'en-US': 'Andy'}}], 'target': [{'id': '1',
                                                                                                                                                                                             'description': {'en-US': 'ADL LRS'}}, {'id': '2', 'description': {'en-US': 'lrs'}},
                                                                                                                                                                                            {'id': '3', 'description': {'en-US': 'the adl lrs', 'en-CH': 'the lrs'}}]}},
                                      "result": {"score": {"scaled": .50, "raw": 50, "min": 1, "max": 51}, "completion": True,
                                                 "success": True, "response": "Poorly done",
                                                 "duration": "P3Y6M4DT12H30M5S", "extensions": {"ext:resultKey11": "resultValue11", "ext:resultKey22": "resultValue22"}},
                                      "context": {"registration": sub_context_id,
                                                  "contextActivities": {"other": {"id": "http://example.adlnet.gov/tincan/example/test/nest"}},
                                                  "language": "en-US",
                                                  "statement": {"objectType": "StatementRef", "id": str(nested_sub_st_id)},
                                                  "extensions": {"ext:contextKey11": "contextVal11", "ext:contextKey22": "contextVal22"}}},
                           "result": {"score": {"scaled": .85, "raw": 85, "min": 0, "max": 100}, "completion": True, "success": True, "response": "Well done",
                                      "duration": "P3Y6M4DT12H30M5S", "extensions": {"ext:resultKey1": "resultValue1", "ext:resultKey2": "resultValue2"}},
                           "context": {"registration": context_id, "contextActivities": {"other": {"id": "http://example.adlnet.gov/tincan/example/test"}},
                                       "language": "en-US",
                                       "statement": {"objectType": "StatementRef", "id": str(nested_st_id)},
                                       "extensions": {"ext:contextKey1": "contextVal1", "ext:contextKey2": "contextVal2"}},
                           "timestamp": self.firstTime})
        put_stmt = self.client.put(path, stmt, content_type="application/json",
                                   Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)

        self.assertEqual(put_stmt.status_code, 204)
        get_response = self.client.get(
            path, X_Experience_API_Version=settings.XAPI_VERSION, Authorization=self.auth)

        the_returned = json.loads(get_response.content)
        self.assertEqual(the_returned['id'], stmt_id)
        self.assertEqual(the_returned['actor']['objectType'], 'Agent')
        self.assertEqual(the_returned['actor']['name'], 'Lou Wolford')
        self.assertEqual(the_returned['actor']['account'][
                         'name'], 'louUniqueName')
        self.assertEqual(the_returned['actor']['account'][
                         'homePage'], 'http://example.com')

        self.assertEqual(the_returned['verb']['id'],
                         'http://example.com/verbs/said')
        self.assertEqual(the_returned['verb']['display']['en-GB'], 'talked')
        self.assertEqual(the_returned['verb']['display']['en-US'], 'said')

        self.assertEqual(the_returned['object'][
                         'actor']['objectType'], 'Agent')
        self.assertEqual(the_returned['object']['actor'][
                         'name'], 'Tom Creighton')
        self.assertEqual(the_returned['object']['actor'][
                         'mbox'], 'mailto:tom@adlnet.gov')

        self.assertEqual(the_returned['object']['context'][
                         'registration'], sub_context_id)
        self.assertEqual(the_returned['object'][
                         'context']['language'], 'en-US')
        self.assertEqual(the_returned['object']['context'][
                         'statement']['id'], str(nested_sub_st_id))
        self.assertEqual(the_returned['object']['context'][
                         'statement']['objectType'], 'StatementRef')
        self.assertEqual(the_returned['object']['context']['contextActivities']['other'][
                         0]['id'], 'http://example.adlnet.gov/tincan/example/test/nest')
        self.assertEqual(the_returned['object']['context']['extensions'][
                         'ext:contextKey11'], 'contextVal11')
        self.assertEqual(the_returned['object']['context']['extensions'][
                         'ext:contextKey22'], 'contextVal22')
        self.assertEqual(the_returned['object']['object'][
                         'id'], 'http://example.adlnet.gov/tincan/example/simplestatement')
        self.assertEqual(the_returned['object']['object']['definition'][
                         'type'], 'http://adlnet.gov/expapi/activities/cmi.interaction')
        self.assertEqual(the_returned['object']['object']['definition'][
                         'description']['en-US'], 'SubStatement description')
        self.assertEqual(the_returned['object']['object'][
                         'definition']['interactionType'], 'matching')
        self.assertEqual(the_returned['object']['object']['definition'][
                         'name']['en-US'], 'SubStatement name')
        # arrays.. testing slightly differently
        source_str = json.dumps(the_returned['object']['object'][
                                'definition']['source'])
        self.assertIn('description', source_str)
        self.assertIn('id', source_str)
        self.assertIn('Lou', source_str)
        self.assertIn('Luigi', source_str)
        self.assertIn('lou', source_str)
        self.assertIn('Tom', source_str)
        self.assertIn('Tim', source_str)
        self.assertIn('tom', source_str)
        self.assertIn('Andy', source_str)
        self.assertIn('andy', source_str)

        target_str = json.dumps(the_returned['object']['object'][
                                'definition']['target'])
        self.assertIn('description', target_str)
        self.assertIn('id', target_str)
        self.assertIn('ADL LRS', target_str)
        self.assertIn('1', target_str)
        self.assertIn('lrs', target_str)
        self.assertIn('2', target_str)
        self.assertIn('the lrs', target_str)
        self.assertIn('the adl lrs', target_str)
        self.assertIn('3', target_str)

        self.assertEqual(the_returned['object']['objectType'], 'SubStatement')

        self.assertEqual(the_returned['object']['result']['completion'], True)
        self.assertEqual(the_returned['object']['result'][
                         'duration'], 'P3Y6M4DT12H30M5S')
        self.assertEqual(the_returned['object']['result']['extensions'][
                         'ext:resultKey11'], 'resultValue11')
        self.assertEqual(the_returned['object']['result']['extensions'][
                         'ext:resultKey22'], 'resultValue22')
        self.assertEqual(the_returned['object']['result'][
                         'response'], 'Poorly done')
        self.assertEqual(the_returned['object']['result']['score']['max'], 51)
        self.assertEqual(the_returned['object']['result']['score']['min'], 1)
        self.assertEqual(the_returned['object']['result']['score']['raw'], 50)
        self.assertEqual(the_returned['object']['result'][
                         'score']['scaled'], 0.5)
        self.assertEqual(the_returned['object']['result']['success'], True)

        self.assertEqual(the_returned['object']['verb'][
                         'id'], 'http://example.com/verbs/assess')
        self.assertEqual(the_returned['object']['verb'][
                         'display']['en-GB'], 'Graded')
        self.assertEqual(the_returned['object']['verb'][
                         'display']['en-US'], 'assessed')

        self.assertEqual(the_returned['result']['completion'], True)
        self.assertEqual(the_returned['result'][
                         'duration'], 'P3Y6M4DT12H30M5S')
        self.assertEqual(the_returned['result']['extensions'][
                         'ext:resultKey1'], 'resultValue1')
        self.assertEqual(the_returned['result']['extensions'][
                         'ext:resultKey2'], 'resultValue2')
        self.assertEqual(the_returned['result']['response'], 'Well done')
        self.assertEqual(the_returned['result']['score']['max'], 100)
        self.assertEqual(the_returned['result']['score']['min'], 0)
        self.assertEqual(the_returned['result']['score']['raw'], 85)
        self.assertEqual(the_returned['result']['score']['scaled'], 0.85)
        self.assertEqual(the_returned['result']['success'], True)

        self.assertEqual(the_returned['context']['contextActivities']['other'][0][
                         'id'], 'http://example.adlnet.gov/tincan/example/test')
        self.assertEqual(the_returned['context']['extensions'][
                         'ext:contextKey1'], 'contextVal1')
        self.assertEqual(the_returned['context']['extensions'][
                         'ext:contextKey2'], 'contextVal2')
        self.assertEqual(the_returned['context']['language'], 'en-US')
        self.assertEqual(the_returned['context']['registration'], context_id)
        self.assertEqual(the_returned['context'][
                         'statement']['id'], nested_st_id)
        self.assertEqual(the_returned['context']['statement'][
                         'objectType'], 'StatementRef')

    # Third stmt in list is missing actor - should throw error and perform
    # cascading delete on first three statements
    def test_post_list_rollback(self):
        cguid1 = str(uuid.uuid1())

        stmts = json.dumps([{"verb": {"id": "http://example.com/verbs/wrong-failed", "display": {"en-US": "wrong-failed"}}, "object": {"id": "act:test_wrong_list_post2"},
                             "actor": {"objectType": "Agent", "mbox": "mailto:wrong-t@t.com"}, "result": {"score": {"scaled": .99}, "completion": True, "success": True, "response": "wrong",
                                                                                                          "extensions": {"ext:resultwrongkey1": "value1", "ext:resultwrongkey2": "value2"}}},
                            {"verb": {"id": "http://example.com/verbs/wrong-kicked", "display": {"en-US": "wrong-kicked"}},
                             "object": {"objectType": "Activity", "id": "act:test_wrong_list_post",
                                        "definition": {"name": {"en-US": "wrongactName", "en-GB": "anotherActName"},
                                                       "description": {"en-US": "This is my activity description.", "en-GB": "This is another activity description."},
                                                       "type": "http://adlnet.gov/expapi/activities/http://adlnet.gov/expapi/activities/cmi.interaction",
                                                       "interactionType": "choice",
                                                       "correctResponsesPattern": ["wronggolf", "wrongtetris"],
                                                       "choices":[{"id": "wronggolf", "description": {"en-US": "Golf Example", "en-GB": "GOLF"}},
                                                                  {"id": "wrongtetris", "description": {
                                                                      "en-US": "Tetris Example", "en-GB": "TETRIS"}},
                                                                  {"id": "wrongfacebook", "description": {
                                                                      "en-US": "Facebook App", "en-GB": "FACEBOOK"}},
                                                                  {"id": "wrongscrabble", "description": {"en-US": "Scrabble Example", "en-GB": "SCRABBLE"}}],
                                                       "extensions": {"ext:wrongkey1": "wrongvalue1", "ext:wrongkey2": "wrongvalue2", "ext:wrongkey3": "wrongvalue3"}}},
                             "actor": {"objectType": "Agent", "mbox": "mailto:wrong-t@t.com"}},
                            {"verb": {"id": "http://example.com/verbs/wrong-passed", "display": {"en-US": "wrong-passed"}}, "object": {"id": "act:test_wrong_list_post1"},
                             "actor": {"objectType": "Agent", "mbox": "mailto:wrong-t@t.com"}, "context": {"registration": cguid1, "contextActivities": {"other": {"id": "act:wrongActivityID2"}},
                                                                                                           "revision": "wrong", "platform": "wrong", "language": "en-US", "extensions": {"ext:wrongkey1": "wrongval1",
                                                                                                                                                                                         "ext:wrongkey2": "wrongval2"}}},
                            {"verb": {"id": "http://example.com/verbs/wrong-kicked", "display": {
                                "en-US": "wrong-kicked"}}, "object": {"id": "act:test_wrong_list_post2"}},
                            {"verb": {"id": "http://example.com/verbs/wrong-kicked", "display": {"en-US": "wrong-kicked"}}, "object": {"id": "act:test_wrong_list_post4"}, "actor": {"objectType": "Agent", "mbox": "wrong-t@t.com"}}])

        response = self.client.post(reverse('lrs:statements'), stmts, content_type="application/json",
                                    Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(response.status_code, 400)
        self.assertIn('actor is missing in Statement', response.content)

        verbs = Verb.objects.filter(verb_id__contains='wrong')

        activities = Activity.objects.filter(
            activity_id__contains='test_wrong_list_post')

        stmts = Statement.objects.all()

        # 11 statements from setup
        self.assertEqual(len(stmts), 11)

        self.assertEqual(len(verbs), 0)
        self.assertEqual(len(activities), 0)

    def test_post_list_rollback_part_2(self):
        stmts = json.dumps([{"object": {"objectType": "Agent", "name": "john", "mbox": "mailto:john@john.com"},
                             "verb": {"id": "http://example.com/verbs/wrong", "display": {"en-US": "wrong"}},
                             "actor": {"objectType": "Agent", "mbox": "mailto:s@s.com"}},
                            {"verb": {"id": "http://example.com/verbs/created"},
                             "object": {"objectType": "Activity", "id": "act:foogie",
                                        "definition": {"name": {"en-US": "testname2", "en-GB": "altname"},
                                                       "description": {"en-US": "testdesc2", "en-GB": "altdesc"}, "type": "http://adlnet.gov/expapi/activities/cmi.interaction",
                                                       "interactionType": "fill-in", "correctResponsesPattern": ["answer"]}},
                             "actor":{"objectType": "Agent", "mbox": "mailto:wrong-t@t.com"}},
                            {"verb": {"id": "http://example.com/verbs/wrong-kicked"}, "object": {"id": "act:test_wrong_list_post2"}}])

        response = self.client.post(reverse('lrs:statements'), stmts, content_type="application/json",
                                    Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(response.status_code, 400)
        self.assertIn('actor is missing in Statement', response.content)
        created_verbs = Verb.objects.filter(
            verb_id__contains='http://example.com/verbs/created')
        wrong_verbs = Verb.objects.filter(
            verb_id__contains='http://example.com/verbs/wrong')

        activities = Activity.objects.filter(activity_id='act:foogie')

        stmts = Statement.objects.all()

        wrong_agent = Agent.objects.filter(mbox='mailto:wrong-t@t.com')
        john_agent = Agent.objects.filter(mbox='mailto:john@john.com')
        s_agent = Agent.objects.filter(mbox='mailto:s@s.com')
        auth_agent = Agent.objects.filter(mbox='mailto:test1@tester.com')

        self.assertEqual(len(created_verbs), 1)
        # Both verbs from the first and last stmts in the list would still be
        # there
        self.assertEqual(len(wrong_verbs), 0)

        self.assertEqual(len(activities), 1)

        self.assertEqual(len(stmts), 11)

        self.assertEqual(len(wrong_agent), 0)
        self.assertEqual(len(john_agent), 1)
        self.assertEqual(len(s_agent), 1)
        self.assertEqual(len(auth_agent), 0)

    def test_post_list_rollback_with_void(self):
        stmts = json.dumps([{"actor": {"objectType": "Agent", "mbox": "mailto:only-s@s.com"},
                             "object": {"objectType": "StatementRef", "id": str(self.exist_stmt_id)},
                             "verb": {"id": "http://adlnet.gov/expapi/verbs/voided", "display": {"en-US": "voided"}}},
                            {"verb": {"id": "http://example.com/verbs/wrong-kicked"}, "object": {"id": "act:test_wrong_list_post2"}}])

        response = self.client.post(reverse('lrs:statements'), stmts, content_type="application/json",
                                    Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(response.status_code, 400)
        self.assertIn('actor is missing in Statement', response.content)

        voided_st = Statement.objects.get(statement_id=str(self.exist_stmt_id))
        voided_verb = Verb.objects.filter(verb_id__contains='voided')
        only_actor = Agent.objects.filter(mbox="mailto:only-s@s.com")
        stmts = Statement.objects.all()

        self.assertEqual(len(stmts), 11)
        self.assertEqual(voided_st.voided, False)
        self.assertEqual(len(voided_verb), 0)
        self.assertEqual(len(only_actor), 0)

    def test_post_list_rollback_with_subs(self):
        sub_context_id = str(uuid.uuid1())
        stmts = json.dumps([{"actor": {"objectType": "Agent", "mbox": "mailto:wrong-s@s.com"},
                             "verb": {"id": "http://example.com/verbs/wrong", "display": {"en-US": "wrong"}},
                             "object": {"objectType": "Agent", "name": "john", "mbox": "mailto:john@john.com"}},
                            {"actor": {"objectType": "Agent", "mbox": "mailto:s@s.com"},
                             "verb": {"id": "http://example.com/verbs/wrong-next", "display": {"en-US": "wrong-next"}},
                             "object": {"objectType": "SubStatement",
                                        "actor": {"objectType": "Agent", "mbox": "mailto:wrong-ss@ss.com"}, "verb": {"id": "http://example.com/verbs/wrong-sub"},
                                        "object": {"objectType": "Activity", "id": "act:wrong-testex.com"}, "result": {"completion": True, "success": True,
                                                                                                                       "response": "sub-wrong-kicked"}, "context": {"registration": sub_context_id,
                                                                                                                                                                    "contextActivities": {"other": {"id": "act:sub-wrong-ActivityID"}}, "revision": "foo", "platform": "bar",
                                                                                                                                                                    "language": "en-US", "extensions": {"ext:wrong-k1": "v1", "ext:wrong-k2": "v2"}}}},
                            {"verb": {"id": "http://example.com/verbs/wrong-kicked"}, "object": {"id": "act:test_wrong_list_post2"}}])

        response = self.client.post(reverse('lrs:statements'), stmts, content_type="application/json",
                                    Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(response.status_code, 400)
        self.assertIn('actor is missing in Statement', response.content)

        s_agent = Agent.objects.filter(mbox="mailto:wrong-s@s.com")
        ss_agent = Agent.objects.filter(mbox="mailto:wrong-ss@ss.com")
        john_agent = Agent.objects.filter(mbox="mailto:john@john.com")
        subs = SubStatement.objects.all()
        wrong_verb = Verb.objects.filter(verb_id__contains="wrong")
        activities = Activity.objects.filter(activity_id__contains="wrong")
        stmts = Statement.objects.all()

        self.assertEqual(len(stmts), 11)
        self.assertEqual(len(s_agent), 0)
        self.assertEqual(len(ss_agent), 0)
        self.assertEqual(len(john_agent), 1)
        # Only 1 sub from setup
        self.assertEqual(len(subs), 1)
        self.assertEqual(len(wrong_verb), 0)
        self.assertEqual(len(activities), 0)

    def test_activity_definition_change(self):
        username_1 = "tester1"
        email_1 = "test1@tester.com"
        password_1 = "test"
        auth_1 = "Basic %s" % base64.b64encode(
            "%s:%s" % (username_1, password_1))
        form_1 = {"username": username_1, "email": email_1,
                  "password": password_1, "password2": password_1}
        response_1 = self.client.post(
            reverse(register), form_1, X_Experience_API_Version=settings.XAPI_VERSION)

        username_2 = "tester2"
        email_2 = "test2@tester.com"
        password_2 = "test2"
        auth_2 = "Basic %s" % base64.b64encode(
            "%s:%s" % (username_2, password_2))
        form_2 = {"username": username_2, "email": email_2,
                  "password": password_2, "password2": password_2}
        response_2 = self.client.post(
            reverse(register), form_2, X_Experience_API_Version=settings.XAPI_VERSION)

        # Should have no definition
        stmt_1 = json.dumps({"actor": {"objectType": "Agent", "name": "max", "mbox": "mailto:max@max.com"},
                             "object": {"id": "act:test_activity_change"},
                             "verb": {"id": "http://example.com/verbs/created", "display": {"en-US": "created"}}})
        response_1 = self.client.post(reverse('lrs:statements'), stmt_1, content_type="application/json",
                                      Authorization=auth_1, X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(response_1.status_code, 200)
        user1_agent = Agent.objects.get(mbox="mailto:test1@tester.com")
        act = Activity.objects.get(
            activity_id="act:test_activity_change").return_activity_with_lang_format()
        self.assertEqual(act["id"], "act:test_activity_change")
        with self.assertRaises(KeyError):
            act["definition"]
        acts = Activity.objects.filter(
            activity_id="act:test_activity_change").count()
        self.assertEqual(acts, 1)

        # Does not update existing activity
        stmt_2 = json.dumps({"actor": {"objectType": "Agent", "name": "max", "mbox": "mailto:max@max.com"},
                             "object": {"id": "act:test_activity_change", "definition": {"name": {"en-US": "fail_test"}}},
                             "verb": {"id": "http://example.com/verbs/created", "display": {"en-US": "created"}}})
        response_2 = self.client.post(reverse('lrs:statements'), stmt_2, content_type="application/json",
                                      Authorization=auth_2, X_Experience_API_Version=settings.XAPI_VERSION)
        user2_agent = Agent.objects.get(mbox="mailto:test2@tester.com")
        self.assertEqual(response_2.status_code, 200)
        with self.assertRaises(Activity.DoesNotExist):
            Activity.objects.get(activity_id="act:test_activity_change",
                                 authority=user2_agent).return_activity_with_lang_format()

        acts = Activity.objects.filter(activity_id="act:test_activity_change")
        self.assertEqual(acts.count(), 1)
        with self.assertRaises(KeyError):
            acts[0].return_activity_with_lang_format()["definition"]

        # Should not update activity
        response_3 = self.client.post(reverse('lrs:statements'), stmt_1, content_type="application/json",
                                      Authorization=auth_2, X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(response_3.status_code, 200)
        act = Activity.objects.get(
            activity_id="act:test_activity_change").return_activity_with_lang_format()
        self.assertEqual(act["id"], "act:test_activity_change")
        with self.assertRaises(KeyError):
            act["definition"]
        acts = Activity.objects.filter(
            activity_id="act:test_activity_change").count()
        self.assertEqual(acts, 1)

        # Should have new definition since user is owner
        stmt_3 = json.dumps({"actor": {"objectType": "Agent", "name": "max", "mbox": "mailto:max@max.com"},
                             "object": {"id": "act:test_activity_change", "definition": {"name": {"en-US": "foo"}}},
                             "verb": {"id": "http://example.com/verbs/created", "display": {"en-US": "created"}}})
        response_4 = self.client.post(reverse('lrs:statements'), stmt_3, content_type="application/json",
                                      Authorization=auth_1, X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(response_4.status_code, 200)
        act = Activity.objects.get(activity_id="act:test_activity_change",
                                   authority=user1_agent).return_activity_with_lang_format()
        self.assertEqual(act["id"], "act:test_activity_change")
        self.assertEqual(act["definition"], {"name": {"en-US": "foo"}})

        # Should still have definition from above
        response_5 = self.client.post(reverse('lrs:statements'), stmt_3, content_type="application/json",
                                      Authorization=auth_2, X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(response_5.status_code, 200)
        act = Activity.objects.get(
            activity_id="act:test_activity_change").return_activity_with_lang_format()
        self.assertEqual(act["id"], "act:test_activity_change")
        self.assertEqual(act["definition"], {"name": {"en-US": "foo"}})
        acts = Activity.objects.filter(
            activity_id="act:test_activity_change").count()
        self.assertEqual(acts, 1)

        # Should still have definition from above
        stmt_4 = json.dumps({"actor": {"objectType": "Agent", "name": "max", "mbox": "mailto:max@max.com"},
                             "object": {"id": "act:test_activity_change", "definition": {"name": {"en-US": "bar"}}},
                             "verb": {"id": "http://example.com/verbs/created", "display": {"en-US": "created"}}})
        response_6 = self.client.post(reverse('lrs:statements'), stmt_4, content_type="application/json",
                                      Authorization=auth_2, X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(response_6.status_code, 200)
        act = Activity.objects.get(
            activity_id="act:test_activity_change").return_activity_with_lang_format()
        self.assertEqual(act["id"], "act:test_activity_change")
        self.assertEqual(act["definition"], {"name": {"en-US": "foo"}})
        acts = Activity.objects.filter(
            activity_id="act:test_activity_change").count()
        self.assertEqual(acts, 1)

        # Should still have definition from above
        stmt_5 = json.dumps({"actor": {"objectType": "Agent", "name": "max", "mbox": "mailto:max@max.com"},
                             "object": {"id": "act:test_activity_change", "definition": {"name": {"fr": "bar"}}},
                             "verb": {"id": "http://example.com/verbs/created", "display": {"en-US": "created"}}})
        response_7 = self.client.post(reverse('lrs:statements'), stmt_5, content_type="application/json",
                                      Authorization=auth_2, X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(response_7.status_code, 200)
        act = Activity.objects.get(
            activity_id="act:test_activity_change").return_activity_with_lang_format()
        self.assertEqual(act["id"], "act:test_activity_change")
        self.assertNotIn("fr", act['definition']['name'])
        acts = Activity.objects.filter(
            activity_id="act:test_activity_change").count()
        self.assertEqual(acts, 1)

        # Should still have definition from above
        response_8 = self.client.post(reverse('lrs:statements'), stmt_1, content_type="application/json",
                                      Authorization=auth_2, X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(response_8.status_code, 200)
        act = Activity.objects.get(
            activity_id="act:test_activity_change").return_activity_with_lang_format()
        self.assertEqual(act["id"], "act:test_activity_change")
        self.assertIn("definition", list(act.keys()))
        acts = Activity.objects.filter(
            activity_id="act:test_activity_change").count()
        self.assertEqual(acts, 1)

        # Check canonical of last stmt returned from query to make sure it
        # contains the definition
        param = {"agent": {"mbox": "mailto:max@max.com"},
                 "format": "canonical", "activity": "act:test_activity_change"}
        path = "%s?%s" % (reverse('lrs:statements'), urllib.parse.urlencode(param))
        r = self.client.get(
            path, X_Experience_API_Version="1.0", Authorization=auth_1)
        self.assertEqual(r.status_code, 200)
        first_stmt = json.loads(r.content)["statements"][0]
        self.assertEqual(first_stmt["object"]["definition"], {
                         "name": {"en-US": "foo"}})

    def test_post_with_non_oauth_not_existing_group(self):
        ot = "Group"
        name = "the group ST"
        mbox = "mailto:the.groupST@example.com"
        stmt = json.dumps({"actor": {"name": "agentA", "mbox": "mailto:agentA@example.com"}, "verb": {"id": "http://verb/iri/joined", "display": {"en-US": "joined"}},
                           "object": {"id": "act:i.pity.the.fool"}, "authority": {"objectType": ot, "name": name, "mbox": mbox, "member": [{"name": "agentA", "mbox": "mailto:agentA@example.com"}, {"name": "agentB", "mbox": "mailto:agentB@example.com"}]}})

        response = self.client.post(reverse('lrs:statements'), stmt, content_type="application/json",
                                    Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(response.status_code, 400)

    def test_post_with_non_oauth_existing_group(self):
        ot = "Group"
        name = "the group ST"
        mbox = "mailto:the.groupST@example.com"
        group = {"objectType": ot, "name": name, "mbox": mbox, "member": [
            {"name": "agentA", "mbox": "mailto:agentA@example.com"}, {"name": "agentB", "mbox": "mailto:agentB@example.com"}]}
        Agent.objects.retrieve_or_create(**group)

        stmt = json.dumps({"actor": {"name": "agentA", "mbox": "mailto:agentA@example.com"}, "verb": {"id": "http://verb/iri/joined", "display": {"en-US": "joined"}},
                           "object": {"id": "act:i.pity.the.fool"}, "authority": {"objectType": ot, "name": name, "mbox": mbox, "member": [{"name": "agentA", "mbox": "mailto:agentA@example.com"}, {"name": "agentB", "mbox": "mailto:agentB@example.com"}]}})

        response = self.client.post(reverse('lrs:statements'), stmt, content_type="application/json",
                                    Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(response.status_code, 400)

    def test_interaction_activity_update(self):
        username_1 = "tester1"
        email_1 = "test1@tester.com"
        password_1 = "test"
        auth_1 = "Basic %s" % base64.b64encode(
            "%s:%s" % (username_1, password_1))
        form_1 = {"username": username_1, "email": email_1,
                  "password": password_1, "password2": password_1}
        response_1 = self.client.post(
            reverse(register), form_1, X_Experience_API_Version=settings.XAPI_VERSION)

        username_2 = "tester2"
        email_2 = "test2@tester.com"
        password_2 = "test2"
        auth_2 = "Basic %s" % base64.b64encode(
            "%s:%s" % (username_2, password_2))
        form_2 = {"username": username_2, "email": email_2,
                  "password": password_2, "password2": password_2}
        response_2 = self.client.post(
            reverse(register), form_2, X_Experience_API_Version=settings.XAPI_VERSION)

        st = json.dumps({"actor": {"objectType": "Agent", "mbox": "mailto:tom@adlnet.gov"},
                         "verb": {"id": "http://example.com/verbs/assess"},
                         "object": {'objectType': 'Activity', 'id': 'http://example/intupdate',
                                    'definition': {'name': {'en-US': 'testname2'}, 'description': {'en-US': 'testdesc2'},
                                                   'type': 'http://adlnet.gov/expapi/activities/cmi.interaction', 'interactionType': 'likert', 'correctResponsesPattern': ['likert_3'],
                                                   'scale': [{'id': 'likert_0', 'description': {'en-US': 'Its OK'}},
                                                             {'id': 'likert_1', 'description': {
                                                                 'en-US': 'Its Pretty Cool'}},
                                                             {'id': 'likert_2', 'description': {
                                                                 'en-US': 'Its Cool Cool'}},
                                                             {'id': 'likert_3', 'description': {'en-US': 'Its Gonna Change the World'}}]}}})
        st_post = self.client.post(reverse('lrs:statements'), st, content_type="application/json", Authorization=auth_1,
                                   X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(st_post.status_code, 200)

        act = Activity.objects.get(activity_id="http://example/intupdate")
        self.assertIn('scale', act.canonical_data['definition'])
        scale_ids = [s['id']
                     for s in act.canonical_data['definition']['scale']]
        self.assertIn('likert_0', scale_ids)
        self.assertIn('likert_1', scale_ids)
        self.assertIn('likert_2', scale_ids)
        self.assertIn('likert_3', scale_ids)
        scale_descs = [s['description']
                       for s in act.canonical_data['definition']['scale']]
        scale_desc_keys = list(set().union(*(list(d.keys()) for d in scale_descs)))
        scale_desc_values = list(set().union(
            *(list(d.values()) for d in scale_descs)))
        self.assertEqual(len(scale_descs), 4)
        self.assertIn('en-US', scale_desc_keys)
        self.assertIn('Its OK', scale_desc_values)
        self.assertIn('Its Pretty Cool', scale_desc_values)
        self.assertIn('Its Cool Cool', scale_desc_values)
        self.assertIn('Its Gonna Change the World', scale_desc_values)

        st = json.dumps({"actor": {"objectType": "Agent", "mbox": "mailto:tom@adlnet.gov"},
                         "verb": {"id": "http://example.com/verbs/assess"},
                         "object": {'objectType': 'Activity', 'id': 'http://example/intupdate',
                                    'definition': {'name': {'en-US': 'testname2'}, 'description': {'en-US': 'testdesc2'},
                                                   'type': 'http://adlnet.gov/expapi/activities/cmi.interaction', 'interactionType': 'likert', 'correctResponsesPattern': ['likert_3'],
                                                   'scale': [{'id': 'likert_0', 'description': {'en-US': 'Its OK'}},
                                                             {'id': 'likert_1', 'description': {
                                                                 'en-US': 'Its Pretty Coolio'}},
                                                             {'id': 'likert_3', 'description': {'en-UK': 'Its Gonna Be Great'}}]}}})
        st_post = self.client.post(reverse('lrs:statements'), st, content_type="application/json", Authorization=auth_2,
                                   X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(st_post.status_code, 200)

        # Shouldn't change, doesn't have permission
        act = Activity.objects.get(activity_id="http://example/intupdate")
        self.assertIn('scale', act.canonical_data['definition'])
        scale_ids = [s['id']
                     for s in act.canonical_data['definition']['scale']]
        self.assertIn('likert_0', scale_ids)
        self.assertIn('likert_1', scale_ids)
        self.assertIn('likert_2', scale_ids)
        self.assertIn('likert_3', scale_ids)
        scale_descs = [s['description']
                       for s in act.canonical_data['definition']['scale']]
        scale_desc_keys = list(set().union(*(list(d.keys()) for d in scale_descs)))
        scale_desc_values = list(set().union(
            *(list(d.values()) for d in scale_descs)))
        self.assertEqual(len(scale_descs), 4)
        self.assertIn('en-US', scale_desc_keys)
        self.assertIn('Its OK', scale_desc_values)
        self.assertIn('Its Pretty Cool', scale_desc_values)
        self.assertIn('Its Cool Cool', scale_desc_values)
        self.assertIn('Its Gonna Change the World', scale_desc_values)

        st = json.dumps({"actor": {"objectType": "Agent", "mbox": "mailto:tom@adlnet.gov"},
                         "verb": {"id": "http://example.com/verbs/assess"},
                         "object": {'objectType': 'Activity', 'id': 'http://example/intupdate',
                                    'definition': {'name': {'en-US': 'testname2'}, 'description': {'en-US': 'testdesc2'},
                                                   'type': 'http://adlnet.gov/expapi/activities/cmi.interaction', 'interactionType': 'likert', 'correctResponsesPattern': ['likert_3'],
                                                   'scale': [{'id': 'likert_0', 'description': {'en-US': 'Its OK'}},
                                                             {'id': 'likert_1', 'description': {
                                                                 'en-US': 'Its Pretty Coolio'}},
                                                             {'id': 'likert_3', 'description': {'en-UK': 'Its Gonna Be Great'}}]}}})
        st_post = self.client.post(reverse('lrs:statements'), st, content_type="application/json", Authorization=auth_1,
                                   X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(st_post.status_code, 200)

        # Should still keep same number of scales, only will update the
        # descriptions
        act = Activity.objects.get(activity_id="http://example/intupdate")
        self.assertIn('scale', act.canonical_data['definition'])
        scale_ids = [s['id']
                     for s in act.canonical_data['definition']['scale']]
        self.assertIn('likert_0', scale_ids)
        self.assertIn('likert_1', scale_ids)
        self.assertIn('likert_2', scale_ids)
        self.assertIn('likert_3', scale_ids)
        scale_descs = [s['description']
                       for s in act.canonical_data['definition']['scale']]
        scale_desc_keys = list(set().union(*(list(d.keys()) for d in scale_descs)))
        scale_desc_values = list(set().union(
            *(list(d.values()) for d in scale_descs)))
        self.assertEqual(len(scale_descs), 4)
        self.assertIn('en-US', scale_desc_keys)
        self.assertIn('en-UK', scale_desc_keys)
        self.assertIn('Its OK', scale_desc_values)
        self.assertIn('Its Pretty Coolio', scale_desc_values)
        self.assertIn('Its Cool Cool', scale_desc_values)
        self.assertIn('Its Gonna Be Great', scale_desc_values)
