import ast
import json
import uuid
from collections import OrderedDict

from django.db import models, IntegrityError
from django.db.models.signals import post_save
from django.contrib.auth.models import User
from django.contrib.postgres.fields import JSONField
from django.core.files.storage import FileSystemStorage
from django.utils import timezone

from oauth_provider.consts import MAX_URL_LENGTH

from .exceptions import BadRequest
from .utils import get_lang

AGENT_PROFILE_UPLOAD_TO = "agent_profile"
ACTIVITY_STATE_UPLOAD_TO = "activity_state"
ACTIVITY_PROFILE_UPLOAD_TO = "activity_profile"
STATEMENT_ATTACHMENT_UPLOAD_TO = "attachment_payloads"

# Called when a user is created, saved, or logging in.
def attach_user(sender, **kwargs):
    user = kwargs["instance"]
    if kwargs["created"]:
        agent = Agent.objects.retrieve_or_create(
            **{'name': user.username, 'mbox': 'mailto:%s' % user.email, 'objectType': 'Agent'})[0]
        agent.user = user
        agent.save()
post_save.connect(attach_user, sender=User)


class Verb(models.Model):
    verb_id = models.CharField(
        max_length=MAX_URL_LENGTH, db_index=True, unique=True)
    canonical_data = JSONField(default=dict)

    def return_verb_with_lang(self, lang=None, ids_only=False):
        if ids_only:
            return {'id': self.verb_id}
        ret = OrderedDict(self.canonical_data)
        if 'display' in ret and ret['display'].items():
            ret['display'] = get_lang(self.canonical_data['display'], lang)
        return ret

    def get_a_name(self):
        if 'display' in self.canonical_data:
            return self.canonical_data['display'].get('en-US', self.verb_id)
        return self.verb_id

    def __unicode__(self):
        return json.dumps(self.canonical_data, sort_keys=False)


