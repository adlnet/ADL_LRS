import pytz
import ast
import json
import urllib
import urlparse
import datetime as dt
from datetime import datetime
from time import time
from django_extensions.db.fields import UUIDField
from django.db import models
from django.db import transaction
from django.conf import settings
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.utils.timezone import utc
from .exceptions import IDNotFoundError, ParamError
from oauth_provider.managers import TokenManager, ConsumerManager
from oauth_provider.consts import KEY_SIZE, SECRET_SIZE, CONSUMER_KEY_SIZE, CONSUMER_STATES,\
                   PENDING, VERIFIER_SIZE, MAX_URL_LENGTH

ADL_LRS_STRING_KEY = 'ADL_LRS_STRING_KEY'

gen_pwd = User.objects.make_random_password
generate_random = User.objects.make_random_password

class Nonce(models.Model):
    token_key = models.CharField(max_length=KEY_SIZE)
    consumer_key = models.CharField(max_length=CONSUMER_KEY_SIZE)
    key = models.CharField(max_length=50)
    
    def __unicode__(self):
        return u"Nonce %s for %s" % (self.key, self.consumer_key)

class Consumer(models.Model):
    name = models.CharField(max_length=50)
    description = models.TextField()

    default_scopes = models.CharField(max_length=100, default="statements/write,statements/read/mine")
    
    key = UUIDField(version=1)
    secret = models.CharField(max_length=SECRET_SIZE, default=gen_pwd)

    status = models.SmallIntegerField(choices=CONSUMER_STATES, default=PENDING)
    user = models.ForeignKey(User, null=True, blank=True, related_name="consumer_user", db_index=True)

    objects = ConsumerManager()
        
    def __unicode__(self):
        return u"Consumer %s with key %s" % (self.name, self.key)

    def generate_random_codes(self):
        """
        Used to generate random key/secret pairings.
        Use this after you've added the other data in place of save().
        """
        key = generate_random(length=KEY_SIZE)
        secret = generate_random(length=SECRET_SIZE)
        while Consumer.objects.filter(models.Q(key__exact=key) | models.Q(secret__exact=secret)).count():
            key = generate_random(length=KEY_SIZE)
            secret = generate_random(length=SECRET_SIZE)
        self.key = key
        self.secret = secret
        self.save()


class Token(models.Model):
    REQUEST = 1
    ACCESS = 2
    TOKEN_TYPES = ((REQUEST, u'Request'), (ACCESS, u'Access'))
    
    key = models.CharField(max_length=KEY_SIZE, null=True, blank=True)
    secret = models.CharField(max_length=SECRET_SIZE, null=True, blank=True)
    token_type = models.SmallIntegerField(choices=TOKEN_TYPES, db_index=True)
    timestamp = models.IntegerField(default=long(time()))
    is_approved = models.BooleanField(default=False)
    lrs_auth_id = models.CharField(max_length=50, null=True)

    user = models.ForeignKey(User, null=True, blank=True, related_name='tokens', db_index=True)
    consumer = models.ForeignKey(Consumer)
    scope = models.CharField(max_length=100, default="statements/write,statements/read/mine")
    
    ## OAuth 1.0a stuff
    verifier = models.CharField(max_length=VERIFIER_SIZE)
    callback = models.CharField(max_length=MAX_URL_LENGTH, null=True, blank=True)
    callback_confirmed = models.BooleanField(default=False)
    
    objects = TokenManager()
    
    def __unicode__(self):
        return u"%s Token %s for %s" % (self.get_token_type_display(), self.key, self.consumer)

    def scope_to_list(self):
        return self.scope.split(",")

    def timestamp_asdatetime(self):
        return datetime.fromtimestamp(self.timestamp)

    def key_partial(self):
        return self.key[:10]

    def to_string(self, only_key=False):
        token_dict = {
            'oauth_token': self.key, 
            'oauth_token_secret': self.secret,
            'oauth_callback_confirmed': self.callback_confirmed and 'true' or 'error'
        }
        if self.verifier:
            token_dict['oauth_verifier'] = self.verifier

        if only_key:
            del token_dict['oauth_token_secret']
            del token_dict['oauth_callback_confirmed']

        return urllib.urlencode(token_dict)

    def generate_random_codes(self):
        """
        Used to generate random key/secret pairings. 
        Use this after you've added the other data in place of save(). 
        """
        key = generate_random(length=KEY_SIZE)
        secret = generate_random(length=SECRET_SIZE)
        while Token.objects.filter(models.Q(key__exact=key) | models.Q(secret__exact=secret)).count():
            key = generate_random(length=KEY_SIZE)
            secret = generate_random(length=SECRET_SIZE)
        self.key = key
        self.secret = secret
        self.save()

    def get_callback_url(self):
        """
        OAuth 1.0a, append the oauth_verifier.
        """
        if self.callback and self.verifier:
            parts = urlparse.urlparse(self.callback)
            scheme, netloc, path, params, query, fragment = parts[:6]
            if query:
                query = '%s&oauth_verifier=%s' % (query, self.verifier)
            else:
                query = 'oauth_verifier=%s' % self.verifier
            return urlparse.urlunparse((scheme, netloc, path, params,
                query, fragment))
        return self.callback

