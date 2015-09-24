import json
from datetime import datetime
from jsonfield import JSONField

from django_extensions.db.fields import UUIDField
from django.db import models
from django.contrib.auth.models import User
from django.core.files.storage import FileSystemStorage
from django.utils.timezone import utc

from oauth_provider.consts import MAX_URL_LENGTH

from .util import util

AGENT_PROFILE_UPLOAD_TO = "agent_profile"
ACTIVITY_STATE_UPLOAD_TO = "activity_state"
ACTIVITY_PROFILE_UPLOAD_TO = "activity_profile"
STATEMENT_ATTACHMENT_UPLOAD_TO = "attachment_payloads"

class Verb(models.Model):
    verb_id = models.CharField(max_length=MAX_URL_LENGTH, db_index=True, unique=True)
    display = JSONField(default={}, blank=True)

    def to_dict(self, lang=None):
        ret = {}
        ret['id'] = self.verb_id
        if self.display:
            ret['display'] = util.get_lang(self.display, lang)
        return ret

    # Just return one value for human-readable
    def get_display(self, lang=None):
        if not self.display:
            return self.verb_id
        if lang:
            return self.display[lang]
        try:    
            return self.display['en-US']
        except:
            try:
                return self.display['en']
            except:
                pass
        return self.display.values()[0]

    def __unicode__(self):
        return json.dumps(self.to_dict())

class AgentManager(models.Manager):
    def retrieve_or_create(self, **kwargs):
        agent_ifps_can_only_be_one = ['mbox', 'mbox_sha1sum', 'account', 'openid']
        ifp_sent = [a for a in agent_ifps_can_only_be_one if kwargs.get(a, None) != None]        
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
                # If DNE create the agent based off of kwargs (kwargs now includes account_homePage and account_name fields)
                agent = Agent.objects.create(**kwargs)
                created = True

            # For identified groups with members
            if is_group and has_member:
                # If newly created identified group add all of the incoming members
                if created:
                    members = [self.retrieve_or_create(**a) for a in member]
                    agent.member.add(*(a for a, c in members))
                    agent.save()
        # Only way it doesn't have IFP is if anonymous group
        else:
            agent, created = self.retrieve_or_create_anonymous_group(member, kwargs)
        return agent, created

    def retrieve_or_create_anonymous_group(self, member, kwargs):
        # Narrow oauth down to 2 members and one member having an account
        if len(member) == 2 and ('account' in member[0] or 'account' in member[1]):
            # If oauth account is in first member
            if 'account' in member[0] and 'OAuth' in member[0]['account']['homePage']:
                created_oauth_identifier = "anongroup:%s-%s" % (member[0]['account']['name'], member[1]['mbox'])
                try:
                    agent = Agent.objects.get(oauth_identifier=created_oauth_identifier)
                    created = False
                except Agent.DoesNotExist:
                    agent = Agent.objects.create(**kwargs)
                    created = True
            # If oauth account is in second member
            elif 'account' in member[1] and 'OAuth' in member[1]['account']['homePage']:
                created_oauth_identifier = "anongroup:%s-%s" % (member[1]['account']['name'], member[0]['mbox'])
                try:
                    agent = Agent.objects.get(oauth_identifier=created_oauth_identifier)
                    created = False
                except Agent.DoesNotExist:
                    agent = Agent.objects.create(**kwargs)
                    created = True
            # Non-oauth anonymous group that has 2 members, one having an account
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
    mbox = models.CharField(max_length=128, db_index=True, null=True, unique=True)
    mbox_sha1sum = models.CharField(max_length=40, db_index=True, null=True, unique=True)
    openid = models.CharField(max_length=MAX_URL_LENGTH, db_index=True, null=True, unique=True)
    oauth_identifier = models.CharField(max_length=192, db_index=True, null=True, unique=True)
    member = models.ManyToManyField('self', related_name="agents", null=True)
    account_homePage = models.CharField(max_length=MAX_URL_LENGTH, null=True)
    account_name = models.CharField(max_length=50, null=True)
    objects = AgentManager()

    class Meta:
        unique_together = ("account_homePage", "account_name")

    def to_dict(self, format='exact'):
        ret = {}
        if self.mbox:
            ret['mbox'] = self.mbox
        if self.mbox_sha1sum:
            ret['mbox_sha1sum'] = self.mbox_sha1sum
        if self.openid:
            ret['openid'] = self.openid
        if self.account_name:
            ret['account'] = {}
            ret['account']['name'] = self.account_name
            ret['account']['homePage'] = self.account_homePage
        if self.objectType == 'Group':
            ret['objectType'] = self.objectType
            # show members for groups if format isn't 'ids'
            # show members' ids for anon groups if format is 'ids'
            if not format == 'ids' or not (set(['mbox','mbox_sha1sum','openid','account']) & set(ret.keys())):
                ret['member'] = [a.to_dict(format) for a in self.member.all()]
        if self.objectType and not format == 'ids':
            ret['objectType'] = self.objectType
        if self.name and not format == 'ids':
            ret['name'] = self.name
        return ret

    # Used only for /agent GET endpoint (check spec)
    def to_dict_person(self):
        ret = {}
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
            acc = {}
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
        return json.dumps(self.to_dict())

