import json
import types
import uuid
import datetime
from lrs import models, exceptions
from lrs.objects.Agent import Agent
from django.core.exceptions import FieldError
from django.db import transaction
from functools import wraps
from Activity import Activity
from functools import wraps
from django.utils.timezone import utc
import pdb

class default_on_exception(object):
    def __init__(self,default):
        self.default = default
    def __call__(self,f):
        @wraps(f)
        def closure(obj,*args,**kwargs):
            try:
                return f(obj,*args,**kwargs)
            except:
                return self.default
        return closure


class Statement():
    #Use single transaction for all the work done in function
    @transaction.commit_on_success
    def __init__(self, initial=None, auth=None, statement_id=None, get=False):
        if get and statement_id is not None:
            self.statement_id = statement_id
            self.statement = None
            try:
                self.statement = models.statement.objects.get(statement_id=self.statement_id)
            except models.statement.DoesNotExist:
                raise exceptions.IDNotFoundError('There is no statement associated with the id: %s' % self.statement_id)
        else:
            # pdb.set_trace()
            obj = self._parse(initial)
            self._populate(obj, auth)

    #Make sure initial data being received is JSON
    def _parse(self,initial):
        if initial:
            if type(initial) is dict:
                initial=json.dumps(initial)

            #Don't put in try..catching exception to raise exception removes stack trace-will have better stack trace if this fails
            try:
                return json.loads(initial)
            except:
                raise exceptions.ParamError("Invalid JSON")
        return {}		


    def _voidStatement(self,stmt_id):
        # Retrieve statement, check if the verb is 'voided' - if not then set the voided flag to true else return error 
        # since you cannot unvoid a statement and should just reissue the statement under a new ID.
        try:
            stmt = models.statement.objects.get(statement_id=stmt_id)
        except Exception:
            raise exceptions.IDNotFoundError("Statement with that ID does not exist")
        
        if not stmt.voided:
            stmt.voided = True
            stmt.save()
            stmt_ref = models.StatementRef(ref_id=stmt_id)
            stmt_ref.save()
            return stmt_ref
        else:
            raise exceptions.Forbidden('Statment already voided, cannot unvoid. Please re-issue the statement under a new ID.')

    def _remove_extra_agent_info(self, ret, fieldName):
        if 'familyName' in ret[fieldName]:
            del ret[fieldName]['familyName']
        
        if 'givenName' in ret[fieldName]:
            del ret[fieldName]['givenName']
        
        if 'firstName' in ret[fieldName]:
            del ret[fieldName]['firstName']
        
        if 'lastName' in ret[fieldName]:
            del ret[fieldName]['lastName']
        
        if 'openid' in ret[fieldName]:
            del ret[fieldName]['openid']
        
        if 'account' in ret[fieldName]:
            del ret[fieldName]['account']
        return ret

    def get_full_statement_json(self, sparse=False, language=None):
        # Set statement to return
        # ret = models.objsReturn(self.statement, language)
        ret = self.statement.object_return(language)
        # Remove details if sparse is true
        if sparse:
            # Remove responses and only return language for name and description
            if 'definition' in ret['object']:
                if 'correctresponsespattern' in ret['object']['definition']:
                    del ret['object']['definition']['correctresponsespattern']
                    ret['object']['definition']['description'] = ret['object']['definition']['description'].keys()
                    ret['object']['definition']['name'] = ret['object']['definition']['name'].keys()

            # Remove other names/accounts in actor
            if 'actor' in ret:
                self._remove_extra_agent_info(ret, 'actor')

            # Remove other names/accounts in authority
            if 'authority' in ret:
                self._remove_extra_agent_info(ret, 'authority')

            # Remove other names/accounts if agent is the object of statement
            if 'objectType' in ret['object']:
                if ret['object']['objectType'].lower() == 'agent' or ret['object']['objectType'].lower() == 'person':
                    self._remove_extra_agent_info(ret, 'object')

            # Remove other names/accounts if there is a context and it has an instructor
            if 'context' in ret:
                if 'instructor' in ret['context']:
                    if 'familyName' in ret['context']['instructor']: 
                        del ret['context']['instructor']['familyName']

                    if 'givenName'in ret['context']['instructor']:
                        del ret['context']['instructor']['givenName']

                    if 'firstName' in ret['context']['instructor']: 
                        del ret['context']['instructor']['firstName']

                    if 'lastName'in ret['context']['instructor']:
                        del ret['context']['instructor']['lastName']

                    if 'openid' in ret['context']['instructor']: 
                        del ret['context']['instructor']['openid']

                    if 'account'in ret['context']['instructor']:
                        del ret['context']['instructor']['account']

        return ret

    def _validateVerbResult(self,result, verb, obj_data):
        completedVerbs = ['completed', 'mastered', 'passed', 'failed']

        #If completion is false then verb cannot be completed, mastered, 
        if 'completion' in result:
            if result['completion'] == False:                
                if verb in completedVerbs:
                    #Throw exceptions b/c those verbs must have true completion
                    raise exceptions.ParamError('Completion must be True if using the verb ' + verb)

        if verb == 'mastered' and result['success'] == False:
            #Throw exception b/c mastered and success contradict each other or completion is false
            raise exceptions.ParamError('Result success must be True if verb is ' + verb)

        if verb == 'passed' and result['success'] == False:
            #Throw exception b/c passed and success contradict each other or completion is false
            raise exceptions.ParamError('Result success must be True if verb is ' + verb)

        if verb == 'failed' and result['success'] == True:
            #Throw exception b/c failed and success contradict each other or completion is false
            raise exceptions.ParamError('Result success must be False if verb is ' + verb)

    def _validateScoreResult(self, score_data):
        if 'min' in score_data:
            score_data['score_min'] = score_data['min']
            del score_data['min']

        if 'max' in score_data:
            score_data['score_max'] = score_data['max']
            del score_data['max']

        return score_data

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
        # pdb.set_trace()
        con_act_data = None
        if 'contextActivities' in context:
            con_act_data = context['contextActivities']
            del context['contextActivities']

        # if 'instructor' in context:
        #     del context['instructor']
        # if 'team' in context:
        #     del context['team']
        # if 'cntx_statement' in context:
        #     del context['cntx_statement']
        # pdb.set_trace()
        cntx = models.context(**context)    
        cntx.save()

        if con_act_data:
            for con_act in con_act_data.items():
                ca = models.ContextActivity(key=con_act[0], context_activity=con_act[1]['id'])
                ca.save()
                cntx.contextActivities.add(ca)
            cntx.save()

        if contextExts:
            for k, v in contextExts.items():
                conExt = models.context_extensions(key=k, value=v, context=cntx)
                conExt.save()

        return cntx        

    #Save statement to DB
    def _saveStatementToDB(self, args, sub):
        # pdb.set_trace()
        if sub:
            del args['voided']
            del args['statement_id']
            if 'authority' in args:
                del args['authority']
            stmt = models.SubStatement(**args)
            stmt.save()
        else:
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
                result['score'] = self._validateScoreResult(result['score'])
                result['score'] = self._saveScoreToDB(result['score'])

        #Save result
        return self._saveResultToDB(result, resultExts, resultString)

    def _populateContext(self, stmt_data):
        instructor = team = False
        revision = platform = True
        contextExts = {}


        if 'registration' not in stmt_data['context']:
            # raise Exception('Registration UUID required for context')
            stmt_data['context']['registration'] = uuid.uuid4()

        # Statement Actor and Object supercede context instructor and team
        # If there is an actor or object is an agent in the stmt then remove the instructor
        if 'actor' in stmt_data:
            if 'objectType' not in stmt_data['actor'] or (stmt_data['actor']['objectType'].lower() == 'agent' 
                                                      or stmt_data['actor']['objectType'].lower() == 'group'):
                stmt_data['context']['instructor'] = Agent(initial=stmt_data['actor'], create=True).agent
        elif 'objectType' in stmt_data['object'] and (stmt_data['object']['objectType'].lower() == 'agent'
                                                    or stmt_data['object']['objectType'].lower() == 'group'):
            stmt_data['context']['instructor'] = Agent(initial=stmt_data['object'], create=True).agent
        elif 'instructor' in stmt_data['context']:
            stmt_data['context']['instructor'] = Agent(initial=stmt_data['context']['instructor'], create=True).agent


        # If there is an actor or object is a group in the stmt then remove the team
        if 'actor' in stmt_data or 'group' == stmt_data['object']['objectType'].lower():
            if 'team' in stmt_data['context']:                
                del stmt_data['context']['team']                

        # Revision and platform not applicable if object is agent
        if 'objectType' in stmt_data['object'] and ('agent' == stmt_data['object']['objectType'].lower()
                                                or 'group' == stmt_data['object']['objectType'].lower()):
            del stmt_data['context']['revision']
            del stmt_data['context']['platform']

        if 'extensions' in stmt_data['context']:
            context = {key: value for key, value in stmt_data['context'].items() if not key == 'extensions'}
            contextExts = stmt_data['context']['extensions']
        else:
            context = stmt_data['context']

        if 'statement' in context:
            # stmt = Statement(context['statement']).statement.id 
            stmt = models.statement.objects.get(statement_id=context['statement']['id'])
            # stmt = Statement(statement_id=context['statement']['id'], get=True)
            stmt_ref = models.StatementRef(ref_id=context['statement']['id'])
            stmt_ref.save()
            context['cntx_statement'] = stmt_ref
            del context['statement']

        return self._saveContextToDB(context, contextExts)


    def _save_lang_map(self, lang_map):
        k = lang_map[0]
        v = lang_map[1]

        language_map = models.LanguageMap(key = k, value = v)
        
        language_map.save()        
        return language_map

    def _build_verb_object(self, incoming_verb):
        verb = {}
        
        if 'id' not in incoming_verb:
            raise exceptions.ParamError("ID field is not included in statement verb")

        # verb_object, created = models.Verb.objects.get_or_create(verb_id=incoming_verb['id'], statement=self.statement)
        verb_object, created = models.Verb.objects.get_or_create(verb_id=incoming_verb['id'])

        if not created:
            existing_lang_map_keys = verb_object.display.all().values_list('key', flat=True)
        else:
            existing_lang_map_keys = []

        # Save verb displays
        if 'display' in incoming_verb:
            # Iterate incoming lang maps
            for verb_lang_map in incoming_verb['display'].items():
                # Make sure it's a dict
                if isinstance(verb_lang_map, tuple):
                    # If incoming key doesn't already exist in verb's lang maps - add it
                    if not verb_lang_map[0] in existing_lang_map_keys: 
                        lang_map = self._save_lang_map(verb_lang_map)    
                        verb_object.display.add(lang_map)
                    else:
                        existing_verb_lang_map = verb_object.display.get(key=verb_lang_map[0])
                        models.LanguageMap.objects.filter(id=existing_verb_lang_map.id).update(value=verb_lang_map[1])
                        # existing_verb_lang_map.update(value=verb_lang_map[1])
                else:
                    raise exceptions.ParamError("Verb display for verb %s is not a correct language map" % incoming_verb['id'])        
            verb_object.save()
        return verb_object

    #Once JSON is verified, populate the statement object
    def _populate(self, stmt_data, auth, sub=False):
        # pdb.set_trace()
        args ={}
        #Must include verb - set statement verb 
        try:
            raw_verb = stmt_data['verb']
        except KeyError:
            raise exceptions.ParamError("No verb provided, must provide 'verb' field")

        #Must include object - set statement object
        try:
            statementObjectData = stmt_data['object']
        except KeyError:
            raise exceptions.ParamError("No object provided, must provide 'object' field")

        try:
            raw_actor = stmt_data['actor']
        except KeyError:
            raise exceptions.ParamError("No actor provided, must provide 'actor' field")

        # Throw error since you can't set voided to True
        if 'voided' in stmt_data:
            if stmt_data['voided']:
                raise exceptions.Forbidden('Cannot have voided statement unless it is being voided by another statement')
        
        # If not specified, the object is assumed to be an activity
        if not 'objectType' in statementObjectData:
            statementObjectData['objectType'] = 'Activity'

        args['verb'] = self._build_verb_object(raw_verb)

        valid_agent_objects = ['agent', 'group']
        # Check to see if voiding statement
        # if raw_verb['id'] == 'http://adlnet.gov/expapi/verbs/voided':
        if args['verb'].verb_id == 'http://adlnet.gov/expapi/verbs/voided':
            # objectType must be statementRef if want to void another statement
            if statementObjectData['objectType'].lower() == 'statementref' and 'id' in statementObjectData.keys():
                stmt_ref = self._voidStatement(statementObjectData['id'])
                args['stmt_object'] = stmt_ref
            else:
                raise exceptions.ParamError("There was a problem voiding the Statement")
        else:
            # Check objectType, get object based on type
            if statementObjectData['objectType'].lower() == 'activity':
                if auth is not None:        
                    args['stmt_object'] = Activity(json.dumps(statementObjectData),auth=auth.username).activity
                else:
                    args['stmt_object'] = Activity(json.dumps(statementObjectData)).activity
            elif statementObjectData['objectType'].lower() in valid_agent_objects:
                args['stmt_object'] = Agent(initial=statementObjectData, create=True).agent
            elif statementObjectData['objectType'].lower() == 'substatement':
                sub_statement = SubStatement(statementObjectData, auth)
                args['stmt_object'] = sub_statement.statement

        #Retrieve actor
        args['actor'] = Agent(initial=stmt_data['actor'], create=True).agent

        #Set voided to default false
        args['voided'] = False

        #Set result when present - result object can be string or JSON object
        if 'result' in stmt_data:
            # args['result'] = self._populateResult(stmt_data, raw_verb)
            args['result'] = self._populateResult(stmt_data, args['verb'])

	    # Set context when present
        if 'context' in stmt_data:
            args['context'] = self._populateContext(stmt_data)

      	# Set timestamp when present
      	if 'timestamp' in stmt_data:
      		args['timestamp'] = stmt_data['timestamp']

        if 'authority' in stmt_data:
            args['authority'] = Agent(initial=stmt_data['authority'], create=True).agent
        else:
            # pdb.set_trace()
            if auth:
                authArgs = {}
                authArgs['name'] = auth.username
                authArgs['mbox'] = auth.email
                args['authority'] = Agent(initial=authArgs, create=True).agent

        #See if statement_id already exists, throw exception if it does
        if 'statement_id' in stmt_data:
            try:
                existingSTMT = models.statement.objects.get(statement_id=stmt_data['statement_id'])
            except models.statement.DoesNotExist:
                args['statement_id'] = stmt_data['statement_id']
            else:
                raise exceptions.ParamConflict("The Statement ID %s already exists in the system" % stmt_data['statement_id'])
        else:
            #Create uuid for ID
            args['statement_id'] = uuid.uuid4()

        #Save statement
        self.statement = self._saveStatementToDB(args, sub)

class SubStatement(Statement):
    @transaction.commit_on_success
    def __init__(self, data, auth):
        # pdb.set_trace()
        unallowed_fields = ['id', 'stored', 'authority']

        for field in unallowed_fields:
            if field in data:
                raise exceptions.ParamError("%s is not allowed in a SubStatement.")

        if 'objectType' in data['object']:
            if data['object']['objectType'].lower() == 'substatement':
                raise exceptions.ParamError("SubStatements cannot be nested inside of other SubStatements")

        self._populate(data, auth, sub=True)

        
