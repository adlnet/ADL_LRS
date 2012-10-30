from django.db import models
from django.db import transaction
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes import generic
from django.contrib.contenttypes.generic import GenericForeignKey
from django.core import serializers
from datetime import datetime
from django.utils.timezone import utc
from lrs.exceptions import IDNotFoundError, ParamError
import ast
import json
import pdb
#this is BAD, if anyone knows a better way to store kv pairs in MySQL let me know

ADL_LRS_STRING_KEY = 'ADL_LRS_STRING_KEY'

def convertToUTC(timestr):
    # Strip off TZ info
    timestr = timestr[:timestr.rfind('+')]
    
    # Convert to date_object (directive for parsing TZ out is buggy, which is why we do it this way)
    date_object = datetime.strptime(timestr, '%Y-%m-%dT%H:%M:%S.%f')
    
    # Localize TZ to UTC since everything is being stored in DB as UTC
    date_object = pytz.timezone("UTC").localize(date_object)
    return date_object

import time
def filename(instance, filename):
    print filename
    return filename

class score(models.Model):  
    scaled = models.FloatField(blank=True, null=True)
    raw = models.PositiveIntegerField(blank=True, null=True)
    score_min = models.PositiveIntegerField(blank=True, null=True)
    score_max = models.PositiveIntegerField(blank=True, null=True)
    
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
            if not field.name == 'id':
                value = getattr(self, field.name)
                if not value is None:
                    ret[field.name] = value
        return ret

class result(models.Model): 
    success = models.NullBooleanField(blank=True,null=True)
    completion = models.NullBooleanField(blank=True,null=True)
    response = models.CharField(max_length=200, blank=True, null=True)
    #Made charfield since it would be stored in ISO8601 duration format
    duration = models.CharField(max_length=200, blank=True, null=True)
    score = models.OneToOneField(score, blank=True, null=True)

    def object_return(self):
        ret = {}
        for field in self._meta.fields:
            if not field.name == 'id':
                value = getattr(self, field.name)
                if not value is None:
                    if not field.name == 'score':
                        ret[field.name] = value
                    else:
                        ret[field.name] = self.score.object_return()
        ret['extensions'] = {}
        result_ext = result_extensions.objects.filter(result=self)
        for ext in result_ext:
            ret['extensions'][ext.key] = ext.value        
        return ret

class result_extensions(models.Model):
    key=models.CharField(max_length=200)
    value=models.CharField(max_length=200)
    result = models.ForeignKey(result)

    def object_return(self):
        return (self.key, self.value)

class statement_object(models.Model):
    pass

agent_attrs_can_only_be_one = ('mbox', 'mbox_sha1sum', 'openid', 'account')
class agentmgr(models.Manager):
    def gen(self, **kwargs):
        group = kwargs.get('objectType', None) == "Group"
        attrs = [a for a in agent_attrs_can_only_be_one if kwargs.get(a, None) != None]
        if not group and len(attrs) != 1:
            raise ParamError('One and only one of %s may be supplied' % ', '.join(agent_attrs_can_only_be_one))
        val = kwargs.pop('account', None)
        if val:
            if isinstance(val, agent_account):
                kwargs['account'] = val
            elif isinstance(val, int):
                try:
                    kwargs['account'] = agent_account.objects.get(pk=val)
                except agent_account.DoesNotExist:
                    raise IDNotFoundError('Agent Account ID was not found')
            else:
                if not isinstance(val, dict):
                    try:
                        account = ast.literal_eval(val)
                    except:
                        account = json.loads(val)
                else:
                    account = val
                try:
                    acc = agent_account.objects.get(**account)
                except agent_account.DoesNotExist:
                    acc = agent_account(**account)
                    acc.save()
                kwargs['account'] = acc
        if group and 'member' in kwargs:
            mem = kwargs.pop('member')
            try:
                members = ast.literal_eval(mem)
            except:
                try:
                    members = json.loads(mem)
                except:
                    members = mem
        try:
            agent = self.get(**kwargs)
            created = False
        except self.model.DoesNotExist:
            agent = self.model(**kwargs)
            agent.save()
            created = True
        if group:
            ags = [self.gen(**a) for a in members]
            agent.member.add(*(a for a, c in ags))
        agent.save()
        return agent, created

