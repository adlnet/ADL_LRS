import pytz
import ast
import json
import uuid
import urllib
import urlparse
import datetime as dt
from datetime import datetime
from time import time
from django.db import models
from django.db import transaction
from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes import generic
from django.core.exceptions import ValidationError
from django.utils.timezone import utc
from .exceptions import IDNotFoundError, ParamError
from oauth_provider.managers import TokenManager, ConsumerManager
from oauth_provider.consts import KEY_SIZE, SECRET_SIZE, CONSUMER_KEY_SIZE, CONSUMER_STATES,\
                   PENDING, VERIFIER_SIZE, MAX_URL_LENGTH
import pdb
import base64

ADL_LRS_STRING_KEY = 'ADL_LRS_STRING_KEY'

gen_pwd = User.objects.make_random_password
generate_random = User.objects.make_random_password

def gen_uuid():
    return str(uuid.uuid1())

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
    
    key = models.CharField(max_length=CONSUMER_KEY_SIZE, unique=True, default=gen_uuid)
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

import time
def filename(instance, filename):
    print filename
    return filename

class LanguageMap(models.Model):
    key = models.CharField(max_length=50, db_index=True)
    value = models.TextField()
    content_type = models.ForeignKey(ContentType)
    object_id = models.PositiveIntegerField()
    content_object = generic.GenericForeignKey('content_type', 'object_id')
    
    class Meta:
        abstract = True

    def object_return(self):
        return {self.key: self.value}

    def __unicode__(self):
        return json.dumps(self.object_return())

class VerbDisplay(LanguageMap):
    pass

class Verb(models.Model):
    verb_id = models.CharField(max_length=MAX_URL_LENGTH, db_index=True)
    display = generic.GenericRelation(VerbDisplay)

    def object_return(self, lang=None):
        ret = {}
        ret['id'] = self.verb_id
        
        if lang is not None:
            lang_map_set = self.display.filter(key=lang)
        else:
            lang_map_set = self.display.all() 

        if len(lang_map_set) > 0:
            ret['display'] = {}
            for lang_map in lang_map_set:
                ret['display'].update(lang_map.object_return())        
        return ret

    def get_display(self, lang=None):
        if not len(self.display.all()) > 0:
            return self.verb_id
        if lang:
            try:
                return self.display.get(key=lang).value
            except:
                pass
        try:
            return self.display(key='en-US').value
        except:
            try:
                return self.display(key='en').value
            except:
                pass
        return self.display.all()[0].value

    def __unicode__(self):
        return json.dumps(self.object_return())         


class extensions(models.Model):
    key=models.CharField(max_length=MAX_URL_LENGTH, db_index=True)
    value=models.TextField()
    content_type = models.ForeignKey(ContentType)
    object_id = models.PositiveIntegerField()
    content_object = generic.GenericForeignKey('content_type', 'object_id')
    
    class Meta:
        abstract = True
    
    def object_return(self):
        return {self.key:self.value}

    def __unicode__(self):
        return json.dumps(self.object_return())

class ResultExtensions(extensions):
    pass

class result(models.Model): 
    success = models.NullBooleanField()
    completion = models.NullBooleanField()
    response = models.TextField(blank=True)
    #Made charfield since it would be stored in ISO8601 duration format
    duration = models.CharField(max_length=40, blank=True)
    extensions = generic.GenericRelation(ResultExtensions)
    content_type = models.ForeignKey(ContentType)
    object_id = models.PositiveIntegerField()
    content_object = generic.GenericForeignKey('content_type', 'object_id')

    def object_return(self):
        ret = {}
        
        if self.success:
            ret['success'] = self.success

        if self.completion:
            ret['completion'] = self.completion

        if self.response:
            ret['response'] = self.response

        if self.duration:
            ret['duration'] = self.duration
                        
        try:
            ret['score'] = self.score.object_return()
        except score.DoesNotExist:
            pass

        result_ext = self.extensions.all()
        if len(result_ext) > 0:
            ret['extensions'] = {}
            for ext in result_ext:
                ret['extensions'].update(ext.object_return())        
        return ret

    def __unicode__(self):
        return json.dumps(self.object_return())            


