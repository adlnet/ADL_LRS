from django.test import TestCase
from django.test.utils import setup_test_environment
from django.core.urlresolvers import reverse
from lrs import models, views, objects
import json
import time
import datetime
from django.utils.timezone import utc
import hashlib
from unittest import TestCase as py_tc
from django.core.exceptions import ValidationError, ObjectDoesNotExist
import urllib

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
    this_url = reverse(views.activity_state)
    actor = {"name":["me"],"mbox":["mailto:me@example.com"]}
    activityId = "http://example.com/activities/"
    stateId = "the_state_id"
    x_www_form = 'application/x-www-form-urlencoded'
    registrationId = "some_sort_of_reg_id"
    def test_put(self):
        actor = self.actor
        activityId = self.activityId + "test_put"
        stateId = self.stateId 
        params = {"actor":actor, "activityId":activityId, "stateId":stateId}
        response = self.client.put(self.this_url, params,content_type=self.x_www_form)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, actor['name'][0])
        self.assertContains(response, actor['mbox'][0])
        self.assertContains(response, activityId)
        self.assertContains(response, stateId)
     
    def test_put_with_registrationId(self):
        actor = self.actor
        activityId = self.activityId + "test_put_with_registrationId"
        stateId = self.stateId 
        regId = self.registrationId
        params = {"actor":actor, "activityId":activityId, "stateId":stateId, "registrationId":regId}
        response = self.client.put(self.this_url, params,content_type=self.x_www_form)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, actor['name'][0])
        self.assertContains(response, actor['mbox'][0])
        self.assertContains(response, activityId)
        self.assertContains(response, stateId)
        self.assertContains(response, regId)
        

    def test_put_without_activityid(self):
        actor = self.actor
        stateId = "test_put_without_activityid" 
        params = {"actor":actor, "stateId":stateId}
        response = self.client.put(self.this_url, params,content_type=self.x_www_form)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Error')
        self.assertContains(response, 'activityId parameter is missing')
    
    def test_put_without_actor(self):
        activityId = self.activityId + "test_put_without_actor"
        stateId = self.stateId 
        params = {"activityId":activityId, "stateId":stateId}
        response = self.client.put(self.this_url, params,content_type=self.x_www_form)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Error')
        self.assertContains(response, 'actor parameter is missing')
    
    def test_put_without_stateid(self):
        actor = self.actor
        activityId = self.activityId + "test_put_without_stateid"
        params = {"actor":actor, "activityId":activityId}
        response = self.client.put(self.this_url, params,content_type=self.x_www_form)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Error')
        self.assertContains(response, 'stateId parameter is missing')
    
    def test_get(self):
        actor = self.actor
        activityId = self.activityId + "test_get"
        stateId = self.stateId 
        params = {"actor":actor, "activityId":activityId, "stateId":stateId}
        response = self.client.get(self.this_url, params,content_type=self.x_www_form)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, actor['name'][0])
        self.assertContains(response, actor['mbox'][0])
        self.assertContains(response, activityId)
        self.assertContains(response, stateId)
        resp_hash = hashlib.sha1(response.content).hexdigest()
        self.assertEqual(response['ETag'], resp_hash)
     
    def test_get_with_registrationId(self):
        actor = self.actor
        activityId = self.activityId + "test_get_with_registrationId"
        stateId = self.stateId 
        regId = self.registrationId
        params = {"actor":actor, "activityId":activityId, "stateId":stateId, "registrationId":regId}
        response = self.client.get(self.this_url, params,content_type=self.x_www_form)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, actor['name'][0])
        self.assertContains(response, actor['mbox'][0])
        self.assertContains(response, activityId)
        self.assertContains(response, stateId)
        self.assertContains(response, regId)
        resp_hash = hashlib.sha1(response.content).hexdigest()
        self.assertEqual(response['ETag'], resp_hash)
        
    def test_get_with_since(self):
        actor = self.actor
        activityId = self.activityId + "test_get_with_since"
        since = time.time()
        params = {"actor":actor, "activityId":activityId, "since":since}
        response = self.client.get(self.this_url, params,content_type=self.x_www_form)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, actor['name'][0])
        self.assertContains(response, actor['mbox'][0])
        self.assertContains(response, activityId)
        self.assertContains(response, since)
        resp_hash = hashlib.sha1(response.content).hexdigest()
        self.assertEqual(response['ETag'], resp_hash)
        
    def test_get_with_since_and_regid(self):
        actor = self.actor
        activityId = self.activityId + "test_get_with_since_and_regid"
        stateId = self.stateId 
        since = time.time()
        regId = self.registrationId
        params = {"actor":actor, "activityId":activityId, "since":since, "registrationId":regId}
        response = self.client.get(self.this_url, params,content_type=self.x_www_form)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, actor['name'][0])
        self.assertContains(response, actor['mbox'][0])
        self.assertContains(response, activityId)
        self.assertContains(response, since)
        self.assertContains(response, regId)
        resp_hash = hashlib.sha1(response.content).hexdigest()
        self.assertEqual(response['ETag'], resp_hash)
        
    def test_get_without_activityid(self):
        actor = self.actor
        stateId = "test_get_without_activityid" 
        params = {"actor":actor, "stateId":stateId}
        response = self.client.get(self.this_url, params,content_type=self.x_www_form)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Error')
        self.assertContains(response, 'activityId parameter is missing')
    
    def test_get_without_actor(self):
        activityId = self.activityId + "test_get_without_actor"
        stateId = self.stateId 
        params = {"activityId":activityId, "stateId":stateId}
        response = self.client.get(self.this_url, params,content_type=self.x_www_form)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Error')
        self.assertContains(response, 'actor parameter is missing')
    
    def test_get_without_stateid(self):
        actor = self.actor
        activityId = self.activityId + "test_get_without_stateid"
        params = {"actor":actor, "activityId":activityId}
        response = self.client.get(self.this_url, params,content_type=self.x_www_form)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Success')
        self.assertContains(response, actor['name'][0])
        self.assertContains(response, actor['mbox'][0])
        self.assertContains(response, activityId)
        resp_hash = hashlib.sha1(response.content).hexdigest()
        self.assertEqual(response['ETag'], resp_hash)
    
    def test_delete(self):
        actor = self.actor
        activityId = self.activityId + "test_delete"
        stateId = self.stateId 
        params = {"actor":actor, "activityId":activityId, "stateId":stateId}
        response = self.client.delete(self.this_url, params,content_type=self.x_www_form)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, actor['name'][0])
        self.assertContains(response, actor['mbox'][0])
        self.assertContains(response, activityId)
        self.assertContains(response, stateId)
     
    def test_delete_with_registrationId(self):
        actor = self.actor
        activityId = self.activityId + "test_delete_with_registrationId"
        stateId = self.stateId 
        regId = self.registrationId
        params = {"actor":actor, "activityId":activityId, "stateId":stateId, "registrationId":regId}
        response = self.client.delete(self.this_url, params,content_type=self.x_www_form)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, actor['name'][0])
        self.assertContains(response, actor['mbox'][0])
        self.assertContains(response, activityId)
        self.assertContains(response, stateId)
        self.assertContains(response, regId)
        
    def test_delete_without_activityid(self):
        actor = self.actor
        stateId = "test_delete_without_activityid" 
        params = {"actor":actor, "stateId":stateId}
        response = self.client.delete(self.this_url, params,content_type=self.x_www_form)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Error')
        self.assertContains(response, 'activityId parameter is missing')
    
    def test_delete_without_actor(self):
        activityId = self.activityId + "test_delete_without_actor"
        stateId = self.stateId 
        params = {"activityId":activityId, "stateId":stateId}
        response = self.client.delete(self.this_url, params,content_type=self.x_www_form)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Error')
        self.assertContains(response, 'actor parameter is missing')
    
    def test_delete_without_stateid(self):
        actor = self.actor
        activityId = self.activityId + "test_delete_without_stateid"
        params = {"actor":actor, "activityId":activityId}
        response = self.client.delete(self.this_url, params,content_type=self.x_www_form)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Success')
        self.assertContains(response, actor['name'][0])
        self.assertContains(response, actor['mbox'][0])
        self.assertContains(response, activityId)
    
        
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
        self.assertEqual(r.status_code, 200)

        r = self.client.get(reverse(views.actor_profile), params)
        self.assertEqual(r.status_code, 400)

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
        me = objects.Actor(actor,create=True)
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

    def do_activity_object(self,act, act_id, objType):
        self.assertEqual(act.activity.activity_id, act_id)
        self.assertEqual(act.activity.objectType, objType)
        
    def do_activity_model(self,act_id, objType):
        self.assertEqual(models.activity.objects.get(activity_id=act_id).objectType, objType)
        self.assertEqual(models.activity.objects.get(activity_id=act_id).activity_id, act_id)

    def do_activity_definition_object(self, act, name, desc, course, intType):
        self.assertEqual(act.activity.activity_definition.name, name)
        self.assertEqual(act.activity.activity_definition.description, desc)
        self.assertEqual(act.activity.activity_definition.activity_definition_type, course)
        self.assertEqual(act.activity.activity_definition.interactionType, intType)

    def do_activity_definition_model(self, PK, testname, testdesc, course, intType):
        self.assertEqual(models.activity_definition.objects.get(activity=PK).name, testname)
        self.assertEqual(models.activity_definition.objects.get(activity=PK).description, testdesc)
        self.assertEqual(models.activity_definition.objects.get(activity=PK).activity_definition_type, course)
        self.assertEqual(models.activity_definition.objects.get(activity=PK).interactionType, intType)

    def do_activity_definition_extensions_object(self, act, key1, key2, key3, value1, value2, value3):
        self.assertEqual(act.activity_definition_extensions[0].key, key3)
        self.assertEqual(act.activity_definition_extensions[1].key, key2)
        self.assertEqual(act.activity_definition_extensions[2].key, key1)

        self.assertEqual(act.activity_definition_extensions[0].value, value3)    
        self.assertEqual(act.activity_definition_extensions[1].value, value2)
        self.assertEqual(act.activity_definition_extensions[2].value, value1)        

    def do_activity_definition_extensions_model(self, defPK, key1, key2, key3, value1, value2, value3):
        #Create list comprehesions to easier assess keys and values
        extList = models.activity_extentions.objects.values_list().filter(activity_definition=defPK)
        extKeys = [ext[1] for ext in extList]
        extVals = [ext[2] for ext in extList]

        self.assertIn('key1', extKeys)
        self.assertIn('key2', extKeys)
        self.assertIn('key3', extKeys)
        self.assertIn('value1', extVals)
        self.assertIn('value2', extVals)
        self.assertIn('value3', extVals)

    def do_activity_definition_correctResponsePattern_object(self, act, defPK, rspPK, answer):
        self.assertEqual(act.correctResponsesPattern.activity_definition, defPK)
        self.assertEqual(rspPK.activity_definition, defPK)
        self.assertEqual(act.answers[0].answer, answer)

    def do_activity_definition_correctResponsePattern_model(self, rspPK, answers):
        rspAnswers = models.correctresponsespattern_answer.objects.values_list('answer', flat=True).filter(correctresponsespattern=rspPK)
        
        for answer in answers:
            self.assertIn(answer,rspAnswers)

    def do_actvity_definition_choices_model(self, defPK, clist, dlist):
        descs = models.activity_definition_choices.objects.values_list('description', flat=True).filter(activity_definition=defPK)
        choices = models.activity_definition_choices.objects.values_list('choice_id', flat=True).filter(activity_definition=defPK)
        
        for c in clist:
            self.assertIn(c,choices)

        for d in dlist:
            self.assertIn(d, descs)

    def test_activity(self):
        #Test basic activity
        act = objects.Activity(json.dumps({'objectType':'Activity', 'id':'http://tincanapi.wikispaces.com/', }))
        
        self.do_activity_object(act,'http://tincanapi.wikispaces.com/','Activity')
        self.do_activity_model('http://tincanapi.wikispaces.com/', 'Activity')
    
    def test_activity_not_json(self):
        #Given wrong data format
        self.assertRaises(Exception, objects.Activity,"This string should throw exception since it's not JSON")

    def test_activity_no_objectType(self):
        #Not given an objectType
        act = objects.Activity(json.dumps({'id':'http://tincanapi.wikispaces.com/Tin+Can+API+Specification'}))
        
        self.do_activity_object(act,'http://tincanapi.wikispaces.com/Tin+Can+API+Specification', None)
        self.do_activity_model('http://tincanapi.wikispaces.com/Tin+Can+API+Specification', None)

    def test_activity_wrong_objectType(self):
        #Given invalid objectType
        act = objects.Activity(json.dumps({'id': 'http://tincanapi.wikispaces.com/Best+Practices', 'objectType':'Wrong'}))    

        self.do_activity_object(act,'http://tincanapi.wikispaces.com/Best+Practices', 'Activity')
        self.do_activity_model('http://tincanapi.wikispaces.com/Best+Practices', 'Activity')

    def test_activity_invalid_activity_id(self):
        #Given URL that doesn't resolve
        self.assertRaises(ValidationError, objects.Activity, json.dumps({'id': 'http://foo', 'objectType':'Activity'}))

    def test_activity_definition(self):
        #Test activity with definition - must retrieve activity object in order to test definition from DB
        act = objects.Activity(json.dumps({'objectType': 'Activity', 'id':'http://tincanapi.wikispaces.com/TinCan+Use+Cases',
                'definition': {'name': 'testname','description': 'testdesc', 'type': 'course',
                'interactionType': 'intType'}}))

        PK = models.activity.objects.get(activity_id=act.activity.activity_id)
        
        self.do_activity_object(act,'http://tincanapi.wikispaces.com/TinCan+Use+Cases', 'Activity')
        self.do_activity_definition_object(act, 'testname', 'testdesc', 'course', 'intType')
        self.do_activity_model('http://tincanapi.wikispaces.com/TinCan+Use+Cases', 'Activity')        
        self.do_activity_definition_model(PK, 'testname', 'testdesc', 'course', 'intType')

    def test_activity_definition_wrong_type(self):
        #Given wrong type
        self.assertRaises(Exception, objects.Activity, json.dumps({'objectType': 'Activity',
                'id':'http://tincanapi.wikispaces.com/Wish+List','definition': {'NAME': 'testname',
                'descripTION': 'testdesc', 'tYpe': 'wrong','interactionType': 'intType'}}))

        self.assertRaises(models.activity.DoesNotExist, models.activity.objects.get, activity_id='http://tincanapi.wikispaces.com/Wish+List')
    
    def test_activity_definition_required_fields(self):
        #Missing name in definition
        self.assertRaises(Exception, objects.Activity, json.dumps({'objectType': 'Activity',
                'id':'http://google.com','definition': {'description': 'testdesc',
                'type': 'wrong','interactionType': 'intType'}}))

        self.assertRaises(models.activity.DoesNotExist, models.activity.objects.get, activity_id='http://google.com')

    def test_activity_definition_extensions(self):
        #Test extensions - need to retrieve activity and activity definition objects in order to test extenstions
        act = objects.Activity(json.dumps({'objectType': 'Activity', 'id':'http://tincanapi.wikispaces.com/Verbs+and+Activities',
                'definition': {'name': 'testname2','description': 'testdesc2', 'type': 'course',
                'interactionType': 'intType2', 'extensions': {'key1': 'value1', 'key2': 'value2',
                'key3': 'value3'}}}))

        PK = models.activity.objects.get(activity_id=act.activity.activity_id)
        defPK = models.activity_definition.objects.get(activity=PK)

        self.do_activity_object(act,'http://tincanapi.wikispaces.com/Verbs+and+Activities', 'Activity')
        self.do_activity_definition_object(act, 'testname2', 'testdesc2', 'course', 'intType2')
        
        self.do_activity_model('http://tincanapi.wikispaces.com/Verbs+and+Activities', 'Activity')        
        self.do_activity_definition_model(PK, 'testname2', 'testdesc2', 'course', 'intType2')

        self.do_activity_definition_extensions_object(act, 'key1', 'key2', 'key3', 'value1', 'value2', 'value3')
        self.do_activity_definition_extensions_model(defPK, 'key1', 'key2', 'key3', 'value1', 'value2', 'value3')

    def test_activity_definition_wrong_interactionType(self):
        #Should fail because of invalid interactionType
        self.assertRaises(Exception, objects.Activity, json.dumps({'objectType': 'Activity', 'id':'http://linkedin.com',
                'definition': {'name': 'testname2','description': 'testdesc2', 'type': 'cmi.interaction',
                'interactionType': 'intType2', 'correctResponsesPatteRN': 'response', 'extensions': {'key1': 'value1', 'key2': 'value2',
                'key3': 'value3'}}}))
     
        self.assertRaises(models.activity.DoesNotExist, models.activity.objects.get, activity_id='http://linkedin.com')

    def test_activity_definition_no_correctResponsesPattern(self):
        #If it has a valid interactionType it must also provide the correctResponsesPattern field
        self.assertRaises(Exception, objects.Activity, json.dumps({'objectType': 'Activity', 'id':'http://msn.com',
                'definition': {'name': 'testname2','description': 'testdesc2', 'type': 'cmi.interaction',
                'interactionType': 'true-false', 'extensions': {'key1': 'value1', 'key2': 'value2',
                'key3': 'value3'}}}))
     
        self.assertRaises(models.activity.DoesNotExist, models.activity.objects.get, activity_id='http://msn.com')

    
    def test_activity_definition_cmiInteraction_true_false(self):
        act = objects.Activity(json.dumps({'objectType': 'Activity', 'id':'http://www.vmware.com/',
                'definition': {'name': 'testname2','description': 'testdesc2', 'type': 'cmi.interaction',
                'interactionType': 'true-false','correctResponsesPattern': ['true'] ,'extensions': {'key1': 'value1', 'key2': 'value2',
                'key3': 'value3'}}}))

        PK = models.activity.objects.get(activity_id=act.activity.activity_id)
        defPK = models.activity_definition.objects.get(activity=PK)
        rspPK = models.activity_def_correctresponsespattern.objects.get(activity_definition=defPK)

        self.do_activity_object(act,'http://www.vmware.com/', 'Activity')
        self.do_activity_definition_object(act, 'testname2', 'testdesc2', 'cmi.interaction', 'true-false')
        
        self.do_activity_model('http://www.vmware.com/', 'Activity')        
        self.do_activity_definition_model(PK, 'testname2', 'testdesc2', 'cmi.interaction', 'true-false')

        self.do_activity_definition_extensions_object(act, 'key1', 'key2', 'key3', 'value1', 'value2', 'value3')
        self.do_activity_definition_extensions_model(defPK, 'key1', 'key2', 'key3', 'value1', 'value2', 'value3')

        self.do_activity_definition_correctResponsePattern_object(act, defPK, rspPK, 'true')
        self.do_activity_definition_correctResponsePattern_model(rspPK, ['true'])
    
    def test_activity_definition_cmiInteraction_multiple_choice(self):    
        act = objects.Activity(json.dumps({'objectType': 'Activity', 'id':'http://facebook.com',
                'definition': {'name': 'testname2','description': 'testdesc2', 'type': 'cmi.interaction',
                'interactionType': 'multiple-choice','correctResponsesPattern': ['golf', 'tetris'],
                'choices':[{'id': 'golf', 'description': {'en-US':'Golf Example'}},{'id': 'tetris',
                'description':{'en-US': 'Tetris Example'}}, {'id':'facebook', 'description':{'en-US':'Facebook App'}},
                {'id':'scrabble', 'description': {'en-US': 'Scrabble Example'}}],
                'extensions': {'key1': 'value1', 'key2': 'value2',
                'key3': 'value3'}}}))

        PK = models.activity.objects.get(activity_id=act.activity.activity_id)
        defPK = models.activity_definition.objects.get(activity=PK)
        rspPK = models.activity_def_correctresponsespattern.objects.get(activity_definition=defPK)

        self.do_activity_object(act,'http://facebook.com', 'Activity')
        self.do_activity_model('http://facebook.com', 'Activity')

        self.do_activity_definition_object(act, 'testname2', 'testdesc2', 'cmi.interaction', 'multiple-choice')        
        self.do_activity_definition_model(PK, 'testname2', 'testdesc2', 'cmi.interaction', 'multiple-choice')

        self.do_activity_definition_extensions_object(act, 'key1', 'key2', 'key3', 'value1', 'value2', 'value3')
        self.do_activity_definition_extensions_model(defPK, 'key1', 'key2', 'key3', 'value1', 'value2', 'value3')

        #Need to rewrite do_activity_definition_correctResponsePattern_object to accept multiple values
        #This works for now
        self.assertEqual(act.answers[0].answer, 'golf')
        self.assertEqual(act.answers[1].answer, 'tetris')
        #self.do_activity_definition_correctResponsePattern_object(act, defPK, rspPK, ['golf', 'tetris'])
        self.do_activity_definition_correctResponsePattern_model(rspPK, ['golf', 'tetris'])

        #Need to create function to test object choice values, but this works
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
        
    
    def test_activity_definition_cmiInteraction_multiple_choice_no_choices(self):
        self.assertRaises(Exception, objects.Activity, json.dumps({'objectType': 'Activity', 'id':'http://youtube.com',
                'definition': {'name': 'testname2','description': 'testdesc2', 'type': 'cmi.interaction',
                'interactionType': 'multiple-choice','correctResponsesPattern': ['golf', 'tetris'],
                'extensions': {'key1': 'value1', 'key2': 'value2',
                'key3': 'value3'}}}))   

        self.assertRaises(models.activity.DoesNotExist, models.activity.objects.get, activity_id='http://youtube.com')
    '''
    def test_activity_definition_cmiInteraction_likert(self):    
        act = objects.Activity(json.dumps({'objectType': 'Activity', 'id':'http://adlnet.gov/resources',
                'definition': {'name': 'testname2','description': 'testdesc2', 'type': 'cmi.interaction',
                'interactionType': 'likert','correctResponsesPattern': ['likert_3'],
                'choices':[{'id': 'golf', 'description': {'en-US':'Golf Example'}},{'id': 'tetris',
                'description':{'en-US': 'Tetris Example'}}],
                'extensions': {'key1': 'value1', 'key2': 'value2',
                'key3': 'value3'}}}))

        PK = models.activity.objects.get(activity_id=act.activity.activity_id)
        defPK = models.activity_definition.objects.get(activity=PK)
        rspPK = models.activity_def_correctresponsespattern.objects.get(activity_definition=defPK)

        self.do_activity_object(act,'http://adlnet.gov/resources', 'Activity')
        self.do_activity_model('http://adlnet.gov/resources', 'Activity')

        self.do_activity_definition_object(act, 'testname2', 'testdesc2', 'cmi.interaction', 'likert')        
        self.do_activity_definition_model(PK, 'testname2', 'testdesc2', 'cmi.interaction', 'likert')

        self.do_activity_definition_extensions_object(act, 'key1', 'key2', 'key3', 'value1', 'value2', 'value3')
        self.do_activity_definition_extensions_model(defPK, 'key1', 'key2', 'key3', 'value1', 'value2', 'value3')

        #self.do_activity_definition_correctResponsePattern_object(act, defPK, rspPK, ['golf', 'tetris'])
        self.do_activity_definition_correctResponsePattern_model(rspPK, ['golf', 'tetris'])

        #Need to rewrite do_activity_definition_correctResponsePattern_object to accept multiple values
        #This works for now
        self.assertEqual(act.answers[0].answer, 'golf')
        self.assertEqual(act.answers[1].answer, 'tetris')
    '''
    def test_activity_definition_cmiInteraction_fill_in(self):
        act = objects.Activity(json.dumps({'objectType': 'Activity', 'id':'http://twitter.com',
                'definition': {'name': 'testname2','description': 'testdesc2', 'type': 'cmi.interaction',
                'interactionType': 'fill-in','correctResponsesPattern': ['Fill in answer'],
                'extensions': {'key1': 'value1', 'key2': 'value2',
                'key3': 'value3'}}}))

        PK = models.activity.objects.get(activity_id=act.activity.activity_id)
        defPK = models.activity_definition.objects.get(activity=PK)
        rspPK = models.activity_def_correctresponsespattern.objects.get(activity_definition=defPK)

        self.do_activity_object(act,'http://twitter.com', 'Activity')
        self.do_activity_model('http://twitter.com', 'Activity')

        self.do_activity_definition_object(act, 'testname2', 'testdesc2', 'cmi.interaction', 'fill-in')        
        self.do_activity_definition_model(PK, 'testname2', 'testdesc2', 'cmi.interaction', 'fill-in')

        self.do_activity_definition_extensions_object(act, 'key1', 'key2', 'key3', 'value1', 'value2', 'value3')
        self.do_activity_definition_extensions_model(defPK, 'key1', 'key2', 'key3', 'value1', 'value2', 'value3')

        self.do_activity_definition_correctResponsePattern_object(act, defPK, rspPK, 'Fill in answer')
        self.do_activity_definition_correctResponsePattern_model(rspPK, ['Fill in answer'])

    def test_activity_definition_cmiInteraction_long_fill_in(self):
        act = objects.Activity(json.dumps({'objectType': 'Activity', 'id':'http://yahoo.com',
                'definition': {'name': 'testname2','description': 'testdesc2', 'type': 'cmi.interaction',
                'interactionType': 'fill-in','correctResponsesPattern': ['Long fill in answer'],
                'extensions': {'key1': 'value1', 'key2': 'value2',
                'key3': 'value3'}}}))

        PK = models.activity.objects.get(activity_id=act.activity.activity_id)
        defPK = models.activity_definition.objects.get(activity=PK)
        rspPK = models.activity_def_correctresponsespattern.objects.get(activity_definition=defPK)

        self.do_activity_object(act,'http://yahoo.com', 'Activity')
        self.do_activity_model('http://yahoo.com', 'Activity')

        self.do_activity_definition_object(act, 'testname2', 'testdesc2', 'cmi.interaction', 'fill-in')        
        self.do_activity_definition_model(PK, 'testname2', 'testdesc2', 'cmi.interaction', 'fill-in')

        self.do_activity_definition_extensions_object(act, 'key1', 'key2', 'key3', 'value1', 'value2', 'value3')
        self.do_activity_definition_extensions_model(defPK, 'key1', 'key2', 'key3', 'value1', 'value2', 'value3')

        self.do_activity_definition_correctResponsePattern_object(act, defPK, rspPK, 'Long fill in answer')
        self.do_activity_definition_correctResponsePattern_model(rspPK, ['Long fill in answer'])

    def test_activity_definition_cmiInteraction_numeric(self):
        act = objects.Activity(json.dumps({'objectType': 'Activity', 'id':'http://ebay.com',
                'definition': {'name': 'testname2','description': 'testdesc2', 'type': 'cmi.interaction',
                'interactionType': 'numeric','correctResponsesPattern': ['4'],
                'extensions': {'key1': 'value1', 'key2': 'value2',
                'key3': 'value3'}}}))

        PK = models.activity.objects.get(activity_id=act.activity.activity_id)
        defPK = models.activity_definition.objects.get(activity=PK)
        rspPK = models.activity_def_correctresponsespattern.objects.get(activity_definition=defPK)

        self.do_activity_object(act,'http://ebay.com', 'Activity')
        self.do_activity_model('http://ebay.com', 'Activity')

        self.do_activity_definition_object(act, 'testname2', 'testdesc2', 'cmi.interaction', 'numeric')        
        self.do_activity_definition_model(PK, 'testname2', 'testdesc2', 'cmi.interaction', 'numeric')

        self.do_activity_definition_extensions_object(act, 'key1', 'key2', 'key3', 'value1', 'value2', 'value3')
        self.do_activity_definition_extensions_model(defPK, 'key1', 'key2', 'key3', 'value1', 'value2', 'value3')

        self.do_activity_definition_correctResponsePattern_object(act, defPK, rspPK, '4')
        self.do_activity_definition_correctResponsePattern_model(rspPK, ['4'])

    def test_activity_definition_cmiInteraction_other(self):
        act = objects.Activity(json.dumps({'objectType': 'Activity', 'id':'http://amazon.com',
                'definition': {'name': 'testname2','description': 'testdesc2', 'type': 'cmi.interaction',
                'interactionType': 'other','correctResponsesPattern': ['(35.937432,-86.868896)'],
                'extensions': {'key1': 'value1', 'key2': 'value2',
                'key3': 'value3'}}}))

        PK = models.activity.objects.get(activity_id=act.activity.activity_id)
        defPK = models.activity_definition.objects.get(activity=PK)
        rspPK = models.activity_def_correctresponsespattern.objects.get(activity_definition=defPK)

        self.do_activity_object(act,'http://amazon.com', 'Activity')
        self.do_activity_model('http://amazon.com', 'Activity')

        self.do_activity_definition_object(act, 'testname2', 'testdesc2', 'cmi.interaction', 'other')        
        self.do_activity_definition_model(PK, 'testname2', 'testdesc2', 'cmi.interaction', 'other')

        self.do_activity_definition_extensions_object(act, 'key1', 'key2', 'key3', 'value1', 'value2', 'value3')
        self.do_activity_definition_extensions_model(defPK, 'key1', 'key2', 'key3', 'value1', 'value2', 'value3')

        self.do_activity_definition_correctResponsePattern_object(act, defPK, rspPK, '(35.937432,-86.868896)')
        self.do_activity_definition_correctResponsePattern_model(rspPK, ['(35.937432,-86.868896)'])