class AgentManager(models.Manager):

    def retrieve(self, **kwargs):
        agent_ifps_can_only_be_one = [
            'mbox', 'mbox_sha1sum', 'account', 'openid']
        ifp_sent = [
            a for a in agent_ifps_can_only_be_one if kwargs.get(a, None) is not None]
        if ifp_sent:
            # Get IFP
            ifp = ifp_sent[0]
            ifp_dict = {}
            # If IFP is account, have to set the kwargs keys differently since they have different
            # field names
            if not 'account' == ifp:
                ifp_dict[ifp] = kwargs[ifp]
            else:
                # Set ifp_dict and kwargs
                ifp_dict['account_homePage'] = kwargs['account']['homePage']
                ifp_dict['account_name'] = kwargs['account']['name']
            try:
                # Try getting agent by IFP in ifp_dict
                agent = Agent.objects.filter(**ifp_dict)[0]
                return agent
            except IndexError:
                return None
        else:
            return None

    def retrieve_or_create(self, **kwargs):
        agent_ifps_can_only_be_one = [
            'mbox', 'mbox_sha1sum', 'account', 'openid']
        ifp_sent = [
            a for a in agent_ifps_can_only_be_one if kwargs.get(a, None) is not None]
        is_group = kwargs.get('objectType', None) == "Group"
        has_member = False
        # Set member if incoming group
        if is_group:
            member = kwargs.pop('member', None)
            if member:
                has_member = True
        # Create agent based on IFP
        if ifp_sent:
            # Get IFP
            ifp = ifp_sent[0]
            ifp_dict = {}
            # If IFP is account, have to set the kwargs keys differently since they have different
            # field names
            if not 'account' == ifp:
                ifp_dict[ifp] = kwargs[ifp]
            else:
                # Set ifp_dict and kwargs
                ifp_dict['account_homePage'] = kwargs['account']['homePage']
                kwargs['account_homePage'] = kwargs['account']['homePage']
                ifp_dict['account_name'] = kwargs['account']['name']
                kwargs['account_name'] = kwargs['account']['name']
                del kwargs['account']
            try:
                # Try getting agent by IFP in ifp_dict
                agent = Agent.objects.filter(**ifp_dict)[0]
                created = False
            except IndexError:
                # If DNE create the agent based off of kwargs (kwargs now
                # includes account_homePage and account_name fields)
                try:
                    agent = Agent.objects.create(**kwargs)
                    created = True
                except (IntegrityError, ValidationError):
                    # Try getting agent by IFP in ifp_dict
                    agent = Agent.objects.filter(**ifp_dict)[0]
                    created = False

            # For identified groups with members
            if is_group and has_member:
                # If newly created identified group add all of the incoming
                # members
                if created:
                    members = [self.retrieve_or_create(**a) for a in member]
                    agent.member.add(*(a for a, c in members))
                    agent.save()
        # Only way it doesn't have IFP is if anonymous group
        else:
            agent, created = self.retrieve_or_create_anonymous_group(
                member, kwargs)
        return agent, created

    def retrieve_or_create_anonymous_group(self, member, kwargs):
        # Narrow oauth down to 2 members and one member having an account
        if len(member) == 2 and ('account' in member[0] or 'account' in member[1]):
            # If oauth account is in first member
            if 'account' in member[0] and 'OAuth' in member[0]['account']['homePage']:
                created_oauth_identifier = "anongroup:%s-%s" % (
                    member[0]['account']['name'], member[1]['mbox'])
                try:
                    agent = Agent.objects.get(
                        oauth_identifier=created_oauth_identifier)
                    created = False
                except Agent.DoesNotExist:
                    try:
                        agent = Agent.objects.create(**kwargs)
                        created = True
                    except (IntegrityError, ValidationError):
                        agent = Agent.objects.get(
                            oauth_identifier=created_oauth_identifier)
                        created = False
            # If oauth account is in second member
            elif 'account' in member[1] and 'OAuth' in member[1]['account']['homePage']:
                created_oauth_identifier = "anongroup:%s-%s" % (
                    member[1]['account']['name'], member[0]['mbox'])
                try:
                    agent = Agent.objects.get(
                        oauth_identifier=created_oauth_identifier)
                    created = False
                except Agent.DoesNotExist:
                    try:
                        agent = Agent.objects.create(**kwargs)
                        created = True
                    except (IntegrityError, ValidationError):
                        agent = Agent.objects.get(
                            oauth_identifier=created_oauth_identifier)
                        created = False
            # Non-oauth anonymous group that has 2 members, one having an
            # account
            else:
                agent = Agent.objects.create(**kwargs)
                created = True
        # Normal non-oauth anonymous group
        else:
            agent = Agent.objects.create(**kwargs)
            created = True
        # If it is a newly created anonymous group, add the members
        if created:
            members = [self.retrieve_or_create(**a) for a in member]
            agent.member.add(*(a for a, c in members))
        return agent, created

    def oauth_group(self, **kwargs):
        try:
            g = Agent.objects.get(oauth_identifier=kwargs['oauth_identifier'])
            return g, False
        except Agent.DoesNotExist:
            return Agent.objects.retrieve_or_create(**kwargs)


class Agent(models.Model):
    objectType = models.CharField(max_length=6, blank=True, default="Agent")
    name = models.CharField(max_length=100, blank=True)
    mbox = models.CharField(
        max_length=128, db_index=True, null=True, unique=True)
    mbox_sha1sum = models.CharField(
        max_length=40, db_index=True, null=True, unique=True)
    openid = models.CharField(
        max_length=MAX_URL_LENGTH, db_index=True, null=True, unique=True)
    oauth_identifier = models.CharField(
        max_length=192, db_index=True, null=True, unique=True)
    member = models.ManyToManyField('self', related_name="agents")
    account_homePage = models.CharField(max_length=MAX_URL_LENGTH, null=True)
    account_name = models.CharField(max_length=50, null=True)
    user = models.OneToOneField(User, on_delete=models.SET_NULL, null=True)
    objects = AgentManager()

    class Meta:
        unique_together = ("account_homePage", "account_name")

    def to_dict(self, ids_only=False):
        ret = OrderedDict()
        if self.mbox:
            ret['mbox'] = self.mbox
        if self.mbox_sha1sum:
            ret['mbox_sha1sum'] = self.mbox_sha1sum
        if self.openid:
            ret['openid'] = self.openid
        if self.account_name:
            ret['account'] = OrderedDict()
            ret['account']['name'] = self.account_name
            ret['account']['homePage'] = self.account_homePage
        if self.objectType == 'Group':
            ret['objectType'] = self.objectType
            # Show members for groups if ids_only is false.
            # Show members' ids for anon groups if ids_only is true.
            if not ids_only or not (set(['mbox', 'mbox_sha1sum', 'openid', 'account']) & set(ret.keys())):
                if self.member.all():
                    ret['member'] = [a.to_dict(ids_only)
                                     for a in self.member.all()]

        ret['objectType'] = self.objectType
        if self.name and not ids_only:
            ret['name'] = self.name
        return ret

    # Used only for /agent GET endpoint (check spec)
    def to_dict_person(self):
        ret = OrderedDict()
        ret['objectType'] = "Person"
        if self.name:
            ret['name'] = [self.name]
        if self.mbox:
            ret['mbox'] = [self.mbox]
        if self.mbox_sha1sum:
            ret['mbox_sha1sum'] = [self.mbox_sha1sum]
        if self.openid:
            ret['openid'] = [self.openid]
        if self.account_name:
            ret['account'] = []
            acc = OrderedDict()
            acc['name'] = self.account_name
            acc['homePage'] = self.account_homePage
            ret['account'].append(acc)
        return ret

    def get_a_name(self):
        if self.name:
            return self.name
        if self.mbox:
            return self.mbox
        if self.mbox_sha1sum:
            return self.mbox_sha1sum
        if self.openid:
            return self.openid
        if self.account_name:
            return self.account_name
        if self.objectType == 'Agent':
            return "unknown"
        else:
            return "anonymous group"

    def get_user_from_oauth_group(self):
        if self.oauth_identifier:
            if self.member.all()[0].account_homePage:
                return self.member.all()[1]
            else:
                return self.member.all()[0]
        return None

    def __unicode__(self):
        return json.dumps(self.to_dict(), sort_keys=False)


