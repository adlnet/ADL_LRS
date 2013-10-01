import ast
import json
import time
import hashlib
import urllib
from os import path
import base64
from django.test import TestCase
from django.conf import settings
from django.core.urlresolvers import reverse
from lrs import models, views
from lrs.objects.ActivityManager import ActivityManager

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
        print "\n%s" % __name__

    def setUp(self):
        self.username = "tester"
        self.email = "test@tester.com"
        self.password = "test"
        self.auth = "Basic %s" % base64.b64encode("%s:%s" % (self.username, self.password))
        form = {'username':self.username, 'email': self.email,'password':self.password,'password2':self.password}
        response = self.client.post(reverse(views.register),form, X_Experience_API_Version="1.0.0")

        self.testparams1 = {"profileId": self.testprofileId1, "activityId": self.test_activityId1}
        path = '%s?%s' % (reverse(views.activity_profile), urllib.urlencode(self.testparams1))
        self.testprofile1 = {"test":"put profile 1","obj":{"activity":"test"}}
        self.put1 = self.client.put(path, json.dumps(self.testprofile1), content_type=self.content_type, Authorization=self.auth,  X_Experience_API_Version="1.0.0")
        
        self.testparams2 = {"profileId": self.testprofileId2, "activityId": self.test_activityId2}
        path = '%s?%s' % (reverse(views.activity_profile), urllib.urlencode(self.testparams2))
        self.testprofile2 = {"test":"put profile 2","obj":{"activity":"test"}}
        self.put2 = self.client.put(path, json.dumps(self.testprofile2), content_type=self.content_type, Authorization=self.auth,  X_Experience_API_Version="1.0.0")

        self.testparams3 = {"profileId": self.testprofileId3, "activityId": self.test_activityId3}
        path = '%s?%s' % (reverse(views.activity_profile), urllib.urlencode(self.testparams3))
        self.testprofile3 = {"test":"put profile 3","obj":{"activity":"test"}}
        self.put3 = self.client.put(path, json.dumps(self.testprofile3), content_type=self.content_type, Authorization=self.auth,  X_Experience_API_Version="1.0.0")

        self.testparams4 = {"profileId": self.otherprofileId1, "activityId": self.other_activityId}
        path = '%s?%s' % (reverse(views.activity_profile), urllib.urlencode(self.testparams4))
        self.otherprofile1 = {"test":"put profile other","obj":{"activity":"other"}}
        self.put4 = self.client.put(path, json.dumps(self.otherprofile1), content_type=self.content_type, Authorization=self.auth,  X_Experience_API_Version="1.0.0")

        self.testparams5 = {"profileId": self.otherprofileId1, "activityId": self.test_activityId1}
        path = '%s?%s' % (reverse(views.activity_profile), urllib.urlencode(self.testparams5))
        self.anotherprofile1 = {"test":"put another profile 1","obj":{"activity":"other"}}
        self.put5 = self.client.put(path, json.dumps(self.anotherprofile1), content_type=self.content_type, Authorization=self.auth,  X_Experience_API_Version="1.0.0")

        
    def tearDown(self):
        self.client.delete(reverse(views.activity_profile), self.testparams1, Authorization=self.auth, X_Experience_API_Version="1.0.0")
        self.client.delete(reverse(views.activity_profile), self.testparams2, Authorization=self.auth, X_Experience_API_Version="1.0.0")
        self.client.delete(reverse(views.activity_profile), self.testparams3, Authorization=self.auth, X_Experience_API_Version="1.0.0")
        self.client.delete(reverse(views.activity_profile), self.testparams4, Authorization=self.auth, X_Experience_API_Version="1.0.0")    
        self.client.delete(reverse(views.activity_profile), self.testparams5, Authorization=self.auth, X_Experience_API_Version="1.0.0")    
    
    def test_put(self):
        #Test the puts
        self.assertEqual(self.put1.status_code, 204)

        self.assertEqual(self.put2.status_code, 204)
        
        self.assertEqual(self.put3.status_code, 204)
        
        self.assertEqual(self.put4.status_code, 204)
        
        self.assertEqual(self.put5.status_code, 204)

        #Make sure profiles have correct activities
        self.assertEqual(models.ActivityProfile.objects.filter(profileId=self.testprofileId1)[0].activityId, self.test_activityId1)
        self.assertEqual(models.ActivityProfile.objects.filter(profileId=self.testprofileId2)[0].activityId, self.test_activityId2)
        self.assertEqual(models.ActivityProfile.objects.filter(profileId=self.testprofileId3)[0].activityId, self.test_activityId3)

    def test_put_no_params(self):
        put = self.client.put(reverse(views.activity_profile) ,content_type=self.content_type, Authorization=self.auth, X_Experience_API_Version="1.0.0")
        self.assertEquals(put.content, 'Error -- activity_profile - method = PUT, but activityId parameter missing..')

    def test_put_no_activityId(self):
        put = self.client.put(reverse(views.activity_profile), {'profileId':'10'},content_type=self.content_type, Authorization=self.auth, X_Experience_API_Version="1.0.0")
        self.assertEquals(put.content, 'Error -- activity_profile - method = PUT, but activityId parameter missing..')

    def test_put_no_profileId(self):
        testparams = {'activityId':'act:act:act'}
        path = '%s?%s' % (reverse(views.activity_profile), urllib.urlencode(testparams))
        put = self.client.put(path, content_type=self.content_type, Authorization=self.auth, X_Experience_API_Version="1.0.0")
        self.assertEquals(put.content, 'Error -- activity_profile - method = PUT, but profileId parameter missing..')

    def test_put_etag_missing_on_change(self):
        path = '%s?%s' % (reverse(views.activity_profile), urllib.urlencode(self.testparams1))
        profile = {"test":"error - trying to put new profile w/o etag header","obj":{"activity":"test"}}
        response = self.client.put(path, profile, content_type=self.content_type, Authorization=self.auth, X_Experience_API_Version="1.0.0")
        self.assertEqual(response.status_code, 409)
        self.assertIn('If-Match and If-None-Match headers were missing', response.content)
        
        r = self.client.get(reverse(views.activity_profile), self.testparams1, X_Experience_API_Version="1.0.0", Authorization=self.auth)
        self.assertEqual(r.status_code, 200)
        robj = ast.literal_eval(r.content)
        self.assertEqual(robj['test'], self.testprofile1['test'])
        self.assertEqual(robj['obj']['activity'], self.testprofile1['obj']['activity'])

    def test_put_etag_right_on_change(self):
        path = '%s?%s' % (reverse(views.activity_profile), urllib.urlencode(self.testparams1))
        profile = {"test":"good - trying to put new profile w/ etag header","obj":{"activity":"act:test"}}
        thehash = '"%s"' % hashlib.sha1(json.dumps(self.testprofile1)).hexdigest()
        response = self.client.put(path, json.dumps(profile), content_type=self.content_type, If_Match=thehash, Authorization=self.auth, X_Experience_API_Version="1.0.0")
        self.assertEqual(response.status_code, 204)
        r = self.client.get(reverse(views.activity_profile), self.testparams1, X_Experience_API_Version="1.0.0", Authorization=self.auth)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.content, json.dumps(profile))

    def test_put_etag_wrong_on_change(self):
        path = '%s?%s' % (reverse(views.activity_profile), urllib.urlencode(self.testparams1))
        profile = {"test":"error - trying to put new profile w/ wrong etag value","obj":{"activity":"act:test"}}
        thehash = '"%s"' % hashlib.sha1('%s' % 'wrong hash').hexdigest()
        response = self.client.put(path, profile, content_type=self.content_type, If_Match=thehash, Authorization=self.auth, X_Experience_API_Version="1.0.0")
        self.assertEqual(response.status_code, 412)
        self.assertIn('No resources matched', response.content)

        r = self.client.get(reverse(views.activity_profile), self.testparams1, X_Experience_API_Version="1.0.0", Authorization=self.auth)
        self.assertEqual(r.status_code, 200)
        robj = ast.literal_eval(r.content)
        self.assertEqual(robj['test'], self.testprofile1['test'])
        self.assertEqual(robj['obj']['activity'], self.testprofile1['obj']['activity'])

    def test_put_etag_if_none_match_good(self):
        params = {"profileId": 'http://etag.nomatch.good', "activityId": self.test_activityId1}
        path = '%s?%s' % (reverse(views.activity_profile), urllib.urlencode(params))
        profile = {"test":"good - trying to put new profile w/ if none match etag header","obj":{"activity":"act:test"}}
        response = self.client.put(path, json.dumps(profile), content_type=self.content_type, if_none_match='*', Authorization=self.auth, X_Experience_API_Version="1.0.0")
        self.assertEqual(response.status_code, 204)
        r = self.client.get(reverse(views.activity_profile), params, X_Experience_API_Version="1.0.0", Authorization=self.auth)
        self.assertEqual(r.status_code, 200)
        robj = ast.literal_eval(r.content)
        self.assertEqual(robj['test'], profile['test'])
        self.assertEqual(robj['obj']['activity'], profile['obj']['activity'])

        r = self.client.delete(reverse(views.activity_profile), params, Authorization=self.auth, X_Experience_API_Version="1.0.0")

    def test_put_etag_if_none_match_bad(self):
        path = '%s?%s' % (reverse(views.activity_profile), urllib.urlencode(self.testparams1))
        profile = {"test":"error - trying to put new profile w/ if none match etag but one exists","obj":{"activity":"act:test"}}
        response = self.client.put(path, profile, content_type=self.content_type, If_None_Match='*', Authorization=self.auth, X_Experience_API_Version="1.0.0")
        self.assertEqual(response.status_code, 412)
        self.assertEqual(response.content, 'Resource detected')

        r = self.client.get(reverse(views.activity_profile), self.testparams1, X_Experience_API_Version="1.0.0", Authorization=self.auth)
        self.assertEqual(r.status_code, 200)
        robj = ast.literal_eval(r.content)
        self.assertEqual(robj['test'], self.testprofile1['test'])
        self.assertEqual(robj['obj']['activity'], self.testprofile1['obj']['activity'])
  
    def test_get_activity_only(self):
        response = self.client.get(reverse(views.activity_profile), {'activityId':self.test_activityId2}, X_Experience_API_Version="1.0.0", Authorization=self.auth)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.testprofileId2)

        params = {'activityId': self.test_activityId2, 'profileId': self.testprofileId2}

        self.client.delete(reverse(views.activity_profile), params, Authorization=self.auth, X_Experience_API_Version="1.0.0")

    def test_get_activity_profileId(self):
        response = self.client.get(reverse(views.activity_profile), {'activityId':self.test_activityId1,'profileId':self.testprofileId1}, X_Experience_API_Version="1.0.0", Authorization=self.auth)
        self.assertEqual(response.status_code, 200)
        robj = ast.literal_eval(response.content)
        self.assertEqual(robj['test'], self.testprofile1['test'])
        self.assertEqual(robj['obj']['activity'], self.testprofile1['obj']['activity'])
        resp_hash = hashlib.sha1(response.content).hexdigest()
        self.assertEqual(response['etag'], '"%s"' % resp_hash)    
        params = {'activityId': self.test_activityId1, 'profileId': self.testprofileId1}

        self.client.delete(reverse(views.activity_profile), params, Authorization=self.auth, X_Experience_API_Version="1.0.0")
    
    def test_get_activity_profileId_no_auth(self):
        # Will return 200 if HTTP_AUTH is not enabled
        response = self.client.get(reverse(views.activity_profile), {'activityId':self.test_activityId1,'profileId':self.testprofileId1}, X_Experience_API_Version="1.0.0")
        self.assertEqual(response.status_code, 401)

    def test_get_activity_profileId_activity_dne(self):
        response = self.client.get(reverse(views.activity_profile), {'activityId':'http://actID','profileId':self.testprofileId1}, X_Experience_API_Version="1.0.0", Authorization=self.auth)
        self.assertEqual(response.status_code, 404)
        
    def test_get_activity_since_tz(self):
        actid = "test:activity"
        profid = "test://test/tz"
        act = ActivityManager(json.dumps({'objectType':'Activity', 'id': actid}))
        params = {"profileId": profid, "activityId": actid}
        path = '%s?%s' % (reverse(views.activity_profile), urllib.urlencode(params))
        prof = {"test":"timezone since","obj":{"activity":"other"}}
        r = self.client.put(path, json.dumps(prof), content_type=self.content_type, updated="2012-11-11T12:00:00+00:00", Authorization=self.auth, X_Experience_API_Version="1.0.0")
        self.assertEqual(r.status_code, 204)

        since = "2012-11-11T12:00:00-02:00"
        response = self.client.get(reverse(views.activity_profile), {'activityId': actid,'since':since}, X_Experience_API_Version="1.0.0", Authorization=self.auth)
        self.assertEqual(response.status_code, 200)
        self.assertNotIn(profid, response.content)
        
        params = {"activityId": actid, "profileId": profid}
        self.client.delete(reverse(views.activity_profile), params, Authorization=self.auth, X_Experience_API_Version="1.0.0")

    def test_get_no_activity_profileId(self):
        response = self.client.get(reverse(views.activity_profile), {'profileId': self.testprofileId3}, X_Experience_API_Version="1.0.0", Authorization=self.auth)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.content, 'Error -- activity_profile - method = GET, but no activityId parameter.. the activityId parameter is required')

    def test_get_no_activity_since(self):
        since = str(time.time())
        response = self.client.get(reverse(views.activity_profile), {'since':since}, X_Experience_API_Version="1.0.0", Authorization=self.auth)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.content, 'Error -- activity_profile - method = GET, but no activityId parameter.. the activityId parameter is required')
    
    def test_delete(self):
        response = self.client.delete(reverse(views.activity_profile), {'activityId':self.other_activityId, 'profileId':self.otherprofileId1}, Authorization=self.auth, X_Experience_API_Version="1.0.0")
        self.assertEqual(response.status_code, 204)
        self.assertEqual(response.content, '')        

    def test_cors_put(self):
        profileid = 'http://test.cors.put'
        activityid = 'act:test_cors_put-activity'
        
        testparams1 = {"profileId": profileid, "activityId": activityid}
        content = {"test":"put profile 1","obj":{"activity":"act:test"}}
        params = "profileId=%s&activityId=%s&Authorization=%s&content=%s&X-Experience-API-Version=1.0" % (profileid, activityid,self.auth,content)
         
        path = path = '%s?%s' % (reverse(views.activity_profile), urllib.urlencode({"method":"PUT"}))
        the_act = ActivityManager(json.dumps({'objectType':'Activity', 'id': activityid}))
        thedata = urllib.quote_plus(params)
        put1 = self.client.post(path, thedata, content_type="application/x-www-form-urlencoded")
        self.assertEqual(put1.status_code, 204)
        get1 = self.client.get(reverse(views.activity_profile), testparams1, Authorization=self.auth, X_Experience_API_Version="1.0.0")
        self.assertEqual(get1.status_code, 200)
        
        import ast
        c = ast.literal_eval(get1.content)
        self.assertEqual(c['test'], content['test'])
        self.client.delete(reverse(views.activity_profile), testparams1, Authorization=self.auth, X_Experience_API_Version="1.0.0")

    def test_cors_put_etag(self):
        pid = 'http://ie.cors.etag/test'
        aid = 'act:ie.cors.etag/test'

        actaid = ActivityManager(json.dumps({'objectType':'Activity', 'id': aid}))
        
        params = {"profileId": pid, "activityId": aid}
        path = '%s?%s' % (reverse(views.activity_profile), urllib.urlencode(self.testparams1))
        tp = {"test":"put example profile for test_cors_put_etag","obj":{"activity":"this should be replaced -- ie cors post/put"}}
        put1 = self.client.put(path, tp, content_type=self.content_type, Authorization=self.auth, X_Experience_API_Version="1.0.0")
        path = '%s?%s' % (reverse(views.activity_profile), urllib.urlencode({"method":"PUT"}))
        
        content = {"test":"good - trying to put new profile w/ etag header - IE cors","obj":{"activity":"test IE cors etag"}}
        thehash = '"%s"' % hashlib.sha1('%s' % tp).hexdigest()
        thedata = "profileId=%s&activityId=%s&If-Match=%s&Authorization=%s&Content-Type=application/x-www-form-urlencoded&content=%s&X-Experience-API-Version=1.0.0" % (pid, aid, thehash, self.auth, content)

        response = self.client.post(path, thedata, content_type="application/x-www-form-urlencoded")
        
        self.assertEqual(response.status_code, 204)
        r = self.client.get(reverse(views.activity_profile), {'activityId': aid, 'profileId': pid}, X_Experience_API_Version="1.0.0", Authorization=self.auth)
        self.assertEqual(r.status_code, 200)
        import ast
        c = ast.literal_eval(r.content)
        self.assertEqual(c['test'], content['test'])

        self.client.delete(reverse(views.activity_profile), {'activityId': aid, 'profileId': pid}, Authorization=self.auth, X_Experience_API_Version="1.0.0")

    def test_tetris_snafu(self):
        params = {"profileId": "http://test.tetris/", "activityId": "act:tetris.snafu"}
        path = '%s?%s' % (reverse(views.activity_profile), urllib.urlencode(params))
        profile = {"test":"put profile 1","obj":{"activity":"test"}}
        the_act = ActivityManager(json.dumps({'objectType':'Activity', 'id': "act:tetris.snafu"}))
        p_r = self.client.put(path, json.dumps(profile), content_type=self.content_type, Authorization=self.auth, X_Experience_API_Version="1.0.0")
        self.assertEqual(p_r.status_code, 204)
        r = self.client.get(reverse(views.activity_profile), {'activityId': "act:tetris.snafu", 'profileId': "http://test.tetris/"}, X_Experience_API_Version="1.0.0", Authorization=self.auth)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r['Content-Type'], self.content_type)
        self.assertIn("\"", r.content)
        
        self.client.delete(path, Authorization=self.auth,  X_Experience_API_Version="1.0.0")

    def test_post_new_profile(self):
        params = {"profileId": "prof:test_post_new_profile", "activityId": "act:test.post.new.prof"}
        path = '%s?%s' % (reverse(views.activity_profile), urllib.urlencode(params))
        prof = {"test":"post new profile","obj":{"activity":"act:test.post.new.prof"}}
        
        post = self.client.post(path, json.dumps(prof), content_type="application/json", Authorization=self.auth,  X_Experience_API_Version="1.0.0")
        self.assertEqual(post.status_code, 204)
        
        get = self.client.get(path, Authorization=self.auth,  X_Experience_API_Version="1.0.0")
        self.assertEqual(get.status_code, 200)
        self.assertEqual(ast.literal_eval(get.content), prof)
        self.assertEqual(get.get('etag'), '"%s"' % hashlib.sha1(get.content).hexdigest())
        self.client.delete(path, Authorization=self.auth,  X_Experience_API_Version="1.0.0")

    def test_post_update_profile(self):
        params = {"profileId": "prof:test_post_update_profile", "activityId": "act:test.post.update.prof"}
        path = '%s?%s' % (reverse(views.activity_profile), urllib.urlencode(params))
        prof = {"test":"post updated profile","obj":{"activity":"act:test.post.update.prof"}}
        
        post = self.client.post(path, json.dumps(prof), content_type="application/json", Authorization=self.auth,  X_Experience_API_Version="1.0.0")
        self.assertEqual(post.status_code, 204)
        
        get = self.client.get(path, Authorization=self.auth,  X_Experience_API_Version="1.0.0")
        self.assertEqual(get.status_code, 200)
        what = ast.literal_eval(get.content)
        self.assertEqual(what, prof)
        etag = '"%s"' % hashlib.sha1(get.content).hexdigest()
        self.assertEqual(get.get('etag'), etag)

        params = {"profileId": "prof:test_post_update_profile", "activityId": "act:test.post.update.prof"}
        path = '%s?%s' % (reverse(views.activity_profile), urllib.urlencode(params))
        prof = {"obj":{"activity":"act:test.post.update.prof_changed", "new":"thing"}, "added":"yes"}
        
        post = self.client.post(path, json.dumps(prof), content_type="application/json", Authorization=self.auth,  X_Experience_API_Version="1.0.0")
        self.assertEqual(post.status_code, 409)

        post = self.client.post(path, json.dumps(prof), content_type="application/json", If_Match=etag, Authorization=self.auth,  X_Experience_API_Version="1.0.0")
        self.assertEqual(post.status_code, 204)

        get = self.client.get(path, Authorization=self.auth,  X_Experience_API_Version="1.0.0")
        self.assertEqual(get.status_code, 200)
        ret_json = ast.literal_eval(get.content)
        self.assertEqual(ret_json['added'], prof['added'])
        self.assertEqual(ret_json['test'], "post updated profile")
        self.assertEqual(ret_json['obj']['activity'], prof['obj']['activity'])
        self.assertEqual(ret_json['obj']['new'], prof['obj']['new'])
        self.assertEqual(get.get('etag'), '"%s"' % hashlib.sha1(get.content).hexdigest())

        self.client.delete(path, Authorization=self.auth,  X_Experience_API_Version="1.0.0")

    def test_post_and_put_profile(self):
        params = {"profileId": "prof:test_post_and_put_profile", "activityId": "act:test.post.put.prof"}
        path = '%s?%s' % (reverse(views.activity_profile), urllib.urlencode(params))
        prof = {"test":"post and put profile","obj":{"activity":"act:test.post.put.prof"}}
        
        post = self.client.post(path, json.dumps(prof), content_type="application/json", Authorization=self.auth,  X_Experience_API_Version="1.0.0")
        self.assertEqual(post.status_code, 204)
        
        get = self.client.get(path, Authorization=self.auth,  X_Experience_API_Version="1.0.0")
        self.assertEqual(get.status_code, 200)
        self.assertEqual(ast.literal_eval(get.content), prof)
        self.assertEqual(get.get('etag'), '"%s"' % hashlib.sha1(get.content).hexdigest())

        params = {"profileId": "prof:test_post_and_put_profile", "activityId": "act:test.post.put.prof"}
        path = '%s?%s' % (reverse(views.activity_profile), urllib.urlencode(params))
        prof = {"wipe":"new data"}
        thehash = get.get('etag')
        
        put = self.client.put(path, json.dumps(prof), content_type="application/json", If_Match=thehash, Authorization=self.auth,  X_Experience_API_Version="1.0.0")
        self.assertEqual(put.status_code, 204)
        
        get = self.client.get(path, Authorization=self.auth,  X_Experience_API_Version="1.0.0")
        self.assertEqual(get.status_code, 200)
        self.assertEqual(ast.literal_eval(get.content), prof)
        etag = '"%s"' % hashlib.sha1(get.content).hexdigest()
        self.assertEqual(get.get('etag'), etag)

        params = {"profileId": "prof:test_post_and_put_profile", "activityId": "act:test.post.put.prof"}
        path = '%s?%s' % (reverse(views.activity_profile), urllib.urlencode(params))
        prof = {"test":"post updated profile","obj":{"activity":"act:test.post.update.prof_changed", "new":"thing"}, "added":"yes"}
        
        post = self.client.post(path, json.dumps(prof), content_type="application/json", Authorization=self.auth,  X_Experience_API_Version="1.0.0")
        self.assertEqual(post.status_code, 409)

        post = self.client.post(path, json.dumps(prof), content_type="application/json", If_Match=etag, Authorization=self.auth,  X_Experience_API_Version="1.0.0")
        self.assertEqual(post.status_code, 204)

        get = self.client.get(path, Authorization=self.auth,  X_Experience_API_Version="1.0.0")
        self.assertEqual(get.status_code, 200)
        ret_json = ast.literal_eval(get.content)
        self.assertEqual(ret_json['wipe'], "new data")
        self.assertEqual(ret_json['added'], prof['added'])
        self.assertEqual(ret_json['test'], prof['test'])
        self.assertEqual(ret_json['obj']['activity'], prof['obj']['activity'])
        self.assertEqual(ret_json['obj']['new'], prof['obj']['new'])
        self.assertEqual(get.get('etag'), '"%s"' % hashlib.sha1(get.content).hexdigest())

        self.client.delete(path, Authorization=self.auth,  X_Experience_API_Version="1.0.0")

    def test_current_tetris(self):
        params = {"profileId":"profile:highscores","activityId":"act:adlnet.gov/JsTetris_TCAPI"}
        path = '%s?%s' % (reverse(views.activity_profile), urllib.urlencode(params))
        
        put = self.client.put(path, '[{"actor":{"name":"tom","mbox":"mailto:tom@tom.com"},"score":802335,"date":"2013-07-26T13:42:13.465Z"},{"actor":{"name":"tom","mbox":"mailto:tom@tom.com"},"score":159482,"date":"2013-07-26T13:49:14.011Z"},{"actor":{"name":"lou","mbox":"mailto:l@l.com"},"score":86690,"date":"2013-07-26T13:27:29.083Z"},{"actor":{"name":"tom","mbox":"mailto:tom@tom.com"},"score":15504,"date":"2013-07-26T13:27:30.763Z"},{"actor":{"name":"tom","mbox":"mailto:tom@tom.com"},"score":1982,"date":"2013-07-26T13:29:46.067Z"},{"actor":{"name":"unknown","mbox":"mailto:unknown@example.com"},"score":348,"date":"2013-07-26T13:51:08.043Z"}]', content_type="application/json", Authorization=self.auth, X_Experience_API_Version="1.0.0")
        self.assertEqual(put.status_code, 204)
        
        theget = self.client.get(path, Authorization=self.auth, X_Experience_API_Version="1.0")
        self.assertEqual(theget['ETag'], '"d4827d99a5cc3510d3847baa341ba5a3b477fdfc"')
