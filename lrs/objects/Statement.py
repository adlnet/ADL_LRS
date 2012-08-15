import json
import types
import uuid
from lrs import models
from django.core.exceptions import FieldError
from django.db import transaction
from functools import wraps
from Activity import Activity
from Actor import Actor

class Statement():

    #Use single transaction for all the work done in function
    @transaction.commit_on_success
    def __init__(self, initial=None):
        obj = self._parse(initial)
        self._populate(obj)

    #Make sure initial data being received is JSON
    def _parse(self,initial):
        if initial:
            #TODO:If it can't load it as JSON, should we try dumping it to JSON and testing as well?
            #Don't put in try..catching exception to raise exception removes stack trace-will have better stack trace if this fails
            return json.loads(initial)
        return {}		


    def _voidStatement(self,stmt_id):
        #Retrieve statement, check if the verb is 'voided' - if not then set the voided flag to true else return error 
        #since you cannot unvoid a statement and should just reissue the statement under a new ID.
        try:
            stmt = models.statement.objects.get(statement_id=stmt_id)
        except Exception, e:
            raise e
        
        if not stmt.voided:
            stmt.voided = True
            stmt.save()
        else:
            raise Exception('Statment already voided, cannot unvoid. Please reissure the statement under a new ID.')


    def _validateVerbResult(result, obj, verb):
        completedVerbs = ['completed', 'mastered', 'passed', 'failed']
        
        #If completion is false then verb cannot be completed, mastered, 
        if result['completion'] == False:                
            if verb in completedVerbs:
                #Throw exceptions b/c those verbs must have true completion
                raise Exception('Completion must be True if using the verb ' + verb)

        if verb == 'mastered' and result['success'] == False:
            #Throw exception b/c mastered and success contradict each other or completion is false
            raise Exception('Result success must be True if verb is ' + verb)

        if verb == 'passed' and result['success'] == False:
            #Throw exception b/c passed and success contradict each other or completion is false
            raise Exception('Result success must be True if verb is ' + verb)

        if verb == 'failed' and result['success'] == True:
            #Throw exception b/c failed and success contradict each other or completion is false
            raise Exception('Result success must be False if verb is ' + verb)

    #Save statement to DB
    #def _save_statement_to_db(self, statement_id, verb, stmt_object, actor=False, inProgress=False, result=False, context=False, timestamp=False, authority=False, voided=False):
    def _save_statement_to_db(self, args):
        #st = models.statement(statement_id=statement_id, verb=verb, stmt_object=stmt_object)
        st = models.statement(**args)
        st.save()
        return st

    #Once JSON is verified, populate the statement object
    def _populate(self, stmt_data):
        resultJSON = False
        args ={}
        #Must include verb - set statement verb - set to lower too
        try:
            args['verb'] = stmt_data['verb'].lower()
        except KeyError:
            raise Exception("No verb provided, must provide 'verb' field")

        #Must include object - set statement object
        try:
            statementObjectData = stmt_data['object']
        except KeyError:
            raise Exception("No object provided, must provide 'object' field")

        #Retrieve actor if in JSON only for now
        if 'actor' in stmt_data.keys():
        	args['actor'] = models.Actor(stmt_data['actor']).agent
        else:
        	#Determine actor from authentication
            pass

        #Set inProgress to false
        args['inProgress'] = False

        #Set inProgress when present
        if 'inProgress' in stmt_data.keys():
            args['inProgress'] = stmt_data['inProgress']

        #Set voided to default false
        args['voided'] = False

        #Cannot have voided as True
        if 'voided' in stmt_data.keys():
            if stmt_data['voided'] == 'True':
                raise Exception('Cannot have voided statement unless it is being voided by another statement')

        #If not specified, the object is assumed to be an activity
        if not 'objectType' in statementObjectData.keys():
        	statementObjectData['objectType'] = 'Activity'

        #Check objectType, create object based on type
        if statementObjectData['objectType'] == 'Activity':
            args['stmt_object'] = Activity(json.dumps(statementObjectData)).activity
        if statementObjectData['objectType'] == 'Person':
            args['stmt_object'] = Actor(json.dumps(statementObjectData)).agent	

        #Set result when present - result object can be string or JSON object
        if 'result' in stmt_data.keys():
	        try:
	        	args['result'] = json.loads(stmt_data['result'])
	        	resultJSON = True
	        except Exception, e:
	        	#Is string, not JSON
	        	args['result'] = stmt_data['result']

	    #Set context when present
      	if 'context' in stmt_data.keys():
            #Is instructor or team saved as an agent object or string?
      		args['context'] = stmt_data['context']

      	#Set timestamp when present
      	if 'timestamp' in stmt_data.keys():
      		args['timestamp'] = stmt_data['timestamp']

      	if 'authority' in stmt_data.keys():
      		args['authority'] = Actor(stmt_data['authority'])
      	else:
      		#TODO:Find authenticated user???
            pass


        #Check to see if voiding statement
        if args['verb'] == 'voided':
        	#objectType must be statement if want to void another statement
        	if statementObjectData['objectType'].lower() == 'statement' and 'id' in statementObjectData.keys():
        		self._voidStatement(statementObjectData['id'])

        #If verb is imported then create either the actor or activity it is importing
        if args['verb'] == 'imported':
            if statementObjectData['objectType'].lower() == 'activity':
                importedActivity = Activity(statementObjectData)
            elif obj['objectType'].lower() == 'actor':
                importedActor = Actor(statementObjectData)

        #Catch contradictory results if results is JSON object
        if resultJSON:
                self._validateVerbResult(args['result'], args['stmt_object'], args['verb'])

        #Create uuid for ID
        args['statement_id'] = uuid.uuid4()
        self.statement = self._save_statement_to_db(args)