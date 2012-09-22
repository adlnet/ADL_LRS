from django.test import TestCase
from django.test.utils import setup_test_environment
from django.core.urlresolvers import reverse
from lrs import models, views
import json
import time
import hashlib
import urllib
from os import path
import sys
from lrs.objects import Activity
import base64

#TODO: delete profiles that are being stored in /var/www/adllrs/media/activity profiles
class ActivityProfileTests(TestCase):
    test_activityId1 = 'act-1'
    test_activityId2 = 'act-2'
    test_activityId3 = 'act-3'
    other_activityId = 'act-other'
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

        self.act1 = Activity.Activity(json.dumps({'objectType':'Activity', 'id': self.test_activityId1}))
        self.act2 = Activity.Activity(json.dumps({'objectType':'Activity', 'id': self.test_activityId2}))
        self.act3 = Activity.Activity(json.dumps({'objectType':'Activity', 'id': self.test_activityId3}))
        self.actother = Activity.Activity(json.dumps({'objectType':'Activity', 'id': self.other_activityId}))

        self.testparams1 = {"profileId": self.testprofileId1, "activityId": self.test_activityId1}
        path = '%s?%s' % (reverse(views.activity_profile), urllib.urlencode(self.testparams1))
        self.testprofile1 = {"test":"put profile 1","obj":{"activity":"test"}}
        self.put1 = self.client.put(path, self.testprofile1, content_type=self.content_type, Authorization=self.auth)
        
        self.testparams2 = {"profileId": self.testprofileId2, "activityId": self.test_activityId2}
        path = '%s?%s' % (reverse(views.activity_profile), urllib.urlencode(self.testparams2))
        self.testprofile2 = {"test":"put profile 2","obj":{"activity":"test"}}
        self.put2 = self.client.put(path, self.testprofile2, content_type=self.content_type, Authorization=self.auth)

        self.testparams3 = {"profileId": self.testprofileId3, "activityId": self.test_activityId3}
        path = '%s?%s' % (reverse(views.activity_profile), urllib.urlencode(self.testparams3))
        self.testprofile3 = {"test":"put profile 3","obj":{"activity":"test"}}
        self.put3 = self.client.put(path, self.testprofile3, content_type=self.content_type, Authorization=self.auth)

        self.testparams4 = {"profileId": self.otherprofileId1, "activityId": self.other_activityId}
        path = '%s?%s' % (reverse(views.activity_profile), urllib.urlencode(self.testparams4))
        self.otherprofile1 = {"test":"put profile other","obj":{"activity":"other"}}
        self.put4 = self.client.put(path, self.otherprofile1, content_type=self.content_type, Authorization=self.auth)

        self.testparams5 = {"profileId": self.otherprofileId1, "activityId": self.test_activityId1}
        path = '%s?%s' % (reverse(views.activity_profile), urllib.urlencode(self.testparams5))
        self.anotherprofile1 = {"test":"put another profile 1","obj":{"activity":"other"}}
        self.put5 = self.client.put(path, self.anotherprofile1, content_type=self.content_type, Authorization=self.auth)

        
    def tearDown(self):
        self.client.delete(reverse(views.activity_profile), self.testparams1, Authorization=self.auth)
        self.client.delete(reverse(views.activity_profile), self.testparams2, Authorization=self.auth)
        self.client.delete(reverse(views.activity_profile), self.testparams3, Authorization=self.auth)
        self.client.delete(reverse(views.activity_profile), self.testparams4, Authorization=self.auth)    
        self.client.delete(reverse(views.activity_profile), self.testparams5, Authorization=self.auth)    
    
    def test_put(self):
        #Test the puts
        self.assertEqual(self.put1.status_code, 200)
        self.assertEqual(self.put1.content, 'Success -- activity profile - method = PUT - profileId = %s' % self.testprofileId1)
        
        self.assertEqual(self.put2.status_code, 200)
        self.assertEqual(self.put2.content, 'Success -- activity profile - method = PUT - profileId = %s' % self.testprofileId2)

        self.assertEqual(self.put3.status_code, 200)
        self.assertEqual(self.put3.content, 'Success -- activity profile - method = PUT - profileId = %s' % self.testprofileId3)

        self.assertEqual(self.put4.status_code, 200)
        self.assertEqual(self.put4.content, 'Success -- activity profile - method = PUT - profileId = %s' % self.otherprofileId1)

        self.assertEqual(self.put5.status_code, 200)
        self.assertEqual(self.put5.content, 'Success -- activity profile - method = PUT - profileId = %s' % self.otherprofileId1)

        #Grab the activity models
        actmodel1 = models.activity.objects.filter(activity_id=self.test_activityId1)[0]
        actmodel2 = models.activity.objects.filter(activity_id=self.test_activityId2)[0]
        actmodel3 = models.activity.objects.filter(activity_id=self.test_activityId3)[0]
        actmodel4 = models.activity.objects.filter(activity_id=self.other_activityId)[0]

        #Make sure profiles have correct activities
        self.assertEqual(models.activity_profile.objects.filter(profileId=self.testprofileId1)[0].activity, actmodel1)
        self.assertEqual(models.activity_profile.objects.filter(profileId=self.testprofileId2)[0].activity, actmodel2)
        self.assertEqual(models.activity_profile.objects.filter(profileId=self.testprofileId3)[0].activity, actmodel3)
        self.assertEqual(models.activity_profile.objects.filter(profileId=self.otherprofileId1)[0].activity, actmodel4)
        self.assertEqual(models.activity_profile.objects.filter(profileId=self.otherprofileId1)[1].activity, actmodel1)

        
    def test_put_no_params(self):
        put = self.client.put(reverse(views.activity_profile) ,content_type=self.content_type, Authorization=self.auth)
        self.assertEquals(put.content, 'Error -- activity_profile - method = PUT, but activityId parameter missing..')

    def test_put_no_activityId(self):
        put = self.client.put(reverse(views.activity_profile), {'profileId':'10'},content_type=self.content_type, Authorization=self.auth)
        self.assertEquals(put.content, 'Error -- activity_profile - method = PUT, but activityId parameter missing..')

    def test_put_no_profileId(self):
        testparams = {'activityId':'act'}
        path = '%s?%s' % (reverse(views.activity_profile), urllib.urlencode(testparams))
        put = self.client.put(path, content_type=self.content_type, Authorization=self.auth)
        self.assertEquals(put.content, 'Error -- activity_profile - method = PUT, but profileId parameter missing..')

    def test_put_etag_missing_on_change(self):
        path = '%s?%s' % (reverse(views.activity_profile), urllib.urlencode(self.testparams1))
        profile = {"test":"error - trying to put new profile w/o etag header","obj":{"activity":"test"}}
        response = self.client.put(path, profile, content_type=self.content_type, Authorization=self.auth)
        self.assertEqual(response.status_code, 409)
        self.assertIn('If-Match and If-None-Match headers were missing', response.content)
        
        r = self.client.get(reverse(views.activity_profile), self.testparams1)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.content, '%s' % self.testprofile1)

    def test_put_etag_right_on_change(self):
        path = '%s?%s' % (reverse(views.activity_profile), urllib.urlencode(self.testparams1))
        profile = {"test":"good - trying to put new profile w/ etag header","obj":{"activity":"test"}}
        thehash = '"%s"' % hashlib.sha1('%s' % self.testprofile1).hexdigest()
        response = self.client.put(path, profile, content_type=self.content_type, if_match=thehash, Authorization=self.auth)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, 'Success -- activity profile - method = PUT - profileId = %s' % self.testprofileId1)

        r = self.client.get(reverse(views.activity_profile), self.testparams1)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.content, '%s' % profile)

    def test_put_etag_wrong_on_change(self):
        path = '%s?%s' % (reverse(views.activity_profile), urllib.urlencode(self.testparams1))
        profile = {"test":"error - trying to put new profile w/ wrong etag value","obj":{"activity":"test"}}
        thehash = '"%s"' % hashlib.sha1('%s' % 'wrong hash').hexdigest()
        response = self.client.put(path, profile, content_type=self.content_type, if_match=thehash, Authorization=self.auth)
        self.assertEqual(response.status_code, 412)
        self.assertIn('No resources matched', response.content)

        r = self.client.get(reverse(views.activity_profile), self.testparams1)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.content, '%s' % self.testprofile1)

    def test_put_etag_if_none_match_good(self):
        params = {"profileId": 'http://etag.nomatch.good', "activityId": self.test_activityId1}
        path = '%s?%s' % (reverse(views.activity_profile), urllib.urlencode(params))
        profile = {"test":"good - trying to put new profile w/ if none match etag header","obj":{"activity":"test"}}
        response = self.client.put(path, profile, content_type=self.content_type, if_none_match='*', Authorization=self.auth)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, 'Success -- activity profile - method = PUT - profileId = %s' % 'http://etag.nomatch.good')

        r = self.client.get(reverse(views.activity_profile), params)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.content, '%s' % profile)

        r = self.client.delete(reverse(views.activity_profile), params, Authorization=self.auth)

    def test_put_etag_if_none_match_bad(self):
        path = '%s?%s' % (reverse(views.activity_profile), urllib.urlencode(self.testparams1))
        profile = {"test":"error - trying to put new profile w/ if none match etag but one exists","obj":{"activity":"test"}}
        response = self.client.put(path, profile, content_type=self.content_type, if_none_match='*', Authorization=self.auth)
        self.assertEqual(response.status_code, 412)
        self.assertEqual(response.content, 'Resource detected')

        r = self.client.get(reverse(views.activity_profile), self.testparams1)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.content, '%s' % self.testprofile1)
  
    #TODO: Need etag for ID list?
    def test_get_activity_only(self):
        response = self.client.get(reverse(views.activity_profile), {'activityId':self.test_activityId2})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.testprofileId2)
        #resp_hash = hashlib.sha1(response.content).hexdigest()
        #self.assertEqual(response['etag'], '"%s"' % resp_hash)
        params = {'activityId': self.test_activityId2, 'profileId': self.testprofileId2}

        self.client.delete(reverse(views.activity_profile), params, Authorization=self.auth)

    def test_get_activity_profileId(self):
        response = self.client.get(reverse(views.activity_profile), {'activityId':self.test_activityId1,'profileId':self.testprofileId1})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.testprofile1)
        resp_hash = hashlib.sha1(response.content).hexdigest()
        self.assertEqual(response['etag'], '"%s"' % resp_hash)    
        params = {'activityId': self.test_activityId1, 'profileId': self.testprofileId1}

        self.client.delete(reverse(views.activity_profile), params, Authorization=self.auth)


    def test_get_activity_since(self):
        #Convert since to string since will be string in header
        since = str(time.time())
        response = self.client.get(reverse(views.activity_profile), {'activityId': self.test_activityId3,'since':since})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.testprofileId3)
        self.assertEqual(response['since'], since)
        #resp_hash = hashlib.sha1(response.content).hexdigest()
        #self.assertEqual(response['etag'], '"%s"' % resp_hash)
        params = {'activityId': self.test_activityId3, 'profileId': self.testprofileId3}

        self.client.delete(reverse(views.activity_profile), params, Authorization=self.auth)
    
    def test_get_no_activity_profileId(self):
        response = self.client.get(reverse(views.activity_profile), {'profileId': self.testprofileId3})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.content, 'Error -- activity_profile - method = GET, but no activityId parameter.. the activityId parameter is required')

    def test_get_no_activity_since(self):
        since = str(time.time())
        response = self.client.get(reverse(views.activity_profile), {'since':since})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.content, 'Error -- activity_profile - method = GET, but no activityId parameter.. the activityId parameter is required')
    
    def test_delete(self):
        response = self.client.delete(reverse(views.activity_profile), {'activityId':self.other_activityId, 'profileId':self.otherprofileId1}, Authorization=self.auth)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, 'Success -- activity profile - method = DELETE - profileId = %s' % self.otherprofileId1)        
