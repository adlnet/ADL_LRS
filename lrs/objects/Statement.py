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
import pprint
import ast

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
    def __init__(self, data=None, auth=None):
        self.auth = auth
        self.params = data
        if not isinstance(data, dict):
            self.params = self.parse(data)
        self.populate(self.params)

    #Make sure initial data being received is JSON
    def parse(self,data):
        try:
            params = json.loads(data)
        except Exception, e:
            try:
                params = ast.literal_eval(data)
            except Exception, e:
                raise exceptions.ParamError("Error parsing the Statement object. Expecting json. Received: %s which is %s" % (data, type(data))) 
        return params

    def voidStatement(self,stmt_id):
        # Retrieve statement, check if the verb is 'voided' - if not then set the voided flag to true else return error 
        # since you cannot unvoid a statement and should just reissue the statement under a new ID.
        try:
            stmt = models.statement.objects.get(statement_id=stmt_id)
        except Exception:
            raise exceptions.IDNotFoundError("Statement with that ID does not exist")

        # Check if it is already voided 
        if not stmt.voided:
            stmt.voided = True
            stmt.save()
            # Create statement ref
            stmt_ref = models.StatementRef(ref_id=stmt_id)
            stmt_ref.save()
            return stmt_ref
        else:
            raise exceptions.Forbidden('Statment already voided, cannot unvoid. Please re-issue the statement under a new ID.')

    def validateVerbResult(self,result, verb, obj_data):
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

    def validateScoreResult(self, score_data):
        if 'min' in score_data:
            score_data['score_min'] = score_data['min']
            del score_data['min']

        if 'max' in score_data:
            score_data['score_max'] = score_data['max']
            del score_data['max']

        return score_data

    def saveScoreToDB(self, score):
        sc = models.score(**score)
        sc.save()
        return sc

    def saveResultToDB(self, result, resultExts):
        # Save the result with all of the args
        sc = result.pop('score', None)
        rslt = models.result(content_object=self.model_object, **result)
        rslt.save()
        if sc:
            sc.result = rslt
            sc.save()

        #If it has extensions, save them all
        if resultExts:
            for k, v in resultExts.items():
                resExt = models.extensions(key=k, value=v, content_object=rslt)
                resExt.save()

        return rslt

    def saveContextToDB(self, context, contextExts):
        # Set context activities to context dict
        con_act_data = None
        if 'contextActivities' in context:
            con_act_data = context['contextActivities']
            del context['contextActivities']

        # Set context statement
        cs = None
        if 'cntx_statement' in context:
            cs = context['cntx_statement'] 
            del context['cntx_statement']
        
        # Save context
        cntx = models.context(content_object=self.model_object, **context)    
        cntx.save()

        # Set context in context statement and save
        if cs:
            cs.context = cntx
            cs.save()

        # Save context activities
        if con_act_data:
            for con_act in con_act_data.items():
                ca = models.ContextActivity(key=con_act[0], context_activity=con_act[1]['id'], context=cntx)
                ca.save()
            cntx.save()

        # Save context extensions
        if contextExts:
            for k, v in contextExts.items():
                conExt = models.extensions(key=k, value=v, content_object=cntx)
                conExt.save()

        return cntx        

    #Save statement to DB
    def saveObjectToDB(self, args):
        # If it's a substatement, remove voided, authority, and id keys
        if self.__class__.__name__ == 'SubStatement':
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

    def populateResult(self, stmt_data, verb):
        resultExts = {}
                    
        #Catch contradictory results
        if 'extensions' in stmt_data['result']:
            result = {key: value for key, value in stmt_data['result'].items() if not key == 'extensions'}
            resultExts = stmt_data['result']['extensions']   
        else:
            result = stmt_data['result']

        self.validateVerbResult(result, verb, stmt_data['object'])

        #Once found that the results are valid against the verb, check score object and save
        if 'score' in result.keys():
            result['score'] = self.validateScoreResult(result['score'])
            result['score'] = self.saveScoreToDB(result['score'])

        #Save result
        return self.saveResultToDB(result, resultExts)

    def populateContext(self, stmt_data):
        instructor = False
        team = False
        revision = True
        platform = True
        contextExts = {}

        # Assign UUID if there is no registration for context
        if 'registration' not in stmt_data['context']:
            # raise Exception('Registration UUID required for context')
            stmt_data['context']['registration'] = uuid.uuid4()

        if 'instructor' in stmt_data['context']:
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

        # Set extensions
        if 'extensions' in stmt_data['context']:
            context = {key: value for key, value in stmt_data['context'].items() if not key == 'extensions'}
            contextExts = stmt_data['context']['extensions']
        else:
            context = stmt_data['context']

        # Save context stmt if one
        if 'statement' in context:
            stmt_ref = models.StatementRef(ref_id=context['statement']['id'])
            stmt_ref.save()
            context['cntx_statement'] = stmt_ref
            del context['statement']

        return self.saveContextToDB(context, contextExts)


    def save_lang_map(self, lang_map, verb):
        # If verb is model object but not saved yet
        if not verb.id:
            verb.save()
        
        k = lang_map[0]
        v = lang_map[1]

        # Save lang map
        language_map = models.LanguageMap(key = k, value = v, content_object=verb)
        language_map.save()        

        return language_map

    def build_verb_object(self, incoming_verb):
        verb = {}
        
        # Must have an ID
        if 'id' not in incoming_verb:
            raise exceptions.ParamError("ID field is not included in statement verb")

        # Get or create the verb
        verb_object, created = models.Verb.objects.get_or_create(verb_id=incoming_verb['id'])

        # If existing, get existing keys
        if not created:
            existing_lang_map_keys = verb_object.display.all().values_list('key', flat=True)
        else:
            existing_lang_map_keys = []

        # Save verb displays
        if 'display' in incoming_verb:
            # Iterate incoming lang maps
            for verb_lang_map in incoming_verb['display'].items():
                # Make sure it's a tuple
                if isinstance(verb_lang_map, tuple):
                    # If incoming key doesn't already exist in verb's lang maps - add it
                    if not verb_lang_map[0] in existing_lang_map_keys: 
                        lang_map = self.save_lang_map(verb_lang_map, verb_object)    
                    else:
                        existing_verb_lang_map = verb_object.display.get(key=verb_lang_map[0])
                        models.LanguageMap.objects.filter(id=existing_verb_lang_map.id).update(value=verb_lang_map[1])
                else:
                    raise exceptions.ParamError("Verb display for verb %s is not a correct language map" % incoming_verb['id'])        
            verb_object.save()
        return verb_object

    #Once JSON is verified, populate the statement object
    def populate(self, stmt_data):
        args ={}

        # Must include verb - set statement verb 
        try:
            raw_verb = stmt_data['verb']
        except KeyError:
            raise exceptions.ParamError("No verb provided, must provide 'verb' field")

        # Must include object - set statement object
        try:
            statementObjectData = stmt_data['object']
        except KeyError:
            raise exceptions.ParamError("No object provided, must provide 'object' field")
        
        # Must include actor - set statement actor
        try:
            raw_actor = stmt_data['actor']
        except KeyError:
            raise exceptions.ParamError("No actor provided, must provide 'actor' field")

        args['verb'] = self.build_verb_object(raw_verb)


        # Throw error since you can't set voided to True
        if 'voided' in stmt_data:
            if stmt_data['voided']:
                raise exceptions.Forbidden('Cannot have voided statement unless it is being voided by another statement')
        
        # If not specified, the object is assumed to be an activity
        if not 'objectType' in statementObjectData:
            statementObjectData['objectType'] = 'Activity'

        valid_agent_objects = ['agent', 'group']
        # Check to see if voiding statement
        if args['verb'].verb_id == 'http://adlnet.gov/expapi/verbs/voided':
            # objectType must be statementRef if want to void another statement
            if statementObjectData['objectType'].lower() == 'statementref' and 'id' in statementObjectData.keys():
                stmt_ref = self.voidStatement(statementObjectData['id'])
                args['stmt_object'] = stmt_ref
            else:
                raise exceptions.ParamError("There was a problem voiding the Statement")
        else:
            # Check objectType, get object based on type
            if statementObjectData['objectType'].lower() == 'activity':
                args['stmt_object'] = Activity(statementObjectData,auth=self.auth).activity
            elif statementObjectData['objectType'].lower() in valid_agent_objects:
                args['stmt_object'] = Agent(initial=statementObjectData, create=True).agent
            elif statementObjectData['objectType'].lower() == 'substatement':
                sub_statement = SubStatement(statementObjectData, self.auth)
                args['stmt_object'] = sub_statement.model_object
            elif statementObjectData['objectType'].lower() == 'statementref':
                try:
                    existing_stmt = models.statement.objects.get(statement_id=statementObjectData['id'])
                except models.statement.DoesNotExist:
                    raise exceptions.IDNotFoundError("No statement with ID %s was found" % statementObjectData['id'])
                else:
                    stmt_ref = models.StatementRef(ref_id=statementObjectData['id'])
                    stmt_ref.save()
                    args['stmt_object'] = stmt_ref

        #Retrieve actor
        args['actor'] = Agent(initial=stmt_data['actor'], create=True).agent

        #Set voided to default false
        args['voided'] = False
        
        # Set timestamp when present
        if 'timestamp' in stmt_data:
            args['timestamp'] = stmt_data['timestamp']

        if 'authority' in stmt_data:
            args['authority'] = Agent(initial=stmt_data['authority'], create=True).agent
        else:
            # Look at request from auth if not supplied in stmt_data
            if self.auth:
                authArgs = {}
                if self.auth.__class__.__name__ == 'group':
                    args['authority'] = self.auth
                else:    
                    authArgs['name'] = self.auth.username
                    authArgs['mbox'] = self.auth.email
                    args['authority'] = Agent(initial=authArgs, create=True).agent

        # Check if statement_id already exists, throw exception if it does
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

        #Save statement/substatement
        self.model_object = self.saveObjectToDB(args)

        if 'result' in stmt_data:
            self.populateResult(stmt_data, args['verb'])

        if 'context' in stmt_data:
            self.populateContext(stmt_data)


class SubStatement(Statement):
    @transaction.commit_on_success
    def __init__(self, data, auth):
        unallowed_fields = ['id', 'stored', 'authority']
        # Raise error if an unallowed field is present
        for field in unallowed_fields:
            if field in data:
                raise exceptions.ParamError("%s is not allowed in a SubStatement.")
        # Make sure object isn't another substatement
        if 'objectType' in data['object']:
            if data['object']['objectType'].lower() == 'substatement':
                raise exceptions.ParamError("SubStatements cannot be nested inside of other SubStatements")

        Statement.__init__(self, data, auth)