class Activity(models.Model):
    activity_id = models.CharField(max_length=MAX_URL_LENGTH, db_index=True, unique=True)
    objectType = models.CharField(max_length=8,blank=True, default="Activity")
    activity_definition_name = JSONField(default={}, blank=True)
    activity_definition_description = JSONField(default={}, blank=True)
    activity_definition_type = models.CharField(max_length=MAX_URL_LENGTH, blank=True)
    activity_definition_moreInfo = models.CharField(max_length=MAX_URL_LENGTH, blank=True)
    activity_definition_interactionType = models.CharField(max_length=25, blank=True)
    activity_definition_extensions = JSONField(default={}, blank=True)
    activity_definition_crpanswers = JSONField(default={}, blank=True)
    activity_definition_choices = JSONField(default={}, blank=True)
    activity_definition_scales = JSONField(default={}, blank=True)
    activity_definition_sources = JSONField(default={}, blank=True)
    activity_definition_targets = JSONField(default={}, blank=True)
    activity_definition_steps = JSONField(default={}, blank=True)
    authority = models.ForeignKey(Agent, null=True)

    def add_interaction_type(self, i_type, ret, lang):
        if i_type == 'scale':
            interactions = self.activity_definition_scales
        elif i_type == 'choices':
            interactions = self.activity_definition_choices
        elif i_type == 'steps':
            interactions = self.activity_definition_steps
        elif i_type == 'source':
            interactions = self.activity_definition_sources
        elif i_type == 'target':
            interactions = self.activity_definition_targets
        for i in interactions:
            i['description'] = util.get_lang(i['description'], lang)
            ret['definition'][i_type].append(i)        

    def to_dict(self, lang=None, format='exact'):
        ret = {}
        ret['id'] = self.activity_id
        if format != 'ids':
            ret['objectType'] = self.objectType
            ret['definition'] = {}
            if self.activity_definition_name:
                ret['definition']['name'] = util.get_lang(self.activity_definition_name, lang)
            if self.activity_definition_description:
                ret['definition']['description'] = util.get_lang(self.activity_definition_description, lang)
            if self.activity_definition_type:
                ret['definition']['type'] = self.activity_definition_type
            if self.activity_definition_moreInfo != '':
                ret['definition']['moreInfo'] = self.activity_definition_moreInfo
            if self.activity_definition_interactionType != '':
                ret['definition']['interactionType'] = self.activity_definition_interactionType
            # Get answers
            if self.activity_definition_crpanswers:
                ret['definition']['correctResponsesPattern'] = self.activity_definition_crpanswers
            if self.activity_definition_scales:
                ret['definition']['scale'] = []
                self.add_interaction_type('scale', ret, lang)
            if self.activity_definition_choices:
                ret['definition']['choices'] = []
                self.add_interaction_type('choices', ret, lang)
            if self.activity_definition_steps:
                ret['definition']['steps'] = []
                self.add_interaction_type('steps', ret, lang)
            if self.activity_definition_sources:
                ret['definition']['source'] = []
                self.add_interaction_type('source', ret, lang)
            if self.activity_definition_targets:
                ret['definition']['target'] = []
                self.add_interaction_type('target', ret, lang)
            if self.activity_definition_extensions:
                ret['definition']['extensions'] = self.activity_definition_extensions
            if not ret['definition']:
                del ret['definition']
        return ret

    def get_a_name(self):
        return self.activity_definition_name.get('en-US', self.activity_id)

    def __unicode__(self):
        return json.dumps(self.to_dict())

