from django.db import models
from uuidfield import UUIDField
class actor(models.Model):
	id = models.PositiveIntegerField(primary_key=True)

class context(models.Model):
	id = models.PositiveIntegerField(primary_key=True)

class activity(models.Model):
	id = models.PositiveIntegerField(primary_key=True)

class result(models.Model):
	id = models.PositiveIntegerField(primary_key=True)	
	score = models.PositiveIntegerField()
	success = models.CharField(max_length=200)
	completion = models.BooleanField()
	duration = models.DateTimeField()
	extensions = models.CharField(max_length=200)
# Create your models here.
class statement(models.Model):
	id = UUIDField(primary_key=True)
	actor = models.ForeignKey(actor)
	verb = models.CharField(max_length=200)
	inProgress = models.BooleanField()
	object = models.ForeignKey(activity)
	result = models.ForeignKey(result)
	timestamp = models.DateTimeField()
	stored = models.DateTimeField()
	authority = models.ForeignKey(actor)
	voided = models.BooleanField()