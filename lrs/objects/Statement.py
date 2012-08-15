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


    def _validateVerbResult(self,result, verb):
        completedVerbs = ['completed', 'mastered', 'passed', 'failed']
        print 'in _validateVerbResult'
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

    def _parseResult(self, stmt_data):
        resultJSON = False
        #TODO: distinguish between json and string type for result
        '''
        try:
            results = json.loads(stmt_data['result'])
            resultJSON = True
        except Exception, e:
            #Is string, not JSON
            results = stmt_data['result']
        '''
        resultJSON = True
        return (resultJSON, results)

    #TODO: Validate score results against cmi.score in scorm 2004 4th ed. RTE
    def _validateResultScore(self, score_data):
        pass

    def _saveScoreToDB(self, args):
        sc = models.score(**score)
        sc.save()
        return sc

    def _saveResultToDB(self, result):
        rslt = models.result(**result)
        rslt.save()
        return rslt

    #Save statement to DB
    def _saveStatementToDB(self, args):
        stmt = models.statement(**args)
        stmt.save()
        return stmt

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

        #TODO: Needed? Just make voided false? Cannot have voided as True
        #if 'voided' in stmt_data.keys():
        #    if stmt_data['voided'] == 'True':
        #        raise Exception('Cannot have voided statement unless it is being voided by another statement')

        #If not specified, the object is assumed to be an activity
        if not 'objectType' in statementObjectData.keys():
        	statementObjectData['objectType'] = 'Activity'

        #Check objectType, create object based on type
        if statementObjectData['objectType'] == 'Activity':
            args['stmt_object'] = Activity(json.dumps(statementObjectData)).activity
        if statementObjectData['objectType'] == 'Person':
            args['stmt_object'] = Actor(json.dumps(statementObjectData)).agent	

        #TODO: finish testing result
        #Set result when present - result object can be string or JSON object
        if 'result' in stmt_data.keys():
            resultJSON, result = self._parseResult(stmt_data)

            #Catch contradictory results if results is JSON object
            if resultJSON:
                print 'in resultJSON'
                self._validateVerbResult(result, args['verb'])
                #Once found that the results are valid against the verb, check score object and save
                if 'score' in result.keys():
                    self._validateResultScore(result['score'])
                    result['score'] = self._saveScore(result['score'])

            #Should save result if it is string or result object
            #TODO: If result is just string, how do we save to DB? 
            args['result'] = self._saveResultToDB(result)

        #TODO:Validate/parse context object
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


        #Create uuid for ID
        args['statement_id'] = uuid.uuid4()
        self.statement = self._saveStatementToDB(args)