import ast
import json
import hashlib
import urllib.request, urllib.parse, urllib.error
import base64

from django.test import TestCase
from django.conf import settings
from django.urls import reverse

from lrs import models

from adl_lrs.views import register


class ActivityProfileTests(TestCase):
    test_activityId1 = 'act:act-1'
    test_activityId2 = 'act:act-2'
    test_activityId3 = 'act:act-3'
    other_activityId = 'act:act-other'
    content_type = "application/json"
    testprofileId1 = "http://profile.test.id/test/1"
    testprofileId2 = "http://profile.test.id/test/2"
    testprofileId3 = "http://profile.test.id/test/3"
    otherprofileId1 = "http://profile.test.id/other/1"

    @classmethod
    def setUpClass(cls):
        print("\n%s" % __name__)
        super(ActivityProfileTests, cls).setUpClass()

    def setUp(self):
        self.username = "tester"
        self.email = "test@tester.com"
        self.password = "test"
        self.auth = "Basic %s" % base64.b64encode(
            "%s:%s" % (self.username, self.password))
        form = {'username': self.username, 'email': self.email,
                'password': self.password, 'password2': self.password}
        self.client.post(reverse(register), form,
                         X_Experience_API_Version=settings.XAPI_VERSION)

        self.testparams1 = {"profileId": self.testprofileId1,
                            "activityId": self.test_activityId1}
        path = '%s?%s' % (reverse('lrs:activity_profile'),
                          urllib.parse.urlencode(self.testparams1))
        self.testprofile1 = {"test": "put profile 1",
                             "obj": {"activity": "test"}}
        self.post1 = self.client.post(path, self.testprofile1, content_type=self.content_type,
                                    Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)

        self.testparams2 = {"profileId": self.testprofileId2,
                            "activityId": self.test_activityId2}
        path = '%s?%s' % (reverse('lrs:activity_profile'),
                          urllib.parse.urlencode(self.testparams2))
        self.testprofile2 = {"test": "put profile 2",
                             "obj": {"activity": "test"}}
        self.post2 = self.client.post(path, self.testprofile2, content_type=self.content_type,
                                    Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)

        self.testparams3 = {"profileId": self.testprofileId3,
                            "activityId": self.test_activityId3}
        path = '%s?%s' % (reverse('lrs:activity_profile'),
                          urllib.parse.urlencode(self.testparams3))
        self.testprofile3 = {"test": "put profile 3",
                             "obj": {"activity": "test"}}
        self.post3 = self.client.post(path, self.testprofile3, content_type=self.content_type,
                                    Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)

        self.testparams4 = {"profileId": self.otherprofileId1,
                            "activityId": self.other_activityId}
        path = '%s?%s' % (reverse('lrs:activity_profile'),
                          urllib.parse.urlencode(self.testparams4))
        self.otherprofile1 = {
            "test": "put profile other", "obj": {"activity": "other"}}
        self.post4 = self.client.post(path, self.otherprofile1, content_type=self.content_type,
                                    Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)

        self.testparams5 = {"profileId": self.otherprofileId1,
                            "activityId": self.test_activityId1}
        path = '%s?%s' % (reverse('lrs:activity_profile'),
                          urllib.parse.urlencode(self.testparams5))
        self.anotherprofile1 = {
            "test": "put another profile 1", "obj": {"activity": "other"}}
        self.post5 = self.client.post(path, self.anotherprofile1, content_type=self.content_type,
                                    Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)

    def tearDown(self):
        self.client.delete(reverse('lrs:activity_profile'), self.testparams1,
                           Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)
        self.client.delete(reverse('lrs:activity_profile'), self.testparams2,
                           Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)
        self.client.delete(reverse('lrs:activity_profile'), self.testparams3,
                           Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)
        self.client.delete(reverse('lrs:activity_profile'), self.testparams4,
                           Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)
        self.client.delete(reverse('lrs:activity_profile'), self.testparams5,
                           Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)

    def test_post(self):
        # Test the posts
        self.assertEqual(self.post1.status_code, 204)

        self.assertEqual(self.post2.status_code, 204)

        self.assertEqual(self.post3.status_code, 204)

        self.assertEqual(self.post4.status_code, 204)

        self.assertEqual(self.post5.status_code, 204)

        # Make sure profiles have correct activities
        self.assertEqual(models.ActivityProfile.objects.filter(
            profile_id=self.testprofileId1)[0].activity_id, self.test_activityId1)
        self.assertEqual(models.ActivityProfile.objects.filter(
            profile_id=self.testprofileId2)[0].activity_id, self.test_activityId2)
        self.assertEqual(models.ActivityProfile.objects.filter(
            profile_id=self.testprofileId3)[0].activity_id, self.test_activityId3)

    def test_put(self):
        path = '%s?%s' % (reverse('lrs:activity_profile'),
                          urllib.parse.urlencode({"profileId": "http://put.profile.id/new",
                            "activityId": "http://main.activity.com"}))
        profile = {"test": "good - trying to put new profile w/ etag header",
                   "obj": {"activity": "act:test"}}
        response = self.client.put(path, json.dumps(profile), content_type=self.content_type,
                                   If_None_Match="*", Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(response.status_code, 204)

        path = '%s?%s' % (reverse('lrs:activity_profile'),
                          urllib.parse.urlencode({"profileId": "http://put.profile.id/new",
                            "activityId": "http://main.activity.com"}))
        profile = {"test": "good - trying to put new profile w/ etag header",
                   "obj": {"activity": "act:test"}}
        response = self.client.put(path, json.dumps(profile), content_type=self.content_type,
                                   If_Match="*", Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(response.status_code, 204)

    def test_put_no_params(self):
        put = self.client.put(reverse('lrs:activity_profile'), content_type=self.content_type,
                              Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(
            put.content, 'Error -- activity_profile - method = PUT, but activityId parameter missing..')

    def test_put_no_activityId(self):
        put = self.client.put(reverse('lrs:activity_profile'), {
                              'profileId': '10'}, content_type=self.content_type, Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(
            put.content, 'Error -- activity_profile - method = PUT, but activityId parameter missing..')

    def test_put_no_profileId(self):
        testparams = {'activityId': 'act:act:act'}
        path = '%s?%s' % (reverse('lrs:activity_profile'),
                          urllib.parse.urlencode(testparams))
        put = self.client.put(path, content_type=self.content_type,
                              Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(
            put.content, 'Error -- activity_profile - method = PUT, but profileId parameter missing..')

    def test_put_etag_missing_on_change(self):
        path = '%s?%s' % (reverse('lrs:activity_profile'),
                          urllib.parse.urlencode(self.testparams1))
        profile = {"test": "error - trying to put new profile w/o etag header",
                   "obj": {"activity": "test"}}
        response = self.client.put(path, profile, content_type=self.content_type,
                                   Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(response.status_code, 409)
        self.assertIn(
            'If-Match and If-None-Match headers were missing. One of these headers is required for this request.', response.content)

        r = self.client.get(reverse('lrs:activity_profile'), self.testparams1,
                            X_Experience_API_Version=settings.XAPI_VERSION, Authorization=self.auth)
        self.assertEqual(r.status_code, 200)
        robj = ast.literal_eval(r.content)
        self.assertEqual(robj['test'], self.testprofile1['test'])
        self.assertEqual(robj['obj']['activity'],
                         self.testprofile1['obj']['activity'])

    def test_put_etag_right_on_change(self):
        path = '%s?%s' % (reverse('lrs:activity_profile'),
                          urllib.parse.urlencode(self.testparams1))
        profile = {"test": "good - trying to put new profile w/ etag header",
                   "obj": {"activity": "act:test"}}
        thehash = '"%s"' % hashlib.sha1('%s' % self.testprofile1).hexdigest()
        response = self.client.put(path, json.dumps(profile), content_type=self.content_type,
                                   If_Match=thehash, Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(response.status_code, 204)
        r = self.client.get(reverse('lrs:activity_profile'), self.testparams1,
                            X_Experience_API_Version=settings.XAPI_VERSION, Authorization=self.auth)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.content, json.dumps(profile))

    def test_put_etag_wrong_on_change(self):
        path = '%s?%s' % (reverse('lrs:activity_profile'),
                          urllib.parse.urlencode(self.testparams1))
        profile = {"test": "error - trying to put new profile w/ wrong etag value",
                   "obj": {"activity": "act:test"}}
        thehash = '"%s"' % hashlib.sha1('%s' % 'wrong hash').hexdigest()
        response = self.client.put(path, profile, content_type=self.content_type, If_Match=thehash,
                                   Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(response.status_code, 412)
        self.assertIn('No resources matched', response.content)

        r = self.client.get(reverse('lrs:activity_profile'), self.testparams1,
                            X_Experience_API_Version=settings.XAPI_VERSION, Authorization=self.auth)
        self.assertEqual(r.status_code, 200)
        robj = ast.literal_eval(r.content)
        self.assertEqual(robj['test'], self.testprofile1['test'])
        self.assertEqual(robj['obj']['activity'],
                         self.testprofile1['obj']['activity'])

    def test_put_etag_if_none_match_good(self):
        params = {"profileId": 'http://etag.nomatch.good',
                  "activityId": self.test_activityId1}
        path = '%s?%s' % (reverse('lrs:activity_profile'),
                          urllib.parse.urlencode(params))
        profile = {"test": "good - trying to put new profile w/ if none match etag header",
                   "obj": {"activity": "act:test"}}
        response = self.client.put(path, json.dumps(profile), content_type=self.content_type,
                                   If_None_Match='*', Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(response.status_code, 204)
        r = self.client.get(reverse('lrs:activity_profile'), params,
                            X_Experience_API_Version=settings.XAPI_VERSION, Authorization=self.auth)
        self.assertEqual(r.status_code, 200)
        robj = ast.literal_eval(r.content)
        self.assertEqual(robj['test'], profile['test'])
        self.assertEqual(robj['obj']['activity'], profile['obj']['activity'])

        r = self.client.delete(reverse('lrs:activity_profile'), params,
                               Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)

    def test_put_etag_if_none_match_good_value(self):
        path = '%s?%s' % (reverse('lrs:activity_profile'),
                          urllib.parse.urlencode({"profileId": self.testprofileId1,
                  "activityId": self.test_activityId1}))
        profile = {"test": "good - trying to put updated profile w/ if none match etag header",
                   "obj": {"activity": "test"}}
        thehash = "fa76b3e4d77adf6795d914a3d00d8949b95aa803"          
        response = self.client.put(path, profile, content_type=self.content_type, If_None_Match=thehash,
                                   Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)

        self.assertEqual(response.status_code, 204)
        self.assertEqual(response.content, '')

        r = self.client.get(reverse('lrs:activity_profile'), {"profileId": self.testprofileId1,"activityId": self.test_activityId1},
                            Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(r.status_code, 200)
        robj = ast.literal_eval(r.content)
        self.assertEqual(robj['test'], profile['test'])
        self.assertEqual(robj['obj']['activity'], profile['obj']['activity'])

        r = self.client.delete(reverse('lrs:agent_profile'), {"profileId": self.testprofileId1,"activityId": self.test_activityId1},
                               Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)

    def test_put_etag_if_none_match_bad(self):
        path = '%s?%s' % (reverse('lrs:activity_profile'),
                          urllib.parse.urlencode(self.testparams1))
        profile = {"test": "error - trying to put new profile w/ if none match etag but one exists",
                   "obj": {"activity": "act:test"}}
        response = self.client.put(path, profile, content_type=self.content_type, If_None_Match='*',
                                   Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(response.status_code, 412)
        self.assertEqual(response.content, 'Resource detected')

        r = self.client.get(reverse('lrs:activity_profile'), self.testparams1,
                            X_Experience_API_Version=settings.XAPI_VERSION, Authorization=self.auth)
        self.assertEqual(r.status_code, 200)
        robj = ast.literal_eval(r.content)
        self.assertEqual(robj['test'], self.testprofile1['test'])
        self.assertEqual(robj['obj']['activity'],
                         self.testprofile1['obj']['activity'])

    def test_put_etag_if_none_match_bad_value(self):
        path = '%s?%s' % (reverse('lrs:activity_profile'),
                          urllib.parse.urlencode(self.testparams1))
        profile = {"test": "error - trying to put new profile w/ if none match etag but one exists",
                   "obj": {"agent": "test"}}        
        thehash = '"%s"' % hashlib.sha1('%s' % self.testprofile1).hexdigest()
        response = self.client.put(path, profile, content_type=self.content_type, If_None_Match=thehash,
                                   Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)

        self.assertEqual(response.status_code, 412)
        self.assertEqual(response.content, 'Resource detected')

        r = self.client.get(reverse('lrs:activity_profile'), self.testparams1,
                            X_Experience_API_Version=settings.XAPI_VERSION, Authorization=self.auth)
        self.assertEqual(r.status_code, 200)
        robj = ast.literal_eval(r.content)
        self.assertEqual(robj['test'], self.testprofile1['test'])
        self.assertEqual(robj['obj']['activity'],
                         self.testprofile1['obj']['activity'])

    def test_get_activity_only(self):
        response = self.client.get(reverse('lrs:activity_profile'), {
                                   'activityId': self.test_activityId2}, X_Experience_API_Version=settings.XAPI_VERSION, Authorization=self.auth)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.testprofileId2)

        params = {'activityId': self.test_activityId2,
                  'profileId': self.testprofileId2}

        self.client.delete(reverse('lrs:activity_profile'), params,
                           Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)

    def test_get_activity_profileId(self):
        response = self.client.get(reverse('lrs:activity_profile'), {'activityId': self.test_activityId1, 'profileId': self.testprofileId1},
                                   X_Experience_API_Version=settings.XAPI_VERSION, Authorization=self.auth)
        self.assertEqual(response.status_code, 200)
        robj = ast.literal_eval(response.content)
        self.assertEqual(robj['test'], self.testprofile1['test'])
        self.assertEqual(robj['obj']['activity'],
                         self.testprofile1['obj']['activity'])
        resp_hash = hashlib.sha1(response.content).hexdigest()
        self.assertEqual(response['etag'], '"%s"' % resp_hash)
        params = {'activityId': self.test_activityId1,
                  'profileId': self.testprofileId1}

        self.client.delete(reverse('lrs:activity_profile'), params,
                           Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)

    def test_get_activity_profileId_no_auth(self):
        response = self.client.get(reverse('lrs:activity_profile'), {
                                   'activityId': self.test_activityId1, 'profileId': self.testprofileId1}, X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(response.status_code, 400)

    def test_get_activity_profileId_activity_dne(self):
        response = self.client.get(reverse('lrs:activity_profile'), {
                                   'activityId': 'http://actID', 'profileId': self.testprofileId1}, X_Experience_API_Version=settings.XAPI_VERSION, Authorization=self.auth)
        self.assertEqual(response.status_code, 404)

    def test_get_activity_since_tz(self):
        actid = "test:activity"
        profid = "test://test/tz"
        st = json.dumps({"actor": {"objectType": "Agent", "mbox": "mailto:tom@adlnet.gov"},
                         "verb": {"id": "http://example.com/verbs/assess", "display": {"en-US": "assessed"}},
                         "object": {'objectType': 'Activity', 'id': actid}})
        st_post = self.client.post(reverse('lrs:statements'), st, content_type="application/json",
                                   Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(st_post.status_code, 200)

        params = {"profileId": profid, "activityId": actid}
        path = '%s?%s' % (reverse('lrs:activity_profile'),
                          urllib.parse.urlencode(params))
        prof = {"test": "timezone since", "obj": {"activity": "other"}}
        r = self.client.put(path, json.dumps(prof), content_type=self.content_type, updated="2012-11-11T12:00:00+00:00",
                            If_None_Match="*", Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(r.status_code, 204)

        since = "2012-11-11T12:00:00-02:00"
        response = self.client.get(reverse('lrs:activity_profile'), {
                                   'activityId': actid, 'since': since}, X_Experience_API_Version=settings.XAPI_VERSION, Authorization=self.auth)
        self.assertEqual(response.status_code, 200)
        self.assertNotIn(profid, response.content)

        params = {"activityId": actid, "profileId": profid}
        self.client.delete(reverse('lrs:activity_profile'), params,
                           Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)

    def test_get_activity_bad_since(self):
        actid = "test:activity"
        profid = "test://test/tz"
        st = json.dumps({"actor": {"objectType": "Agent", "mbox": "mailto:tom@adlnet.gov"},
                         "verb": {"id": "http://example.com/verbs/assess", "display": {"en-US": "assessed"}},
                         "object": {'objectType': 'Activity', 'id': actid}})
        st_post = self.client.post(reverse('lrs:statements'), st, content_type="application/json",
                                   Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(st_post.status_code, 200)

        params = {"profileId": profid, "activityId": actid}
        path = '%s?%s' % (reverse('lrs:activity_profile'),
                          urllib.parse.urlencode(params))
        prof = {"test": "timezone since", "obj": {"activity": "other"}}
        r = self.client.put(path, json.dumps(prof), content_type=self.content_type, updated="2012-11-11T12:00:00+00:00",
                            If_None_Match="*", Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(r.status_code, 204)

        since = "2012-11-1112:00:00-02:00"
        response = self.client.get(reverse('lrs:activity_profile'), {
                                   'activityId': actid, 'since': since}, X_Experience_API_Version=settings.XAPI_VERSION, Authorization=self.auth)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.content,
                         "Since parameter was not a valid ISO8601 timestamp")

        params = {"activityId": actid, "profileId": profid}
        self.client.delete(reverse('lrs:activity_profile'), params,
                           Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)

    def test_get_no_activityId_with_profileId(self):
        response = self.client.get(reverse('lrs:activity_profile'), {
                                   'profileId': self.testprofileId3}, X_Experience_API_Version=settings.XAPI_VERSION, Authorization=self.auth)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.content, 'Error -- activity_profile - method = GET, but activityId parameter missing..')

    def test_get_no_activityId_with_since(self):
        since = "2012-07-01T13:30:00+04:00"
        response = self.client.get(reverse('lrs:activity_profile'), {
                                   'since': since}, X_Experience_API_Version=settings.XAPI_VERSION, Authorization=self.auth)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.content, 'Error -- activity_profile - method = GET, but activityId parameter missing..')

    def test_delete(self):
        response = self.client.delete(reverse('lrs:activity_profile'), {
                                      'activityId': self.other_activityId, 'profileId': self.otherprofileId1}, Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(response.status_code, 204)
        self.assertEqual(response.content, '')

    def test_cors_put(self):
        profileid = 'http://test.cors.put'
        activityid = 'act:test_cors_put-activity'

        testparams1 = {"profileId": profileid, "activityId": activityid}
        content = {"test": "put profile 1", "obj": {"activity": "act:test"}}
        params = "profileId=%s&activityId=%s&Authorization=%s&content=%s&X-Experience-API-Version=1.0&If-None-Match=*" % (
            profileid, activityid, self.auth, urllib.parse.quote(str(content)))

        path = path = '%s?%s' % (
            reverse('lrs:activity_profile'), urllib.parse.urlencode({"method": "PUT"}))

        st = json.dumps({"actor": {"objectType": "Agent", "mbox": "mailto:tom@adlnet.gov"},
                         "verb": {"id": "http://example.com/verbs/assess", "display": {"en-US": "assessed"}},
                         "object": {'objectType': 'Activity', 'id': activityid}})
        st_post = self.client.post(reverse('lrs:statements'), st, content_type="application/json",
                                   Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(st_post.status_code, 200)

        thedata = params
        put1 = self.client.post(
            path, thedata, content_type="application/x-www-form-urlencoded")
        self.assertEqual(put1.status_code, 204)
        get1 = self.client.get(reverse('lrs:activity_profile'), testparams1,
                               Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(get1.status_code, 200)

        import ast
        c = ast.literal_eval(get1.content)
        self.assertEqual(c['test'], content['test'])
        self.client.delete(reverse('lrs:activity_profile'), testparams1,
                           Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)

    def test_cors_put_etag(self):
        pid = 'http://ie.cors.etag/test'
        aid = 'act:ie.cors.etag/test'

        st = json.dumps({"actor": {"objectType": "Agent", "mbox": "mailto:tom@adlnet.gov"},
                         "verb": {"id": "http://example.com/verbs/assess", "display": {"en-US": "assessed"}},
                         "object": {'objectType': 'Activity', 'id': aid}})
        st_post = self.client.post(reverse('lrs:statements'), st, content_type="application/json",
                                   Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(st_post.status_code, 200)

        path = '%s?%s' % (reverse('lrs:activity_profile'),
                          urllib.parse.urlencode(self.testparams1))
        tp = {"test": "put example profile for test_cors_put_etag", "obj": {
            "activity": "this should be replaced -- ie cors post/put"}}
        thehash = '"%s"' % hashlib.sha1('%s' % self.testprofile1).hexdigest()
        put1 = self.client.put(path, tp, content_type=self.content_type, If_Match=thehash,
                               Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(put1.status_code, 204)
        path = '%s?%s' % (reverse('lrs:activity_profile'),
                          urllib.parse.urlencode({"method": "PUT"}))

        content = {"test": "good - trying to put new profile w/ etag header - IE cors",
                   "obj": {"activity": "test IE cors etag"}}
        thehash = '"%s"' % hashlib.sha1('%s' % tp).hexdigest()
        thedata = "profileId=%s&activityId=%s&If-Match=%s&Authorization=%s&Content-Type=application/x-www-form-urlencoded&content=%s&X-Experience-API-Version=1.0.0&If-None-Match=*" % (
            pid, aid, thehash, self.auth, urllib.parse.quote(str(content)))

        response = self.client.post(
            path, thedata, content_type="application/x-www-form-urlencoded")
        self.assertEqual(response.status_code, 204)
        r = self.client.get(reverse('lrs:activity_profile'), {
                            'activityId': aid, 'profileId': pid}, X_Experience_API_Version=settings.XAPI_VERSION, Authorization=self.auth)
        self.assertEqual(r.status_code, 200)
        import ast
        c = ast.literal_eval(r.content)
        self.assertEqual(c['test'], content['test'])

        self.client.delete(reverse('lrs:activity_profile'), {
                           'activityId': aid, 'profileId': pid}, Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)

    def test_tetris_snafu(self):
        params = {"profileId": "http://test.tetris/",
                  "activityId": "act:tetris.snafu"}
        path = '%s?%s' % (reverse('lrs:activity_profile'),
                          urllib.parse.urlencode(params))
        profile = {"test": "put profile 1", "obj": {"activity": "test"}}

        st = json.dumps({"actor": {"objectType": "Agent", "mbox": "mailto:tom@adlnet.gov"},
                         "verb": {"id": "http://example.com/verbs/assess", "display": {"en-US": "assessed"}},
                         "object": {'objectType': 'Activity', 'id': "act:tetris.snafu"}})
        st_post = self.client.post(reverse('lrs:statements'), st, content_type="application/json",
                                   Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(st_post.status_code, 200)

        p_r = self.client.put(path, json.dumps(profile), content_type=self.content_type,
                              If_None_Match="*", Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(p_r.status_code, 204)
        r = self.client.get(reverse('lrs:activity_profile'), {
                            'activityId': "act:tetris.snafu", 'profileId': "http://test.tetris/"}, X_Experience_API_Version=settings.XAPI_VERSION, Authorization=self.auth)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r['Content-Type'], self.content_type)
        self.assertIn("\"", r.content)

        self.client.delete(path, Authorization=self.auth,
                           X_Experience_API_Version=settings.XAPI_VERSION)

    def test_post_new_profile(self):
        params = {"profileId": "prof:test_post_new_profile",
                  "activityId": "act:test.post.new.prof"}
        path = '%s?%s' % (reverse('lrs:activity_profile'),
                          urllib.parse.urlencode(params))
        prof = {"test": "post new profile", "obj": {
            "activity": "act:test.post.new.prof"}}

        post = self.client.post(path, json.dumps(prof), content_type="application/json",
                                Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(post.status_code, 204)

        get = self.client.get(path, Authorization=self.auth,
                              X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(get.status_code, 200)
        self.assertEqual(ast.literal_eval(get.content), prof)
        self.assertEqual(get.get('etag'), '"%s"' %
                         hashlib.sha1(get.content).hexdigest())
        self.client.delete(path, Authorization=self.auth,
                           X_Experience_API_Version=settings.XAPI_VERSION)

    def test_post_blank_profile(self):
        params = {"profileId": "prof:test_post_new_profile",
                  "activityId": "act:test.post.new.prof"}
        path = '%s?%s' % (reverse('lrs:activity_profile'),
                          urllib.parse.urlencode(params))
        prof = ""

        post = self.client.post(path, prof, content_type="application/json",
                                Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)

        self.assertEqual(post.status_code, 400)
        self.assertEqual(post.content, 'Could not find the profile document')

    def test_post_and_put_profile(self):
        params = {"profileId": "prof:test_post_and_put_profile",
                  "activityId": "act:test.post.put.prof"}
        path = '%s?%s' % (reverse('lrs:activity_profile'),
                          urllib.parse.urlencode(params))
        prof = {"test": "post and put profile", "obj": {
            "activity": "act:test.post.put.prof"}}

        post = self.client.post(path, json.dumps(prof), content_type="application/json",
                                Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(post.status_code, 204)

        get = self.client.get(path, Authorization=self.auth,
                              X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(get.status_code, 200)
        self.assertEqual(ast.literal_eval(get.content), prof)
        self.assertEqual(get.get('etag'), '"%s"' %
                         hashlib.sha1(get.content).hexdigest())

        params = {"profileId": "prof:test_post_and_put_profile",
                  "activityId": "act:test.post.put.prof"}
        path = '%s?%s' % (reverse('lrs:activity_profile'),
                          urllib.parse.urlencode(params))
        prof = {"wipe": "new data"}
        thehash = get.get('etag')

        put = self.client.put(path, json.dumps(prof), content_type="application/json", If_Match=thehash,
                              Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(put.status_code, 204)

        get = self.client.get(path, Authorization=self.auth,
                              X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(get.status_code, 200)
        self.assertEqual(ast.literal_eval(get.content), prof)
        etag = '"%s"' % hashlib.sha1(get.content).hexdigest()
        self.assertEqual(get.get('etag'), etag)

        self.client.delete(path, Authorization=self.auth,
                           X_Experience_API_Version=settings.XAPI_VERSION)

    def test_put_wrong_activityId(self):
        params = {'activityId': 'foo', 'profileId': '10'}
        path = '%s?%s' % (reverse('lrs:activity_profile'),
                          urllib.parse.urlencode(params))

        put = self.client.put(path, '{"test":"body"}', content_type=self.content_type,
                              Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(
            put.content, 'activityId param for activity profile with value foo was not a valid IRI')

    def test_current_tetris(self):
        params = {"profileId": "profile:highscores",
                  "activityId": "act:adlnet.gov/JsTetris_TCAPI"}
        path = '%s?%s' % (reverse('lrs:activity_profile'),
                          urllib.parse.urlencode(params))
        put = self.client.put(path, '[{"actor":{"name":"tom","mbox":"mailto:tom@tom.com"},"score":802335,"date":"2013-07-26T13:42:13.465Z"},{"actor":{"name":"tom","mbox":"mailto:tom@tom.com"},"score":159482,"date":"2013-07-26T13:49:14.011Z"},{"actor":{"name":"lou","mbox":"mailto:l@l.com"},"score":86690,"date":"2013-07-26T13:27:29.083Z"},{"actor":{"name":"tom","mbox":"mailto:tom@tom.com"},"score":15504,"date":"2013-07-26T13:27:30.763Z"},{"actor":{"name":"tom","mbox":"mailto:tom@tom.com"},"score":1982,"date":"2013-07-26T13:29:46.067Z"},{"actor":{"name":"unknown","mbox":"mailto:unknown@example.com"},"score":348,"date":"2013-07-26T13:51:08.043Z"}]', If_None_Match="*", content_type="application/json", Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(put.status_code, 204)

        theget = self.client.get(
            path, If_None_Match="*", Authorization=self.auth, X_Experience_API_Version="1.0")
        self.assertEqual(
            theget['ETag'], '"d4827d99a5cc3510d3847baa341ba5a3b477fdfc"')

    def test_json_merge(self):
        prof = '{"test": { "goal": "ensure proper json parse", "attempt": 1, "result": null } }'

        params = {"profileId": "prof:test_json_merge",
                  "activityId": "act:test.json.merge.prof"}
        path = '%s?%s' % (reverse('lrs:activity_profile'),
                          urllib.parse.urlencode(params))

        post = self.client.post(path, prof, content_type="application/json", If_None_Match='*',
                                Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(post.status_code, 204)

        get = self.client.get(path, Authorization=self.auth,
                              X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(get.status_code, 200)
        returned = json.loads(get.content)
        sent = json.loads(prof)
        self.assertEqual(returned['test']['goal'], sent['test']['goal'])
        self.assertEqual(returned['test']['attempt'], sent['test']['attempt'])
        self.assertEqual(returned['test']['result'], sent['test']['result'])
        etag = '"%s"' % hashlib.sha1(get.content).hexdigest()
        self.assertEqual(get.get('etag'), etag)

        sent['test']['result'] = True
        sent['test']['attempt'] = sent['test']['attempt'] + 1
        prof = json.dumps(sent)
        post = self.client.post(path, prof, content_type="application/json", If_Match=etag,
                                Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(post.status_code, 204)

        get = self.client.get(path, Authorization=self.auth,
                              X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(get.status_code, 200)
        returned = json.loads(get.content)
        sent = json.loads(prof)
        self.assertEqual(returned['test']['goal'], sent['test']['goal'])
        self.assertEqual(returned['test']['attempt'], sent['test']['attempt'])
        self.assertEqual(returned['test']['result'], sent['test']['result'])
        etag = '"%s"' % hashlib.sha1(get.content).hexdigest()
        self.assertEqual(get.get('etag'), etag)