class RelevantType(models.Model):
    relevantType = models.CharField(max_length=MAX_URL_LENGTH, blank=True, db_index=True)


class ContextAgent(models.Model):
    objectType = models.CharField(max_length=14, blank=True, default="contextAgent")
    agent = models.ForeignKey(
        Agent, related_name="conag_agent", on_delete=models.SET_NULL, blank=True, db_index=True, null=True)
    relevantType = models.ManyToManyField(RelevantType, related_name="conag_relevantType")

    def to_dict(self, ids_only=False):
        ret = OrderedDict()
        if self.agent:
            ret['agent'] = self.agent.to_dict(ids_only)
        if self.relevantType.all():
            ret['relevantType'] = [relType.relevantType for relType in self.relevantType.all()]

        ret['objectType'] = self.objectType

        return ret


class ContextGroup(models.Model):
    objectType = models.CharField(max_length=14, blank=True, default="contextGroup")
    group = models.ForeignKey(
        Agent, related_name="congrp_group", on_delete=models.SET_NULL, blank=True, db_index=True, null=True)
    relevantType = models.ManyToManyField(RelevantType, related_name="congrp_relevantType")

    def to_dict(self, ids_only=False):
        ret = OrderedDict()
        if self.group:
            ret['group'] = self.group.to_dict(ids_only)
        if self.relevantType.all():
            ret['relevantType'] = [relType.relevantType for relType in self.relevantType.all()]

        ret['objectType'] = self.objectType

        return ret


class Activity(models.Model):
    activity_id = models.CharField(
        max_length=MAX_URL_LENGTH, db_index=True, unique=True)
    canonical_data = JSONField(default=dict)
    authority = models.ForeignKey(Agent, null=True)

    def return_activity_with_lang_format(self, lang=None, ids_only=False):
        if ids_only:
            return {'id': self.activity_id}
        ret = self.canonical_data
        if 'objectType' not in self.canonical_data:
            ret['objectType'] = 'Activity'
        if 'definition' in self.canonical_data:
            if 'name' in ret['definition'] and ret['definition']['name'].items():
                ret['definition']['name'] = get_lang(
                    ret['definition']['name'], lang)
            if 'description' in ret['definition'] and ret['definition']['description'].items():
                ret['definition']['description'] = get_lang(
                    ret['definition']['description'], lang)
            if 'scale' in ret['definition']:
                for s in ret['definition']['scale']:
                    if s.items():
                        s['description'] = get_lang(s['description'], lang)
            if 'choices' in ret['definition']:
                for c in ret['definition']['choices']:
                    if c.items():
                        c['description'] = get_lang(c['description'], lang)
            if 'steps' in ret['definition']:
                for st in ret['definition']['steps']:
                    if st.items:
                        st['description'] = get_lang(st['description'], lang)
            if 'source' in ret['definition']:
                for so in ret['definition']['source']:
                    if so.items:
                        so['description'] = get_lang(so['description'], lang)
                for t in ret['definition']['target']:
                    if t.items():
                        t['description'] = get_lang(t['description'], lang)
        return ret

    def get_a_name(self):
        if 'definition' in self.canonical_data:
            return self.canonical_data['definition'].get('en-US', self.activity_id)
        else:
            return self.activity_id

    def __unicode__(self):
        return json.dumps(self.canonical_data, sort_keys=False)