class SubStatement(models.Model):
    object_agent = models.ForeignKey(Agent, related_name="object_of_substatement", on_delete=models.SET_NULL, null=True, db_index=True)
    object_activity = models.ForeignKey(Activity, related_name="object_of_substatement", on_delete=models.SET_NULL, null=True, db_index=True)
    object_statementref = models.CharField(max_length=40, blank=True, null=True, db_index=True)
    actor = models.ForeignKey(Agent,related_name="actor_of_substatement", null=True, on_delete=models.SET_NULL)
    verb = models.ForeignKey(Verb, null=True, on_delete=models.SET_NULL)
    result_success = models.NullBooleanField()
    result_completion = models.NullBooleanField()
    result_response = models.TextField(blank=True)
    # Made charfield since it would be stored in ISO8601 duration format
    result_duration = models.CharField(max_length=40, blank=True)
    result_score_scaled = models.FloatField(blank=True, null=True)
    result_score_raw = models.FloatField(blank=True, null=True)
    result_score_min = models.FloatField(blank=True, null=True)
    result_score_max = models.FloatField(blank=True, null=True)
    result_extensions = JSONField(default={}, blank=True)
    timestamp = models.DateTimeField(blank=True,null=True,
        default=lambda: datetime.utcnow().replace(tzinfo=utc).isoformat())
    context_registration = models.CharField(max_length=40, blank=True, db_index=True)
    context_instructor = models.ForeignKey(Agent,blank=True, null=True, on_delete=models.SET_NULL,
        db_index=True, related_name='substatement_context_instructor')
    context_team = models.ForeignKey(Agent,blank=True, null=True, on_delete=models.SET_NULL,
        related_name="substatement_context_team")
    context_revision = models.TextField(blank=True)
    context_platform = models.CharField(max_length=50,blank=True)
    context_language = models.CharField(max_length=50,blank=True)
    context_extensions = JSONField(default={}, blank=True)
    context_ca_parent = models.ManyToManyField(Activity, related_name="sub_context_ca_parent")
    context_ca_grouping = models.ManyToManyField(Activity, related_name="sub_context_ca_grouping")
    context_ca_category = models.ManyToManyField(Activity, related_name="sub_context_ca_category")
    context_ca_other = models.ManyToManyField(Activity, related_name="sub_context_ca_other")
    # context also has a stmt field which is a statementref
    context_statement = models.CharField(max_length=40, blank=True)
    
    def to_dict(self, lang=None, format='exact'):
        ret = {}
        ret['actor'] = self.actor.to_dict(format)
        ret['verb'] = self.verb.to_dict()
        
        if self.object_agent:
            ret['object'] = self.object_agent.to_dict(format)
        elif self.object_activity:
            ret['object'] = self.object_activity.to_dict(lang, format)
        else:
            ret['object'] = {'id': self.object_statementref, 'objectType': 'StatementRef'}
        
        ret['result'] = {}
        if self.result_success != None:
            ret['result']['success'] = self.result_success
        if self.result_completion != None:
            ret['result']['completion'] = self.result_completion
        if self.result_response:
            ret['result']['response'] = self.result_response
        if self.result_duration:
            ret['result']['duration'] = self.result_duration
        
        ret['result']['score'] = {}
        if not self.result_score_scaled is None:
            ret['result']['score']['scaled'] = self.result_score_scaled
        if not self.result_score_raw is None:
            ret['result']['score']['raw'] = self.result_score_raw
        if not self.result_score_min is None:
            ret['result']['score']['min'] = self.result_score_min
        if not self.result_score_max is None:
            ret['result']['score']['max'] = self.result_score_max
        # If there is no score, delete from dict
        if not ret['result']['score']:
            del ret['result']['score']
        if self.result_extensions:
            ret['result']['extensions'] = self.result_extensions
        # If no result, delete from dict
        if not ret['result']:
            del ret['result']

        ret['context'] = {}
        if self.context_registration:
            ret['context']['registration'] = self.context_registration
        if self.context_instructor:
            ret['context']['instructor'] = self.context_instructor.to_dict(format)
        if self.context_team:
            ret['context']['team'] = self.context_team.to_dict(format)
        if self.context_revision:
            ret['context']['revision'] = self.context_revision
        if self.context_platform:
            ret['context']['platform'] = self.context_platform
        if self.context_language:
            ret['context']['language'] = self.context_language
        if self.context_statement:
            ret['context']['statement'] = {'id': self.context_statement, 'objectType': 'StatementRef'}

        ret['context']['contextActivities'] = {}
        if self.context_ca_parent.all():
            ret['context']['contextActivities']['parent'] = [cap.to_dict(lang, format) for cap in self.context_ca_parent.all()]
        if self.context_ca_grouping.all():
            ret['context']['contextActivities']['grouping'] = [cag.to_dict(lang, format) for cag in self.context_ca_grouping.all()]
        if self.context_ca_category.all():
            ret['context']['contextActivities']['category'] = [cac.to_dict(lang, format) for cac in self.context_ca_category.all()]
        if self.context_ca_other.all():
            ret['context']['contextActivities']['other'] = [cao.to_dict(lang, format) for cao in self.context_ca_other.all()]
        if self.context_extensions:
            ret['context']['extensions'] = self.context_extensions
        if not ret['context']['contextActivities']:
            del ret['context']['contextActivities']
        if not ret['context']:
            del ret['context']

        ret['timestamp'] = str(self.timestamp)
        ret['objectType'] = "SubStatement"
        return ret

    def get_a_name(self):
        if self.object_activity:
            return self.object_activity.get_a_name()
        elif self.object_agent:
            return self.object_agent.get_a_name()
        else:
            return self.object_statementref

    def get_object(self):
        if self.object_activity:
            stmt_object = self.object_activity
        elif self.object_agent:
            stmt_object = self.object_agent
        else:
            stmt_object = {'id': self.object_statementref, 'objectType': 'StatementRef'}
        return stmt_object

    def __unicode__(self):
        return json.dumps(self.to_dict())