class agent_account(models.Model):  
    homePage = models.CharField(max_length=200, blank=True, null=True)
    name = models.CharField(max_length=200)

    def get_json(self):
        ret = {}
        ret['homePage'] = self.homePage
        ret['name'] = self.name
        return ret
    
    def equals(self, other):
        if not isinstance(other, self.__class__):
            raise TypeError('Only models of same class can be compared')
        return self.name == other.name and self.homePage == other.homePage 


class agent(statement_object):
    objectType = models.CharField(max_length=200, blank=True, default="Agent")
    name = models.CharField(max_length=200, blank=True, null=True)
    mbox = models.CharField(max_length=200, blank=True, null=True)
    mbox_sha1sum = models.CharField(max_length=200, blank=True, null=True)
    openid = models.CharField(max_length=200, blank=True, null=True)
    account = models.OneToOneField('agent_account', blank=True, null=True)
    objects = agentmgr()

    def get_agent_json(self):
        ret = {}
        ret['objectType'] = self.objectType
        if self.name:
            ret['name'] = self.name
        if self.mbox:
            ret['mbox'] = self.mbox
        if self.mbox_sha1sum:
            ret['mbox_sha1sum'] = self.mbox_sha1sum
        if self.openid:
            ret['openid'] = self.openid
        if self.account:
            ret['account'] = self.account.get_json()
        return ret

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
        if self.account:
            ret['account'] = [self.account.get_json()]
        return ret


class group(agent):
    member = models.ManyToManyField(agent, related_name="agents")
    objects = agentmgr()

    def __init__(self, *args, **kwargs):
        kwargs["objectType"] = "Group"
        super(group, self).__init__(*args, **kwargs)

    def get_agent_json(self):
        ret = super(group, self).get_agent_json()
        ret['member'] = [a.get_agent_json() for a in self.member.all()]
        return ret


class agent_profile(models.Model):
    profileId = models.CharField(max_length=200)
    updated = models.DateTimeField(auto_now_add=True, blank=True)
    agent = models.ForeignKey(agent)
    profile = models.FileField(upload_to="agent_profile")
    content_type = models.CharField(max_length=200,blank=True,null=True)
    etag = models.CharField(max_length=200,blank=True,null=True)

    def delete(self, *args, **kwargs):
        self.profile.delete()
        super(agent_profile, self).delete(*args, **kwargs)

class LanguageMap(models.Model):
    key = models.CharField(max_length=200)
    value = models.CharField(max_length=200)
    
    def object_return(self):
        return (self.key, self.value)

class activity_def_correctresponsespattern(models.Model):
    pass

class activity_definition(models.Model):
    name = models.ManyToManyField(LanguageMap, related_name="activity_definition_name", blank=True, null=True)
    description = models.ManyToManyField(LanguageMap, related_name="activity_definition_description", blank=True, null=True)
    activity_definition_type = models.CharField(max_length=200, blank=True, null=True)
    interactionType = models.CharField(max_length=200, blank=True, null=True)
    correctresponsespattern = models.OneToOneField(activity_def_correctresponsespattern, blank=True, null=True)

    def object_return(self, lang=None):
        ret = {}
        if lang is not None:
            name_lang_map_set = self.name.filter(key=lang)
            desc_lang_map_set = self.name.filter(key=lang)
        else:
            name_lang_map_set = self.name.all()
            desc_lang_map_set = self.description.all()

        ret['name'] = {}
        ret['description'] = {}
        for lang_map in name_lang_map_set:
            ret['name'][lang_map.key] = lang_map.value                    
        for lang_map in desc_lang_map_set:
            ret['description'][lang_map.key] = lang_map.value 

        ret['type'] = self.activity_definition_type
        
        if not self.interactionType is None:
            ret['interactionType'] = self.interactionType

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
                    ret['scale'].append(s.object_return(lang))
            # Get choices
            choices = activity_definition_choice.objects.filter(activity_definition=self)
            if choices:
                ret['choices'] = []
                for c in choices:
                    ret['choices'].append(c.object_return(lang))
            # Get steps
            steps = activity_definition_step.objects.filter(activity_definition=self)
            if steps:
                ret['steps'] = []
                for st in steps:
                    ret['steps'].append(st.object_return(lang))
            # Get sources
            sources = activity_definition_source.objects.filter(activity_definition=self)
            if sources:
                ret['source'] = []
                for so in sources:
                    ret['source'].append(so.object_return(lang))
            # Get targets
            targets = activity_definition_target.objects.filter(activity_definition=self)
            if targets:
                ret['target'] = []
                for t in targets:
                    ret['target'].append(t.object_return(lang))            
        act_def_ext = activity_extensions.objects.filter(activity_definition=self)
        if act_def_ext:
            ret['extensions'] = {}             
            for ext in act_def_ext:
                ret['extensions'][ext.key] = ext.value        
        return ret



