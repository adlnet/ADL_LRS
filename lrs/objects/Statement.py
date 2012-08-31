import json
import types
import uuid
import datetime
from lrs import models
from django.core.exceptions import FieldError
from django.db import transaction
from functools import wraps
from Activity import Activity
from Actor import Actor
import pdb

class Statement():

    #Use single transaction for all the work done in function
    @transaction.commit_on_success
    def __init__(self, initial=None, auth=None, statement_id=None,get=False):
        if get and statement_id is not None:
            self.statement_id = statement_id
        else:
            obj = self._parse(initial)
            self._populate(obj, auth)

    #Make sure initial data being received is JSON
    def _parse(self,initial):
        if initial:
            if type(initial) is dict:
                initial=json.dumps(initial)

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

    def _validateResultResponse(self, result, obj_data):
        pass
        # #Check if there is a response in result, and check the activity type 
        # if 'response' in result and 'definition' in obj_data:
        #     actDef = obj_data['definition']
        #     if 'type' in actDef:
        #         #If activity is not a cmi.interaction  or interaction type then throw exception
        #         if not actDef['type'] == 'cmi.interaction' or actDef['type'] == 'interaction':
        #             raise Exception("Response only valid for interaction or cmi.interaction activity types")
        #         else:
        #             #Check each type of interactionType if it is a cmi.interaction
        #             if actDef['type'] == 'cmi.interaction':
        #                 actDefIntType = actDef['interactionType']
        #                 #Throw exception if it is true-false type yet response isn't string of true or false
        #                 if actDefIntType == 'true-false' and result['response'] not in ['true', 'false']:
        #                     raise Exception("Activity is true-false interactionType, your response must either be 'true' or 'false'")
        #                 if actDefIntType == 'multiple-choice' and result['response'] not in ['true', 'false']:
        #                     raise Exception("Activity is true-false interactionType, your response must either be 'true' or 'false'")

    def get_full_statement_json(self):
        #Check to see if statement exists
        try:
            stmt = models.statement.objects.get(statement_id=self.statement_id)            
        except models.statement.DoesNotExist:
            raise IDNotFoundError('There is no statement associated with the id: %s' % self.statement_id)

        # pdb.set_trace()
        #Set statement to return
        ret = models.objsReturn(stmt)
        # ret = stmt.StmtObjReturn()
        print ret
        return ret

    def _validateVerbResult(self,result, verb, obj_data):
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

        #Validate response
        # self._validateResultResponse(result, obj_data)

    #TODO: Validate score results against cmi.score in scorm 2004 4th ed. RTE
    def _validateScoreResult(self, score_data):
        pass

    def _saveScoreToDB(self, score):
        sc = models.score(**score)
        sc.save()
        return sc

    def _saveResultToDB(self, result, resultExts, resultString):
        #If the result is a string, create empty result and save the string in a result extension with the key resultString
        if resultString:
            rslt = models.result()
            rslt.save()

            res_ext = models.result_extensions(key='resultString', value=result, result=rslt)
            res_ext.save()
            return rslt

        #Save the result with all of the args
        rslt = models.result(**result)
        rslt.save()

        #If it has extensions, save them all
        if resultExts:
            for k, v in resultExts.items():
                resExt = models.result_extensions(key=k, value=v, result=rslt)
                resExt.save()

        return rslt

    def _saveContextToDB(self, context, contextExts):
        
        cntx = models.context(**context)    
        cntx.save()

        if contextExts:
            for k, v in contextExts.items():
                conExt = models.context_extensions(key=k, value=v, context=cntx)
                conExt.save()

        return cntx        

    #Save statement to DB
    def _saveStatementToDB(self, args):
        #pdb.set_trace()
        stmt = models.statement(**args)
        stmt.save()
        return stmt

    def _populateResult(self, stmt_data, verb):
        resultString = False
        stringExt = {}
        resultExts = {}
        
        #Check if the result is not a dict inside of JSON, if it's not then the data has a string instead
        if not type(stmt_data['result']) is dict:
            #Set resultString to True and result to the string
            resultString = True
            result = stmt_data['result']
            
        #Catch contradictory results if results is JSON object
        if not resultString:    
            if 'extensions' in stmt_data['result']:
                result = {key: value for key, value in stmt_data['result'].items() if not key == 'extensions'}
                resultExts = stmt_data['result']['extensions']   
            else:
                result = stmt_data['result']

            self._validateVerbResult(result, verb, stmt_data['object'])

            #Once found that the results are valid against the verb, check score object and save
            if 'score' in result.keys():
                self._validateScoreResult(result['score'])
                result['score'] = self._saveScoreToDB(result['score'])

        #Save result
        return self._saveResultToDB(result, resultExts, resultString)

    def _populateContext(self, stmt_data):
        instructor = team = False
        revision = platform = True
        contextExts = {}


        if 'registration' not in stmt_data['context']:
            raise Exception('Registration UUID required for context')

        if 'contextActivities' not in stmt_data['context']:
            raise Exception('contextActivities required for context')

        # Statement Actor and Object supercede context instructor and team
        # If there is an actor or object is a person in the stmt then remove the instructor
        if 'actor' in stmt_data:
            if stmt_data['actor']['objectType'] == 'Person':
                stmt_data['context']['instructor'] = Actor(json.dumps(stmt_data['actor']), create=True).agent
        elif stmt_data['object']['objectType'] == 'Person':
            stmt_data['context']['instructor'] = Actor(json.dumps(stmt_data['object']), create=True).agent
        elif 'instructor' in stmt_data['context']:
            stmt_data['context']['instructor'] = Actor(json.dumps(stmt_data['context']['instructor']), create=True).agent


        # If there is an actor or object is a group in the stmt then remove the team
        if 'actor' in stmt_data or 'group' == stmt_data['object']['objectType']:
            if 'team' in stmt_data['context']:                
                del stmt_data['context']['team']                

        # Revision and platform not applicable if object is person
        if 'person' == stmt_data['object']['objectType']:
            del stmt_data['context']['revision']
            del stmt_data['context']['platform']

        if 'extensions' in stmt_data['context']:
            context = {key: value for key, value in stmt_data['context'].items() if not key == 'extensions'}
            contextExts = stmt_data['context']['extensions']
        else:
            context = stmt_data['context']

        if 'statement' in context:
            context['statement'] = Statement(context['statement']).statement.id

        return self._saveContextToDB(context, contextExts)

    #Once JSON is verified, populate the statement object
    def _populate(self, stmt_data, auth):
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

        #Throw error since you can't set voided to True
        if 'voided' in stmt_data:
            if stmt_data['voided']:
                raise Exception('Cannot have voided statement unless it is being voided by another statement')


        #Retrieve actor if in JSON only for now
        if 'actor' in stmt_data:
            args['actor'] = Actor(json.dumps(stmt_data['actor']), create=True).agent
        else:
             if auth:
                authArgs = {}
                authArgs['name'] = [auth.username]
                authArgs['mbox'] = [auth.email]
                args['actor'] = Actor(json.dumps(authArgs), create=True).agent

        #Set inProgress to false
        args['inProgress'] = False

        #Set inProgress when present
        if 'inProgress' in stmt_data:
            args['inProgress'] = stmt_data['inProgress']

        #Set voided to default false
        args['voided'] = False

        #If not specified, the object is assumed to be an activity
        if not 'objectType' in statementObjectData:
        	statementObjectData['objectType'] = 'Activity'

        #Check objectType, create object based on type
        if statementObjectData['objectType'] == 'Activity':
            args['stmt_object'] = Activity(json.dumps(statementObjectData)).activity
        elif statementObjectData['objectType'] == 'Person':
            args['stmt_object'] = Actor(json.dumps(statementObjectData), create=True).agent	

        #Set result when present - result object can be string or JSON object
        if 'result' in stmt_data:
            args['result'] = self._populateResult(stmt_data, args['verb'])

	    #Set context when present
        if 'context' in stmt_data:
            args['context'] = self._populateContext(stmt_data)

      	#Set timestamp when present
      	if 'timestamp' in stmt_data:
      		args['timestamp'] = stmt_data['timestamp']

        if 'authority' in stmt_data:
            args['authority'] = Actor(json.dumps(stmt_data['authority']), create=True).agent
        else:
            if auth:
                authArgs = {}
                authArgs['name'] = [auth.username]
                authArgs['mbox'] = [auth.email]
                args['authority'] = Actor(json.dumps(authArgs), create=True).agent

        #Check to see if voiding statement
        if args['verb'] == 'voided':
        	#objectType must be statement if want to void another statement
        	if statementObjectData['objectType'].lower() == 'statement' and 'id' in statementObjectData.keys():
        		self._voidStatement(statementObjectData['id'])

        #If verb is imported then create either the actor or activity it is importing
        if args['verb'] == 'imported':
            if statementObjectData['objectType'].lower() == 'activity':
                importedActivity = Activity(statementObjectData).activity
            elif obj['objectType'].lower() == 'actor':
                importedActor = Actor(statementObjectData).agent

        #See if statement_id already exists, throw exception if it does
        if 'statement_id' in stmt_data:
            try:
                existingSTMT = models.statement.objects.get(statement_id=stmt_data['statement_id'])
            except models.statement.DoesNotExist:
                args['statement_id'] = stmt_data['statement_id']
            else:
                raise Exception("The Statement ID %s already exists in the system" % args['statement_id'])
        else:
            #Create uuid for ID
            args['statement_id'] = uuid.uuid4()
        
        #Save statement
        self.statement = self._saveStatementToDB(args)