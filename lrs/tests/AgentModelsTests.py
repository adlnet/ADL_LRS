from django.test import TestCase
from lrs.exceptions import ParamError
from lrs.models import agent, agent_account
from lrs.objects.Agent import Agent
import hashlib
import json
import pdb
''' TODO:
recreate this to make agents (personas) at the model level w/in setUp
then make tests to get merged results (persons)
'''

class AgentModelsTests(TestCase):
    def test_agent_mbox_create(self):
        mbox = "mailto:bob@example.com"
        bob = agent(mbox=mbox)
        self.assertEquals(bob.mbox, mbox)
        self.assertEquals(bob.objectType, "Agent")
        self.assertFalse(bob.name)

    def test_agent_mbox_sha1sum_create(self):
        msha = hashlib.sha1("mailto:bob@example.com").hexdigest()
        bob = agent(mbox_sha1sum=msha)
        self.assertEquals(bob.mbox_sha1sum, msha)
        self.assertEquals(bob.objectType, "Agent")
        self.assertFalse(bob.name)
        self.assertFalse(bob.mbox)

    def test_agent_openid_create(self):
        openid = "bob.openid.com"
        bob = agent(openid=openid)
        bob.save()
        self.assertEquals(bob.openid, openid)
        self.assertEquals(bob.objectType, "Agent")
        self.assertFalse(bob.name)
        self.assertFalse(bob.mbox)
        self.assertFalse(bob.mbox_sha1sum)

    def test_agent_account_create(self):
        account = {"homePage":"http://www.adlnet.gov","name":"freakshow"}
        bob = agent()
        bob.save()
        bobacc = agent_account(agent=bob, **account)
        bobacc.save()
        a = bob.agent_account
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
        self.assertEquals(bob.objectType, ot)
        self.assertEquals(bob.name, name)
        a = bob.agent_account
        self.assertEquals(a.homePage, "http://www.adlnet.gov")
        self.assertEquals(a.name, "freakshow")

    def test_group_kwargs(self):
        ot = "Agent"
        name = "bob bobson"
        kwargs = {"objectType":ot,"name":name, "mbox": "mailto:bob@example.com"}
        bob, created = agent.objects.gen(**kwargs)

        ot = "Agent"
        name = "john johnson"
        kwargs = {"objectType":ot,"name":name, "mbox": "mailto:john@example.com"}
        john, created = agent.objects.gen(**kwargs)
        
        ot = "Group"
        members = [{"name":"bob bobson","mbox":"mailto:bob@example.com"},
                    {"name":"john johnson","mbox":"mailto:john@example.com"}]
        
        kwargs = {"objectType":ot, "member": members}
        gr, created = agent.objects.gen(**kwargs)
        # Already created from above
        self.assertTrue(created)

        kwargs1 = {"objectType":ot, "member": members, "name": "my group"}
        gr1, created = agent.objects.gen(**kwargs1)
        # creates another one b/c of adding a name
        self.assertTrue(created)
        self.assertEquals(gr1.name, "my group")
        agents = agent.objects.all()
        self.assertEquals(len(agents), 4)
        obj_types = agents.values_list('objectType', flat=True)
        self.assertEquals(len(agents.filter(objectType='Group')), 2)
        self.assertEquals(len(agents.filter(objectType='Agent')), 2)

    def test_agent_update_kwargs(self):
        ot = "Agent"
        name = "bill billson"
        kwargs = {"objectType":ot, "mbox": "mailto:bill@example.com"}
        bill, created = agent.objects.gen(**kwargs)
        self.assertTrue(created)

        kwargs1 = {"objectType":ot, "mbox": "mailto:bill@example.com", "name": name}
        bill2, created = agent.objects.gen(**kwargs1)
        
        self.assertFalse(created)
        self.assertEquals(bill2.name, name)
        self.assertEquals(bill.id, bill2.id)
        self.assertEquals(len(agent.objects.all()), 1)

    def test_agent_update_kwargs_with_account(self):
        ot = "Agent"
        name = "bill billson"
        account = json.dumps({"homePage":"http://www.adlnet.gov","name":"freakshow"})
        kwargs = {"objectType":ot,"account":account}
        
        bill, created = agent.objects.gen(**kwargs)
        self.assertTrue(created)

        kwargs1 = {"objectType":ot, "name": name, "account":account}
        bill2, created = agent.objects.gen(**kwargs1)
        
        self.assertFalse(created)
        self.assertEquals(bill2.name, name)
        self.assertEquals(bill.id, bill2.id)
        self.assertEquals(len(agent.objects.all()), 1)
        self.assertEquals(len(agent_account.objects.all()), 1)

    def test_group_update_kwargs_with_account(self):
        ot = "Group"
        name = "the group"
        account = json.dumps({"homePage":"http://www.adlnet.gov","name":"freakshow-group"})
        members = [{"name":"agent1","mbox":"mailto:agent1@example.com"},
                    {"name":"agent2","mbox":"mailto:agent2@example.com"}]

        kwargs = {"objectType":ot,"member":members, "account":account}
        
        g, created = agent.objects.gen(**kwargs)
        self.assertTrue(created)

        kwargs1 = {"objectType":ot,"member":members, "name": name, "account":account}
        g1, created = agent.objects.gen(**kwargs1)
        
        self.assertFalse(created)
        self.assertEquals(g1.name, name)
        self.assertEquals(g.id, g1.id)
        self.assertEquals(len(agent.objects.all()), 3)
        self.assertEquals(len(agent_account.objects.all()), 1)
        self.assertEquals(agent_account.objects.all()[0].agent.id, g.id)


    def test_group_update_kwargs(self):
        ot = "Group"
        name = "the group"
        mbox = "mailto:the.group@example.com"
        members = [{"name":"agent1","mbox":"mailto:agent1@example.com"},
                    {"name":"agent2","mbox":"mailto:agent2@example.com"}]
        kwargs = {"objectType":ot, "mbox":mbox,"member":members}
        g, created = agent.objects.gen(**kwargs)
        self.assertTrue(created)

        kwargs1 = {"objectType":ot, "name":name, "mbox":mbox,"member":members}
        g1, created = agent.objects.gen(**kwargs1)
        self.assertFalse(created)

        self.assertEquals(g1.name, name)
        self.assertEquals(g.id, g1.id)
        # 2 agents 1 group
        self.assertEquals(len(agent.objects.all()), 3)

    def test_group_update_members(self):
        ot = "Group"
        name = "the group"
        mbox = "mailto:the.group@example.com"
        members = [{"name":"agent1","mbox":"mailto:agent1@example.com"},
                    {"name":"agent2","mbox":"mailto:agent2@example.com"}]
        kwargs = {"objectType":ot, "mbox":mbox,"member":members}
        g, created = agent.objects.gen(**kwargs)
        self.assertTrue(created)

        members = [{"name":"agent1","mbox":"mailto:agent1@example.com"},
                    {"name":"agent2","mbox":"mailto:agent2@example.com"},
                    {"name":"agent3","mbox":"mailto:agent3@example.com"}]

        kwargs1 = {"objectType":ot, "mbox":mbox,"member":members}
        g1, created = agent.objects.gen(**kwargs1)
        self.assertFalse(created)

        ags = agent.objects.filter(objectType='Agent')
        mems = g1.member.all()
        self.assertEquals(len(ags), len(mems))
        self.assertTrue(set(ags) == set(mems))
        self.assertEquals(g.id, g1.id)
        # 3 agents 1 group
        self.assertEquals(len(agent.objects.all()), 4)

    def test_group_update_members_with_account(self):
        ot = "Group"
        name = "the group"
        account = json.dumps({"homePage":"http://www.adlnet.gov","name":"freakshow-group"})
        members = [{"name":"agent1","mbox":"mailto:agent1@example.com"},
                    {"name":"agent2","mbox":"mailto:agent2@example.com"}]

        kwargs = {"objectType":ot,"member":members,"name":name ,"account":account}
        g, created = agent.objects.gen(**kwargs)
        self.assertTrue(created)

        members = [{"name":"agent1","mbox":"mailto:agent1@example.com"},
                    {"name":"agent2","mbox":"mailto:agent2@example.com"},
                    {"name":"agent3","mbox":"mailto:agent3@example.com"}]

        kwargs1 = {"objectType":ot, "account":account,"name":name,"member":members}
        g1, created = agent.objects.gen(**kwargs1)
        self.assertFalse(created)

        ags = agent.objects.filter(objectType='Agent')
        mems = g1.member.all()
        self.assertEquals(len(ags), len(mems))
        self.assertTrue(set(ags) == set(mems))
        self.assertEquals(g.id, g1.id)
        # 3 agents 1 group
        self.assertEquals(len(agent.objects.all()), 4)
        self.assertEquals(len(agent_account.objects.all()), 1)
        self.assertEquals(agent_account.objects.all()[0].agent.id, g1.id)

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
        g, created = agent.objects.gen(**kwargs)
        self.assertTrue(created)
        self.assertEquals(g.name, name)
        self.assertEquals(g.mbox, mbox)
        mems = g.member.values_list('name', flat=True)
        self.assertEquals(len(mems), 2)
        self.assertIn('agent1', mems)
        self.assertIn('agent2', mems)
        gr_dict = g.get_agent_json()
        self.assertEquals(gr_dict['objectType'],'Group')
        
        for member in gr_dict['member']:
            self.assertEquals(member['objectType'], 'Agent')
            if member['name'] == 'agent1':
                self.assertEquals(member['mbox'], 'mailto:agent1@example.com')
            elif member['name'] == 'agent2':
                self.assertEquals(member['mbox'], 'mailto:agent2@example.com')

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


    def test_agent_del(self):
        ag = agent(name="the agent")
        ag.save()
        acc = agent_account(agent=ag, homePage="http://adlnet.gov/agent/1", name="agent 1 account")
        acc.save()

        self.assertEquals(ag.name, "the agent")
        self.assertEquals(ag.agent_account.name, "agent 1 account")
        self.assertEquals(ag.agent_account.homePage, "http://adlnet.gov/agent/1")
        self.assertEquals(1, len(agent.objects.all()))
        self.assertEquals(1, len(agent_account.objects.all()))

        ag.delete()

        self.assertEquals(0, len(agent.objects.all()))
        self.assertEquals(0, len(agent_account.objects.all()))
