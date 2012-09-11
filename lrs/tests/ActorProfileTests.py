from django.test import TestCase
from django.test.utils import setup_test_environment
from django.core.urlresolvers import reverse
from lrs import views
import datetime
from django.utils.timezone import utc
import hashlib
import urllib
import base64

#TODO: delete profiles that are being stored
class ActorProfileTests(TestCase):
    testactor = '{"mbox":["mailto:test@example.com"]}'
    otheractor = '{"mbox":["mailto:other@example.com"]}'
    content_type = "application/json"
    testprofileId1 = "http://profile.test.id/test/1"
    testprofileId2 = "http://profile.test.id/test/2"
    testprofileId3 = "http://profile.test.id/test/3"
    otherprofileId1 = "http://profile.test.id/other/1"

    def setUp(self):
        self.username = "tester"
        self.email = "test@tester.com"
        self.password = "test"
        self.auth = "Basic %s" % base64.b64encode("%s:%s" % (self.username, self.password))
        form = {'username':self.username, 'email': self.email,'password':self.password,'password2':self.password}
        response = self.client.post(reverse(views.register),form)
        
        self.testparams1 = {"profileId": self.testprofileId1, "actor": self.testactor}
        path = '%s?%s' % (reverse(views.actor_profile), urllib.urlencode(self.testparams1))
        self.testprofile1 = {"test":"put profile 1","obj":{"actor":"test"}}
        self.put1 = self.client.put(path, self.testprofile1, content_type=self.content_type, HTTP_AUTHORIZATION=self.auth)

        self.testparams2 = {"profileId": self.testprofileId2, "actor": self.testactor}
        path = '%s?%s' % (reverse(views.actor_profile), urllib.urlencode(self.testparams2))
        self.testprofile2 = {"test":"put profile 2","obj":{"actor":"test"}}
        self.put2 = self.client.put(path, self.testprofile2, content_type=self.content_type, HTTP_AUTHORIZATION=self.auth)

        self.testparams3 = {"profileId": self.testprofileId3, "actor": self.testactor}
        path = '%s?%s' % (reverse(views.actor_profile), urllib.urlencode(self.testparams3))
        self.testprofile3 = {"test":"put profile 3","obj":{"actor":"test"}}
        self.put3 = self.client.put(path, self.testprofile3, content_type=self.content_type, HTTP_AUTHORIZATION=self.auth)

        self.testparams4 = {"profileId": self.otherprofileId1, "actor": self.otheractor}
        path = '%s?%s' % (reverse(views.actor_profile), urllib.urlencode(self.testparams4))
        self.otherprofile1 = {"test":"put profile 1","obj":{"actor":"other"}}
        self.put4 = self.client.put(path, self.otherprofile1, content_type=self.content_type, HTTP_AUTHORIZATION=self.auth)

    def tearDown(self):
        self.client.delete(reverse(views.actor_profile), self.testparams1, HTTP_AUTHORIZATION=self.auth)
        self.client.delete(reverse(views.actor_profile), self.testparams2, HTTP_AUTHORIZATION=self.auth)
        self.client.delete(reverse(views.actor_profile), self.testparams3, HTTP_AUTHORIZATION=self.auth)
        self.client.delete(reverse(views.actor_profile), self.testparams4, HTTP_AUTHORIZATION=self.auth)

    def test_put(self):
        self.assertEqual(self.put1.status_code, 204)
        self.assertEqual(self.put1.content, '')

        self.assertEqual(self.put2.status_code, 204)
        self.assertEqual(self.put2.content, '')

        self.assertEqual(self.put3.status_code, 204)
        self.assertEqual(self.put3.content, '')

        self.assertEqual(self.put4.status_code, 204)
        self.assertEqual(self.put4.content, '')

    def test_put_etag_missing_on_change(self):
        path = '%s?%s' % (reverse(views.actor_profile), urllib.urlencode(self.testparams1))
        profile = {"test":"error - trying to put new profile w/o etag header","obj":{"actor":"test"}}
        response = self.client.put(path, profile, content_type=self.content_type, HTTP_AUTHORIZATION=self.auth)
        self.assertEqual(response.status_code, 409)
        self.assertIn('If-Match and If-None-Match headers were missing', response.content)
        
        r = self.client.get(reverse(views.actor_profile), self.testparams1)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.content, '%s' % self.testprofile1)

    def test_put_etag_right_on_change(self):
        path = '%s?%s' % (reverse(views.actor_profile), urllib.urlencode(self.testparams1))
        profile = {"test":"good - trying to put new profile w/ etag header","obj":{"actor":"test"}}
        thehash = '"%s"' % hashlib.sha1('%s' % self.testprofile1).hexdigest()
        response = self.client.put(path, profile, content_type=self.content_type, if_match=thehash, HTTP_AUTHORIZATION=self.auth)
        self.assertEqual(response.status_code, 204)
        self.assertEqual(response.content, '')

        r = self.client.get(reverse(views.actor_profile), self.testparams1)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.content, '%s' % profile)

    def test_put_etag_wrong_on_change(self):
        path = '%s?%s' % (reverse(views.actor_profile), urllib.urlencode(self.testparams1))
        profile = {"test":"error - trying to put new profile w/ wrong etag value","obj":{"actor":"test"}}
        thehash = '"%s"' % hashlib.sha1('%s' % 'wrong hash').hexdigest()
        response = self.client.put(path, profile, content_type=self.content_type, if_match=thehash, HTTP_AUTHORIZATION=self.auth)
        self.assertEqual(response.status_code, 412)
        self.assertIn('No resources matched', response.content)

        r = self.client.get(reverse(views.actor_profile), self.testparams1)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.content, '%s' % self.testprofile1)

    def test_put_etag_if_none_match_good(self):
        params = {"profileId": 'http://etag.nomatch.good', "actor": self.testactor}
        path = '%s?%s' % (reverse(views.actor_profile), urllib.urlencode(params))
        profile = {"test":"good - trying to put new profile w/ if none match etag header","obj":{"actor":"test"}}
        response = self.client.put(path, profile, content_type=self.content_type, if_none_match='*', HTTP_AUTHORIZATION=self.auth)
        self.assertEqual(response.status_code, 204)
        self.assertEqual(response.content, '')

        r = self.client.get(reverse(views.actor_profile), params)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.content, '%s' % profile)

        r = self.client.delete(reverse(views.actor_profile), params, HTTP_AUTHORIZATION=self.auth)

    def test_put_etag_if_none_match_bad(self):
        path = '%s?%s' % (reverse(views.actor_profile), urllib.urlencode(self.testparams1))
        profile = {"test":"error - trying to put new profile w/ if none match etag but one exists","obj":{"actor":"test"}}
        response = self.client.put(path, profile, content_type=self.content_type, if_none_match='*', HTTP_AUTHORIZATION=self.auth)
        self.assertEqual(response.status_code, 412)
        self.assertEqual(response.content, 'Resource detected')

        r = self.client.get(reverse(views.actor_profile), self.testparams1)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.content, '%s' % self.testprofile1)

    def test_get(self):
        r = self.client.get(reverse(views.actor_profile), self.testparams1)
        self.assertEqual(r.status_code, 200)
        prof1_str = '%s' % self.testprofile1
        self.assertEqual(r.content, prof1_str)
        self.assertEqual(r['etag'], '"%s"' % hashlib.sha1(prof1_str).hexdigest())

        r2 = self.client.get(reverse(views.actor_profile), self.testparams2)
        self.assertEqual(r2.status_code, 200)
        prof2_str = '%s' % self.testprofile2
        self.assertEqual(r2.content, prof2_str)
        self.assertEqual(r2['etag'], '"%s"' % hashlib.sha1(prof2_str).hexdigest())
        
        r3 = self.client.get(reverse(views.actor_profile), self.testparams3)
        self.assertEqual(r3.status_code, 200)
        prof3_str = '%s' % self.testprofile3
        self.assertEqual(r3.content, prof3_str)
        self.assertEqual(r3['etag'], '"%s"' % hashlib.sha1(prof3_str).hexdigest())

        r4 = self.client.get(reverse(views.actor_profile), self.testparams4)
        self.assertEqual(r4.status_code, 200)
        prof4_str = '%s' % self.otherprofile1
        self.assertEqual(r4.content, prof4_str)
        self.assertEqual(r4['etag'], '"%s"' % hashlib.sha1(prof4_str).hexdigest())

    def test_get_no_params(self):
        r = self.client.get(reverse(views.actor_profile))
        self.assertEqual(r.status_code, 400)
        self.assertIn('actor parameter missing', r.content)
    
    def test_get_no_actor(self):
        params = {"profileId": self.testprofileId1}
        r = self.client.get(reverse(views.actor_profile), params)
        self.assertEqual(r.status_code, 400)
        self.assertIn('actor parameter missing', r.content)

    def test_get_no_profileId(self):
        params = {"actor": self.testactor}
        r = self.client.get(reverse(views.actor_profile), params)
        self.assertEqual(r.status_code, 200)
    
    def test_delete(self):
        prof_id = "http://deleteme"
        params = {"profileId": prof_id, "actor": self.testactor}
        path = '%s?%s' % (reverse(views.actor_profile), urllib.urlencode(params))
        profile = {"test":"delete profile","obj":{"actor":"test"}}
        response = self.client.put(path, profile, content_type=self.content_type, HTTP_AUTHORIZATION=self.auth)
        
        r = self.client.get(reverse(views.actor_profile), params)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.content, '%s' % profile)

        r = self.client.delete(reverse(views.actor_profile), params, HTTP_AUTHORIZATION=self.auth)
        self.assertEqual(r.status_code, 204)

        r = self.client.get(reverse(views.actor_profile), params)
        self.assertEqual(r.status_code, 404)

    def test_get_actor_since(self):
        prof_id = "http://oldprofile/time"
        updated =  datetime.datetime(2012, 6, 12, 12, 00).replace(tzinfo=utc)
        params = {"profileId": prof_id, "actor": self.testactor}
        path = '%s?%s' % (reverse(views.actor_profile), urllib.urlencode(params))
        profile = {"test":"actor profile since time: %s" % updated,"obj":{"actor":"test"}}
        response = self.client.put(path, profile, content_type=self.content_type, updated=updated.isoformat(), HTTP_AUTHORIZATION=self.auth)

        r = self.client.get(reverse(views.actor_profile), params)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.content, '%s' % profile)

        since = datetime.datetime(2012, 7, 1, 12, 00).replace(tzinfo=utc)
        params2 = {"actor": self.testactor, "since":since.isoformat()}
        r2 = self.client.get(reverse(views.actor_profile), params2)
        self.assertNotIn(prof_id, r2.content)

        self.client.delete(reverse(views.actor_profile), params, HTTP_AUTHORIZATION=self.auth)