class SubStatement(models.Model):
    object_agent = models.ForeignKey(
        Agent, related_name="object_of_substatement", on_delete=models.SET_NULL, null=True, db_index=True)
    object_activity = models.ForeignKey(
        Activity, related_name="object_of_substatement", on_delete=models.SET_NULL, null=True, db_index=True)
    object_statementref = models.UUIDField(
        null=True, editable=False, db_index=True)
    actor = models.ForeignKey(
        Agent, related_name="actor_of_substatement", null=True, on_delete=models.SET_NULL)
    verb = models.ForeignKey(Verb, null=True, on_delete=models.SET_NULL)
    result_success = models.NullBooleanField()
    result_completion = models.NullBooleanField()
    result_response = models.TextField(blank=True)
    result_duration = models.CharField(max_length=40, blank=True)
    result_score_scaled = models.FloatField(blank=True, null=True)
    result_score_raw = models.FloatField(blank=True, null=True)
    result_score_min = models.FloatField(blank=True, null=True)
    result_score_max = models.FloatField(blank=True, null=True)
    result_extensions = JSONField(default=dict, blank=True)
    timestamp = models.DateTimeField(null=True)
    context_registration = models.CharField(
        max_length=40, blank=True, db_index=True)
    context_instructor = models.ForeignKey(Agent, blank=True, null=True, on_delete=models.SET_NULL,
                                           db_index=True, related_name='substatement_context_instructor')
    context_team = models.ForeignKey(Agent, blank=True, null=True, on_delete=models.SET_NULL,
                                     related_name="substatement_context_team")
    context_revision = models.TextField(blank=True)
    context_platform = models.CharField(max_length=50, blank=True)
    context_language = models.CharField(max_length=50, blank=True)
    context_extensions = JSONField(default=dict, blank=True)
    context_ca_parent = models.ManyToManyField(
        Activity, related_name="sub_context_ca_parent")
    context_ca_grouping = models.ManyToManyField(
        Activity, related_name="sub_context_ca_grouping")
    context_ca_category = models.ManyToManyField(
        Activity, related_name="sub_context_ca_category")
    context_ca_other = models.ManyToManyField(
        Activity, related_name="sub_context_ca_other")
    context_contextAgents = models.ManyToManyField(
        ContextAgent, related_name="sub_context_contextAgent")
    context_contextGroups = models.ManyToManyField(
        ContextGroup, related_name="sub_context_contextGroup")
        
    # Context also has a stmt field which is a StatementRef.
    context_statement = models.CharField(max_length=40, blank=True)

    def to_dict(self, lang=None, ids_only=False):
        ret = OrderedDict()
        ret['actor'] = self.actor.to_dict(ids_only)
        ret['verb'] = self.verb.return_verb_with_lang(lang, ids_only)

        if self.object_agent:
            ret['object'] = self.object_agent.to_dict(ids_only)
        elif self.object_activity:
            ret['object'] = self.object_activity.return_activity_with_lang_format(
                lang, ids_only)
        else:
            ret['object'] = {
                'id': str(self.object_statementref), 'objectType': 'StatementRef'}

        ret['result'] = OrderedDict()
        if self.result_success is not None:
            ret['result']['success'] = self.result_success
        if self.result_completion is not None:
            ret['result']['completion'] = self.result_completion
        if self.result_response:
            ret['result']['response'] = self.result_response
        if self.result_duration:
            ret['result']['duration'] = self.result_duration

        ret['result']['score'] = OrderedDict()
        if self.result_score_scaled is not None:
            ret['result']['score']['scaled'] = self.result_score_scaled
        if self.result_score_raw is not None:
            ret['result']['score']['raw'] = self.result_score_raw
        if self.result_score_min is not None:
            ret['result']['score']['min'] = self.result_score_min
        if self.result_score_max is not None:
            ret['result']['score']['max'] = self.result_score_max
        # If there is no score, delete from dict
        if not ret['result']['score']:
            del ret['result']['score']
        if self.result_extensions:
            ret['result']['extensions'] = self.result_extensions
        # If no result, delete from dict
        if not ret['result']:
            del ret['result']

        ret['context'] = OrderedDict()
        if self.context_registration:
            ret['context']['registration'] = self.context_registration
        if self.context_instructor:
            ret['context'][
                'instructor'] = self.context_instructor.to_dict(ids_only)
        if self.context_team:
            ret['context']['team'] = self.context_team.to_dict(ids_only)
        if self.context_revision:
            ret['context']['revision'] = self.context_revision
        if self.context_platform:
            ret['context']['platform'] = self.context_platform
        if self.context_language:
            ret['context']['language'] = self.context_language
        if self.context_statement:
            ret['context']['statement'] = {
                'id': self.context_statement, 'objectType': 'StatementRef'}

        ret['context']['contextActivities'] = OrderedDict()
        if self.context_ca_parent.all():
            ret['context']['contextActivities']['parent'] = [cap.return_activity_with_lang_format(
                lang, ids_only) for cap in self.context_ca_parent.all()]
        if self.context_ca_grouping.all():
            ret['context']['contextActivities']['grouping'] = [cag.return_activity_with_lang_format(
                lang, ids_only) for cag in self.context_ca_grouping.all()]
        if self.context_ca_category.all():
            ret['context']['contextActivities']['category'] = [cac.return_activity_with_lang_format(
                lang, ids_only) for cac in self.context_ca_category.all()]
        if self.context_ca_other.all():
            ret['context']['contextActivities']['other'] = [cao.return_activity_with_lang_format(
                lang, ids_only) for cao in self.context_ca_other.all()]
        if self.context_extensions:
            ret['context']['extensions'] = self.context_extensions
        if not ret['context']['contextActivities']:
            del ret['context']['contextActivities']

        ret['context']['contextAgents'] = []
        if self.context_contextAgents.all():
            ret['context']['contextAgents'] = [conag.context_contextAgents.to_dict(ids_only) for conag in self.context_contextAgents.all()]
        if not ret['context']['contextAgents']:
            del ret['context']['contextAgents']

        ret['context']['contextGroups'] = []
        if self.context_contextGroups.all():
            ret['context']['contextGroups'] = [congrp.context_contextGroups.to_dict(ids_only) for congrp in self.context_contextGroups.all()]
        if not ret['context']['contextGroups']:
            del ret['context']['contextGroups']

        if not ret['context']:
            del ret['context']

        if self.timestamp:
            ret['timestamp'] = self.timestamp.isoformat()
        ret['objectType'] = "SubStatement"
        return ret

    def get_a_name(self):
        if self.object_activity:
            return self.object_activity.get_a_name()
        elif self.object_agent:
            return self.object_agent.get_a_name()
        else:
            return str(self.object_statementref)

    def get_object(self):
        if self.object_activity:
            stmt_object = self.object_activity
        elif self.object_agent:
            stmt_object = self.object_agent
        else:
            stmt_object = {
                'id': str(self.object_statementref), 'objectType': 'StatementRef'}
        return stmt_object

    def __unicode__(self):
        return json.dumps(self.to_dict(), sort_keys=False)


