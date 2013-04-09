import json
import re
from django.core.exceptions import ValidationError
from django.db import transaction
from functools import wraps
from isodate.isoduration import parse_duration
from isodate.isoerror import ISO8601Error
from lrs import models, exceptions
from lrs.util import get_user_from_auth, log_message, update_parent_log_status, uri
from Agent import Agent
from Activity import Activity
import logging
import pprint
import pdb

logger = logging.getLogger('user_system_actions')

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
    def __init__(self, data, auth=None, log_dict=None, define=True):
        self.auth = auth
        self.params = data
        self.log_dict = log_dict
        self.define = define
        if not isinstance(data, dict):
            self.params = self.parse(data)
        self.populate(self.params)

    #Make sure initial data being received is JSON
    def parse(self,data):
        try:
            params = json.loads(data)
        except Exception, e:
            err_msg = "Error parsing the Statement object. Expecting json. Received: %s which is %s" % (data, type(data))
            log_message(self.log_dict, err_msg, __name__, self.parse.__name__, True)
            update_parent_log_status(self.log_dict, 400)
            raise exceptions.ParamError(err_msg) 
        return params

    def voidStatement(self,stmt_id):
        str_id = str(stmt_id)
        log_message(self.log_dict, "Voiding Statement with ID %s" % str_id,
            __name__, self.voidStatement.__name__)        
        
        # Retrieve statement, check if the verb is 'voided' - if not then set the voided flag to true else return error 
        # since you cannot unvoid a statement and should just reissue the statement under a new ID.
        try:
            stmt = models.statement.objects.get(statement_id=stmt_id)
        except Exception:
            err_msg = "Statement with ID %s does not exist" % str(stmt_id)
            log_message(self.log_dict, err_msg, __name__, self.voidStatement.__name__, True)
            update_parent_log_status(self.log_dict, 404)
            raise exceptions.IDNotFoundError(err_msg)
        
        # Check if it is already voided 
        if not stmt.voided:
            stmt.voided = True
            stmt.save()
            # Create statement ref
            stmt_ref = models.StatementRef(ref_id=stmt_id)
            stmt_ref.save()

            return stmt_ref
        else:
            err_msg = "Statement with ID: %s is already voided, cannot unvoid. Please re-issue the statement under a new ID." % str_id
            log_message(self.log_dict, err_msg, __name__, self.voidStatement.__name__, True)
            update_parent_log_status(self.log_dict, 403)
            raise exceptions.Forbidden(err_msg)

    # Statement fields are score_min and score_max
    def validateScoreResult(self, score_data):
        # If min and max are both in score, make sure min is less than max and if raw is included
        # make sure it's between those two values
        # Elif it's either just min or max, set them
        if 'min' in score_data and 'max' in score_data:
            sc_min = score_data['min']
            sc_max = score_data['max']
            if sc_min >= sc_max:
                err_msg = "Score minimum must be less than the maximum"
                log_message(self.log_dict, err_msg, __name__, self.validateScoreResult.__name__, True)
                update_parent_log_status(self.log_dict, 400)
                raise exceptions.ParamError(err_msg)
            
            if 'raw' in score_data and (score_data['raw'] < sc_min or score_data['raw'] > sc_max):
                err_msg = "Raw must be between minimum and maximum"
                log_message(self.log_dict, err_msg, __name__, self.validateScoreResult.__name__, True)
                update_parent_log_status(self.log_dict, 400)
                raise exceptions.ParamError(err_msg)
            score_data['score_min'] = sc_min
            score_data['score_max'] = sc_max
        elif 'min' in score_data:
            score_data['score_min'] = score_data['min']
            del score_data['min']
        elif 'max' in score_data:
            score_data['score_max'] = score_data['max']
            del score_data['max']

        # If scale is included make sure it's between -1 and 1
        if 'scaled' in score_data:
            if score_data['scaled'] < -1 or score_data['scaled'] > 1:
                err_msg = "Scaled must be between -1 and 1"
                log_message(self.log_dict, err_msg, __name__, self.validateScoreResult.__name__, True)
                update_parent_log_status(self.log_dict, 400)
                raise exceptions.ParamError(err_msg)

        return score_data

    def saveScoreToDB(self, score):
        sc = models.score(**score)
        sc.save()
        log_message(self.log_dict, "Score saved to database", __name__, self.saveScoreToDB.__name__)
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
                if not uri.validate_uri(k):
                    err_msg = "Extension ID %s is not a valid URI" % k
                    log_message(self.log_dict, err_msg, __name__, self.saveResultToDB.__name__, True)
                    update_parent_log_status(self.log_dict, 400)
                    raise exceptions.ParamError(err_msg)
                resExt = models.extensions(key=k, value=v, content_object=rslt)
                resExt.save()
        log_message(self.log_dict, "Result saved to database", __name__, self.saveResultToDB.__name__)
        return rslt

    def saveContextToDB(self, context, contextExts):
        # Set context activities to context dict
        con_act_data = None
        if 'contextActivities' in context:
            con_act_data = context['contextActivities']
            del context['contextActivities']
        
        # Save context
        cntx = models.context(content_object=self.model_object, **context)    
        cntx.save()

        # Save context activities
        if con_act_data:
            for con_act in con_act_data.items():
                ca_id = con_act[1]['id']
                if not uri.validate_uri(ca_id):
                    raise exceptions.ParamError('Context Activity ID %s is not a valid URI' % ca_id)
                ca = models.ContextActivity(key=con_act[0], context_activity=ca_id, context=cntx)
                ca.save()
            cntx.save()

        # Save context extensions
        if contextExts:
            for k, v in contextExts.items():
                if not uri.validate_uri(k):
                    err_msg = "Extension ID %s is not a valid URI" % k
                    log_message(self.log_dict, err_msg, __name__, self.saveContextToDB.__name__, True)
                    update_parent_log_status(self.log_dict, 400)
                    raise exceptions.ParamError(err_msg)                    
                conExt = models.extensions(key=k, value=v, content_object=cntx)
                conExt.save()

        log_message(self.log_dict, "Context saved to database", __name__, self.saveContextToDB.__name__)

        return cntx        

    #Save statement to DB
    def saveObjectToDB(self, args):
        # If it's a substatement, remove voided, authority, and id keys
        args['user'] = get_user_from_auth(self.auth)
        if self.__class__.__name__ == 'SubStatement':
            del args['voided']
            
            # If ID not given, created by models
            if 'statement_id' in args:
                del args['statement_id']
            
            if 'authority' in args:
                del args['authority']
            stmt = models.SubStatement(**args)
            stmt.save()
        else:
            stmt = models.statement(**args)
            stmt.save()

        if self.log_dict:
            self.log_dict['message'] = "Saved statement to database in %s.%s" % (__name__, self.saveObjectToDB.__name__)
            logger.info(msg=self.log_dict)
            self.log_dict['message'] = stmt.statement_id #stmt.object_return()
            logger.log(models.SystemAction.STMT_REF, msg=self.log_dict)            

        return stmt

    def populateResult(self, stmt_data):
        log_message(self.log_dict, "Populating result", __name__, self.populateResult.__name__)

        resultExts = {}                    
        #Catch contradictory results
        if 'extensions' in stmt_data['result']:
            result = {key: value for key, value in stmt_data['result'].items() if not key == 'extensions'}
            resultExts = stmt_data['result']['extensions']   
        else:
            result = stmt_data['result']

        # Validate duration, throw error if duration is not formatted correctly
        if 'duration' in result:
            try:
                dur = parse_duration(result['duration'])
            except ISO8601Error as e:
                log_message(self.log_dict, e.message, __name__, self.populateResult.__name__, True)
                update_parent_log_status(self.log_dict, 400)
                raise exceptions.ParamError(e.message)

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
        log_message(self.log_dict, "Populating context", __name__, self.populateContext.__name__)

        if 'registration' in stmt_data['context']:
            self.validate_incoming_uuid(stmt_data['context']['registration'])

        if 'instructor' in stmt_data['context']:
            stmt_data['context']['instructor'] = Agent(initial=stmt_data['context']['instructor'],
                create=True, log_dict=self.log_dict, define=self.define).agent

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
            stmt_obj = context['statement']

            # Check objectType since can be both ref or sub
            if 'objectType' in stmt_obj:
                if stmt_obj['objectType'] == 'StatementRef':
                    stmt_ref = models.StatementRef(ref_id=stmt_obj['id'])
                    stmt_ref.save()
                    context['statement'] = stmt_ref                    
                elif stmt_obj['objectType'] == 'SubStatement':
                    sub_stmt = SubStatement(stmt_obj, self.auth, self.log_dict).model_object
                    context['statement'] = sub_stmt
                else:
                    err_msg = "Statement in context must be SubStatement or StatementRef"
                    log_message(self.log_dict, err_msg, __name__, self.populateContext.__name__, True)
                    update_parent_log_status(self.log_dict, 400)
                    raise exceptions.ParamError(err_msg)                    
            else:
                err_msg = "Statement in context must contain an objectType"
                log_message(self.log_dict, err_msg, __name__, self.populateContext.__name__, True)
                update_parent_log_status(self.log_dict, 400)
                raise exceptions.ParamError(err_msg)
        return self.saveContextToDB(context, contextExts)

    def save_lang_map(self, lang_map, verb):
        # If verb is model object but not saved yet
        if not verb.id:
            try:
                verb.full_clean()
                verb.save()
            except ValidationError as e:
                err_msg = e.messages[0]
                log_message(self.log_dict, err_msg, __name__, self.save_lang_map.__name__, True)
                update_parent_log_status(self.log_dict, 400)
                raise exceptions.ParamError(err_msg)
        
        k = lang_map[0]
        v = lang_map[1]

        # Save lang map
        language_map = models.LanguageMap(key = k, value = v, content_object=verb)
        language_map.save()        

        return language_map

    def build_verb_object(self, incoming_verb):
        log_message(self.log_dict, "Building verb object", __name__, self.build_verb_object.__name__)

        verb = {}    
        # Must have an ID
        if 'id' not in incoming_verb:
            err_msg = "ID field is not included in statement verb"
            log_message(self.log_dict, err_msg, __name__, self.build_verb_object.__name__, True) 
            update_parent_log_status(self.log_dict, 400)       
            raise exceptions.ParamError(err_msg)

        if not uri.validate_uri(incoming_verb['id']):
            err_msg = 'Verb ID %s is not a valid URI' % incoming_verb['id']
            log_message(self.log_dict, err_msg, __name__, self.build_verb_object.__name__, True) 
            update_parent_log_status(self.log_dict, 400)       
            raise exceptions.ParamError(err_msg)

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
                    err_msg = "Verb display for verb %s is not a correct language map" % incoming_verb['id']
                    log_message(self.log_dict, err_msg, __name__, self.build_verb_object.__name__, True) 
                    update_parent_log_status(self.log_dict, 400)       
                    raise exceptions.ParamError(err_msg)
            verb_object.save()

        return verb_object

    def validate_incoming_uuid(self, incoming_uuid):
        regex = re.compile("[a-fA-F0-9]{8}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{12}")
        match = regex.match(incoming_uuid)
        if not match:
            err_msg = "%s is not a valid UUID" % incoming_uuid
            log_message(self.log_dict, err_msg, __name__, self.validate_incoming_uuid.__name__, True)
            update_parent_log_status(self.log_dict, 400)                   
            raise exceptions.ParamError(err_msg)

    #Once JSON is verified, populate the statement object
    def populate(self, stmt_data):
        log_message(self.log_dict, "Populating Statement", __name__, self.populate.__name__)

        args ={}
        # Must include verb - set statement verb 
        try:
            raw_verb = stmt_data['verb']
        except KeyError:
            err_msg = "No verb provided, must provide 'verb' field"
            log_message(self.log_dict, err_msg, __name__, self.populate.__name__, True) 
            update_parent_log_status(self.log_dict, 400)       
            raise exceptions.ParamError(err_msg)

        # Must include object - set statement object
        try:
            statementObjectData = stmt_data['object']
        except KeyError:
            err_msg = "No object provided, must provide 'object' field"
            log_message(self.log_dict, err_msg, __name__, self.populate.__name__, True) 
            update_parent_log_status(self.log_dict, 400)       
            raise exceptions.ParamError(err_msg)
        
        # Must include actor - set statement actor
        try:
            raw_actor = stmt_data['actor']
        except KeyError:
            err_msg = "No actor provided, must provide 'actor' field"
            log_message(self.log_dict, err_msg, __name__, self.populate.__name__, True) 
            update_parent_log_status(self.log_dict, 400)       
            raise exceptions.ParamError(err_msg)

        args['verb'] = self.build_verb_object(raw_verb)

        # Throw error since you can't set voided to True
        if 'voided' in stmt_data:
            if stmt_data['voided']:
                err_msg = "Cannot have voided statement unless it is being voided by another statement"
                log_message(self.log_dict, err_msg, __name__, self.populate.__name__, True)  
                update_parent_log_status(self.log_dict, 403)      
                raise exceptions.Forbidden(err_msg)
        
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
                err_msg = "There was a problem voiding the Statement"
                log_message(self.log_dict, err_msg, __name__, self.populate.__name__, True) 
                update_parent_log_status(self.log_dict, 400)       
                raise exceptions.ParamError(err_msg)
        else:
            # Check objectType, get object based on type
            if statementObjectData['objectType'].lower() == 'activity':
                args['stmt_object'] = Activity(statementObjectData,auth=self.auth,
                    log_dict=self.log_dict, define=self.define).activity
            elif statementObjectData['objectType'].lower() in valid_agent_objects:
                args['stmt_object'] = Agent(initial=statementObjectData, create=True,
                    log_dict=self.log_dict, define=self.define).agent
            elif statementObjectData['objectType'].lower() == 'substatement':
                sub_statement = SubStatement(statementObjectData, self.auth, self.log_dict)
                args['stmt_object'] = sub_statement.model_object
            elif statementObjectData['objectType'].lower() == 'statementref':
                try:
                    existing_stmt = models.statement.objects.get(statement_id=statementObjectData['id'])
                except models.statement.DoesNotExist:
                    err_msg = "No statement with ID %s was found" % statementObjectData['id']
                    log_message(self.log_dict, err_msg, __name__, self.populate.__name__, True)
                    update_parent_log_status(self.log_dict, 404)
                    raise exceptions.IDNotFoundError(err_msg)
                else:
                    stmt_ref = models.StatementRef(ref_id=statementObjectData['id'])
                    stmt_ref.save()
                    args['stmt_object'] = stmt_ref

        #Retrieve actor
        args['actor'] = Agent(initial=stmt_data['actor'], create=True, log_dict=self.log_dict,
            define=self.define).agent

        #Set voided to default false
        args['voided'] = False
        
        # Set timestamp when present
        if 'timestamp' in stmt_data:
            args['timestamp'] = stmt_data['timestamp']

        # If non oauth group won't be sent with the authority key, so if it's a group it's a non
        # oauth group which isn't allowed to be the authority
        if 'authority' in stmt_data:
            auth_data = stmt_data['authority']
            if not isinstance(auth_data, dict):
                auth_data = json.loads(auth_data)

            # If they're trying to put their oauth group in authority for some reason, just retrieve
            # it. If it doesn't exist, the Agent class responds with a 404
            if auth_data['objectType'].lower() == 'group':
                args['authority'] = Agent(initial=stmt_data['authority'], create=False,
                    log_dict=self.log_dict, define=self.define).agent
            else:
                args['authority'] = Agent(initial=stmt_data['authority'], create=True,
                    log_dict=self.log_dict, define=self.define).agent

            # If they try using a non-oauth group that already exists-throw error
            if args['authority'].objectType == 'Group' and not args['authority'].oauth_identifier:
                err_msg = "Statements cannot have a non-Oauth group as the authority"
                log_message(self.log_dict, err_msg, __name__, self.populate.__name__, True)
                update_parent_log_status(self.log_dict, 400)                   
                raise exceptions.ParamError(err_msg)

        else:
            # Look at request from auth if not supplied in stmt_data.
            if self.auth:
                authArgs = {}
                if self.auth.__class__.__name__ == 'agent':
                    if self.auth.oauth_identifier:
                        args['authority'] = self.auth
                    else:
                        err_msg = "Statements cannot have a non-Oauth group as the authority"
                        log_message(self.log_dict, err_msg, __name__, self.populate.__name__, True)
                        update_parent_log_status(self.log_dict, 400)                   
                        raise exceptions.ParamError(err_msg)
                else:    
                    authArgs['name'] = self.auth.username
                    if self.auth.email.startswith("mailto:"):
                        authArgs['mbox'] = self.auth.email
                    else:
                        authArgs['mbox'] = "mailto:%s" % self.auth.email
                    args['authority'] = Agent(initial=authArgs, create=True,
                        log_dict=self.log_dict, define=self.define).agent

        # Check if statement_id already exists, throw exception if it does
        if 'statement_id' in stmt_data:
            try:
                existingSTMT = models.statement.objects.get(statement_id=stmt_data['statement_id'])
            except models.statement.DoesNotExist:
                self.validate_incoming_uuid(stmt_data['statement_id'])
                args['statement_id'] = stmt_data['statement_id']
            else:
                err_msg = "The Statement ID %s already exists in the system" % stmt_data['statement_id']
                log_message(self.log_dict, err_msg, __name__, self.populate.__name__, True)
                update_parent_log_status(self.log_dict, 409)                   
                raise exceptions.ParamConflict(err_msg)

        #Save statement/substatement
        self.model_object = self.saveObjectToDB(args)

        if 'result' in stmt_data:
            self.populateResult(stmt_data)

        if 'context' in stmt_data:
            self.populateContext(stmt_data)

class SubStatement(Statement):
    @transaction.commit_on_success
    def __init__(self, data, auth, log_dict=None):
        self.log_dict = log_dict
        unallowed_fields = ['id', 'stored', 'authority']
        # Raise error if an unallowed field is present
        for field in unallowed_fields:
            if field in data:
                err_msg = "%s is not allowed in a SubStatement." % field
                log_message(self.log_dict, err_msg, __name__, self.__init__.__name__, True)
                update_parent_log_status(self.log_dict, 400)    
                raise exceptions.ParamError(err_msg)
        # Make sure object isn't another substatement
        if 'objectType' in data['object']:
            if data['object']['objectType'].lower() == 'substatement':
                err_msg = "SubStatements cannot be nested inside of other SubStatements"
                log_message(self.log_dict, err_msg, __name__, self.__init__.__name__, True)
                update_parent_log_status(self.log_dict, 400)
                raise exceptions.ParamError(err_msg)

        Statement.__init__(self, data, auth)
