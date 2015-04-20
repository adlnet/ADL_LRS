import json
from datetime import datetime
from jsonfield import JSONField

from django_extensions.db.fields import UUIDField
from django.db import models
from django.db import transaction
from django.contrib.auth.models import User
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

agent_ifps_can_only_be_one = ['mbox', 'mbox_sha1sum', 'openID', 'account', 'openid']
class AgentManager(models.Manager):
    @transaction.commit_on_success
    def retrieve_or_create(self, **kwargs):
        ifp_sent = [a for a in agent_ifps_can_only_be_one if kwargs.get(a, None) != None]        
        is_group = kwargs.get('objectType', None) == "Group"
        has_member = False
        
        if is_group:
            member = kwargs.pop('member', None)
            if member:
                has_member = True
                if isinstance(member, basestring):
                    member = json.loads(member)

        if ifp_sent:
            # Canonical is defaulted to true
            canonical_version = kwargs.get('canonical_version', True)

            ifp = ifp_sent[0]
            ifp_dict = {'canonical_version': canonical_version}

            if not 'account' == ifp:
                ifp_dict[ifp] = kwargs[ifp]
            else:
                if not isinstance(kwargs['account'], dict):
                    account = json.loads(kwargs['account'])
                else:
                    account = kwargs['account']

                ifp_dict['account_homePage'] = account['homePage']
                kwargs['account_homePage'] = account['homePage']

                ifp_dict['account_name'] = account['name']
                kwargs['account_name'] = account['name']

                del kwargs['account']

            try:
                if not 'account' == ifp:
                    agent = Agent.objects.filter(**ifp_dict)[0]
                else:
                    agent = Agent.objects.filter(**ifp_dict)[0]
                created = False
            except IndexError:
                agent = Agent.objects.create(**kwargs)
                created = True

            # For identified groups
            if is_group and has_member:

                members = [self.retrieve_or_create(**a) for a in member]

                # If newly created identified group add all of the incoming members
                if created:
                    agent.member.add(*(a for a, c in members))

                # If retrieving existing canonical identified group, update members if necessary
                if not created and canonical_version:
                    for mem in members:
                        member_agent = mem[0]
                        if not member_agent in agent.member.all():
                            agent.member.add(member_agent)
                            agent.save()

            # If retreived agent or identified group is canonical version and name is different then update the name
            if 'name' in kwargs and kwargs['name'] != agent.name and canonical_version and not created:
                agent.name = kwargs['name']
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
    mbox = models.CharField(max_length=128, db_index=True, null=True)
    mbox_sha1sum = models.CharField(max_length=40, db_index=True, null=True)
    openID = models.CharField(max_length=MAX_URL_LENGTH, db_index=True, null=True)
    oauth_identifier = models.CharField(max_length=192, db_index=True, null=True)
    member = models.ManyToManyField('self', related_name="agents", null=True)
    canonical_version = models.BooleanField(default=True)
    account_homePage = models.CharField(max_length=MAX_URL_LENGTH, null=True)
    account_name = models.CharField(max_length=50, null=True)
    objects = AgentManager()

    class Meta:
        unique_together = (("mbox", "canonical_version"), ("mbox_sha1sum", "canonical_version"),
            ("openID", "canonical_version"),("oauth_identifier", "canonical_version"), ("account_homePage", "account_name", "canonical_version"))

    def to_dict(self, format='exact', just_objectType=False):
        just_id = format == 'ids'
        ret = {}
        # add object type if format isn't id,
        # or if it is a group,
        # or if it's an object
        if not just_id or self.objectType == 'Group' or just_objectType:
            ret['objectType'] = self.objectType
        if self.name and not just_id:
            ret['name'] = self.name
        if self.mbox:
            ret['mbox'] = self.mbox
        if self.mbox_sha1sum:
            ret['mbox_sha1sum'] = self.mbox_sha1sum
        if self.openID:
            ret['openID'] = self.openID
        
        ret['account'] = {}
        if self.account_name:
            ret['account']['name'] = self.account_name

        if self.account_homePage:
            ret['account']['homePage'] = self.account_homePage

        # If not account, delete it
        if not ret['account']:
            del ret['account']

        if self.objectType == 'Group':
            # show members for groups if format isn't 'ids'
            # show members' ids for anon groups if format is 'ids'
            if not just_id or not (set(['mbox','mbox_sha1sum','openID','account']) & set(ret.keys())):
                ret['member'] = [a.to_dict(format) for a in self.member.all()]
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
        if self.openID:
            ret['openID'] = [self.openID]

        ret['account'] = {}
        if self.account_name:
            ret['account']['name'] = self.account_name

        if self.account_homePage:
            ret['account']['homePage'] = self.account_homePage

        if not ret['account']:
            del ret['account']

        return ret

    def get_a_name(self):
        if self.name:
            return self.name
        if self.mbox:
            return self.mbox
        if self.mbox_sha1sum:
            return self.mbox_sha1sum
        if self.openID:
            return self.openID
        try:
            return self.account_name
        except:
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

