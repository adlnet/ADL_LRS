from django.db import models
from uuidfield import UUIDField
#this is BAD, if anyone knows a better way to store kv pairs in MySQL let me know


class statement(models.Model):
	id = UUIDField(primary_key=True)	
	verb = models.CharField(max_length=200)
	inProgress = models.BooleanField()	
	result = models.ForeignKey(result)
	timestamp = models.DateTimeField()
	stored = models.DateTimeField()	
	voided = models.BooleanField()

class statement_actor(models.Model):
	id = models.PositiveIntegerField(primary_key=True)
	stmt = models.ForeignKey(statement)

class statement_object(models.Model):
	# Fill in

class statement_authority(models.Model):
	# Fill in

#Completion should be charfield since may be not specified, score should be score object, extensions should be ext obj
class result(models.Model):
	id = models.PositiveIntegerField(primary_key=True)	
	score = models.PositiveIntegerField()
	success = models.CharField(max_length=200)
	completion = models.BooleanField()
	duration = models.DateTimeField()
	extensions = models.CharField(max_length=200)

class result_extension(models.Model):
	id = models.PositiveIntegerField(primary_key=True)
	key=models.CharField(max_length=200)
	value=models.CharField(max_length=200)
	result = models.ForeignKey(result)

# Need instructor (should be actor?), contextActivities should be map,Platform is TBD depending if a statement's object is a person
class context(models.Model):
	id = models.PositiveIntegerField(primary_key=True)
	registration = UUIDField()
	team = models.CharField(max_length=200)
	contextActivities = models.CharField(max_length=200)
	revision = models.CharField(max_length=200)
	platform = models.CharField(max_length=200)
	language = models.CharField(max_length=200)
	statement = models.CharField(max_length=200)

class context_actor(models.Model):
	id = models.PositiveIntegerField(primary_key=True)
	ctx = models.ForeignKey(context)

class context_extentions(models.Model):
	id = models.PositiveIntegerField(primary_key=True)
	key=models.CharField(max_length=200)
	value=models.CharField(max_length=200)
	context = models.ForeignKey(context)

#fields are all part of cmi, needs changed?
class score(models.Model):
	id = models.PositiveIntegerField(primary_key=True)
	scaled = models.BooleanField()
	raw = models.PositiveIntegerField()
	min = models.PositiveIntegerField()
	max = models.PositiveIntegerField()

class state(models.Model):
	key = models.PositiveIntegerField(primary_key=True)
	id = models.CharField(max_length=200)
	updated = models.DateTimeField()
	contents = models.CharField(max_length=200)



	
# Needs name, mbox, mbox_sha1sum, openid, account (all arrays)
class agent(models.Model):
	id = models.PositiveIntegerField(primary_key=True)
	objectType = models.CharField(max_length=200)


class agent_name(models.Model):
	id = models.PositiveIntegerField(primary_key=True)
	name = models.CharField(max_length=200)
	agent = models.ForeignKey(agent)

class agent_mbox(models.Model):
	id = models.PositiveIntegerField(primary_key=True)	
	email = models.EmailField()
	agent = models.ForeignKey(agent)

# What to do for sha1?
class agent_sha1(models.Model):
	id = models.PositiveIntegerField(primary_key=True)
	sha1 = models.CharField(max_length=200)	
	agent = models.ForeignKey(agent)

class agent_openid(models.Model):
	id = models.PositiveIntegerField(primary_key=True)
	openid = URLField()
	agent = models.ForeignKey(agent)	

class agent_account(models.Model):
	id = models.PositiveIntegerField(primary_key=True)
	account = models.account()
	agent = models.ForeignKey(agent)

class account(models.Model):
	id = models.PositiveIntegerField(primary_key=True)
	accountServiceHomePage = models.CharField(max_length=200)
	accountName = models.CharField(max_length=200)
	
class person(models.Model):
	id = models.PositiveIntegerField(primary_key=True)

class person_givenName(models.Model):
	id = models.PositiveIntegerField(primary_key=True)
	givenName = models.CharField(max_length=200)	
	person = models.ForeignKey(person)

class person_familyName(models.Model):
	id = models.PositiveIntegerField(primary_key=True)
	familyName = models.CharField(max_length=200)
	person = models.ForeignKey(person)

class person_firstName(models.Model):
	id = models.PositiveIntegerField(primary_key=True)
	firstName = models.CharField(max_length=200)
	person = models.ForeignKey(person)

class person_lastName(models.Model):
	id = models.PositiveIntegerField(primary_key=True)
	lastName = models.CharField(max_length=200)
	person = models.ForeignKey(person)


	

class activity(models.Model):
	key = models.PositiveIntegerField(primary_key=True)
	id = models.CharField(max_length=200)
	objectType = models.ForeignKey(statement)	

#Needs name map, desc map, extensions map, type
class activity_definition(models.Model):
	id = models.PositiveIntegerField(primary_key=True)
	interactionType = models.CharField(max_length=200)
	activity = models.ForeignKey(activity)