class Statement(models.Model):
    # If no statement_id is given, will create one automatically
    statement_id = UUIDField(version=1, db_index=True, unique=True)
    object_agent = models.ForeignKey(Agent, related_name="object_of_statement", null=True, on_delete=models.SET_NULL, db_index=True)
    object_activity = models.ForeignKey(Activity, related_name="object_of_statement", null=True, on_delete=models.SET_NULL, db_index=True)
    object_substatement = models.ForeignKey(SubStatement, related_name="object_of_statement", null=True, on_delete=models.SET_NULL, db_index=True)
    object_statementref = models.CharField(max_length=40, blank=True, null=True, db_index=True)    
    actor = models.ForeignKey(Agent,related_name="actor_statement", db_index=True, null=True,
        on_delete=models.SET_NULL)
    verb = models.ForeignKey(Verb, null=True, on_delete=models.SET_NULL)
    result_success = models.NullBooleanField()
    result_completion = models.NullBooleanField()
    result_response = models.TextField(blank=True)
    # Made charfield since it would be stored in ISO8601 duration format
    result_duration = models.CharField(max_length=40, blank=True)
    result_score_scaled = models.FloatField(blank=True, null=True)
    result_score_raw = models.FloatField(blank=True, null=True)
    result_score_min = models.FloatField(blank=True, null=True)
    result_score_max = models.FloatField(blank=True, null=True)
    result_extensions = JSONField(default={}, blank=True)
    # If no stored or timestamp given - will create automatically (only happens if using StatementManager directly)
    stored = models.DateTimeField(default=datetime.utcnow().replace(tzinfo=utc).isoformat(), db_index=True)
    timestamp = models.DateTimeField(default=datetime.utcnow().replace(tzinfo=utc).isoformat(), db_index=True)
    authority = models.ForeignKey(Agent, blank=True,null=True,related_name="authority_statement", db_index=True,
        on_delete=models.SET_NULL)
    voided = models.NullBooleanField(default=False)
    context_registration = models.CharField(max_length=40, blank=True, db_index=True)
    context_instructor = models.ForeignKey(Agent,blank=True, null=True, on_delete=models.SET_NULL,
        db_index=True, related_name='statement_context_instructor')
    context_team = models.ForeignKey(Agent,blank=True, null=True, on_delete=models.SET_NULL,
        related_name="statement_context_team")
    context_revision = models.TextField(blank=True)
    context_platform = models.CharField(max_length=50,blank=True)
    context_language = models.CharField(max_length=50,blank=True)
    context_extensions = JSONField(default={}, blank=True)
    context_ca_parent = models.ManyToManyField(Activity, related_name="stmt_context_ca_parent")
    context_ca_grouping = models.ManyToManyField(Activity, related_name="stmt_context_ca_grouping")
    context_ca_category = models.ManyToManyField(Activity, related_name="stmt_context_ca_category")
    context_ca_other = models.ManyToManyField(Activity, related_name="stmt_context_ca_other")
    # context also has a stmt field which is a statementref
    context_statement = models.CharField(max_length=40, blank=True)
    version = models.CharField(max_length=7)
    # Used in views
    user = models.ForeignKey(User, null=True, blank=True, db_index=True, on_delete=models.SET_NULL)
    full_statement = JSONField()
    
    def to_dict(self, lang=None, format='exact'):
        if format == 'exact':
            return self.full_statement
        ret = {}
        ret['id'] = self.statement_id
        ret['actor'] = self.actor.to_dict(format)
        ret['verb'] = self.verb.to_dict()

        if self.object_agent:
            ret['object'] = self.object_agent.to_dict(format)            
        elif self.object_activity:
            ret['object'] = self.object_activity.to_dict(lang, format)
        elif self.object_substatement:
            ret['object'] = self.object_substatement.to_dict(lang, format)
        else:
            ret['object'] = {'id': self.object_statementref, 'objectType': 'StatementRef'}

        ret['result'] = {}
        if self.result_success != None:
            ret['result']['success'] = self.result_success
        if self.result_completion != None:
            ret['result']['completion'] = self.result_completion
        if self.result_response:
            ret['result']['response'] = self.result_response
        if self.result_duration:
            ret['result']['duration'] = self.result_duration

        ret['result']['score'] = {}
        if not self.result_score_scaled is None:
            ret['result']['score']['scaled'] = self.result_score_scaled
        if not self.result_score_raw is None:
            ret['result']['score']['raw'] = self.result_score_raw
        if not self.result_score_min is None:
            ret['result']['score']['min'] = self.result_score_min
        if not self.result_score_max is None:
            ret['result']['score']['max'] = self.result_score_max
        # If there is no score, delete from dict
        if not ret['result']['score']:
            del ret['result']['score']
        if self.result_extensions:
            ret['result']['extensions'] = self.result_extensions
        if not ret['result']:
            del ret['result']

        ret['context'] = {}
        if self.context_registration:
            ret['context']['registration'] = self.context_registration
        if self.context_instructor:
            ret['context']['instructor'] = self.context_instructor.to_dict(format)
        if self.context_team:
            ret['context']['team'] = self.context_team.to_dict(format)
        if self.context_revision:
            ret['context']['revision'] = self.context_revision
        if self.context_platform:
            ret['context']['platform'] = self.context_platform
        if self.context_language:
            ret['context']['language'] = self.context_language
        if self.context_statement:
            ret['context']['statement'] = {'id': self.context_statement, 'objectType': 'StatementRef'}
        
        ret['context']['contextActivities'] = {}
        if self.context_ca_parent.all():
            ret['context']['contextActivities']['parent'] = [cap.to_dict(lang, format) for cap in self.context_ca_parent.all()]
        if self.context_ca_grouping.all():
            ret['context']['contextActivities']['grouping'] = [cag.to_dict(lang, format) for cag in self.context_ca_grouping.all()]
        if self.context_ca_category.all():
            ret['context']['contextActivities']['category'] = [cac.to_dict(lang, format) for cac in self.context_ca_category.all()]
        if self.context_ca_other.all():
            ret['context']['contextActivities']['other'] = [cao.to_dict(lang, format) for cao in self.context_ca_other.all()]
        if self.context_extensions:
            ret['context']['extensions'] = self.context_extensions
        if not ret['context']['contextActivities']:
            del ret['context']['contextActivities']
        if not ret['context']:
            del ret['context']

        ret['timestamp'] = self.timestamp.isoformat()
        ret['stored'] = self.stored.isoformat()
        ret['version'] = self.version
        if not self.authority is None:
            ret['authority'] = self.authority.to_dict(format)        
        if self.stmt_attachments.all():
            ret['attachments'] = [a.to_dict(lang) for a in self.stmt_attachments.all()]

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
            stmt_object = {'id': self.object_statementref, 'objectType': 'StatementRef'}
        return stmt_object

    def __unicode__(self):
        return json.dumps(self.to_dict())