class Activity(models.Model):
    activity_id = models.CharField(max_length=MAX_URL_LENGTH, db_index=True)
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
    canonical_version = models.BooleanField(default=True)

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

class StatementRef(models.Model):
    object_type = models.CharField(max_length=12, default="StatementRef")
    ref_id = models.CharField(max_length=40)

    def to_dict(self):
        ret = {}
        ret['objectType'] = "StatementRef"
        ret['id'] = self.ref_id
        return ret

    def get_a_name(self):
        s = Statement.objects.get(statement_id=self.ref_id)
        return s.get_object().get_a_name()
        
class SubStatementContextActivity(models.Model):
    key = models.CharField(max_length=8)
    context_activity = models.ManyToManyField(Activity)
    substatement = models.ForeignKey('SubStatement')

    def to_dict(self, lang=None, format='exact'):
        ret = {}
        ret[self.key] = {}
        ret[self.key] = [a.to_dict(lang, format) for a in self.context_activity.all()]
        return ret

class StatementContextActivity(models.Model):
    key = models.CharField(max_length=8)
    context_activity = models.ManyToManyField(Activity)
    statement = models.ForeignKey('Statement')

    def to_dict(self, lang=None, format='exact'):
        ret = {}
        ret[self.key] = {}
        ret[self.key] = [a.to_dict(lang, format) for a in self.context_activity.all()]
        return ret

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

class SubStatement(models.Model):
    object_agent = models.ForeignKey(Agent, related_name="object_of_substatement", on_delete=models.SET_NULL, null=True, db_index=True)
    object_activity = models.ForeignKey(Activity, related_name="object_of_substatement", on_delete=models.SET_NULL, null=True, db_index=True)
    object_statementref = models.ForeignKey(StatementRef, related_name="object_of_substatement", on_delete=models.SET_NULL, null=True, db_index=True)    
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
    # context also has a stmt field which is a statementref
    context_statement = models.CharField(max_length=40, blank=True)
    
    def to_dict(self, lang=None, format='exact'):
        ret = {}
        ret['actor'] = self.actor.to_dict(format)
        ret['verb'] = self.verb.to_dict()

        if self.object_agent:
            ret['object'] = self.object_agent.to_dict(format, just_objectType=True)
        elif self.object_activity:
            if not self.object_activity.canonical_version:
                ret['object'] = Activity.objects.get(activity_id=self.object_activity.activity_id, canonical_version=True).to_dict(lang, format)
            else:
                ret['object'] = self.object_activity.to_dict(lang, format)
        else:
            ret['object'] = self.object_statementref.to_dict()

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

        if self.substatementcontextactivity_set.all():
            ret['context']['contextActivities'] = {}
            for con_act in self.substatementcontextactivity_set.all():
                ret['context']['contextActivities'].update(con_act.to_dict(lang, format))

        if self.context_extensions:
            ret['context']['extensions'] = self.context_extensions

        if not ret['context']:
            del ret['context']

        ret['timestamp'] = str(self.timestamp)
        ret['objectType'] = "SubStatement"
        return ret

    def get_a_name(self):
        return self.get_object().get_a_name()

    def get_object(self):
        if self.object_activity:
            stmt_object = self.object_activity
        elif self.object_agent:
            stmt_object = self.object_agent
        else:
            stmt_object = self.object_statementref
        return stmt_object

    def delete(self, *args, **kwargs):
        if self.object_statementref:
            self.object_statementref.delete()
        
        super(SubStatement, self).delete(*args, **kwargs)

