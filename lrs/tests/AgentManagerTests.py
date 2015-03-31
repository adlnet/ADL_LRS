import hashlib
import json
import base64

from django.test import TestCase
from django.core.urlresolvers import reverse
from django.conf import settings

from ..models import Agent, Statement
from ..views import register, statements
from ..objects.AgentManager import AgentManager

class AgentManagerTests(TestCase):
    @classmethod
    def setUpClass(cls):
        print "\n%s" % __name__

    def setUp(self):
        if not settings.ALLOW_EMPTY_HTTP_AUTH:
            settings.ALLOW_EMPTY_HTTP_AUTH = True
        
        self.username = "tester1"
        self.email = "test1@tester.com"
        self.password = "test"
        self.auth = "Basic %s" % base64.b64encode("%s:%s" % (self.username, self.password))
        form = {"username":self.username, "email":self.email,"password":self.password,"password2":self.password}
        self.client.post(reverse(register),form, X_Experience_API_Version="1.0.0")           

    def test_agent_mbox_create(self):
        stmt = json.dumps({"actor":{"objectType": "Agent", "mbox":"mailto:bob@example.com"},
            "verb":{"id": "http://adlnet.gov/expapi/verbs/passed"},
            "object": {'id': 'act://blah.com'}})

        response = self.client.post(reverse(statements), stmt, content_type="application/json",
            Authorization=self.auth, X_Experience_API_Version="1.0.0")
        
        self.assertEqual(response.status_code, 200)
        st_id = json.loads(response.content)        
        st = Statement.objects.get(statement_id=st_id[0])
        bob = st.actor
        self.assertEquals(bob.objectType, "Agent")
        self.assertFalse(bob.name)

    def test_agent_mbox_sha1sum_create(self):
        stmt = json.dumps({"actor":{"objectType": "Agent", "mbox_sha1sum":hashlib.sha1("mailto:bob@example.com").hexdigest()},
            "verb":{"id": "http://adlnet.gov/expapi/verbs/passed"},
            "object": {'id': 'act://blah.com'}})

        response = self.client.post(reverse(statements), stmt, content_type="application/json",
            Authorization=self.auth, X_Experience_API_Version="1.0.0")
        
        self.assertEqual(response.status_code, 200)
        st_id = json.loads(response.content)        
        st = Statement.objects.get(statement_id=st_id[0])
        bob = st.actor

        self.assertEquals(bob.mbox_sha1sum, hashlib.sha1("mailto:bob@example.com").hexdigest())
        self.assertEquals(bob.objectType, "Agent")
        self.assertFalse(bob.name)
        self.assertFalse(bob.mbox)

    def test_agent_bogus_mbox_sha1sum_create(self):
        stmt = json.dumps({"actor":{"objectType": "Agent", "mbox_sha1sum":"notarealsum"},
            "verb":{"id": "http://adlnet.gov/expapi/verbs/passed"},
            "object": {'id': 'act://blah.com'}})

        response = self.client.post(reverse(statements), stmt, content_type="application/json",
            Authorization=self.auth, X_Experience_API_Version="1.0.0")
        
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.content, "mbox_sha1sum value [notarealsum] is not a valid sha1sum")

    def test_agent_openID_create(self):
        stmt = json.dumps({"actor":{"objectType": "Agent", "openid":"http://bob.openid.com"},
            "verb":{"id": "http://adlnet.gov/expapi/verbs/passed"},
            "object": {'id': 'act://blah.com'}})

        response = self.client.post(reverse(statements), stmt, content_type="application/json",
            Authorization=self.auth, X_Experience_API_Version="1.0.0")

        self.assertEqual(response.status_code, 200)
        st_id = json.loads(response.content)        
        st = Statement.objects.get(statement_id=st_id[0])
        bob = st.actor

        self.assertEquals(bob.openid, "http://bob.openid.com")
        self.assertEquals(bob.objectType, "Agent")
        self.assertFalse(bob.name)
        self.assertFalse(bob.mbox)
        self.assertFalse(bob.mbox_sha1sum)

    def test_agent_account_create(self):
        stmt = json.dumps({"actor":{"objectType": "Agent", "account":{"homePage": "http://www.adlnet.gov", "name":"freakshow"}},
            "verb":{"id": "http://adlnet.gov/expapi/verbs/passed"},
            "object": {'id': 'act://blah.com'}})

        response = self.client.post(reverse(statements), stmt, content_type="application/json",
            Authorization=self.auth, X_Experience_API_Version="1.0.0")
        
        self.assertEqual(response.status_code, 200)
        st_id = json.loads(response.content)        
        st = Statement.objects.get(statement_id=st_id[0])
        bob = st.actor

        self.assertEquals(bob.account_name, "freakshow")
        self.assertEquals(bob.account_homePage, "http://www.adlnet.gov")
        self.assertFalse(bob.name)
        self.assertFalse(bob.mbox)
        self.assertFalse(bob.mbox_sha1sum)
        self.assertFalse(bob.openid)

    def test_agent_kwargs_basic(self):
        ot = "Agent"
        name = "bob bobson"
        mbox = "mailto:bobbobson@example.com"
        kwargs = {"objectType":ot,"name":name,"mbox":mbox}
        bob, created = Agent.objects.retrieve_or_create(**kwargs)
        self.assertTrue(created)
        bob.save()
        self.assertEquals(bob.objectType, ot)
        self.assertEquals(bob.name, name)
        self.assertEquals(bob.mbox, mbox)

        bob2, created = Agent.objects.retrieve_or_create(**kwargs)
        self.assertFalse(created)
        self.assertEquals(bob.pk, bob2.pk)
        self.assertEquals(bob, bob2)

        kwargs['mbox'] = "mailto:bob.secret@example.com"
        bob3, created = Agent.objects.retrieve_or_create(**kwargs)
        self.assertTrue(created)
        bob3.save()
        self.assertNotEqual(bob.pk, bob3.pk)

    def test_agent_kwargs_basic_account(self):        
        ot = "Agent"
        name = "bob bobson"
        account = json.dumps({"homePage":"http://www.adlnet.gov","name":"freakshow"})
        kwargs = {"objectType":ot,"name":name,"account":account}
        bob, created = Agent.objects.retrieve_or_create(**kwargs)
        self.assertTrue(created)
        self.assertEquals(bob.objectType, ot)
        self.assertEquals(bob.name, name)
        self.assertEquals(bob.account_homePage, "http://www.adlnet.gov")
        self.assertEquals(bob.account_name, "freakshow")

    def test_group_kwargs(self):
        ot = "Agent"
        name = "bob bobson"
        kwargs = {"objectType":ot,"name":name, "mbox": "mailto:bob@example.com"}
        bob, created = Agent.objects.retrieve_or_create(**kwargs)

        ot = "Agent"
        name = "john johnson"
        kwargs = {"objectType":ot,"name":name, "mbox": "mailto:john@example.com"}
        john, created = Agent.objects.retrieve_or_create(**kwargs)
        
        ot = "Group"
        members = [{"name":"bob bobson","mbox":"mailto:bob@example.com"},
                    {"name":"john johnson","mbox":"mailto:john@example.com"}]
        
        kwargs = {"objectType":ot, "member": members}
        gr, created = Agent.objects.retrieve_or_create(**kwargs)
        # Already created from above
        self.assertTrue(created)

        kwargs1 = {"objectType":ot, "member": members, "name": "my group"}
        gr1, created = Agent.objects.retrieve_or_create(**kwargs1)
        # creates another one b/c of adding a name
        self.assertTrue(created)
        self.assertEquals(gr1.name, "my group")
        agents = Agent.objects.all()
        self.assertEquals(len(agents), 4)
        self.assertEquals(len(agents.filter(objectType='Group')), 2)
        self.assertEquals(len(agents.filter(objectType='Agent')), 2)

    def test_agent_update_kwargs(self):
        ot = "Agent"
        name = "bill billson"
        kwargs = {"objectType":ot, "mbox": "mailto:bill@example.com"}
        bill, created = Agent.objects.retrieve_or_create(**kwargs)
        self.assertTrue(created)

        kwargs1 = {"objectType":ot, "mbox": "mailto:bill@example.com", "name": name}
        bill2, created = Agent.objects.retrieve_or_create(**kwargs1)
        
        self.assertFalse(created)
        self.assertEquals(bill2.name, name)
        self.assertEquals(bill.id, bill2.id)
        self.assertEquals(len(Agent.objects.all()), 1)

    def test_agent_update_kwargs_with_account(self):
        ot = "Agent"
        name = "bill billson"
        account = json.dumps({"homePage":"http://www.adlnet.gov","name":"freakshow"})
        kwargs = {"objectType":ot,"account":account}
        
        bill, created = Agent.objects.retrieve_or_create(**kwargs)
        self.assertTrue(created)

        kwargs1 = {"objectType":ot, "name": name, "account":account}
        bill2, created = Agent.objects.retrieve_or_create(**kwargs1)
        
        self.assertFalse(created)
        self.assertEquals(bill2.name, name)
        self.assertEquals(bill.id, bill2.id)
        self.assertEquals(len(Agent.objects.all()), 1)

    def test_group_update_kwargs_with_account(self):
        ot = "Group"
        name = "the group"
        account = json.dumps({"homePage":"http://www.adlnet.gov","name":"freakshow-group"})
        members = [{"name":"agent1","mbox":"mailto:agent1@example.com"},
                    {"name":"agent2","mbox":"mailto:agent2@example.com"}]

        kwargs = {"objectType":ot,"member":members, "account":account}
        
        g, created = Agent.objects.retrieve_or_create(**kwargs)
        self.assertTrue(created)

        kwargs1 = {"objectType":ot,"member":members, "name": name, "account":account}
        g1, created = Agent.objects.retrieve_or_create(**kwargs1)
        
        self.assertFalse(created)
        self.assertEquals(g1.name, name)
        self.assertEquals(g.id, g1.id)
        self.assertEquals(len(Agent.objects.all()), 3)
        self.assertEquals(g1.account_name, "freakshow-group")
        self.assertEquals(g.account_name, "freakshow-group")
        self.assertEquals(g1.account_homePage, "http://www.adlnet.gov")
        self.assertEquals(g.account_homePage, "http://www.adlnet.gov")

    def test_group_update_kwargs(self):
        ot = "Group"
        name = "the group"
        mbox = "mailto:the.group@example.com"
        members = [{"name":"agent1","mbox":"mailto:agent1@example.com"},
                    {"name":"agent2","mbox":"mailto:agent2@example.com"}]
        kwargs = {"objectType":ot, "mbox":mbox,"member":members}
        g, created = Agent.objects.retrieve_or_create(**kwargs)
        self.assertTrue(created)

        kwargs1 = {"objectType":ot, "name":name, "mbox":mbox,"member":members}
        g1, created = Agent.objects.retrieve_or_create(**kwargs1)
        self.assertFalse(created)

        self.assertEquals(g1.name, name)
        self.assertEquals(g.id, g1.id)
        # 2 agents 1 group
        self.assertEquals(len(Agent.objects.all()), 3)

    def test_group_update_members(self):
        ot = "Group"
        mbox = "mailto:the.group@example.com"
        members = [{"name":"agent1","mbox":"mailto:agent1@example.com"},
                    {"name":"agent2","mbox":"mailto:agent2@example.com"}]
        kwargs = {"objectType":ot, "mbox":mbox,"member":members}
        g, created = Agent.objects.retrieve_or_create(**kwargs)
        self.assertTrue(created)

        members = [{"name":"agent1","mbox":"mailto:agent1@example.com"},
                    {"name":"agent2","mbox":"mailto:agent2@example.com"},
                    {"name":"agent3","mbox":"mailto:agent3@example.com"}]

        kwargs1 = {"objectType":ot, "mbox":mbox,"member":members}
        g1, created = Agent.objects.retrieve_or_create(**kwargs1)
        self.assertFalse(created)

        ags = Agent.objects.filter(objectType='Agent')
        mems = g1.member.all()
        self.assertEquals(len(ags), len(mems))
        self.assertTrue(set(ags) == set(mems))
        self.assertEquals(g.id, g1.id)
        # 3 agents 1 group
        self.assertEquals(len(Agent.objects.all()), 4)

    def test_group_update_members_with_account(self):
        ot = "Group"
        name = "the group"
        account = json.dumps({"homePage":"http://www.adlnet.gov","name":"freakshow-group"})
        members = [{"name":"agent1","mbox":"mailto:agent1@example.com"},
                    {"name":"agent2","mbox":"mailto:agent2@example.com"}]

        kwargs = {"objectType":ot,"member":members,"name":name ,"account":account}
        g, created = Agent.objects.retrieve_or_create(**kwargs)
        self.assertTrue(created)

        members = [{"name":"agent1","mbox":"mailto:agent1@example.com"},
                    {"name":"agent2","mbox":"mailto:agent2@example.com"},
                    {"name":"agent3","mbox":"mailto:agent3@example.com"}]

        kwargs1 = {"objectType":ot, "account":account,"name":name,"member":members}
        g1, created = Agent.objects.retrieve_or_create(**kwargs1)
        self.assertFalse(created)

        ags = Agent.objects.filter(objectType='Agent')
        mems = g1.member.all()
        self.assertEquals(len(ags), len(mems))
        self.assertTrue(set(ags) == set(mems))
        self.assertEquals(g.id, g1.id)
        # 3 agents 1 group
        self.assertEquals(len(Agent.objects.all()), 4)
        self.assertEquals(g1.account_name, "freakshow-group")
        self.assertEquals(g.account_name, "freakshow-group")
        self.assertEquals(g1.account_homePage, "http://www.adlnet.gov")
        self.assertEquals(g.account_homePage, "http://www.adlnet.gov")
        self.assertEquals(g1.name, "the group")
        self.assertEquals(g.name, "the group")


    def test_agent_json_no_ids(self):
        stmt = json.dumps({"actor":{"objectType": "Agent", "name":"freakshow"},
            "verb":{"id": "http://adlnet.gov/expapi/verbs/passed"},
            "object": {'id': 'act://blah.com'}})

        response = self.client.post(reverse(statements), stmt, content_type="application/json",
            Authorization=self.auth, X_Experience_API_Version="1.0.0")
        
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.content, 'One and only one of mbox, mbox_sha1sum, openid, account may be supplied with an Agent')

    def test_agent_json_many_ids(self):
        stmt = json.dumps({"actor":{"objectType": "Agent", "mbox":"mailto:bob@example.com", "openid":"bob.bobson.openid.org"},
            "verb":{"id": "http://adlnet.gov/expapi/verbs/passed"},
            "object": {'id': 'act://blah.com'}})

        response = self.client.post(reverse(statements), stmt, content_type="application/json",
            Authorization=self.auth, X_Experience_API_Version="1.0.0")
        
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.content, 'One and only one of mbox, mbox_sha1sum, openid, account may be supplied with an Agent')

    def test_group(self):
        ot = "Group"
        name = "the group"
        mbox = "mailto:the.group@example.com"
        members = [{"name":"agent1","mbox":"mailto:agent1@example.com"},
                    {"name":"agent2","mbox":"mailto:agent2@example.com"}]
        kwargs = {"objectType":ot, "name":name, "mbox":mbox,"member":members}
        g, created = Agent.objects.retrieve_or_create(**kwargs)
        self.assertTrue(created)
        self.assertEquals(g.name, name)
        self.assertEquals(g.mbox, mbox)
        mems = g.member.values_list('name', flat=True)
        self.assertEquals(len(mems), 2)
        self.assertIn('agent1', mems)
        self.assertIn('agent2', mems)
        gr_dict = g.to_dict()
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
        g = AgentManager(params=kwargs).Agent
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
        kwargs = {"objectType":ot, "name":name, "mbox":mbox,"member":members}
        g = AgentManager(params=kwargs).Agent
        self.assertEquals(g.name, name)
        self.assertEquals(g.mbox, mbox)
        mems = g.member.values_list('name', flat=True)
        self.assertEquals(len(mems), 2)
        self.assertIn('agent1', mems)
        self.assertIn('agent2', mems)

    def test_agent_del(self):
        ag = Agent(name="the agent", account_homePage="http://adlnet.gov/agent/1",
            account_name="agent 1 account")
        ag.save()

        self.assertEquals(ag.name, "the agent")
        self.assertEquals(ag.account_name, "agent 1 account")
        self.assertEquals(ag.account_homePage, "http://adlnet.gov/agent/1")
        self.assertEquals(1, len(Agent.objects.all()))

        ag.delete()

        self.assertEquals(0, len(Agent.objects.all()))

    def test_agent_format(self):
        ot_s = "Agent"
        name_s = "superman"
        mbox_s = "mailto:superman@example.com"
        kwargs_s = {"objectType":ot_s,"name":name_s,"mbox":mbox_s}
        clark, created = Agent.objects.retrieve_or_create(**kwargs_s)
        self.assertTrue(created)
        clark.save()
        self.assertEquals(clark.objectType, ot_s)
        self.assertEquals(clark.name, name_s)
        self.assertEquals(clark.mbox, mbox_s)

        clark_exact = clark.to_dict()
        self.assertEquals(clark_exact['objectType'], ot_s)
        self.assertEquals(clark_exact['name'], name_s)
        self.assertEquals(clark_exact['mbox'], mbox_s)

        clark_ids = clark.to_dict(format='ids')
        self.assertFalse('objectType' in str(clark_ids), "object type was found in agent json")
        self.assertFalse('name' in str(clark_ids), "name was found in agent json")
        self.assertEquals(clark_ids['mbox'], mbox_s)

        ot_ww = "Agent"
        name_ww = "wonder woman"
        mbox_sha1sum_ww = hashlib.sha1("mailto:wonderwoman@example.com").hexdigest()
        kwargs_ww = {"objectType":ot_ww,"name":name_ww,"mbox_sha1sum":mbox_sha1sum_ww}
        diana, created = Agent.objects.retrieve_or_create(**kwargs_ww)
        self.assertTrue(created)
        diana.save()
        self.assertEquals(diana.objectType, ot_ww)
        self.assertEquals(diana.name, name_ww)
        self.assertEquals(diana.mbox_sha1sum, mbox_sha1sum_ww)

        diana_exact = diana.to_dict()
        self.assertEquals(diana_exact['objectType'], ot_ww)
        self.assertEquals(diana_exact['name'], name_ww)
        self.assertEquals(diana_exact['mbox_sha1sum'], mbox_sha1sum_ww)

        diana_ids = diana.to_dict(format='ids')
        self.assertFalse('objectType' in str(diana_ids), "object type was found in agent json")
        self.assertFalse('name' in str(diana_ids), "name was found in agent json")
        self.assertFalse('mbox' in diana_ids.items(), "mbox was found in agent json")
        self.assertEquals(diana_ids['mbox_sha1sum'], mbox_sha1sum_ww)

        ot_b = "Agent"
        name_b = "batman"
        openid_b = "id:batman"
        kwargs_b = {"objectType":ot_b,"name":name_b,"openid":openid_b}
        bruce, created = Agent.objects.retrieve_or_create(**kwargs_b)
        self.assertTrue(created)
        bruce.save()
        self.assertEquals(bruce.objectType, ot_b)
        self.assertEquals(bruce.name, name_b)
        self.assertEquals(bruce.openid, openid_b)

        bruce_exact = bruce.to_dict()
        self.assertEquals(bruce_exact['objectType'], ot_b)
        self.assertEquals(bruce_exact['name'], name_b)
        self.assertEquals(bruce_exact['openid'], openid_b)

        bruce_ids = bruce.to_dict(format='ids')
        self.assertFalse('objectType' in str(bruce_ids), "object type was found in agent json")
        self.assertFalse('name' in str(bruce_ids), "name was found in agent json")
        self.assertFalse('mbox' in str(bruce_ids), "mbox was found in agent json")
        self.assertFalse('mbox_sha1sum' in str(bruce_ids), "mbox_sha1sum was found in agent json")
        self.assertEquals(bruce_ids['openid'], openid_b)

        ot_f = "Agent"
        name_f = "the flash"
        account_f = {"homePage":"http://ultrasecret.justiceleague.com/accounts/", "name":"theflash"}
        kwargs_f = {"objectType":ot_f,"name":name_f,"account":account_f}
        barry, created = Agent.objects.retrieve_or_create(**kwargs_f)
        self.assertTrue(created)
        barry.save()
        self.assertEquals(barry.objectType, ot_f)
        self.assertEquals(barry.name, name_f)
        self.assertEquals(barry.account_homePage, account_f['homePage'])
        self.assertEquals(barry.account_name, account_f['name'])

        barry_exact = barry.to_dict()
        self.assertEquals(barry_exact['objectType'], ot_f)
        self.assertEquals(barry_exact['name'], name_f)
        self.assertEquals(barry_exact['account']['homePage'], account_f['homePage'])
        self.assertEquals(barry_exact['account']['name'], account_f['name'])

        barry_ids = barry.to_dict(format='ids')
        self.assertFalse('objectType' in str(barry_ids), "object type was found in agent json")
        self.assertFalse('name' in barry_ids.items(), "name was found in agent json")
        self.assertFalse('mbox' in barry_ids.items(), "mbox was found in agent json")
        self.assertFalse('mbox_sha1sum' in str(barry_ids), "mbox_sha1sum was found in agent json")
        self.assertFalse('openid' in str(barry_ids), "openid was found in agent json")
        self.assertEquals(barry_ids['account']['homePage'], account_f['homePage'])
        self.assertEquals(barry_ids['account']['name'], account_f['name'])

        ot_j = "Group"
        name_j = "Justice League"
        mbox_j = "mailto:justiceleague@example.com"
        kwargs_j = {"objectType":ot_j,"name":name_j,"mbox":mbox_j, "member":[kwargs_s,kwargs_ww,kwargs_f,kwargs_b]}
        justiceleague, created = Agent.objects.retrieve_or_create(**kwargs_j)
        self.assertTrue(created)
        justiceleague.save()
        self.assertEquals(justiceleague.objectType, ot_j)
        self.assertEquals(justiceleague.name, name_j)
        self.assertEquals(justiceleague.mbox, mbox_j)

        justiceleague_exact = justiceleague.to_dict()
        self.assertEquals(justiceleague_exact['objectType'], ot_j)
        self.assertEquals(justiceleague_exact['name'], name_j)
        self.assertEquals(justiceleague_exact['mbox'], mbox_j)

        justiceleague_ids = justiceleague.to_dict(format='ids')
        self.assertTrue('objectType' in str(justiceleague_ids), "object type was not found in group json")
        self.assertFalse('name' in str(justiceleague_ids), "name was found in agent json")
        self.assertEquals(justiceleague_ids['mbox'], mbox_j)

        badguy_ds = {"objectType":"Agent", "mbox":"mailto:darkseid@example.com", "name":"Darkseid"}
        badguy_m = {"objectType":"Agent", "mbox":"mailto:mantis@example.com", "name":"Mantis"}

        ot_bg = "Group"
        members_bg = [badguy_ds, badguy_m]
        kwargs_bg = {"objectType":ot_bg,"member":members_bg}
        badguys, created = Agent.objects.retrieve_or_create(**kwargs_bg)
        self.assertTrue(created)
        badguys.save()
        self.assertEquals(badguys.objectType, ot_bg)
        bg_members = badguys.member.all()
        self.assertEquals(len(bg_members), 2)
        for bg in bg_members:
            self.assertTrue(bg.name in str(kwargs_bg['member']))

        badguys_exact = badguys.to_dict()
        self.assertEquals(badguys_exact['objectType'], ot_bg)
        for m in badguys_exact['member']:
            if m['name'] == badguy_ds['name']:
                self.assertEquals(m['objectType'], badguy_ds['objectType'])
                self.assertEquals(m['mbox'], badguy_ds['mbox'])
            elif m['name'] == badguy_m['name']:
                self.assertEquals(m['objectType'], badguy_m['objectType'])
                self.assertEquals(m['mbox'], badguy_m['mbox'])
            else:
                self.fail("got an unexpected name: " % m['name'])

        badguys_ids = badguys.to_dict(format='ids')
        self.assertTrue('objectType' in str(badguys_ids), "object type was not found in group json")
        for m in badguys_ids['member']:
            self.assertFalse('objectType' in str(m), "object type was found in member agent")
            self.assertFalse('name' in str(m), "name was found in member agent")
            if m['mbox'] == badguy_ds['mbox']:
                self.assertEquals(m['mbox'], badguy_ds['mbox'])
            elif m['mbox'] == badguy_m['mbox']:
                self.assertEquals(m['mbox'], badguy_m['mbox'])
            else:
                self.fail("got an unexpected mbox: " % m['mbox'])
