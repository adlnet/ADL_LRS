import hashlib
import json
import base64

from django.test import TestCase
from django.urls import reverse
from django.conf import settings

from ..models import Agent, Statement

from adl_lrs.views import register


class AgentManagerTests(TestCase):

    @classmethod
    def setUpClass(cls):
        print("\n%s" % __name__)
        super(AgentManagerTests, cls).setUpClass()

    def setUp(self):
        self.username = "tester1"
        self.email = "test1@tester.com"
        self.password = "test"
        self.auth = "Basic %s" % base64.b64encode(
            "%s:%s" % (self.username, self.password))
        form = {"username": self.username, "email": self.email,
                "password": self.password, "password2": self.password}
        self.client.post(reverse(register), form,
                         X_Experience_API_Version=settings.XAPI_VERSION)

    def test_agent_mbox_create(self):
        stmt = json.dumps({"actor": {"objectType": "Agent", "mbox": "mailto:bob@example.com"},
                           "verb": {"id": "http://example.com/verbs/passed"},
                           "object": {'id': 'act://blah.com'}})

        response = self.client.post(reverse('lrs:statements'), stmt, content_type="application/json",
                                    Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)

        self.assertEqual(response.status_code, 200)
        st_id = json.loads(response.content)
        st = Statement.objects.get(statement_id=st_id[0])
        bob = st.actor
        self.assertEqual(bob.objectType, "Agent")
        self.assertFalse(bob.name)

    def test_agent_mbox_sha1sum_create(self):
        stmt = json.dumps({"actor": {"objectType": "Agent", "mbox_sha1sum": hashlib.sha1("mailto:bob@example.com").hexdigest()},
                           "verb": {"id": "http://example.com/verbs/passed"},
                           "object": {'id': 'act://blah.com'}})

        response = self.client.post(reverse('lrs:statements'), stmt, content_type="application/json",
                                    Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)

        self.assertEqual(response.status_code, 200)
        st_id = json.loads(response.content)
        st = Statement.objects.get(statement_id=st_id[0])
        bob = st.actor

        self.assertEqual(bob.mbox_sha1sum, hashlib.sha1(
            "mailto:bob@example.com").hexdigest())
        self.assertEqual(bob.objectType, "Agent")
        self.assertFalse(bob.name)
        self.assertFalse(bob.mbox)

    def test_agent_bogus_mbox_sha1sum_create(self):
        stmt = json.dumps({"actor": {"objectType": "Agent", "mbox_sha1sum": "notarealsum"},
                           "verb": {"id": "http://example.com/verbs/passed"},
                           "object": {'id': 'act://blah.com'}})

        response = self.client.post(reverse('lrs:statements'), stmt, content_type="application/json",
                                    Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.content, "mbox_sha1sum value [notarealsum] is not a valid sha1sum")

    def test_agent_openID_create(self):
        stmt = json.dumps({"actor": {"objectType": "Agent", "openid": "http://bob.openid.com"},
                           "verb": {"id": "http://example.com/verbs/passed"},
                           "object": {'id': 'act://blah.com'}})

        response = self.client.post(reverse('lrs:statements'), stmt, content_type="application/json",
                                    Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)

        self.assertEqual(response.status_code, 200)
        st_id = json.loads(response.content)
        st = Statement.objects.get(statement_id=st_id[0])
        bob = st.actor

        self.assertEqual(bob.openid, "http://bob.openid.com")
        self.assertEqual(bob.objectType, "Agent")
        self.assertFalse(bob.name)
        self.assertFalse(bob.mbox)
        self.assertFalse(bob.mbox_sha1sum)

    def test_agent_account_create(self):
        stmt = json.dumps({"actor": {"objectType": "Agent", "account": {"homePage": "http://www.adlnet.gov", "name": "freakshow"}},
                           "verb": {"id": "http://example.com/verbs/passed"},
                           "object": {'id': 'act://blah.com'}})

        response = self.client.post(reverse('lrs:statements'), stmt, content_type="application/json",
                                    Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)

        self.assertEqual(response.status_code, 200)
        st_id = json.loads(response.content)
        st = Statement.objects.get(statement_id=st_id[0])
        bob = st.actor

        self.assertEqual(bob.account_name, "freakshow")
        self.assertEqual(bob.account_homePage, "http://www.adlnet.gov")
        self.assertFalse(bob.name)
        self.assertFalse(bob.mbox)
        self.assertFalse(bob.mbox_sha1sum)
        self.assertFalse(bob.openid)

    def test_agent_kwargs_basic(self):
        ot = "Agent"
        name = "bob bobson"
        mbox = "mailto:bobbobson@example.com"
        kwargs = {"objectType": ot, "name": name, "mbox": mbox}
        bob, created = Agent.objects.retrieve_or_create(**kwargs)
        self.assertTrue(created)
        bob.save()
        self.assertEqual(bob.objectType, ot)
        self.assertEqual(bob.name, name)
        self.assertEqual(bob.mbox, mbox)

        bob2, created = Agent.objects.retrieve_or_create(**kwargs)
        self.assertFalse(created)
        self.assertEqual(bob.pk, bob2.pk)
        self.assertEqual(bob, bob2)

        kwargs['mbox'] = "mailto:bob.secret@example.com"
        bob3, created = Agent.objects.retrieve_or_create(**kwargs)
        self.assertTrue(created)
        bob3.save()
        self.assertNotEqual(bob.pk, bob3.pk)

    def test_agent_kwargs_basic_account(self):
        ot = "Agent"
        name = "bob bobson"
        account = {"homePage": "http://www.adlnet.gov", "name": "freakshow"}
        kwargs = {"objectType": ot, "name": name, "account": account}
        bob, created = Agent.objects.retrieve_or_create(**kwargs)
        self.assertTrue(created)
        self.assertEqual(bob.objectType, ot)
        self.assertEqual(bob.name, name)
        self.assertEqual(bob.account_homePage, "http://www.adlnet.gov")
        self.assertEqual(bob.account_name, "freakshow")

    def test_group_kwargs(self):
        ot = "Agent"
        name = "bob bobson"
        kwargs = {"objectType": ot, "name": name,
                  "mbox": "mailto:bob@example.com"}
        bob, created = Agent.objects.retrieve_or_create(**kwargs)

        ot = "Agent"
        name = "john johnson"
        kwargs = {"objectType": ot, "name": name,
                  "mbox": "mailto:john@example.com"}
        john, created = Agent.objects.retrieve_or_create(**kwargs)

        ot = "Group"
        members = [{"name": "bob bobson", "mbox": "mailto:bob@example.com"},
                   {"name": "john johnson", "mbox": "mailto:john@example.com"}]

        kwargs = {"objectType": ot, "member": members}
        gr, created = Agent.objects.retrieve_or_create(**kwargs)
        # Already created from above
        self.assertTrue(created)

        kwargs1 = {"objectType": ot, "member": members, "name": "my group"}
        gr1, created = Agent.objects.retrieve_or_create(**kwargs1)
        # creates another one b/c of adding a name
        self.assertTrue(created)
        self.assertEqual(gr1.name, "my group")
        agents = Agent.objects.all()
        # 5 total agents - an extra one for the user
        self.assertEqual(len(agents), 5)
        self.assertEqual(len(agents.filter(objectType='Group')), 2)
        # 3 agents - an extra one for the user
        self.assertEqual(len(agents.filter(objectType='Agent')), 3)

    def test_agent_json_no_ids(self):
        stmt = json.dumps({"actor": {"objectType": "Agent", "name": "freakshow"},
                           "verb": {"id": "http://example.com/verbs/passed"},
                           "object": {'id': 'act://blah.com'}})

        response = self.client.post(reverse('lrs:statements'), stmt, content_type="application/json",
                                    Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.content, 'One and only one of mbox, mbox_sha1sum, openid, account may be supplied with an Agent')

    def test_agent_json_many_ids(self):
        stmt = json.dumps({"actor": {"objectType": "Agent", "mbox": "mailto:bob@example.com", "openid": "bob.bobson.openid.org"},
                           "verb": {"id": "http://example.com/verbs/passed"},
                           "object": {'id': 'act://blah.com'}})

        response = self.client.post(reverse('lrs:statements'), stmt, content_type="application/json",
                                    Authorization=self.auth, X_Experience_API_Version=settings.XAPI_VERSION)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.content, 'One and only one of mbox, mbox_sha1sum, openid, account may be supplied with an Agent')

    def test_group(self):
        ot = "Group"
        name = "the group"
        mbox = "mailto:the.group@example.com"
        members = [{"name": "agent1", "mbox": "mailto:agent1@example.com"},
                   {"name": "agent2", "mbox": "mailto:agent2@example.com"}]
        kwargs = {"objectType": ot, "name": name,
                  "mbox": mbox, "member": members}
        g, created = Agent.objects.retrieve_or_create(**kwargs)
        self.assertTrue(created)
        self.assertEqual(g.name, name)
        self.assertEqual(g.mbox, mbox)
        mems = g.member.values_list('name', flat=True)
        self.assertEqual(len(mems), 2)
        self.assertIn('agent1', mems)
        self.assertIn('agent2', mems)
        gr_dict = g.to_dict()
        self.assertEqual(gr_dict['objectType'], 'Group')

        for member in gr_dict['member']:
            self.assertEqual(member['objectType'], 'Agent')
            if member['name'] == 'agent1':
                self.assertEqual(member['mbox'], 'mailto:agent1@example.com')
            elif member['name'] == 'agent2':
                self.assertEqual(member['mbox'], 'mailto:agent2@example.com')

    def test_group_from_agent_object(self):
        ot = "Group"
        name = "the group"
        mbox = "mailto:the.group@example.com"
        members = [{"name": "agent1", "mbox": "mailto:agent1@example.com"},
                   {"name": "agent2", "mbox": "mailto:agent2@example.com"}]
        kwargs = {"objectType": ot, "name": name,
                  "mbox": mbox, "member": members}
        g = Agent.objects.retrieve_or_create(**kwargs)[0]
        self.assertEqual(g.name, name)
        self.assertEqual(g.mbox, mbox)
        mems = g.member.values_list('name', flat=True)
        self.assertEqual(len(mems), 2)
        self.assertIn('agent1', mems)
        self.assertIn('agent2', mems)

    def test_group_from_agent_string(self):
        ot = "Group"
        name = "the group"
        mbox = "mailto:the.group@example.com"
        members = [{"name": "agent1", "mbox": "mailto:agent1@example.com"},
                   {"name": "agent2", "mbox": "mailto:agent2@example.com"}]
        kwargs = {"objectType": ot, "name": name,
                  "mbox": mbox, "member": members}
        g = Agent.objects.retrieve_or_create(**kwargs)[0]
        self.assertEqual(g.name, name)
        self.assertEqual(g.mbox, mbox)
        mems = g.member.values_list('name', flat=True)
        self.assertEqual(len(mems), 2)
        self.assertIn('agent1', mems)
        self.assertIn('agent2', mems)

    def test_agent_format(self):
        ot_s = "Agent"
        name_s = "superman"
        mbox_s = "mailto:superman@example.com"
        kwargs_s = {"objectType": ot_s, "name": name_s, "mbox": mbox_s}
        clark, created = Agent.objects.retrieve_or_create(**kwargs_s)
        self.assertTrue(created)
        clark.save()
        self.assertEqual(clark.objectType, ot_s)
        self.assertEqual(clark.name, name_s)
        self.assertEqual(clark.mbox, mbox_s)

        clark_exact = clark.to_dict()
        self.assertEqual(clark_exact['objectType'], ot_s)
        self.assertEqual(clark_exact['name'], name_s)
        self.assertEqual(clark_exact['mbox'], mbox_s)

        clark_ids = clark.to_dict(ids_only=True)
        self.assertTrue('objectType' in str(clark_ids),
                         "objectType was found in agent json")
        self.assertFalse('name' in str(clark_ids),
                         "name was found in agent json")
        self.assertEqual(clark_ids['mbox'], mbox_s)

        ot_ww = "Agent"
        name_ww = "wonder woman"
        mbox_sha1sum_ww = hashlib.sha1(
            "mailto:wonderwoman@example.com").hexdigest()
        kwargs_ww = {"objectType": ot_ww, "name": name_ww,
                     "mbox_sha1sum": mbox_sha1sum_ww}
        diana, created = Agent.objects.retrieve_or_create(**kwargs_ww)
        self.assertTrue(created)
        diana.save()
        self.assertEqual(diana.objectType, ot_ww)
        self.assertEqual(diana.name, name_ww)
        self.assertEqual(diana.mbox_sha1sum, mbox_sha1sum_ww)

        diana_exact = diana.to_dict()
        self.assertEqual(diana_exact['objectType'], ot_ww)
        self.assertEqual(diana_exact['name'], name_ww)
        self.assertEqual(diana_exact['mbox_sha1sum'], mbox_sha1sum_ww)

        diana_ids = diana.to_dict(ids_only=True)
        self.assertTrue('objectType' in str(diana_ids),
                         "objectType was not found in agent json")
        self.assertFalse('name' in str(diana_ids),
                         "name was found in agent json")
        self.assertFalse('mbox' in list(diana_ids.items()),
                         "mbox was found in agent json")
        self.assertEqual(diana_ids['mbox_sha1sum'], mbox_sha1sum_ww)

        ot_b = "Agent"
        name_b = "batman"
        openid_b = "id:batman"
        kwargs_b = {"objectType": ot_b, "name": name_b, "openid": openid_b}
        bruce, created = Agent.objects.retrieve_or_create(**kwargs_b)
        self.assertTrue(created)
        bruce.save()
        self.assertEqual(bruce.objectType, ot_b)
        self.assertEqual(bruce.name, name_b)
        self.assertEqual(bruce.openid, openid_b)

        bruce_exact = bruce.to_dict()
        self.assertEqual(bruce_exact['objectType'], ot_b)
        self.assertEqual(bruce_exact['name'], name_b)
        self.assertEqual(bruce_exact['openid'], openid_b)

        bruce_ids = bruce.to_dict(ids_only=True)
        self.assertTrue('objectType' in str(bruce_ids),
                         "objectType was not found in agent json")
        self.assertFalse('name' in str(bruce_ids),
                         "name was found in agent json")
        self.assertFalse('mbox' in str(bruce_ids),
                         "mbox was found in agent json")
        self.assertFalse('mbox_sha1sum' in str(bruce_ids),
                         "mbox_sha1sum was found in agent json")
        self.assertEqual(bruce_ids['openid'], openid_b)

        ot_f = "Agent"
        name_f = "the flash"
        account_f = {
            "homePage": "http://ultrasecret.justiceleague.com/accounts/", "name": "theflash"}
        kwargs_f = {"objectType": ot_f, "name": name_f, "account": account_f}
        barry, created = Agent.objects.retrieve_or_create(**kwargs_f)
        self.assertTrue(created)
        barry.save()
        self.assertEqual(barry.objectType, ot_f)
        self.assertEqual(barry.name, name_f)
        self.assertEqual(barry.account_homePage, account_f['homePage'])
        self.assertEqual(barry.account_name, account_f['name'])

        barry_exact = barry.to_dict()
        self.assertEqual(barry_exact['objectType'], ot_f)
        self.assertEqual(barry_exact['name'], name_f)
        self.assertEqual(barry_exact['account'][
                          'homePage'], account_f['homePage'])
        self.assertEqual(barry_exact['account']['name'], account_f['name'])

        barry_ids = barry.to_dict(ids_only=True)
        self.assertTrue('objectType' in str(barry_ids),
                         "objectType was not found in agent json")
        self.assertFalse('name' in list(barry_ids.items()),
                         "name was found in agent json")
        self.assertFalse('mbox' in list(barry_ids.items()),
                         "mbox was found in agent json")
        self.assertFalse('mbox_sha1sum' in str(barry_ids),
                         "mbox_sha1sum was found in agent json")
        self.assertFalse('openid' in str(barry_ids),
                         "openid was found in agent json")
        self.assertEqual(barry_ids['account'][
                          'homePage'], account_f['homePage'])
        self.assertEqual(barry_ids['account']['name'], account_f['name'])

        ot_j = "Group"
        name_j = "Justice League"
        mbox_j = "mailto:justiceleague@example.com"
        kwargs_j = {"objectType": ot_j, "name": name_j, "mbox": mbox_j,
                    "member": [kwargs_s, kwargs_ww, kwargs_f, kwargs_b]}
        justiceleague, created = Agent.objects.retrieve_or_create(**kwargs_j)
        self.assertTrue(created)
        justiceleague.save()
        self.assertEqual(justiceleague.objectType, ot_j)
        self.assertEqual(justiceleague.name, name_j)
        self.assertEqual(justiceleague.mbox, mbox_j)

        justiceleague_exact = justiceleague.to_dict()
        self.assertEqual(justiceleague_exact['objectType'], ot_j)
        self.assertEqual(justiceleague_exact['name'], name_j)
        self.assertEqual(justiceleague_exact['mbox'], mbox_j)

        justiceleague_ids = justiceleague.to_dict(ids_only=True)
        self.assertTrue('objectType' in str(justiceleague_ids),
                        "objectType was not found in group json")
        self.assertFalse('name' in str(justiceleague_ids),
                         "name was found in agent json")
        self.assertEqual(justiceleague_ids['mbox'], mbox_j)

        badguy_ds = {"objectType": "Agent",
                     "mbox": "mailto:darkseid@example.com", "name": "Darkseid"}
        badguy_m = {"objectType": "Agent",
                    "mbox": "mailto:mantis@example.com", "name": "Mantis"}

        ot_bg = "Group"
        members_bg = [badguy_ds, badguy_m]
        kwargs_bg = {"objectType": ot_bg, "member": members_bg}
        badguys, created = Agent.objects.retrieve_or_create(**kwargs_bg)
        self.assertTrue(created)
        badguys.save()
        self.assertEqual(badguys.objectType, ot_bg)
        bg_members = badguys.member.all()
        self.assertEqual(len(bg_members), 2)
        for bg in bg_members:
            self.assertTrue(bg.name in str(kwargs_bg['member']))

        badguys_exact = badguys.to_dict()
        self.assertEqual(badguys_exact['objectType'], ot_bg)
        for m in badguys_exact['member']:
            if m['name'] == badguy_ds['name']:
                self.assertEqual(m['objectType'], badguy_ds['objectType'])
                self.assertEqual(m['mbox'], badguy_ds['mbox'])
            elif m['name'] == badguy_m['name']:
                self.assertEqual(m['objectType'], badguy_m['objectType'])
                self.assertEqual(m['mbox'], badguy_m['mbox'])
            else:
                self.fail("got an unexpected name: " % m['name'])

        badguys_ids = badguys.to_dict(ids_only=True)
        self.assertTrue('objectType' in str(badguys_ids),
                        "objectType was not found in group json")
        for m in badguys_ids['member']:
            self.assertTrue('objectType' in str(
                m), "objectType was not found in member agent")
            self.assertFalse('name' in str(
                m), "name was found in member agent")
            if m['mbox'] == badguy_ds['mbox']:
                self.assertEqual(m['mbox'], badguy_ds['mbox'])
            elif m['mbox'] == badguy_m['mbox']:
                self.assertEqual(m['mbox'], badguy_m['mbox'])
            else:
                self.fail("got an unexpected mbox: " % m['mbox'])