class AttachmentFileSystemStorage(FileSystemStorage):
    def get_available_name(self, name):
        return name

    def _save(self, name, content):
        if self.exists(name):
            # if the file exists, do not call the superclasses _save method
            return name
        # if the file is new, DO call it
        return super(AttachmentFileSystemStorage, self)._save(name, content)    
class StatementAttachment(models.Model):
    usageType = models.CharField(max_length=MAX_URL_LENGTH)
    contentType = models.CharField(max_length=128)
    length = models.PositiveIntegerField()
    sha2 = models.CharField(max_length=128, blank=True)
    fileUrl = models.CharField(max_length=MAX_URL_LENGTH, blank=True)
    payload = models.FileField(upload_to=STATEMENT_ATTACHMENT_UPLOAD_TO, storage=AttachmentFileSystemStorage(), null=True)
    display = JSONField(default={}, blank=True)
    description = JSONField(default={}, blank=True)
    statement = models.ForeignKey(Statement, related_name="stmt_attachments", null=True)

    def to_dict(self, lang=None):
        ret = {}
        ret['usageType'] = self.usageType
        if self.display:
            ret['display'] = util.get_lang(self.display, lang)
        if self.description:
            ret['description'] = util.get_lang(self.description, lang)
        ret['contentType'] = self.contentType
        ret['length'] = self.length
        if self.sha2:
            ret['sha2'] = self.sha2
        if self.fileUrl:
            ret['fileUrl'] = self.fileUrl
        return ret

    def __unicode__(self):
        return json.dumps(self.to_dict())