class activity(statement_object):
    activity_id = models.CharField(max_length=200)
    objectType = models.CharField(max_length=200,blank=True, null=True) 
    activity_definition = models.OneToOneField(activity_definition, blank=True, null=True)
    authoritative = models.CharField(max_length=200, blank=True, null=True)

    def object_return(self, lang=None):

        ret = {}
        ret['id'] = self.activity_id
        ret['objectType'] = self.objectType
        if not self.activity_definition is None:
            ret['definition'] = self.activity_definition.object_return(lang)
        return ret

class correctresponsespattern_answer(models.Model):
    answer = models.TextField()
    correctresponsespattern = models.ForeignKey(activity_def_correctresponsespattern)    

    def objReturn(self):
        return self.answer

class activity_definition_choice(models.Model):
    choice_id = models.CharField(max_length=200)
    description = models.ManyToManyField(LanguageMap, blank=True, null=True)
    activity_definition = models.ForeignKey(activity_definition)

    def object_return(self, lang=None):
        ret = {}
        ret['id'] = self.choice_id
        ret['description'] = {}
        
        if lang is not None:
            lang_map_set = self.description.filter(key=lang)
        else:
            lang_map_set = self.description.all()

        for lang_map in lang_map_set:
            ret['description'][lang_map.key] = lang_map.value
        
        return ret

class activity_definition_scale(models.Model):
    scale_id = models.CharField(max_length=200)
    description = models.ManyToManyField(LanguageMap, blank=True, null=True)        
    activity_definition = models.ForeignKey(activity_definition)

    def object_return(self, lang=None):
        ret = {}
        ret['id'] = self.scale_id
        ret['description'] = {}
        
        if lang is not None:
            lang_map_set = self.description.filter(key=lang)
        else:
            lang_map_set = self.description.all()

        for lang_map in lang_map_set:
            ret['description'][lang_map.key] = lang_map.value
        return ret

class activity_definition_source(models.Model):
    source_id = models.CharField(max_length=200)
    description = models.ManyToManyField(LanguageMap, blank=True, null=True)
    activity_definition = models.ForeignKey(activity_definition)
    
    def object_return(self, lang=None):
        ret = {}
        ret['id'] = self.source_id
        ret['description'] = {}
        if lang is not None:
            lang_map_set = self.description.filter(key=lang)
        else:
            lang_map_set = self.description.all()        

        for lang_map in lang_map_set:
            ret['description'][lang_map.key] = lang_map.value
        return ret

class activity_definition_target(models.Model):
    target_id = models.CharField(max_length=200)
    description = models.ManyToManyField(LanguageMap, blank=True, null=True)
    activity_definition = models.ForeignKey(activity_definition)
    
    def object_return(self, lang=None):
        ret = {}
        ret['id'] = self.target_id
        ret['description'] = {}
        if lang is not None:
            lang_map_set = self.description.filter(key=lang)
        else:
            lang_map_set = self.description.all()        

        for lang_map in lang_map_set:
            ret['description'][lang_map.key] = lang_map.value
        return ret

