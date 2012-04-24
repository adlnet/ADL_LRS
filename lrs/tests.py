from django.test import TestCase
from django.core.urlresolvers import reverse
from lrs import views

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
        response = self.client.post(reverse(views.activities), {'activityId':'my_activity'})
        self.assertEqual(response.status_code, 405)


class ActorProfileTest(TestCase):
    def test_put(self):
        response = self.client.put(reverse(views.actor_profile), {'actor':'bob','profileId':'10'})
        self.assertContains(response, 'Success')
        self.assertContains(response, 'bob')
        self.assertContains(response, '10')
        
    def test_put_no_params(self):
        response = self.client.put(reverse(views.actor_profile))
        self.assertContains(response, 'Error')

        
class ActorsTest(TestCase):
    def test_get(self):
        response = self.client.get(reverse(views.actors), {'actor':'bob'})
        self.assertContains(response, 'Success')
        self.assertContains(response, 'bob')
    
    def test_get_no_actor(self):
        response = self.client.get(reverse(views.actors))
        self.assertContains(response, 'Error')
    
    def test_post(self):
        response = self.client.post(reverse(views.actors), {'actor':'bob'})
        self.assertEqual(response.status_code, 405)