class Statement(models.Model):
    # If no statement_id is given, will create one automatically
    statement_id = models.UUIDField(
        default=uuid.uuid4, db_index=True, editable=False)
    object_agent = models.ForeignKey(
        Agent, related_name="object_of_statement", null=True, on_delete=models.SET_NULL, db_index=True)
    object_activity = models.ForeignKey(
        Activity, related_name="object_of_statement", null=True, on_delete=models.SET_NULL, db_index=True)
    object_substatement = models.ForeignKey(
        SubStatement, related_name="object_of_statement", null=True, on_delete=models.SET_NULL)
    object_statementref = models.UUIDField(
        null=True, editable=False, db_index=True)
    actor = models.ForeignKey(Agent, related_name="actor_statement", db_index=True, null=True,
                              on_delete=models.SET_NULL)
    verb = models.ForeignKey(Verb, null=True, on_delete=models.SET_NULL)
    result_success = models.NullBooleanField()
    result_completion = models.NullBooleanField()
    result_response = models.TextField(blank=True)
    result_duration = models.CharField(max_length=40, blank=True)
    result_score_scaled = models.FloatField(blank=True, null=True)
    result_score_raw = models.FloatField(blank=True, null=True)
    result_score_min = models.FloatField(blank=True, null=True)
    result_score_max = models.FloatField(blank=True, null=True)
    result_extensions = JSONField(default=dict, blank=True)
    stored = models.DateTimeField(default=timezone.now, db_index=True)
    timestamp = models.DateTimeField(db_index=True)
    authority = models.ForeignKey(Agent, blank=True, null=True, related_name="authority_statement", db_index=True,
                                  on_delete=models.SET_NULL)
    voided = models.NullBooleanField(default=False)
    context_registration = models.CharField(
        max_length=40, blank=True, db_index=True)
    context_instructor = models.ForeignKey(Agent, blank=True, null=True, on_delete=models.SET_NULL,
                                           db_index=True, related_name='statement_context_instructor')
    context_team = models.ForeignKey(Agent, blank=True, null=True, on_delete=models.SET_NULL,
                                     related_name="statement_context_team")
    context_revision = models.TextField(blank=True)
    context_platform = models.CharField(max_length=50, blank=True)
    context_language = models.CharField(max_length=50, blank=True)
    context_extensions = JSONField(default=dict, blank=True)
    context_ca_parent = models.ManyToManyField(
        Activity, related_name="stmt_context_ca_parent")
    context_ca_grouping = models.ManyToManyField(
        Activity, related_name="stmt_context_ca_grouping")
    context_ca_category = models.ManyToManyField(
        Activity, related_name="stmt_context_ca_category")
    context_ca_other = models.ManyToManyField(
        Activity, related_name="stmt_context_ca_other")
    # context_contextAgent = models.ManyToManyField(
    #     Agent, related_name="sub_context_contextAgent")
    context_contextAgent = models.ForeignKey(Agent, blank=True, null=True, on_delete=models.SET_NULL,
        db_index=True, related_name='sub_context_contextAgent')
    context_contextAgent_relevantType = models.CharField(
        max_length=MAX_URL_LENGTH, blank=True, db_index=True)
    # context_contextGroup = models.ManyToManyField(
    #     Agent, related_name="sub_context_contextGroup")
    context_contextGroup = models.ForeignKey(Agent, blank=True, null=True, on_delete=models.SET_NULL,
        db_index=True, related_name='sub_context_contextGroup')
    context_contextGroup_relevantType = models.CharField(
        max_length=MAX_URL_LENGTH, blank=True, db_index=True)
    # Context also has a stmt field which is a statementref.
    context_statement = models.CharField(max_length=40, blank=True)
    version = models.CharField(max_length=7)
    # Used in views
    user = models.ForeignKey(User, null=True, blank=True,
                             db_index=True, on_delete=models.SET_NULL)
    full_statement = JSONField()

    def to_dict(self, lang=None, ret_format='exact'):
        ret = OrderedDict()
        if ret_format == 'exact':
            return self.full_statement

        ids_only = True if ret_format == 'ids' else False
        ret['id'] = str(self.statement_id)
        ret['actor'] = self.actor.to_dict(ids_only)
        ret['verb'] = self.verb.return_verb_with_lang(lang, ids_only)

        if self.object_agent:
            ret['object'] = self.object_agent.to_dict(ids_only)
        elif self.object_activity:
            ret['object'] = self.object_activity.return_activity_with_lang_format(
                lang, ids_only)
        elif self.object_substatement:
            ret['object'] = self.object_substatement.to_dict(lang, ids_only)
        else:
            ret['object'] = {
                'id': str(self.object_statementref), 'objectType': 'StatementRef'}

        ret['result'] = OrderedDict()
        if self.result_success is not None:
            ret['result']['success'] = self.result_success
        if self.result_completion is not None:
            ret['result']['completion'] = self.result_completion
        if self.result_response:
            ret['result']['response'] = self.result_response
        if self.result_duration:
            ret['result']['duration'] = self.result_duration

        ret['result']['score'] = OrderedDict()
        if self.result_score_scaled is not None:
            ret['result']['score']['scaled'] = self.result_score_scaled
        if self.result_score_raw is not None:
            ret['result']['score']['raw'] = self.result_score_raw
        if self.result_score_min is not None:
            ret['result']['score']['min'] = self.result_score_min
        if self.result_score_max is not None:
            ret['result']['score']['max'] = self.result_score_max
        # If there is no score, delete from dict
        if not ret['result']['score']:
            del ret['result']['score']
        if self.result_extensions:
            ret['result']['extensions'] = self.result_extensions
        if not ret['result']:
            del ret['result']

        ret['context'] = OrderedDict()
        if self.context_registration:
            ret['context']['registration'] = self.context_registration
        if self.context_instructor:
            ret['context'][
                'instructor'] = self.context_instructor.to_dict(ids_only)
        if self.context_team:
            ret['context']['team'] = self.context_team.to_dict(ids_only)
        if self.context_revision:
            ret['context']['revision'] = self.context_revision
        if self.context_platform:
            ret['context']['platform'] = self.context_platform
        if self.context_language:
            ret['context']['language'] = self.context_language
        if self.context_statement:
            ret['context']['statement'] = {
                'id': self.context_statement, 'objectType': 'StatementRef'}

        ret['context']['contextActivities'] = OrderedDict()
        if self.context_ca_parent.all():
            ret['context']['contextActivities']['parent'] = [cap.return_activity_with_lang_format(
                lang, ids_only) for cap in self.context_ca_parent.all()]
        if self.context_ca_grouping.all():
            ret['context']['contextActivities']['grouping'] = [cag.return_activity_with_lang_format(
                lang, ids_only) for cag in self.context_ca_grouping.all()]
        if self.context_ca_category.all():
            ret['context']['contextActivities']['category'] = [cac.return_activity_with_lang_format(
                lang, ids_only) for cac in self.context_ca_category.all()]
        if self.context_ca_other.all():
            ret['context']['contextActivities']['other'] = [cao.return_activity_with_lang_format(
                lang, ids_only) for cao in self.context_ca_other.all()]
        if self.context_extensions:
            ret['context']['extensions'] = self.context_extensions
        if not ret['context']['contextActivities']:
            del ret['context']['contextActivities']

        ret['context']['contextAgents'] = OrderedDict()
        ret['context']['contextAgents']['objectType'] = "contextAgent"
        if self.context_contextAgent:
            ret['context']['contextAgents']['agent'] = self.context_contextAgent
        # if self.context_contextAgent.all():
        #     ret['context']['contextAgents']['agent'] = [conag.context_contextAgent.to_dict(ids_only) for conag in self.context_contextAgent.all()]
        if self.context_contextAgent_relevantType:
            ret['context']['contextAgents']['relevantTypes'] = self.context_contextAgent_relevantType
        if not ret['context']['contextAgents']:
            del ret['context']['contextAgents']

        ret['context']['contextGroups'] = OrderedDict()
        ret['context']['contextGroups']['objectType'] = "contextGroup"
        if self.context_contextGroup:
            ret['context']['contextGroups']['group'] = self.context_contextGroup
        # if self.context_contextGroup.all():
        #     ret['context']['contextGroups']['agent'] = [congrp.context_contextGroup.to_dict(ids_only) for congrp in self.context_contextGroup.all()]
        if self.context_contextGroup_relevantType:
            ret['context']['contextGroups']['relevantTypes'] = self.context_contextGroup_relevantType
        if not ret['context']['contextGroups']:
            del ret['context']['contextGroups']
        
        if not ret['context']:
            del ret['context']

        ret['timestamp'] = self.timestamp.isoformat()
        ret['stored'] = self.stored.isoformat()
        if self.authority is not None:
            ret['authority'] = self.authority.to_dict(ids_only)
        ret['version'] = self.version
        if self.stmt_attachments.all():
            ret['attachments'] = [a.return_attachment_with_lang(
                lang) for a in self.stmt_attachments.all()]
        return ret

    def get_a_name(self):
        return self.statement_id

    def get_object(self):
        if self.object_activity:
            stmt_object = self.object_activity
        elif self.object_agent:
            stmt_object = self.object_agent
        elif self.object_substatement:
            stmt_object = self.object_substatement
        else:
            stmt_object = {
                'id': str(self.object_statementref), 'objectType': 'StatementRef'}
        return stmt_object

    def __unicode__(self):
        return json.dumps(self.to_dict(), sort_keys=False)