class LanguageMap(models.Model):
    key = models.CharField(max_length=50, db_index=True)
    value = models.TextField()
    
    class Meta:
        abstract = True

    def object_return(self):
        return {self.key: self.value}

    def __unicode__(self):
        return json.dumps(self.object_return())

class VerbDisplay(LanguageMap):
    verb = models.ForeignKey("Verb")

class Verb(models.Model):
    verb_id = models.CharField(max_length=MAX_URL_LENGTH, db_index=True)

    def object_return(self, lang=None):
        ret = {}
        ret['id'] = self.verb_id
        
        if lang is not None:
            lang_map_set = self.verbdisplay_set.filter(key=lang)
        else:
            lang_map_set = self.verbdisplay_set.all()

        if len(lang_map_set) > 0:
            ret['display'] = {}
            for lang_map in lang_map_set:
                ret['display'].update(lang_map.object_return())        
        return ret

    # Just return one value for human-readable
    def get_display(self, lang=None):
        if not len(self.verbdisplay_set.all()) > 0:
            return self.verb_id
        if lang:
            return self.verbdisplay_set.get(key=lang).value

        try:
            return self.verbdisplay_set.get(key='en-US').value
        except:
            try:
                return self.verbdisplay_set.get(key='en').value
            except:
                pass
        return self.verbdisplay_set.all()[0].value

    def __unicode__(self):
        return json.dumps(self.object_return())         


class Extensions(models.Model):
    key=models.CharField(max_length=MAX_URL_LENGTH, db_index=True)
    value=models.TextField()
    
    class Meta:
        abstract = True
    
    def object_return(self):
        return {self.key:self.value}

    def __unicode__(self):
        return json.dumps(self.object_return())
    
    def get_a_name(self):
        return "please override"