class score(models.Model):  
    scaled = models.FloatField(blank=True, null=True)
    raw = models.FloatField(blank=True, null=True)
    score_min = models.FloatField(blank=True, null=True)
    score_max = models.FloatField(blank=True, null=True)
    result = models.OneToOneField(result, blank=True, null=True)
    
    def __init__(self, *args, **kwargs):
        the_min = kwargs.pop('min', None)
        the_max = kwargs.pop('max', None)
        super(score, self).__init__(*args, **kwargs)
        if the_min:
            self.score_min = the_min
        if the_max:
            self.score_max = the_max

    def object_return(self):
        ret = {}
        for field in self._meta.fields:
            if field.name != 'id' and field.name != 'result':
                value = getattr(self, field.name)
                if not value is None:
                    if field.name is 'score_min':
                        ret['min'] = value
                    elif field.name is 'score_max':
                        ret['max'] = value
                    else:
                        ret[field.name] = value
        return ret

    def __unicode__(self):
        return json.dumps(self.object_return())

class KnowsChild(models.Model):
    subclass = models.CharField(max_length=20)

    class Meta:
        abstract = True

    def as_child(self):
        return getattr(self, self.subclass)

    def save(self, *args, **kwargs):
        self.subclass = self.__class__.__name__.lower()
        super(KnowsChild, self).save(*args, **kwargs)

class statement_object(KnowsChild):
    # for linking this to other objects
    content_type = models.ForeignKey(ContentType, null=True)
    object_id = models.PositiveIntegerField(null=True)
    content_object = generic.GenericForeignKey('content_type', 'object_id')

    
    def get_a_name(self):
        return "please override"

agent_attrs_can_only_be_one = ('mbox', 'mbox_sha1sum', 'openid', 'account')
class agentmgr(models.Manager):
    # Have to return ret_agent since we may re-bind it after update
    def update_agent_name_and_members(self, kwargs, ret_agent, members, define):
        need_to_create = False
        # Update the name if not the same
        if 'name' in kwargs and kwargs['name'] != ret_agent.name:
            # If name is different and has define then update-if not then need to create new agent
            if define:
                agent.objects.filter(id=ret_agent.id).update(name=kwargs['name'])
                ret_agent = agent.objects.get(id=ret_agent.id)
            else:
                need_to_create = True
        # Get or create members in list
        if members:
            # If have define, update - if not need to create new agent
            ags = [self.gen(**a) for a in members]
            # If any of the members are not in the current member list of ret_agent, add them
            for ag in ags:
                if not ag[0] in ret_agent.member.all():
                    if define:
                        ret_agent.member.add(ag[0])
                    else:
                        need_to_create = True
                        break
        return ret_agent, need_to_create

    def create_agent(self, kwargs, define):
        if not define:
            kwargs['global_representation'] = False
        ret_agent = agent(**kwargs)
        ret_agent.full_clean(exclude=['subclass', 'content_type', 'content_object', 'object_id'])
        ret_agent.save()
        return ret_agent, True

    # Have to return ret_agent since it can be potentially updated
    def handle_account(self, val, kwargs, members, define):
        # Load into dict if necessary
        if not isinstance(val, dict):
            account = json.loads(val)
        else:
            account = val
        # Try to get the account with the account kwargs. If it exists set ret_agent to the account's
        # agent and created to false. Update agent if necessary
        try:
            if 'homePage' in account:
                from lrs.util import uri
                if not uri.validate_uri(account['homePage']):
                    raise ValidationError('homePage value [%s] is not a valid URI' % account['homePage'])
            acc = agent_account.objects.get(**account)
            created = False
            ret_agent = acc.agent
            ret_agent, need_to_create = self.update_agent_name_and_members(kwargs, ret_agent, members, define)
            if need_to_create:
                ret_agent, created = self.create_agent(kwargs, define)        
        except agent_account.DoesNotExist:
            # If account doesn't exist try to get agent with the remaining kwargs (don't need
            # attr_dict) since IFP is account which doesn't exist yet
            try:
                ret_agent = agent.objects.get(**kwargs)     
            except agent.DoesNotExist:
                # If agent/group does not exist, create, clean, save it and create an account
                # to attach to it. Created account is true. If don't have define permissions
                # then the agent/group is non-global
                if not define:
                    kwargs['global_representation'] = False
                ret_agent = agent(**kwargs)
            ret_agent.full_clean(exclude=['subclass', 'content_type', 'content_object', 'object_id'])
            ret_agent.save()
            acc = agent_account(agent=ret_agent, **account)
            acc.save()
            created = True
        return ret_agent, created

    def gen(self, **kwargs):
        types = ['Agent', 'Group']
        if 'objectType' in kwargs and kwargs['objectType'] not in types:
            raise ParamError('Actor objectType must be: %s' % ' or '.join(types))
        # Gen will only get called from Agent or Authorization. Since global is true by default and
        # Agent always sets the define key based off of the oauth scope, default this to True if the
        # define key is not true
        define = kwargs.pop('define', True)

        # Check if group or not 
        is_group = kwargs.get('objectType', None) == "Group"
        # Find any IFPs
        attrs = [a for a in agent_attrs_can_only_be_one if kwargs.get(a, None) != None]
        # If it is an agent, it must have one IFP
        if not is_group and len(attrs) != 1:
            raise ParamError('One and only one of %s may be supplied with an Agent' % ', '.join(agent_attrs_can_only_be_one))
        # If there is an IFP (could be blank if group) make a dict with the IFP key and value
        if attrs:
            attr = attrs[0]
            # Don't create the attrs_dict if the IFP is an account
            if not 'account' == attr:
                attrs_dict = {attr:kwargs[attr]}
        
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
        
        # Pop account
        val = kwargs.pop('account', None)
        # If it is incoming account object
        if val:
            ret_agent, created = self.handle_account(val, kwargs, members, define)

        # Try to get the agent/group
        try:
            # If there are no IFPs but there are members (group with no IFPs)
            if not attrs and members:
                ret_agent, created = self.create_agent(kwargs, define)
            # Cannot have no IFP and no members
            elif not attrs and not members:
                raise ParamError("Agent object cannot have zero IFPs. If the object has zero IFPs it must be a group with members")
            # If there is and IFP and members (group with IFP that's not account since it should be
            # updated already from above)if there is an IFP that isn't account and no members (agent object)
            else:
                if not 'account' in attrs:
                    ret_agent = agent.objects.get(**attrs_dict)
                    created = False
                ret_agent, need_to_create = self.update_agent_name_and_members(kwargs, ret_agent, members, define)
                if need_to_create:
                    ret_agent, created = self.create_agent(kwargs, define)
        # If agent/group does not exist, create it then clean and save it so if it's a group below
        # we can add members
        except agent.DoesNotExist:
            # If no define permission then the created agent/group is non-global
            ret_agent, created = self.create_agent(kwargs, define)

        # If it is a group and has just been created, grab all of the members and send them through
        # this process then clean and save
        if is_group and created:
            ags = [self.gen(**a) for a in members]
            ret_agent.member.add(*(a for a, c in ags))
        ret_agent.full_clean(exclude='subclass, content_type, content_object, object_id')
        ret_agent.save()
        return ret_agent, created

    def oauth_group(self, **kwargs):
        try:
            g = agent.objects.get(oauth_identifier=kwargs['oauth_identifier'])
            return g, False
        except:
            return agent.objects.gen(**kwargs)

