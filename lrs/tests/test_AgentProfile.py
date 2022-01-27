import hashlib
import urllib.request, urllib.parse, urllib.error
import base64
import json
import ast

from django.test import TestCase
from django.conf import settings
from django.urls import reverse

from adl_lrs.views import register


class AgentProfileTests(TestCase):
    testagent = '{"mbox":"mailto:test@example.com"}'
    otheragent = '{"mbox":"mailto:other@example.com"}'
    content_type = "application/json"
    testprofileId1 = "http://profile.test.id/test/1"
    testprofileId2 = "http://profile.test.id/test/2"
    testprofileId3 = "http://profile.test.id/test/3"
    otherprofileId1 = "http://profile.test.id/other/1"

    @classmethod
    def setUpClass(cls):
        print("\n%s" % __name__)
        super(AgentProfileTests, cls).setUpClass()

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

        self.testparams1 = {
            "profileId": self.testprofileId1, "agent": self.testagent}
        path = '%s?%s' % (reverse('lrs:agent_profile'),
                          urllib.parse.urlencode(self.testparams1))
        self.testprofile1 = {"test": "post profile 1", "obj": {"agent": "test"}}
        self.post1 = self.client.post(path, self.testprofile1, content_type=self.content_type,
                                    Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)

        self.testparams2 = {
            "profileId": self.testprofileId2, "agent": self.testagent}
        path = '%s?%s' % (reverse('lrs:agent_profile'),
                          urllib.parse.urlencode(self.testparams2))
        self.testprofile2 = {"test": "post profile 2", "obj": {"agent": "test"}}
        self.post2 = self.client.post(path, self.testprofile2, content_type=self.content_type,
                                    Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)

        self.testparams3 = {
            "profileId": self.testprofileId3, "agent": self.testagent}
        path = '%s?%s' % (reverse('lrs:agent_profile'),
                          urllib.parse.urlencode(self.testparams3))
        self.testprofile3 = {"test": "post profile 3", "obj": {"agent": "test"}}
        self.post3 = self.client.post(path, self.testprofile3, content_type=self.content_type,
                                    Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)

        self.testparams4 = {
            "profileId": self.otherprofileId1, "agent": self.otheragent}
        path = '%s?%s' % (reverse('lrs:agent_profile'),
                          urllib.parse.urlencode(self.testparams4))
        self.otherprofile1 = {
            "test": "post profile 1", "obj": {"agent": "other"}}
        self.post4 = self.client.post(path, self.otherprofile1, content_type=self.content_type,
                                    Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)

    def tearDown(self):
        self.client.delete(reverse('lrs:agent_profile'), self.testparams1,
                           Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)
        self.client.delete(reverse('lrs:agent_profile'), self.testparams2,
                           Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)
        self.client.delete(reverse('lrs:agent_profile'), self.testparams3,
                           Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)
        self.client.delete(reverse('lrs:agent_profile'), self.testparams4,
                           Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)

    def test_get_agent_not_found(self):
        a = '{"mbox":"mailto:notfound@example.com"}'
        p = 'http://agent.not.found'
        param = {"profileId": p, "agent": a}
        r = self.client.get(reverse('lrs:agent_profile'), param,
                            Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(r.status_code, 404)

    def test_post(self):
        self.assertEqual(self.post1.status_code, 204)
        self.assertEqual(self.post1.content, '')

        self.assertEqual(self.post2.status_code, 204)
        self.assertEqual(self.post2.content, '')

        self.assertEqual(self.post3.status_code, 204)
        self.assertEqual(self.post3.content, '')

        self.assertEqual(self.post4.status_code, 204)
        self.assertEqual(self.post4.content, '')

    def test_put(self):
        path = '%s?%s' % (reverse('lrs:agent_profile'),
                          urllib.parse.urlencode({
            "profileId": "http://simple.put/test/none", "agent": self.testagent}))
        profile = {"test": "good - simple test w/ etag header",
                   "obj": {"agent": "test"}}
        response = self.client.put(path, profile, content_type=self.content_type, If_None_Match="*",
                                   Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(response.status_code, 204)
        self.assertEqual(response.content, '')        

        path = '%s?%s' % (reverse('lrs:agent_profile'),
                          urllib.parse.urlencode({
            "profileId": "http://simple.put/test/none", "agent": self.testagent}))
        profile = {"test": "good - simple test w/ etag header",
                   "obj": {"agent": "test"}}
        response = self.client.put(path, profile, content_type=self.content_type, If_Match="*",
                                   Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(response.status_code, 204)
        self.assertEqual(response.content, '') 

    def test_put_etag_missing_on_change(self):
        path = '%s?%s' % (reverse('lrs:agent_profile'),
                          urllib.parse.urlencode(self.testparams1))
        profile = {"test": "error - trying to put new profile w/o etag header",
                   "obj": {"agent": "test"}}
        response = self.client.put(path, profile, content_type=self.content_type,
                                   Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)

        self.assertEqual(response.status_code, 409)
        self.assertIn(
            'If-Match and If-None-Match headers were missing. One of these headers is required for this request.',
                response.content)

        r = self.client.get(reverse('lrs:agent_profile'), self.testparams1,
                            Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(r.status_code, 200)
        robj = ast.literal_eval(r.content)
        self.assertEqual(robj['test'], self.testprofile1['test'])
        self.assertEqual(robj['obj']['agent'],
                         self.testprofile1['obj']['agent'])

    def test_put_etag_right_on_change(self):
        path = '%s?%s' % (reverse('lrs:agent_profile'),
                          urllib.parse.urlencode(self.testparams1))
        profile = {"test": "good - trying to put new profile w/ etag header",
                   "obj": {"agent": "test"}}
        thehash = '"%s"' % hashlib.sha1('%s' % self.testprofile1).hexdigest()
        thehash2 = '"%s"' % hashlib.sha1('%s' % profile).hexdigest()
        hashes = '%s, %s' % (thehash, thehash2)
        response = self.client.put(path, profile, content_type=self.content_type, If_Match=hashes,
                                   Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(response.status_code, 204)
        self.assertEqual(response.content, '')

        r = self.client.get(reverse('lrs:agent_profile'), self.testparams1,
                            Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(r.status_code, 200)
        robj = ast.literal_eval(r.content)
        self.assertEqual(robj['test'], profile['test'])
        self.assertEqual(robj['obj']['agent'], profile['obj']['agent'])

    def test_put_etag_wrong_on_change(self):
        path = '%s?%s' % (reverse('lrs:agent_profile'),
                          urllib.parse.urlencode(self.testparams1))
        profile = {"test": "error - trying to put new profile w/ wrong etag value",
                   "obj": {"agent": "test"}}
        thehash = '"%s"' % hashlib.sha1('%s' % 'wrong hash').hexdigest()
        response = self.client.put(path, profile, content_type=self.content_type, If_Match=thehash,
                                   Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(response.status_code, 412)
        self.assertIn('No resources matched', response.content)

        r = self.client.get(reverse('lrs:agent_profile'), self.testparams1,
                            Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(r.status_code, 200)
        robj = ast.literal_eval(r.content)
        self.assertEqual(robj['test'], self.testprofile1['test'])
        self.assertEqual(robj['obj']['agent'],
                         self.testprofile1['obj']['agent'])

    def test_put_etag_if_none_match_good(self):
        params = {"profileId": 'http://etag.nomatch.good',
                  "agent": self.testagent}
        path = '%s?%s' % (reverse('lrs:agent_profile'),
                          urllib.parse.urlencode(params))
        profile = {"test": "good - trying to put new profile w/ if none match etag header",
                   "obj": {"agent": "test"}}
        response = self.client.put(path, profile, content_type=self.content_type, If_None_Match='*',
                                   Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)

        self.assertEqual(response.status_code, 204)
        self.assertEqual(response.content, '')

        r = self.client.get(reverse('lrs:agent_profile'), params,
                            Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(r.status_code, 200)
        robj = ast.literal_eval(r.content)
        self.assertEqual(robj['test'], profile['test'])
        self.assertEqual(robj['obj']['agent'], profile['obj']['agent'])

        r = self.client.delete(reverse('lrs:agent_profile'), params,
                               Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)

    def test_put_etag_if_none_match_good_value(self):
        path = '%s?%s' % (reverse('lrs:agent_profile'),
                          urllib.parse.urlencode(self.testparams1))
        profile = {"test": "good - trying to put updated profile w/ if none match etag header",
                   "obj": {"agent": "test"}}
        thehash = "fa76b3e4d77adf6795d914a3d00d8949b95aa803"          
        response = self.client.put(path, profile, content_type=self.content_type, If_None_Match=thehash,
                                   Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)

        self.assertEqual(response.status_code, 204)
        self.assertEqual(response.content, '')

        r = self.client.get(reverse('lrs:agent_profile'), self.testparams1,
                            Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(r.status_code, 200)
        robj = ast.literal_eval(r.content)
        self.assertEqual(robj['test'], profile['test'])
        self.assertEqual(robj['obj']['agent'], profile['obj']['agent'])

        r = self.client.delete(reverse('lrs:agent_profile'), self.testparams1,
                               Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)

    def test_put_etag_if_none_match_bad(self):
        path = '%s?%s' % (reverse('lrs:agent_profile'),
                          urllib.parse.urlencode(self.testparams1))
        profile = {"test": "error - trying to put new profile w/ if none match etag but one exists",
                   "obj": {"agent": "test"}}
        response = self.client.put(path, profile, content_type=self.content_type, If_None_Match='*',
                                   Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)

        self.assertEqual(response.status_code, 412)
        self.assertEqual(response.content, 'Resource detected')

        r = self.client.get(reverse('lrs:agent_profile'), self.testparams1,
                            Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(r.status_code, 200)
        robj = ast.literal_eval(r.content)
        self.assertEqual(robj['test'], self.testprofile1['test'])
        self.assertEqual(robj['obj']['agent'],
                         self.testprofile1['obj']['agent'])

    def test_put_etag_if_none_match_bad_value(self):
        path = '%s?%s' % (reverse('lrs:agent_profile'),
                          urllib.parse.urlencode(self.testparams1))
        profile = {"test": "error - trying to put new profile w/ if none match etag but one exists",
                   "obj": {"activity": "test"}}
        thehash = '"%s"' % hashlib.sha1('%s' % self.testprofile1).hexdigest()
        response = self.client.put(path, profile, content_type=self.content_type, If_None_Match=thehash,
                                   Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)

        self.assertEqual(response.status_code, 412)
        self.assertEqual(response.content, 'Resource detected')

        r = self.client.get(reverse('lrs:agent_profile'), self.testparams1,
                            Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(r.status_code, 200)
        robj = ast.literal_eval(r.content)
        self.assertEqual(robj['test'], self.testprofile1['test'])
        self.assertEqual(robj['obj']['agent'],
                         self.testprofile1['obj']['agent'])

    def test_get_invalid_agent_structure(self):
        r = self.client.get(reverse('lrs:agent_profile'), {
                            "profileId": self.testprofileId1, "agent": "wrong"}, Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(r.status_code, 400)
        self.assertEqual(
            r.content, "agent param wrong is not valid")

    def test_get_invalid_agent(self):
        r = self.client.get(reverse('lrs:agent_profile'), {"profileId": self.testprofileId1, "agent": {
                            "mbox": "foo"}}, Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(r.status_code, 400)
        self.assertEqual(
            r.content, "mbox value foo did not start with mailto:")

    def test_get(self):
        r = self.client.get(reverse('lrs:agent_profile'), self.testparams1,
                            Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(r.status_code, 200)
        robj = ast.literal_eval(r.content)
        self.assertEqual(robj['test'], self.testprofile1['test'])
        self.assertEqual(robj['obj']['agent'],
                         self.testprofile1['obj']['agent'])
        self.assertEqual(r['etag'], '"%s"' % hashlib.sha1(
            '%s' % self.testprofile1).hexdigest())

        r2 = self.client.get(reverse('lrs:agent_profile'), self.testparams2,
                             Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(r2.status_code, 200)
        robj2 = ast.literal_eval(r2.content)
        self.assertEqual(robj2['test'], self.testprofile2['test'])
        self.assertEqual(robj2['obj']['agent'],
                         self.testprofile2['obj']['agent'])
        self.assertEqual(r2['etag'], '"%s"' % hashlib.sha1(
            '%s' % self.testprofile2).hexdigest())

        r3 = self.client.get(reverse('lrs:agent_profile'), self.testparams3,
                             Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(r3.status_code, 200)
        robj3 = ast.literal_eval(r3.content)
        self.assertEqual(robj3['test'], self.testprofile3['test'])
        self.assertEqual(robj3['obj']['agent'],
                         self.testprofile3['obj']['agent'])
        self.assertEqual(r3['etag'], '"%s"' % hashlib.sha1(
            '%s' % self.testprofile3).hexdigest())

        r4 = self.client.get(reverse('lrs:agent_profile'), self.testparams4,
                             Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(r4.status_code, 200)
        robj4 = ast.literal_eval(r4.content)
        self.assertEqual(robj4['test'], self.otherprofile1['test'])
        self.assertEqual(robj4['obj']['agent'],
                         self.otherprofile1['obj']['agent'])
        self.assertEqual(r4['etag'], '"%s"' % hashlib.sha1(
            '%s' % self.otherprofile1).hexdigest())

    def test_get_no_params(self):
        r = self.client.get(reverse('lrs:agent_profile'), Authorization=self.auth,
                            X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(r.status_code, 400)
        self.assertIn('agent parameter missing', r.content)

    def test_get_no_agent(self):
        params = {"profileId": self.testprofileId1}
        r = self.client.get(reverse('lrs:agent_profile'), params,
                            Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(r.status_code, 400)
        self.assertIn('agent parameter missing', r.content)

    def test_get_no_profileId(self):
        params = {"agent": self.testagent}
        r = self.client.get(reverse('lrs:agent_profile'), params,
                            Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(r.status_code, 200)

    def test_delete(self):
        prof_id = "http://deleteme"
        params = {"profileId": prof_id, "agent": self.testagent}
        path = '%s?%s' % (reverse('lrs:agent_profile'),
                          urllib.parse.urlencode(params))
        profile = {"test": "delete profile", "obj": {"agent": "test"}}
        response = self.client.put(path, profile, content_type=self.content_type, If_None_Match="*",
                                   Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(response.status_code, 204)

        r = self.client.get(reverse('lrs:agent_profile'), params,
                            Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(r.status_code, 200)
        robj = ast.literal_eval(r.content)
        self.assertEqual(robj['test'], profile['test'])
        self.assertEqual(robj['obj']['agent'], profile['obj']['agent'])

        r = self.client.delete(reverse('lrs:agent_profile'), params,
                               Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(r.status_code, 204)

        r = self.client.get(reverse('lrs:agent_profile'), params,
                            Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(r.status_code, 404)

    def test_get_agent_since(self):
        prof_id = "http://oldprofile/time"
        updated = "2012-06-12:T12:00:00Z"
        params = {"profileId": prof_id, "agent": self.testagent}
        path = '%s?%s' % (reverse('lrs:agent_profile'),
                          urllib.parse.urlencode(params))

        profile = {"test1": "agent profile since time: %s" %
                   updated, "obj": {"agent": "test"}}
        response = self.client.put(path, profile, content_type=self.content_type, updated=updated, If_None_Match="*",
                                   Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(response.status_code, 204)

        r = self.client.get(reverse('lrs:agent_profile'), params,
                            Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(r.status_code, 200)
        robj = ast.literal_eval(r.content)
        self.assertEqual(robj['test1'], profile['test1'])
        self.assertEqual(robj['obj']['agent'], profile['obj']['agent'])

        since = "2012-07-01T12:00:00Z"
        params2 = {"agent": self.testagent, "since": since}
        r2 = self.client.get(reverse('lrs:agent_profile'), params2,
                             Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertNotIn(prof_id, r2.content)

        self.client.delete(reverse('lrs:agent_profile'), params,
                           Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)

    def test_get_agent_since_tz(self):
        prof_id = "http://oldprofile/time"
        updated = "2012-06-12:T12:00:00Z"
        params = {"profileId": prof_id, "agent": self.testagent}
        path = '%s?%s' % (reverse('lrs:agent_profile'),
                          urllib.parse.urlencode(params))

        profile = {"test2": "agent profile since time: %s" %
                   updated, "obj": {"agent": "test"}}
        response = self.client.put(path, profile, content_type=self.content_type, updated=updated, If_None_Match="*",
                                   Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)

        r = self.client.get(reverse('lrs:agent_profile'), params,
                            Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(r.status_code, 200)
        robj = ast.literal_eval(r.content)
        self.assertEqual(robj['test2'], profile['test2'])
        self.assertEqual(robj['obj']['agent'], profile['obj']['agent'])

        prof_id2 = "http://newprofile/timezone"
        updated2 = "2012-07-01T08:30:00-04:00"

        params2 = {"profileId": prof_id2, "agent": self.testagent}
        path2 = '%s?%s' % (reverse('lrs:agent_profile'),
                           urllib.parse.urlencode(params2))

        profile2 = {"test3": "agent profile since time: %s" %
                    updated2, "obj": {"agent": "test"}}
        response = self.client.put(path2, profile2, content_type=self.content_type, updated=updated2, If_None_Match="*",
                                   Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(response.status_code, 204)

        r2 = self.client.get(reverse('lrs:agent_profile'), params2,
                             Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(r2.status_code, 200)
        robj2 = ast.literal_eval(r2.content)
        self.assertEqual(robj2['test3'], profile2['test3'])
        self.assertEqual(robj2['obj']['agent'], profile2['obj']['agent'])

        since = "2012-07-01T12:00:00Z"

        par = {"agent": self.testagent, "since": since}
        r = self.client.get(reverse('lrs:agent_profile'), par,
                            Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)

        self.assertNotIn(prof_id, r.content)
        self.assertIn(prof_id2, r.content)

        self.client.delete(reverse('lrs:agent_profile'), params,
                           Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)
        self.client.delete(reverse('lrs:agent_profile'), params2,
                           Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)

    def test_cors_post_put_delete(self):
        prof_id = "http://deleteme.too"
        path = '%s?%s' % (reverse('lrs:agent_profile'),
                          urllib.parse.urlencode({"method": "PUT"}))
        content = {"test": "delete profile", "obj": {
            "actor": "test", "testcase": "ie cors post for put and delete"}}
        thedata = "profileId=%s&agent=%s&content=%s&Authorization=%s&Content-Type=application/json&X-Experience-API-Version=1.0.0&If-None-Match=*" % (
            prof_id, self.testagent, urllib.parse.quote(str(content)), self.auth)
        response = self.client.post(
            path, thedata, content_type="application/x-www-form-urlencoded")
        self.assertEqual(response.status_code, 204)
        r = self.client.get(reverse('lrs:agent_profile'), {
                            "profileId": prof_id, "agent": self.testagent}, Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(r.status_code, 200)
        import ast
        c = ast.literal_eval(r.content)
        self.assertEqual(c['test'], content['test'])

        thedata = "profileId=%s&agent=%s&Authorization=%s&X-Experience-API-Version=1.0" % (
            prof_id, self.testagent, self.auth)
        path = '%s?%s' % (reverse('lrs:agent_profile'),
                          urllib.parse.urlencode({"method": "DELETE"}))
        r = self.client.post(path, thedata, content_type="application/x-www-form-urlencoded",
                             Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(r.status_code, 204)

        r = self.client.get(reverse('lrs:agent_profile'), {
                            "profileId": prof_id, "agent": self.testagent}, Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(r.status_code, 404)

    def test_group_as_agent(self):
        ot = "Group"
        name = "the group APT"
        mbox = "mailto:the.groupAPT@example.com"
        members = [{"name": "agentA", "mbox": "mailto:agentA@example.com"},
                   {"name": "agentB", "mbox": "mailto:agentB@example.com"}]
        testagent = json.dumps(
            {"objectType": ot, "name": name, "mbox": mbox, "member": members})
        testprofileId = "http://profile.test.id/group.as.agent/"
        testparams1 = {"profileId": testprofileId, "agent": testagent}
        path = '%s?%s' % (reverse('lrs:agent_profile'),
                          urllib.parse.urlencode(testparams1))
        testprofile = {"test": "put profile - group as agent",
                       "obj": {"agent": "group"}}
        put1 = self.client.put(path, testprofile, content_type=self.content_type, If_None_Match="*",
                               Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)

        self.assertEqual(put1.status_code, 204)

        getr = self.client.get(reverse('lrs:agent_profile'), testparams1,
                               Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(getr.status_code, 200)
        robj = ast.literal_eval(getr.content)
        self.assertEqual(robj['test'], testprofile['test'])
        self.assertEqual(robj['obj']['agent'], testprofile['obj']['agent'])

        self.client.delete(reverse('lrs:agent_profile'), testparams1,
                           Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)

    def test_post_new_profile(self):
        params = {"profileId": "prof:test_post_new_profile",
                  "agent": self.testagent}
        path = '%s?%s' % (reverse('lrs:agent_profile'),
                          urllib.parse.urlencode(params))
        prof = {"test": "post new profile", "obj": {
            "agent": "mailto:test@example.com"}}

        post = self.client.post(path, prof, content_type="application/json",
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
                  "agent": self.testagent}
        path = '%s?%s' % (reverse('lrs:agent_profile'),
                          urllib.parse.urlencode(params))
        prof = ""

        post = self.client.post(path, prof, content_type="application/json",
                                Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)

        self.assertEqual(post.status_code, 400)
        self.assertEqual(post.content, 'Could not find the profile document')

    def test_post_and_put_profile(self):
        params = {"profileId": "prof:test_post_and_put_profile",
                  "agent": self.testagent}
        path = '%s?%s' % (reverse('lrs:agent_profile'),
                          urllib.parse.urlencode(params))
        prof = {"test": "post and put profile", "obj": {
            "agent": "mailto:test@example.com"}}

        post = self.client.post(path, json.dumps(prof), content_type="application/json",
                                Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(post.status_code, 204)

        get = self.client.get(path, Authorization=self.auth,
                              X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(get.status_code, 200)
        self.assertEqual(json.loads(get.content), prof)
        self.assertEqual(get.get('etag'), '"%s"' %
                         hashlib.sha1(get.content).hexdigest())

        params = {"profileId": "prof:test_post_and_put_profile",
                  "agent": self.testagent}
        path = '%s?%s' % (reverse('lrs:agent_profile'),
                          urllib.parse.urlencode(params))
        prof = {"wipe": "new data"}
        thehash = get.get('etag')

        put = self.client.put(path, json.dumps(prof), content_type="application/json", If_Match=thehash,
                              Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(put.status_code, 204)

        get = self.client.get(path, Authorization=self.auth,
                              X_Experience_API_Version=settings.XAPI_VERSION)
        self.assertEqual(get.status_code, 200)
        self.assertEqual(json.loads(get.content), prof)
        etag = '"%s"' % hashlib.sha1(get.content).hexdigest()
        self.assertEqual(get.get('etag'), etag)

        self.client.delete(path, Authorization=self.auth,
                           X_Experience_API_Version=settings.XAPI_VERSION)