agent_attrs_can_only_be_one = ('mbox', 'mbox_sha1sum', 'openID', 'account', 'openid')
class AgentMgr(models.Manager):
    # Have to return ret_agent since we may re-bind it after update
    def update_agent_name_and_members(self, kwargs, ret_agent, members, define):
        need_to_create = False
        # Update the name if not the same
        if 'name' in kwargs and kwargs['name'] != ret_agent.name:
            # If name is different and has define then update-if not then need to create new agent
            if define:
                ret_agent.name = kwargs['name']
                ret_agent.save()
            else:
                need_to_create = True
        # Get or create members in list
        if members:
            ags = [self.gen(**a) for a in members]
            # If any of the members are not in the current member list of ret_agent, add them
            for ag in ags:
                member_agent = ag[0]
                if not member_agent in ret_agent.member.all():
                    if define:
                        ret_agent.member.add(member_agent)
                    else:
                        need_to_create = True
                        break
        return ret_agent, need_to_create

    def create_agent(self, kwargs, define): 
        if 'account' in kwargs:
            account = kwargs['account']
            if 'homePage' in account:
                kwargs['account_homePage'] = kwargs['account']['homePage']

            if 'name' in account:
                kwargs['account_name'] = kwargs['account']['name']

            del kwargs['account']

        if not define:
            kwargs['global_representation'] = False
        ret_agent = Agent(**kwargs)
        ret_agent.clean()
        ret_agent.save()
        return ret_agent, True

    def gen(self, **kwargs):
        types = ['Agent', 'Group']
        if 'objectType' in kwargs and kwargs['objectType'] not in types:
            raise ParamError('Actor objectType must be: %s' % ' or '.join(types))

        # Check if group or not 
        is_group = kwargs.get('objectType', None) == "Group"
        # Find any IFPs
        attrs = [a for a in agent_attrs_can_only_be_one if kwargs.get(a, None) != None]
        # If there is an IFP (could be blank if group) make a dict with the IFP key and value
        if attrs:
            attr = attrs[0]
            if not 'account' == attr:
                attrs_dict = {attr:kwargs[attr]}
            else:
                if not isinstance(kwargs['account'], dict):
                    kwargs['account'] = json.loads(kwargs['account'])
                account = kwargs['account']

                if 'homePage' in account:
                    attrs_dict = {'account_homePage': account['homePage']}

                if 'name' in account:
                    attrs_dict = {'account_name': account['name']}

        # Gen will only get called from AgentManager or Authorization. Since global is true by default and
        # AgentManager always sets the define key based off of the oauth scope, default this to True if the
        # define key is not true
        define = kwargs.pop('define', True)
        
        # Agents won't have members 
        members = None
        # If there is no account, check to see if it a group and has members
        if is_group and 'member' in kwargs:
            mem = kwargs.pop('member')
            try:
                members = json.loads(mem)
            except:
                members = mem
            # If it does not have define permissions, each member in the non-global group must also be
            # non-global
            if not define:
                for a in members:
                    a['global_representation'] = False    
        
        # Try to get the agent/group
        try:
            # If there are no IFPs but there are members (group with no IFPs)
            if not attrs and members:
                ret_agent, created = self.create_agent(kwargs, define)
            else:
                ret_agent = Agent.objects.get(**attrs_dict)
                created = False
                ret_agent, need_to_create = self.update_agent_name_and_members(kwargs, ret_agent, members, define)
                if need_to_create:
                    ret_agent, created = self.create_agent(kwargs, define)
        # If agent/group does not exist, create it then clean and save it so if it's a group below
        # we can add members
        except Agent.DoesNotExist:
            # If no define permission then the created agent/group is non-global
            ret_agent, created = self.create_agent(kwargs, define)

        # If it is a group and has just been created, grab all of the members and send them through
        # this process then clean and save
        if is_group and created:
            # Grabs args for each agent in members list and calls self
            ags = [self.gen(**a) for a in members]
            # Adds each created/retrieved agent object to the return object since ags is a list of tuples (agent, created)
            ret_agent.member.add(*(a for a, c in ags))
        ret_agent.clean()
        ret_agent.save()
        return ret_agent, created

    def oauth_group(self, **kwargs):
        try:
            g = Agent.objects.get(oauth_identifier=kwargs['oauth_identifier'])
            return g, False
        except:
            return Agent.objects.gen(**kwargs)

class Agent(models.Model):
    objectType = models.CharField(max_length=6, blank=True, default="Agent")
    name = models.CharField(max_length=100, blank=True)
    mbox = models.CharField(max_length=128, blank=True, db_index=True)
    mbox_sha1sum = models.CharField(max_length=40, blank=True, db_index=True)
    openID = models.CharField(max_length=MAX_URL_LENGTH, blank=True, db_index=True)
    oauth_identifier = models.CharField(max_length=192, blank=True, db_index=True)
    member = models.ManyToManyField('self', related_name="agents", null=True)
    global_representation = models.BooleanField(default=True)
    account_homePage = models.CharField(max_length=MAX_URL_LENGTH, blank=True)
    account_name = models.CharField(max_length=50, blank=True)    
    objects = AgentMgr()

    def __init__(self, *args, **kwargs):
        if "member" in kwargs:
            if "objectType" in kwargs and kwargs["objectType"] == "Agent":
                raise ParamError('An Agent cannot have members')

            kwargs["objectType"] = "Group"
        super(Agent, self).__init__(*args, **kwargs)

    def clean(self):
        from lrs.util import uri
        if self.mbox != '' and not uri.validate_email(self.mbox):
            raise ValidationError('mbox value [%s] did not start with mailto:' % self.mbox)

        if self.openID != '' and not uri.validate_uri(self.openID):
            raise ValidationError('openID value [%s] is not a valid URI' % self.openID)            

    def get_agent_json(self, format='exact', as_object=False):
        just_id = format == 'ids'
        ret = {}
        # add object type if format isn't id,
        # or if it is a group,
        # or if it's an object
        if not just_id or self.objectType == 'Group' or as_object:
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
                ret['member'] = [a.get_agent_json(format) for a in self.member.all()]
        return ret

    # Used only for /agent GET endpoint (check spec)
    def get_person_json(self):
        ret = {}
        ret['objectType'] = self.objectType
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

    def __unicode__(self):
        return json.dumps(self.get_agent_json())

