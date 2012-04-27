from django.test import TestCase
from django.core.urlresolvers import reverse
from lrs import views
import json
import time

class StatementsTest(TestCase):
    def test_stuff(self):
        response = self.client.get(reverse(views.statements))
        self.assertEqual(response.status_code, 200)


class ActivityStateTest(TestCase):
    def test_stuff(self):
        response = self.client.get(reverse(views.activity_state))
        self.assertEqual(response.status_code, 200)

        
class ActivityProfileTest(TestCase):
    def test_stuff(self):
        response = self.client.get(reverse(views.activity_profile))
        self.assertEqual(response.status_code, 200)

        
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
        response = self.client.put(reverse(views.actor_profile), {'actor':'bob','profileId':'10'},content_type='application/json')#x-www-form-urlencoded')
        #print 'basic put test, line 43: %s' % response.content
        self.assertContains(response, 'Success')
        self.assertContains(response, 'bob')
        self.assertContains(response, '10')
        
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
    
    def test_get_actor_profileId(self):
        actor = json.dumps({"name":"bob","mbox":"mailto:bob@example.com"})
        response = self.client.get(reverse(views.actor_profile), {'actor':actor,'profileId':'10'})
        self.assertContains(response, 'Success')
        self.assertContains(response, 'bob')
    
    def test_get_actor_since(self):
        actor = json.dumps({"name":"bob","mbox":"mailto:bob@example.com"})
        since = time.time()
        response = self.client.get(reverse(views.actor_profile), {'actor':actor,'since':since})
        self.assertContains(response, 'Success')
        self.assertContains(response, actor)
        self.assertContains(response, since)
    
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

