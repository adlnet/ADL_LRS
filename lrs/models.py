from django.db import models
from django.db import transaction
from django.contrib.contenttypes.generic import GenericForeignKey
from django.core import serializers
import json
#this is BAD, if anyone knows a better way to store kv pairs in MySQL let me know

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

class activity_def_correctresponsespattern(models.Model):
    #activity_definition = models.OneToOneField(activity_definition, blank=True,null=True)
    pass

class activity_definition(models.Model):
    name = models.CharField(max_length=200)
    description = models.CharField(max_length=200)
    activity_definition_type = models.CharField(max_length=200)
    interactionType = models.CharField(max_length=200)
    correctresponsespattern = models.OneToOneField(activity_def_correctresponsespattern, blank=True, null=True)
    #activity = models.OneToOneField(activity)

    def objReturn(self):
        ret = {}
        ret['name'] = self.name
        ret['description'] = self.description
        ret['type'] = self.activity_definition_type
        ret['interactionType'] = self.interactionType
        return ret

class activity(statement_object):
    activity_id = models.CharField(max_length=200)
    objectType = models.CharField(max_length=200,blank=True, null=True) 
    activity_definition = models.OneToOneField(activity_definition, blank=True, null=True)

    def objReturn(self):
        ret = {}
        ret['activity_id'] = self.activity_id
        ret['objectType'] = self.objectType
        return ret

class correctresponsespattern_answer(models.Model):
    answer = models.TextField()
    correctresponsespattern = models.ForeignKey(activity_def_correctresponsespattern)    

    def objReturn(self):
        return self.answer

class activity_definition_choice(models.Model):
    choice_id = models.CharField(max_length=200)
    description = models.TextField()        
    activity_definition = models.ForeignKey(activity_definition)

    def objReturn(self):
        ret = {}
        ret['id'] = self.choice_id
        ret['description'] = self.description
        return ret

class activity_definition_scale(models.Model):
    scale_id = models.CharField(max_length=200)
    description = models.TextField()        
    activity_definition = models.ForeignKey(activity_definition)

    def objReturn(self):
        ret = {}
        ret['id'] = self.scale_id
        ret['description'] = self.description
        return ret

class activity_definition_source(models.Model):
    source_id = models.CharField(max_length=200)
    description = models.CharField(max_length=200)        
    activity_definition = models.ForeignKey(activity_definition)
    
    def objReturn(self):
        ret = {}
        ret['id'] = self.source_id
        ret['description'] = self.description
        return ret

class activity_definition_target(models.Model):
    target_id = models.CharField(max_length=200)
    description = models.CharField(max_length=200)        
    activity_definition = models.ForeignKey(activity_definition)
    
    def objReturn(self):
        ret = {}
        ret['id'] = self.target_id
        ret['description'] = self.description
        return ret

class activity_definition_step(models.Model):
    step_id = models.CharField(max_length=200)
    description = models.CharField(max_length=200)        
    activity_definition = models.ForeignKey(activity_definition)

    def objReturn(self):
        ret = {}
        ret['id'] = self.step_id
        ret['description'] = self.description
        return ret

class activity_extensions(models.Model):
    key = models.TextField()
    value = models.TextField()
    activity_definition = models.ForeignKey(activity_definition)

    def objReturn(self):
        return (self.key, self.value) 

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

class statement(statement_object):
    #TODO: can't get django extensions UUIDField to generate UUID
    #statement_id = UUIDField(version=4)  
    statement_id = models.CharField(max_length=200)
    actor = models.ForeignKey(agent,related_name="actor_statement", blank=True, null=True)
    verb = models.CharField(max_length=200)
    inProgress = models.NullBooleanField(blank=True, null=True)    
    result = models.OneToOneField(result, blank=True,null=True)
    timestamp = models.DateTimeField(blank=True,null=True)
    stored = models.DateTimeField(auto_now_add=True,blank=True)
    # stored = models.DateTimeField(editable=False,blank=True) 
    authority = models.ForeignKey(agent, blank=True,null=True,related_name="authority_statement")
    voided = models.NullBooleanField(blank=True, null=True)
    context = models.OneToOneField(context, related_name="context_statement",blank=True, null=True)
    # stmt_object = models.OneToOneField(statement_object)
    stmt_object = models.ForeignKey(statement_object, related_name="object_of_statement")


