from django.db import models
from django.db import transaction
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes import generic
from django.contrib.contenttypes.generic import GenericForeignKey
import pdb

ADL_LRS_STRING_KEY = 'ADL_LRS_STRING_KEY'

ourModels = ['agent','result','person','context','activity_definition','activity_def_correctresponsespattern']
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

class result(models.Model): 
    success = models.NullBooleanField(blank=True,null=True)
    completion = models.CharField(max_length=200, blank=True, null=True)
    response = models.CharField(max_length=200, blank=True, null=True)
    #Made charfield since it would be stored in ISO8601 duration format
    duration = models.CharField(max_length=200, blank=True, null=True)
    score = models.OneToOneField(score, blank=True, null=True)

class result_extensions(models.Model):
    key=models.CharField(max_length=200)
    value=models.CharField(max_length=200)
    result = models.ForeignKey(result)


class statement_object(models.Model):
    pass

class agent(statement_object):  
    objectType = models.CharField(max_length=200)
    
    def __unicode__(self):
        return ': '.join([str(self.id), self.objectType])

    def get_agent_names():
        return agent_name.objects.filter(agent=self)

class agent_name(models.Model):
    name = models.CharField(max_length=200)
    date_added = models.DateTimeField(auto_now_add=True, blank=True)
    agent = models.ForeignKey(agent)

    def equals(self, other):
        if not isinstance(other, self.__class__):
            raise TypeError('Only models of same class can be compared')
        return self.name == other.name

class agent_mbox(models.Model):
    mbox = models.CharField(max_length=200)
    date_added = models.DateTimeField(auto_now_add=True, blank=True)
    agent = models.ForeignKey(agent)

    def equals(self, other):
        if not isinstance(other, self.__class__):
            raise TypeError('Only models of same class can be compared')
        return self.mbox == other.mbox

class agent_mbox_sha1sum(models.Model):
    mbox_sha1sum = models.CharField(max_length=200)
    date_added = models.DateTimeField(auto_now_add=True, blank=True)
    agent = models.ForeignKey(agent)

    def equals(self, other):
        if not isinstance(other, self.__class__):
            raise TypeError('Only models of same class can be compared')
        return self.mbox_sha1sum == other.mbox_sha1sum        

class agent_openid(models.Model):
    openid = models.CharField(max_length=200)
    date_added = models.DateTimeField(auto_now_add=True, blank=True)
    agent = models.ForeignKey(agent)

    def equals(self, other):
        if not isinstance(other, self.__class__):
            raise TypeError('Only models of same class can be compared')
        return self.openid == other.openid        

class agent_account(models.Model):  
    accountServiceHomePage = models.CharField(max_length=200, blank=True, null=True)
    accountName = models.CharField(max_length=200)
    date_added = models.DateTimeField(auto_now_add=True, blank=True)
    agent = models.ForeignKey(agent)

    def equals(self, other):
        if not isinstance(other, self.__class__):
            raise TypeError('Only models of same class can be compared')
        return self.accountName == other.accountName and self.accountServiceHomePage == other.accountServiceHomePage  

class person(agent):    
    pass

class person_givenName(models.Model):
    givenName = models.CharField(max_length=200)
    date_added = models.DateTimeField(auto_now_add=True, blank=True)
    person = models.ForeignKey(person)

    def equals(self, other):
        if not isinstance(other, self.__class__):
            raise TypeError('Only models of same class can be compared')
        return self.givenName == other.givenName  

class person_familyName(models.Model):
    familyName = models.CharField(max_length=200)
    date_added = models.DateTimeField(auto_now_add=True, blank=True)
    person = models.ForeignKey(person)

    def equals(self, other):
        if not isinstance(other, self.__class__):
            raise TypeError('Only models of same class can be compared')
        return self.familyName == other.familyName  

class person_firstName(models.Model):
    firstName = models.CharField(max_length=200)
    date_added = models.DateTimeField(auto_now_add=True, blank=True)
    person = models.ForeignKey(person)

    def equals(self, other):
        if not isinstance(other, self.__class__):
            raise TypeError('Only models of same class can be compared')
        return self.firstName == other.firstName
    
class person_lastName(models.Model):
    lastName = models.CharField(max_length=200)
    date_added = models.DateTimeField(auto_now_add=True, blank=True)
    person = models.ForeignKey(person)

    def equals(self, other):
        if not isinstance(other, self.__class__):
            raise TypeError('Only models of same class can be compared')
        return self.lastName == other.lastName

class group(agent):
    member = models.TextField()