class AttachmentFileSystemStorage(FileSystemStorage):

    def get_available_name(self, name, max_length=None):
        return name

    def _save(self, name, content, max_length=None):
        if self.exists(name):
            # if the file exists, do not call the superclasses _save method
            return name
        # if the file is new, DO call it
        return super(AttachmentFileSystemStorage, self)._save(name, content)


class StatementAttachment(models.Model):
    canonical_data = JSONField(default=dict)
    payload = models.FileField(max_length=150, upload_to=STATEMENT_ATTACHMENT_UPLOAD_TO,
                               storage=AttachmentFileSystemStorage(), null=True)
    statement = models.ForeignKey(
        Statement, related_name="stmt_attachments", null=True)

    def return_attachment_with_lang(self, lang=None):
        ret = OrderedDict(self.canonical_data)
        if 'display' in ret and ret['display'].items():
            ret['display'] = get_lang(self.canonical_data['display'], lang)
        if 'description' in ret and ret['description'].items():
            ret['description'] = get_lang(
                self.canonical_data['description'], lang)
        return ret

    def __unicode__(self):
        return json.dumps(self.canonical_data, sort_keys=False)


class ActivityState(models.Model):
    state_id = models.CharField(max_length=MAX_URL_LENGTH)
    updated = models.DateTimeField(
        auto_now_add=True, blank=True, db_index=True)
    activity_id = models.CharField(max_length=MAX_URL_LENGTH, db_index=True)
    registration_id = models.CharField(max_length=40, db_index=True)
    content_type = models.CharField(max_length=255, blank=True)
    etag = models.CharField(max_length=50, blank=True)
    agent = models.ForeignKey(Agent)
    json_state = JSONField(default=dict)
    state = models.FileField(upload_to=ACTIVITY_STATE_UPLOAD_TO, null=True)

    def delete(self, *args, **kwargs):
        if self.state:
            self.state.delete()
        super(ActivityState, self).delete(*args, **kwargs)

    def save(self, *args, **kwargs):
        if self.json_state and isinstance(self.json_state, basestring):
            try:
                json.loads(self.json_state)
            except Exception:
                try:
                    ast.literal_eval(self.json_state)
                except Exception:
                    raise BadRequest("The Activity State body is not valid JSON")
        elif self.json_state and not isinstance(self.json_state, basestring):
            raise BadRequest("The Activity State body is not valid JSON")
        super(ActivityState, self).save(*args, **kwargs)