class AgentProfile(models.Model):
    profileId = models.CharField(max_length=MAX_URL_LENGTH, db_index=True)
    updated = models.DateTimeField(auto_now_add=True, blank=True)
    agent = models.ForeignKey(Agent)
    profile = models.FileField(upload_to="agent_profile")
    content_type = models.CharField(max_length=255,blank=True)
    etag = models.CharField(max_length=50,blank=True)
    user = models.ForeignKey(User, null=True, blank=True)

    def delete(self, *args, **kwargs):
        self.profile.delete()
        super(AgentProfile, self).delete(*args, **kwargs)


class Activity(models.Model):
    activity_id = models.CharField(max_length=MAX_URL_LENGTH, db_index=True)
    objectType = models.CharField(max_length=8,blank=True, default="Activity") 
    activity_definition_type = models.CharField(max_length=MAX_URL_LENGTH, blank=True)
    activity_definition_moreInfo = models.CharField(max_length=MAX_URL_LENGTH, blank=True)
    activity_definition_interactionType = models.CharField(max_length=25, blank=True)    
    authoritative = models.CharField(max_length=100, blank=True)
    global_representation = models.BooleanField(default=True)

    def object_return(self, lang=None, format='exact'):
        ret = {}
        ret['id'] = self.activity_id
        if format != 'ids':
            ret['objectType'] = self.objectType
            
            ret['definition'] = {}
            if lang:
                name_lang_map_set = self.activitydefinitionnamelangmap_set.filter(key=lang)
                desc_lang_map_set = self.activitydefinitiondesclangmap_set.filter(key=lang)
            else:
                name_lang_map_set = self.activitydefinitionnamelangmap_set.all()
                desc_lang_map_set = self.activitydefinitiondesclangmap_set.all()

            if name_lang_map_set:
                ret['definition']['name'] = {}
                for lang_map in name_lang_map_set:
                    ret['definition']['name'].update(lang_map.object_return())
            if desc_lang_map_set:
                ret['definition']['description'] = {}
                for lang_map in desc_lang_map_set:
                    ret['definition']['description'].update(lang_map.object_return())

            if self.activity_definition_type:
                ret['definition']['type'] = self.activity_definition_type
            
            if self.activity_definition_moreInfo != '':
                ret['definition']['moreInfo'] = self.activity_definition_moreInfo

            if self.activity_definition_interactionType != '':
                ret['definition']['interactionType'] = self.activity_definition_interactionType

            # Get answers
            answers = self.correctresponsespatternanswer_set.all()
            if answers:
                ret['definition']['correctResponsesPattern'] = []
                for a in answers:
                    ret['definition']['correctResponsesPattern'].append(a.object_return())            

            # Get scales
            scales = self.activitydefinitionscale_set.all()
            if scales:
                ret['definition']['scale'] = []
                for s in scales:
                    ret['definition']['scale'].append(s.object_return())
            # Get choices
            choices = self.activitydefinitionchoice_set.all()
            if choices:
                ret['definition']['choices'] = []
                for c in choices:
                    ret['definition']['choices'].append(c.object_return())
            # Get steps
            steps = self.activitydefinitionstep_set.all()
            if steps:
                ret['definition']['steps'] = []
                for st in steps:
                    ret['definition']['steps'].append(st.object_return())
            # Get sources
            sources = self.activitydefinitionsource_set.all()
            if sources:
                ret['definition']['source'] = []
                for so in sources:
                    ret['definition']['source'].append(so.object_return())
            # Get targets
            targets = self.activitydefinitiontarget_set.all()
            if targets:
                ret['definition']['target'] = []
                for t in targets:
                    ret['definition']['target'].append(t.object_return())            

            result_ext = self.activitydefinitionextensions_set.all()
            if len(result_ext) > 0:
                ret['definition']['extensions'] = {}
                for ext in result_ext:
                    ret['definition']['extensions'].update(ext.object_return())        

            if not ret['definition']:
                del ret['definition']

        return ret

    def get_a_name(self):
        try:
            return self.activitydefinitionnamelangmap_set.get(key='en-US').value
        except:
            return self.activity_id

    def __unicode__(self):
        return json.dumps(self.object_return())

