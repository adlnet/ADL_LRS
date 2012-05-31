from django.test import TestCase
from django.core.urlresolvers import reverse
from lrs import views
import json
import time
import hashlib
import models

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

        statement = models.Statement()
        statement.save()
        self.assertEqual(statement.verb, 'created')

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
        response = self.client.get(reverse(views.actors), {'actor':'bob'})
        self.assertContains(response, 'Success')
        self.assertContains(response, 'bob')
    
    def test_get_no_actor(self):
        response = self.client.get(reverse(views.actors))
        self.assertContains(response, 'Error')
    
    def test_post(self):
        response = self.client.post(reverse(views.actors), {'actor':'bob'},content_type='application/x-www-form-urlencoded')
        self.assertEqual(response.status_code, 405)

