from django.test import TestCase
from django.test.utils import setup_test_environment
from django.core.urlresolvers import reverse
from lrs import models, views
import json
import time
import datetime
from django.utils.timezone import utc
import hashlib
from unittest import TestCase as py_tc
from django.core.exceptions import ValidationError, ObjectDoesNotExist
import urllib
from objectContainer import Actor, Activity

home = 'http://localhost:8000/TCAPI/'

class StatementsTest(TestCase):
    def test_post_but_really_get(self):
        response = self.client.post(reverse(views.statements), {"verb":"created","object": {"id":"http://example.com/test_post_but_really_get"}},content_type='application/x-www-form-urlencoded')
        #print "\nTesting post with type to url form encoded\n %s \n-----done----" % response.content
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'weird POST/GET')
        
    def test_post_but_really_get_no_type(self):
        response = self.client.post(reverse(views.statements), {"verb":"created","object": {"id":"http://example.com/test_post_but_really_get_no_type"}})
        #print "\nTesting post with no content type\n %s \n-----done----" % response.content
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'weird POST/GET')
    
        
    def test_post_but_really_get_with_no_valid_params(self):
        response = self.client.post(reverse(views.statements), {"feet":"yes","hands": {"id":"http://example.com/test_post_but_really_get"}},content_type='application/x-www-form-urlencoded')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Error')
        self.assertContains(response, 'could not find a valid parameter')
    

    def test_post(self):
        response = self.client.post(reverse(views.statements), {"verb":"created","object": {"id":"http://example.com/test_post"}},content_type='application/json')
        #print "\nTesting post with json type\n %s \n-----done----" % response.content
        self.assertEqual(response.status_code, 200)
        # failing.. worry about when implementing for real: self.assertContains(response, 'method = POST')
        
    def test_get(self):
        response = self.client.get(reverse(views.statements), {'statementId':'stmtid'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'stmtid')
        
    def test_get_no_statementid(self):
        response = self.client.get(reverse(views.statements))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Error')
        self.assertContains(response, 'statementId parameter is missing')

class ActivityStateTest(TestCase):
    url = reverse(views.activity_state)
    testactor = '{"name":["test"],"mbox":["mailto:test@example.com"]}'
    otheractor = '{"name":["other"],"mbox":["mailto:other@example.com"]}'
    activityId = "http://www.iana.org/domains/example/"
    activityId2 = "http://www.google.com"
    stateId = "the_state_id"
    stateId2 = "state_id_2"
    stateId3 = "third_state_id"
    stateId4 = "4th.id"
    registrationId = "some_sort_of_reg_id"
    content_type = "application/json"

    def setUp(self):
        self.activity = models.activity(activity_id=self.activityId)
        self.activity.save()

        self.activity2 = models.activity(activity_id=self.activityId2)
        self.activity2.save()

        self.testparams1 = {"stateId": self.stateId, "activityId": self.activityId, "actor": self.testactor}
        path = '%s?%s' % (self.url, urllib.urlencode(self.testparams1))
        self.teststate1 = {"test":"put activity state 1","obj":{"actor":"test"}}
        self.put1 = self.client.put(path, self.teststate1, content_type=self.content_type)

        self.testparams2 = {"stateId": self.stateId2, "activityId": self.activityId, "actor": self.testactor}
        path = '%s?%s' % (self.url, urllib.urlencode(self.testparams2))
        self.teststate2 = {"test":"put activity state 2","obj":{"actor":"test"}}
        self.put2 = self.client.put(path, self.teststate2, content_type=self.content_type)

        self.testparams3 = {"stateId": self.stateId3, "activityId": self.activityId2, "actor": self.testactor}
        path = '%s?%s' % (self.url, urllib.urlencode(self.testparams3))
        self.teststate3 = {"test":"put activity state 3","obj":{"actor":"test"}}
        self.put3 = self.client.put(path, self.teststate3, content_type=self.content_type)

        self.testparams4 = {"stateId": self.stateId4, "activityId": self.activityId2, "actor": self.otheractor}
        path = '%s?%s' % (self.url, urllib.urlencode(self.testparams4))
        self.teststate4 = {"test":"put activity state 4","obj":{"actor":"other"}}
        self.put4 = self.client.put(path, self.teststate4, content_type=self.content_type)

    def tearDown(self):
        self.client.delete(self.url, self.testparams1)
        self.client.delete(self.url, self.testparams2)
        self.client.delete(self.url, self.testparams3)
        self.client.delete(self.url, self.testparams4)

    def test_put(self):
        self.assertEqual(self.put1.status_code, 204)
        self.assertEqual(self.put1.content, '')

        self.assertEqual(self.put2.status_code, 204)
        self.assertEqual(self.put2.content, '')

        self.assertEqual(self.put3.status_code, 204)
        self.assertEqual(self.put3.content, '')

        self.assertEqual(self.put4.status_code, 204)
        self.assertEqual(self.put4.content, '')
     
    def test_put_with_registrationId(self):
        testparamsregid = {"registrationId": self.registrationId, "stateId": self.stateId, "activityId": self.activityId, "actor": self.testactor}
        path = '%s?%s' % (self.url, urllib.urlencode(testparamsregid))
        teststateregid = {"test":"put activity state w/ registrationId","obj":{"actor":"test"}}
        put1 = self.client.put(path, teststateregid, content_type=self.content_type)

        self.assertEqual(put1.status_code, 204)
        self.assertEqual(put1.content, '')
        # also testing get w/ registration id
        r = self.client.get(self.url, testparamsregid)
        self.assertEqual(r.status_code, 200)
        state1_str = '%s' % teststateregid
        self.assertEqual(r.content, state1_str)
        self.assertEqual(r['etag'], '"%s"' % hashlib.sha1(state1_str).hexdigest())
        # and tests delete w/ registration id
        del_r = self.client.delete(self.url, testparamsregid)
        self.assertEqual(del_r.status_code, 204)

    def test_put_etag_conflict_if_none_match(self):
        teststateetaginm = {"test":"etag conflict - if none match *","obj":{"actor":"test"}}
        path = '%s?%s' % (self.url, urllib.urlencode(self.testparams1))
        r = self.client.put(path, teststateetaginm, content_type=self.content_type, if_none_match='*')
        self.assertEqual(r.status_code, 412)
        self.assertEqual(r.content, 'Resource detected')

        r = self.client.get(self.url, self.testparams1)
        self.assertEqual(r.status_code, 200)
        state1_str = '%s' % self.teststate1
        self.assertEqual(r.content, state1_str)
        self.assertEqual(r['etag'], '"%s"' % hashlib.sha1(state1_str).hexdigest())

    def test_put_etag_conflict_if_match(self):
        teststateetagim = {"test":"etag conflict - if match wrong hash","obj":{"actor":"test"}}
        new_etag = '"%s"' % hashlib.sha1('wrong etag value').hexdigest()
        path = '%s?%s' % (self.url, urllib.urlencode(self.testparams1))
        r = self.client.put(path, teststateetagim, content_type=self.content_type, if_match=new_etag)
        self.assertEqual(r.status_code, 412)
        self.assertIn('No resources matched', r.content)

        r = self.client.get(self.url, self.testparams1)
        self.assertEqual(r.status_code, 200)
        state1_str = '%s' % self.teststate1
        self.assertEqual(r.content, state1_str)
        self.assertEqual(r['etag'], '"%s"' % hashlib.sha1(state1_str).hexdigest())

    def test_put_etag_no_conflict_if_match(self):
        teststateetagim = {"test":"etag no conflict - if match good hash","obj":{"actor":"test"}}
        new_etag = '"%s"' % hashlib.sha1('%s' % self.teststate1).hexdigest()
        path = '%s?%s' % (self.url, urllib.urlencode(self.testparams1))
        r = self.client.put(path, teststateetagim, content_type=self.content_type, if_match=new_etag)
        self.assertEqual(r.status_code, 204)
        self.assertEqual(r.content, '')

        r = self.client.get(self.url, self.testparams1)
        self.assertEqual(r.status_code, 200)
        state1_str = '%s' % teststateetagim
        self.assertEqual(r.content, state1_str)
        self.assertEqual(r['etag'], '"%s"' % hashlib.sha1(state1_str).hexdigest())    

    def test_put_without_activityid(self):
        testparamsbad = {"stateId": "bad_state", "actor": self.testactor}
        path = '%s?%s' % (self.url, urllib.urlencode(testparamsbad))
        teststatebad = {"test":"put activity state BAD no activity id","obj":{"actor":"test"}}
        put1 = self.client.put(path, teststatebad, content_type=self.content_type)

        self.assertEqual(put1.status_code, 400)
        self.assertIn('activityId parameter is missing', put1.content)

    
    def test_put_without_actor(self):
        testparamsbad = {"stateId": "bad_state", "activityId": self.activityId}
        path = '%s?%s' % (self.url, urllib.urlencode(testparamsbad))
        teststatebad = {"test":"put activity state BAD no actor","obj":{"actor":"none"}}
        put1 = self.client.put(path, teststatebad, content_type=self.content_type)

        self.assertEqual(put1.status_code, 400)
        self.assertIn('actor parameter is missing', put1.content)

    
    def test_put_without_stateid(self):
        testparamsbad = {"activityId": self.activityId, "actor": self.testactor}
        path = '%s?%s' % (self.url, urllib.urlencode(testparamsbad))
        teststatebad = {"test":"put activity state BAD no state id","obj":{"actor":"test"}}
        put1 = self.client.put(path, teststatebad, content_type=self.content_type)

        self.assertEqual(put1.status_code, 400)
        self.assertIn('stateId parameter is missing', put1.content)

    
    def test_get(self):
        r = self.client.get(self.url, self.testparams1)
        self.assertEqual(r.status_code, 200)
        state1_str = '%s' % self.teststate1
        self.assertEqual(r.content, state1_str)
        self.assertEqual(r['etag'], '"%s"' % hashlib.sha1(state1_str).hexdigest())

        r2 = self.client.get(self.url, self.testparams2)
        self.assertEqual(r2.status_code, 200)
        state2_str = '%s' % self.teststate2
        self.assertEqual(r2.content, state2_str)
        self.assertEqual(r2['etag'], '"%s"' % hashlib.sha1(state2_str).hexdigest())
        
        r3 = self.client.get(self.url, self.testparams3)
        self.assertEqual(r3.status_code, 200)
        state3_str = '%s' % self.teststate3
        self.assertEqual(r3.content, state3_str)
        self.assertEqual(r3['etag'], '"%s"' % hashlib.sha1(state3_str).hexdigest())

        r4 = self.client.get(self.url, self.testparams4)
        self.assertEqual(r4.status_code, 200)
        state4_str = '%s' % self.teststate4
        self.assertEqual(r4.content, state4_str)
        self.assertEqual(r4['etag'], '"%s"' % hashlib.sha1(state4_str).hexdigest())

    def test_get_ids(self):
        params = {"activityId": self.activityId, "actor": self.testactor}
        r = self.client.get(self.url, params)
        self.assertEqual(r.status_code, 200)
        self.assertIn(self.stateId, r.content)
        self.assertIn(self.stateId2, r.content)
        self.assertNotIn(self.stateId3, r.content)
        self.assertNotIn(self.stateId4, r.content)
     
    def test_get_with_since(self):
        state_id = "old_state_test"
        testparamssince = {"stateId": state_id, "activityId": self.activityId, "actor": self.testactor}
        path = '%s?%s' % (self.url, urllib.urlencode(testparamssince))
        teststatesince = {"test":"get w/ since","obj":{"actor":"test"}}
        updated =  datetime.datetime(2012, 6, 12, 12, 00).replace(tzinfo=utc)
        put1 = self.client.put(path, teststatesince, content_type=self.content_type, updated=updated.isoformat())

        self.assertEqual(put1.status_code, 204)
        self.assertEqual(put1.content, '')
        
        r = self.client.get(self.url, testparamssince)
        self.assertEqual(r.status_code, 200)
        state1_str = '%s' % teststatesince
        self.assertEqual(r.content, state1_str)
        self.assertEqual(r['etag'], '"%s"' % hashlib.sha1(state1_str).hexdigest())

        since = datetime.datetime(2012, 7, 1, 12, 00).replace(tzinfo=utc)
        params2 = {"activityId": self.activityId, "actor": self.testactor, "since": since}
        r = self.client.get(self.url, params2)
        self.assertEqual(r.status_code, 200)
        self.assertIn(self.stateId, r.content)
        self.assertIn(self.stateId2, r.content)
        self.assertNotIn(state_id, r.content)
        self.assertNotIn(self.stateId3, r.content)
        self.assertNotIn(self.stateId4, r.content)

        del_r = self.client.delete(self.url, testparamssince)
        
    def test_get_with_since_and_regid(self):
        # create old state w/ no registration id
        state_id = "old_state_test_no_reg"
        testparamssince = {"stateId": state_id, "activityId": self.activityId, "actor": self.testactor}
        path = '%s?%s' % (self.url, urllib.urlencode(testparamssince))
        teststatesince = {"test":"get w/ since","obj":{"actor":"test","stateId":state_id}}
        updated =  datetime.datetime(2012, 6, 12, 12, 00).replace(tzinfo=utc)
        put1 = self.client.put(path, teststatesince, content_type=self.content_type, updated=updated.isoformat())

        self.assertEqual(put1.status_code, 204)
        self.assertEqual(put1.content, '')
        
        r = self.client.get(self.url, testparamssince)
        self.assertEqual(r.status_code, 200)
        state1_str = '%s' % teststatesince
        self.assertEqual(r.content, state1_str)
        self.assertEqual(r['etag'], '"%s"' % hashlib.sha1(state1_str).hexdigest())

        # create old state w/ registration id
        regid = 'test_since_w_regid'
        state_id2 = "old_state_test_w_reg"
        testparamssince2 = {"registrationId": regid, "activityId": self.activityId, "actor": self.testactor, "stateId":state_id2}
        path = '%s?%s' % (self.url, urllib.urlencode(testparamssince2))
        teststatesince2 = {"test":"get w/ since and registrationId","obj":{"actor":"test","stateId":state_id2}}
        put2 = self.client.put(path, teststatesince2, content_type=self.content_type, updated=updated.isoformat())

        self.assertEqual(put2.status_code, 204)
        self.assertEqual(put2.content, '')

        r2 = self.client.get(self.url, testparamssince2)
        self.assertEqual(r2.status_code, 200)
        state2_str = '%s' % teststatesince2
        self.assertEqual(r2.content, state2_str)
        self.assertEqual(r2['etag'], '"%s"' % hashlib.sha1(state2_str).hexdigest())

        # create new state w/ registration id
        state_id3 = "old_state_test_w_new_reg"
        testparamssince3 = {"registrationId": regid, "activityId": self.activityId, "actor": self.testactor, "stateId":state_id3}
        path = '%s?%s' % (self.url, urllib.urlencode(testparamssince3))
        teststatesince3 = {"test":"get w/ since and registrationId","obj":{"actor":"test","stateId":state_id3}}
        put3 = self.client.put(path, teststatesince3, content_type=self.content_type)

        self.assertEqual(put3.status_code, 204)
        self.assertEqual(put3.content, '')

        r3 = self.client.get(self.url, testparamssince3)
        self.assertEqual(r3.status_code, 200)
        state3_str = '%s' % teststatesince3
        self.assertEqual(r3.content, state3_str)
        self.assertEqual(r3['etag'], '"%s"' % hashlib.sha1(state3_str).hexdigest())

        # get no reg ids set w/o old state
        since1 = datetime.datetime(2012, 7, 1, 12, 00).replace(tzinfo=utc)
        params = {"activityId": self.activityId, "actor": self.testactor, "since": since1}
        r = self.client.get(self.url, params)
        self.assertEqual(r.status_code, 200)
        self.assertIn(self.stateId, r.content)
        self.assertIn(self.stateId2, r.content)
        self.assertNotIn(state_id, r.content)
        self.assertNotIn(self.stateId3, r.content)
        self.assertNotIn(self.stateId4, r.content)

        # get reg id set w/o old state
        since2 = datetime.datetime(2012, 7, 1, 12, 00).replace(tzinfo=utc)
        params2 = {"registrationId": regid, "activityId": self.activityId, "actor": self.testactor, "since": since2}
        r = self.client.get(self.url, params2)
        self.assertEqual(r.status_code, 200)
        self.assertIn(state_id3, r.content)
        self.assertNotIn(state_id2, r.content)
        self.assertNotIn(self.stateId, r.content)
        self.assertNotIn(self.stateId2, r.content)
        self.assertNotIn(self.stateId3, r.content)
        self.assertNotIn(self.stateId4, r.content)
        
        self.client.delete(self.url, testparamssince)
        self.client.delete(self.url, testparamssince2)
        self.client.delete(self.url, testparamssince3)

        
    def test_get_without_activityid(self):
        params = {"stateId": self.stateId, "actor": self.testactor}
        r = self.client.get(self.url, params)
        self.assertEqual(r.status_code, 400)
        self.assertIn('activityId parameter is missing', r.content)

    
    def test_get_without_actor(self):
        params = {"stateId": self.stateId, "activityId": self.activityId}
        r = self.client.get(self.url, params)
        self.assertEqual(r.status_code, 400)
        self.assertIn('actor parameter is missing', r.content)

    
    def test_delete_without_activityid(self):
        testparamsregid = {"registrationId": self.registrationId, "stateId": self.stateId, "activityId": self.activityId, "actor": self.testactor}
        path = '%s?%s' % (self.url, urllib.urlencode(testparamsregid))
        teststateregid = {"test":"delete activity state w/o activityid","obj":{"actor":"test"}}
        put1 = self.client.put(path, teststateregid, content_type=self.content_type)

        self.assertEqual(put1.status_code, 204)
        self.assertEqual(put1.content, '')
        
        r = self.client.get(self.url, testparamsregid)
        self.assertEqual(r.status_code, 200)
        state1_str = '%s' % teststateregid
        self.assertEqual(r.content, state1_str)
        self.assertEqual(r['etag'], '"%s"' % hashlib.sha1(state1_str).hexdigest())

        f_r = self.client.delete(self.url, {"registrationId": self.registrationId, "stateId": self.stateId, "actor": self.testactor})
        self.assertEqual(f_r.status_code, 400)
        self.assertIn('activityId parameter is missing', f_r.content)

        del_r = self.client.delete(self.url, testparamsregid)
        self.assertEqual(del_r.status_code, 204)

    
    def test_delete_without_actor(self):
        testparamsregid = {"registrationId": self.registrationId, "stateId": self.stateId, "activityId": self.activityId, "actor": self.testactor}
        path = '%s?%s' % (self.url, urllib.urlencode(testparamsregid))
        teststateregid = {"test":"delete activity state w/o actor","obj":{"actor":"test"}}
        put1 = self.client.put(path, teststateregid, content_type=self.content_type)

        self.assertEqual(put1.status_code, 204)
        self.assertEqual(put1.content, '')
        
        r = self.client.get(self.url, testparamsregid)
        self.assertEqual(r.status_code, 200)
        state1_str = '%s' % teststateregid
        self.assertEqual(r.content, state1_str)
        self.assertEqual(r['etag'], '"%s"' % hashlib.sha1(state1_str).hexdigest())

        f_r = self.client.delete(self.url, {"registrationId": self.registrationId, "stateId": self.stateId, "activityId": self.activityId})
        self.assertEqual(f_r.status_code, 400)
        self.assertIn('actor parameter is missing', f_r.content)

        del_r = self.client.delete(self.url, testparamsregid)
        self.assertEqual(del_r.status_code, 204)

    
    def test_delete_set(self):
        testparamsdelset1 = {"registrationId": self.registrationId, "stateId": "del_state_set_1", "activityId": self.activityId, "actor": self.testactor}
        path = '%s?%s' % (self.url, urllib.urlencode(testparamsdelset1))
        teststatedelset1 = {"test":"delete set #1","obj":{"actor":"test"}}
        put1 = self.client.put(path, teststatedelset1, content_type=self.content_type)

        self.assertEqual(put1.status_code, 204)
        self.assertEqual(put1.content, '')
        
        r = self.client.get(self.url, testparamsdelset1)
        self.assertEqual(r.status_code, 200)
        state1_str = '%s' % teststatedelset1
        self.assertEqual(r.content, state1_str)
        self.assertEqual(r['etag'], '"%s"' % hashlib.sha1(state1_str).hexdigest())

        testparamsdelset2 = {"registrationId": self.registrationId, "stateId": "del_state_set_2", "activityId": self.activityId, "actor": self.testactor}
        path = '%s?%s' % (self.url, urllib.urlencode(testparamsdelset2))
        teststatedelset2 = {"test":"delete set #2","obj":{"actor":"test"}}
        put1 = self.client.put(path, teststatedelset2, content_type=self.content_type)

        self.assertEqual(put1.status_code, 204)
        self.assertEqual(put1.content, '')
        
        r = self.client.get(self.url, testparamsdelset2)
        self.assertEqual(r.status_code, 200)
        state1_str = '%s' % teststatedelset2
        self.assertEqual(r.content, state1_str)
        self.assertEqual(r['etag'], '"%s"' % hashlib.sha1(state1_str).hexdigest())

        f_r = self.client.delete(self.url, {"registrationId": self.registrationId, "actor": self.testactor, "activityId": self.activityId})
        self.assertEqual(f_r.status_code, 204)

        r = self.client.get(self.url, testparamsdelset1)
        self.assertEqual(r.status_code, 404)
        self.assertIn('no activity', r.content)

        r = self.client.get(self.url, testparamsdelset2)
        self.assertEqual(r.status_code, 404)
        self.assertIn('no activity', r.content)

        
class ActivitiesTest(TestCase):
    def test_get(self):
        response = self.client.get(reverse(views.activities), {'activityId':'my_activity'})
        self.assertContains(response, 'Success')
        self.assertContains(response, 'my_activity')
    
    def test_get_no_activity(self):
        response = self.client.get(reverse(views.activities))
        self.assertContains(response, 'Error')
    
    def test_post(self):
        response = self.client.post(reverse(views.activities), {'activityId':'my_activity'},content_type='application/x-www-form-urlencoded')
        self.assertEqual(response.status_code, 405)

class ActivityProfileTest(TestCase):
    def test_put(self):
        response = self.client.put(reverse(views.activity_profile), {'activityId':'act-10','profileId':'10'},content_type='application/x-www-form-urlencoded')
        self.assertContains(response, 'Success')
        self.assertContains(response, 'act-10')
        self.assertContains(response, '10')
        
    def test_put_no_params(self):
        response = self.client.put(reverse(views.activity_profile),content_type='application/x-www-form-urlencoded')
        self.assertContains(response, 'Error')
    
    def test_put_no_actor(self):
        response = self.client.put(reverse(views.activity_profile), {'profileId':'10'},content_type='application/x-www-form-urlencoded')
        self.assertContains(response, 'Error')
        self.assertContains(response, 'activityId parameter missing')

    def test_put_no_profileId(self):
        response = self.client.put(reverse(views.activity_profile), {'activityId':'act'},content_type='application/x-www-form-urlencoded')
        self.assertContains(response, 'Error')
        self.assertContains(response, 'profileId parameter missing')
    
    def test_get_activity_only(self):
        response = self.client.get(reverse(views.activity_profile), {'activityId':'act'})
        self.assertContains(response, 'Success')
        self.assertContains(response, 'act')
        resp_hash = hashlib.sha1(response.content).hexdigest()
        self.assertEqual(response['ETag'], resp_hash)
    
    def test_get_activity_profileId(self):
        response = self.client.get(reverse(views.activity_profile), {'activityId':'act','profileId':'10'})
        self.assertContains(response, 'Success')
        self.assertContains(response, 'act')
        resp_hash = hashlib.sha1(response.content).hexdigest()
        self.assertEqual(response['ETag'], resp_hash)
    
    def test_get_activity_since(self):
        since = time.time()
        response = self.client.get(reverse(views.activity_profile), {'activityId':'act-foo','since':since})
        self.assertContains(response, 'Success')
        self.assertContains(response, 'act-foo')
        self.assertContains(response, since)
        resp_hash = hashlib.sha1(response.content).hexdigest()
        self.assertEqual(response['ETag'], resp_hash)
    
    def test_get_no_activity_profileId(self):
        response = self.client.get(reverse(views.activity_profile), {'profileId':'10'})
        self.assertContains(response, 'Error')
        self.assertContains(response, 'no activityId parameter')

    def test_get_no_activity_since(self):
        since = time.time()
        response = self.client.get(reverse(views.activity_profile), {'since':since})
        self.assertContains(response, 'Error')
        self.assertContains(response, 'no activityId parameter')
    
    def test_delete(self):
        response = self.client.delete(reverse(views.activity_profile), {'activityId':'act-del', 'profileId':'100'})
        self.assertContains(response, 'Success')
        self.assertContains(response, 'act-del')        
        self.assertContains(response, '100')

class ActorProfileTest(TestCase):
    testactor = '{"mbox":["mailto:test@example.com"]}'
    otheractor = '{"mbox":["mailto:other@example.com"]}'
    content_type = "application/json"
    testprofileId1 = "http://profile.test.id/test/1"
    testprofileId2 = "http://profile.test.id/test/2"
    testprofileId3 = "http://profile.test.id/test/3"
    otherprofileId1 = "http://profile.test.id/other/1"

    def setUp(self):
        self.testparams1 = {"profileId": self.testprofileId1, "actor": self.testactor}
        path = '%s?%s' % (reverse(views.actor_profile), urllib.urlencode(self.testparams1))
        self.testprofile1 = {"test":"put profile 1","obj":{"actor":"test"}}
        self.put1 = self.client.put(path, self.testprofile1, content_type=self.content_type)

        self.testparams2 = {"profileId": self.testprofileId2, "actor": self.testactor}
        path = '%s?%s' % (reverse(views.actor_profile), urllib.urlencode(self.testparams2))
        self.testprofile2 = {"test":"put profile 2","obj":{"actor":"test"}}
        self.put2 = self.client.put(path, self.testprofile2, content_type=self.content_type)

        self.testparams3 = {"profileId": self.testprofileId3, "actor": self.testactor}
        path = '%s?%s' % (reverse(views.actor_profile), urllib.urlencode(self.testparams3))
        self.testprofile3 = {"test":"put profile 3","obj":{"actor":"test"}}
        self.put3 = self.client.put(path, self.testprofile3, content_type=self.content_type)

        self.testparams4 = {"profileId": self.otherprofileId1, "actor": self.otheractor}
        path = '%s?%s' % (reverse(views.actor_profile), urllib.urlencode(self.testparams4))
        self.otherprofile1 = {"test":"put profile 1","obj":{"actor":"other"}}
        self.put4 = self.client.put(path, self.otherprofile1, content_type=self.content_type)

    def tearDown(self):
        self.client.delete(reverse(views.actor_profile), self.testparams1)
        self.client.delete(reverse(views.actor_profile), self.testparams2)
        self.client.delete(reverse(views.actor_profile), self.testparams3)
        self.client.delete(reverse(views.actor_profile), self.testparams4)

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
        response = self.client.put(path, profile, content_type=self.content_type)
        self.assertEqual(response.status_code, 409)
        self.assertIn('If-Match and If-None-Match headers were missing', response.content)
        
        r = self.client.get(reverse(views.actor_profile), self.testparams1)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.content, '%s' % self.testprofile1)

    def test_put_etag_right_on_change(self):
        path = '%s?%s' % (reverse(views.actor_profile), urllib.urlencode(self.testparams1))
        profile = {"test":"good - trying to put new profile w/ etag header","obj":{"actor":"test"}}
        thehash = '"%s"' % hashlib.sha1('%s' % self.testprofile1).hexdigest()
        response = self.client.put(path, profile, content_type=self.content_type, if_match=thehash)
        self.assertEqual(response.status_code, 204)
        self.assertEqual(response.content, '')

        r = self.client.get(reverse(views.actor_profile), self.testparams1)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.content, '%s' % profile)

    def test_put_etag_wrong_on_change(self):
        path = '%s?%s' % (reverse(views.actor_profile), urllib.urlencode(self.testparams1))
        profile = {"test":"error - trying to put new profile w/ wrong etag value","obj":{"actor":"test"}}
        thehash = '"%s"' % hashlib.sha1('%s' % 'wrong hash').hexdigest()
        response = self.client.put(path, profile, content_type=self.content_type, if_match=thehash)
        self.assertEqual(response.status_code, 412)
        self.assertIn('No resources matched', response.content)

        r = self.client.get(reverse(views.actor_profile), self.testparams1)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.content, '%s' % self.testprofile1)

    def test_put_etag_if_none_match_good(self):
        params = {"profileId": 'http://etag.nomatch.good', "actor": self.testactor}
        path = '%s?%s' % (reverse(views.actor_profile), urllib.urlencode(params))
        profile = {"test":"good - trying to put new profile w/ if none match etag header","obj":{"actor":"test"}}
        response = self.client.put(path, profile, content_type=self.content_type, if_none_match='*')
        self.assertEqual(response.status_code, 204)
        self.assertEqual(response.content, '')

        r = self.client.get(reverse(views.actor_profile), params)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.content, '%s' % profile)

        r = self.client.delete(reverse(views.actor_profile), params)

    def test_put_etag_if_none_match_bad(self):
        path = '%s?%s' % (reverse(views.actor_profile), urllib.urlencode(self.testparams1))
        profile = {"test":"error - trying to put new profile w/ if none match etag but one exists","obj":{"actor":"test"}}
        response = self.client.put(path, profile, content_type=self.content_type, if_none_match='*')
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
        response = self.client.put(path, profile, content_type=self.content_type)
        
        r = self.client.get(reverse(views.actor_profile), params)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.content, '%s' % profile)

        r = self.client.delete(reverse(views.actor_profile), params)
        self.assertEqual(r.status_code, 204)

        r = self.client.get(reverse(views.actor_profile), params)
        self.assertEqual(r.status_code, 404)

    def test_get_actor_since(self):
        prof_id = "http://oldprofile/time"
        updated =  datetime.datetime(2012, 6, 12, 12, 00).replace(tzinfo=utc)
        params = {"profileId": prof_id, "actor": self.testactor}
        path = '%s?%s' % (reverse(views.actor_profile), urllib.urlencode(params))
        profile = {"test":"actor profile since time: %s" % updated,"obj":{"actor":"test"}}
        response = self.client.put(path, profile, content_type=self.content_type, updated=updated.isoformat())

        r = self.client.get(reverse(views.actor_profile), params)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.content, '%s' % profile)

        since = datetime.datetime(2012, 7, 1, 12, 00).replace(tzinfo=utc)
        params2 = {"actor": self.testactor, "since":since.isoformat()}
        r2 = self.client.get(reverse(views.actor_profile), params2)
        self.assertNotIn(prof_id, r2.content)

        self.client.delete(reverse(views.actor_profile), params)

