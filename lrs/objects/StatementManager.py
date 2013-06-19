import json
import re
from django.core.exceptions import ValidationError
from django.db import transaction
from django.core.files.base import ContentFile
from django.core.cache import get_cache
from functools import wraps
from isodate.isoduration import parse_duration
from isodate.isoerror import ISO8601Error
from lrs import models, exceptions
from lrs.util import get_user_from_auth, uri
from AgentManager import AgentManager
from ActivityManager import ActivityManager

att_cache = get_cache('attachment_cache')

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

class StatementManager():
    #Use single transaction for all the work done in function
    @transaction.commit_on_success
    def __init__(self, data, auth=None, define=True):
        self.auth = auth
        self.define = define
        if not isinstance(data, dict):
            data = self.parse(data)
        self.validate_statement_fields(data)
        self.populate(data)

    def validate_statement_fields(self, stmt):
        if self.__class__.__name__ == 'StatementManager':
            allowed_fields = ['id', 'actor', 'verb', 'object', 'result', 'context', 'timestamp', 'authority', 'version',
                            'attachments']
        else:
            allowed_fields = ['actor', 'verb', 'object', 'result', 'context', 'timestamp', "objectType"]

        failed_list = [x for x in stmt.keys() if not x in allowed_fields]
        if failed_list:
            err_msg = "Invalid field(s) found in statement - %s" % ', '.join(failed_list)
            raise exceptions.ParamError(err_msg)

    #Make sure initial data being received is JSON
    def parse(self,data):
        try:
            params = json.loads(data)
        except Exception, e:
            err_msg = "Error parsing the Statement object. Expecting json. Received: %s which is %s" % (data,
                type(data))
            raise exceptions.ParamError(err_msg) 
        return params

    def void_statement(self,stmt_id):
        str_id = str(stmt_id)        
        # Retrieve statement, check if the verb is 'voided' - if not then set the voided flag to true else return error 
        # since you cannot unvoid a statement and should just reissue the statement under a new ID.
        try:
            stmt = models.Statement.objects.get(statement_id=stmt_id)
        except models.Statement.DoesNotExist:
            err_msg = "Statement with ID %s does not exist" % str(stmt_id)
            raise exceptions.IDNotFoundError(err_msg)
        
        # Check if it is already voided 
        if not stmt.voided:
            stmt.voided = True
            stmt.save()
            # Create statement ref
            stmt_ref = models.StatementRef.objects.create(ref_id=stmt_id)
            return stmt_ref
        else:
            err_msg = "Statement with ID: %s is already voided, cannot unvoid. Please re-issue the statement under a new ID." % str_id
            raise exceptions.Forbidden(err_msg)

    # Statement fields are score_min and score_max
    def validate_score_result(self, score_data):
        # If min and max are both in score, make sure min is less than max and if raw is included
        # make sure it's between those two values
        # Elif it's either just min or max, set them
        if 'min' in score_data and 'max' in score_data:
            sc_min = score_data['min']
            sc_max = score_data['max']
            if sc_min >= sc_max:
                err_msg = "Score minimum in statement result must be less than the maximum"
                raise exceptions.ParamError(err_msg)
            
            if 'raw' in score_data and (score_data['raw'] < sc_min or score_data['raw'] > sc_max):
                err_msg = "Raw value in statement result must be between minimum and maximum"
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
                err_msg = "Scaled value in statement result must be between -1 and 1"
                raise exceptions.ParamError(err_msg)

        return score_data

    def save_result_to_db(self, result, result_exts):
        if 'score' in result:
            for k,v in result['score'].iteritems():
                if not 'score' in k:
                    result['score_' + k] = v
                else:
                    result[k] = v
            del result['score']

        try:
            rslt = models.Result.objects.create(**result)
        except TypeError, e:
            err_msg = "Invalid field in result - %s" % e.message
            raise exceptions.ParamError(err_msg)

        #If it has extensions, save them all
        if result_exts:
            for k, v in result_exts.items():
                if not uri.validate_uri(k):
                    err_msg = "Extension ID %s is not a valid URI" % k
                    raise exceptions.ParamError(err_msg)
                models.ResultExtensions.objects.create(key=k, value=v, result=rslt)
        return rslt

    def save_context_to_db(self, context, context_exts):
        # Set context activities to context dict
        con_act_data = None
        if 'contextActivities' in context:
            con_act_data = context['contextActivities']
            del context['contextActivities']

        # Save context stmt if one
        stmt_data = None
        if 'statement' in context:
            stmt_data = context['statement']
            del context['statement']

        # Save context
        try:
            cntx = models.Context.objects.create(**context)
        except TypeError, e:
            err_msg = "Invalid field in context - %s" % e.message
            raise exceptions.ParamError(err_msg)

        # Save context stmt if one
        if stmt_data:
            # Check objectType since can be both ref or sub
            if 'objectType' in stmt_data:
                if stmt_data['objectType'] == 'StatementRef':
                    st_id = stmt_data['id']
                    if not models.Statement.objects.filter(statement_id=st_id).exists():
                        err_msg = "No existing statements found for statement in context with ID %s" % st_id
                        raise exceptions.ParamError(err_msg)
                    cntx.statement = st_id
                    cntx.save()
                else:
                    err_msg = "Statement in context must be StatementRef"
                    raise exceptions.ParamError(err_msg)                    
            else:
                err_msg = "Statement in context must contain an objectType"
                raise exceptions.ParamError(err_msg)

        # Save context activities
        if con_act_data:
            context_types = ['parent', 'grouping', 'category', 'other']
            # Can have multiple groupings
            for con_act_group in con_act_data.items():
                if not con_act_group[0] in context_types:
                    raise exceptions.ParamError('Context Activity type is not valid.')
                ca = models.ContextActivity.objects.create(key=con_act_group[0], context=cntx)
                # Incoming contextActivities can either be a list or dict
                if isinstance(con_act_group[1], list):
                    for con_act in con_act_group[1]:
                        act = ActivityManager(con_act,auth=self.auth, define=self.define).Activity
                        ca.context_activity.add(act)
                else:
                    act = ActivityManager(con_act_group[1],auth=self.auth, define=self.define).Activity
                    ca.context_activity.add(act)
                ca.save()

        # Save context extensions
        if context_exts:
            for k, v in context_exts.items():
                if not uri.validate_uri(k):
                    err_msg = "Extension ID %s is not a valid URI" % k
                    raise exceptions.ParamError(err_msg)              
                conExt = models.ContextExtensions.objects.create(key=k, value=v, context=cntx)
        return cntx        

    #Save statement to DB
    def save_object_to_db(self, args):
        # If it's a substatement, remove voided, authority, and id keys
        args['user'] = get_user_from_auth(self.auth)
        if self.__class__.__name__ == 'SubStatementManager':
            del args['voided']
            
            # If ID not given, created by models
            if 'statement_id' in args:
                del args['statement_id']
            
            if 'authority' in args:
                del args['authority']

            stmt = models.SubStatement.objects.create(**args)
        else:
            stmt = models.Statement.objects.create(**args)
        return stmt

    def populate_result(self, stmt_data):
        result_exts = {}                    
        #Catch contradictory results
        if 'extensions' in stmt_data['result']:
            result = dict((key, value) for (key, value) in stmt_data['result'].items() if not key == 'extensions')
            result_exts = stmt_data['result']['extensions']
        else:
            result = stmt_data['result']

        # Validate duration, throw error if duration is not formatted correctly
        if 'duration' in result:
            try:
                dur = parse_duration(result['duration'])
            except ISO8601Error as e:
                raise exceptions.ParamError(e.message)

        if 'score' in result.keys():
            result['score'] = self.validate_score_result(result['score'])
        #Save result
        return self.save_result_to_db(result, result_exts)

    def populate_attachments(self, attachment_data, attachment_payloads):
        # Iterate through each attachment
        for attach in attachment_data:
            # Pop displays and descs off
            displays = attach.pop('display')
            descriptions = attach.pop('description', None)

            # Get or create based on sha2
            if 'sha2' in attach:
                sha2 = attach['sha2']
                try:
                    attachment = models.StatementAttachment.objects.get(sha2=sha2)
                    created = False
                except models.StatementAttachment.DoesNotExist:
                    try:
                        attachment = models.StatementAttachment.objects.create(**attach)
                    except TypeError, e:
                        err_msg = "Invalid field in attachments - %s" % e.message
                        raise exceptions.ParamError(err_msg)
                        
                    created = True                
                    # Since there is a sha2, there must be a payload cached
                    # Decode payload from msg object saved in cache and create ContentFile from raw data
                    msg = att_cache.get(sha2)
                    raw_payload = msg.get_payload(decode=True)
                    try:
                        payload = ContentFile(raw_payload)
                    except:
                        try:
                            payload = ContentFile(raw_payload.read())
                        except Exception, e:
                            raise e    
                    # Save ContentFile payload to attachment model object
                    attachment.payload.save(sha2, payload)
            # If no sha2 there must be a fileUrl which is unique
            else:
                try:
                    attachment = models.StatementAttachment.objects.get(fileUrl=attach['fileUrl'])
                    created = False
                except Exception, e:
                    try:
                        attachment = models.StatementAttachment.objects.create(**attach)
                    except TypeError, e:
                        err_msg = "Invalid field in attachments - %s" % e.message
                        raise exceptions.ParamError(err_msg)
                    created = True

            # If it was just created, create the displays and descs
            if created:
                for display in displays.items():
                    models.StatementAttachmentDisplay.objects.create(key=display[0], value=display[1],
                        attachment=attachment)
            
                if descriptions:
                    for desc in descriptions.items():
                        models.StatementAttachmentDesc.objects.create(key=desc[0], value=desc[1],
                            attachment=attachment)

            # If have define permission and attachment already has existed
            if self.define and not created:
                # Grab existing display and desc keys for the attachment
                existing_display_keys = attachment.statementattachmentdisplay_set.all().values_list('key', flat=True)
                existing_desc_keys = attachment.statementattachmentdesc_set.all().values_list('key', flat=True)                

                # Iterate through each incoming display
                for d in displays.items():
                    # If it's a tuple
                    if isinstance(d, tuple):
                        # If the new key already exists, update that display with the new value
                        if d[0] in existing_display_keys:
                            existing_display = attachment.statementattachmentdisplay_set.get(key=d[0])
                            existing_display.value = d[1]
                            existing_display.save()
                        # Else it doesn't exist so just create it
                        else:
                            models.StatementAttachmentDisplay.objects.create(key=d[0], value=d[1],
                                attachment=attachment)
                # Iterate through each incoming desc
                for de in descriptions.items():
                    # If it's a tuple
                    if isinstance(de, tuple):
                        #  If the new key alerady exists, update that desc with the new value
                        if de[0] in existing_desc_keys:
                            existing_desc = attachment.statementattachmentdesc_set.get(key=de[0])
                            existing_desc.value = de[1]
                            existing_desc.save()
                        #  Else it doesn't exist so just create it
                        else:
                            models.StatementAttachmentDesc.objects.create(key=de[0], value=de[1],
                                attachment=attachment)

            # Add each attach to the stmt
            self.model_object.attachments.add(attachment)

            # Delete everything in cache for this statement
            if attachment_payloads:
                att_cache.delete_many(attachment_payloads)
        self.model_object.save()

    def populate_context(self, stmt_data):
        context_exts = {}

        if 'registration' in stmt_data['context']:
            self.validate_incoming_uuid(stmt_data['context']['registration'])

        if 'instructor' in stmt_data['context']:
            stmt_data['context']['instructor'] = AgentManager(params=stmt_data['context']['instructor'],
                create=True, define=self.define).Agent
            
        if 'team' in stmt_data['context']:
            stmt_data['context']['team'] = AgentManager(params=stmt_data['context']['team'],
                create=True, define=self.define).Agent

        # Revision and platform not applicable if object is agent
        if 'objectType' in stmt_data['object'] and ('agent' == stmt_data['object']['objectType'].lower()
                                                or 'group' == stmt_data['object']['objectType'].lower()):
            if 'revision' in stmt_data['context']:
                del stmt_data['context']['revision']
            if 'platform' in stmt_data['context']:
                del stmt_data['context']['platform']

        # Set extensions
        if 'extensions' in stmt_data['context']:
            context = dict((key, value) for (key, value) in stmt_data['context'].items() if not key == 'extensions')
            context_exts = stmt_data['context']['extensions']
        else:
            context = stmt_data['context']

        return self.save_context_to_db(context, context_exts)

    def save_lang_map(self, lang_map, verb):
        # If verb is model object but not saved yet
        if not verb.id:
            try:
                verb.full_clean()
                verb.save()
            except ValidationError as e:
                err_msg = e.messages[0]
                raise exceptions.ParamError(err_msg)
        
        k = lang_map[0]
        v = lang_map[1]

        # Save lang map
        language_map = models.VerbDisplay.objects.create(key = k, value = v, verb=verb)
        return language_map

    def build_verb_object(self, incoming_verb):
        verb = {}    
        # Must have an ID
        if 'id' not in incoming_verb:
            err_msg = "ID field is not included in statement verb"
            raise exceptions.ParamError(err_msg)
        
        verb_id = incoming_verb['id']
        if not uri.validate_uri(verb_id):
            err_msg = 'Verb ID %s is not a valid URI' % verb_id
            raise exceptions.ParamError(err_msg)

        # Get or create the verb
        verb_object, created = models.Verb.objects.get_or_create(verb_id=verb_id)

        # If existing, get existing keys
        if not created:
            existing_lang_map_keys = verb_object.verbdisplay_set.all().values_list('key', flat=True)
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
                        existing_verb_lang_map = verb_object.verbdisplay_set.get(key=verb_lang_map[0])
                        existing_verb_lang_map.value = verb_lang_map[1]
                        existing_verb_lang_map.save()
                else:
                    err_msg = "Verb display for verb %s is not a correct language map" % verb_id
                    raise exceptions.ParamError(err_msg)
            verb_object.save()

        return verb_object

    def validate_incoming_uuid(self, incoming_uuid):
        regex = re.compile("[a-fA-F0-9]{8}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{12}")
        match = regex.match(incoming_uuid)
        if not match:
            err_msg = "%s is not a valid UUID" % incoming_uuid
            raise exceptions.ParamError(err_msg)

    #Once JSON is verified, populate the statement object
    def populate(self, stmt_data):
        args ={}
        # Must include verb - set statement verb 
        try:
            raw_verb = stmt_data['verb']
        except KeyError:
            err_msg = "No verb provided in the statement, must provide 'verb' field"
            raise exceptions.ParamError(err_msg)

        # Must include object - set statement object
        try:
            statement_object_data = stmt_data['object']
        except KeyError:
            err_msg = "No object provided in the statement, must provide 'object' field"
            raise exceptions.ParamError(err_msg)
        
        # Must include actor - set statement actor
        try:
            raw_actor = stmt_data['actor']
        except KeyError:
            err_msg = "No actor provided in the statement, must provide 'actor' field"
            raise exceptions.ParamError(err_msg)

        args['verb'] = self.build_verb_object(raw_verb)

        # Throw error since you can't set voided to True
        if 'voided' in stmt_data:
            if stmt_data['voided']:
                err_msg = "Cannot have voided statement unless it is being voided by another statement"
                raise exceptions.Forbidden(err_msg)
        
        # If not specified, the object is assumed to be an activity
        if not 'objectType' in statement_object_data:
            statement_object_data['objectType'] = 'Activity'

        valid_agent_objects = ['agent', 'group']
        # Check to see if voiding statement
        if args['verb'].verb_id == 'http://adlnet.gov/expapi/verbs/voided':
            # objectType must be statementRef if want to void another statement
            if statement_object_data['objectType'].lower() == 'statementref' and 'id' in statement_object_data.keys():
                stmt_ref = self.void_statement(statement_object_data['id'])
                args['stmt_object'] = stmt_ref
            else:
                err_msg = "When voiding, the objectType must be a StatementRef and contain an ID to void"
                raise exceptions.ParamError(err_msg)
        else:
            # Check objectType, get object based on type
            if statement_object_data['objectType'].lower() == 'activity':
                args['stmt_object'] = ActivityManager(statement_object_data,auth=self.auth, define=self.define).Activity
            elif statement_object_data['objectType'].lower() in valid_agent_objects:
                args['stmt_object'] = AgentManager(params=statement_object_data, create=True, define=self.define).Agent
            elif statement_object_data['objectType'].lower() == 'substatement':
                sub_statement = SubStatementManager(statement_object_data, self.auth)
                args['stmt_object'] = sub_statement.model_object
            elif statement_object_data['objectType'].lower() == 'statementref':
                try:
                    existing_stmt = models.Statement.objects.get(statement_id=statement_object_data['id'])
                except models.Statement.DoesNotExist:
                    err_msg = "No statement with ID %s was found" % statement_object_data['id']
                    raise exceptions.IDNotFoundError(err_msg)
                else:
                    stmt_ref = models.StatementRef.objects.create(ref_id=statement_object_data['id'])
                    args['stmt_object'] = stmt_ref

        #Retrieve actor
        args['actor'] = AgentManager(params=stmt_data['actor'], create=True, define=self.define).Agent

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
                args['authority'] = AgentManager(params=stmt_data['authority'], create=False, 
                    define=self.define).Agent
            else:
                args['authority'] = AgentManager(params=stmt_data['authority'], create=True, 
                    define=self.define).Agent

            # If they try using a non-oauth group that already exists-throw error
            if args['authority'].objectType == 'Group' and not args['authority'].oauth_identifier:
                err_msg = "Statements cannot have a non-Oauth group as the authority"
                raise exceptions.ParamError(err_msg)

        else:
            # Look at request from auth if not supplied in stmt_data.
            if self.auth:
                auth_args = {}
                if self.auth.__class__.__name__ == 'Agent':
                    if self.auth.oauth_identifier:
                        args['authority'] = self.auth
                    else:
                        err_msg = "Statements cannot have a non-Oauth group as the authority"
                        raise exceptions.ParamError(err_msg)
                else:    
                    auth_args['name'] = self.auth.username
                    if self.auth.email.startswith("mailto:"):
                        auth_args['mbox'] = self.auth.email
                    else:
                        auth_args['mbox'] = "mailto:%s" % self.auth.email
                    args['authority'] = AgentManager(params=auth_args, create=True, define=self.define).Agent

        # Check if statement_id already exists, throw exception if it does
        # There will only be an ID when someone is performing a PUT
        if 'id' in stmt_data:
            try:
                models.Statement.objects.get(statement_id=stmt_data['id'])
            except models.Statement.DoesNotExist:
                self.validate_incoming_uuid(stmt_data['id'])
                args['statement_id'] = stmt_data['id']
            else:
                err_msg = "The Statement ID %s already exists in the system" % stmt_data['id']
                raise exceptions.ParamConflict(err_msg)
        
        if 'context' in stmt_data:
            args['context'] = self.populate_context(stmt_data)
        
        if 'result' in stmt_data:
            args['result'] = self.populate_result(stmt_data)

        #Save statement/substatement
        self.model_object = self.save_object_to_db(args)

        if 'attachments' in stmt_data:
            self.populate_attachments(stmt_data['attachments'], stmt_data.get('attachment_payloads', None))

class SubStatementManager(StatementManager):
    @transaction.commit_on_success
    def __init__(self, data, auth):        
        # Make sure object isn't another substatement
        if 'objectType' in data['object']:
            if data['object']['objectType'].lower() == 'substatement':
                err_msg = "SubStatements cannot be nested inside of other SubStatements"
                raise exceptions.ParamError(err_msg)
        StatementManager.__init__(self, data, auth)