class actor_profile(models.Model):
    profileId = models.CharField(max_length=200)
    updated = models.DateTimeField(auto_now_add=True, blank=True)
    actor = models.ForeignKey(agent)
    profile = models.FileField(upload_to="actor_profile")
    content_type = models.CharField(max_length=200,blank=True,null=True)
    etag = models.CharField(max_length=200,blank=True,null=True)

    def delete(self, *args, **kwargs):
        self.profile.delete()
        super(actor_profile, self).delete(*args, **kwargs)

class LanguageMap(models.Model):
    key = models.CharField(max_length=200)
    value = models.CharField(max_length=200)

class activity_def_correctresponsespattern(models.Model):
    pass

class activity_definition(models.Model):
    name = models.ManyToManyField(LanguageMap, related_name="activity_definition_name", blank=True, null=True)
    description = models.ManyToManyField(LanguageMap, related_name="activity_definition_description", blank=True, null=True)
    activity_definition_type = models.CharField(max_length=200, blank=True, null=True)
    interactionType = models.CharField(max_length=200, blank=True, null=True)
    correctresponsespattern = models.OneToOneField(activity_def_correctresponsespattern, blank=True, null=True)


class activity(statement_object):
    activity_id = models.CharField(max_length=200)
    objectType = models.CharField(max_length=200,blank=True, null=True) 
    activity_definition = models.OneToOneField(activity_definition, blank=True, null=True)
    authoritative = models.CharField(max_length=200, blank=True, null=True)

class correctresponsespattern_answer(models.Model):
    answer = models.TextField()
    correctresponsespattern = models.ForeignKey(activity_def_correctresponsespattern)    

    def objReturn(self):
        return self.answer

class activity_definition_choice(models.Model):
    choice_id = models.CharField(max_length=200)
    description = models.ManyToManyField(LanguageMap, blank=True, null=True)        
    activity_definition = models.ForeignKey(activity_definition)

    def objReturn(self, lang):
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

    def objReturn(self, lang):
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
    
    def objReturn(self, lang):
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
    
    def objReturn(self, lang):
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

    def objReturn(self, lang):
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


class context(models.Model):    
    registration = models.CharField(max_length=200)
    instructor = models.ForeignKey(agent,blank=True, null=True)
    team = models.ForeignKey(group,blank=True, null=True, related_name="context_team")
    contextActivities = models.TextField()
    revision = models.CharField(max_length=200,blank=True, null=True)
    platform = models.CharField(max_length=200,blank=True, null=True)
    language = models.CharField(max_length=200,blank=True, null=True)
    statement = models.BigIntegerField(blank=True, null=True)

class context_extensions(models.Model):
    key=models.CharField(max_length=200)
    value=models.CharField(max_length=200)
    context = models.ForeignKey(context)

class activity_state(models.Model):
    state_id = models.CharField(max_length=200)
    updated = models.DateTimeField(auto_now_add=True, blank=True)
    state = models.FileField(upload_to="activity_state")
    actor = models.ForeignKey(agent)
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

class statement(statement_object):
    statement_id = models.CharField(max_length=200)
    stmt_object = models.ForeignKey(statement_object, related_name="object_of_statement")
    actor = models.ForeignKey(agent,related_name="actor_statement", blank=True, null=True)
    verb = models.CharField(max_length=200)
    inProgress = models.NullBooleanField(blank=True, null=True)    
    result = models.OneToOneField(result, blank=True,null=True)
    timestamp = models.DateTimeField(blank=True,null=True)
    stored = models.DateTimeField(auto_now_add=True,blank=True)
    authority = models.ForeignKey(agent, blank=True,null=True,related_name="authority_statement")
    voided = models.NullBooleanField(blank=True, null=True)
    context = models.OneToOneField(context, related_name="context_statement",blank=True, null=True)
    authoritative = models.BooleanField(default=True)


    def save(self, *args, **kwargs):
        # actor object context authority
        statement.objects.filter(actor=self.actor, stmt_object=self.stmt_object, context=self.context, authority=self.authority).update(authoritative=False)
        super(statement, self).save(*args, **kwargs)

def convert_stmt_object_field_name(return_dict):
    if 'stmt_object' in return_dict:
        return_dict['object'] = return_dict['stmt_object']
        del return_dict['stmt_object']
    return return_dict    

def convert_activity_definition_field_name(return_dict):
    if 'activity_definition' in return_dict:
        return_dict['definition'] = return_dict['activity_definition']
        del return_dict['activity_definition']

    if 'activity_definition_type' in return_dict:
        return_dict['type'] = return_dict['activity_definition_type']
        del return_dict['activity_definition_type']
    return return_dict