class ActorsTest(TestCase):
    def test_get(self):
        actor = json.dumps({"name":["me"],"mbox":["mailto:me@example.com"]})
        me = Actor.Actor(actor,create=True)
        response = self.client.get(reverse(views.actors), {'actor':actor})
        #print response
        self.assertContains(response, 'mailto:me@example.com')

    #def test_get_merge(self):
    #    actor = json.dumps({"name":["me"],"mbox":["mailto:me@example.com"]})
    #    response = self.client.get(reverse(views.actors), {'actor':actor})
    #    actor = json.dumps({"mbox":["mailto:me@example.com"]})
    #    response = self.client.get(reverse(views.actors), {'actor':actor})
    #    self.assertContains(response, 'mailto:me@example.com')
    #    self.assertContains(response, 'name')
    #    self.assertContains(response, 'me')
    
    def test_get_no_actor(self):
        response = self.client.get(reverse(views.actors))
        self.assertEqual(response.status_code, 400)
    
    def test_post(self):
        actor = json.dumps({"name":["me"],"mbox":["mailto:me@example.com"]})
        response = self.client.post(reverse(views.actors), {'actor':actor},content_type='application/x-www-form-urlencoded')
        self.assertEqual(response.status_code, 405)

class Models_ActivityTest(py_tc):
    
    #Called on all activity objects to see if they were created with the correct fields
    def do_activity_object(self,act, act_id, objType):
        self.assertEqual(act.activity.activity_id, act_id)
        self.assertEqual(act.activity.objectType, objType)
        
    #Called on all activity django models to see if they were created with the correct fields    
    def do_activity_model(self,realid,act_id, objType):
        self.assertEqual(models.activity.objects.filter(id=realid)[0].objectType, objType)
        self.assertEqual(models.activity.objects.filter(id=realid)[0].activity_id, act_id)

    #Called on all activity objects with definitions to see if they were created with the correct fields
    def do_activity_definition_object(self, act, name, desc, course, intType):
        self.assertEqual(act.activity.activity_definition.name, name)
        self.assertEqual(act.activity.activity_definition.description, desc)
        self.assertEqual(act.activity.activity_definition.activity_definition_type, course)
        self.assertEqual(act.activity.activity_definition.interactionType, intType)

    #Called on all activity django models with definitions to see if they were created with the correct fields
    def do_activity_definition_model(self, PK, testname, testdesc, course, intType):
        self.assertEqual(models.activity_definition.objects.get(activity=PK).name, testname)
        self.assertEqual(models.activity_definition.objects.get(activity=PK).description, testdesc)
        self.assertEqual(models.activity_definition.objects.get(activity=PK).activity_definition_type, course)
        self.assertEqual(models.activity_definition.objects.get(activity=PK).interactionType, intType)

    #Called on all activity objects with extensions to see if they were created with the correct fields and values
    #All extensions are created with the same three values and keys
    def do_activity_definition_extensions_object(self, act, key1, key2, key3, value1, value2, value3):
        self.assertEqual(act.activity_definition_extensions[0].key, key3)
        self.assertEqual(act.activity_definition_extensions[1].key, key2)
        self.assertEqual(act.activity_definition_extensions[2].key, key1)

        self.assertEqual(act.activity_definition_extensions[0].value, value3)    
        self.assertEqual(act.activity_definition_extensions[1].value, value2)
        self.assertEqual(act.activity_definition_extensions[2].value, value1)        

    #Called on all activity django models with extensions to see if they were created with the correct fields and values
    #All extensions are created with the same three values and keys
    def do_activity_definition_extensions_model(self, defPK, key1, key2, key3, value1, value2, value3):
        #Create list comprehesions to easier assess keys and values
        extList = models.activity_extentions.objects.values_list().filter(activity_definition=defPK)
        extKeys = [ext[1] for ext in extList]
        extVals = [ext[2] for ext in extList]

        self.assertIn(key1, extKeys)
        self.assertIn(key2, extKeys)
        self.assertIn(key3, extKeys)
        self.assertIn(value1, extVals)
        self.assertIn(value2, extVals)
        self.assertIn(value3, extVals)

    #call on all activity objects with a correctResponsePattern because of cmi.interaction type
    def do_activity_definition_correctResponsePattern_object(self, act, defPK, rspPK, answer):
        self.assertIn(act.correctResponsesPattern.activity_definition, defPK)
        self.assertIn(rspPK[0].activity_definition, defPK)
        self.assertEqual(act.answers[0].answer, answer)

    #Called on all activity django models with a correctResponsePattern because of cmi.interaction type
    def do_activity_definition_correctResponsePattern_model(self, rspPK, answers):
        rspAnswers = models.correctresponsespattern_answer.objects.values_list('answer', flat=True).filter(correctresponsespattern=rspPK)
        
        for answer in answers:
            self.assertIn(answer,rspAnswers)

    #Called on all activity django models with choices because of sequence and choice interactionType
    def do_actvity_definition_choices_model(self, defPK, clist, dlist):
        descs = models.activity_definition_choice.objects.values_list('description', flat=True).filter(activity_definition=defPK)
        choices = models.activity_definition_choice.objects.values_list('choice_id', flat=True).filter(activity_definition=defPK)
        
        for c in clist:
            self.assertIn(c,choices)

        for d in dlist:
            self.assertIn(d, descs)

    #Called on all activity django models with scale because of likert interactionType
    def do_actvity_definition_likert_model(self, defPK, clist, dlist):
        descs = models.activity_definition_scale.objects.values_list('description', flat=True).filter(activity_definition=defPK)
        choices = models.activity_definition_scale.objects.values_list('scale_id', flat=True).filter(activity_definition=defPK)
        
        for c in clist:
            self.assertIn(c,choices)

        for d in dlist:
            self.assertIn(d, descs)

    #Called on all activity django models with steps because of performance interactionType
    def do_actvity_definition_performance_model(self, defPK, slist, dlist):
        descs = models.activity_definition_step.objects.values_list('description', flat=True).filter(activity_definition=defPK)
        steps = models.activity_definition_step.objects.values_list('step_id', flat=True).filter(activity_definition=defPK)
        
        for s in slist:
            self.assertIn(s,steps)

        for d in dlist:
            self.assertIn(d, descs)

    #Called on all activity django models with source and target because of matching interactionType
    def do_actvity_definition_matching_model(self, defPK, source_id_list, source_desc_list, target_id_list, target_desc_list):
        source_descs = models.activity_definition_source.objects.values_list('description', flat=True).filter(activity_definition=defPK)
        sources = models.activity_definition_source.objects.values_list('source_id', flat=True).filter(activity_definition=defPK)
        
        target_descs = models.activity_definition_target.objects.values_list('description', flat=True).filter(activity_definition=defPK)
        targets = models.activity_definition_target.objects.values_list('target_id', flat=True).filter(activity_definition=defPK)
        
        for s_id in source_id_list:
            self.assertIn(s_id,sources)

        for s_desc in source_desc_list:
            self.assertIn(s_desc, source_descs)

        for t_id in target_id_list:
            self.assertIn(t_id,targets)

        for t_desc in target_desc_list:
            self.assertIn(t_desc, target_descs)            


    #Test activity that doesn't have a def, isn't a link and resolves (will not create Activity object)
    def test_activity_no_def_not_link_resolve(self):
        self.assertRaises(Exception, Activity.Activity, json.dumps({'objectType': 'Activity', 'id': 'http://yahoo.com'}))

        self.assertRaises(models.activity.DoesNotExist, models.activity.objects.get, activity_id='http://yahoo.com')

    #Test activity that doesn't have a def, isn't a link and doesn't resolve (creates useless Activity object)
    def test_activity_no_def_not_link_no_resolve(self):
        act = Activity.Activity(json.dumps({'objectType':'Activity', 'id':'foo'}))
        
        self.do_activity_object(act,'foo','Activity')
        self.do_activity_model(act.activity.id, 'foo', 'Activity')

    #Test activity that doesn't have a def, isn't a link and conforms to schema (populates everything from XML)
    def test_activity_no_def_not_link_schema_conform(self):
        act = Activity.Activity(json.dumps({'objectType':'Activity', 'id': 'http://localhost:8000/TCAPI/tcexample/'}))

        PK = models.activity.objects.filter(id=act.activity.id)
        
        self.do_activity_object(act,'http://localhost:8000/TCAPI/tcexample/', 'Activity')
        self.do_activity_definition_object(act, 'Example Name', 'Example Desc', 'module', 'course')
        self.do_activity_model(act.activity.id, 'http://localhost:8000/TCAPI/tcexample/', 'Activity')        
        self.do_activity_definition_model(PK, 'Example Name', 'Example Desc', 'module', 'course')

    #Test activity that doesn't have a def, isn't a link and conforms to schema but ID already exists (won't create it)
    def test_activity_no_def_not_link_schema_conform1(self):
        self.assertRaises(Exception, Activity.Activity, json.dumps({'objectType': 'Activity', 'id': 'http://localhost:8000/TCAPI/tcexample/'}))

    '''
    Choices is not part of the XML so this will throw an exception
    #Test activity that doesn't have a def, isn't a link and conforms to schema with CRP (populates everything from XML)
    def test_activity_no_def_not_link_schema_conform_correctResponsesPattern(self):
        act = Activity.Activity(json.dumps({'objectType':'Activity', 'id': 'http://localhost:8000/TCAPI/tcexample3/'}))

        PK = models.activity.objects.filter(id=act.activity.id)
        defPK = models.activity_definition.objects.filter(activity=PK)
        rspPK = models.activity_def_correctresponsespattern.objects.filter(activity_definition=defPK)

        self.do_activity_object(act,'http://localhost:8000/TCAPI/tcexample3/', 'Activity')
        self.do_activity_definition_object(act, 'Example Name', 'Example Desc', 'cmi.interaction', 'multiple-choice')
        self.do_activity_model(act.activity.id, 'http://localhost:8000/TCAPI/tcexample3/', 'Activity')        
        self.do_activity_definition_model(PK, 'Example Name', 'Example Desc', 'cmi.interaction', 'multiple-choice')
    
        self.assertEqual(act.answers[0].answer, 'golf')
        self.assertEqual(act.answers[1].answer, 'tetris')
        self.do_activity_definition_correctResponsePattern_model(rspPK, ['golf', 'tetris'])
    '''

    #Test activity that doesn't have a def, isn't a link and conforms to schema with extensions (populates everything from XML)
    def test_activity_no_def_not_link_schema_conform_extensions(self):
        act = Activity.Activity(json.dumps({'objectType':'Activity', 'id': 'http://localhost:8000/TCAPI/tcexample2/'}))

        PK = models.activity.objects.filter(id=act.activity.id)
        defPK = models.activity_definition.objects.filter(activity=PK)

        self.do_activity_object(act,'http://localhost:8000/TCAPI/tcexample2/', 'Activity')
        self.do_activity_definition_object(act, 'Example Name', 'Example Desc', 'module', 'course')
        self.do_activity_model(act.activity.id, 'http://localhost:8000/TCAPI/tcexample2/', 'Activity')        
        self.do_activity_definition_model(PK, 'Example Name', 'Example Desc', 'module', 'course')

        self.do_activity_definition_extensions_object(act, 'keya', 'keyb', 'keyc', 'first value', 'second value', 'third value')
        self.do_activity_definition_extensions_model(defPK, 'keya', 'keyb', 'keyc','first value', 'second value', 'third value')

    #Test an activity that has a def,is not a link yet the ID resolves, but doesn't conform to XML schema (will not create one)
    def test_activity_not_link_resolve(self):
        self.assertRaises(Exception, Activity.Activity, json.dumps({'objectType': 'Activity', 'id': 'http://tincanapi.wikispaces.com',
                'definition': {'name': 'testname','description': 'testdesc', 'type': 'course',
                'interactionType': 'intType'}}))

        self.assertRaises(models.activity.DoesNotExist, models.activity.objects.get, activity_id='http://tincanapi.wikispaces.com')

    #Test an activity that has a def, not a link and the provided ID doesn't resolve (should still use values from JSON)
    def test_activity_not_link_no_resolve(self):
        act = Activity.Activity(json.dumps({'objectType': 'Activity', 'id':'/var/www/adllrs/activity/example.xml',
                'definition': {'name': 'testname','description': 'testdesc', 'type': 'course',
                'interactionType': 'intType'}}))

        PK = models.activity.objects.filter(id=act.activity.id)
        
        self.do_activity_object(act, '/var/www/adllrs/activity/example.xml', 'Activity')
        self.do_activity_definition_object(act, 'testname', 'testdesc', 'course', 'intType')
        self.do_activity_model(act.activity.id, '/var/www/adllrs/activity/example.xml', 'Activity')        
        self.do_activity_definition_model(PK, 'testname', 'testdesc', 'course', 'intType')

    #Test an activity that has a def, not a link and the provided ID conforms to the schema (should use values from XML and override JSON)
    def test_activity_not_link_schema_conform(self):
        act = Activity.Activity(json.dumps({'objectType': 'Activity', 'id':'http://localhost:8000/TCAPI/tcexample4/',
                'definition': {'name': 'testname','description': 'testdesc', 'type': 'course',
                'interactionType': 'intType'}}))

        PK = models.activity.objects.filter(id=act.activity.id)
        
        self.do_activity_object(act, 'http://localhost:8000/TCAPI/tcexample4/', 'Activity')
        self.do_activity_definition_object(act, 'Example Name', 'Example Desc', 'module', 'course')
        self.do_activity_model(act.activity.id, 'http://localhost:8000/TCAPI/tcexample4/', 'Activity')        
        self.do_activity_definition_model(PK, 'Example Name', 'Example Desc', 'module', 'course')

    #Test an activity that has a def, is a link and the ID resolves (should use values from JSON)
    def test_activity_link_resolve(self):
        act = Activity.Activity(json.dumps({'objectType': 'Activity', 'id': home,
                'definition': {'name': 'testname','description': 'testdesc', 'type': 'link',
                'interactionType': 'intType'}}))

        PK = models.activity.objects.filter(id=act.activity.id)
        
        self.do_activity_object(act, home, 'Activity')
        self.do_activity_definition_object(act, 'testname', 'testdesc', 'link', 'intType')
        self.do_activity_model(act.activity.id, home, 'Activity')        
        self.do_activity_definition_model(PK, 'testname', 'testdesc', 'link', 'intType')

    #Test an activity that has a def, is a link and the ID does not resolve (will not create one)
    def test_activity_link_no_resolve(self):
        self.assertRaises(Exception, Activity.Activity, json.dumps({'objectType': 'Activity', 'id': 'http://foo',
                'definition': {'name': 'testname','description': 'testdesc', 'type': 'link',
                'interactionType': 'intType'}}))

        self.assertRaises(models.activity.DoesNotExist, models.activity.objects.get, activity_id='http://foo')

    #Throws exception because incoming data is not JSON
    def test_activity_not_json(self):
        self.assertRaises(Exception, Activity.Activity,"This string should throw exception since it's not JSON")

    #Test an activity where there is no given objectType, won't be created with one
    def test_activity_no_objectType(self):
        act = Activity.Activity(json.dumps({'id':'fooa'}))
        
        self.do_activity_object(act,'fooa', None)
        self.do_activity_model(act.activity.id,'fooa', None)

    #Test an activity with a provided objectType but http://localhost:8000/TCAPI/tcexample4/    def test_activity_wrong_objectType(self):
        act = Activity.Activity(json.dumps({'id': 'foob', 'objectType':'Wrong'}))    

        self.do_activity_object(act,'foob', 'Activity')
        self.do_activity_model(act.activity.id, 'foob', 'Activity')

    #Test activity where given URL doesn't resolve
    def test_activity_invalid_activity_id(self):
        self.assertRaises(ValidationError, Activity.Activity, json.dumps({'id': 'http://foo', 'objectType':'Activity',
                'definition': {'name': 'testname','description': 'testdesc', 'type': 'link',
                'interactionType': 'intType'}}))

    #Test activity with definition - must retrieve activity object in order to test definition from DB
    def test_activity_definition(self):
        act = Activity.Activity(json.dumps({'objectType': 'Activity', 'id':'fooc',
                'definition': {'name': 'testname','description': 'testdesc', 'type': 'course',
                'interactionType': 'intType'}}))

        PK = models.activity.objects.filter(id=act.activity.id)
        
        self.do_activity_object(act,'fooc', 'Activity')
        self.do_activity_definition_object(act, 'testname', 'testdesc', 'course', 'intType')
        self.do_activity_model(act.activity.id,'fooc', 'Activity')        
        self.do_activity_definition_model(PK, 'testname', 'testdesc', 'course', 'intType')

    #Test activity with definition given wrong type (won't create it)
    def test_activity_definition_wrong_type(self):
        self.assertRaises(Exception, Activity.Activity, json.dumps({'objectType': 'Activity',
                'id':'http://msn.com','definition': {'NAME': 'testname',
                'descripTION': 'testdesc', 'tYpe': 'wrong','interactionType': 'intType'}}))

        self.assertRaises(models.activity.DoesNotExist, models.activity.objects.get, activity_id='http://msn.com')
    
    #Test activity with definition missing name in definition (won't create it)
    def test_activity_definition_required_fields(self):
        self.assertRaises(Exception, Activity.Activity, json.dumps({'objectType': 'Activity',
                'id':'http://google.com','definition': {'description': 'testdesc',
                'type': 'wrong','interactionType': 'intType'}}))

        self.assertRaises(models.activity.DoesNotExist, models.activity.objects.get, activity_id='http://google.com')

    #Test activity with definition that contains extensions - need to retrieve activity and activity definition objects in order to test extenstions
    def test_activity_definition_extensions(self):
        act = Activity.Activity(json.dumps({'objectType': 'Activity', 'id':'food',
                'definition': {'name': 'testname2','description': 'testdesc2', 'type': 'course',
                'interactionType': 'intType2', 'extensions': {'key1': 'value1', 'key2': 'value2',
                'key3': 'value3'}}}))

        PK = models.activity.objects.filter(id=act.activity.id)
        defPK = models.activity_definition.objects.filter(activity=PK)

        self.do_activity_object(act,'food', 'Activity')
        self.do_activity_definition_object(act, 'testname2', 'testdesc2', 'course', 'intType2')
        
        self.do_activity_model(act.activity.id,'food', 'Activity')        
        self.do_activity_definition_model(PK, 'testname2', 'testdesc2', 'course', 'intType2')

        self.do_activity_definition_extensions_object(act, 'key1', 'key2', 'key3', 'value1', 'value2', 'value3')
        self.do_activity_definition_extensions_model(defPK, 'key1', 'key2', 'key3', 'value1', 'value2', 'value3')

    #Test activity with definition given wrong interactionType (won't create one)
    def test_activity_definition_wrong_interactionType(self):

        self.assertRaises(Exception, Activity.Activity, json.dumps({'objectType': 'Activity', 'id':'http://facebook.com',
                'definition': {'name': 'testname2','description': 'testdesc2', 'type': 'cmi.interaction',
                'interactionType': 'intType2', 'correctResponsesPatteRN': 'response', 'extensions': {'key1': 'value1', 'key2': 'value2',
                'key3': 'value3'}}}))
     
        self.assertRaises(models.activity.DoesNotExist, models.activity.objects.get, activity_id='http://facebook.com')


    #Test activity with definition and valid interactionType-it must also provide the correctResponsesPattern field
    #(wont' create it)
    def test_activity_definition_no_correctResponsesPattern(self):
        self.assertRaises(Exception, Activity.Activity, json.dumps({'objectType': 'Activity', 'id':'http://twitter.com',
                'definition': {'name': 'testname2','description': 'testdesc2', 'type': 'cmi.interaction',
                'interactionType': 'true-false', 'extensions': {'key1': 'value1', 'key2': 'value2',
                'key3': 'value3'}}}))
     
        self.assertRaises(models.activity.DoesNotExist, models.activity.objects.get, activity_id='http://twitter.com')

    #Test activity with definition that is cmi.interaction and true-false interactionType
    def test_activity_definition_cmiInteraction_true_false(self):

        act = Activity.Activity(json.dumps({'objectType': 'Activity', 'id':'fooe',
                'definition': {'name': 'testname2','description': 'testdesc2', 'type': 'cmi.interaction',
                'interactionType': 'true-false','correctResponsesPattern': ['true'] ,'extensions': {'key1': 'value1', 'key2': 'value2',
                'key3': 'value3'}}}))

        PK = models.activity.objects.filter(id=act.activity.id)
        defPK = models.activity_definition.objects.filter(activity=PK)
        rspPK = models.activity_def_correctresponsespattern.objects.filter(activity_definition=defPK)


        self.do_activity_object(act,'fooe', 'Activity')
        self.do_activity_definition_object(act, 'testname2', 'testdesc2', 'cmi.interaction', 'true-false')
        
        self.do_activity_model(act.activity.id,'fooe', 'Activity')                
        self.do_activity_definition_model(PK, 'testname2', 'testdesc2', 'cmi.interaction', 'true-false')

        self.do_activity_definition_extensions_object(act, 'key1', 'key2', 'key3', 'value1', 'value2', 'value3')
        self.do_activity_definition_extensions_model(defPK, 'key1', 'key2', 'key3', 'value1', 'value2', 'value3')

        self.do_activity_definition_correctResponsePattern_object(act, defPK, rspPK, 'true')
        self.do_activity_definition_correctResponsePattern_model(rspPK, ['true'])
    
    #Test activity with definition that is cmi.interaction and multiple choice interactionType
    def test_activity_definition_cmiInteraction_multiple_choice(self):    
        act = Activity.Activity(json.dumps({'objectType': 'Activity', 'id':'foof',
                'definition': {'name': 'testname2','description': 'testdesc2', 'type': 'cmi.interaction',
                'interactionType': 'multiple-choice','correctResponsesPattern': ['golf', 'tetris'],
                'choices':[{'id': 'golf', 'description': {'en-US':'Golf Example'}},{'id': 'tetris',
                'description':{'en-US': 'Tetris Example'}}, {'id':'facebook', 'description':{'en-US':'Facebook App'}},
                {'id':'scrabble', 'description': {'en-US': 'Scrabble Example'}}],
                'extensions': {'key1': 'value1', 'key2': 'value2',
                'key3': 'value3'}}}))

        PK = models.activity.objects.filter(id=act.activity.id)
        defPK = models.activity_definition.objects.filter(activity=PK)
        rspPK = models.activity_def_correctresponsespattern.objects.filter(activity_definition=defPK)

        self.do_activity_object(act,'foof', 'Activity')
        self.do_activity_model(act.activity.id,'foof', 'Activity')

        self.do_activity_definition_object(act, 'testname2', 'testdesc2', 'cmi.interaction', 'multiple-choice')        
        self.do_activity_definition_model(PK, 'testname2', 'testdesc2', 'cmi.interaction', 'multiple-choice')

        self.do_activity_definition_extensions_object(act, 'key1', 'key2', 'key3', 'value1', 'value2', 'value3')
        self.do_activity_definition_extensions_model(defPK, 'key1', 'key2', 'key3', 'value1', 'value2', 'value3')

        self.assertEqual(act.answers[0].answer, 'golf')
        self.assertEqual(act.answers[1].answer, 'tetris')
        self.do_activity_definition_correctResponsePattern_model(rspPK, ['golf', 'tetris'])

        #Test object choice values
        self.assertEqual(act.choices[0].choice_id, 'golf')
        self.assertEqual(act.choices[0].description, '{"en-US": "Golf Example"}')

        self.assertEqual(act.choices[1].choice_id, 'tetris')
        self.assertEqual(act.choices[1].description, '{"en-US": "Tetris Example"}')
        
        self.assertEqual(act.choices[2].choice_id, 'facebook')
        self.assertEqual(act.choices[2].description, '{"en-US": "Facebook App"}')

        self.assertEqual(act.choices[3].choice_id, 'scrabble')
        self.assertEqual(act.choices[3].description, '{"en-US": "Scrabble Example"}')

        #Check model choice values
        clist = ['golf', 'tetris', 'facebook', 'scrabble']
        dlist = ['{"en-US": "Golf Example"}','{"en-US": "Tetris Example"}','{"en-US": "Facebook App"}','{"en-US": "Scrabble Example"}']
        self.do_actvity_definition_choices_model(defPK, clist, dlist)        
        
    #Test activity with definition that is cmi.interaction and multiple choice but missing choices (won't create it)
    def test_activity_definition_cmiInteraction_multiple_choice_no_choices(self):
        self.assertRaises(Exception, Activity.Activity, json.dumps({'objectType': 'Activity', 'id':'http://wikipedia.org',
                'definition': {'name': 'testname2','description': 'testdesc2', 'type': 'cmi.interaction',
                'interactionType': 'multiple-choice','correctResponsesPattern': ['golf', 'tetris'],
                'extensions': {'key1': 'value1', 'key2': 'value2',
                'key3': 'value3'}}}))   

        self.assertRaises(models.activity.DoesNotExist, models.activity.objects.get, activity_id='http://wikipedia.org')
    
    #Test activity with definition that is cmi.interaction and fill in interactionType
    def test_activity_definition_cmiInteraction_fill_in(self):
        act = Activity.Activity(json.dumps({'objectType': 'Activity', 'id':'foog',
                'definition': {'name': 'testname2','description': 'testdesc2', 'type': 'cmi.interaction',
                'interactionType': 'fill-in','correctResponsesPattern': ['Fill in answer'],
                'extensions': {'key1': 'value1', 'key2': 'value2',
                'key3': 'value3'}}}))

        PK = models.activity.objects.filter(id=act.activity.id)
        defPK = models.activity_definition.objects.filter(activity=PK)
        rspPK = models.activity_def_correctresponsespattern.objects.filter(activity_definition=defPK)

        self.do_activity_object(act,'foog', 'Activity')
        self.do_activity_model(act.activity.id,'foog', 'Activity')

        self.do_activity_definition_object(act, 'testname2', 'testdesc2', 'cmi.interaction', 'fill-in')        
        self.do_activity_definition_model(PK, 'testname2', 'testdesc2', 'cmi.interaction', 'fill-in')

        self.do_activity_definition_extensions_object(act, 'key1', 'key2', 'key3', 'value1', 'value2', 'value3')
        self.do_activity_definition_extensions_model(defPK, 'key1', 'key2', 'key3', 'value1', 'value2', 'value3')

        self.do_activity_definition_correctResponsePattern_object(act, defPK, rspPK, 'Fill in answer')
        self.do_activity_definition_correctResponsePattern_model(rspPK, ['Fill in answer'])

    #Test activity with definition that is cmi.interaction and long fill in interactionType
    def test_activity_definition_cmiInteraction_long_fill_in(self):

        act = Activity.Activity(json.dumps({'objectType': 'Activity', 'id':'fooh',
                'definition': {'name': 'testname2','description': 'testdesc2', 'type': 'cmi.interaction',
                'interactionType': 'fill-in','correctResponsesPattern': ['Long fill in answer'],
                'extensions': {'key1': 'value1', 'key2': 'value2',
                'key3': 'value3'}}}))

        PK = models.activity.objects.filter(id=act.activity.id)
        defPK = models.activity_definition.objects.filter(activity=PK)
        rspPK = models.activity_def_correctresponsespattern.objects.filter(activity_definition=defPK)

        self.do_activity_object(act, 'fooh', 'Activity')
        self.do_activity_model(act.activity.id, 'fooh', 'Activity')

        self.do_activity_definition_object(act, 'testname2', 'testdesc2', 'cmi.interaction', 'fill-in')        
        self.do_activity_definition_model(PK, 'testname2', 'testdesc2', 'cmi.interaction', 'fill-in')

        self.do_activity_definition_extensions_object(act, 'key1', 'key2', 'key3', 'value1', 'value2', 'value3')
        self.do_activity_definition_extensions_model(defPK, 'key1', 'key2', 'key3', 'value1', 'value2', 'value3')

        self.do_activity_definition_correctResponsePattern_object(act, defPK, rspPK, 'Long fill in answer')
        self.do_activity_definition_correctResponsePattern_model(rspPK, ['Long fill in answer'])

    #Test activity with definition that is cmi.interaction and likert interactionType
    def test_activity_definition_cmiInteraction_likert(self):    
        act = Activity.Activity(json.dumps({'objectType': 'Still gonna be activity', 'id':'fooi',
                'definition': {'name': 'testname2','description': 'testdesc2', 'type': 'cmi.interaction',
                'interactionType': 'likert','correctResponsesPattern': ['likert_3'],
                'scale':[{'id': 'likert_0', 'description': {'en-US':'Its OK'}},{'id': 'likert_1',
                'description':{'en-US': 'Its Pretty Cool'}}, {'id':'likert_2', 'description':{'en-US':'Its Damn Cool'}},
                {'id':'likert_3', 'description': {'en-US': 'Its Gonna Change the World'}}]}}))

        PK = models.activity.objects.filter(id=act.activity.id)
        defPK = models.activity_definition.objects.filter(activity=PK)
        rspPK = models.activity_def_correctresponsespattern.objects.filter(activity_definition=defPK)

        self.do_activity_object(act, 'fooi', 'Activity')
        self.do_activity_model(act.activity.id, 'fooi', 'Activity')

        self.do_activity_definition_object(act, 'testname2', 'testdesc2', 'cmi.interaction', 'likert')        
        self.do_activity_definition_model(PK, 'testname2', 'testdesc2', 'cmi.interaction', 'likert')

        self.assertEqual(act.answers[0].answer, 'likert_3')
        self.do_activity_definition_correctResponsePattern_model(rspPK, ['likert_3'])

        #Test object choice values
        self.assertEqual(act.scale_choices[0].scale_id, 'likert_0')
        self.assertEqual(act.scale_choices[0].description, '{"en-US": "Its OK"}')

        self.assertEqual(act.scale_choices[1].scale_id, 'likert_1')
        self.assertEqual(act.scale_choices[1].description, '{"en-US": "Its Pretty Cool"}')
        
        self.assertEqual(act.scale_choices[2].scale_id, 'likert_2')
        self.assertEqual(act.scale_choices[2].description, '{"en-US": "Its Damn Cool"}')

        self.assertEqual(act.scale_choices[3].scale_id, 'likert_3')
        self.assertEqual(act.scale_choices[3].description, '{"en-US": "Its Gonna Change the World"}')

        #Check model choice values
        clist = ['likert_3']
        dlist = ['{"en-US": "Its OK"}','{"en-US": "Its Pretty Cool"}','{"en-US": "Its Damn Cool"}','{"en-US": "Its Gonna Change the World"}']
        self.do_actvity_definition_likert_model(defPK, clist, dlist)

    #Test activity with definition that is cmi.interaction and matching interactionType
    def test_activity_definition_cmiInteraction_matching(self):    
        act = Activity.Activity(json.dumps({'objectType': 'Still gonna be activity', 'id':'fooj',
                'definition': {'name': 'testname2','description': 'testdesc2', 'type': 'cmi.interaction',
                'interactionType': 'matching','correctResponsesPattern': ['lou.3,tom.2,andy.1'],
                'source':[{'id': 'lou', 'description': {'en-US':'Lou'}},{'id': 'tom',
                'description':{'en-US': 'Tom'}}, {'id':'andy', 'description':{'en-US':'Andy'}}],
                'target':[{'id':'1', 'description':{'en-US': 'SCORM Engine'}},{'id':'2',
                'description':{'en-US': 'Pure-sewage'}},{'id':'3', 'description':{'en-US': 'SCORM Cloud'}}]}}))

        PK = models.activity.objects.filter(id=act.activity.id)
        defPK = models.activity_definition.objects.filter(activity=PK)
        rspPK = models.activity_def_correctresponsespattern.objects.filter(activity_definition=defPK)

        self.do_activity_object(act, 'fooj', 'Activity')
        self.do_activity_model(act.activity.id, 'fooj', 'Activity')

        self.do_activity_definition_object(act, 'testname2', 'testdesc2', 'cmi.interaction', 'matching')        
        self.do_activity_definition_model(PK, 'testname2', 'testdesc2', 'cmi.interaction', 'matching')

        self.assertEqual(act.answers[0].answer, 'lou.3,tom.2,andy.1')
        self.do_activity_definition_correctResponsePattern_model(rspPK, ['lou.3,tom.2,andy.1'])

        #Test object choice values
        self.assertEqual(act.source_choices[0].source_id, 'lou')
        self.assertEqual(act.source_choices[0].description, '{"en-US": "Lou"}')

        self.assertEqual(act.source_choices[1].source_id, 'tom')
        self.assertEqual(act.source_choices[1].description, '{"en-US": "Tom"}')
        
        self.assertEqual(act.source_choices[2].source_id, 'andy')
        self.assertEqual(act.source_choices[2].description, '{"en-US": "Andy"}')

        self.assertEqual(act.target_choices[0].target_id, '1')
        self.assertEqual(act.target_choices[0].description, '{"en-US": "SCORM Engine"}')

        self.assertEqual(act.target_choices[1].target_id, '2')
        self.assertEqual(act.target_choices[1].description, '{"en-US": "Pure-sewage"}')
        
        self.assertEqual(act.target_choices[2].target_id, '3')
        self.assertEqual(act.target_choices[2].description, '{"en-US": "SCORM Cloud"}')

        #Check model choice values
        source_id_list = ['lou', 'tom', 'andy']
        source_desc_list = ['{"en-US": "Lou"}','{"en-US": "Tom"}','{"en-US": "Andy"}']
        target_id_list = ['1','2','3']
        target_desc_list = ['{"en-US": "SCORM Engine"}','{"en-US": "Pure-sewage"}','{"en-US": "SCORM Cloud"}']
        self.do_actvity_definition_matching_model(defPK, source_id_list, source_desc_list, target_id_list, target_desc_list)

    #Test activity with definition that is cmi.interaction and performance interactionType
    def test_activity_definition_cmiInteraction_performance(self):    
        act = Activity.Activity(json.dumps({'objectType': 'activity', 'id':'fook',
                'definition': {'name': 'testname2','description': 'testdesc2', 'type': 'cmi.interaction',
                'interactionType': 'performance','correctResponsesPattern': ['pong.1,dg.10,lunch.4'],
                'steps':[{'id': 'pong', 'description': {'en-US':'Net pong matches won'}},{'id': 'dg',
                'description':{'en-US': 'Strokes over par in disc golf at Liberty'}},
                {'id':'lunch', 'description':{'en-US':'Lunch having been eaten'}}]}}))

        PK = models.activity.objects.filter(id=act.activity.id)
        defPK = models.activity_definition.objects.filter(activity=PK)
        rspPK = models.activity_def_correctresponsespattern.objects.filter(activity_definition=defPK)

        self.do_activity_object(act, 'fook', 'Activity')
        self.do_activity_model(act.activity.id, 'fook', 'Activity')

        self.do_activity_definition_object(act, 'testname2', 'testdesc2', 'cmi.interaction', 'performance')        
        self.do_activity_definition_model(PK, 'testname2', 'testdesc2', 'cmi.interaction', 'performance')

        self.assertEqual(act.answers[0].answer, 'pong.1,dg.10,lunch.4')
        self.do_activity_definition_correctResponsePattern_model(rspPK, ['pong.1,dg.10,lunch.4'])

        #Test object step values
        self.assertEqual(act.steps[0].step_id, 'pong')
        self.assertEqual(act.steps[0].description, '{"en-US": "Net pong matches won"}')

        self.assertEqual(act.steps[1].step_id, 'dg')
        self.assertEqual(act.steps[1].description, '{"en-US": "Strokes over par in disc golf at Liberty"}')
        
        self.assertEqual(act.steps[2].step_id, 'lunch')
        self.assertEqual(act.steps[2].description, '{"en-US": "Lunch having been eaten"}')

        #Check model choice values
        slist = ['pong', 'dg', 'lunch']
        dlist = ['{"en-US": "Net pong matches won"}','{"en-US": "Strokes over par in disc golf at Liberty"}','{"en-US": "Lunch having been eaten"}']
        self.do_actvity_definition_performance_model(defPK, slist, dlist)

    #Test activity with definition that is cmi.interaction and sequencing interactionType
    def test_activity_definition_cmiInteraction_sequencing(self):    
        act = Activity.Activity(json.dumps({'objectType': 'activity', 'id':'fool',
                'definition': {'name': 'testname2','description': 'testdesc2', 'type': 'cmi.interaction',
                'interactionType': 'sequencing','correctResponsesPattern': ['lou,tom,andy,aaron'],
                'choices':[{'id': 'lou', 'description': {'en-US':'Lou'}},{'id': 'tom','description':{'en-US': 'Tom'}},
                {'id':'andy', 'description':{'en-US':'Andy'}},{'id':'aaron', 'description':{'en-US':'Aaron'}}]}}))

        PK = models.activity.objects.filter(id=act.activity.id)
        defPK = models.activity_definition.objects.filter(activity=PK)
        rspPK = models.activity_def_correctresponsespattern.objects.filter(activity_definition=defPK)

        self.do_activity_object(act, 'fool', 'Activity')
        self.do_activity_model(act.activity.id, 'fool', 'Activity')

        self.do_activity_definition_object(act, 'testname2', 'testdesc2', 'cmi.interaction', 'sequencing')        
        self.do_activity_definition_model(PK, 'testname2', 'testdesc2', 'cmi.interaction', 'sequencing')

        self.assertEqual(act.answers[0].answer, 'lou,tom,andy,aaron')
        self.do_activity_definition_correctResponsePattern_model(rspPK, ['lou,tom,andy,aaron'])

        #Test object step values
        self.assertEqual(act.choices[0].choice_id, 'lou')
        self.assertEqual(act.choices[0].description, '{"en-US": "Lou"}')

        self.assertEqual(act.choices[1].choice_id, 'tom')
        self.assertEqual(act.choices[1].description, '{"en-US": "Tom"}')
        
        self.assertEqual(act.choices[2].choice_id, 'andy')
        self.assertEqual(act.choices[2].description, '{"en-US": "Andy"}')

        self.assertEqual(act.choices[3].choice_id, 'aaron')
        self.assertEqual(act.choices[3].description, '{"en-US": "Aaron"}')

        #Check model choice values
        clist = ['lou', 'tom', 'andy', 'aaron']
        dlist = ['{"en-US": "Lou"}','{"en-US": "Tom"}','{"en-US": "Andy"}', '{"en-US": "Aaron"}']
        self.do_actvity_definition_choices_model(defPK, clist, dlist)

    #Test activity with definition that is cmi.interaction and numeric interactionType
    def test_activity_definition_cmiInteraction_numeric(self):

        act = Activity.Activity(json.dumps({'objectType': 'Activity', 'id':'foom',
                'definition': {'name': 'testname2','description': 'testdesc2', 'type': 'cmi.interaction',
                'interactionType': 'numeric','correctResponsesPattern': ['4'],
                'extensions': {'key1': 'value1', 'key2': 'value2',
                'key3': 'value3'}}}))

        PK = models.activity.objects.filter(id=act.activity.id)
        defPK = models.activity_definition.objects.filter(activity=PK)
        rspPK = models.activity_def_correctresponsespattern.objects.filter(activity_definition=defPK)

        self.do_activity_object(act, 'foom', 'Activity')
        self.do_activity_model(act.activity.id, 'foom', 'Activity')

        self.do_activity_definition_object(act, 'testname2', 'testdesc2', 'cmi.interaction', 'numeric')        
        self.do_activity_definition_model(PK, 'testname2', 'testdesc2', 'cmi.interaction', 'numeric')

        self.do_activity_definition_extensions_object(act, 'key1', 'key2', 'key3', 'value1', 'value2', 'value3')
        self.do_activity_definition_extensions_model(defPK, 'key1', 'key2', 'key3', 'value1', 'value2', 'value3')

        self.do_activity_definition_correctResponsePattern_object(act, defPK, rspPK, '4')
        self.do_activity_definition_correctResponsePattern_model(rspPK, ['4'])

    #Test activity with definition that is cmi.interaction and other interactionType
    def test_activity_definition_cmiInteraction_other(self):

        act = Activity.Activity(json.dumps({'objectType': 'Activity', 'id': 'foon',
                'definition': {'name': 'testname2','description': 'testdesc2', 'type': 'cmi.interaction',
                'interactionType': 'other','correctResponsesPattern': ['(35.937432,-86.868896)'],
                'extensions': {'key1': 'value1', 'key2': 'value2',
                'key3': 'value3'}}}))

        PK = models.activity.objects.filter(id=act.activity.id)
        defPK = models.activity_definition.objects.filter(activity=PK)
        rspPK = models.activity_def_correctresponsespattern.objects.filter(activity_definition=defPK)

        self.do_activity_object(act, 'foon', 'Activity')
        self.do_activity_model(act.activity.id, 'foon', 'Activity')

        self.do_activity_definition_object(act, 'testname2', 'testdesc2', 'cmi.interaction', 'other')        
        self.do_activity_definition_model(PK, 'testname2', 'testdesc2', 'cmi.interaction', 'other')

        self.do_activity_definition_extensions_object(act, 'key1', 'key2', 'key3', 'value1', 'value2', 'value3')
        self.do_activity_definition_extensions_model(defPK, 'key1', 'key2', 'key3', 'value1', 'value2', 'value3')

        self.do_activity_definition_correctResponsePattern_object(act, defPK, rspPK, '(35.937432,-86.868896)')
        self.do_activity_definition_correctResponsePattern_model(rspPK, ['(35.937432,-86.868896)'])