class agent(statement_object):
    objectType = models.CharField(max_length=6, blank=True, default="Agent")
    name = models.CharField(max_length=100, blank=True)
    mbox = models.CharField(max_length=128, blank=True, db_index=True)
    mbox_sha1sum = models.CharField(max_length=40, blank=True, db_index=True)
    openid = models.CharField(max_length=MAX_URL_LENGTH, blank=True, db_index=True)
    oauth_identifier = models.CharField(max_length=192, blank=True, db_index=True)
    member = models.ManyToManyField('self', related_name="agents", null=True)
    global_representation = models.BooleanField(default=True)
    objects = agentmgr()

    def __init__(self, *args, **kwargs):
        if "member" in kwargs:
            if "objectType" in kwargs and kwargs["objectType"] == "Agent":
                raise ParamError('An Agent cannot have members')

            kwargs["objectType"] = "Group"
        super(agent, self).__init__(*args, **kwargs)

    def clean(self):
        from lrs.util import uri
        if self.mbox != '' and not uri.validate_email(self.mbox):
            raise ValidationError('mbox value [%s] did not start with mailto:' % self.mbox)

        if self.openid != '' and not uri.validate_uri(self.openid):
            raise ValidationError('openid value [%s] is not a valid URI' % self.openid)            

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
        if self.openid:
            ret['openid'] = self.openid
        try:
            ret['account'] = self.agent_account.get_json()
        except:
            pass
        if self.objectType == 'Group':
            # show members for groups if format isn't 'ids'
            # show members' ids for anon groups if format is 'ids'
            if not just_id or not (set(['mbox','mbox_sha1sum','openid','account']) & set(ret.keys())):
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
        if self.openid:
            ret['openid'] = [self.openid]
        try:
            ret['account'] = [self.agent_account.get_json()]
        except:
            pass
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
        try:
            return self.agent_account.get_a_name()
        except:
            if self.objectType == 'Agent':
                return "unknown"
            else:
                return "anonymous group"

    def __unicode__(self):
        return json.dumps(self.get_agent_json())


