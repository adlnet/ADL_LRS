from django.test import TestCase
from lrs.exceptions import ParamError
from lrs.models import agent, group, agent_account
from lrs.objects.Agent import Agent
import hashlib
import json

''' TODO:
recreate this to make agents (personas) at the model level w/in setUp
then make tests to get merged results (persons)
'''

class AgentModelsTests(TestCase):
    def test_agent_mbox_create(self):
        mbox = "bob@example.com"
        bob = agent(mbox=mbox)
        self.assertEquals(bob.mbox, mbox)
        self.assertEquals(bob.objectType, "Agent")
        self.assertFalse(bob.name)

    def test_agent_mbox_sha1sum_create(self):
        msha = hashlib.sha1("bob@example.com").hexdigest()
        bob = agent(mbox_sha1sum=msha)
        self.assertEquals(bob.mbox_sha1sum, msha)
        self.assertEquals(bob.objectType, "Agent")
        self.assertFalse(bob.name)
        self.assertFalse(bob.mbox)

    def test_agent_openid_create(self):
        openid = "bob.openid.com"
        bob = agent(openid=openid)
        self.assertEquals(bob.openid, openid)
        self.assertEquals(bob.objectType, "Agent")
        self.assertFalse(bob.name)
        self.assertFalse(bob.mbox)
        self.assertFalse(bob.mbox_sha1sum)
        self.assertFalse(bob.account)

    def test_agent_account_create(self):
        account = {"homePage":"http://www.adlnet.gov","name":"freakshow"}
        bobacc = agent_account(**account)
        bob = agent(account=bobacc)
        bob.save()
        a = bob.account
        self.assertEquals(a.name, "freakshow")
        self.assertEquals(a.homePage, "http://www.adlnet.gov")
        self.assertEquals(a.agent, bob)
        self.assertFalse(bob.name)
        self.assertFalse(bob.mbox)
        self.assertFalse(bob.mbox_sha1sum)
        self.assertFalse(bob.openid)

    def test_agent_kwargs_basic(self):
        ot = "Agent"
        name = "bob bobson"
        mbox = "mailto:bobbobson@example.com"
        kwargs = {"objectType":ot,"name":name,"mbox":mbox}
        bob, created = agent.objects.gen(**kwargs)
        self.assertTrue(created)
        bob.save()
        self.assertEquals(bob.objectType, ot)
        self.assertEquals(bob.name, name)
        self.assertEquals(bob.mbox, mbox)

        bob2, created = agent.objects.gen(**kwargs)
        self.assertFalse(created)
        self.assertEquals(bob.pk, bob2.pk)
        self.assertEquals(bob, bob2)

        kwargs['mbox'] = "mailto:bob.secret@example.com"
        bob3, created = agent.objects.gen(**kwargs)
        self.assertTrue(created)
        bob3.save()
        self.assertNotEqual(bob.pk, bob3.pk)

    def test_agent_kwargs_basic_account(self):
        ot = "Agent"
        name = "bob bobson"
        account = json.dumps({"homePage":"http://www.adlnet.gov","name":"freakshow"})
        kwargs = {"objectType":ot,"name":name,"account":account}
        bob, created = agent.objects.gen(**kwargs)
        self.assertTrue(created)
        bob.save()
        self.assertEquals(bob.objectType, ot)
        self.assertEquals(bob.name, name)
        a = bob.account
        self.assertEquals(a.homePage, "http://www.adlnet.gov")
        self.assertEquals(a.name, "freakshow")

    def test_agent_json_no_ids(self):
        self.assertRaises(ParamError, agent.objects.gen, 
            **{"name":"bob bobson"})

    def test_agent_json_many_ids(self):
        self.assertRaises(ParamError, agent.objects.gen, 
            **{"mbox":"mailto:bob@example.com",
               "openid":"bob.bobson.openid.org"})

    def test_group(self):
        ot = "Group"
        name = "the group"
        mbox = "mailto:the.group@example.com"
        members = [{"name":"agent1","mbox":"mailto:agent1@example.com"},
                    {"name":"agent2","mbox":"mailto:agent2@example.com"}]
        kwargs = {"objectType":ot, "name":name, "mbox":mbox,"member":members}
        g, created = group.objects.gen(**kwargs)
        g.save()
        self.assertTrue(created)
        self.assertEquals(g.name, name)
        self.assertEquals(g.mbox, mbox)
        mems = g.member.values_list('name', flat=True)
        self.assertEquals(len(mems), 2)
        self.assertIn('agent1', mems)
        self.assertIn('agent2', mems)

    def test_group_from_agent_object(self):
        ot = "Group"
        name = "the group"
        mbox = "mailto:the.group@example.com"
        members = [{"name":"agent1","mbox":"mailto:agent1@example.com"},
                    {"name":"agent2","mbox":"mailto:agent2@example.com"}]
        kwargs = {"objectType":ot, "name":name, "mbox":mbox,"member":members}
        g = Agent(initial=kwargs, create=True).agent
        self.assertEquals(g.name, name)
        self.assertEquals(g.mbox, mbox)
        mems = g.member.values_list('name', flat=True)
        self.assertEquals(len(mems), 2)
        self.assertIn('agent1', mems)
        self.assertIn('agent2', mems)

    def test_group_from_agent_string(self):
        ot = "Group"
        name = "the group"
        mbox = "mailto:the.group@example.com"
        members = [{"name":"agent1","mbox":"mailto:agent1@example.com"},
                    {"name":"agent2","mbox":"mailto:agent2@example.com"}]
        kwargs = json.dumps({"objectType":ot, "name":name, "mbox":mbox,"member":members})
        g = Agent(initial=kwargs, create=True).agent
        self.assertEquals(g.name, name)
        self.assertEquals(g.mbox, mbox)
        mems = g.member.values_list('name', flat=True)
        self.assertEquals(len(mems), 2)
        self.assertIn('agent1', mems)
        self.assertIn('agent2', mems)

    def test_group_oauth_authority(self):
        ot = "Group"
        name = "auth group"
        account = json.dumps({"homePage":"http://www.adlnet.gov","name":"freakshow"})
        members = [{"name":"the agent","account":account},
                    {"name":"the user","mbox":"mailto:user@example.com"}]
        kwargs = {"objectType":ot, "name":name, "member":members}
        g = Agent(initial=kwargs, create=True).agent
        self.assertEquals(g.name, name)
        self.assertEquals(g.mbox, None)
        mems = g.member.values_list('name', flat=True)
        self.assertEquals(len(mems), 2)
        self.assertIn('the agent', mems)
        self.assertIn('the user', mems)