class ActivityDefinitionNameLangMap(LanguageMap):
    activity = models.ForeignKey(Activity)

class ActivityDefinitionDescLangMap(LanguageMap):
    activity = models.ForeignKey(Activity)

class ActivityDefinitionExtensions(Extensions):
    activity = models.ForeignKey(Activity)

class CorrectResponsesPatternAnswer(models.Model):
    answer = models.TextField()
    activity = models.ForeignKey(Activity)    

    def object_return(self):
        return self.answer

    def __unicode__(self):
        return self.object_return()

class ActivityDefinitionChoiceDesc(LanguageMap):
    act_def_choice = models.ForeignKey("ActivityDefinitionChoice")

class ActivityDefinitionChoice(models.Model):
    choice_id = models.CharField(max_length=50)
    activity = models.ForeignKey(Activity, db_index=True)

    def object_return(self, lang=None):
        ret = {}
        ret['id'] = self.choice_id
        ret['description'] = {}
        
        if lang is not None:
            lang_map_set = self.activitydefinitionchoicedesc_set.filter(key=lang)
        else:
            lang_map_set = self.activitydefinitionchoicedesc_set.all()

        for lang_map in lang_map_set:
            ret['description'].update(lang_map.object_return())
        
        return ret

class ActivityDefinitionScaleDesc(LanguageMap):
    act_def_scale = models.ForeignKey("ActivityDefinitionScale")

class ActivityDefinitionScale(models.Model):
    scale_id = models.CharField(max_length=50)
    activity = models.ForeignKey(Activity, db_index=True)

    def object_return(self, lang=None):
        ret = {}
        ret['id'] = self.scale_id
        ret['description'] = {}
        
        if lang is not None:
            lang_map_set = self.activitydefinitionscaledesc_set.filter(key=lang)
        else:
            lang_map_set = self.activitydefinitionscaledesc_set.all()

        for lang_map in lang_map_set:
            ret['description'].update(lang_map.object_return())
        return ret

class ActivityDefinitionSourceDesc(LanguageMap):
    act_def_source = models.ForeignKey("ActivityDefinitionSource")

class ActivityDefinitionSource(models.Model):
    source_id = models.CharField(max_length=50)
    activity = models.ForeignKey(Activity, db_index=True)
    
    def object_return(self, lang=None):
        ret = {}
        ret['id'] = self.source_id
        ret['description'] = {}
        if lang is not None:
            lang_map_set = self.activitydefinitionsourcedesc_set.filter(key=lang)
        else:
            lang_map_set = self.activitydefinitionsourcedesc_set.all()        

        for lang_map in lang_map_set:
            ret['description'].update(lang_map.object_return())
        return ret

class ActivityDefinitionTargetDesc(LanguageMap):
    act_def_target = models.ForeignKey("ActivityDefinitionTarget")

class ActivityDefinitionTarget(models.Model):
    target_id = models.CharField(max_length=50)
    activity = models.ForeignKey(Activity, db_index=True)
    
    def object_return(self, lang=None):
        ret = {}
        ret['id'] = self.target_id
        ret['description'] = {}
        if lang is not None:
            lang_map_set = self.activitydefinitiontargetdesc_set.filter(key=lang)
        else:
            lang_map_set = self.activitydefinitiontargetdesc_set.all()        

        for lang_map in lang_map_set:
            ret['description'].update(lang_map.object_return())
        return ret