def objsReturn(obj, language=None):
    ret = {}

    # If the object being sent in is derived from a statement_object, must retrieve the specific object then loop through all of it's fields
    if type(obj).__name__ == 'statement_object':
        try:
            obj = activity.objects.get(id=obj.id)
        except Exception, e:
            try:
                obj = agent.objects.get(id=obj.id)
            except Exception, e:
                try:
                    obj = statement.objects.get(id=obj.id)
                except Exception, e:
                    raise e
    # Else if the object is a LanguageMap we have to handle this different since we actually want the
    # key value as the key in the dict we're returning
    elif type(obj).__name__ == 'LanguageMap':
        ret = handle_lang_map(obj)
        return ret
    # Have to handle the name and desc fields since they are manytomany and don't appear in _meta.fields
    elif type(obj).__name__ == 'activity_definition':

        if language is not None:
            name_lang_map_set = obj.name.filter(key=language)
            desc_lang_map_set = obj.name.filter(key=language)
        else:
            name_lang_map_set = obj.name.all()
            desc_lang_map_set = obj.description.all()
        
        ret['name'] = {}
        ret['description'] = {}
        for lang_map in name_lang_map_set:
            ret['name'][lang_map.key] = lang_map.value
                    
        for lang_map in desc_lang_map_set:
            ret['description'][lang_map.key] = lang_map.value        

    # Once we retrieve the specific object if needed, loop through all fields in model
    for field in obj._meta.fields:
        # Get the value of the field and the type of the field
        fieldValue = getattr(obj, field.name)
        fieldType = type(fieldValue).__name__.lower()
        
        # Set fieldType and fieldValue when receiving statement_object that is a FK
        if fieldType == 'statement_object':
            try:
                fieldValue = activity.objects.get(id=fieldValue.id)
                fieldType = 'activity'
            except Exception, e:
                try:
                    fieldValue = agent.objects.get(id=fieldValue.id)
                    fieldType = 'agent'
                except Exception, e:
                    try:
                        fieldValue = statement.objects.get(id=fieldValue.id)
                        fieldType = 'statement'
                    except Exception, e:
                        raise e

        # If type of field is agent, need to retrieve all FKs associated with it
        if fieldType == 'agent':
            # Check to see if the agent is of type Person
            if fieldValue.objectType == 'Person':
                ret[field.name] = {}
                # Get all names associated with object
                names = agent_name.objects.filter(agent=fieldValue).values_list('name', flat=True)
                if names:
                    ret[field.name]['name'] = [k for k in names]
                # Get all mboxes associated with object
                mboxes = agent_mbox.objects.filter(agent=fieldValue).values_list('mbox', flat=True)
                if mboxes:
                    ret[field.name]['mbox'] = [k for k in mboxes]
                # Get all givenNames associated with object
                givenNames = person_givenName.objects.filter(person=fieldValue).values_list('givenName', flat=True)
                if givenNames:
                    ret[field.name]['givenName'] = [k for k in givenNames]
                # Get all familyNames associated with object
                familyNames = person_familyName.objects.filter(person=fieldValue).values_list('familyName', flat=True)
                if familyNames:
                    ret[field.name]['familyName'] = [k for k in familyNames]
                # Get all firstNames associated with object
                firstNames = person_firstName.objects.filter(person=fieldValue).values_list('firstName', flat=True)
                if firstNames:
                    ret[field.name]['firstName'] = [k for k in firstNames]
                # Get all lastNames associated with object
                lastNames = person_lastName.objects.filter(person=fieldValue).values_list('lastName', flat=True)
                if lastNames:
                    ret[field.name]['lastName'] = [k for k in lastNames]
            # If agent isn't person
            else:
                ret[field.name] = {}
                # Get all names associated with object
                names = agent_name.objects.filter(agent=fieldValue).values_list('name', flat=True)
                if names:
                    ret[field.name]['name'] = [k for k in names]
                # Get all mboxes associated with object
                mboxes = agent_mbox.objects.filter(agent=fieldValue).values_list('mbox', flat=True)
                if mboxes:
                    ret[field.name]['mbox'] = [k for k in mboxes]
                # Get all open ids associated with object
                openids = agent_openid.objects.filter(agent=fieldValue).values_list('openid', flat=True)
                if openids:
                    ret[field.name]['openid'] = [k for k in openids]
                # Get all accounts associated with object
                accounts = agent_account.objects.filter(agent=fieldValue).values_list('accountName', flat=True)
                if accounts:
                    ret[field.name]['account'] = [k for k in accounts]
                
        # If type of field is result
        elif fieldType == 'result':
            # Call recursively, send in result object
            ret[field.name] = objsReturn(getattr(obj, field.name), language)
            # Once done with result object, get result extensions
            ret[field.name]['extensions'] = {}
            resultExt = result_extensions.objects.filter(result=fieldValue)
            for ext in resultExt:
                ret[field.name]['extensions'][ext.key] = ext.value                
        
        # If type of field is context
        elif fieldType == 'context':
            # Call recursively, send in context object
            ret[field.name] = objsReturn(getattr(obj, field.name), language)
            # Once done with context object, get context extensions
            ret[field.name]['extensions'] = {}
            contextExt = context_extensions.objects.filter(context=fieldValue)
            for ext in contextExt:
                ret[field.name]['extensions'][ext.key] = ext.value
        
        # If type of field is activity_definition, need to grab all FKs associated with object
        elif fieldType == 'activity_definition':
            # Call recursively, send in act_def object
            ret[field.name] = objsReturn(getattr(obj, field.name), language)
            # Get scales
            scales = activity_definition_scale.objects.filter(activity_definition=fieldValue)
            if scales:
                ret[field.name]['scale'] = []
                for s in scales:
                    ret[field.name]['scale'].append(s.objReturn(language))
            # Get choices
            choices = activity_definition_choice.objects.filter(activity_definition=fieldValue)
            if choices:
                ret[field.name]['choices'] = []
                for c in choices:
                    ret[field.name]['choices'].append(c.objReturn(language))
            # Get steps
            steps = activity_definition_step.objects.filter(activity_definition=fieldValue)
            if steps:
                ret[field.name]['steps'] = []
                for st in steps:
                    ret[field.name]['steps'].append(st.objReturn(language))
            # Get sources
            sources = activity_definition_source.objects.filter(activity_definition=fieldValue)
            if sources:
                ret[field.name]['source'] = []
                for so in sources:
                    ret[field.name]['source'].append(so.objReturn(language))
            # Get targets
            targets = activity_definition_target.objects.filter(activity_definition=fieldValue)
            if targets:
                ret[field.name]['target'] = []
                for t in targets:
                    ret[field.name]['target'].append(t.objReturn(language))
            
            ret[field.name]['extensions'] = {}
            act_def_ext = activity_extensions.objects.filter(activity_definition=fieldValue)
            for ext in act_def_ext:
                ret[field.name]['extensions'][ext.key] = ext.value
        # If type of field is activity_def_crp, grab all FKs associated with it
        elif fieldType == 'activity_def_correctresponsespattern':
            ret[field.name] = []
            # Get answers
            answers = correctresponsespattern_answer.objects.filter(correctresponsespattern=fieldValue)
            for a in answers:
                ret[field.name].append(a.objReturn())
        
        # Else if not any specified LRS object above
        else:
            # If it is a OneToOneField, skip _ptr name and if it has a value recursively send object
            if field.get_internal_type() == 'OneToOneField':
                # Don't care about inheritance field
                if not field.name.endswith('_ptr'):
                    if getattr(obj, field.name):
                        ret[field.name] = objsReturn(getattr(obj, field.name), language)
            # If ForeignKey and if it has a value recursively send object
            elif field.get_internal_type() == 'ForeignKey':
                # If the object being sent in is derived from a statement_object, must retrieve the specific object
                if fieldType == 'statement_object':
                    try:
                        obj = activity.objects.get(id=obj.id)
                    except Exception, e:
                        try:
                            obj = agent.objects.get(id=obj.id)
                        except Exception, e:
                            try:
                                obj = statement.objects.get(id=obj.id)
                            except Exception, e:
                                raise e

                if getattr(obj, field.name):
                    ret[field.name] = objsReturn(getattr(obj, field.name), language)

            # Return DateTime as string
            elif field.get_internal_type() == 'DateTimeField':
                if getattr(obj, field.name):
                    ret[field.name] = str(getattr(obj, field.name))
            # If it's any type of other field(int string, bool)
            else:
                # Don't care about internal ID or the authoritative field in statement objects
                if not field.name == 'id' and not field.name == 'authoritative':
                    # If there is a value set it in return dict
                    if not getattr(obj, field.name) is None:
                        # If statement_id field in statement object-rename to id in return dict
                        if field.name == 'statement_id' or field.name == 'activity_id':
                            ret['id'] = getattr(obj, field.name)
                        else:
                            ret[field.name] = getattr(obj, field.name)
    
    convert_stmt_object_field_name(ret)
    convert_activity_definition_field_name(ret)
    return ret

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