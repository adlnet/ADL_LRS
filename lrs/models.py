from django.db import models
from uuidfield import UUIDField
#this is BAD, if anyone knows a better way to store kv pairs in MySQL let me know

#needs object
class statement(models.Model):
	id = UUIDField(primary_key=True)	
	verb = models.CharField(max_length=200)
	inProgress = models.BooleanField(blank=True)	
	result = models.ForeignKey(result, blank=True)
	timestamp = models.DateTimeField(blank=True)
	stored = models.DateTimeField(blank=True)	
	authority = models.ForeignKey(agent, blank=True)
	voided = models.BooleanField(blank=True)

class statement_actor(models.Model):
	id = models.PositiveIntegerField(primary_key=True)
	actor = models.ForeignKey(agent)
	statement = models.ForeignKey(statement)

class statement_context(models.Model):
	id = models.PositiveIntegerField(primary_key=True)
	context = models.ForeignKey(context)
	statement = models.ForeignKey(statement)		

class result(models.Model):
	id = models.PositiveIntegerField(primary_key=True)	
	score = models.PositiveIntegerField(blank=True)
	success = models.CharField(max_length=200, blank=True)
	completion = models.BooleanField(blank=True)
	response = models.CharField(max_length=200)
	duration = models.DateTimeField()

class result_extensions(models.Model):
	id = models.PositiveIntegerField(primary_key=True)
	key=models.CharField(max_length=200)
	value=models.CharField(max_length=200)
	result = models.ForeignKey(result)

class context(models.Model):
	id = models.PositiveIntegerField(primary_key=True)
	registration = UUIDField()
	team = models.CharField(max_length=200)
	contextActivities = models.CharField(max_length=200)
	revision = models.CharField(max_length=200)
	platform = models.CharField(max_length=200)
	language = models.CharField(max_length=200)
	statement = models.CharField(max_length=200)

class context_instructor(models.Model):
	id = models.PositiveIntegerField(primary_key=True)
	instructor = models.ForeignKey(agent)
	context = models.ForeignKey(context)

class context_extentions(models.Model):
	id = models.PositiveIntegerField(primary_key=True)
	key=models.CharField(max_length=200)
	value=models.CharField(max_length=200)
	context = models.ForeignKey(context)

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

class agent(models.Model):
	id = models.PositiveIntegerField(primary_key=True)
	objectType = models.CharField(max_length=200)
	weblog = models.CharField(max_length=200)
	icqChatID = models.CharField(max_length=200)
	msnChatID = models.CharField(max_length=200)
	age = models.PositiveIntegerField()
	yahooChatID = models.CharField(max_length=200)
	tipjar = models.CharField(max_length=200)
	jabberID = models.CharField(max_length=200)
	status = models.CharField(max_length=200)
	gender = models.CharField(max_length=6)
	interest = models.CharField(max_length=200)
	holdsAccount = models.CharField(max_length=200)
	topic_interest = models.CharField(max_length=200)
	aimChatID = models.CharField(max_length=200)
	birthday = models.CharField(max_length=10)
	made = models.CharField(max_length=200)
	skypeID = models.CharField(max_length=200)

class agent_name(models.Model):
	id = models.PositiveIntegerField(primary_key=True)
	name = models.CharField(max_length=200)
	agent = models.ForeignKey(agent)

class agent_mbox(models.Model):
	id = models.PositiveIntegerField(primary_key=True)
	mbox = models.CharField(max_length=200)
	agent = models.ForeignKey(agent)

class agent_mbox_sha1sum(models.Model):
	id = models.PositiveIntegerField(primary_key=True)
	mbox_sha1sum = models.CharField(max_length=200)
	agent = models.ForeignKey(agent)		

class agent_openid(models.Model):
	id = models.PositiveIntegerField(primary_key=True)
	openid = models.CharField(max_length=200)
	agent = models.ForeignKey(agent)		

class account(models.Model):
	id = models.PositiveIntegerField(primary_key=True)
	accountServiceHomePage = models.CharField(max_length=200)
	accountName = models.CharField(max_length=200)

class agent_account(models.Model):
	id = models.PositiveIntegerField(primary_key=True)
	account = models.ForeignKey(account)
	agent = models.ForeignKey(agent)		

class person(models.Model):
	id = models.PositiveIntegerField(primary_key=True)
	agent = ForeignKey(agent)

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

class group(models.Model):
	id = models.PositiveIntegerField(primary_key=True)

class group_member(models.Model):
	id = models.PositiveIntegerField(primary_key=True)
	agent = models.ForeignKey(agent)
	member = models.ForeignKey(group)

class activity(models.Model):
	key = models.PositiveIntegerField(primary_key=True)
	id = models.CharField(max_length=200)
	objectType = models.ForeignKey(statement)
	definition = models.ForeignKey(activity_definition)

class activity_definition(models.Model):
	id = models.PositiveIntegerField(primary_key=True)
	name = models.CharField(max_length=200)
	description = models.CharField(max_length=200)
	type = 	models.CharField(max_length=200)
	interactionType = models.CharField(max_length=200)

class activity_extentions(models.Model):
	id = models.PositiveIntegerField(primary_key=True)
	key = models.CharField(max_length=200)
	value = models.CharField(max_length=200)
	activity_definition = models.ForeignKey(activity_definition)

	