class ActivityDefinitionStepDesc(LanguageMap):
    act_def_step = models.ForeignKey("ActivityDefinitionStep")

class ActivityDefinitionStep(models.Model):
    step_id = models.CharField(max_length=50)
    activity = models.ForeignKey(Activity, db_index=True)

    def object_return(self, lang=None):
        ret = {}
        ret['id'] = self.step_id
        ret['description'] = {}
        if lang is not None:
            lang_map_set = self.activitydefinitionstepdesc_set.filter(key=lang)
        else:
            lang_map_set = self.activitydefinitionstepdesc_set.all()        

        for lang_map in lang_map_set:
            ret['description'].update(lang_map.object_return())
        return ret

class StatementRef(models.Model):
    object_type = models.CharField(max_length=12, default="StatementRef")
    ref_id = models.CharField(max_length=40)

    def object_return(self):
        ret = {}
        ret['objectType'] = "StatementRef"
        ret['id'] = self.ref_id
        return ret

    def get_a_name(self):
        s = Statement.objects.get(statement_id=self.ref_id)
        o, f = s.get_object()
        return " ".join([s.actor.get_a_name(),s.verb.get_display(),o.get_a_name()])


class SubStatementContextActivity(models.Model):
    key = models.CharField(max_length=8)
    context_activity = models.ManyToManyField(Activity)
    substatement = models.ForeignKey('SubStatement')

    def object_return(self, lang=None, format='exact'):
        ret = {}
        ret[self.key] = {}
        ret[self.key] = [a.object_return(lang, format) for a in self.context_activity.all()]
        return ret

class StatementContextActivity(models.Model):
    key = models.CharField(max_length=8)
    context_activity = models.ManyToManyField(Activity)
    statement = models.ForeignKey('Statement')

    def object_return(self, lang=None, format='exact'):
        ret = {}
        ret[self.key] = {}
        ret[self.key] = [a.object_return(lang, format) for a in self.context_activity.all()]
        return ret

class SubStatementContextExtensions(Extensions):
    substatement = models.ForeignKey('SubStatement')

class StatementContextExtensions(Extensions):
    statement = models.ForeignKey('Statement')

class ActivityState(models.Model):
    state_id = models.CharField(max_length=MAX_URL_LENGTH)
    updated = models.DateTimeField(auto_now_add=True, blank=True, db_index=True)
    state = models.FileField(upload_to="activity_state")
    agent = models.ForeignKey(Agent, db_index=True)
    activity_id = models.CharField(max_length=MAX_URL_LENGTH, db_index=True)
    registration_id = models.CharField(max_length=40)
    content_type = models.CharField(max_length=255,blank=True)
    etag = models.CharField(max_length=50,blank=True)
    user = models.ForeignKey(User, null=True, blank=True)

    def delete(self, *args, **kwargs):
        self.state.delete()
        super(ActivityState, self).delete(*args, **kwargs)

class ActivityProfile(models.Model):
    profileId = models.CharField(max_length=MAX_URL_LENGTH, db_index=True)
    updated = models.DateTimeField(auto_now_add=True, blank=True, db_index=True)
    activityId = models.CharField(max_length=MAX_URL_LENGTH, db_index=True)
    profile = models.FileField(upload_to="activity_profile")
    content_type = models.CharField(max_length=255,blank=True)
    etag = models.CharField(max_length=50,blank=True)

    def delete(self, *args, **kwargs):
        self.profile.delete()
        super(ActivityProfile, self).delete(*args, **kwargs)

class StatementResultExtensions(Extensions):
    statement = models.ForeignKey('Statement')
           
class SubStatementResultExtensions(Extensions):
    substatement = models.ForeignKey('SubStatement')