class activity_definition_step(models.Model):
    step_id = models.CharField(max_length=200)
    description = models.ManyToManyField(LanguageMap, blank=True, null=True)
    activity_definition = models.ForeignKey(activity_definition)

    def object_return(self, lang=None):
        ret = {}
        ret['id'] = self.step_id
        ret['description'] = {}
        if lang is not None:
            lang_map_set = self.description.filter(key=lang)
        else:
            lang_map_set = self.description.all()        

        for lang_map in lang_map_set:
            ret['description'][lang_map.key] = lang_map.value
        return ret

class activity_extensions(models.Model):
    key = models.TextField()
    value = models.TextField()
    activity_definition = models.ForeignKey(activity_definition)

    def object_return(self):
        return (self.key, self.value) 

class StatementRef(statement_object):
    object_type = models.CharField(max_length=12, default="StatementRef")
    ref_id = models.CharField(max_length=200)

    def object_return(self):
        ret = {}
        ret['objectType'] = "StatementRef"
        ret['id'] = self.ref_id
        return ret

class ContextActivity(models.Model):
    key = models.CharField(max_length=20, null=True)
    context_activity = models.CharField(max_length=200, null=True)
    
    def object_return(self):
        ret = {}
        ret[self.key] = {}
        ret[self.key]['id'] = self.context_activity
        return ret

class context(models.Model):    
    registration = models.CharField(max_length=200)
    instructor = models.ForeignKey(agent,blank=True, null=True)
    team = models.ForeignKey(group,blank=True, null=True, related_name="context_team")
    contextActivities = models.ManyToManyField(ContextActivity)
    revision = models.CharField(max_length=200,blank=True, null=True)
    platform = models.CharField(max_length=200,blank=True, null=True)
    language = models.CharField(max_length=200,blank=True, null=True)
    statement = models.OneToOneField(StatementRef, blank=True, null=True)

    def object_return(self):

        ret = {}
        linked_fields = ['instructor', 'team', 'statement', 'contextActivities']
        for field in self._meta.fields:
            if not field.name == 'id':
                value = getattr(self, field.name)
                if not value is None:
                    if not field.name in linked_fields:
                        ret[field.name] = value
                    elif field.name == 'instructor':
                        ret[field.name] = self.instructor.get_agent_json()
                    elif field.name == 'team':
                        ret[field.name] = self.team.get_agent_json()
                    elif field.name == 'statement':
                        ret[field.name] = self.statement.object_return()                    
        if self.contextActivities:
            con_act_set = self.contextActivities.all()
            ret['contextActivities'] = {}
            for con_act in con_act_set:
                ret['contextActivities'][con_act.key] = {}
                ret['contextActivities'][con_act.key]['id'] = con_act.context_activity    

        ret['extensions'] = {}
        context_ext = context_extensions.objects.filter(context=self)
        for ext in context_ext:
            ret['extensions'][ext.key] = ext.value        
        return ret

class context_extensions(models.Model):
    key=models.CharField(max_length=200)
    value=models.TextField()
    context = models.ForeignKey(context)
    
    def objReturn(self):
        return (self.key, self.value)

class activity_state(models.Model):
    state_id = models.CharField(max_length=200)
    updated = models.DateTimeField(auto_now_add=True, blank=True)
    state = models.FileField(upload_to="activity_state")
    agent = models.ForeignKey(agent)
    activity = models.ForeignKey(activity)
    registration_id = models.CharField(max_length=200)
    content_type = models.CharField(max_length=200,blank=True,null=True)
    etag = models.CharField(max_length=200,blank=True,null=True)

    def delete(self, *args, **kwargs):
        self.state.delete()
        super(activity_state, self).delete(*args, **kwargs)

class activity_profile(models.Model):
    profileId = models.CharField(max_length=200)
    updated = models.DateTimeField(auto_now_add=True, blank=True)
    activity = models.ForeignKey(activity)
    profile = models.FileField(upload_to="activity_profile")
    content_type = models.CharField(max_length=200,blank=True,null=True)
    etag = models.CharField(max_length=200,blank=True,null=True)

    def delete(self, *args, **kwargs):
        self.profile.delete()
        super(activity_profile, self).delete(*args, **kwargs)