def objsReturn(obj):
    ret = {}

    # If the object being sent in is derived from a statement_object, must retrieve the specific object
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

    # Loop through all fields in model
    for field in obj._meta.fields:
        fieldValue = getattr(obj, field.name)
        objType = type(fieldValue).__name__

        if objType == 'agent' or objType == 'person':
            ret[field.name] = {}
            names = agent_name.objects.filter(agent=fieldValue).values_list('name', flat=True)
            if names:
                ret[field.name]['name'] = [k for k in names]
            
            mboxes = agent_mbox.objects.filter(agent=fieldValue).values_list('mbox', flat=True)
            if mboxes:
                ret[field.name]['mbox'] = [k for k in mboxes]

        elif objType == 'result':
            ret[field.name] = objsReturn(getattr(obj, field.name))
            ret[field.name]['extensions'] = {}
            resultExt = result_extensions.objects.filter(result=fieldValue)
            for ext in resultExt:
                ret[field.name]['extensions'][ext.key] = ext.value                

        elif objType == 'context':
            ret[field.name] = objsReturn(getattr(obj, field.name))
            ret[field.name]['extensions'] = {}
            contextExt = context_extensions.objects.filter(context=fieldValue)
            for ext in contextExt:
                ret[field.name]['extensions'][ext.key] = ext.value

        elif objType == 'activity_definition':
            ret[field.name] = objsReturn(getattr(obj, field.name))

            scales = activity_definition_scale.objects.filter(activity_definition=fieldValue)
            if scales:
                ret[field.name]['scale'] = []
                for s in scales:
                    ret[field.name]['scale'].append(s.objReturn())

            choices = activity_definition_choice.objects.filter(activity_definition=fieldValue)
            if choices:
                ret[field.name]['choices'] = []
                for c in choices:
                    ret[field.name]['choices'].append(c.objReturn())

            steps = activity_definition_step.objects.filter(activity_definition=fieldValue)
            if steps:
                ret[field.name]['steps'] = []
                for st in steps:
                    ret[field.name]['steps'].append(st.objReturn())

            sources = activity_definition_source.objects.filter(activity_definition=fieldValue)
            if sources:
                ret[field.name]['source'] = []
                for so in sources:
                    ret[field.name]['source'].append(so.objReturn())

            targets = activity_definition_target.objects.filter(activity_definition=fieldValue)
            if targets:
                ret[field.name]['target'] = []
                for t in targets:
                    ret[field.name]['target'].append(str(t.objReturn()))

        elif objType == 'activity_def_correctresponsespattern':
            ret[field.name] = []
            answers = correctresponsespattern_answer.objects.filter(correctresponsespattern=fieldValue)
            for a in answers:
                ret[field.name].append(a.objReturn())

        else:
            if field.get_internal_type() == 'OneToOneField':
                # Don't care about inheritance field
                if not field.name.endswith('_ptr'):
                    if getattr(obj, field.name):
                        ret[field.name] = objsReturn(getattr(obj, field.name))
            
            elif field.get_internal_type() == 'ForeignKey':
                if getattr(obj, field.name):
                    ret[field.name] = objsReturn(getattr(obj, field.name))

            # Return DateTime as string
            elif field.get_internal_type() == 'DateTimeField':
                if getattr(obj, field.name):
                    ret[field.name] = str(getattr(obj, field.name))
            else:
                # Don't care about internal ID
                if not field.name == 'id':
                    # Set value in dict
                    if not getattr(obj, field.name) is None:
                        ret[field.name] = getattr(obj, field.name)

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