class SubStatement(models.Model):
    object_agent = models.ForeignKey(Agent, related_name="object_of_substatement", on_delete=models.SET_NULL, null=True, db_index=True)
    object_activity = models.ForeignKey(Activity, related_name="object_of_substatement", on_delete=models.SET_NULL, null=True, db_index=True)
    actor = models.ForeignKey(Agent,related_name="actor_of_substatement", null=True, on_delete=models.SET_NULL)
    verb = models.ForeignKey(Verb, null=True, on_delete=models.SET_NULL)
    result_success = models.NullBooleanField()
    result_completion = models.NullBooleanField()
    result_response = models.TextField(blank=True)
    #Made charfield since it would be stored in ISO8601 duration format
    result_duration = models.CharField(max_length=40, blank=True)
    result_score_scaled = models.FloatField(blank=True, null=True)
    result_score_raw = models.FloatField(blank=True, null=True)
    result_score_min = models.FloatField(blank=True, null=True)
    result_score_max = models.FloatField(blank=True, null=True)
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
    # context also has a stmt field which is a statementref
    context_statement = models.CharField(max_length=40, blank=True)
    user = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)

    def object_return(self, lang=None, format='exact'):
        activity_object = True
        ret = {}
        ret['actor'] = self.actor.get_agent_json(format)
        ret['verb'] = self.verb.object_return()

        if self.object_agent:
            ret['object'] = self.object_agent.get_agent_json(format, as_object=True)
        else:
            ret['object'] = self.object_activity.object_return(lang, format)

        ret['result'] = {}
        if self.result_success:
            ret['result']['success'] = self.result_success

        if self.result_completion:
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

        result_ext = self.substatementresultextensions_set.all()
        if len(result_ext) > 0:
            ret['result']['extensions'] = {}
            for ext in result_ext:
                ret['result']['extensions'].update(ext.object_return())        

        if not ret['result']:
            del ret['result']

        ret['context'] = {}
        if self.context_registration:
            ret['context']['registration'] = self.context_registration

        if self.context_instructor:
            ret['context']['instructor'] = self.context_instructor.get_agent_json(format)

        if self.context_team:
            ret['context']['team'] = self.context_team.get_agent_json(format)

        if self.context_revision:
            ret['context']['revision'] = self.context_revision

        if self.context_platform:
            ret['context']['platform'] = self.context_platform

        if self.context_language:
            ret['context']['language'] = self.context_language

        if self.context_statement:
            ret['context']['statement'] = {'id': self.context_statement, 'objectType': 'StatementRef'}

        if len(self.substatementcontextactivity_set.all()) > 0:
            ret['context']['contextActivities'] = {}
            for con_act in self.substatementcontextactivity_set.all():
                ret['context']['contextActivities'].update(con_act.object_return(lang, format))

        context_ext = self.substatementcontextextensions_set.all()
        if len(context_ext) > 0:
            ret['context']['extensions'] = {}
            for ext in context_ext:
                ret['context']['extensions'].update(ext.object_return()) 

        if not ret['context']:
            del ret['context']

        ret['timestamp'] = str(self.timestamp)
        ret['objectType'] = "SubStatement"
        return ret

class StatementAttachmentDisplay(LanguageMap):
    attachment = models.ForeignKey("StatementAttachment")

class StatementAttachmentDesc(LanguageMap):
    attachment = models.ForeignKey("StatementAttachment")

class StatementAttachment(models.Model):
    usageType = models.CharField(max_length=MAX_URL_LENGTH)
    contentType = models.CharField(max_length=128)
    length = models.PositiveIntegerField()
    sha2 = models.CharField(max_length=128, blank=True)
    fileUrl = models.CharField(max_length=MAX_URL_LENGTH, blank=True)
    payload = models.FileField(upload_to="attachment_payloads", null=True)

    def object_return(self, lang=None):
        ret = {}
        ret['usageType'] = self.usageType

        if lang is not None:
            statement_attachment_display_set = self.statementattachmentdisplay_set.filter(key=lang)
            statement_attachment_desc_set = self.statementattachmentdesc_set.filter(key=lang)
        else:
            statement_attachment_display_set = self.statementattachmentdisplay_set.all()
            statement_attachment_desc_set = self.statementattachmentdesc_set.all()

        if len(statement_attachment_display_set) > 0:
            ret['display'] = {}
            for lang_map in statement_attachment_display_set:
                ret['display'].update(lang_map.object_return())
        
        if len(statement_attachment_desc_set) > 0:
            ret['description'] = {}
            for lang_map in statement_attachment_desc_set:
                ret['description'].update(lang_map.object_return())        

        ret['contentType'] = self.contentType
        ret['length'] = self.length

        if self.sha2:
            ret['sha2'] = self.sha2

        if self.fileUrl:
            ret['fileUrl'] = self.fileUrl
        return ret