class Verb(models.Model):
    verb_id = models.CharField(max_length=200)
    display = models.ManyToManyField(LanguageMap, null=True, blank=True)

    def object_return(self, lang=None):
        ret = {}
        ret['id'] = self.verb_id
        ret['display'] = {}
        if lang is not None:
            lang_map_set = self.display.filter(key=lang)
        else:
            lang_map_set = self.display.all()        

        for lang_map in lang_map_set:
            ret['display'][lang_map.key] = lang_map.value        
        return ret

class SubStatement(statement_object):
    stmt_object = models.ForeignKey(statement_object, related_name="object_of_substatement")
    actor = models.ForeignKey(agent,related_name="actor_of_substatement")
    verb = models.ForeignKey(Verb)    
    result = models.OneToOneField(result, blank=True,null=True)
    timestamp = models.DateTimeField(blank=True,null=True, default=datetime.utcnow().replace(tzinfo=utc).isoformat())
    context = models.OneToOneField(context, related_name="context_of_statement",blank=True, null=True)

    def object_return(self, lang=None):
        activity_object = True
        ret = {}
        ret['actor'] = self.actor.get_agent_json()
        ret['verb'] = self.verb.object_return()

        try:
            stmt_object = activity.objects.get(id=self.stmt_object.id)
        except activity.DoesNotExist:
            try:
                stmt_object = agent.objects.get(id=self.stmt_object.id)
                activity_object = False
            except agent.DoesNotExist:
                raise IDNotFoundError('No activity or agent object found with given ID')

        if activity_object:
            ret['object'] = stmt_object.object_return(lang)  
        else:
            ret['object'] = stmt_object.get_agent_json()

        ret['result'] = self.result.object_return()
        ret['context'] = self.context.object_return()
        ret['timestamp'] = str(self.timestamp)
        ret['objectType'] = "SubStatement"
        return ret

class statement(statement_object):
    statement_id = models.CharField(max_length=200)
    stmt_object = models.ForeignKey(statement_object, related_name="object_of_statement")
    actor = models.ForeignKey(agent,related_name="actor_statement")
    verb = models.ForeignKey(Verb)    
    result = models.OneToOneField(result, blank=True,null=True)
    stored = models.DateTimeField(auto_now_add=True,blank=True)
    timestamp = models.DateTimeField(blank=True,null=True, default=lambda: datetime.utcnow().replace(tzinfo=utc).isoformat())    
    authority = models.ForeignKey(agent, blank=True,null=True,related_name="authority_statement")
    voided = models.NullBooleanField(blank=True, null=True)
    context = models.OneToOneField(context, related_name="context_statement",blank=True, null=True)
    authoritative = models.BooleanField(default=True)

    def object_return(self, lang=None):
        object_type = 'activity'
        ret = {}
        ret['id'] = self.statement_id
        ret['actor'] = self.actor.get_agent_json()
        ret['verb'] = self.verb.object_return(lang)

        try:
            stmt_object = activity.objects.get(id=self.stmt_object.id)
        except activity.DoesNotExist:
            try:
                stmt_object = agent.objects.get(id=self.stmt_object.id)
                object_type = 'agent'
            except agent.DoesNotExist:
                try:
                    stmt_object = SubStatement.objects.get(id=self.stmt_object.id)
                    object_type = 'substatement'            
                except SubStatement.DoesNotExist:
                    raise IDNotFoundError("No activity, agent, or substatement found with given ID")

        if object_type == 'activity' or object_type == 'substatement':
            ret['object'] = stmt_object.object_return(lang)  
        else:
            ret['object'] = stmt_object.get_agent_json()
        if not self.result is None:
            ret['result'] = self.result.object_return()        
        if not self.context is None:
            ret['context'] = self.context.object_return()
        
        ret['timestamp'] = str(self.timestamp)
        ret['stored'] = str(self.stored)
        
        if not self.authority is None:
            ret['authority'] = self.authority.get_agent_json()
        
        ret['voided'] = self.voided
        return ret

    def save(self, *args, **kwargs):
        # actor object context authority
        statement.objects.filter(actor=self.actor, stmt_object=self.stmt_object, context=self.context, authority=self.authority).update(authoritative=False)
        super(statement, self).save(*args, **kwargs)