class agent_account(models.Model):  
    homePage = models.CharField(max_length=MAX_URL_LENGTH, blank=True)
    name = models.CharField(max_length=50)
    agent = models.OneToOneField(agent, null=True)

    def get_json(self):
        ret = {}
        ret['homePage'] = self.homePage
        ret['name'] = self.name
        return ret
    
    def equals(self, other):
        if not isinstance(other, self.__class__):
            raise TypeError('Only models of same class can be compared')
        return self.name == other.name and self.homePage == other.homePage 

    def get_a_name(self):
        return self.name

    def __unicode__(self):
        return json.dumps(self.get_json())


class agent_profile(models.Model):
    profileId = models.CharField(max_length=MAX_URL_LENGTH, db_index=True)
    updated = models.DateTimeField(auto_now_add=True, blank=True)
    agent = models.ForeignKey(agent)
    profile = models.FileField(upload_to="agent_profile")
    content_type = models.CharField(max_length=255,blank=True)
    etag = models.CharField(max_length=50,blank=True)
    user = models.ForeignKey(User, null=True, blank=True)

    def delete(self, *args, **kwargs):
        self.profile.delete()
        super(agent_profile, self).delete(*args, **kwargs)


class activity(statement_object):
    activity_id = models.CharField(max_length=MAX_URL_LENGTH, db_index=True)
    objectType = models.CharField(max_length=8,blank=True, default="Activity") 
    authoritative = models.CharField(max_length=100, blank=True)
    global_representation = models.BooleanField(default=True)

    def object_return(self, lang=None, format='exact'):
        ret = {}
        ret['id'] = self.activity_id
        if format != 'ids':
            ret['objectType'] = self.objectType
            try:
                ret['definition'] = self.activity_definition.object_return(lang)
            except activity_definition.DoesNotExist:
                pass
        return ret

    def get_a_name(self):
        try:
            return self.activity_definition.name.get(key='en-US').value
        except:
            return self.activity_id

    def __unicode__(self):
        return json.dumps(self.object_return())

class name_lang(models.Model):
    key = models.CharField(max_length=50, db_index=True)
    value = models.TextField()
    content_type = models.ForeignKey(ContentType)
    object_id = models.PositiveIntegerField()
    content_object = generic.GenericForeignKey('content_type', 'object_id')
    
    def object_return(self):
        return {self.key: self.value}

    def __unicode__(self):
        return json.dumps(self.object_return())

class desc_lang(models.Model):
    key = models.CharField(max_length=50, db_index=True)
    value = models.TextField()
    content_type = models.ForeignKey(ContentType)
    object_id = models.PositiveIntegerField()
    content_object = generic.GenericForeignKey('content_type', 'object_id')
    
    def object_return(self):
        return {self.key: self.value}

    def __unicode__(self):
        return json.dumps(self.object_return())

class ActivityDefinitionExtensions(extensions):
    pass