class Statement(models.Model):
    statement_id = UUIDField(version=1, db_index=True)
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
    #Made charfield since it would be stored in ISO8601 duration format
    result_duration = models.CharField(max_length=40, blank=True)
    result_score_scaled = models.FloatField(blank=True, null=True)
    result_score_raw = models.FloatField(blank=True, null=True)
    result_score_min = models.FloatField(blank=True, null=True)
    result_score_max = models.FloatField(blank=True, null=True)
    stored = models.DateTimeField(auto_now_add=True,blank=True, db_index=True)
    timestamp = models.DateTimeField(blank=True,null=True,
        default=lambda: datetime.utcnow().replace(tzinfo=utc).isoformat())
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
    # context also has a stmt field which is a statementref
    context_statement = models.CharField(max_length=40, blank=True)
    version = models.CharField(max_length=7, default="1.0.0")
    user = models.ForeignKey(User, null=True, blank=True, db_index=True, on_delete=models.SET_NULL)
    attachments = models.ManyToManyField(StatementAttachment)

    def object_return(self, lang=None, format='exact'):
        object_type = 'activity'
        ret = {}
        ret['id'] = self.statement_id
        ret['actor'] = self.actor.get_agent_json(format)
        ret['verb'] = self.verb.object_return()

        if self.object_agent:
            ret['object'] = self.object_agent.get_agent_json(format, as_object=True)            
        elif self.object_activity:
            ret['object'] = self.object_activity.object_return(lang, format)
        elif self.object_substatement:
            ret['object'] = self.object_substatement.object_return(lang, format)
        else:
            ret['object'] = self.object_statementref.object_return()

        ret['result'] = {}
        if self.result_success:
            ret['result']['success'] = self.result_success

        if self.result_completion:
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

        result_ext = self.statementresultextensions_set.all()
        if len(result_ext) > 0:
            ret['result']['extensions'] = {}
            for ext in result_ext:
                ret['result']['extensions'].update(ext.object_return())        

        if not ret['result']:
            del ret['result']

        ret['context'] = {}
        if self.context_registration:
            ret['context']['registration'] = self.context_registration

        if self.context_instructor:
            ret['context']['instructor'] = self.context_instructor.get_agent_json(format)

        if self.context_team:
            ret['context']['team'] = self.context_team.get_agent_json(format)

        if self.context_revision:
            ret['context']['revision'] = self.context_revision

        if self.context_platform:
            ret['context']['platform'] = self.context_platform

        if self.context_language:
            ret['context']['language'] = self.context_language

        if self.context_statement:
            ret['context']['statement'] = {'id': self.context_statement, 'objectType': 'StatementRef'}

        if len(self.statementcontextactivity_set.all()) > 0:
            ret['context']['contextActivities'] = {}
            for con_act in self.statementcontextactivity_set.all():
                ret['context']['contextActivities'].update(con_act.object_return(lang, format))

        context_ext = self.statementcontextextensions_set.all()
        if len(context_ext) > 0:
            ret['context']['extensions'] = {}
            for ext in context_ext:
                ret['context']['extensions'].update(ext.object_return()) 

        if not ret['context']:
            del ret['context']
        
        ret['timestamp'] = str(self.timestamp)
        ret['stored'] = str(self.stored)
        
        if not self.authority is None:
            ret['authority'] = self.authority.get_agent_json(format)
        
        ret['version'] = self.version

        if len(self.attachments.all()) > 0:
            ret['attachments'] = [a.object_return(lang) for a in self.attachments.all()]
        return ret

    def unvoid_statement(self):
        Statement.objects.filter(statement_id=self.object_statementref.ref_id).update(voided=False)        

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
