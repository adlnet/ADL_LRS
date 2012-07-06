from django.test import TestCase
from django.core.urlresolvers import reverse
from lrs import models, views, objects
import json
import time
import hashlib
from unittest import TestCase as py_tc
from django.core.exceptions import ValidationError, ObjectDoesNotExist

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
        self.assertContains(response, 'method = POST')
        
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
    def test_put(self):
        response = self.client.put(reverse(views.actor_profile), {'actor':'bob','profileId':'10'},content_type='application/x-www-form-urlencoded')
        #print 'basic put test, line 43: %s' % response.content
        self.assertContains(response, 'Success')
        self.assertContains(response, 'bob')
        self.assertContains(response, '10')
        
    def test_put_curious(self):
        response = self.client.put(reverse(views.actor_profile), {"actor":"bob","profileId":"10"},content_type='application/json')#x-www-form-urlencoded')
        self.assertContains(response, 'Error') # no parameters.. this stuff is the body
        
    def test_put_no_params(self):
        response = self.client.put(reverse(views.actor_profile),content_type='application/x-www-form-urlencoded')
        self.assertContains(response, 'Error')
    
    def test_put_no_actor(self):
        response = self.client.put(reverse(views.actor_profile), {'profileId':'10'},content_type='application/x-www-form-urlencoded')
        self.assertContains(response, 'Error')
        self.assertContains(response, 'actor parameter missing')

    def test_put_no_profileId(self):
        response = self.client.put(reverse(views.actor_profile), {'actor':'me'},content_type='application/x-www-form-urlencoded')
        #print 'no prof id test, line 59: %s' % response.content
        self.assertContains(response, 'Error')
        self.assertContains(response, 'profileId parameter missing')
    
    def test_get_actor_only(self):
        response = self.client.get(reverse(views.actor_profile), {'actor':'bob'})
        self.assertContains(response, 'Success')
        self.assertContains(response, 'bob')
        resp_hash = hashlib.sha1(response.content).hexdigest()
        self.assertEqual(response['ETag'], resp_hash)
    
    def test_get_actor_profileId(self):
        actor = json.dumps({"name":"bob","mbox":"mailto:bob@example.com"})
        response = self.client.get(reverse(views.actor_profile), {'actor':actor,'profileId':'10'})
        self.assertContains(response, 'Success')
        self.assertContains(response, 'bob')
        resp_hash = hashlib.sha1(response.content).hexdigest()
        self.assertEqual(response['ETag'], resp_hash)
    
    def test_get_actor_since(self):
        actor = json.dumps({"name":"bob","mbox":"mailto:bob@example.com"})
        since = time.time()
        response = self.client.get(reverse(views.actor_profile), {'actor':actor,'since':since})
        self.assertContains(response, 'Success')
        self.assertContains(response, actor)
        self.assertContains(response, since)
        resp_hash = hashlib.sha1(response.content).hexdigest()
        self.assertEqual(response['ETag'], resp_hash)
    
    def test_get_no_actor_profileId(self):
        response = self.client.get(reverse(views.actor_profile), {'profileId':'10'})
        self.assertContains(response, 'Error')
        self.assertContains(response, 'actor parameter missing')

    def test_get_no_actor_since(self):
        since = time.time()
        response = self.client.get(reverse(views.actor_profile), {'since':since})
        self.assertContains(response, 'Error')
        self.assertContains(response, 'actor parameter missing')
    
    def test_delete(self):
        actor = json.dumps({"name":"me","mbox":"mailto:me@example.com"})
        response = self.client.delete(reverse(views.actor_profile), {'actor':actor, 'profileId':'100'})
        self.assertContains(response, 'Success')
        self.assertContains(response, actor)        
        self.assertContains(response, '100')
        
        
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
    def test_activity(self):
        #Test basic activity
        act = objects.Activity(json.dumps({'objectType':'Activity', 'ACtivity_id':'http://tincanapi.wikispaces.com/', }))
        
        self.assertEqual(act.activity.activity_id, 'http://tincanapi.wikispaces.com/')
        self.assertEqual(act.activity.objectType, 'Activity')
        
        self.assertEqual(models.activity.objects.get(activity_id=act.activity.activity_id).objectType, 'Activity')
        self.assertEqual(models.activity.objects.get(activity_id=act.activity.activity_id).activity_id, 'http://tincanapi.wikispaces.com/')

    def test_activity_not_json(self):
        #Given wrong data format
        self.assertRaises(Exception, objects.Activity,"This string should throw exception since it's not JSON")

    def test_activity_no_objectType(self):
        #Not given an objectType
        act = objects.Activity(json.dumps({'activity_id':'http://tincanapi.wikispaces.com/Tin+Can+API+Specification'}))
        
        self.assertEqual(act.activity.activity_id, 'http://tincanapi.wikispaces.com/Tin+Can+API+Specification')
        self.assertEqual(act.activity.objectType, None)
        
        self.assertEqual(models.activity.objects.get(activity_id=act.activity.activity_id).objectType, None)
        self.assertEqual(models.activity.objects.get(activity_id=act.activity.activity_id).activity_id, 'http://tincanapi.wikispaces.com/Tin+Can+API+Specification')

    def test_activity_wrong_objectType(self):
        #Given invalid objectType
        act = objects.Activity(json.dumps({'activity_id': 'http://tincanapi.wikispaces.com/Best+Practices', 'objectType':'Wrong'}))    
        
        self.assertEqual(act.activity.activity_id, 'http://tincanapi.wikispaces.com/Best+Practices')
        self.assertEqual(act.activity.objectType, 'Activity')
        
        self.assertEqual(models.activity.objects.get(activity_id=act.activity.activity_id).objectType, 'Activity')
        self.assertEqual(models.activity.objects.get(activity_id=act.activity.activity_id).activity_id, 'http://tincanapi.wikispaces.com/Best+Practices')

    def test_activity_invalid_activity_id(self):
        #Given URL that doesn't resolve
        self.assertRaises(ValidationError, objects.Activity, json.dumps({'activity_id': 'http://foo', 'objectType':'Activity'}))

    def test_activity_definition(self):
        #Test activity with definition - must retrieve activity object in order to test definition from DB
        act = objects.Activity(json.dumps({'objectType': 'Activity', 'activity_id':'http://tincanapi.wikispaces.com/TinCan+Use+Cases',
                'definition': {'NAME': 'testname','descripTION': 'testdesc', 'tYpe': 'course',
                'interactionType': 'intType'}}))

        self.assertEqual(act.activity.activity_id, 'http://tincanapi.wikispaces.com/TinCan+Use+Cases')
        self.assertEqual(act.activity.objectType, 'Activity')
        self.assertEqual(act.activity.activity_definition.name, 'testname')
        self.assertEqual(act.activity.activity_definition.description, 'testdesc')
        self.assertEqual(act.activity.activity_definition.activity_definition_type, 'course')
        self.assertEqual(act.activity.activity_definition.interactionType, 'intType')

        PK = models.activity.objects.get(activity_id=act.activity.activity_id)

        self.assertEqual(models.activity.objects.get(activity_id=act.activity.activity_id).objectType, 'Activity')
        self.assertEqual(models.activity.objects.get(activity_id=act.activity.activity_id).activity_id, 'http://tincanapi.wikispaces.com/TinCan+Use+Cases')
        
        self.assertEqual(models.activity_definition.objects.get(activity=PK).name, 'testname')
        self.assertEqual(models.activity_definition.objects.get(activity=PK).description, 'testdesc')
        self.assertEqual(models.activity_definition.objects.get(activity=PK).activity_definition_type, 'course')
        self.assertEqual(models.activity_definition.objects.get(activity=PK).interactionType, 'intType')

    def test_activity_definition_wrong_type(self):
        #Given wrong type
        self.assertRaises(Exception, objects.Activity, json.dumps({'objectType': 'Activity',
                'activity_id':'http://tincanapi.wikispaces.com/Wish+List','definition': {'NAME': 'testname',
                'descripTION': 'testdesc', 'tYpe': 'wrong','interactionType': 'intType'}}))

        self.assertRaises(models.activity.DoesNotExist, models.activity.objects.get, activity_id='http://tincanapi.wikispaces.com/Wish+List')
    
    def test_activity_definition_required_fields(self):
        #Missing name in definition
        self.assertRaises(Exception, objects.Activity, json.dumps({'objectType': 'Activity',
                'activity_id':'http://google.com','definition': {'descripTION': 'testdesc',
                'tYpe': 'wrong','interactionType': 'intType'}}))

        self.assertRaises(models.activity.DoesNotExist, models.activity.objects.get, activity_id='http://google.com')

    def test_activity_definition_extensions(self):
        #Test extensions - need to retrieve activity and activity definition objects in order to test extenstions
        act = objects.Activity(json.dumps({'objectType': 'Activity', 'activity_id':'http://tincanapi.wikispaces.com/Verbs+and+Activities',
                'definition': {'name': 'testname2','description': 'testdesc2', 'type': 'course',
                'interactionType': 'intType2', 'extensions': {'key1': 'value1', 'key2': 'value2',
                'key3': 'value3'}}}))
        
        self.assertEqual(act.activity.activity_id, 'http://tincanapi.wikispaces.com/Verbs+and+Activities')
        self.assertEqual(act.activity.objectType, 'Activity')
        
        self.assertEqual(act.activity_definition.name, 'testname2')
        self.assertEqual(act.activity_definition.description, 'testdesc2')
        self.assertEqual(act.activity_definition.activity_definition_type, 'course')
        self.assertEqual(act.activity_definition.interactionType, 'intType2')
        
        self.assertEqual(act.activity_definition_extensions[0].key, 'key3')
        self.assertEqual(act.activity_definition_extensions[1].key, 'key2')
        self.assertEqual(act.activity_definition_extensions[2].key, 'key1')

        self.assertEqual(act.activity_definition_extensions[0].value, 'value3')    
        self.assertEqual(act.activity_definition_extensions[1].value, 'value2')
        self.assertEqual(act.activity_definition_extensions[2].value, 'value1')

        PK = models.activity.objects.get(activity_id=act.activity.activity_id)

        self.assertEqual(models.activity.objects.get(activity_id=act.activity.activity_id).objectType, 'Activity')
        self.assertEqual(models.activity.objects.get(activity_id=act.activity.activity_id).activity_id, 'http://tincanapi.wikispaces.com/Verbs+and+Activities')
        
        self.assertEqual(models.activity_definition.objects.get(activity=PK).name, 'testname2')
        self.assertEqual(models.activity_definition.objects.get(activity=PK).description, 'testdesc2')
        self.assertEqual(models.activity_definition.objects.get(activity=PK).activity_definition_type, 'course')
        self.assertEqual(models.activity_definition.objects.get(activity=PK).interactionType, 'intType2')

        defPK = models.activity_definition.objects.get(activity=PK)

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

    def test_activity_definition_wrong_interactionType(self):
        #Should fail because of invalid interactionType
        self.assertRaises(Exception, objects.Activity, json.dumps({'objectType': 'Activity', 'activity_id':'http://yahoo.com',
                'definition': {'name': 'testname2','description': 'testdesc2', 'type': 'cmi.interaction',
                'interactionType': 'intType2', 'correctResponsesPatteRN': 'response', 'extensions': {'key1': 'value1', 'key2': 'value2',
                'key3': 'value3'}}}))
     
        self.assertRaises(models.activity.DoesNotExist, models.activity.objects.get, activity_id='http://yahoo.com')

    def test_activity_definition_no_correctResponsesPattern(self):
        #If it has a valid interactionType it must also provide the correctResponsesPattern field
        self.assertRaises(Exception, objects.Activity, json.dumps({'objectType': 'Activity', 'activity_id':'http://msn.com',
                'definition': {'name': 'testname2','description': 'testdesc2', 'type': 'cmi.interaction',
                'interactionType': 'true-false', 'extensions': {'key1': 'value1', 'key2': 'value2',
                'key3': 'value3'}}}))
     
        self.assertRaises(models.activity.DoesNotExist, models.activity.objects.get, activity_id='http://msn.com')

    
    def test_activity_definition_cmiInteration_true_false(self):
        act = objects.Activity(json.dumps({'objectType': 'Activity', 'activity_id':'http://microsoft.com',
                'definition': {'name': 'testname2','description': 'testdesc2', 'type': 'cmi.interaction',
                'interactionType': 'true-false','correctResponsesPattern': ['true'] ,'extensions': {'key1': 'value1', 'key2': 'value2',
                'key3': 'value3'}}}))

        self.assertEqual(act.activity.activity_id, 'http://microsoft.com')
        self.assertEqual(act.activity.objectType, 'Activity')
        
        self.assertEqual(act.activity_definition.name, 'testname2')
        self.assertEqual(act.activity_definition.description, 'testdesc2')
        self.assertEqual(act.activity_definition.activity_definition_type, 'cmi.interaction')
        self.assertEqual(act.activity_definition.interactionType, 'true-false')
        
        self.assertEqual(act.activity_definition_extensions[0].key, 'key3')
        self.assertEqual(act.activity_definition_extensions[1].key, 'key2')
        self.assertEqual(act.activity_definition_extensions[2].key, 'key1')

        self.assertEqual(act.activity_definition_extensions[0].value, 'value3')    
        self.assertEqual(act.activity_definition_extensions[1].value, 'value2')
        self.assertEqual(act.activity_definition_extensions[2].value, 'value1')

        self.assertEqual(act.answers[0].answer, 'true')

        
        PK = models.activity.objects.get(activity_id=act.activity.activity_id)

        self.assertEqual(models.activity.objects.get(activity_id=act.activity.activity_id).objectType, 'Activity')
        self.assertEqual(models.activity.objects.get(activity_id=act.activity.activity_id).activity_id, 'http://microsoft.com')
        
        self.assertEqual(models.activity_definition.objects.get(activity=PK).name, 'testname2')
        self.assertEqual(models.activity_definition.objects.get(activity=PK).description, 'testdesc2')
        self.assertEqual(models.activity_definition.objects.get(activity=PK).activity_definition_type, 'cmi.interaction')
        self.assertEqual(models.activity_definition.objects.get(activity=PK).interactionType, 'true-false')

        defPK = models.activity_definition.objects.get(activity=PK)
        rspPK = models.activity_def_correctresponsespattern.objects.get(activity_definition=defPK)

        self.assertEqual(act.correctResponsesPattern.activity_definition, defPK)
        self.assertEqual(rspPK.activity_definition, defPK)



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

        rspAnswers = models.correctresponsespattern_answer.objects.values_list().filter(correctresponsespattern=rspPK)
        
        self.assertIn('true', rspAnswers)

    def test_activity_definition_cmiInteration_multiple_choice(self):    
        act = objects.Activity(json.dumps({'objectType': 'Activity', 'activity_id':'http://facebook.com',
                'definition': {'name': 'testname2','description': 'testdesc2', 'type': 'cmi.interaction',
                'interactionType': 'multiple-choice','correctResponsesPattern': ['golf', 'tetris'],
                'choices':[{'id': 'golf', 'description': {'en-US':'Golf Example'}},{'id': 'tetris',
                'description':{'en-US': 'Tetris Example'}}],
                'extensions': {'key1': 'value1', 'key2': 'value2',
                'key3': 'value3'}}}))

        self.assertEqual(act.activity.activity_id, 'http://facebook.com')
        self.assertEqual(act.activity.objectType, 'Activity')
        
        self.assertEqual(act.activity_definition.name, 'testname2')
        self.assertEqual(act.activity_definition.description, 'testdesc2')
        self.assertEqual(act.activity_definition.activity_definition_type, 'cmi.interaction')
        self.assertEqual(act.activity_definition.interactionType, 'multiple-choice')
        
        self.assertEqual(act.activity_definition_extensions[0].key, 'key3')
        self.assertEqual(act.activity_definition_extensions[1].key, 'key2')
        self.assertEqual(act.activity_definition_extensions[2].key, 'key1')

        self.assertEqual(act.activity_definition_extensions[0].value, 'value3')    
        self.assertEqual(act.activity_definition_extensions[1].value, 'value2')
        self.assertEqual(act.activity_definition_extensions[2].value, 'value1')

        self.assertEqual(act.answers[0].answer, 'golf')
        self.assertEqual(act.answers[1].answer, 'tetris')

        
        PK = models.activity.objects.get(activity_id=act.activity.activity_id)

        self.assertEqual(models.activity.objects.get(activity_id=act.activity.activity_id).objectType, 'Activity')
        self.assertEqual(models.activity.objects.get(activity_id=act.activity.activity_id).activity_id, 'http://facebook.com')
        
        self.assertEqual(models.activity_definition.objects.get(activity=PK).name, 'testname2')
        self.assertEqual(models.activity_definition.objects.get(activity=PK).description, 'testdesc2')
        self.assertEqual(models.activity_definition.objects.get(activity=PK).activity_definition_type, 'cmi.interaction')
        self.assertEqual(models.activity_definition.objects.get(activity=PK).interactionType, 'multiple-choice')

        defPK = models.activity_definition.objects.get(activity=PK)
        self.assertEqual(act.correctResponsesPattern.activity_definition, defPK)
        self.assertEqual(models.activity_def_correctresponsespattern.objects.get(activity_definition=defPK).activity_definition, defPK)

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
