from django.test import TestCase
from django.core.urlresolvers import reverse
from lrs import views
import datetime
from django.utils.timezone import utc
import hashlib
import urllib
import base64
import json
import ast

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
        print "\n%s" % __name__

    def setUp(self):
        self.username = "tester"
        self.email = "test@tester.com"
        self.password = "test"
        self.auth = "Basic %s" % base64.b64encode("%s:%s" % (self.username, self.password))
        form = {'username':self.username, 'email': self.email,'password':self.password,'password2':self.password}
        response = self.client.post(reverse(views.register),form, X_Experience_API_Version="1.0.0")
        
        self.testparams1 = {"profileId": self.testprofileId1, "agent": self.testagent}
        path = '%s?%s' % (reverse(views.agent_profile), urllib.urlencode(self.testparams1))
        self.testprofile1 = {"test":"put profile 1","obj":{"agent":"test"}}
        self.put1 = self.client.put(path, self.testprofile1, content_type=self.content_type, Authorization=self.auth, X_Experience_API_Version="1.0.0")

        self.testparams2 = {"profileId": self.testprofileId2, "agent": self.testagent}
        path = '%s?%s' % (reverse(views.agent_profile), urllib.urlencode(self.testparams2))
        self.testprofile2 = {"test":"put profile 2","obj":{"agent":"test"}}
        self.put2 = self.client.put(path, self.testprofile2, content_type=self.content_type, Authorization=self.auth, X_Experience_API_Version="1.0.0")

        self.testparams3 = {"profileId": self.testprofileId3, "agent": self.testagent}
        path = '%s?%s' % (reverse(views.agent_profile), urllib.urlencode(self.testparams3))
        self.testprofile3 = {"test":"put profile 3","obj":{"agent":"test"}}
        self.put3 = self.client.put(path, self.testprofile3, content_type=self.content_type, Authorization=self.auth, X_Experience_API_Version="1.0.0")

        self.testparams4 = {"profileId": self.otherprofileId1, "agent": self.otheragent}
        path = '%s?%s' % (reverse(views.agent_profile), urllib.urlencode(self.testparams4))
        self.otherprofile1 = {"test":"put profile 1","obj":{"agent":"other"}}
        self.put4 = self.client.put(path, self.otherprofile1, content_type=self.content_type, Authorization=self.auth, X_Experience_API_Version="1.0.0")

    def tearDown(self):
        self.client.delete(reverse(views.agent_profile), self.testparams1, Authorization=self.auth, X_Experience_API_Version="1.0.0")
        self.client.delete(reverse(views.agent_profile), self.testparams2, Authorization=self.auth, X_Experience_API_Version="1.0.0")
        self.client.delete(reverse(views.agent_profile), self.testparams3, Authorization=self.auth, X_Experience_API_Version="1.0.0")
        self.client.delete(reverse(views.agent_profile), self.testparams4, Authorization=self.auth, X_Experience_API_Version="1.0.0")

    def test_get_agent_not_found(self):
        a = '{"mbox":["mailto:notfound@example.com"]}'
        p = 'http://agent.not.found'
        param = {"profileId": p, "agent": a}
        r = self.client.get(reverse(views.agent_profile), param, Authorization=self.auth, X_Experience_API_Version="1.0.0")
        self.assertEqual(r.status_code, 404)

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
        path = '%s?%s' % (reverse(views.agent_profile), urllib.urlencode(self.testparams1))
        profile = {"test":"error - trying to put new profile w/o etag header","obj":{"agent":"test"}}
        response = self.client.put(path, profile, content_type=self.content_type, Authorization=self.auth, X_Experience_API_Version="1.0.0")

        self.assertEqual(response.status_code, 409)
        self.assertIn('If-Match and If-None-Match headers were missing', response.content)
        
        r = self.client.get(reverse(views.agent_profile), self.testparams1, Authorization=self.auth, X_Experience_API_Version="1.0.0")
        self.assertEqual(r.status_code, 200)
        robj = ast.literal_eval(r.content)
        self.assertEqual(robj['test'], self.testprofile1['test'])
        self.assertEqual(robj['obj']['agent'], self.testprofile1['obj']['agent'])

    def test_put_etag_right_on_change(self):
        path = '%s?%s' % (reverse(views.agent_profile), urllib.urlencode(self.testparams1))
        profile = {"test":"good - trying to put new profile w/ etag header","obj":{"agent":"test"}}
        thehash = '"%s"' % hashlib.sha1('%s' % self.testprofile1).hexdigest()
        response = self.client.put(path, profile, content_type=self.content_type, If_Match=thehash, Authorization=self.auth, X_Experience_API_Version="1.0.0")
        self.assertEqual(response.status_code, 204)
        self.assertEqual(response.content, '')

        r = self.client.get(reverse(views.agent_profile), self.testparams1, Authorization=self.auth, X_Experience_API_Version="1.0.0")
        self.assertEqual(r.status_code, 200)
        robj = ast.literal_eval(r.content)
        self.assertEqual(robj['test'], profile['test'])
        self.assertEqual(robj['obj']['agent'], profile['obj']['agent'])

    def test_put_etag_wrong_on_change(self):
        path = '%s?%s' % (reverse(views.agent_profile), urllib.urlencode(self.testparams1))
        profile = {"test":"error - trying to put new profile w/ wrong etag value","obj":{"agent":"test"}}
        thehash = '"%s"' % hashlib.sha1('%s' % 'wrong hash').hexdigest()
        response = self.client.put(path, profile, content_type=self.content_type, If_Match=thehash, Authorization=self.auth, X_Experience_API_Version="1.0.0")
        self.assertEqual(response.status_code, 412)
        self.assertIn('No resources matched', response.content)

        r = self.client.get(reverse(views.agent_profile), self.testparams1, Authorization=self.auth, X_Experience_API_Version="1.0.0")
        self.assertEqual(r.status_code, 200)
        robj = ast.literal_eval(r.content)
        self.assertEqual(robj['test'], self.testprofile1['test'])
        self.assertEqual(robj['obj']['agent'], self.testprofile1['obj']['agent'])

    def test_put_etag_if_none_match_good(self):
        params = {"profileId": 'http://etag.nomatch.good', "agent": self.testagent}
        path = '%s?%s' % (reverse(views.agent_profile), urllib.urlencode(params))
        profile = {"test":"good - trying to put new profile w/ if none match etag header","obj":{"agent":"test"}}
        response = self.client.put(path, profile, content_type=self.content_type, If_None_Match='*', Authorization=self.auth, X_Experience_API_Version="1.0.0")

        self.assertEqual(response.status_code, 204)
        self.assertEqual(response.content, '')

        r = self.client.get(reverse(views.agent_profile), params, Authorization=self.auth, X_Experience_API_Version="1.0.0")
        self.assertEqual(r.status_code, 200)
        robj = ast.literal_eval(r.content)
        self.assertEqual(robj['test'], profile['test'])
        self.assertEqual(robj['obj']['agent'], profile['obj']['agent'])

        r = self.client.delete(reverse(views.agent_profile), params, Authorization=self.auth, X_Experience_API_Version="1.0.0")

    def test_put_etag_if_none_match_bad(self):
        path = '%s?%s' % (reverse(views.agent_profile), urllib.urlencode(self.testparams1))
        profile = {"test":"error - trying to put new profile w/ if none match etag but one exists","obj":{"agent":"test"}}
        response = self.client.put(path, profile, content_type=self.content_type, If_None_Match='*', Authorization=self.auth, X_Experience_API_Version="1.0.0")

        self.assertEqual(response.status_code, 412)
        self.assertEqual(response.content, 'Resource detected')

        r = self.client.get(reverse(views.agent_profile), self.testparams1, Authorization=self.auth, X_Experience_API_Version="1.0.0")
        self.assertEqual(r.status_code, 200)
        robj = ast.literal_eval(r.content)
        self.assertEqual(robj['test'], self.testprofile1['test'])
        self.assertEqual(robj['obj']['agent'], self.testprofile1['obj']['agent'])

    def test_get(self):
        r = self.client.get(reverse(views.agent_profile), self.testparams1, Authorization=self.auth, X_Experience_API_Version="1.0.0")
        self.assertEqual(r.status_code, 200)
        
        robj = ast.literal_eval(r.content)
        self.assertEqual(robj['test'], self.testprofile1['test'])
        self.assertEqual(robj['obj']['agent'], self.testprofile1['obj']['agent'])
        self.assertEqual(r['etag'], '"%s"' % hashlib.sha1('%s' % self.testprofile1).hexdigest())

        r2 = self.client.get(reverse(views.agent_profile), self.testparams2, Authorization=self.auth, X_Experience_API_Version="1.0.0")
        self.assertEqual(r2.status_code, 200)
        robj2 = ast.literal_eval(r2.content)
        self.assertEqual(robj2['test'], self.testprofile2['test'])
        self.assertEqual(robj2['obj']['agent'], self.testprofile2['obj']['agent'])
        self.assertEqual(r2['etag'], '"%s"' % hashlib.sha1('%s' % self.testprofile2).hexdigest())
        
        r3 = self.client.get(reverse(views.agent_profile), self.testparams3, Authorization=self.auth, X_Experience_API_Version="1.0.0")
        self.assertEqual(r3.status_code, 200)
        robj3 = ast.literal_eval(r3.content)
        self.assertEqual(robj3['test'], self.testprofile3['test'])
        self.assertEqual(robj3['obj']['agent'], self.testprofile3['obj']['agent'])
        self.assertEqual(r3['etag'], '"%s"' % hashlib.sha1('%s' % self.testprofile3).hexdigest())

        r4 = self.client.get(reverse(views.agent_profile), self.testparams4, Authorization=self.auth, X_Experience_API_Version="1.0.0")
        self.assertEqual(r4.status_code, 200)
        robj4 = ast.literal_eval(r4.content)
        self.assertEqual(robj4['test'], self.otherprofile1['test'])
        self.assertEqual(robj4['obj']['agent'], self.otherprofile1['obj']['agent'])
        self.assertEqual(r4['etag'], '"%s"' % hashlib.sha1('%s' % self.otherprofile1).hexdigest())

    def test_get_no_params(self):
        r = self.client.get(reverse(views.agent_profile), Authorization=self.auth, X_Experience_API_Version="1.0.0")
        self.assertEqual(r.status_code, 400)
        self.assertIn('agent parameter missing', r.content)
    
    def test_get_no_agent(self):
        params = {"profileId": self.testprofileId1}
        r = self.client.get(reverse(views.agent_profile), params, Authorization=self.auth, X_Experience_API_Version="1.0.0")
        self.assertEqual(r.status_code, 400)
        self.assertIn('agent parameter missing', r.content)

    def test_get_no_profileId(self):
        params = {"agent": self.testagent}
        r = self.client.get(reverse(views.agent_profile), params, Authorization=self.auth, X_Experience_API_Version="1.0.0")
        self.assertEqual(r.status_code, 200)
    
    def test_delete(self):
        prof_id = "http://deleteme"
        params = {"profileId": prof_id, "agent": self.testagent}
        path = '%s?%s' % (reverse(views.agent_profile), urllib.urlencode(params))
        profile = {"test":"delete profile","obj":{"agent":"test"}}
        response = self.client.put(path, profile, content_type=self.content_type, Authorization=self.auth, X_Experience_API_Version="1.0.0")
        
        r = self.client.get(reverse(views.agent_profile), params, Authorization=self.auth, X_Experience_API_Version="1.0.0")
        self.assertEqual(r.status_code, 200)
        robj = ast.literal_eval(r.content)
        self.assertEqual(robj['test'], profile['test'])
        self.assertEqual(robj['obj']['agent'], profile['obj']['agent'])

        r = self.client.delete(reverse(views.agent_profile), params, Authorization=self.auth, X_Experience_API_Version="1.0.0")
        self.assertEqual(r.status_code, 204)

        r = self.client.get(reverse(views.agent_profile), params, Authorization=self.auth, X_Experience_API_Version="1.0.0")
        self.assertEqual(r.status_code, 404)

    def test_get_agent_since(self):
        prof_id = "http://oldprofile/time"
        updated =  datetime.datetime(2012, 6, 12, 12, 00).replace(tzinfo=utc)

        params = {"profileId": prof_id, "agent": self.testagent}
        path = '%s?%s' % (reverse(views.agent_profile), urllib.urlencode(params))

        profile = {"test1":"agent profile since time: %s" % updated,"obj":{"agent":"test"}}
        response = self.client.put(path, profile, content_type=self.content_type, updated=updated.isoformat(), Authorization=self.auth, X_Experience_API_Version="1.0.0")

        r = self.client.get(reverse(views.agent_profile), params, Authorization=self.auth, X_Experience_API_Version="1.0.0")
        self.assertEqual(r.status_code, 200)
        robj = ast.literal_eval(r.content)
        self.assertEqual(robj['test1'], profile['test1'])
        self.assertEqual(robj['obj']['agent'], profile['obj']['agent'])

        since = datetime.datetime(2012, 7, 1, 12, 00).replace(tzinfo=utc)
        params2 = {"agent": self.testagent, "since":since.isoformat()}
        r2 = self.client.get(reverse(views.agent_profile), params2, Authorization=self.auth, X_Experience_API_Version="1.0.0")
        self.assertNotIn(prof_id, r2.content)

        self.client.delete(reverse(views.agent_profile), params, Authorization=self.auth, X_Experience_API_Version="1.0.0")

    def test_get_agent_since_tz(self):
        prof_id = "http://oldprofile/time"
        updated =  datetime.datetime(2012, 6, 12, 12, 00).replace(tzinfo=utc)

        params = {"profileId": prof_id, "agent": self.testagent}
        path = '%s?%s' % (reverse(views.agent_profile), urllib.urlencode(params))

        profile = {"test2":"agent profile since time: %s" % updated,"obj":{"agent":"test"}}
        response = self.client.put(path, profile, content_type=self.content_type, updated=updated.isoformat(), Authorization=self.auth, X_Experience_API_Version="1.0.0")

        r = self.client.get(reverse(views.agent_profile), params, Authorization=self.auth, X_Experience_API_Version="1.0.0")
        self.assertEqual(r.status_code, 200)
        robj = ast.literal_eval(r.content)
        self.assertEqual(robj['test2'], profile['test2'])
        self.assertEqual(robj['obj']['agent'], profile['obj']['agent'])

        prof_id2 = "http://newprofile/timezone"
        updated2 =  "2012-7-1T08:30:00-04:00"

        params2 = {"profileId": prof_id2, "agent": self.testagent}
        path2 = '%s?%s' % (reverse(views.agent_profile), urllib.urlencode(params2))

        profile2 = {"test3":"agent profile since time: %s" % updated2,"obj":{"agent":"test"}}
        response = self.client.put(path2, profile2, content_type=self.content_type, updated=updated2, Authorization=self.auth, X_Experience_API_Version="1.0.0")

        r2 = self.client.get(reverse(views.agent_profile), params2, Authorization=self.auth, X_Experience_API_Version="1.0.0")
        self.assertEqual(r2.status_code, 200)
        robj2 = ast.literal_eval(r2.content)
        self.assertEqual(robj2['test3'], profile2['test3'])
        self.assertEqual(robj2['obj']['agent'], profile2['obj']['agent'])

        since = datetime.datetime(2012, 7, 1, 12, 00).replace(tzinfo=utc)

        par = {"agent": self.testagent, "since":since.isoformat()}
        r = self.client.get(reverse(views.agent_profile), par, Authorization=self.auth, X_Experience_API_Version="1.0.0")

        self.assertNotIn(prof_id, r.content)
        self.assertIn(prof_id2, r.content)

        self.client.delete(reverse(views.agent_profile), params, Authorization=self.auth, X_Experience_API_Version="1.0.0")
        self.client.delete(reverse(views.agent_profile), params2, Authorization=self.auth, X_Experience_API_Version="1.0.0")

    def test_post_put_delete(self):
        prof_id = "http://deleteme.too"
        path = '%s?%s' % (reverse(views.agent_profile), urllib.urlencode({"method":"PUT"}))
        content = {"test":"delete profile","obj":{"actor":"test", "testcase":"ie cors post for put and delete"}}
        thedata = "profileId=%s&agent=%s&content=%s&Authorization=%s&Content-Type=application/json&X-Experience-API-Version=1.0.0" % (prof_id, self.testagent, content, self.auth)
        response = self.client.post(path, thedata, content_type="application/x-www-form-urlencoded")
        self.assertEqual(response.status_code, 204)
        r = self.client.get(reverse(views.agent_profile), {"profileId": prof_id, "agent": self.testagent}, Authorization=self.auth, X_Experience_API_Version="1.0.0")
        self.assertEqual(r.status_code, 200)
        import ast
        c = ast.literal_eval(r.content)
        self.assertEqual(c['test'], content['test'])
 
        thedata = "profileId=%s&agent=%s&Authorization=%s&X-Experience-API-Version=1.0" % (prof_id, self.testagent, self.auth)
        path = '%s?%s' % (reverse(views.agent_profile), urllib.urlencode({"method":"DELETE"}))
        r = self.client.post(path, thedata, content_type="application/x-www-form-urlencoded", Authorization=self.auth, X_Experience_API_Version="1.0.0")
        self.assertEqual(r.status_code, 204)

        r = self.client.get(reverse(views.agent_profile), {"profileId": prof_id, "agent": self.testagent}, Authorization=self.auth, X_Experience_API_Version="1.0.0")
        self.assertEqual(r.status_code, 404)

    def test_group_as_agent(self):
        ot = "Group"
        name = "the group APT"
        mbox = "mailto:the.groupAPT@example.com"
        members = [{"name":"agentA","mbox":"mailto:agentA@example.com"},
                    {"name":"agentB","mbox":"mailto:agentB@example.com"}]
        testagent = json.dumps({"objectType":ot, "name":name, "mbox":mbox,"member":members})
        testprofileId = "http://profile.test.id/group.as.agent/"
        testparams1 = {"profileId": testprofileId, "agent": testagent}
        path = '%s?%s' % (reverse(views.agent_profile), urllib.urlencode(testparams1))
        testprofile = {"test":"put profile - group as agent","obj":{"agent":"group"}}
        put1 = self.client.put(path, testprofile, content_type=self.content_type, Authorization=self.auth, X_Experience_API_Version="1.0.0")

        self.assertEqual(put1.status_code, 204)

        getr = self.client.get(reverse(views.agent_profile), testparams1, Authorization=self.auth, X_Experience_API_Version="1.0.0")
        self.assertEqual(getr.status_code, 200)
        robj = ast.literal_eval(getr.content)
        self.assertEqual(robj['test'], testprofile['test'])
        self.assertEqual(robj['obj']['agent'], testprofile['obj']['agent'])

        self.client.delete(reverse(views.agent_profile), testparams1, Authorization=self.auth, X_Experience_API_Version="1.0.0")

    def test_post_new_profile(self):
        params = {"profileId": "prof:test_post_new_profile", "agent": self.testagent}
        path = '%s?%s' % (reverse(views.agent_profile), urllib.urlencode(params))
        prof = {"test":"post new profile","obj":{"agent":"mailto:test@example.com"}}
        
        post = self.client.post(path, prof, content_type="application/json", Authorization=self.auth,  X_Experience_API_Version="1.0.0")
        self.assertEqual(post.status_code, 204)
        
        get = self.client.get(path, Authorization=self.auth,  X_Experience_API_Version="1.0.0")
        self.assertEqual(get.status_code, 200)
        self.assertEqual(ast.literal_eval(get.content), prof)
        self.assertEqual(get.get('etag'), '"%s"' % hashlib.sha1(get.content).hexdigest())
        self.client.delete(path, Authorization=self.auth,  X_Experience_API_Version="1.0.0")

    def test_post_update_profile(self):
        params = {"profileId": "prof:test_post_update_profile", "agent": self.testagent}
        path = '%s?%s' % (reverse(views.agent_profile), urllib.urlencode(params))
        prof = {"test":"post updated profile","obj":{"agent":"mailto:test@example.com"}}
        
        post = self.client.post(path, prof, content_type="application/json", Authorization=self.auth,  X_Experience_API_Version="1.0.0")
        self.assertEqual(post.status_code, 204)
        
        get = self.client.get(path, Authorization=self.auth,  X_Experience_API_Version="1.0.0")
        self.assertEqual(get.status_code, 200)
        self.assertEqual(ast.literal_eval(get.content), prof)
        etag = '"%s"' % hashlib.sha1(get.content).hexdigest()
        self.assertEqual(get.get('etag'), etag)

        params = {"profileId": "prof:test_post_update_profile", "agent": self.testagent}
        path = '%s?%s' % (reverse(views.agent_profile), urllib.urlencode(params))
        prof = {"obj":{"agent":"mailto:test@example.com", "new":"thing"}, "added":"yes"}

        post = self.client.post(path, prof, content_type="application/json", Authorization=self.auth,  X_Experience_API_Version="1.0.0")
        self.assertEqual(post.status_code, 409)
        
        post = self.client.post(path, prof, content_type="application/json",If_Match=etag, Authorization=self.auth,  X_Experience_API_Version="1.0.0")
        self.assertEqual(post.status_code, 204)

        get = self.client.get(path, Authorization=self.auth,  X_Experience_API_Version="1.0.0")
        self.assertEqual(get.status_code, 200)
        ret_json = ast.literal_eval(get.content)
        self.assertEqual(ret_json['added'], prof['added'])
        self.assertEqual(ret_json['test'], "post updated profile")
        self.assertEqual(ret_json['obj']['agent'], prof['obj']['agent'])
        self.assertEqual(ret_json['obj']['new'], prof['obj']['new'])
        self.assertEqual(get.get('etag'), '"%s"' % hashlib.sha1(get.content).hexdigest())

        self.client.delete(path, Authorization=self.auth,  X_Experience_API_Version="1.0.0")

    def test_post_and_put_profile(self):
        params = {"profileId": "prof:test_post_and_put_profile", "agent": self.testagent}
        path = '%s?%s' % (reverse(views.agent_profile), urllib.urlencode(params))
        prof = {"test":"post and put profile","obj":{"agent":"mailto:test@example.com"}}
        
        post = self.client.post(path, prof, content_type="application/json", Authorization=self.auth,  X_Experience_API_Version="1.0.0")
        self.assertEqual(post.status_code, 204)
        
        get = self.client.get(path, Authorization=self.auth,  X_Experience_API_Version="1.0.0")
        self.assertEqual(get.status_code, 200)
        self.assertEqual(ast.literal_eval(get.content), prof)
        self.assertEqual(get.get('etag'), '"%s"' % hashlib.sha1(get.content).hexdigest())

        params = {"profileId": "prof:test_post_and_put_profile", "agent": self.testagent}
        path = '%s?%s' % (reverse(views.agent_profile), urllib.urlencode(params))
        prof = {"wipe":"new data"}
        thehash = get.get('etag')
        
        put = self.client.put(path, prof, content_type="application/json", If_Match=thehash, Authorization=self.auth,  X_Experience_API_Version="1.0.0")
        self.assertEqual(put.status_code, 204)
        
        get = self.client.get(path, Authorization=self.auth,  X_Experience_API_Version="1.0.0")
        self.assertEqual(get.status_code, 200)
        self.assertEqual(ast.literal_eval(get.content), prof)
        etag = '"%s"' % hashlib.sha1(get.content).hexdigest()
        self.assertEqual(get.get('etag'), etag)

        params = {"profileId": "prof:test_post_and_put_profile", "agent": self.testagent}
        path = '%s?%s' % (reverse(views.agent_profile), urllib.urlencode(params))
        prof = {"test":"post updated profile","obj":{"agent":"mailto:test@example.com", "new":"thing"}, "added":"yes"}
        
        post = self.client.post(path, prof, content_type="application/json", Authorization=self.auth,  X_Experience_API_Version="1.0.0")
        self.assertEqual(post.status_code, 409)

        post = self.client.post(path, prof, content_type="application/json", If_Match=etag, Authorization=self.auth,  X_Experience_API_Version="1.0.0")
        self.assertEqual(post.status_code, 204)

        get = self.client.get(path, Authorization=self.auth,  X_Experience_API_Version="1.0.0")
        self.assertEqual(get.status_code, 200)
        ret_json = ast.literal_eval(get.content)
        self.assertEqual(ret_json['wipe'], "new data")
        self.assertEqual(ret_json['added'], prof['added'])
        self.assertEqual(ret_json['test'], prof['test'])
        self.assertEqual(ret_json['obj']['agent'], prof['obj']['agent'])
        self.assertEqual(ret_json['obj']['new'], prof['obj']['new'])
        self.assertEqual(get.get('etag'), '"%s"' % hashlib.sha1(get.content).hexdigest())

        self.client.delete(path, Authorization=self.auth,  X_Experience_API_Version="1.0.0")