class activity_definition(models.Model):
    name = generic.GenericRelation(name_lang, related_name="name_lang")
    description = generic.GenericRelation(desc_lang, related_name="desc_lang")
    activity_definition_type = models.CharField(max_length=MAX_URL_LENGTH, blank=True)
    moreInfo = models.CharField(max_length=MAX_URL_LENGTH, blank=True)
    interactionType = models.CharField(max_length=25, blank=True)
    activity = models.OneToOneField(activity)
    extensions = generic.GenericRelation(ActivityDefinitionExtensions)

    def object_return(self, lang=None):
        ret = {}
        if lang:
            name_lang_map_set = self.name.filter(key=lang)
            desc_lang_map_set = self.description.filter(key=lang)
        else:
            name_lang_map_set = self.name.all()
            desc_lang_map_set = self.description.all()

        if name_lang_map_set:
            ret['name'] = {}
            for lang_map in name_lang_map_set:
                ret['name'].update(lang_map.object_return())
        if desc_lang_map_set:
            ret['description'] = {}
            for lang_map in desc_lang_map_set:
                ret['description'].update(lang_map.object_return())

        if self.activity_definition_type:
            ret['type'] = self.activity_definition_type
        
        if self.moreInfo != '':
            ret['moreInfo'] = self.moreInfo

        if self.interactionType != '':
            ret['interactionType'] = self.interactionType

        try:
            self.correctresponsespattern = self.activity_def_correctresponsespattern
        except activity_def_correctresponsespattern.DoesNotExist:
            self.correctresponsespattern = None

        if not self.correctresponsespattern is None:
            ret['correctResponsesPattern'] = []
            # Get answers
            answers = correctresponsespattern_answer.objects.filter(correctresponsespattern=self.correctresponsespattern)
            for a in answers:
                ret['correctResponsesPattern'].append(a.objReturn())            
            scales = activity_definition_scale.objects.filter(activity_definition=self)
            if scales:
                ret['scale'] = []
                for s in scales:
                    ret['scale'].append(s.object_return())
            # Get choices
            choices = activity_definition_choice.objects.filter(activity_definition=self)
            if choices:
                ret['choices'] = []
                for c in choices:
                    ret['choices'].append(c.object_return())
            # Get steps
            steps = activity_definition_step.objects.filter(activity_definition=self)
            if steps:
                ret['steps'] = []
                for st in steps:
                    ret['steps'].append(st.object_return())
            # Get sources
            sources = activity_definition_source.objects.filter(activity_definition=self)
            if sources:
                ret['source'] = []
                for so in sources:
                    ret['source'].append(so.object_return())
            # Get targets
            targets = activity_definition_target.objects.filter(activity_definition=self)
            if targets:
                ret['target'] = []
                for t in targets:
                    ret['target'].append(t.object_return())            
        result_ext = self.extensions.all()
        if len(result_ext) > 0:
            ret['extensions'] = {}
            for ext in result_ext:
                ret['extensions'].update(ext.object_return())        
        return ret

    def __unicode__(self):
        return json.dumps(self.object_return())


class activity_def_correctresponsespattern(models.Model):
    activity_definition = models.OneToOneField(activity_definition, blank=True, null=True)

class correctresponsespattern_answer(models.Model):
    answer = models.TextField()
    correctresponsespattern = models.ForeignKey(activity_def_correctresponsespattern)    

    def objReturn(self):
        return self.answer

    def __unicode__(self):
        return objReturn()

class ActivityDefinitionChoiceDesc(LanguageMap):
    pass

class activity_definition_choice(models.Model):
    choice_id = models.CharField(max_length=50)
    description = generic.GenericRelation(ActivityDefinitionChoiceDesc)
    activity_definition = models.ForeignKey(activity_definition, db_index=True)

    def object_return(self, lang=None):
        ret = {}
        ret['id'] = self.choice_id
        ret['description'] = {}
        
        if lang is not None:
            lang_map_set = self.description.filter(key=lang)
        else:
            lang_map_set = self.description.all()

        for lang_map in lang_map_set:
            ret['description'].update(lang_map.object_return())
        
        return ret

class ActivityDefinitionScaleDesc(LanguageMap):
    pass

class activity_definition_scale(models.Model):
    scale_id = models.CharField(max_length=50)
    description = generic.GenericRelation(ActivityDefinitionScaleDesc)
    activity_definition = models.ForeignKey(activity_definition, db_index=True)

    def object_return(self, lang=None):
        ret = {}
        ret['id'] = self.scale_id
        ret['description'] = {}
        
        if lang is not None:
            lang_map_set = self.description.filter(key=lang)
        else:
            lang_map_set = self.description.all()

        for lang_map in lang_map_set:
            ret['description'].update(lang_map.object_return())
        return ret

class ActivityDefinitionSourceDesc(LanguageMap):
    pass

class activity_definition_source(models.Model):
    source_id = models.CharField(max_length=50)
    description = generic.GenericRelation(ActivityDefinitionSourceDesc)
    activity_definition = models.ForeignKey(activity_definition, db_index=True)
    
    def object_return(self, lang=None):
        ret = {}
        ret['id'] = self.source_id
        ret['description'] = {}
        if lang is not None:
            lang_map_set = self.description.filter(key=lang)
        else:
            lang_map_set = self.description.all()        

        for lang_map in lang_map_set:
            ret['description'].update(lang_map.object_return())
        return ret

class ActivityDefinitionTargetDesc(LanguageMap):
    pass