class Models_ActorTest(py_tc):
    def test_actor(self):
        bob = Actor.Actor(json.dumps({'objectType':'Person','name':['bob'],'mbox':['bob@example.com']}),create=True)
        self.assertEqual(bob.agent.objectType, 'Person')
        self.assertIn('bob', bob.agent.agent_name_set.values_list('name', flat=True))
        self.assertIn('bob@example.com', bob.agent.agent_mbox_set.values_list('mbox', flat=True))

    def test_actor_merge(self):
        bob = Actor.Actor(json.dumps({'objectType':'Person','name':['bob'],'mbox':['bob@example.com']}),create=True)
        robert = Actor.Actor(json.dumps({'mbox':['bob@example.com','robert@example.com'],'name':['robert']}),create=True)
        names = robert.agent.agent_name_set.values_list('name', flat=True)
        mboxes = robert.agent.agent_mbox_set.values_list('mbox', flat=True)
        self.assertIn('robert', names)
        self.assertIn('bob', names)
        self.assertIn('robert@example.com', mboxes)
        self.assertIn('bob@example.com', mboxes)

    def test_actor_double_merge(self):
        bob = Actor.Actor(json.dumps({'objectType':'Person','name':['bob'],'mbox':['bob@example.com']}),create=True)
        robert = Actor.Actor(json.dumps({'mbox':['bob@example.com','robert@example.com'],'name':['robert']}),create=True)
        magicman = Actor.Actor(json.dumps({'mbox':['bob@example.com','robert@example.com','magicman@example.com'],'name':['magic man']}),create=True)
        names = magicman.agent.agent_name_set.values_list('name', flat=True)
        mboxes = magicman.agent.agent_mbox_set.values_list('mbox', flat=True)
        self.assertIn('robert', names)
        self.assertIn('bob', names)
        self.assertIn('magic man', names)
        self.assertIn('robert@example.com', mboxes)
        self.assertIn('bob@example.com', mboxes)
        self.assertIn('magicman@example.com', mboxes)

    def test_actor_double_merge_different_ifp(self):
        bob = Actor.Actor(json.dumps({'objectType':'Person','name':['bob'],'mbox':['bob@example.com']}),create=True)
        robert = Actor.Actor(json.dumps({'mbox':['bob@example.com','robert@example.com'],'openid':['bob@openid.com'],'name':['robert']}),create=True)
        magicman = Actor.Actor(json.dumps({'openid':['bob@openid.com','mgkmn@openid.com'], 'mbox':['magicman@example.com'], 'name':['magic man']}),create=True)
        names = magicman.agent.agent_name_set.values_list('name', flat=True)
        mboxes = magicman.agent.agent_mbox_set.values_list('mbox', flat=True)
        openids = magicman.agent.agent_openid_set.values_list('openid', flat=True)
        self.assertIn('robert', names)
        self.assertIn('bob', names)
        self.assertIn('magic man', names)
        self.assertIn('robert@example.com', mboxes)
        self.assertIn('bob@example.com', mboxes)
        self.assertIn('magicman@example.com', mboxes)
        self.assertIn('bob@openid.com', openids)
        self.assertIn('mgkmn@openid.com', openids)

    def test_actor_double_merge_different_ifp_with_person_stuff(self):
        bob = Actor.Actor(json.dumps({'objectType':'Person','name':['bob'],'mbox':['bob@example.com'], 'firstName':['bob', 'robert'], 'lastName':['tester']}),create=True)
        robert = Actor.Actor(json.dumps({'mbox':['bob@example.com','robert@example.com'],'openid':['bob@openid.com'],'name':['robert']}),create=True)
        magicman = Actor.Actor(json.dumps({'openid':['bob@openid.com','mgkmn@openid.com'], 'mbox':['magicman@example.com'], 'name':['magic man'], 'firstName':['magic']}),create=True)
        names = magicman.agent.agent_name_set.values_list('name', flat=True)
        mboxes = magicman.agent.agent_mbox_set.values_list('mbox', flat=True)
        openids = magicman.agent.agent_openid_set.values_list('openid', flat=True)
        firstNames = magicman.agent.person.person_firstname_set.values_list('firstName', flat=True)
        lastNames = magicman.agent.person.person_lastname_set.values_list('lastName', flat=True)
        self.assertIn('robert', names)
        self.assertIn('bob', names)
        self.assertIn('magic man', names)
        self.assertIn('robert@example.com', mboxes)
        self.assertIn('bob@example.com', mboxes)
        self.assertIn('magicman@example.com', mboxes)
        self.assertIn('bob@openid.com', openids)
        self.assertIn('mgkmn@openid.com', openids)
        self.assertIn('bob', firstNames)
        self.assertIn('robert', firstNames) 
        self.assertIn('magic', firstNames) 
        self.assertIn('tester', lastNames)

    def test_actor_agent_account(self):
        bob = Actor.Actor(json.dumps({'name':['bob'],'account':[{'accountName':'bobaccnt'}]}),create=True)
        self.assertIn('bob', bob.agent.agent_name_set.values_list('name', flat=True))
        self.assertIn('bobaccnt', bob.agent.agent_account_set.values_list('accountName', flat=True))

    def test_actor_agent_account_merge(self):
        bob = Actor.Actor(json.dumps({'name':['bob'],'account':[{'accountName':'bobaccnt'}]}),create=True)
        robert = Actor.Actor(json.dumps({'name':['robert'],'account':[{'accountName':'bobaccnt'}],'mbox':['robert@example.com']}),create=True)
        names = robert.agent.agent_name_set.values_list('name', flat=True)
        accounts = robert.agent.agent_account_set.values_list('accountName', flat=True)
        mboxs = robert.agent.agent_mbox_set.values_list('mbox', flat=True)
        self.assertIn('bob', names)
        self.assertIn('bobaccnt', accounts)
        self.assertIn('robert', names)
        self.assertIn('robert@example.com', mboxs)

    def test_actor_agent_account_double_merge(self):
        bob = Actor.Actor(json.dumps({'name':['bob'],'account':[{'accountName':'bobaccnt'}]}),create=True)
        robert = Actor.Actor(json.dumps({'name':['robert'],'account':[{'accountName':'robertaccnt'}],'mbox':['robert@example.com']}),create=True)
        magicman = Actor.Actor(json.dumps({'name':['magicman'],'account':[{'accountName':'magicman','accountServiceHomePage':'http://accounts.example.com'},{'accountName':'robertaccnt'},{'accountName':'bobaccnt'}]}),create=True)
        names = magicman.agent.agent_name_set.values_list('name', flat=True)
        accounts = magicman.agent.agent_account_set.values_list('accountName', flat=True)
        acchp = magicman.agent.agent_account_set.values_list('accountServiceHomePage', flat=True)
        mboxs = magicman.agent.agent_mbox_set.values_list('mbox', flat=True)
        self.assertIn('bob', names)
        self.assertIn('bobaccnt', accounts)
        self.assertIn('robert', names)
        self.assertIn('robert@example.com', mboxs)
        self.assertIn('magicman', names)
        self.assertIn('magicman', accounts)
        self.assertIn('http://accounts.example.com', acchp)

    def test_actor_agent_account_double_merge_extra_accounts(self):
        bob = Actor.Actor(json.dumps({'name':['bob'],'account':[{'accountName':'bobaccnt'},{'accountName':'otherbobaccnt','accountServiceHomePage':'http://otheraccounts.example.com'}]}),create=True)
        robert = Actor.Actor(json.dumps({'name':['robert'],'account':[{'accountName':'robertaccnt'}],'mbox':['robert@example.com']}),create=True)
        magicman = Actor.Actor(json.dumps({'name':['magicman'],'account':[{'accountName':'magicman','accountServiceHomePage':'http://accounts.example.com'},{'accountName':'robertaccnt'},{'accountName':'bobaccnt'}]}),create=True)
        names = magicman.agent.agent_name_set.values_list('name', flat=True)
        accounts = magicman.agent.agent_account_set.values_list('accountName', flat=True)
        acchp = magicman.agent.agent_account_set.values_list('accountServiceHomePage', flat=True)
        mboxs = magicman.agent.agent_mbox_set.values_list('mbox', flat=True)
        self.assertIn('bob', names)
        self.assertIn('bobaccnt', accounts)
        self.assertIn('otherbobaccnt', accounts)
        self.assertIn('http://otheraccounts.example.com', acchp)
        self.assertIn('robert', names)
        self.assertIn('robert@example.com', mboxs)
        self.assertIn('magicman', names)
        self.assertIn('magicman', accounts)
        self.assertIn('http://accounts.example.com', acchp)

    def test_actor_no_create(self):
        me = Actor.Actor(json.dumps({"name":["me"], "mbox":["mailto:me@example.com"]}))
        self.assertNotIn("me", me.get_name())
        me = Actor.Actor(json.dumps({"name":["me"], "mbox":["mailto:me@example.com"]}),create=True)
        self.assertIn("me", me.get_name())
        self.assertIn("mailto:me@example.com", me.get_mbox())
        anotherme = Actor.Actor(json.dumps({"mbox":["mailto:me@example.com","mailto:anotherme@example.com"]}))
        self.assertIn("me", me.get_name())
        self.assertIn("mailto:me@example.com", me.get_mbox())
        self.assertNotIn("mailto:anotherme@example.com", me.get_mbox())
