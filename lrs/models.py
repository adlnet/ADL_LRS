from django.db import models
from uuidfield import UUIDField
#this is BAD, if anyone knows a better way to store kv pairs in MySQL let me know

class score(models.Model):
	id = models.PositiveIntegerField(primary_key=True)
	scaled = models.BooleanField()
	raw = models.PositiveIntegerField()
	min = models.PositiveIntegerField()
	max = models.PositiveIntegerField()

class state(models.Model):
	key = models.PositiveIntegerField(primary_key=True)
	id = models.CharField(max_length=200)
	contents = models.CharField(max_length=200)

class agent(models.Model):
	id = models.PositiveIntegerField(primary_key=True)
	objectType = models.CharField(max_length=200)

class context(models.Model):
	id = models.PositiveIntegerField(primary_key=True)
	registration = UUIDField()
	team = models.CharField(max_length=200)
	contextActivities = models.CharField(max_length=200)
	revision = models.CharField(max_length=200)
	platform = models.CharField(max_length=200)
	language = models.CharField(max_length=200)
	statement = models.CharField(max_length=200)



class result(models.Model):
	id = models.PositiveIntegerField(primary_key=True)	
	score = models.PositiveIntegerField()
	success = models.CharField(max_length=200)
	completion = models.BooleanField()
	duration = models.DateTimeField()
	extensions = models.CharField(max_length=200)

class statement(models.Model):
	id = UUIDField(primary_key=True)	
	verb = models.CharField(max_length=200)
	inProgress = models.BooleanField()	
	result = models.ForeignKey(result)
	timestamp = models.DateTimeField()
	stored = models.DateTimeField()	
	voided = models.BooleanField()

class context_extentions(models.Model):
	id = models.PositiveIntegerField(primary_key=True)
	key=models.CharField(max_length=200)
	value=models.CharField(max_length=200)
	context = models.ForeignKey(context)
class result_extension(models.Model):
	id = models.PositiveIntegerField(primary_key=True)
	key=models.CharField(max_length=200)
	value=models.CharField(max_length=200)
	result = models.ForeignKey(result)	
class statement_actor(models.Model):
	id = models.PositiveIntegerField(primary_key=True)
	stmt = models.ForeignKey(statement)

class context_actor(models.Model):
	id = models.PositiveIntegerField(primary_key=True)
	ctx = models.ForeignKey(context)	
class activity(models.Model):
	id = models.PositiveIntegerField(primary_key=True)
	object = models.ForeignKey(statement)	