class activity_definition_target(models.Model):
    target_id = models.CharField(max_length=50)
    description = generic.GenericRelation(ActivityDefinitionTargetDesc)
    activity_definition = models.ForeignKey(activity_definition, db_index=True)
    
    def object_return(self, lang=None):
        ret = {}
        ret['id'] = self.target_id
        ret['description'] = {}
        if lang is not None:
            lang_map_set = self.description.filter(key=lang)
        else:
            lang_map_set = self.description.all()        

        for lang_map in lang_map_set:
            ret['description'].update(lang_map.object_return())
        return ret

class ActivityDefinitionStepDesc(LanguageMap):
    pass

class activity_definition_step(models.Model):
    step_id = models.CharField(max_length=50)
    description = generic.GenericRelation(ActivityDefinitionStepDesc)
    activity_definition = models.ForeignKey(activity_definition, db_index=True)

    def object_return(self, lang=None):
        ret = {}
        ret['id'] = self.step_id
        ret['description'] = {}
        if lang is not None:
            lang_map_set = self.description.filter(key=lang)
        else:
            lang_map_set = self.description.all()        

        for lang_map in lang_map_set:
            ret['description'].update(lang_map.object_return())
        return ret


class StatementRef(statement_object):
    object_type = models.CharField(max_length=12, default="StatementRef")
    ref_id = models.CharField(max_length=40)

    def object_return(self):
        ret = {}
        ret['objectType'] = "StatementRef"
        ret['id'] = self.ref_id
        return ret

    def get_a_name(self):
        s = statement.objects.get(statement_id=self.ref_id)
        o, f = s.get_object()
        return " ".join([s.actor.get_a_name(),s.verb.get_display(),o.get_a_name()])


class ContextActivity(models.Model):
    key = models.CharField(max_length=8)
    context_activity = models.ManyToManyField(activity)
    context = models.ForeignKey('context')

    def object_return(self, lang=None, format='exact'):
        ret = {}
        ret[self.key] = {}
        ret[self.key] = [a.object_return(lang, format) for a in self.context_activity.all()]
        return ret

class ContextExtensions(extensions):
    pass

class context(models.Model):
    registration = models.CharField(max_length=40, blank=True, db_index=True)
    instructor = models.ForeignKey(agent,blank=True, null=True, on_delete=models.SET_NULL, db_index=True,
        related_name='context_instructor')
    team = models.ForeignKey(agent,blank=True, null=True, on_delete=models.SET_NULL,
        related_name="context_team")
    revision = models.TextField(blank=True)
    platform = models.CharField(max_length=50,blank=True)
    language = models.CharField(max_length=50,blank=True)
    extensions = generic.GenericRelation(ContextExtensions)
    # context also has a stmt field which can reference a sub-statement or statementref
    statement = generic.GenericRelation(statement_object)

    def object_return(self, lang=None, format='exact'):
        ret = {}
        linked_fields = ['instructor', 'team']
        for field in self._meta.fields:
            if field.name != 'id':
                value = getattr(self, field.name)
                if not value is None and value != "":
                    if not field.name in linked_fields:
                        ret[field.name] = value
                    elif field.name == 'instructor':
                        ret[field.name] = self.instructor.get_agent_json(format)
                    elif field.name == 'team':
                        ret[field.name] = self.team.get_agent_json(format)

        if len(self.statement.all()) > 0:
            subclass = self.statement.all()[0].subclass
            if subclass == 'statementref':
                cntx_stmt = StatementRef.objects.get(id=self.statement.all()[0].id)
                ret['statement'] = cntx_stmt.object_return()          
            elif subclass == 'substatement':
                cntx_stmt = SubStatement.objects.get(id=self.statement.all()[0].id)
                ret['statement'] = cntx_stmt.object_return(lang, format)          

        if len(self.contextactivity_set.all()) > 0:
            ret['contextActivities'] = {}
            for con_act in self.contextactivity_set.all():
                ret['contextActivities'].update(con_act.object_return(lang, format))

        context_ext = self.extensions.all()
        if len(context_ext) > 0:
            ret['extensions'] = {}
            for ext in context_ext:
                ret['extensions'].update(ext.object_return())        
        return ret