class StatementAttachment(models.Model):
    usageType = models.CharField(max_length=MAX_URL_LENGTH)
    contentType = models.CharField(max_length=128)
    length = models.PositiveIntegerField()
    sha2 = models.CharField(max_length=128, blank=True)
    fileUrl = models.CharField(max_length=MAX_URL_LENGTH, blank=True)
    payload = models.FileField(upload_to=STATEMENT_ATTACHMENT_UPLOAD_TO, null=True)
    display = JSONField(default={}, blank=True)
    description = JSONField(default={}, blank=True)

    def to_dict(self, lang=None):
        ret = {}
        ret['usageType'] = self.usageType

        if self.display:
            if lang:
                ret['display'] = util.get_lang(self.display, lang)
            else:
                first = self.display.iteritems().next()
                ret['display'] = {first[0]:first[1]}

        if self.description:
            if lang:
                ret['description'] = util.get_lang(self.description, lang)
            else:
                first = self.description.iteritems().next()
                ret['description'] = {first[0]:first[1]}

        ret['contentType'] = self.contentType
        ret['length'] = self.length

        if self.sha2:
            ret['sha2'] = self.sha2

        if self.fileUrl:
            ret['fileUrl'] = self.fileUrl
        return ret

class Statement(models.Model):
    # If no statement_id is given, will create one automatically
    statement_id = UUIDField(version=1, db_index=True, unique=True)
    object_agent = models.ForeignKey(Agent, related_name="object_of_statement", null=True, on_delete=models.SET_NULL, db_index=True)
    object_activity = models.ForeignKey(Activity, related_name="object_of_statement", null=True, on_delete=models.SET_NULL, db_index=True)
    object_substatement = models.ForeignKey(SubStatement, related_name="object_of_statement", null=True, on_delete=models.SET_NULL, db_index=True)
    object_statementref = models.ForeignKey(StatementRef, related_name="object_of_statement", null=True, on_delete=models.SET_NULL, db_index=True)    
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
    # context also has a stmt field which is a statementref
    context_statement = models.CharField(max_length=40, blank=True)
    version = models.CharField(max_length=7)
    attachments = models.ManyToManyField(StatementAttachment)
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
            ret['object'] = self.object_agent.to_dict(format, just_objectType=True)            
        elif self.object_activity:
            if not self.object_activity.canonical_version:
                ret['object'] = Activity.objects.get(activity_id=self.object_activity.activity_id, canonical_version=True).to_dict(lang, format)
            else:
                ret['object'] = self.object_activity.to_dict(lang, format)
        elif self.object_substatement:
            ret['object'] = self.object_substatement.to_dict(lang, format)
        else:
            ret['object'] = self.object_statementref.to_dict()

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

        if self.statementcontextactivity_set.all():
            ret['context']['contextActivities'] = {}
            for con_act in self.statementcontextactivity_set.all():
                ret['context']['contextActivities'].update(con_act.to_dict(lang, format))

        if self.context_extensions:
            ret['context']['extensions'] = self.context_extensions

        if not ret['context']:
            del ret['context']

        ret['timestamp'] = self.timestamp.isoformat()
        ret['stored'] = self.stored.isoformat()
        
        if not self.authority is None:
            ret['authority'] = self.authority.to_dict(format)
        
        ret['version'] = self.version

        if self.attachments.all():
            ret['attachments'] = [a.to_dict(lang) for a in self.attachments.all()]
        return ret

    def unvoid_statement(self):
        Statement.objects.filter(statement_id=self.object_statementref.ref_id).update(voided=False)        

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
            stmt_object = self.object_statementref
        return stmt_object

    def delete(self, *args, **kwargs):        
        # Unvoid stmt if verb is voided
        if self.verb.verb_id == 'http://adlnet.gov/expapi/verbs/voided':
            self.unvoid_statement()
        
        # If sub or ref, FK will be set to null, then call delete
        if self.verb.verb_id != 'http://adlnet.gov/expapi/verbs/voided':
            if self.object_substatement:
                self.object_substatement.delete()
            elif self.object_statementref:
                self.object_statementref.delete()

        super(Statement, self).delete(*args, **kwargs)