class ActivityProfile(models.Model):
    profile_id = models.CharField(max_length=MAX_URL_LENGTH, db_index=True)
    updated = models.DateTimeField(
        auto_now_add=True, blank=True, db_index=True)
    activity_id = models.CharField(max_length=MAX_URL_LENGTH, db_index=True)
    content_type = models.CharField(max_length=255, blank=True)
    etag = models.CharField(max_length=50, blank=True)
    json_profile = JSONField(default=dict)
    profile = models.FileField(upload_to=ACTIVITY_PROFILE_UPLOAD_TO, null=True)

    def delete(self, *args, **kwargs):
        if self.profile:
            self.profile.delete()
        super(ActivityProfile, self).delete(*args, **kwargs)

    def save(self, *args, **kwargs):
        if self.json_profile and isinstance(self.json_profile, basestring):
            try:
                json.loads(self.json_profile)
            except Exception:
                try:
                    ast.literal_eval(self.json_profile)
                except Exception:
                    raise BadRequest("The Activity Profile body is not valid JSON")
        elif self.json_profile and not isinstance(self.json_profile, basestring):
            raise BadRequest("The Activity Profile body is not valid JSON")
        super(ActivityProfile, self).save(*args, **kwargs)

class AgentProfile(models.Model):
    profile_id = models.CharField(max_length=MAX_URL_LENGTH, db_index=True)
    updated = models.DateTimeField(
        auto_now_add=True, blank=True, db_index=True)
    content_type = models.CharField(max_length=255, blank=True)
    etag = models.CharField(max_length=50, blank=True)
    agent = models.ForeignKey(Agent, db_index=True)
    json_profile = JSONField(default=dict)
    profile = models.FileField(upload_to=AGENT_PROFILE_UPLOAD_TO, null=True)

    def delete(self, *args, **kwargs):
        if self.profile:
            self.profile.delete()
        super(AgentProfile, self).delete(*args, **kwargs)

    def save(self, *args, **kwargs):
        if self.json_profile and isinstance(self.json_profile, basestring):
            try:
                json.loads(self.json_profile)
            except Exception:
                try:
                    ast.literal_eval(self.json_profile)
                except Exception:
                    raise BadRequest("The Agent Profile body is not valid JSON")
        elif self.json_profile and not isinstance(self.json_profile, basestring):
            raise BadRequest("The Agent Profile body is not valid JSON")
        super(AgentProfile, self).save(*args, **kwargs)  