class activity_state(models.Model):
    state_id = models.CharField(max_length=MAX_URL_LENGTH)
    updated = models.DateTimeField(auto_now_add=True, blank=True, db_index=True)
    state = models.FileField(upload_to="activity_state")
    agent = models.ForeignKey(agent, db_index=True)
    activity_id = models.CharField(max_length=MAX_URL_LENGTH, db_index=True)
    registration_id = models.CharField(max_length=40)
    content_type = models.CharField(max_length=255,blank=True)
    etag = models.CharField(max_length=50,blank=True)
    user = models.ForeignKey(User, null=True, blank=True)

    def delete(self, *args, **kwargs):
        self.state.delete()
        super(activity_state, self).delete(*args, **kwargs)

class activity_profile(models.Model):
    profileId = models.CharField(max_length=MAX_URL_LENGTH, db_index=True)
    updated = models.DateTimeField(auto_now_add=True, blank=True, db_index=True)
    activityId = models.CharField(max_length=MAX_URL_LENGTH, db_index=True)
    profile = models.FileField(upload_to="activity_profile")
    content_type = models.CharField(max_length=255,blank=True)
    etag = models.CharField(max_length=50,blank=True)

    def delete(self, *args, **kwargs):
        self.profile.delete()
        super(activity_profile, self).delete(*args, **kwargs)

class SubStatement(statement_object):
    stmt_object = models.ForeignKey(statement_object, related_name="object_of_substatement", null=True,
        on_delete=models.SET_NULL)
    actor = models.ForeignKey(agent,related_name="actor_of_substatement", null=True, on_delete=models.SET_NULL)
    verb = models.ForeignKey(Verb, null=True, on_delete=models.SET_NULL)
    result = generic.GenericRelation(result)
    timestamp = models.DateTimeField(blank=True,null=True,
        default=lambda: datetime.utcnow().replace(tzinfo=utc).isoformat())
    context = models.OneToOneField(context, related_name="substatement_context", null=True,
        on_delete=models.SET_NULL)
    user = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)

    def get_a_name(self):
        return self.stmt_object.statement_id
    
    def object_return(self, lang=None, format='exact'):
        activity_object = True
        ret = {}
        ret['actor'] = self.actor.get_agent_json(format)
        ret['verb'] = self.verb.object_return()
        subclass = self.stmt_object.subclass

        if subclass == 'activity':
           stmt_object = activity.objects.get(id=self.stmt_object.id)
        elif subclass == 'agent':
            stmt_object = agent.objects.get(id=self.stmt_object.id)
            activity_object = False
        else: 
            raise IDNotFoundError('No activity or agent object found with given ID')
        if activity_object:
            ret['object'] = stmt_object.object_return(lang, format)  
        else:
            ret['object'] = stmt_object.get_agent_json(format, as_object=True)

        if len(self.result.all()) > 0:
            # if any, should only be 1
            ret['result'] = self.result.all()[0].object_return()

        if self.context:
            ret['context'] = self.context.object_return(lang, format)
        ret['timestamp'] = str(self.timestamp)
        ret['objectType'] = "SubStatement"
        return ret

    def get_object(self):
        subclass = self.stmt_object.subclass
        if subclass == 'activity':
            stmt_object = activity.objects.get(id=self.stmt_object.id)
        elif subclass == 'agent':
            stmt_object = agent.objects.get(id=self.stmt_object.id)
        else:
            raise IDNotFoundError("No activity, or agent found with given ID")
        return stmt_object, subclass

    def delete(self, *args, **kwargs):
        stmt_object = None
        object_type = None

        stmt_object, object_type = self.get_object()

        # If there is a context
        if self.context:
            cntx = context.objects.get(id=self.context.id)
            cntx.delete()

        if object_type == 'statementref':
            stmt_object.delete()

        super(SubStatement, self).delete(*args, **kwargs)

class StatementAttachmentDisplay(LanguageMap):
    pass

class StatementAttachmentDesc(LanguageMap):
    pass

class StatementAttachment(models.Model):
    usageType = models.CharField(max_length=MAX_URL_LENGTH)
    contentType = models.CharField(max_length=128)
    display = generic.GenericRelation(StatementAttachmentDisplay)
    description = generic.GenericRelation(StatementAttachmentDesc)
    length = models.PositiveIntegerField()
    sha2 = models.CharField(max_length=128, blank=True)
    fileUrl = models.CharField(max_length=MAX_URL_LENGTH, blank=True)
    payload = models.FileField(upload_to="attachment_payloads", null=True)

    def object_return(self, lang=None):
        ret = {}
        ret['usageType'] = self.usageType

        if lang is not None:
            statement_attachment_display_set = self.display.filter(key=lang)
            statement_attachment_desc_set = self.description.filter(key=lang)
        else:
            statement_attachment_display_set = self.display.all()
            statement_attachment_desc_set = self.description.all()

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

