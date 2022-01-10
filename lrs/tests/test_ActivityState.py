import hashlib
import urllib.request, urllib.parse, urllib.error
import os
import json
import base64
import ast
import uuid

from django.test import TestCase
from django.conf import settings
from django.urls import reverse

from adl_lrs.views import register


class ActivityStateTests(TestCase):
    url = reverse('lrs:activity_state')
    testagent = '{"name":"test","mbox":"mailto:test@example.com"}'
    otheragent = '{"name":"other","mbox":"mailto:other@example.com"}'
    activityId = "http://www.iana.org/domains/example/"
    activityId2 = "http://www.google.com"
    stateId = "the_state_id"
    stateId2 = "state_id_2"
    stateId3 = "third_state_id"
    stateId4 = "4th.id"
    registration = str(uuid.uuid1())
    content_type = "application/json"

    @classmethod
    def setUpClass(cls):
        print("\n%s" % __name__)
        super(ActivityStateTests, cls).setUpClass()

    def setUp(self):
        self.username = "test"
        self.email = "test@example.com"
        self.password = "test"
        self.auth = "Basic %s" % base64.b64encode(
            "%s:%s" % (self.username, self.password))
        form = {'username': self.username, 'email': self.email,
                'password': self.password, 'password2': self.password}
        self.client.post(reverse(register), form,
                         X_Experience_API_Version=settings.XAPI_VERSION)

        self.testparams1 = {"stateId": self.stateId,
                            "activityId": self.activityId, "agent": self.testagent}
        path = '%s?%s' % (self.url, urllib.parse.urlencode(self.testparams1))
        self.teststate1 = {"test": "put activity state 1",
                           "obj": {"agent": "test"}}
        self.put1 = self.client.put(path, json.dumps(self.teststate1), content_type=self.content_type,
                                    Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)

        self.testparams2 = {"stateId": self.stateId2,
                            "activityId": self.activityId, "agent": self.testagent}
        path = '%s?%s' % (self.url, urllib.parse.urlencode(self.testparams2))
        self.teststate2 = {"test": "put activity state 2",
                           "obj": {"agent": "test"}}
        self.put2 = self.client.put(path, json.dumps(self.teststate2), content_type=self.content_type,
                                    Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)

        self.testparams3 = {"stateId": self.stateId3,
                            "activityId": self.activityId2, "agent": self.testagent}
        path = '%s?%s' % (self.url, urllib.parse.urlencode(self.testparams3))
        self.teststate3 = {"test": "put activity state 3",
                           "obj": {"agent": "test"}}
        self.put3 = self.client.put(path, json.dumps(self.teststate3), content_type=self.content_type,
                                    Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)

        self.testparams4 = {"stateId": self.stateId4,
                            "activityId": self.activityId2, "agent": self.otheragent}
        path = '%s?%s' % (self.url, urllib.parse.urlencode(self.testparams4))
        self.teststate4 = {"test": "put activity state 4",
                           "obj": {"agent": "other"}}
        self.put4 = self.client.put(path, json.dumps(self.teststate4), content_type=self.content_type,
                                    Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)

    def tearDown(self):
        self.client.delete(self.url, self.testparams1, Authorization=self.auth,
                           X_Experience_API_Version=settings.XAPI_VERSION)
        self.client.delete(self.url, self.testparams2, Authorization=self.auth,
                           X_Experience_API_Version=settings.XAPI_VERSION)
        self.client.delete(self.url, self.testparams3, Authorization=self.auth,
                           X_Experience_API_Version=settings.XAPI_VERSION)
        self.client.delete(self.url, self.testparams4, Authorization=self.auth,
                           X_Experience_API_Version=settings.XAPI_VERSION)

        attach_folder_path = os.path.join(
            settings.MEDIA_ROOT, "activity_state")
        for the_file in os.listdir(attach_folder_path):
            file_path = os.path.join(attach_folder_path, the_file)
            try:
                os.unlink(file_path)
            except Exception as e:
                raise e

    def test_put(self):
        self.assertEqual(self.put1.status_code, 204)
        self.assertEqual(self.put1.content, '')

        self.assertEqual(self.put2.status_code, 204)
        self.assertEqual(self.put2.content, '')

        self.assertEqual(self.put3.status_code, 204)
        self.assertEqual(self.put3.content, '')

        self.assertEqual(self.put4.status_code, 204)
        self.assertEqual(self.put4.content, '')

    def test_put_no_existing_activity(self):
        testparams = {"stateId": self.stateId3,
                      "activityId": "http://foobar", "agent": self.testagent}
        path = '%s?%s' % (self.url, urllib.parse.urlencode(testparams))
        teststate = {"test": "put activity state", "obj": {"agent": "test"}}
        put = self.client.put(path, teststate, content_type=self.content_type,
                              Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)

        self.assertEqual(put.status_code, 204)
        self.client.delete(path, Authorization=self.auth,
                           X_Experience_API_Version=settings.XAPI_VERSION)

    def test_put_with_registration(self):
        testparamsregid = {"registration": "not-uuid", "stateId": self.stateId,
                           "activityId": self.activityId, "agent": self.testagent}
        path = '%s?%s' % (self.url, urllib.parse.urlencode(testparamsregid))
        teststateregid = {
            "test": "put activity state w/ registration", "obj": {"agent": "test"}}
        put1 = self.client.put(path, teststateregid, content_type=self.content_type,
                               Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)

        self.assertEqual(put1.status_code, 400)

        testparamsregid = {"registration": self.registration, "stateId": self.stateId,
                           "activityId": self.activityId, "agent": self.testagent}
        path = '%s?%s' % (self.url, urllib.parse.urlencode(testparamsregid))
        teststateregid = {
            "test": "put activity state w/ registration", "obj": {"agent": "test"}}

        put1 = self.client.put(path, teststateregid, content_type=self.content_type,
                               Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)

        self.assertEqual(put1.status_code, 204)
        self.assertEqual(put1.content, '')

        # also testing get w/ registration id
        r = self.client.get(self.url, testparamsregid,
                            X_Experience_API_Version=settings.XAPI_VERSION, Authorization=self.auth)
        self.assertEqual(r.status_code, 200)
        robj = ast.literal_eval(r.content)
        self.assertEqual(robj['test'], teststateregid['test'])
        self.assertEqual(robj['obj']['agent'], teststateregid['obj']['agent'])
        self.assertEqual(r['etag'], '"%s"' %
                         hashlib.sha1(r.content).hexdigest())

        # and tests delete w/ registration id
        del_r = self.client.delete(
            self.url, testparamsregid, Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(del_r.status_code, 204)

    def test_put_without_auth(self):
        testparamsregid = {"registration": self.registration, "stateId": self.stateId,
                           "activityId": self.activityId, "agent": self.testagent}
        path = '%s?%s' % (self.url, urllib.parse.urlencode(testparamsregid))
        teststateregid = {
            "test": "put activity state w/ registration", "obj": {"agent": "test"}}
        put1 = self.client.put(path, teststateregid, content_type=self.content_type,
                               X_Experience_API_Version=settings.XAPI_VERSION)

        self.assertEqual(put1.status_code, 400)

    def test_put_without_activityid(self):
        testparamsbad = {"stateId": "bad_state", "agent": self.testagent}
        path = '%s?%s' % (self.url, urllib.parse.urlencode(testparamsbad))
        teststatebad = {
            "test": "put activity state BAD no activity id", "obj": {"agent": "test"}}
        put1 = self.client.put(path, teststatebad, content_type=self.content_type,
                               Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)

        self.assertEqual(put1.status_code, 400)
        self.assertIn('activityId parameter is missing', put1.content)

    def test_put_without_agent(self):
        testparamsbad = {"stateId": "bad_state", "activityId": self.activityId}
        path = '%s?%s' % (self.url, urllib.parse.urlencode(testparamsbad))
        teststatebad = {
            "test": "put activity state BAD no agent", "obj": {"agent": "none"}}
        put1 = self.client.put(path, teststatebad, content_type=self.content_type,
                               Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)

        self.assertEqual(put1.status_code, 400)
        self.assertIn('agent parameter is missing', put1.content)

    def test_put_without_stateid(self):
        testparamsbad = {"activityId": self.activityId,
                         "agent": self.testagent}
        path = '%s?%s' % (self.url, urllib.parse.urlencode(testparamsbad))
        teststatebad = {
            "test": "put activity state BAD no state id", "obj": {"agent": "test"}}
        put1 = self.client.put(path, teststatebad, content_type=self.content_type,
                               Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)

        self.assertEqual(put1.status_code, 400)
        self.assertIn('stateId parameter is missing', put1.content)

    # Also tests 403 forbidden status
    def test_get(self):
        username = "other"
        email = "other@example.com"
        password = "test"
        auth = "Basic %s" % base64.b64encode("%s:%s" % (username, password))
        form = {'username': username, 'email': email,
                'password': password, 'password2': password}
        self.client.post(reverse(register), form,
                         X_Experience_API_Version=settings.XAPI_VERSION)

        r = self.client.get(self.url, self.testparams1,
                            X_Experience_API_Version=settings.XAPI_VERSION, Authorization=self.auth)
        self.assertEqual(r.status_code, 200)
        robj = ast.literal_eval(r.content)
        self.assertEqual(robj['test'], self.teststate1['test'])
        self.assertEqual(robj['obj']['agent'], self.teststate1['obj']['agent'])
        self.assertEqual(r['etag'], '"%s"' %
                         hashlib.sha1(r.content).hexdigest())

        r2 = self.client.get(self.url, self.testparams2,
                             X_Experience_API_Version=settings.XAPI_VERSION, Authorization=self.auth)
        self.assertEqual(r2.status_code, 200)
        robj2 = ast.literal_eval(r2.content)
        self.assertEqual(robj2['test'], self.teststate2['test'])
        self.assertEqual(robj2['obj']['agent'],
                         self.teststate2['obj']['agent'])
        self.assertEqual(r2['etag'], '"%s"' %
                         hashlib.sha1(r2.content).hexdigest())

        r3 = self.client.get(self.url, self.testparams3,
                             X_Experience_API_Version=settings.XAPI_VERSION, Authorization=self.auth)
        self.assertEqual(r3.status_code, 200)
        robj3 = ast.literal_eval(r3.content)
        self.assertEqual(robj3['test'], self.teststate3['test'])
        self.assertEqual(robj3['obj']['agent'],
                         self.teststate3['obj']['agent'])
        self.assertEqual(r3['etag'], '"%s"' %
                         hashlib.sha1(r3.content).hexdigest())

        r4 = self.client.get(self.url, self.testparams4,
                             X_Experience_API_Version=settings.XAPI_VERSION, Authorization=auth)
        self.assertEqual(r4.status_code, 200)
        robj4 = ast.literal_eval(r4.content)
        self.assertEqual(robj4['test'], self.teststate4['test'])
        self.assertEqual(robj4['obj']['agent'],
                         self.teststate4['obj']['agent'])
        self.assertEqual(r4['etag'], '"%s"' %
                         hashlib.sha1(r4.content).hexdigest())

        # r5 = self.client.get(self.url, self.testparams3, X_Experience_API_Version=settings.XAPI_VERSION, Authorization=auth)
        # self.assertEqual(r5.status_code, 403)

    def test_get_no_existing_id(self):
        testparams = {"stateId": "testID",
                      "activityId": self.activityId, "agent": self.testagent}
        r = self.client.get(
            self.url, testparams, X_Experience_API_Version=settings.XAPI_VERSION, Authorization=self.auth)
        self.assertEqual(r.status_code, 404)

    def test_get_ids(self):
        params = {"activityId": self.activityId, "agent": self.testagent}
        r = self.client.get(
            self.url, params, X_Experience_API_Version=settings.XAPI_VERSION, Authorization=self.auth)
        self.assertEqual(r.status_code, 200)
        self.assertIn(self.stateId, r.content)
        self.assertIn(self.stateId2, r.content)
        self.assertNotIn(self.stateId3, r.content)
        self.assertNotIn(self.stateId4, r.content)

    def test_get_with_since(self):
        state_id = "old_state_test"
        testparamssince = {"stateId": state_id,
                           "activityId": self.activityId, "agent": self.testagent}
        path = '%s?%s' % (self.url, urllib.parse.urlencode(testparamssince))
        teststatesince = {"test": "get w/ since", "obj": {"agent": "test"}}
        updated = "2012-06-12T12:00:00Z"
        put1 = self.client.put(path, teststatesince, content_type=self.content_type, updated=updated,
                               Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)

        self.assertEqual(put1.status_code, 204)
        self.assertEqual(put1.content, '')

        r = self.client.get(self.url, testparamssince,
                            X_Experience_API_Version=settings.XAPI_VERSION, Authorization=self.auth)
        self.assertEqual(r.status_code, 200)

        robj = ast.literal_eval(r.content)
        self.assertEqual(robj['test'], teststatesince['test'])
        self.assertEqual(robj['obj']['agent'], teststatesince['obj']['agent'])
        self.assertEqual(r['etag'], '"%s"' %
                         hashlib.sha1(r.content).hexdigest())

        since = "2012-07-01T12:00:00Z"
        params2 = {"activityId": self.activityId,
                   "agent": self.testagent, "since": since}
        r = self.client.get(
            self.url, params2, X_Experience_API_Version=settings.XAPI_VERSION, Authorization=self.auth)
        self.assertEqual(r.status_code, 200)
        self.assertIn(self.stateId, r.content)
        self.assertIn(self.stateId2, r.content)
        self.assertNotIn(state_id, r.content)
        self.assertNotIn(self.stateId3, r.content)
        self.assertNotIn(self.stateId4, r.content)

        self.client.delete(self.url, testparamssince, Authorization=self.auth,
                           X_Experience_API_Version=settings.XAPI_VERSION)

    def test_get_with_since_tz(self):
        state_id = "old_state_test"
        testparamssince = {"stateId": state_id,
                           "activityId": self.activityId, "agent": self.testagent}
        path = '%s?%s' % (self.url, urllib.parse.urlencode(testparamssince))
        teststatesince = {"test": "get w/ since", "obj": {"agent": "test"}}
        updated = "2012-06-12:T12:00:00Z"
        put1 = self.client.put(path, teststatesince, content_type=self.content_type, updated=updated,
                               Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)

        self.assertEqual(put1.status_code, 204)
        self.assertEqual(put1.content, '')

        r = self.client.get(self.url, testparamssince,
                            X_Experience_API_Version=settings.XAPI_VERSION, Authorization=self.auth)
        self.assertEqual(r.status_code, 200)

        robj = ast.literal_eval(r.content)
        self.assertEqual(robj['test'], teststatesince['test'])
        self.assertEqual(robj['obj']['agent'], teststatesince['obj']['agent'])
        self.assertEqual(r['etag'], '"%s"' %
                         hashlib.sha1(r.content).hexdigest())

        state_id2 = "new_tz_state_test"
        testparamssince2 = {"stateId": state_id2,
                            "activityId": self.activityId, "agent": self.testagent}
        path = '%s?%s' % (self.url, urllib.parse.urlencode(testparamssince2))
        teststatesince2 = {"test": "get w/ since TZ", "obj": {"agent": "test"}}
        updated_tz = "2012-07-01T13:30:00+04:00"
        put2 = self.client.put(path, teststatesince2, content_type=self.content_type, updated=updated_tz,
                               Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)

        self.assertEqual(put2.status_code, 204)
        self.assertEqual(put2.content, '')

        r2 = self.client.get(self.url, testparamssince2,
                             X_Experience_API_Version=settings.XAPI_VERSION, Authorization=self.auth)
        self.assertEqual(r2.status_code, 200)

        robj2 = ast.literal_eval(r2.content)
        self.assertEqual(robj2['test'], teststatesince2['test'])
        self.assertEqual(robj2['obj']['agent'],
                         teststatesince2['obj']['agent'])
        self.assertEqual(r2['etag'], '"%s"' %
                         hashlib.sha1(r2.content).hexdigest())

        since = "2012-07-01T12:00:00Z"
        params2 = {"activityId": self.activityId,
                   "agent": self.testagent, "since": since}
        r = self.client.get(
            self.url, params2, X_Experience_API_Version=settings.XAPI_VERSION, Authorization=self.auth)
        self.assertEqual(r.status_code, 200)
        self.assertIn(self.stateId, r.content)
        self.assertIn(self.stateId2, r.content)
        self.assertNotIn(state_id, r.content)
        self.assertNotIn(state_id2, r.content)
        self.assertNotIn(self.stateId3, r.content)
        self.assertNotIn(self.stateId4, r.content)

        self.client.delete(self.url, testparamssince, Authorization=self.auth,
                           X_Experience_API_Version=settings.XAPI_VERSION)
        self.client.delete(self.url, testparamssince2, Authorization=self.auth,
                           X_Experience_API_Version=settings.XAPI_VERSION)

    def test_get_with_since_and_regid(self):
        # create old state w/ no registration id
        state_id = "old_state_test_no_reg"
        testparamssince = {"stateId": state_id,
                           "activityId": self.activityId, "agent": self.testagent}
        path = '%s?%s' % (self.url, urllib.parse.urlencode(testparamssince))
        teststatesince = {"test": "get w/ since",
                          "obj": {"agent": "test", "stateId": state_id}}
        updated = "2012-06-12:T12:00:00Z"
        put1 = self.client.put(path, teststatesince, content_type=self.content_type, updated=updated,
                               Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)

        self.assertEqual(put1.status_code, 204)
        self.assertEqual(put1.content, '')

        r = self.client.get(self.url, testparamssince,
                            X_Experience_API_Version=settings.XAPI_VERSION, Authorization=self.auth)
        self.assertEqual(r.status_code, 200)

        robj = ast.literal_eval(r.content)
        self.assertEqual(robj['test'], teststatesince['test'])
        self.assertEqual(robj['obj']['agent'], teststatesince['obj']['agent'])
        self.assertEqual(r['etag'], '"%s"' %
                         hashlib.sha1(r.content).hexdigest())

        # create old state w/ registration id
        regid = str(uuid.uuid1())
        state_id2 = "old_state_test_w_reg"
        testparamssince2 = {"registration": regid, "activityId": self.activityId,
                            "agent": self.testagent, "stateId": state_id2}
        path = '%s?%s' % (self.url, urllib.parse.urlencode(testparamssince2))
        teststatesince2 = {"test": "get w/ since and registration",
                           "obj": {"agent": "test", "stateId": state_id2}}
        put2 = self.client.put(path, teststatesince2, content_type=self.content_type, updated=updated,
                               Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)

        self.assertEqual(put2.status_code, 204)
        self.assertEqual(put2.content, '')

        r2 = self.client.get(self.url, testparamssince2,
                             X_Experience_API_Version=settings.XAPI_VERSION, Authorization=self.auth)
        self.assertEqual(r2.status_code, 200)

        robj2 = ast.literal_eval(r2.content)
        self.assertEqual(robj2['test'], teststatesince2['test'])
        self.assertEqual(robj2['obj']['agent'],
                         teststatesince2['obj']['agent'])
        self.assertEqual(r2['etag'], '"%s"' %
                         hashlib.sha1(r2.content).hexdigest())

        # create new state w/ registration id
        state_id3 = "old_state_test_w_new_reg"
        testparamssince3 = {"registration": regid, "activityId": self.activityId,
                            "agent": self.testagent, "stateId": state_id3}
        path = '%s?%s' % (self.url, urllib.parse.urlencode(testparamssince3))
        teststatesince3 = {"test": "get w/ since and registration",
                           "obj": {"agent": "test", "stateId": state_id3}}
        put3 = self.client.put(path, teststatesince3, content_type=self.content_type,
                               Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)

        self.assertEqual(put3.status_code, 204)
        self.assertEqual(put3.content, '')

        r3 = self.client.get(self.url, testparamssince3,
                             X_Experience_API_Version=settings.XAPI_VERSION, Authorization=self.auth)
        self.assertEqual(r3.status_code, 200)

        robj3 = ast.literal_eval(r3.content)
        self.assertEqual(robj3['test'], teststatesince3['test'])
        self.assertEqual(robj3['obj']['agent'],
                         teststatesince3['obj']['agent'])
        self.assertEqual(r3['etag'], '"%s"' %
                         hashlib.sha1(r3.content).hexdigest())

        # get no reg ids set w/o old state
        since1 = "2012-07-01T12:30:00+04:00"
        params = {"activityId": self.activityId,
                  "agent": self.testagent, "since": since1}
        r = self.client.get(
            self.url, params, X_Experience_API_Version=settings.XAPI_VERSION, Authorization=self.auth)
        self.assertEqual(r.status_code, 200)
        self.assertIn(self.stateId, r.content)
        self.assertIn(self.stateId2, r.content)
        self.assertNotIn(state_id, r.content)
        self.assertNotIn(self.stateId3, r.content)
        self.assertNotIn(self.stateId4, r.content)

        # get reg id set w/o old state
        since2 = "2012-07-01T12:30:00+04:00"
        params2 = {"registration": regid, "activityId": self.activityId,
                   "agent": self.testagent, "since": since2}
        r = self.client.get(
            self.url, params2, X_Experience_API_Version=settings.XAPI_VERSION, Authorization=self.auth)
        self.assertEqual(r.status_code, 200)
        self.assertIn(state_id3, r.content)
        self.assertNotIn(state_id2, r.content)
        self.assertNotIn(self.stateId, r.content)
        self.assertNotIn(self.stateId2, r.content)
        self.assertNotIn(self.stateId3, r.content)
        self.assertNotIn(self.stateId4, r.content)

        self.client.delete(self.url, testparamssince, Authorization=self.auth,
                           X_Experience_API_Version=settings.XAPI_VERSION)
        self.client.delete(self.url, testparamssince2, Authorization=self.auth,
                           X_Experience_API_Version=settings.XAPI_VERSION)
        self.client.delete(self.url, testparamssince3, Authorization=self.auth,
                           X_Experience_API_Version=settings.XAPI_VERSION)

    def test_get_without_activityid(self):
        params = {"stateId": self.stateId, "agent": self.testagent}
        r = self.client.get(
            self.url, params, X_Experience_API_Version=settings.XAPI_VERSION, Authorization=self.auth)
        self.assertEqual(r.status_code, 400)
        self.assertIn('activityId parameter is missing', r.content)

    def test_get_without_agent(self):
        params = {"stateId": self.stateId, "activityId": self.activityId}
        r = self.client.get(
            self.url, params, X_Experience_API_Version=settings.XAPI_VERSION, Authorization=self.auth)
        self.assertEqual(r.status_code, 400)
        self.assertIn('agent parameter is missing', r.content)

    def test_get_invalid_agent_structure(self):
        params = {"stateId": self.stateId,
                  "activityId": self.activityId, "agent": "blahagent"}
        r = self.client.get(
            self.url, params, X_Experience_API_Version=settings.XAPI_VERSION, Authorization=self.auth)
        self.assertEqual(r.status_code, 400)
        self.assertIn('agent param blahagent is not valid', r.content)

    def test_get_invalid_agent(self):
        params = {"stateId": self.stateId,
                  "activityId": self.activityId, "agent": {"mbox": "blahagent"}}
        r = self.client.get(
            self.url, params, X_Experience_API_Version=settings.XAPI_VERSION, Authorization=self.auth)
        self.assertEqual(r.status_code, 400)
        self.assertIn('mbox value blahagent did not start with mailto:', r.content)

    def test_get_invalid_activityid(self):
        params = {"stateId": self.stateId,
                  "activityId": "foo", "agent": self.testagent}
        r = self.client.get(
            self.url, params, X_Experience_API_Version=settings.XAPI_VERSION, Authorization=self.auth)
        self.assertEqual(r.status_code, 400)
        self.assertIn(
            'activityId param for activity state with value foo was not a valid IRI', r.content)

    def test_delete_without_activityid(self):
        testparamsregid = {"registration": self.registration, "stateId": self.stateId,
                           "activityId": self.activityId, "agent": self.testagent}
        path = '%s?%s' % (self.url, urllib.parse.urlencode(testparamsregid))
        teststateregid = {
            "test": "delete activity state w/o activityid", "obj": {"agent": "test"}}
        put1 = self.client.put(path, teststateregid, content_type=self.content_type,
                               Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)

        self.assertEqual(put1.status_code, 204)
        self.assertEqual(put1.content, '')

        r = self.client.get(self.url, testparamsregid,
                            X_Experience_API_Version=settings.XAPI_VERSION, Authorization=self.auth)
        self.assertEqual(r.status_code, 200)
        robj = ast.literal_eval(r.content)
        self.assertEqual(robj['test'], teststateregid['test'])
        self.assertEqual(robj['obj']['agent'], teststateregid['obj']['agent'])
        self.assertEqual(r['etag'], '"%s"' %
                         hashlib.sha1(r.content).hexdigest())

        f_r = self.client.delete(self.url, {"registration": self.registration, "stateId": self.stateId,
                                            "agent": self.testagent}, Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)

        self.assertEqual(f_r.status_code, 400)
        self.assertIn('activityId parameter is missing', f_r.content)

        del_r = self.client.delete(
            self.url, testparamsregid, Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(del_r.status_code, 204)

    def test_delete_without_agent(self):
        testparamsregid = {"registration": self.registration, "stateId": self.stateId,
                           "activityId": self.activityId, "agent": self.testagent}
        path = '%s?%s' % (self.url, urllib.parse.urlencode(testparamsregid))
        teststateregid = {
            "test": "delete activity state w/o agent", "obj": {"agent": "test"}}
        put1 = self.client.put(path, teststateregid, content_type=self.content_type,
                               Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)

        self.assertEqual(put1.status_code, 204)
        self.assertEqual(put1.content, '')

        r = self.client.get(self.url, testparamsregid,
                            X_Experience_API_Version=settings.XAPI_VERSION, Authorization=self.auth)
        self.assertEqual(r.status_code, 200)
        robj = ast.literal_eval(r.content)
        self.assertEqual(robj['test'], teststateregid['test'])
        self.assertEqual(robj['obj']['agent'], teststateregid['obj']['agent'])
        self.assertEqual(r['etag'], '"%s"' %
                         hashlib.sha1(r.content).hexdigest())

        f_r = self.client.delete(self.url, {"registration": self.registration, "stateId": self.stateId,
                                            "activityId": self.activityId}, Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(f_r.status_code, 400)
        self.assertIn('agent parameter is missing', f_r.content)

        del_r = self.client.delete(
            self.url, testparamsregid, Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(del_r.status_code, 204)

    def test_delete_set(self):
        testparamsdelset1 = {"registration": self.registration, "stateId": "del_state_set_1",
                             "activityId": self.activityId, "agent": self.testagent}
        path = '%s?%s' % (self.url, urllib.parse.urlencode(testparamsdelset1))
        teststatedelset1 = {"test": "delete set #1", "obj": {"agent": "test"}}
        put1 = self.client.put(path, teststatedelset1, content_type=self.content_type,
                               Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)

        self.assertEqual(put1.status_code, 204)
        self.assertEqual(put1.content, '')

        r = self.client.get(self.url, testparamsdelset1,
                            X_Experience_API_Version=settings.XAPI_VERSION, Authorization=self.auth)
        self.assertEqual(r.status_code, 200)

        robj = ast.literal_eval(r.content)
        self.assertEqual(robj['test'], teststatedelset1['test'])
        self.assertEqual(robj['obj']['agent'],
                         teststatedelset1['obj']['agent'])
        self.assertEqual(r['etag'], '"%s"' %
                         hashlib.sha1(r.content).hexdigest())

        testparamsdelset2 = {"registration": self.registration, "stateId": "del_state_set_2",
                             "activityId": self.activityId, "agent": self.testagent}
        path = '%s?%s' % (self.url, urllib.parse.urlencode(testparamsdelset2))
        teststatedelset2 = {"test": "delete set #2", "obj": {"agent": "test"}}
        put1 = self.client.put(path, teststatedelset2, content_type=self.content_type,
                               Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)

        self.assertEqual(put1.status_code, 204)
        self.assertEqual(put1.content, '')

        r = self.client.get(self.url, testparamsdelset2,
                            X_Experience_API_Version=settings.XAPI_VERSION, Authorization=self.auth)
        self.assertEqual(r.status_code, 200)

        robj2 = ast.literal_eval(r.content)
        self.assertEqual(robj2['test'], teststatedelset2['test'])
        self.assertEqual(robj2['obj']['agent'],
                         teststatedelset2['obj']['agent'])
        self.assertEqual(r['etag'], '"%s"' %
                         hashlib.sha1(r.content).hexdigest())

        f_r = self.client.delete(self.url, {"registration": self.registration, "agent": self.testagent,
                                            "activityId": self.activityId}, Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(f_r.status_code, 204)

        r = self.client.get(self.url, testparamsdelset1,
                            X_Experience_API_Version=settings.XAPI_VERSION, Authorization=self.auth)
        self.assertEqual(r.status_code, 404)
        self.assertIn('no activity', r.content)

        r = self.client.get(self.url, testparamsdelset2,
                            X_Experience_API_Version=settings.XAPI_VERSION, Authorization=self.auth)
        self.assertEqual(r.status_code, 404)
        self.assertIn('no activity', r.content)

    def test_ie_cors_put_delete(self):
        username = "another test"
        email = "anothertest@example.com"
        password = "test"
        auth = "Basic %s" % base64.b64encode("%s:%s" % (username, password))
        form = {'username': username, 'email': email,
                'password': password, 'password2': password}
        self.client.post(reverse(register), form,
                         X_Experience_API_Version=settings.XAPI_VERSION)

        testagent = '{"name":"another test","mbox":"mailto:anothertest@example.com"}'
        sid = "test_ie_cors_put_delete_set_1"
        path = '%s?%s' % (self.url, urllib.parse.urlencode({"method": "PUT"}))

        content = {"test": "test_ie_cors_put_delete",
                   "obj": {"actor": "another test"}}
        param = "stateId=%s&activityId=%s&agent=%s&content=%s&Content-Type=application/x-www-form-urlencoded&Authorization=%s&X-Experience-API-Version=1.0.0" \
            % (sid, self.activityId, testagent, urllib.parse.quote(str(content)), auth)

        put1 = self.client.post(
            path, param, content_type='application/x-www-form-urlencoded')

        self.assertEqual(put1.status_code, 204)
        self.assertEqual(put1.content, '')

        r = self.client.get(self.url, {"stateId": sid, "activityId": self.activityId,
                                       "agent": testagent}, X_Experience_API_Version=settings.XAPI_VERSION, Authorization=auth)
        self.assertEqual(r.status_code, 200)
        import ast
        c = ast.literal_eval(r.content)

        self.assertEqual(c['test'], content['test'])
        self.assertEqual(r['etag'], '"%s"' %
                         hashlib.sha1('%s' % content).hexdigest())

        dparam = "agent=%s&activityId=%s&Authorization=%s&Content-Type=application/x-www-form-urlencoded&X-Experience-API-Version=1.0.0" % (
            testagent, self.activityId, auth)
        path = '%s?%s' % (self.url, urllib.parse.urlencode({"method": "DELETE"}))
        f_r = self.client.post(
            path, dparam, content_type='application/x-www-form-urlencoded')
        self.assertEqual(f_r.status_code, 204)

    def test_agent_is_group(self):
        username = "the group"
        email = "the.group@example.com"
        password = "test"
        auth = "Basic %s" % base64.b64encode("%s:%s" % (username, password))
        form = {'username': username, 'email': email,
                'password': password, 'password2': password}
        self.client.post(reverse(register), form,
                         X_Experience_API_Version=settings.XAPI_VERSION)

        ot = "Group"
        name = "the group"
        mbox = "mailto:the.group@example.com"
        members = [{"name": "agent1", "mbox": "mailto:agent1@example.com"},
                   {"name": "agent2", "mbox": "mailto:agent2@example.com"}]
        testagent = json.dumps(
            {"objectType": ot, "name": name, "mbox": mbox, "member": members})
        testparams1 = {"stateId": "group.state.id",
                       "activityId": self.activityId, "agent": testagent}
        path = '%s?%s' % (self.url, urllib.parse.urlencode(testparams1))
        teststate1 = {"test": "put activity state using group as agent", "obj": {
            "agent": "group of 2 agents"}}
        put1 = self.client.put(path, teststate1, content_type=self.content_type,
                               Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)

        self.assertEqual(put1.status_code, 204)

        get1 = self.client.get(self.url, {"stateId": "group.state.id", "activityId": self.activityId,
                                          "agent": testagent}, X_Experience_API_Version=settings.XAPI_VERSION, Authorization=auth)
        self.assertEqual(get1.status_code, 200)
        robj = ast.literal_eval(get1.content)
        self.assertEqual(robj['test'], teststate1['test'])
        self.assertEqual(robj['obj']['agent'], teststate1['obj']['agent'])
        self.assertEqual(get1['etag'], '"%s"' %
                         hashlib.sha1(get1.content).hexdigest())

        delr = self.client.delete(
            self.url, testparams1, Authorization=auth, X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(delr.status_code, 204)

    def test_post_new_state(self):
        param = {"stateId": "test:postnewstate", "activityId": "act:test/post.new.state",
                 "agent": '{"mbox":"mailto:testagent@example.com"}'}
        path = '%s?%s' % (self.url, urllib.parse.urlencode(param))
        state = {"post": "testing new state", "obj": {"f1": "v1", "f2": "v2"}}

        r = self.client.post(path, json.dumps(state), content_type=self.content_type,
                             Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(r.status_code, 204)

        r = self.client.get(path, Authorization=self.auth,
                            X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(ast.literal_eval(r.content), state)

        self.client.delete(path, Authorization=self.auth,
                           X_Experience_API_Version=settings.XAPI_VERSION)

    def test_post_blank_state(self):
        param = {"stateId": "test:postnewblankstate", "activityId": "act:test/post.new.blank.state",
                 "agent": '{"mbox":"mailto:testagent@example.com"}'}
        path = '%s?%s' % (self.url, urllib.parse.urlencode(param))
        state = ""
        r = self.client.post(path, state, content_type=self.content_type,
                             Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.content, 'Could not find the state')

    def test_post_update_state(self):
        param = {"stateId": "test:postupdatestate", "activityId": "act:test/post.update.state",
                 "agent": '{"mbox":"mailto:test@example.com"}'}
        path = '%s?%s' % (self.url, urllib.parse.urlencode(param))
        state = {"field1": "value1", "obj": {
            "ofield1": "oval1", "ofield2": "oval2"}}

        r = self.client.post(path, json.dumps(state), content_type=self.content_type,
                             Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(r.status_code, 204)

        r = self.client.get(path, Authorization=self.auth,
                            X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(ast.literal_eval(r.content), state)

        state2 = {"field_xtra": "xtra val", "obj": "ha, not a obj"}
        r = self.client.post(path, json.dumps(state2), content_type=self.content_type,
                             Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(r.status_code, 204)

        r = self.client.get(path, Authorization=self.auth,
                            X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(r.status_code, 200)
        retstate = ast.literal_eval(r.content)
        self.assertEqual(retstate['field1'], state['field1'])
        self.assertEqual(retstate['field_xtra'], state2['field_xtra'])
        self.assertEqual(retstate['obj'], state2['obj'])

        self.client.delete(path, Authorization=self.auth,
                           X_Experience_API_Version=settings.XAPI_VERSION)

    def test_nonjson_put_state(self):
        param = {"stateId": "thisisnotjson", "activityId": "act:test/non.json.accepted",
                 "agent": '{"mbox":"mailto:test@example.com"}'}
        path = '%s?%s' % (self.url, urllib.parse.urlencode(param))
        state = "this is not json"

        r = self.client.put(path, state, content_type="text/plain",
                            Authorization=self.auth, X_Experience_API_Version="1.0.1")
        self.assertEqual(r.status_code, 204)

        r = self.client.get(path, Authorization=self.auth,
                            X_Experience_API_Version="1.0.1")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r['Content-Type'], "text/plain")
        self.assertEqual(r.content, state)
