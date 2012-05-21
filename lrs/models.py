from django.db import models
from uuidfield import UUIDField
#this is BAD, if anyone knows a better way to store kv pairs in MySQL let me know

#needs object

class result(models.Model):	
	success = models.CharField(max_length=200, blank=True,null=True)
	completion = models.BooleanField(blank=True)
	response = models.CharField(max_length=200)
	duration = models.DateTimeField()

class result_extensions(models.Model):
	key=models.CharField(max_length=200)
	value=models.CharField(max_length=200)
	result = models.ForeignKey(result)

class score(models.Model):	
	scaled = models.BooleanField()
	raw = models.PositiveIntegerField()
	score_min = models.PositiveIntegerField()
	score_max = models.PositiveIntegerField()
	result = models.ForeignKey(result)

class state(models.Model):
	key = models.PositiveIntegerField(primary_key=True)
	state_id = models.CharField(max_length=200)
	updated = models.DateTimeField()
	contents = models.CharField(max_length=200)

class agent(models.Model):	
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
	name = models.CharField(max_length=200)
	agent = models.ForeignKey(agent)

class agent_mbox(models.Model):
	mbox = models.CharField(max_length=200)
	agent = models.ForeignKey(agent)

class agent_mbox_sha1sum(models.Model):
	mbox_sha1sum = models.CharField(max_length=200)
	agent = models.ForeignKey(agent)		

class agent_openid(models.Model):
	openid = models.CharField(max_length=200)
	agent = models.ForeignKey(agent)		

class account(models.Model):
	accountServiceHomePage = models.CharField(max_length=200)
	accountName = models.CharField(max_length=200)

class agent_account(models.Model):	
	account = models.OneToOneField(account)
	agent = models.OneToOneField(agent)		

class person(agent):	
	pass

class person_givenName(models.Model):
	givenName = models.CharField(max_length=200)
	person = models.ForeignKey(person)	

class person_familyName(models.Model):
	familyName = models.CharField(max_length=200)
	person = models.ForeignKey(person)	

class person_firstName(models.Model):
	firstName = models.CharField(max_length=200)
	person = models.ForeignKey(person)

class person_lastName(models.Model):
	lastName = models.CharField(max_length=200)
	person = models.ForeignKey(person)		

class group(agent):
	member = models.ForeignKey(agent,related_name="agent_group")

class activity_definition(models.Model):
	name = models.CharField(max_length=200)
	description = models.CharField(max_length=200)
	activity_definition_type = models.CharField(max_length=200)
	interactionType = models.CharField(max_length=200)

class activity_extentions(models.Model):
	key = models.CharField(max_length=200)
	value = models.CharField(max_length=200)
	activity_definition = models.ForeignKey(activity_definition)

class context(models.Model):	
	registration = UUIDField()
	instructor = models.OneToOneField(agent)
	team = models.CharField(max_length=200)
	contextActivities = models.CharField(max_length=200)
	revision = models.CharField(max_length=200)
	platform = models.CharField(max_length=200)
	language = models.CharField(max_length=200)
	statement = models.CharField(max_length=200)

class statement(models.Model):
	statement_id = UUIDField(primary_key=True)	
	verb = models.CharField(max_length=200)
	inProgress = models.BooleanField(blank=True)	
	result = models.OneToOneField(result, blank=True,null=True)
	timestamp = models.DateTimeField(blank=True,null=True)
	stored = models.DateTimeField(blank=True,null=True)	
	authority = models.OneToOneField(agent, blank=True,null=True,related_name="authority_statement")
	voided = models.BooleanField(blank=True)
	actor = models.OneToOneField(agent,related_name="actor_statement")
	context = models.OneToOneField(context, related_name="context_statement")

class context_extentions(models.Model):
	key=models.CharField(max_length=200)
	value=models.CharField(max_length=200)
	context = models.ForeignKey(context)

class activity(models.Model):
	key = models.PositiveIntegerField(primary_key=True)
	activity_id = models.CharField(max_length=200)
	objectType = models.ForeignKey(statement)
	definition = models.ForeignKey(activity_definition)