class statement(models.Model):
    statement_id = models.CharField(max_length=40, unique=True, default=gen_uuid, db_index=True)
    stmt_object = models.ForeignKey(statement_object, related_name="object_of_statement", db_index=True,
        null=True, on_delete=models.SET_NULL)
    actor = models.ForeignKey(agent,related_name="actor_statement", db_index=True, null=True,
        on_delete=models.SET_NULL)
    verb = models.ForeignKey(Verb, null=True, on_delete=models.SET_NULL)
    result = generic.GenericRelation(result)
    stored = models.DateTimeField(auto_now_add=True,blank=True)
    timestamp = models.DateTimeField(blank=True,null=True,
        default=lambda: datetime.utcnow().replace(tzinfo=utc).isoformat())
    authority = models.ForeignKey(agent, blank=True,null=True,related_name="authority_statement", db_index=True,
        on_delete=models.SET_NULL)
    voided = models.NullBooleanField(default=False)
    context = models.OneToOneField(context, related_name="statement_context", null=True, on_delete=models.SET_NULL)
    version = models.CharField(max_length=7, default="1.0.0")
    user = models.ForeignKey(User, null=True, blank=True, db_index=True, on_delete=models.SET_NULL)
    attachments = models.ManyToManyField(StatementAttachment)

    def get_a_name(self):
        return self.statement_id

    def get_object(self):
        subclass = self.stmt_object.subclass
        if subclass == 'activity':
            stmt_object = activity.objects.get(id=self.stmt_object.id)
        elif subclass == 'agent':    
            stmt_object = agent.objects.get(id=self.stmt_object.id)
        elif subclass == 'substatement':
            stmt_object = SubStatement.objects.get(id=self.stmt_object.id)
        elif subclass == 'statementref':
            stmt_object = StatementRef.objects.get(id=self.stmt_object.id)
        else:
            raise IDNotFoundError("No activity, agent, substatement, or statementref found with given ID")
        return stmt_object, subclass

    def object_return(self, lang=None, format='exact'):
        object_type = 'activity'
        ret = {}
        ret['id'] = self.statement_id
        ret['actor'] = self.actor.get_agent_json(format)
        ret['verb'] = self.verb.object_return()

        stmt_object, object_type = self.get_object()
        if object_type == 'activity':
            ret['object'] = stmt_object.object_return(lang, format)
        elif object_type == 'substatement':
            ret['object'] = stmt_object.object_return(lang, format)  
        elif object_type == 'statementref':
            ret['object'] = stmt_object.object_return()
        else:
            ret['object'] = stmt_object.get_agent_json(format, as_object=True)
        if len(self.result.all()) > 0:
            # should only ever be one.. used generic fk to handle sub stmt and stmt
            ret['result'] = self.result.all()[0].object_return()        

        if self.context:
            ret['context'] = self.context.object_return(lang, format)
        
        ret['timestamp'] = str(self.timestamp)
        ret['stored'] = str(self.stored)
        
        if not self.authority is None:
            ret['authority'] = self.authority.get_agent_json(format)
        
        ret['version'] = self.version

        if len(self.attachments.all()) > 0:
            ret['attachments'] = [a.object_return(lang) for a in self.attachments.all()]
        return ret

    def unvoid_statement(self):
        statement_ref = StatementRef.objects.get(id=self.stmt_object.id)
        voided_stmt = statement.objects.filter(statement_id=statement_ref.ref_id).update(voided=False)

    def delete(self, *args, **kwargs):
        stmt_object = None
        object_type = None
        
        # Unvoid stmt if verb is voided
        if self.verb.verb_id == 'http://adlnet.gov/expapi/verbs/voided':
            self.unvoid_statement()
        # Else retrieve its object
        else:
            stmt_object, object_type = self.get_object()

        # If there is a context get it and call it's delete (FK will be set to null here)
        if self.context:
            cntx = context.objects.get(id=self.context.id)
            cntx.delete()
        
        # If sub or ref, FK will be set to null, then call delete
        if self.verb.verb_id != 'http://adlnet.gov/expapi/verbs/voided':
            if object_type == 'substatement' or object_type == 'statementref':
                stmt_object.delete()

        super(statement, self).delete(*args, **kwargs)
