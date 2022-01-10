# -*- coding: utf-8 -*-
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
from django.test.utils import override_settings

from ..models import Statement, Activity, Agent, Verb, SubStatement
from ..utils import retrieve_statement

from adl_lrs.views import register


class StatementTests(TestCase):

    @classmethod
    def setUpClass(cls):
        print("\n%s" % __name__)
        super(StatementTests, cls).setUpClass()

    def setUp(self):
        self.username = "tester1"
        self.email = "test1@tester.com"
        self.password = "test"
        self.auth = "Basic %s" % base64.b64encode(
            "%s:%s" % (self.username, self.password))
        form = {"username": self.username, "email": self.email,
                "password": self.password, "password2": self.password}
        self.client.post(reverse(register), form,
                         X_Experience_API_Version=settings.XAPI_VERSION)

        self.username2 = "tester2"
        self.email2 = "test2@tester.com"
        self.password2 = "test2"
        self.auth2 = "Basic %s" % base64.b64encode(
            "%s:%s" % (self.username2, self.password2))
        form2 = {"username": self.username2, "email": self.email2,
                 "password": self.password2, "password2": self.password2}
        self.client.post(reverse(register), form2,
                         X_Experience_API_Version=settings.XAPI_VERSION)

        self.firstTime = str(datetime.utcnow().replace(tzinfo=utc).isoformat())
        self.guid1 = uuid.uuid4()

    def bunchostmts(self):
        self.guid2 = uuid.uuid4()
        self.guid3 = uuid.uuid4()
        self.guid4 = uuid.uuid4()
        self.guid5 = uuid.uuid4()
        self.guid6 = uuid.uuid4()
        self.guid7 = uuid.uuid4()
        self.guid8 = uuid.uuid4()
        self.guid9 = uuid.uuid4()
        self.guid10 = str(uuid.uuid4())
        self.cguid1 = str(uuid.uuid4())
        self.cguid2 = str(uuid.uuid4())
        self.cguid3 = str(uuid.uuid4())
        self.cguid4 = str(uuid.uuid4())
        self.cguid5 = str(uuid.uuid4())
        self.cguid6 = str(uuid.uuid4())

        stmt = json.dumps({"verb": {"id": "http://example.com/verbs/created",
                                    "display": {"en-US": "created"}}, "object": {"id": "act:activity"},
                           "actor": {"objectType": "Agent", "mbox": "mailto:s@s.com"},
                           "authority": {"objectType": "Agent", "name": "tester1", "mbox": "mailto:test1@tester.com"}})
        response = self.client.post(reverse('lrs:statements'), stmt, content_type="application/json",
                                    Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(response.status_code, 200)
        stmt_id = uuid.UUID(json.loads(response.content)[0])
        self.existStmt = Statement.objects.get(statement_id=stmt_id)
        self.exist_stmt_id = self.existStmt.statement_id

        self.existStmt1 = json.dumps({"verb": {"id": "http://example.com/verbs/created",
                                               "display": {"en-US": "created"}}, "actor": {"objectType": "Agent", "mbox": "mailto:s@s.com"},
                                      "object": {"objectType": "Activity", "id": "act:foogie",
                                                 "definition": {"name": {"en-US": "testname2", "en-GB": "altname"},
                                                                "description": {"en-US": "testdesc2", "en-GB": "altdesc"}, "type": "http://www.adlnet.gov/experienceapi/activity-types/http://adlnet.gov/expapi/activities/cmi.interaction",
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
                                                                "description": {"en-US": "testdesc3", "en-GB": "altdesc"}, "type": "http://www.adlnet.gov/experienceapi/activity-types/http://adlnet.gov/expapi/activities/cmi.interaction",
                                                                "interactionType": "fill-in", "correctResponsesPattern": ["answers"],
                                                                "extensions": {"ext:key11": "value11", "ext:key22": "value22", "ext:key33": "value33"}}},
                                      "result": {"score": {"scaled": .75}, "completion": True, "success": True, "response": "shouted",
                                                 "duration": "P3Y6M4DT12H30M5S", "extensions": {"ext:dkey1": "dvalue1", "ext:dkey2": "dvalue2"}},
                                      "context": {"registration": self.cguid2, "contextActivities": {"other": {"id": "act:NewActivityID22"}},
                                                  "revision": "food", "platform": "bard", "language": "en-US", "extensions": {"ext:ckey11": "cval11",
                                                                                                                              "ext:ckey22": "cval22"}}})

        self.existStmt3 = json.dumps({"verb": {"id": "http://example.com/verbs/created",
                                               "display": {"en-US": "created"}}, "actor": {"objectType": "Agent", "mbox": "mailto:s@s.com"},
                                      "object": {"objectType": "Activity", "id": "act:foogals",
                                                 "definition": {"name": {"en-US": "testname3"}, "description": {"en-US": "testdesc3"}, "type": "http://adlnet.gov/expapi/activities/cmi.interaction",
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
                                                 "definition": {"name": {"en-US": "testname3"}, "description": {"en-US": "testdesc3"}, "type": "http://adlnet.gov/expapi/activities/cmi.interaction",
                                                                "interactionType": "fill-in", "correctResponsesPattern": ["answers"],
                                                                "extensions": {"ext:key111": "value111", "ext:key222": "value222", "ext:key333": "value333"}}},
                                      "result": {"score": {"scaled": .79}, "completion": True, "success": True, "response": "shouted",
                                                 "duration": "P3Y6M4DT12H30M5S", "extensions": {"ext:dkey1": "dvalue1", "ext:dkey2": "dvalue2"}},
                                      "context": {"registration": self.cguid4, "contextActivities": {"other": {"id": "act:NewActivityID22"}},
                                                  "revision": "food", "platform": "bard", "language": "en-US", "instructor": {"name": "bill", "mbox": "mailto:bill@bill.com"},
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
                                      "verb": {"id": "http://example.com/verbs/missed"}, "object": {"objectType": "SubStatement",
                                                                                                    "actor": {"objectType": "Agent", "mbox": "mailto:ss@ss.com"}, "verb": {"id": "verb:verb/url/nested"},
                                                                                                    "object": {"objectType": "Activity", "id": "act:testex.com"}, "result": {"completion": True, "success": True,
                                                                                                                                                                             "response": "kicked"}, "context": {"registration": self.cguid5,
                                                                                                                                                                                                                "contextActivities": {"other": {"id": "act:NewActivityID"}}, "revision": "foo", "platform": "bar",
                                                                                                                                                                                                                "language": "en-US", "extensions": {"ext:k1": "v1", "ext:k2": "v2"}}}})

        self.existStmt10 = json.dumps({"actor": {"objectType": "Agent", "mbox": "mailto:ref@ref.com"},
                                       "verb": {"id": "http://example.com/verbs/missed"}, "object": {"objectType": "StatementRef",
                                                                                                     "id": str(self.exist_stmt_id)}})

        # Put statements
        param = {"statementId": str(self.guid1)}
        path = "%s?%s" % (reverse('lrs:statements'), urllib.parse.urlencode(param))
        stmt_payload = self.existStmt1
        self.putresponse1 = self.client.put(path, stmt_payload, content_type="application/json",
                                            Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(self.putresponse1.status_code, 204)
        time = retrieve_statement.convert_to_datetime_object(
            str((datetime.utcnow() + timedelta(seconds=2)).replace(tzinfo=utc).isoformat()))
        stmt = Statement.objects.filter(
            statement_id=self.guid1).update(stored=time)

        param = {"statementId": str(self.guid3)}
        path = "%s?%s" % (reverse('lrs:statements'), urllib.parse.urlencode(param))
        stmt_payload = self.existStmt3
        self.putresponse3 = self.client.put(path, stmt_payload, content_type="application/json",
                                            Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(self.putresponse3.status_code, 204)
        time = retrieve_statement.convert_to_datetime_object(
            str((datetime.utcnow() + timedelta(seconds=3)).replace(tzinfo=utc).isoformat()))
        stmt = Statement.objects.filter(
            statement_id=self.guid3).update(stored=time)

        param = {"statementId": str(self.guid4)}
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

        param = {"statementId": str(self.guid2)}
        path = "%s?%s" % (reverse('lrs:statements'), urllib.parse.urlencode(param))
        stmt_payload = self.existStmt2
        self.putresponse2 = self.client.put(path, stmt_payload, content_type="application/json",
                                            Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(self.putresponse2.status_code, 204)
        time = retrieve_statement.convert_to_datetime_object(
            str((datetime.utcnow() + timedelta(seconds=6)).replace(tzinfo=utc).isoformat()))
        stmt = Statement.objects.filter(
            statement_id=self.guid2).update(stored=time)

        param = {"statementId": str(self.guid5)}
        path = "%s?%s" % (reverse('lrs:statements'), urllib.parse.urlencode(param))
        stmt_payload = self.existStmt5
        self.putresponse5 = self.client.put(path, stmt_payload, content_type="application/json",
                                            Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(self.putresponse5.status_code, 204)
        time = retrieve_statement.convert_to_datetime_object(
            str((datetime.utcnow() + timedelta(seconds=7)).replace(tzinfo=utc).isoformat()))
        stmt = Statement.objects.filter(
            statement_id=self.guid5).update(stored=time)

        param = {"statementId": str(self.guid6)}
        path = "%s?%s" % (reverse('lrs:statements'), urllib.parse.urlencode(param))
        stmt_payload = self.existStmt6
        self.putresponse6 = self.client.put(path, stmt_payload, content_type="application/json",
                                            Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(self.putresponse6.status_code, 204)
        time = retrieve_statement.convert_to_datetime_object(
            str((datetime.utcnow() + timedelta(seconds=8)).replace(tzinfo=utc).isoformat()))
        stmt = Statement.objects.filter(
            statement_id=self.guid6).update(stored=time)

        param = {"statementId": str(self.guid7)}
        path = "%s?%s" % (reverse('lrs:statements'), urllib.parse.urlencode(param))
        stmt_payload = self.existStmt7
        self.putresponse7 = self.client.put(path, stmt_payload, content_type="application/json",
                                            Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(self.putresponse7.status_code, 204)
        time = retrieve_statement.convert_to_datetime_object(
            str((datetime.utcnow() + timedelta(seconds=9)).replace(tzinfo=utc).isoformat()))
        stmt = Statement.objects.filter(
            statement_id=self.guid7).update(stored=time)

        param = {"statementId": str(self.guid8)}
        path = "%s?%s" % (reverse('lrs:statements'), urllib.parse.urlencode(param))
        stmt_payload = self.existStmt8
        self.putresponse8 = self.client.put(path, stmt_payload, content_type="application/json",
                                            Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(self.putresponse8.status_code, 204)
        time = retrieve_statement.convert_to_datetime_object(
            str((datetime.utcnow() + timedelta(seconds=10)).replace(tzinfo=utc).isoformat()))
        stmt = Statement.objects.filter(
            statement_id=self.guid8).update(stored=time)

        param = {"statementId": str(self.guid9)}
        path = "%s?%s" % (reverse('lrs:statements'), urllib.parse.urlencode(param))
        stmt_payload = self.existStmt9
        self.putresponse9 = self.client.put(path, stmt_payload, content_type="application/json",
                                            Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(self.putresponse9.status_code, 204)
        time = retrieve_statement.convert_to_datetime_object(
            str((datetime.utcnow() + timedelta(seconds=11)).replace(tzinfo=utc).isoformat()))
        stmt = Statement.objects.filter(
            statement_id=self.guid9).update(stored=time)

        param = {"statementId": str(self.guid10)}
        path = "%s?%s" % (reverse('lrs:statements'), urllib.parse.urlencode(param))
        stmt_payload = self.existStmt10
        self.putresponse10 = self.client.put(path, stmt_payload, content_type="application/json",
                                             Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(self.putresponse10.status_code, 204)
        time = retrieve_statement.convert_to_datetime_object(
            str((datetime.utcnow() + timedelta(seconds=11)).replace(tzinfo=utc).isoformat()))
        stmt = Statement.objects.filter(
            statement_id=self.guid10).update(stored=time)

    def test_invalid_result_fields(self):
        stmt = json.dumps({"verb": {"id": "http://example.com/verbs/created",
                                    "display": {"en-US": "created"}}, "actor": {"objectType": "Agent", "mbox": "mailto:s@s.com"},
                           "object": {"objectType": "Activity", "id": "act:foogie"},
                           "result": {"bad": "fields", "foo": "bar", "score": {"scaled": .85}, "completion": True, "success": True,
                                      "response": "kicked", "duration": "P3Y6M4DT12H30M5S", "extensions": {"ext:key1": "value1",
                                                                                                           "ext:key2": "value2"}}})

        resp = self.client.post(reverse('lrs:statements'), stmt, content_type="application/json",
                                Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)

        self.assertEqual(resp.status_code, 400)
        self.assertEqual(
            resp.content, 'Invalid field(s) found in Result - bad, foo')

    def test_invalid_context_fields(self):
        stmt = json.dumps({"verb": {"id": "http://example.com/verbs/created",
                                    "display": {"en-US": "created"}}, "actor": {"objectType": "Agent", "mbox": "mailto:s@s.com"},
                           "object": {"objectType": "Activity", "id": "act:foogals",
                                      "definition": {"name": {"en-US": "testname3"}, "description": {"en-US": "testdesc3"}, "type": "http://adlnet.gov/expapi/activities/cmi.interaction",
                                                     "interactionType": "fill-in", "correctResponsesPattern": ["answers"],
                                                     "extensions": {"ext:key111": "value111", "ext:key222": "value222", "ext:key333": "value333"}}},
                           "result": {"score": {"scaled": .79}, "completion": True, "success": True, "response": "shouted",
                                      "duration": "P3Y6M4DT12H30M5S", "extensions": {"ext:dkey1": "dvalue1", "ext:dkey2": "dvalue2"}},
                           "context": {"contextActivities": {"other": {"id": "act:NewActivityID22"}},
                                       "revision": "food", "bad": "foo", "platform": "bard", "language": "en-US",
                                       "instructor": {"objectType": "Agent", "name": "bob", "mbox": "mailto:bob@bob.com"},
                                       "extensions": {"ext:ckey111": "cval111", "ext:ckey222": "cval222"}}})

        resp = self.client.post(reverse('lrs:statements'), stmt, content_type="application/json",
                                Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)

        self.assertEqual(resp.status_code, 400)
        self.assertEqual(
            resp.content, 'Invalid field(s) found in Context - bad')

    def test_post_with_no_valid_params(self):
        # Error will be thrown in statements class
        resp = self.client.post(reverse('lrs:statements'), {"feet": "yes", "hands": {"id": "http://example.com/test_post"}},
                                content_type="application/json", Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)
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

    def test_post_wrong_crp_type(self):
        stmt = json.dumps({"verb": {"id": "http://example.com/verbs/created"},
                           "object": {"objectType": "Activity", "id": "act:foogie",
                                      "definition": {"name": {"en-US": "testname2", "en-GB": "altname"},
                                                     "description": {"en-US": "testdesc2", "en-GB": "altdesc"}, "type": "http://www.adlnet.gov/experienceapi/activity-types/http://adlnet.gov/expapi/activities/cmi.interaction",
                                                     "interactionType": "fill-in", "correctResponsesPattern": "wrong"}},
                           "actor": {"objectType": "Agent", "mbox": "mailto:wrong-t@t.com"}})
        response = self.client.post(reverse('lrs:statements'), stmt, content_type="application/json",
                                    Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.content, 'Activity definition correctResponsesPattern is not a properly formatted array')

    def test_post_wrong_choice_type(self):
        stmt = json.dumps(
            {"verb": {"id": "http://example.com/verbs/created"},
             "object": {"objectType": "Activity", "id": "act:foogie",
                        "definition": {"name": {"en-US": "testname2", "en-GB": "altname"},
                                       "description": {"en-US": "testdesc2", "en-GB": "altdesc"},
                                       "type": "http://adlnet.gov/expapi/activities/cmi.interaction",
                                       "interactionType": "choice", "correctResponsesPattern": ["a1[,]a3[,]a6[,]a7"],
                                       "choices": "wrong"}},
             "actor": {"objectType": "Agent", "mbox": "mailto:wrong-t@t.com"}})
        response = self.client.post(reverse('lrs:statements'), stmt, content_type="application/json",
                                    Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.content, 'Activity definition choices is not a properly formatted array')

    def test_openid(self):
        stmt = json.dumps({'object': {'objectType': 'Agent', 'name': 'lulu', 'openid': 'id:luluid'},
                           'verb': {"id": "verb:verb/url"}, 'actor': {'objectType': 'Agent', 'mbox': 'mailto:t@t.com'}})

        response = self.client.post(reverse('lrs:statements'), stmt, content_type="application/json",
                                    Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)

        self.assertEqual(response.status_code, 200)
        agent = Agent.objects.get(name='lulu')
        self.assertEqual(agent.openid, 'id:luluid')

    def test_invalid_actor_fields(self):
        stmt = json.dumps({"actor": {"objectType": "Agent", "mbox": "mailto:t@t.com", "name": "bob", "bad": "blah",
                                     "foo": "bar"},
                           "verb": {"id": "http://example.com/verbs/passed", "display": {"en-US": "passed"}},
                           "object": {"id": "act:test_post"}})
        response = self.client.post(reverse('lrs:statements'), stmt, content_type="application/json",
                                    Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.content,
                         'Invalid field(s) found in Agent/Group - bad, foo')

    def test_invalid_activity_fields(self):
        stmt = json.dumps({"actor": {"objectType": "Agent", "mbox": "mailto:t@t.com", "name": "bob"},
                           "verb": {"id": "http://example.com/verbs/passed", "display": {"en-US": "passed"}},
                           "object": {"id": "act:test_post", "bad": "foo", "foo": "bar"}})
        response = self.client.post(reverse('lrs:statements'), stmt, content_type="application/json",
                                    Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.content,
                         "Invalid field(s) found in Activity - bad, foo")

    def test_blank_object_definition(self):
        stmt = json.dumps({"actor": {"objectType": "Agent", "mbox": "mailto:def@def.com", "name": "D"},
                           "verb": {"id": "http://example.com/verbs/passed", "display": {"en-US": "passed"}},
                           "object": {
                            "definition": { },
                            "id": "http://object.com/",
                            "objectType": "Activity"
                        }})
        response = self.client.post(reverse('lrs:statements'), stmt, content_type="application/json",
                                    Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(response.status_code, 200)
        agent = Agent.objects.get(mbox="mailto:def@def.com")
        self.assertEqual(agent.name, "D")
        
        get_response = self.client.get(reverse('lrs:statements'), X_Experience_API_Version=settings.XAPI_VERSION,
                                      Authorization=self.auth)
        self.assertEqual(get_response.status_code, 200)
        rsp = get_response.content
        self.assertIn("definition", rsp)
        json_object = json.loads(rsp)
        jdef = json_object['statements'][0]['object']['definition']
        self.assertEqual(jdef, {})

        param = {"format": 'canonical'}
        path = "%s?%s" % (reverse('lrs:statements'), urllib.parse.urlencode(param))

        get_response = self.client.get(path, X_Experience_API_Version=settings.XAPI_VERSION,
                                      Authorization=self.auth)
        self.assertEqual(get_response.status_code, 200)
        self.assertNotIn('definition', get_response.content)

    def test_blank_score(self):
        stmt = json.dumps({"verb": {"id": "http://example.com/verbs/created",
                                    "display": {"en-US": "created"}}, "actor": {"objectType": "Agent", "mbox": "mailto:s@s.com"},
                           "object": {"objectType": "Activity", "id": "act:foogie2"},
                           "result": {"score": {}, "completion": True, "success": True,
                                      "response": "kicked", "duration": "P3Y6M4DT12H30M5S", "extensions": {"ext:key1": "value1",
                                                                                                           "ext:key2": "value2"}}})
        response = self.client.post(reverse('lrs:statements'), stmt, content_type="application/json",
                                Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)

        self.assertEqual(response.status_code, 200)
        get_response = self.client.get(reverse('lrs:statements'), X_Experience_API_Version=settings.XAPI_VERSION,
                                      Authorization=self.auth)
        self.assertEqual(get_response.status_code, 200)
        rsp = get_response.content
        self.assertIn("score", rsp)
        json_object = json.loads(rsp)
        jscore = json_object['statements'][0]['result']['score']
        self.assertEqual(jscore, {})

        param = {"format": 'canonical'}
        path = "%s?%s" % (reverse('lrs:statements'), urllib.parse.urlencode(param))

        get_response = self.client.get(path, X_Experience_API_Version=settings.XAPI_VERSION,
                                      Authorization=self.auth)
        self.assertEqual(get_response.status_code, 200)
        self.assertNotIn('score', get_response.content)
        
    def test_blank_result(self):
        stmt = json.dumps({"verb": {"id": "http://example.com/verbs/created",
                                    "display": {"en-US": "created"}}, "actor": {"objectType": "Agent", "mbox": "mailto:foo@foo.com"},
                           "object": {"objectType": "Activity", "id": "act:foop"},
                           "result": {}})
        response = self.client.post(reverse('lrs:statements'), stmt, content_type="application/json",
                                Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)

        self.assertEqual(response.status_code, 200)
        get_response = self.client.get(reverse('lrs:statements'), X_Experience_API_Version=settings.XAPI_VERSION,
                                      Authorization=self.auth)
        self.assertEqual(get_response.status_code, 200)
        rsp = get_response.content
        self.assertIn("result", rsp)
        json_object = json.loads(rsp)
        jresult = json_object['statements'][0]['result']
        self.assertEqual(jresult, {})

        param = {"format": 'canonical'}
        path = "%s?%s" % (reverse('lrs:statements'), urllib.parse.urlencode(param))

        get_response = self.client.get(path, X_Experience_API_Version=settings.XAPI_VERSION,
                                      Authorization=self.auth)
        self.assertEqual(get_response.status_code, 200)
        self.assertNotIn('result', get_response.content)

    def test_blank_context(self):
        stmt = json.dumps({"verb": {"id": "http://example.com/verbs/created",
                                    "display": {"en-US": "created"}}, "actor": {"objectType": "Agent", "mbox": "mailto:s@s.com"},
                           "object": {"objectType": "Activity", "id": "act:foobaz"},
                           "context": {}})
        response = self.client.post(reverse('lrs:statements'), stmt, content_type="application/json",
                                Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)

        self.assertEqual(response.status_code, 200)
        get_response = self.client.get(reverse('lrs:statements'), X_Experience_API_Version=settings.XAPI_VERSION,
                                      Authorization=self.auth)
        self.assertEqual(get_response.status_code, 200)
        rsp = get_response.content
        self.assertIn("context", rsp)
        json_object = json.loads(rsp)
        jcontext = json_object['statements'][0]['context']
        self.assertEqual(jcontext, {})

        param = {"format": 'canonical'}
        path = "%s?%s" % (reverse('lrs:statements'), urllib.parse.urlencode(param))

        get_response = self.client.get(path, X_Experience_API_Version=settings.XAPI_VERSION,
                                      Authorization=self.auth)
        self.assertEqual(get_response.status_code, 200)
        self.assertNotIn('result', get_response.content)

    def test_invalid_activity_def_fields(self):
        stmt = json.dumps({"actor": {"objectType": "Agent", "mbox": "mailto:t@t.com", "name": "bob"},
                           "verb": {"id": "http://example.com/verbs/passed", "display": {"en-US": "passed"}},
                           "object": {'objectType': 'Activity', 'id': 'act:food',
                                      'definition': {'bad': 'foo', 'name': {'en-FR': 'testname2', 'en-US': 'testnameEN'}, 'description': {'en-CH': 'testdesc2',
                                                                                                                                          'en-GB': 'testdescGB'}, 'type': 'type:course', 'interactionType': 'intType2', 'extensions': {'ext:key1': 'value1',
                                                                                                                                                                                                                                       'ext:key2': 'value2', 'ext:key3': 'value3'}}}})
        response = self.client.post(reverse('lrs:statements'), stmt, content_type="application/json",
                                    Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.content,
                         'Invalid field(s) found in Activity definition - bad')

    def test_post_wrong_duration(self):
        stmt = json.dumps({"actor": {'name': 'jon',
                                     'mbox': 'mailto:jon@example.com'}, 'verb': {"id": "verb:verb/url"}, "object": {'id': 'act:activity13'},
                           "result": {'completion': True, 'success': True, 'response': 'yes', 'duration': 'wrongduration',
                                      'extensions': {'ext:key1': 'value1', 'ext:key2': 'value2'}}})

        response = self.client.post(reverse('lrs:statements'), stmt, content_type="application/json",
                                    Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.content, "Error with result duration")

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

    def test_context_bad_language(self):
        stmt = json.dumps({"actor": {"mbox": "mailto:mr.t@example.com"},
                           "verb": {"id": "http://example.com/verbs/passed", "display": {"en-US": "passed"}},
                           "object": {"id": "act:i.pity.the.fool"},
                           "context":{"language": "thisisnotalanguage"}})

        response = self.client.post(reverse('lrs:statements'), stmt, content_type="application/json",
                                    Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(response.status_code, 400)

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
        guid = uuid.uuid4()

        param = {"statementId": str(guid)}
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
        self.assertEqual(stmt.authority.name, "tester1")
        self.assertEqual(stmt.authority.mbox, "mailto:test1@tester.com")

        self.assertEqual(stmt.version, '1.0.0')
        self.assertEqual(stmt.verb.verb_id, "http://example.com/verbs/passed")

    def test_put_1_0_0(self):
        guid = uuid.uuid4()

        param = {"statementId": str(guid)}
        path = "%s?%s" % (reverse('lrs:statements'), urllib.parse.urlencode(param))
        stmt = json.dumps({"verb": {"id": "http://example.com/verbs/passed", "display": {"en-US": "passed"}},
                           "object": {"id": "act:test_put"}, "actor": {"objectType": "Agent", "mbox": "mailto:t@t.com"}})

        putResponse = self.client.put(path, stmt, content_type="application/json",
                                      Authorization=self.auth, X_Experience_API_Version="1.0.0")
        self.assertEqual(putResponse.status_code, 204)
        stmt = Statement.objects.get(statement_id=guid)

        act = Activity.objects.get(activity_id="act:test_put")
        self.assertEqual(act.activity_id, "act:test_put")

        self.assertEqual(stmt.actor.mbox, "mailto:t@t.com")
        self.assertEqual(stmt.authority.name, "tester1")
        self.assertEqual(stmt.authority.mbox, "mailto:test1@tester.com")

        self.assertEqual(stmt.version, "1.0.0")
        self.assertEqual(stmt.verb.verb_id, "http://example.com/verbs/passed")

    def test_put_id_in_stmt(self):
        guid = uuid.uuid4()

        stmt = json.dumps({"id": str(guid), "verb": {"id": "http://example.com/verbs/passed", "display": {"en-US": "passed"}},
                           "object": {"id": "act:test_put"}, "actor": {"objectType": "Agent", "mbox": "mailto:t@t.com"}})

        putResponse = self.client.put(reverse('lrs:statements'), stmt, content_type="application/json",
                                      Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(putResponse.status_code, 400)

    def test_put_id_in_both_same(self):
        guid = uuid.uuid4()

        param = {"statementId": str(guid)}
        path = "%s?%s" % (reverse('lrs:statements'), urllib.parse.urlencode(param))
        stmt = json.dumps({"id": str(guid), "verb": {"id": "http://example.com/verbs/passed", "display": {"en-US": "passed"}},
                           "object": {"id": "act:test_put"}, "actor": {"objectType": "Agent", "mbox": "mailto:t@t.com"}})

        putResponse = self.client.put(path, stmt, content_type="application/json",
                                      Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(putResponse.status_code, 204)
        stmt = Statement.objects.get(statement_id=guid)

        act = Activity.objects.get(activity_id="act:test_put")
        self.assertEqual(act.activity_id, "act:test_put")

        self.assertEqual(stmt.actor.mbox, "mailto:t@t.com")
        self.assertEqual(stmt.authority.name, "tester1")
        self.assertEqual(stmt.authority.mbox, "mailto:test1@tester.com")

        self.assertEqual(stmt.version, '1.0.0')
        self.assertEqual(stmt.verb.verb_id, "http://example.com/verbs/passed")

    def test_put_id_in_both_different(self):
        guid1 = str(uuid.uuid4())
        guid2 = str(uuid.uuid4())

        param = {"statementId": guid1}
        path = "%s?%s" % (reverse('lrs:statements'), urllib.parse.urlencode(param))
        stmt = json.dumps({"id": guid2, "verb": {"id": "http://example.com/verbs/passed", "display": {"en-US": "passed"}},
                           "object": {"id": "act:test_put"}, "actor": {"objectType": "Agent", "mbox": "mailto:t@t.com"}})

        putResponse = self.client.put(path, stmt, content_type="application/json",
                                      Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(putResponse.status_code, 400)
        self.assertEqual(
            putResponse.content, "Error -- statements - method = PUT, param and body ID both given, but do not match")

    def test_put_with_substatement(self):
        con_guid = str(uuid.uuid4())
        st_guid = str(uuid.uuid4())

        param = {"statementId": st_guid}
        path = "%s?%s" % (reverse('lrs:statements'), urllib.parse.urlencode(param))
        stmt = json.dumps({"actor": {"objectType": "Agent", "mbox": "mailto:sass@sass.com"},
                           "verb": {"id": "verb:verb/url/tested"}, "object": {"objectType": "SubStatement",
                                                                              "actor": {"objectType": "Agent", "mbox": "mailto:ss@ss.com"}, "verb": {"id": "verb:verb/url/nested"},
                                                                              "object": {"objectType": "Activity", "id": "act:testex.com"}, "result": {"completion": True, "success": True,
                                                                                                                                                       "response": "kicked"}, "context": {"registration": con_guid,
                                                                                                                                                                                          "contextActivities": {"other": {"id": "act:NewActivityID"}}, "revision": "foo", "platform": "bar",
                                                                                                                                                                                          "language": "en-US", "extensions": {"ext:k1": "v1", "ext:k2": "v2"}}}})

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
        self.assertIn("ss@ss.com", rsp)
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
        guid = str(uuid.uuid4())

        param = {"statementId": guid}
        path = "%s?%s" % (reverse('lrs:statements'), urllib.parse.urlencode(param))
        stmt = json.dumps({})

        putResponse = self.client.put(path, stmt, content_type="application/json",
                                      Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(putResponse.status_code, 400)

    def test_existing_stmtID_put(self):
        guid = str(uuid.uuid4())

        exist_stmt = json.dumps({"verb": {"id": "http://example.com/verbs/passed", "display": {"en-US": "passed"}},
                                 "object": {"id": "act:activity"}, "actor": {"objectType": "Agent", "mbox": "mailto:t@t.com"}})
        path = "%s?%s" % (reverse('lrs:statements'),
                          urllib.parse.urlencode({"statementId": guid}))
        response = self.client.put(path, exist_stmt, content_type="application/json",
                                   Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(response.status_code, 204)

        param = {"statementId": guid}
        path = "%s?%s" % (reverse('lrs:statements'), urllib.parse.urlencode(param))
        stmt = json.dumps({"verb": {"id": "http://example.com/verbs/passed", "display": {"en-US": "passed"}},
                           "object": {"id": "act:test_existing_put"}, "actor": {"objectType": "Agent", "mbox": "mailto:t@t.com"}})

        putResponse = self.client.put(path, stmt, content_type="application/json",
                                      Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)

        self.assertEqual(putResponse.status_code, 409)

    def test_missing_stmtID_put(self):
        stmt = json.dumps({"verb": {"id": "http://example.com/verbs/passed", "display": {"en-US": "passed"}},
                           "object": {"id": "act:test_put"}, "actor": {"objectType": "Agent", "mbox": "mailto:t@t.com"}})
        response = self.client.put(reverse('lrs:statements'), stmt, content_type="application/json",
                                   Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(response.status_code, 400)
        self.assertIn(
            response.content, "Error -- statements - method = PUT, but no statementId parameter or ID given in statement")

    def test_get(self):
        self.bunchostmts()
        param = {"statementId": str(self.guid1)}
        path = "%s?%s" % (reverse('lrs:statements'), urllib.parse.urlencode(param))
        getResponse = self.client.get(
            path, X_Experience_API_Version=settings.XAPI_VERSION, Authorization=self.auth)
        self.assertEqual(getResponse.status_code, 200)
        rsp = getResponse.content
        self.assertIn(str(self.guid1), rsp)
        self.assertIn('content-length', getResponse._headers)

    def test_get_no_params(self):
        self.bunchostmts()
        getResponse = self.client.get(reverse('lrs:statements'), X_Experience_API_Version=settings.XAPI_VERSION,
                                      Authorization=self.auth)
        self.assertEqual(getResponse.status_code, 200)
        self.assertIn('content-length', getResponse._headers)

        rsp = json.loads(getResponse.content)
        self.assertEqual(len(rsp['statements']), 11)

    def test_head(self):
        self.bunchostmts()
        param = {"statementId": str(self.guid1)}
        path = "%s?%s" % (reverse('lrs:statements'), urllib.parse.urlencode(param))
        head_resp = self.client.head(
            path, X_Experience_API_Version=settings.XAPI_VERSION, Authorization=self.auth)
        self.assertEqual(head_resp.status_code, 200)
        self.assertEqual(head_resp.content, '')
        self.assertIn('content-length', head_resp._headers)

    def test_get_no_existing_ID(self):
        param = {"statementId": "aaaaaa"}
        path = "%s?%s" % (reverse('lrs:statements'), urllib.parse.urlencode(param))
        getResponse = self.client.get(
            path, X_Experience_API_Version=settings.XAPI_VERSION, Authorization=self.auth)
        self.assertEqual(getResponse.status_code, 400)

    def test_get_no_statementid(self):
        self.bunchostmts()
        getResponse = self.client.get(reverse(
            'lrs:statements'), X_Experience_API_Version=settings.XAPI_VERSION, Authorization=self.auth)
        self.assertEqual(getResponse.status_code, 200)
        jsn = json.loads(getResponse.content)
        self.assertEqual(len(jsn["statements"]), 11)
        self.assertIn('content-length', getResponse._headers)

    def test_head_no_statementid(self):
        self.bunchostmts()
        head_resp = self.client.head(reverse(
            'lrs:statements'), X_Experience_API_Version=settings.XAPI_VERSION, Authorization=self.auth)
        self.assertEqual(head_resp.status_code, 200)
        self.assertEqual(head_resp.content, '')
        self.assertIn('content-length', head_resp._headers)

    # Sever activities are PUT - contextActivities create 3 more
    def test_number_of_activities(self):
        self.bunchostmts()
        acts = len(Activity.objects.all())
        self.assertEqual(9, acts)

    def test_timeout_snafu(self):
        stmt = json.dumps({
            "timestamp": "2013-11-05T07:33:49.512119+00:00",
            "object": {
                "definition": {
                    "name": {
                        "en-US": "news.google.com",
                        "ja": "news.google.com"
                    },
                    "description": {
                        "en-US": "",
                        "ja": ""
                    }
                },
                "id": "http://garewelswe.com/",
                "objectType": "Activity"
            },
            "authority": {
                "mbox": "mailto:kazutaka_kamiya@test.local",
                "name": "adllrs",
                "objectType": "Agent"
            },
            "verb": {
                "id": "http://example.com/verbs/experienced",
                "display": {
                    "en-US": "experienced"
                }
            },
            "actor": {
                "openid": "http://test.local/PEab76617d1d21d725d358a7ad5231bd6e",
                "name": "dev2-001",
                "objectType": "Agent"
            },
            "id": "9cb78e42-45ec-11e3-b8dc-0af904863508"
        })

        response = self.client.post(reverse('lrs:statements'), stmt, content_type="application/json",
                                    Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)

        self.assertEqual(response.status_code, 200)

        stmt = json.dumps({
            "timestamp": "2013-11-08T08:41:55.985064+00:00",
            "object": {
                "definition": {
                    "interactionType": "fill-in",
                    "correctResponsesPattern": [],
                    "type": "http://adlnet.gov/expapi/activities/cmi.interaction",
                    "name": {
                        "ja": "SCORM20110721_12"
                    },
                    "description": {
                        "ja": ""
                    }
                },
                "id": "http://garewelswe.com/",
                "objectType": "Activity"
            },
            "actor": {
                "openid": "http://test.local/EAGLE/PEab76617d1d21d725d358a7ad5231bd6e",
                "name": "dev2-001",
                "objectType": "Agent"
            },
            "verb": {
                "id": "http://example.com/verbs/answered",
                "display": {
                    "en-US": "answered"
                }
            },
            "result": {
                "response": "TEST0",
                "success": True
            },
            "context": {
                "contextActivities": {
                    "parent": [
                        {
                            "id": "http://garewelswe.com/"
                        }
                    ],
                    "grouping": [
                        {
                            "id": "http://garewelswe.com/"
                        }
                    ]
                }
            },
            "id": "9faf143c-4851-11e3-b1a1-000c29bfba11",
            "authority": {
                "mbox": "mailto:kazutaka_kamiya@test.local",
                "name": "adllrs",
                "objectType": "Agent"
            }
        })

        response = self.client.post(reverse('lrs:statements'), stmt, content_type="application/json",
                                    Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)

        self.assertEqual(response.status_code, 200)

    def test_amsterdam_snafu(self):
        stmt = json.dumps({
            "timestamp": "2013-05-23T10:46:39+02:00",
            "verb": {"id": "http://www.adlnet.gov/expapi/verbs/experienced"},
            "context": {
                "contextActivities": {
                    "parent": {
                        "id": "http://localhost:8080/portal/site/~88a4933d-99d2-4a35-8906-993fdcdf2259"
                    }
                }
            },
            "object": {
                "id": "http://localhost:8080/portal/web/~88a4933d-99d2-4a35-8906-993fdcdf2259/id/c50bf034-0f3e-4055-a1e7-8d1cf92be353/url/%2Flibrary%2Fcontent%2Fmyworkspace_info.html",
                "definition": {
                    "type": "http://adlnet.gov/expapi/activities/view-web-content"
                },
                "objectType": "Activity"
            },
            "actor": {
                "name": "Alan Tester",
                "objectType": "Agent",
                "mbox": "mailto:tester@dev.nl"
            }
        })
        post_response = self.client.post(reverse('lrs:statements'), stmt, content_type="application/json",
                                         Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(post_response.status_code, 200)

    def test_update_activity_wrong_auth(self):
        existStmt1 = json.dumps({"verb": {"id": "http://example.com/verbs/created",
                                          "display": {"en-US": "created"}}, "actor": {"objectType": "Agent", "mbox": "mailto:s@s.com"},
                                 "object": {"objectType": "Activity", "id": "act:foogie",
                                            "definition": {"name": {"en-US": "testname2", "en-GB": "altname"}, "description": {"en-US": "testdesc2", "en-GB": "altdesc"},
                                                           "type": "http://www.adlnet.gov/experienceapi/activity-types/http://adlnet.gov/expapi/activities/cmi.interaction",
                                                           "interactionType": "fill-in", "correctResponsesPattern": ["answer"],
                                                           "extensions": {"ext:key1": "value1", "ext:key2": "value2", "ext:key3": "value3"}}},
                                 "result": {"score": {"scaled": .85}, "completion": True, "success": True, "response": "kicked",
                                            "duration": "P3Y6M4DT12H30M5S", "extensions": {"ext:key1": "value1", "ext:key2": "value2"}},
                                 "context": {"registration": str(uuid.uuid4()), "contextActivities": {"other": {"id": "act:NewActivityID2"}},
                                             "revision": "food", "platform": "bard", "language": "en-US", "extensions": {"ext:ckey1": "cval1",
                                                                                                                         "ext:ckey2": "cval2"}}})
        param = {"statementId": str(self.guid1)}
        path = "%s?%s" % (reverse('lrs:statements'), urllib.parse.urlencode(param))
        putresponse1 = self.client.put(path, existStmt1, content_type="application/json",
                                       Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(putresponse1.status_code, 204)

        wrong_username = "tester2"
        wrong_email = "test2@tester.com"
        wrong_password = "test2"
        wrong_auth = "Basic %s" % base64.b64encode(
            "%s:%s" % (wrong_username, wrong_password))
        form = {"username": wrong_username, "email": wrong_email, "password": wrong_password,
                "password2": wrong_password}
        self.client.post(reverse(register), form,
                         X_Experience_API_Version=settings.XAPI_VERSION)

        stmt = json.dumps({"verb": {"id": "verb:verb/iri/attempted"}, "actor": {"objectType": "Agent", "mbox": "mailto:r@r.com"},
                           "object": {"objectType": "Activity", "id": "act:foogie",
                                      "definition": {"name": {"en-US": "testname3"}, "description": {"en-US": "testdesc3"},
                                                     "type": "http://www.adlnet.gov/experienceapi/activity-types/http://adlnet.gov/expapi/activities/cmi.interaction",
                                                     "interactionType": "fill-in", "correctResponsesPattern": ["answer"],
                                                     "extensions": {"ext:key1": "value1", "ext:key2": "value2", "ext:key3": "value3"}}},
                           "result": {"score": {"scaled": .85}, "completion": True, "success": True, "response": "kicked",
                                      "duration": "P3Y6M4DT12H30M5S", "extensions": {"ext:key1": "value1", "ext:key2": "value2"}},
                           "context": {"registration": str(uuid.uuid4()), "contextActivities": {"other": {"id": "act:NewActivityID2"}},
                                       "revision": "food", "platform": "bard", "language": "en-US", "extensions": {"ext:ckey1": "cval1",
                                                                                                                   "ext:ckey2": "cval2"}}, "authority": {"objectType": "Agent", "name": "auth", "mbox": "mailto:auth@example.com"}})

        post_response = self.client.post(reverse('lrs:statements'), stmt, content_type="application/json",
                                         Authorization=wrong_auth, X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(post_response.status_code, 200)

        acts = Activity.objects.filter(activity_id="act:foogie").count()
        self.assertEqual(acts, 1)

    def test_update_activity_correct_auth(self):
        self.bunchostmts()
        stmt = json.dumps({"verb": {"id": "verb:verb/url/changed-act"}, "actor": {"objectType": "Agent", "mbox": "mailto:l@l.com"},
                           "object": {"objectType": "Activity", "id": "act:foogie",
                                      "definition": {"name": {"en-US": "testname3"}, "description": {"en-US": "testdesc3"},
                                                     "type": "http://www.adlnet.gov/experienceapi/activity-types/http://adlnet.gov/expapi/activities/cmi.interaction", "interactionType": "fill-in", "correctResponsesPattern": ["answer"],
                                                     "extensions": {"ext:key1": "value1", "ext:key2": "value2", "ext:key3": "value3"}}},
                           "result": {"score": {"scaled": .85}, "completion": True, "success": True, "response": "kicked",
                                      "duration": "P3Y6M4DT12H30M5S", "extensions": {"ext:key1": "value1", "ext:key2": "value2"}},
                           "context": {"registration": self.cguid6, "contextActivities": {"other": {"id": "act:NewActivityID2"}},
                                       "revision": "food", "platform": "bard", "language": "en-US", "extensions": {"ext:ckey1": "cval1",
                                                                                                                   "ext:ckey2": "cval2"}}, "authority": {"objectType": "Agent", "name": "auth", "mbox": "mailto:auth@example.com"}})

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
        content = ('{"verb": {"id": "verb:verb/url"}, "actor": {"objectType": "Agent", "mbox": "mailto:r@r.com"},' 
                   '"object": {"id": "act:test_cors_post_put"}}')

        bdy = "statementId=886313e1-3b8a-5372-9b90-0c9aee199e5d&content=%s&Authorization=%s&Content-Type=application/json&X-Experience-API-Version=%s" % (
            urllib.parse.quote(content), self.auth, settings.XAPI_VERSION)
        path = "%s?%s" % (reverse('lrs:statements'),
                          urllib.parse.urlencode({"method": "PUT"}))
        response = self.client.post(
            path, bdy, content_type="application/x-www-form-urlencoded")
        self.assertEqual(response.status_code, 204)

        act = Activity.objects.get(activity_id="act:test_cors_post_put")
        self.assertEqual(act.activity_id, "act:test_cors_post_put")

        agent = Agent.objects.get(mbox="mailto:test1@tester.com")
        self.assertEqual(agent.name, "tester1")
        self.assertEqual(agent.mbox, "mailto:test1@tester.com")

    def test_cors_post_put_1_0_0(self):
        content = {"verb": {"id": "verb:verb/url"}, "actor": {"objectType": "Agent", "mbox": "mailto:r@r.com"},
                   "object": {"id": "act:test_cors_post_put"}}

        bdy = "statementId=886313e1-3b8a-5372-9b90-0c9aee199e5d&content=%s&Authorization=%s&Content-Type=application/json&X-Experience-API-Version=1.0.0" % (
            urllib.parse.quote(str(content)), self.auth)
        path = "%s?%s" % (reverse('lrs:statements'),
                          urllib.parse.urlencode({"method": "PUT"}))
        response = self.client.post(
            path, bdy, content_type="application/x-www-form-urlencoded")
        self.assertEqual(response.status_code, 204)

        act = Activity.objects.get(activity_id="act:test_cors_post_put")
        self.assertEqual(act.activity_id, "act:test_cors_post_put")

        agent = Agent.objects.get(mbox="mailto:test1@tester.com")
        self.assertEqual(agent.name, "tester1")
        self.assertEqual(agent.mbox, "mailto:test1@tester.com")

    def test_cors_post_put_wrong_version(self):
        content = {"verb": {"id": "verb:verb/url"}, "actor": {"objectType": "Agent", "mbox": "mailto:r@r.com"},
                   "object": {"id": "act:test_cors_post_put"}}

        bdy = "statementId=886313e1-3b8a-5372-9b90-0c9aee199e5b&content=%s&Authorization=%s&X-Experience-API-Version=1.0.33&Content-Type=application/json" % (
            content, self.auth)
        path = "%s?%s" % (reverse('lrs:statements'),
                          urllib.parse.urlencode({"method": "PUT"}))
        response = self.client.post(
            path, bdy, content_type="application/x-www-form-urlencoded")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.content,
                         "X-Experience-API-Version is not supported")

    def test_cors_post_put_correct_version(self):
        content = {"verb": {"id": "verb:verb/url"}, "actor": {"objectType": "Agent", "mbox": "mailto:r@r.com"},
                   "object": {"id": "act:test_cors_post_put"}}

        bdy = "statementId=886313e1-3b8a-5372-9b90-0c9aee199e5a&content=%s&Authorization=%s&X-Experience-API-Version=1.0.1&Content-Type=application/json" % (
            urllib.parse.quote(str(content)), self.auth)
        path = "%s?%s" % (reverse('lrs:statements'),
                          urllib.parse.urlencode({"method": "PUT"}))
        response = self.client.post(
            path, bdy, content_type="application/x-www-form-urlencoded")
        self.assertEqual(response.status_code, 204)

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
                                   Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(put_stmt.status_code, 204)

    def test_post_with_group(self):
        ot = "Group"
        name = "the group ST"
        mbox = "mailto:the.groupST@example.com"
        stmt = json.dumps({"actor": {"objectType": ot, "name": name, "mbox": mbox, "member": [{"name": "agentA", "mbox": "mailto:agentA@example.com"}, {"name": "agentB", "mbox": "mailto:agentB@example.com"}]}, "verb": {"id": "http://verb/iri/created", "display": {"en-US": "created"}},
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

    def test_post_with_group_no_members_listed(self):
        ot = "Group"
        name = "the group ML"
        mbox = "mailto:the.groupML@example.com"
        stmt = json.dumps({"actor": {"objectType": ot, "name": name, "mbox": mbox}, "verb": {"id": "http://verb/iri/created", "display": {"en-US": "created"}},
                           "object": {"id": "act:i.pity.the.fool"}})
        response = self.client.post(reverse('lrs:statements'), stmt, content_type="application/json",
                                    Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(response.status_code, 200)
        g = Agent.objects.get(mbox="mailto:the.groupML@example.com")
        self.assertEqual(g.name, name)
        self.assertEqual(g.mbox, mbox)
        mems = g.member.values_list("name", flat=True)
        self.assertEqual(len(mems), 0)

    def test_post_with_group_member_not_array(self):
        ot = "Group"
        name = "the group ST"
        mbox = "mailto:the.groupST@example.com"
        members = "wrong"
        stmt = json.dumps({"actor": {"objectType": ot, "name": name, "mbox": mbox, "member": members}, "verb": {"id": "http://verb/iri/created", "display": {"en-US": "created"}},
                           "object": {"id": "act:i.pity.the.fool"}})
        response = self.client.post(reverse('lrs:statements'), stmt, content_type="application/json",
                                    Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.content,
                         'Members is not a properly formatted array')

    def test_post_with_group_member_empty_array(self):
        ot = "Group"
        name = "the group ST"
        mbox = "mailto:the.groupST@example.com"
        members = []
        stmt = json.dumps({"actor": {"objectType": ot, "name": name, "mbox": mbox, "member": members}, "verb": {"id": "http://verb/iri/created", "display": {"en-US": "created"}},
                           "object": {"id": "act:i.pity.the.fool"}})
        response = self.client.post(reverse('lrs:statements'), stmt, content_type="application/json",
                                    Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.content,
                         "Member property must contain agents")

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
        stmt = json.dumps({"verb": {"id": "verb:completed"}, "object": {"id": "act:scorm.com/JsTetris_TCAPI/level2",
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

    def test_issue_put_wrong_version_header_again(self):
        stmt_id = '33f60b35-e1b2-4ddc-9c6f-7b3f65244432'
        stmt = json.dumps({"verb": {"id": "verb:completed"}, "object": {"id": "act:scorm.com/JsTetris_TCAPI/level2",
                                                                        "definition": {"type": "media", "name": {"en-US": "Js Tetris Level2"},
                                                                                       "description": {"en-US": "Starting at 1, the higher the level, the harder the game."}}},
                           "result": {"extensions": {"ext:time": 104, "ext:apm": 229, "ext:lines": 5}, "score": {"raw": 9911, "min": 0}},
                           "context": {"contextActivities": {"grouping": {"id": "act:scorm.com/JsTetris_TCAPI"}},
                                       "registration": "b7be7d9d-bfe2-4917-8ccd-41a0d18dd953"},
                           "actor": {"name": "tom creighton", "mbox": "mailto:tom@example.com"}})

        path = '%s?%s' % (reverse('lrs:statements'),
                          urllib.parse.urlencode({"statementId": stmt_id}))
        put_stmt = self.client.put(path, stmt, content_type="application/json",
                                   Authorization=self.auth, X_Experience_API_Version="1.0.")
        self.assertEqual(put_stmt.status_code, 400)

    def test_issue_put_wrong_version_header_1_1(self):
        stmt_id = '33f60b35-e1b2-4ddc-9c6f-7b3f65244432'
        stmt = json.dumps({"verb": {"id": "verb:completed"}, "object": {"id": "act:scorm.com/JsTetris_TCAPI/level2",
                                                                        "definition": {"type": "media", "name": {"en-US": "Js Tetris Level2"},
                                                                                       "description": {"en-US": "Starting at 1, the higher the level, the harder the game."}}},
                           "result": {"extensions": {"ext:time": 104, "ext:apm": 229, "ext:lines": 5}, "score": {"raw": 9911, "min": 0}},
                           "context": {"contextActivities": {"grouping": {"id": "act:scorm.com/JsTetris_TCAPI"}},
                                       "registration": "b7be7d9d-bfe2-4917-8ccd-41a0d18dd953"},
                           "actor": {"name": "tom creighton", "mbox": "mailto:tom@example.com"}})

        path = '%s?%s' % (reverse('lrs:statements'),
                          urllib.parse.urlencode({"statementId": stmt_id}))
        put_stmt = self.client.put(path, stmt, content_type="application/json",
                                   Authorization=self.auth, X_Experience_API_Version="1.1.")
        self.assertEqual(put_stmt.status_code, 400)

    # Use this test to make sure stmts are being returned correctly with all
    # data - doesn't check timestamp and stored fields
    def test_all_fields_activity_as_object(self):
        self.bunchostmts()
        nested_st_id = str(uuid.uuid4())
        nest_param = {"statementId": nested_st_id}
        nest_path = "%s?%s" % (reverse('lrs:statements'),
                               urllib.parse.urlencode(nest_param))
        nested_stmt = json.dumps({"actor": {"objectType": "Agent", "mbox": "mailto:tincan@adlnet.gov"},
                                  "verb": {"id": "http://example.com/verbs/assess", "display": {"en-US": "assessed"}},
                                  "object": {"id": "http://example.adlnet.gov/tincan/example/simplestatement"}})
        put_sub_stmt = self.client.put(nest_path, nested_stmt, content_type="application/json",
                                       Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(put_sub_stmt.status_code, 204)

        stmt_id = str(uuid.uuid4())
        context_id = str(uuid.uuid4())
        param = {"statementId": stmt_id}
        path = "%s?%s" % (reverse('lrs:statements'), urllib.parse.urlencode(param))
        stmt = json.dumps({"actor": {"objectType": "Agent", "name": "Lou Wolford", "account": {"homePage": "http://example.com", "name": "uniqueName"}},
                           "verb": {"id": "http://example.com/verbs/created", "display": {"en-US": "created", "en-GB": "made"}},
                           "object": {"objectType": "Activity", "id": "http:adlnet.gov/my/Activity/URL",
                                      "definition": {"name": {"en-US": "actName", "en-GB": "anotherActName"},
                                                     "description": {"en-US": "This is my activity description.", "en-GB": "This is another activity description."},
                                                     "type": "http://adlnet.gov/expapi/activities/cmi.interaction",
                                                     "moreInfo": "http://some/activity/url",
                                                     "interactionType": "choice",
                                                     "correctResponsesPattern": ["golf", "tetris"],
                                                     "choices": [{"id": "golf", "description": {"en-US": "Golf Example", "en-GB": "GOLF"}},
                                                                 {"id": "tetris", "description": {
                                                                     "en-US": "Tetris Example", "en-GB": "TETRIS"}},
                                                                 {"id": "facebook", "description": {
                                                                     "en-US": "Facebook App", "en-GB": "FACEBOOK"}},
                                                                 {"id": "scrabble", "description": {"en-US": "Scrabble Example", "en-GB": "SCRABBLE"}}],
                                                     "extensions": {"ext:key1": "value1", "ext:key2": "value2", "ext:key3": "value3"}}},
                           "result": {"score": {"scaled": .85, "raw": 85, "min": 0, "max": 100}, "completion": True, "success": False, "response": "Well done",
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
        param = {"statementId": stmt_id}
        get_response = self.client.get(
            path, X_Experience_API_Version=settings.XAPI_VERSION, Authorization=self.auth)

        the_returned = json.loads(get_response.content)
        self.assertEqual(the_returned['id'], stmt_id)
        self.assertEqual(the_returned['version'], '1.0.0')
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
        self.assertEqual(the_returned['result']['success'], False)

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

        self.assertEqual(the_returned['authority']['objectType'], 'Agent')
        self.assertEqual(the_returned['authority']['name'], 'tester1')
        self.assertEqual(the_returned['authority'][
                         'mbox'], 'mailto:test1@tester.com')

        self.assertEqual(the_returned['object'][
                         'id'], 'http:adlnet.gov/my/Activity/URL')
        self.assertEqual(the_returned['object']['objectType'], 'Activity')
        self.assertEqual(the_returned['object']['definition']['description'][
                         'en-US'], 'This is my activity description.')
        self.assertEqual(the_returned['object']['definition']['description'][
                         'en-GB'], 'This is another activity description.')
        self.assertEqual(the_returned['object']['definition'][
                         'interactionType'], 'choice')
        self.assertEqual(the_returned['object']['definition'][
                         'name']['en-US'], 'actName')
        self.assertEqual(the_returned['object']['definition'][
                         'name']['en-GB'], 'anotherActName')
        self.assertEqual(the_returned['object']['definition'][
                         'type'], 'http://adlnet.gov/expapi/activities/cmi.interaction')
        self.assertEqual(the_returned['object']['definition'][
                         'moreInfo'], 'http://some/activity/url')
        self.assertEqual(the_returned['object']['definition'][
                         'extensions']['ext:key1'], 'value1')
        self.assertEqual(the_returned['object']['definition'][
                         'extensions']['ext:key2'], 'value2')
        self.assertEqual(the_returned['object']['definition'][
                         'extensions']['ext:key3'], 'value3')
        # arrays.. testing slightly differently
        choices_str = json.dumps(the_returned['object'][
                                 'definition']['choices'])
        self.assertIn('description', choices_str)
        self.assertIn('id', choices_str)
        self.assertIn('GOLF', choices_str)
        self.assertIn('Golf Example', choices_str)
        self.assertIn('golf', choices_str)
        self.assertIn('TETRIS', choices_str)
        self.assertIn('Tetris Example', choices_str)
        self.assertIn('tetris', choices_str)
        self.assertIn('FACEBOOK', choices_str)
        self.assertIn('Facebook App', choices_str)
        self.assertIn('Facebook', choices_str)
        self.assertIn('SCRABBLE', choices_str)
        self.assertIn('Scrabble Example', choices_str)
        self.assertIn('scrabble', choices_str)

        crp_str = json.dumps(the_returned['object']['definition'][
                             'correctResponsesPattern'])
        self.assertIn('golf', crp_str)
        self.assertIn('tetris', crp_str)

    # Use this test to make sure stmts are being returned correctly with all
    # data - doesn't check timestamp, stored fields
    def test_all_fields_agent_as_object(self):
        nested_st_id = str(uuid.uuid4())
        nest_param = {"statementId": nested_st_id}
        nest_path = "%s?%s" % (reverse('lrs:statements'),
                               urllib.parse.urlencode(nest_param))
        nested_stmt = json.dumps({"actor": {"objectType": "Agent", "mbox": "mailto:tincan@adlnet.gov"},
                                  "verb": {"id": "http://example.com/verbs/assess", "display": {"en-US": "assessed"}},
                                  "object": {"id": "http://example.adlnet.gov/tincan/example/simplestatement"}})
        put_sub_stmt = self.client.put(nest_path, nested_stmt, content_type="application/json",
                                       Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(put_sub_stmt.status_code, 204)

        stmt_id = str(uuid.uuid4())
        context_id = str(uuid.uuid4())
        param = {"statementId": stmt_id}
        path = "%s?%s" % (reverse('lrs:statements'), urllib.parse.urlencode(param))
        msha = hashlib.sha1("mailto:tom@example.com").hexdigest()
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
        param = {"statementId": stmt_id}
        get_response = self.client.get(
            path, X_Experience_API_Version=settings.XAPI_VERSION, Authorization=self.auth)

        the_returned = json.loads(get_response.content)
        self.assertEqual(the_returned['id'], stmt_id)
        self.assertEqual(the_returned['version'], '1.0.0')
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

        self.assertEqual(the_returned['authority']['objectType'], 'Agent')
        self.assertEqual(the_returned['authority']['name'], 'tester1')
        self.assertEqual(the_returned['authority'][
                         'mbox'], 'mailto:test1@tester.com')

        self.assertEqual(the_returned['object']['objectType'], 'Agent')
        self.assertEqual(the_returned['object']['name'], 'Tom Creighton')
        self.assertEqual(the_returned['object']['mbox_sha1sum'], msha)

    # Use this test to make sure stmts are being returned correctly with all
    # data - doesn't check timestamps or stored fields
    def test_all_fields_substatement_as_object(self):
        nested_st_id = str(uuid.uuid4())
        nest_param = {"statementId": nested_st_id}
        nest_path = "%s?%s" % (reverse('lrs:statements'),
                               urllib.parse.urlencode(nest_param))
        nested_stmt = json.dumps({"actor": {"objectType": "Agent", "mbox": "mailto:tincannest@adlnet.gov"},
                                  "verb": {"id": "http://example.com/verbs/assess", "display": {"en-US": "assessed", "en-GB": "graded"}},
                                  "object": {"id": "http://example.adlnet.gov/tincan/example/simplestatement"}})
        put_sub_stmt = self.client.put(nest_path, nested_stmt, content_type="application/json",
                                       Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(put_sub_stmt.status_code, 204)

        nested_sub_st_id = str(uuid.uuid4())
        nest_sub_param = {"statementId": nested_sub_st_id}
        nest_sub_path = "%s?%s" % (
            reverse('lrs:statements'), urllib.parse.urlencode(nest_sub_param))
        nested_sub_stmt = json.dumps({"actor": {"objectType": "Agent", "mbox": "mailto:tincannestsub@adlnet.gov"},
                                      "verb": {"id": "http://example.com/verbs/verb", "display": {"en-US": "verb", "en-GB": "altVerb"}},
                                      "object": {"id": "http://example.adlnet.gov/tincan/example/simplenestedsubstatement"}})
        put_nest_sub_stmt = self.client.put(nest_sub_path, nested_sub_stmt, content_type="application/json",
                                            Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(put_nest_sub_stmt.status_code, 204)

        stmt_id = str(uuid.uuid4())
        context_id = str(uuid.uuid4())
        sub_context_id = str(uuid.uuid4())
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
                                                  "revision": "Spelling error in target.", "platform": "Ipad.", "language": "en-US",
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
        param = {"statementId": stmt_id}
        get_response = self.client.get(
            path, X_Experience_API_Version=settings.XAPI_VERSION, Authorization=self.auth)

        the_returned = json.loads(get_response.content)
        self.assertEqual(the_returned['id'], stmt_id)
        self.assertEqual(the_returned['version'], '1.0.0')
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
        self.assertEqual(the_returned['object'][
                         'context']['platform'], 'Ipad.')
        self.assertEqual(the_returned['object']['context'][
                         'revision'], 'Spelling error in target.')
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
        self.assertEqual(the_returned['context']['statement'][
                         'id'], str(nested_st_id))
        self.assertEqual(the_returned['context']['statement'][
                         'objectType'], 'StatementRef')

        self.assertEqual(the_returned['authority']['objectType'], 'Agent')
        self.assertEqual(the_returned['authority']['name'], 'tester1')
        self.assertEqual(the_returned['authority'][
                         'mbox'], 'mailto:test1@tester.com')

    # Third stmt in list is missing actor - should throw error and perform
    # cascading delete on first three statements
    def test_post_list_rollback(self):
        self.bunchostmts()
        cguid1 = str(uuid.uuid4())
        stmts = json.dumps([
            {"verb": {"id": "http://example.com/verbs/wrong-failed", "display": {"en-US": "wrong-failed"}},
             "object": {"id": "act:test_wrong_list_post2"}, "actor": {"objectType": "Agent",
                                                                      "mbox": "mailto:wrong-t@t.com"}, "result": {"score": {"scaled": .99}, "completion": True, "success": True,
                                                                                                                  "response": "wrong", "extensions": {"ext:resultwrongkey1": "value1", "ext:resultwrongkey2": "value2"}}},
            {"verb": {"id": "http://example.com/verbs/wrong-kicked", "display": {"en-US": "wrong-kicked"}},
             "object": {"objectType": "Activity", "id": "act:test_wrong_list_post",
                        "definition": {"name": {"en-US": "wrongactName", "en-GB": "anotherActName"},
                                       "description": {"en-US": "This is my activity description.", "en-GB": "This is another activity description."},
                                       "type": "http://www.adlnet.gov/experienceapi/activity-types/http://adlnet.gov/expapi/activities/cmi.interaction",
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
        self.bunchostmts()
        stmts = json.dumps([{"object": {"objectType": "Agent", "name": "john", "mbox": "mailto:john@john.com"},
                             "verb": {"id": "http://example.com/verbs/wrong", "display": {"en-US": "wrong"}},
                             "actor": {"objectType": "Agent", "mbox": "mailto:s@s.com"}},
                            {"verb": {"id": "http://example.com/verbs/created"},
                             "object": {"objectType": "Activity", "id": "act:foogie",
                                        "definition": {"name": {"en-US": "testname2", "en-GB": "altname"},
                                                       "description": {"en-US": "testdesc2", "en-GB": "altdesc"}, "type": "http://www.adlnet.gov/experienceapi/activity-types/http://adlnet.gov/expapi/activities/cmi.interaction",
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
        self.assertEqual(len(wrong_verbs), 0)

        self.assertEqual(len(activities), 1)

        self.assertEqual(len(stmts), 11)

        self.assertEqual(len(wrong_agent), 0)
        self.assertEqual(len(john_agent), 1)
        self.assertEqual(len(s_agent), 1)

        self.assertEqual(len(auth_agent), 1)

    def test_post_list_rollback_with_void(self):
        self.bunchostmts()
        stmts = json.dumps([{"actor": {"objectType": "Agent", "mbox": "mailto:only-s@s.com"},
                             "object": {"objectType": "StatementRef", "id": str(self.exist_stmt_id)},
                             "verb": {"id": "http://adlnet.gov/expapi/verbs/voided", "display": {"en-US": "voided"}}},
                            {"verb": {"id": "http://example.com/verbs/wrong-kicked"}, "object": {"id": "act:test_wrong_list_post2"}}])

        response = self.client.post(reverse('lrs:statements'), stmts, content_type="application/json",
                                    Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(response.status_code, 400)
        self.assertIn('actor is missing in Statement', response.content)
        voided_st = Statement.objects.get(statement_id=self.exist_stmt_id)
        voided_verb = Verb.objects.filter(verb_id__contains='voided')
        only_actor = Agent.objects.filter(mbox="mailto:only-s@s.com")
        stmts = Statement.objects.all()

        self.assertEqual(len(stmts), 11)
        self.assertEqual(voided_st.voided, False)
        self.assertEqual(len(voided_verb), 0)
        self.assertEqual(len(only_actor), 0)

    def test_post_list_rollback_with_subs(self):
        self.bunchostmts()
        sub_context_id = str(uuid.uuid4())
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

    def test_post_list_rollback_context_activities(self):
        self.bunchostmts()
        sub_context_id = str(uuid.uuid4())
        # Will throw error and need to rollback b/c last stmt is missing actor
        stmts = json.dumps([{
            "actor": {"objectType": "Agent", "mbox": "mailto:wrong-s@s.com"},
            "verb": {"id": "http://example.com/verbs/wrong", "display": {"en-US": "wrong"}},
            "object": {"objectType": "Agent", "name": "john", "mbox": "mailto:john@john.com"}},
            {
            "actor": {"objectType": "Agent", "mbox": "mailto:s@s.com"},
            "verb": {"id": "http://example.com/verbs/wrong-next", "display": {"en-US": "wrong-next"}},
            "object": {
                "objectType": "SubStatement",
                "actor": {"objectType": "Agent", "mbox": "mailto:wrong-ss@ss.com"},
                "verb": {"id": "http://example.com/verbs/wrong-sub"},
                "object": {"objectType": "Activity", "id": "act:wrong-testex.com"},
                "result": {"completion": True, "success": True, "response": "sub-wrong-kicked"},
                "context": {
                    "registration": sub_context_id,
                    "contextActivities": {
                        "other": [{"id": "act:subwrongActivityID"}, {"id": "act:foogie"}]},
                    "revision": "foo", "platform": "bar", "language": "en-US",
                    "extensions": {"ext:wrong-k1": "v1", "ext:wrong-k2": "v2"}}
            }
        },
            {
            "verb": {"id": "http://example.com/verbs/wrong-kicked"},
            "object": {"id": "act:test_wrong_list_post2"}}])

        response = self.client.post(reverse('lrs:statements'), stmts, content_type="application/json",
                                    Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(response.status_code, 400)
        self.assertIn('actor is missing in Statement', response.content)

        s_agent = Agent.objects.filter(mbox="mailto:wrong-s@s.com")
        ss_agent = Agent.objects.filter(mbox="mailto:wrong-ss@ss.com")
        john_agent = Agent.objects.filter(mbox="mailto:john@john.com")
        subs = SubStatement.objects.all()
        wrong_verb = Verb.objects.filter(verb_id__contains="wrong")
        wrong_activities = Activity.objects.filter(
            activity_id__contains="wrong")
        foogie_activities = Activity.objects.filter(
            activity_id__exact="act:foogie")
        stmts = Statement.objects.all()

        self.assertEqual(len(stmts), 11)
        self.assertEqual(len(s_agent), 0)
        self.assertEqual(len(ss_agent), 0)
        self.assertEqual(len(john_agent), 1)
        # Only 1 sub from setup
        self.assertEqual(len(subs), 1)
        self.assertEqual(len(wrong_verb), 0)
        self.assertEqual(len(wrong_activities), 0)
        self.assertEqual(len(foogie_activities), 1)

    def test_unique_actor_authority(self):
        stmt = json.dumps({"actor": {"objectType": "Agent", "mbox": "mailto:timmay@timmay.com", "name": "timmay"},
                           "verb": {"id": "http://example.com/verbs/passed", "display": {"en-US": "passed"}},
                           "object": {"id": "act:test_post"}})

        response = self.client.post(reverse('lrs:statements'), stmt, content_type="application/json",
                                    Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(response.status_code, 200)

        response2 = self.client.post(reverse('lrs:statements'), stmt, content_type="application/json",
                                     Authorization=self.auth2, X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(response2.status_code, 200)

        acts = Activity.objects.filter(activity_id='act:test_post').count()
        self.assertEqual(acts, 1)

    def test_stmts_w_same_regid(self):
        stmt1_guid = str(uuid.uuid4())
        stmt2_guid = str(uuid.uuid4())
        reg_guid = str(uuid.uuid4())
        stmt1 = json.dumps({"actor": {"mbox": "mailto:tom@example.com"},
                            "verb": {"id": "http:adlnet.gov/expapi/verbs/tested",
                                     "display": {"en-US": "tested"}},
                            "object": {"id": "test:same.regid"},
                            "context": {"registration": reg_guid}
                            })
        stmt2 = json.dumps({"actor": {"mbox": "mailto:tom@example.com"},
                            "verb": {"id": "http:adlnet.gov/expapi/verbs/tested",
                                     "display": {"en-US": "tested"}},
                            "object": {"id": "test:same.regid.again"},
                            "context": {"registration": reg_guid}
                            })

        param1 = {"statementId": stmt1_guid}
        path1 = "%s?%s" % (reverse('lrs:statements'), urllib.parse.urlencode(param1))
        stmt_payload1 = stmt1
        resp1 = self.client.put(path1, stmt_payload1, content_type="application/json",
                                Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(resp1.status_code, 204)

        param2 = {"statementId": stmt2_guid}
        path2 = "%s?%s" % (reverse('lrs:statements'), urllib.parse.urlencode(param2))
        stmt_payload2 = stmt2
        resp2 = self.client.put(path2, stmt_payload2, content_type="application/json",
                                Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(resp2.status_code, 204)

    @override_settings(CELERY_ALWAYS_EAGER=True,
                       TEST_RUNNER='djcelery.contrib.test_runner.CeleryTestSuiteRunner')
    def test_void(self):
        stmt_guid = str(uuid.uuid4())
        stmt = {"actor": {"mbox": "mailto:tinytom@example.com"},
                "verb": {"id": "http://tommy.com/my-testverbs/danced",
                         "display": {"en-US": "danced"}},
                "object": {"id": "act:the-macarena"}}
        param = {"statementId": stmt_guid}
        path = "%s?%s" % (reverse('lrs:statements'), urllib.parse.urlencode(param))
        payload = json.dumps(stmt)

        r = self.client.put(path, payload, content_type="application/json",
                            Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(r.status_code, 204)

        r = self.client.get(reverse('lrs:statements'), Authorization=self.auth,
                            X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(r.status_code, 200)
        obj = json.loads(r.content)

        self.assertEqual(len(obj['statements']), 1)
        obj = obj['statements'][0]
        self.assertEqual(obj['id'], stmt_guid)
        self.assertEqual(obj['actor']['mbox'], stmt['actor']['mbox'])
        self.assertEqual(obj['verb'], stmt['verb'])
        self.assertEqual(obj['object']['id'], stmt['object']['id'])

        stmt2_guid = str(uuid.uuid4())
        stmt2 = {"actor": {"mbox": "mailto:louo@example.com"},
                 "verb": {"id": "http://tommy.com/my-testverbs/laughed",
                          "display": {"en-US": "laughed at"}},
                 "object": {"objectType": "StatementRef", "id": stmt_guid}}
        param = {"statementId": stmt2_guid}
        path = "%s?%s" % (reverse('lrs:statements'), urllib.parse.urlencode(param))
        payload2 = json.dumps(stmt2)

        r = self.client.put(path, payload2, content_type="application/json",
                            Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(r.status_code, 204)

        r = self.client.get(reverse('lrs:statements'), Authorization=self.auth,
                            X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(r.status_code, 200)
        obj = json.loads(r.content)
        self.assertEqual(len(obj['statements']), 2)
        objs = obj['statements']
        for o in objs:
            if o['id'] == stmt_guid:
                self.assertEqual(o['actor']['mbox'], stmt['actor']['mbox'])
                self.assertEqual(o['verb']['id'], stmt['verb']['id'])
                self.assertEqual(o['object']['id'], stmt['object']['id'])
            else:
                self.assertEqual(o['actor']['mbox'], stmt2['actor']['mbox'])
                self.assertEqual(o['verb']['id'], stmt2['verb']['id'])
                self.assertEqual(o['object']['id'], stmt2['object']['id'])

        stmtv = {"actor": {"mbox": "mailto:hulk@example.com"},
                 "verb": {"id": "http://adlnet.gov/expapi/verbs/voided"},
                 "object": {"objectType": "StatementRef",
                            "id": "%s" % stmt_guid}}
        v_guid = str(uuid.uuid4())
        paramv = {"statementId": v_guid}
        path = "%s?%s" % (reverse('lrs:statements'), urllib.parse.urlencode(paramv))
        vpayload = json.dumps(stmtv)

        r = self.client.put(path, vpayload, content_type="application/json",
                            Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(r.status_code, 204)

        r = self.client.get(reverse('lrs:statements'), Authorization=self.auth,
                            X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(r.status_code, 200)
        obj = json.loads(r.content)
        self.assertEqual(len(obj['statements']), 2)
        objs = obj['statements']
        for o in objs:
            if o['id'] == v_guid:
                self.assertEqual(o['actor']['mbox'], stmtv['actor']['mbox'])
                self.assertEqual(o['verb']['id'], stmtv['verb']['id'])
                self.assertEqual(o['object']['id'], stmtv['object']['id'])
            else:
                self.assertEqual(o['actor']['mbox'], stmt2['actor']['mbox'])
                self.assertEqual(o['verb']['id'], stmt2['verb']['id'])
                self.assertEqual(o['object']['id'], stmt2['object']['id'])

        # get voided statement via voidedStatementId
        path = "%s?%s" % (reverse('lrs:statements'), urllib.parse.urlencode(
            {"voidedStatementId": stmt_guid}))
        r = self.client.get(path, Authorization=self.auth,
                            X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(r.status_code, 200)
        obj = json.loads(r.content)
        self.assertEqual(obj['id'], stmt_guid)
        self.assertEqual(obj['actor']['mbox'], stmt['actor']['mbox'])
        self.assertEqual(obj['verb']['id'], stmt['verb']['id'])
        self.assertEqual(obj['object']['id'], stmt['object']['id'])

        # make sure voided statement returns a 404 on get w/ statementId req
        path = "%s?%s" % (reverse('lrs:statements'),
                          urllib.parse.urlencode({"statementId": stmt_guid}))
        r = self.client.get(path, Authorization=self.auth,
                            X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(r.status_code, 404)

    def test_act_id_iri(self):
        act_id = "act:Flügel"
        stmt = json.dumps({"actor": {"objectType": "Agent", "mbox": "mailto:s@s.com"},
                           "verb": {"id": "http://example.com/verbs/created", "display": {"en-US": "created"}},
                           "object": {"id": act_id}})
        response = self.client.post(reverse('lrs:statements'), stmt, content_type="application/json",
                                    Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)

        self.assertEqual(response.status_code, 200)
        stmt_db = Statement.objects.get(
            statement_id=uuid.UUID(json.loads(response.content)[0]))
        act = Activity.objects.get(id=stmt_db.object_activity.id)
        self.assertEqual(act.activity_id.encode('utf-8'), act_id)

    def test_invalid_act_id_iri(self):
        act_id = "Flügel"
        stmt = json.dumps({"actor": {"objectType": "Agent", "mbox": "mailto:s@s.com"},
                           "verb": {"id": "http://example.com/verbs/created", "display": {"en-US": "created"}},
                           "object": {"id": act_id}})
        response = self.client.post(reverse('lrs:statements'), stmt, content_type="application/json",
                                    Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(response.status_code, 400)
        self.assertIn('not a valid IRI', response.content)

    def test_tag_act_id_uri(self):
        act_id = "tag:adlnet.gov,2013:expapi:0.9:activities"
        stmt = json.dumps({"actor": {"objectType": "Agent", "mbox": "mailto:s@s.com"},
                           "verb": {"id": "http://example.com/verbs/created", "display": {"en-US": "created"}},
                           "object": {"id": act_id}})

        response = self.client.post(reverse('lrs:statements'), stmt, content_type="application/json",
                                    Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)

        self.assertEqual(response.status_code, 200)
        stmt_db = Statement.objects.get(
            statement_id=uuid.UUID(json.loads(response.content)[0]))
        act = Activity.objects.get(id=stmt_db.object_activity.id)
        self.assertEqual(act.activity_id, act_id)

    @override_settings(CELERY_ALWAYS_EAGER=True,
                       TEST_RUNNER='djcelery.contrib.test_runner.CeleryTestSuiteRunner')
    def test_large_batch(self):
        import random
        post_payload = []
        acts = ["http://tom.com/act/1/foo", "http://adlnet.gov/act/arrgs/2",
                "http://google.com/activity/eats/ants", "http://tom.com/act/3/boo"]
        ctxs = ["http://ctx.com/one", "http://ctx.com/two"]

        for x in range(1, 500):
            s = {"verb": {"id": "http://example.com/verbs/passed"}, "object": {"id": ""}, "actor": {"mbox": "mailto:t@t.com"},
                 "context": {"contextActivities": {"grouping": [{"id": ""}]}}}

            s['object']['id'] = acts[random.randrange(0, len(acts) - 1)]
            s['context']['contextActivities']['grouping'][0][
                'id'] = ctxs[random.randrange(0, len(ctxs) - 1)]
            post_payload.append(s)

        response = self.client.post(reverse('lrs:statements'), json.dumps(post_payload), content_type="application/json",
                                    Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(response.status_code, 200)