class ActivityState(models.Model):
    state_id = models.CharField(max_length=MAX_URL_LENGTH)
    updated = models.DateTimeField(auto_now_add=True, blank=True, db_index=True)
    state = models.FileField(upload_to=ACTIVITY_STATE_UPLOAD_TO, null=True)
    json_state = models.TextField(blank=True)
    agent = models.ForeignKey(Agent, db_index=True)
    activity_id = models.CharField(max_length=MAX_URL_LENGTH, db_index=True)
    registration_id = models.CharField(max_length=40)
    content_type = models.CharField(max_length=255,blank=True)
    etag = models.CharField(max_length=50,blank=True)

    def delete(self, *args, **kwargs):
        if self.state:
            self.state.delete()
        super(ActivityState, self).delete(*args, **kwargs)

class ActivityProfile(models.Model):
    profileId = models.CharField(max_length=MAX_URL_LENGTH, db_index=True)
    updated = models.DateTimeField(auto_now_add=True, blank=True, db_index=True)
    activityId = models.CharField(max_length=MAX_URL_LENGTH, db_index=True)
    profile = models.FileField(upload_to=ACTIVITY_PROFILE_UPLOAD_TO, null=True)
    json_profile = models.TextField(blank=True)
    content_type = models.CharField(max_length=255,blank=True)
    etag = models.CharField(max_length=50,blank=True)

    def delete(self, *args, **kwargs):
        if self.profile:
            self.profile.delete()
        super(ActivityProfile, self).delete(*args, **kwargs)

class AgentProfile(models.Model):
    profileId = models.CharField(max_length=MAX_URL_LENGTH, db_index=True)
    updated = models.DateTimeField(auto_now_add=True, blank=True)
    agent = models.ForeignKey(Agent)
    profile = models.FileField(upload_to=AGENT_PROFILE_UPLOAD_TO, null=True)
    json_profile = models.TextField(blank=True)
    content_type = models.CharField(max_length=255,blank=True)
    etag = models.CharField(max_length=50,blank=True)

    def delete(self, *args, **kwargs):
        if self.profile:
            self.profile.delete()
        super(AgentProfile, self).delete(*args, **kwargs)