class Models_ActorTest(py_tc):
    def test_actor(self):
        bob = objects.Actor(json.dumps({'objectType':'Person','name':['bob'],'mbox':['bob@example.com']}),create=True)
        self.assertEqual(bob.agent.objectType, 'Person')
        self.assertIn('bob', bob.agent.agent_name_set.values_list('name', flat=True))
        self.assertIn('bob@example.com', bob.agent.agent_mbox_set.values_list('mbox', flat=True))

    def test_actor_merge(self):
        bob = objects.Actor(json.dumps({'objectType':'Person','name':['bob'],'mbox':['bob@example.com']}),create=True)
        robert = objects.Actor(json.dumps({'mbox':['bob@example.com','robert@example.com'],'name':['robert']}),create=True)
        names = robert.agent.agent_name_set.values_list('name', flat=True)
        mboxes = robert.agent.agent_mbox_set.values_list('mbox', flat=True)
        self.assertIn('robert', names)
        self.assertIn('bob', names)
        self.assertIn('robert@example.com', mboxes)
        self.assertIn('bob@example.com', mboxes)

    def test_actor_double_merge(self):
        bob = objects.Actor(json.dumps({'objectType':'Person','name':['bob'],'mbox':['bob@example.com']}),create=True)
        robert = objects.Actor(json.dumps({'mbox':['bob@example.com','robert@example.com'],'name':['robert']}),create=True)
        magicman = objects.Actor(json.dumps({'mbox':['bob@example.com','robert@example.com','magicman@example.com'],'name':['magic man']}),create=True)
        names = magicman.agent.agent_name_set.values_list('name', flat=True)
        mboxes = magicman.agent.agent_mbox_set.values_list('mbox', flat=True)
        self.assertIn('robert', names)
        self.assertIn('bob', names)
        self.assertIn('magic man', names)
        self.assertIn('robert@example.com', mboxes)
        self.assertIn('bob@example.com', mboxes)
        self.assertIn('magicman@example.com', mboxes)

    def test_actor_double_merge_different_ifp(self):
        bob = objects.Actor(json.dumps({'objectType':'Person','name':['bob'],'mbox':['bob@example.com']}),create=True)
        robert = objects.Actor(json.dumps({'mbox':['bob@example.com','robert@example.com'],'openid':['bob@openid.com'],'name':['robert']}),create=True)
        magicman = objects.Actor(json.dumps({'openid':['bob@openid.com','mgkmn@openid.com'], 'mbox':['magicman@example.com'], 'name':['magic man']}),create=True)
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
        bob = objects.Actor(json.dumps({'objectType':'Person','name':['bob'],'mbox':['bob@example.com'], 'firstName':['bob', 'robert'], 'lastName':['tester']}),create=True)
        robert = objects.Actor(json.dumps({'mbox':['bob@example.com','robert@example.com'],'openid':['bob@openid.com'],'name':['robert']}),create=True)
        magicman = objects.Actor(json.dumps({'openid':['bob@openid.com','mgkmn@openid.com'], 'mbox':['magicman@example.com'], 'name':['magic man'], 'firstName':['magic']}),create=True)
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
        bob = objects.Actor(json.dumps({'name':['bob'],'account':[{'accountName':'bobaccnt'}]}),create=True)
        self.assertIn('bob', bob.agent.agent_name_set.values_list('name', flat=True))
        self.assertIn('bobaccnt', bob.agent.agent_account_set.values_list('accountName', flat=True))

    def test_actor_agent_account_merge(self):
        bob = objects.Actor(json.dumps({'name':['bob'],'account':[{'accountName':'bobaccnt'}]}),create=True)
        robert = objects.Actor(json.dumps({'name':['robert'],'account':[{'accountName':'bobaccnt'}],'mbox':['robert@example.com']}),create=True)
        names = robert.agent.agent_name_set.values_list('name', flat=True)
        accounts = robert.agent.agent_account_set.values_list('accountName', flat=True)
        mboxs = robert.agent.agent_mbox_set.values_list('mbox', flat=True)
        self.assertIn('bob', names)
        self.assertIn('bobaccnt', accounts)
        self.assertIn('robert', names)
        self.assertIn('robert@example.com', mboxs)

    def test_actor_agent_account_double_merge(self):
        bob = objects.Actor(json.dumps({'name':['bob'],'account':[{'accountName':'bobaccnt'}]}),create=True)
        robert = objects.Actor(json.dumps({'name':['robert'],'account':[{'accountName':'robertaccnt'}],'mbox':['robert@example.com']}),create=True)
        magicman = objects.Actor(json.dumps({'name':['magicman'],'account':[{'accountName':'magicman','accountServiceHomePage':'http://accounts.example.com'},{'accountName':'robertaccnt'},{'accountName':'bobaccnt'}]}),create=True)
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
        bob = objects.Actor(json.dumps({'name':['bob'],'account':[{'accountName':'bobaccnt'},{'accountName':'otherbobaccnt','accountServiceHomePage':'http://otheraccounts.example.com'}]}),create=True)
        robert = objects.Actor(json.dumps({'name':['robert'],'account':[{'accountName':'robertaccnt'}],'mbox':['robert@example.com']}),create=True)
        magicman = objects.Actor(json.dumps({'name':['magicman'],'account':[{'accountName':'magicman','accountServiceHomePage':'http://accounts.example.com'},{'accountName':'robertaccnt'},{'accountName':'bobaccnt'}]}),create=True)
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
        me = objects.Actor(json.dumps({"name":["me"], "mbox":["mailto:me@example.com"]}))
        self.assertNotIn("me", me.get_name())
        me = objects.Actor(json.dumps({"name":["me"], "mbox":["mailto:me@example.com"]}),create=True)
        self.assertIn("me", me.get_name())
        self.assertIn("mailto:me@example.com", me.get_mbox())
        anotherme = objects.Actor(json.dumps({"mbox":["mailto:me@example.com","mailto:anotherme@example.com"]}))
        self.assertIn("me", me.get_name())
        self.assertIn("mailto:me@example.com", me.get_mbox())
        self.assertNotIn("mailto:anotherme@example.com", me.get_mbox())
