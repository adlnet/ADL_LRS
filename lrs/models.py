from django.db import models
from uuidfield import UUIDField
from django.db import transaction
from django.contrib.contenttypes.generic import GenericForeignKey

#this is BAD, if anyone knows a better way to store kv pairs in MySQL let me know

#needs object
ADL_LRS_STRING_KEY = 'ADL_LRS_STRING_KEY'

import time
def filename(instance, filename):
    print filename
    return filename

class score(models.Model):  
    scaled = models.NullBooleanField(blank=True)
    raw = models.PositiveIntegerField(blank=True, null=True)
    score_min = models.PositiveIntegerField(blank=True, null=True)
    score_max = models.PositiveIntegerField(blank=True, null=True)

class result(models.Model): 
    success = models.CharField(max_length=200, blank=True,null=True)
    completion = models.NullBooleanField(blank=True)
    response = models.CharField(max_length=200, blank=True, null=True)
    duration = models.DateTimeField(blank=True, null=True)
    score = models.OneToOneField(score, blank=True, null=True)

class result_extensions(models.Model):
    key=models.CharField(max_length=200)
    value=models.CharField(max_length=200)
    result = models.ForeignKey(result)

class state(models.Model):
    key = models.PositiveIntegerField(primary_key=True)
    state_id = models.CharField(max_length=200)
    updated = models.DateTimeField(auto_now_add=True, blank=True)
    contents = models.CharField(max_length=200)

class statement_object(models.Model):
    pass

class agent(statement_object):  
    objectType = models.CharField(max_length=200)
    
    def __unicode__(self):
        return ': '.join([str(self.id), self.objectType])

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
    profileId = UUIDField(auto=True)
    stored = models.DateTimeField(auto_now_add=True, blank=True)
    actor = models.ForeignKey(agent)
    profile = models.FileField(upload_to="actor_profile")
    content_type = models.CharField(max_length=200,blank=True,null=True)
    etag = models.CharField(max_length=200,blank=True,null=True)

class activity(statement_object):
    activity_id = models.CharField(max_length=200)
    objectType = models.CharField(max_length=200,blank=True, null=True) 

class activity_definition(models.Model):
    name = models.CharField(max_length=200)
    description = models.CharField(max_length=200)
    activity_definition_type = models.CharField(max_length=200)
    interactionType = models.CharField(max_length=200)
    activity = models.OneToOneField(activity)

class activity_extentions(models.Model):
    key = models.CharField(max_length=200)
    value = models.CharField(max_length=200)
    activity_definition = models.ForeignKey(activity_definition)

class context(models.Model):    
    registration = UUIDField()
    instructor = models.OneToOneField(agent,blank=True, null=True)
    team = models.CharField(max_length=200,blank=True, null=True)
    contextActivities = models.CharField(max_length=200)
    revision = models.CharField(max_length=200,blank=True, null=True)
    platform = models.CharField(max_length=200,blank=True, null=True)
    language = models.CharField(max_length=200,blank=True, null=True)
    statement = models.CharField(max_length=200,blank=True, null=True)

class context_extentions(models.Model):
    key=models.CharField(max_length=200)
    value=models.CharField(max_length=200)
    context = models.ForeignKey(context)

class statement(statement_object):
    statement_id = UUIDField(primary_key=True)  
    actor = models.OneToOneField(agent,related_name="actor_statement", blank=True, null=True)
    verb = models.CharField(max_length=200)
    inProgress = models.NullBooleanField(blank=True)    
    result = models.OneToOneField(result, blank=True,null=True)
    timestamp = models.DateTimeField(blank=True,null=True)
    stored = models.DateTimeField(auto_now_add=True,blank=True) 
    authority = models.OneToOneField(agent, blank=True,null=True,related_name="authority_statement")
    voided = models.NullBooleanField(blank=True)
    context = models.OneToOneField(context, related_name="context_statement",blank=True, null=True)
    stmt_object = models.OneToOneField(statement_object)

# - from http://djangosnippets.org/snippets/2283/
@transaction.commit_on_success
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