# - from http://djangosnippets.org/snippets/2283/
# @transaction.commit_on_success
def merge_model_objects(primary_object, alias_objects=[], save=True, keep_old=False):
    """
    Use this function to merge model objects (i.e. Users, Organizations, Polls,
    etc.) and migrate all of the related fields from the alias objects to the
    primary object.
    
    Usage:
    from django.contrib.auth.models import User
    primary_user = User.objects.get(email='good_email@example.com')
    duplicate_user = User.objects.get(email='good_email+duplicate@example.com')
    merge_model_objects(primary_user, duplicate_user)
    """
    if not isinstance(alias_objects, list):
        alias_objects = [alias_objects]
    
    # check that all aliases are the same class as primary one and that
    # they are subclass of model
    primary_class = primary_object.__class__
    
    if not issubclass(primary_class, models.Model):
        raise TypeError('Only django.db.models.Model subclasses can be merged')
    
    for alias_object in alias_objects:
        if not isinstance(alias_object, primary_class):
            raise TypeError('Only models of same class can be merged')
    
    # Get a list of all GenericForeignKeys in all models
    # TODO: this is a bit of a hack, since the generics framework should provide a similar
    # method to the ForeignKey field for accessing the generic related fields.
    generic_fields = []
    for model in models.get_models():
        for field_name, field in filter(lambda x: isinstance(x[1], GenericForeignKey), model.__dict__.iteritems()):
            generic_fields.append(field)
            
    blank_local_fields = set([field.attname for field in primary_object._meta.local_fields if getattr(primary_object, field.attname) in [None, '']])
    
    # Loop through all alias objects and migrate their data to the primary object.
    for alias_object in alias_objects:
        # Migrate all foreign key references from alias object to primary object.
        for related_object in alias_object._meta.get_all_related_objects():
            # The variable name on the alias_object model.
            alias_varname = related_object.get_accessor_name()
            # The variable name on the related model.
            obj_varname = related_object.field.name
            try:
                related_objects = getattr(alias_object, alias_varname)
                for obj in related_objects.all():
                    primary_objects = getattr(primary_object, alias_varname)
                    found = [hit for hit in primary_objects.all() if hit.equals(obj)]
                    if not found:
                        setattr(obj, obj_varname, primary_object)
                        obj.save()
            except Exception as e:
                pass # didn't have any of that related object

        # Migrate all many to many references from alias object to primary object.
        for related_many_object in alias_object._meta.get_all_related_many_to_many_objects():
            alias_varname = related_many_object.get_accessor_name()
            obj_varname = related_many_object.field.name
            
            if alias_varname is not None:
                # standard case
                related_many_objects = getattr(alias_object, alias_varname).all()
            else:
                # special case, symmetrical relation, no reverse accessor
                related_many_objects = getattr(alias_object, obj_varname).all()
            for obj in related_many_objects.all():
                getattr(obj, obj_varname).remove(alias_object)
                getattr(obj, obj_varname).add(primary_object)

        # Migrate all generic foreign key references from alias object to primary object.
        for field in generic_fields:
            filter_kwargs = {}
            filter_kwargs[field.fk_field] = alias_object._get_pk_val()
            filter_kwargs[field.ct_field] = field.get_content_type(alias_object)
            for generic_related_object in field.model.objects.filter(**filter_kwargs):
                setattr(generic_related_object, field.name, primary_object)
                generic_related_object.save()
                
        # Try to fill all missing values in primary object by values of duplicates
        filled_up = set()
        for field_name in blank_local_fields:
            val = getattr(alias_object, field_name) 
            if val not in [None, '']:
                setattr(primary_object, field_name, val)
                filled_up.add(field_name)
        blank_local_fields -= filled_up
            
        if not keep_old:
            alias_object.delete()
    if save:
        primary_object.save()
    return primary_object