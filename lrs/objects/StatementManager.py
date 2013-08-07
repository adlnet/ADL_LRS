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
    def __init__(self, data, auth=None, define=True):
        self.auth = auth
        self.define = define
        if not isinstance(data, dict):
            self.data = self.parse(data)
        else:
            self.data = data
        self.populate()

    #Make sure initial data being received is JSON
    def parse(self,data):
        try:
            params = json.loads(data)
        except Exception, e:
            err_msg = "Error parsing the Statement object. Expecting json. Received: %s which is %s" % (data,
                type(data))
            raise exceptions.ParamError(err_msg) 
        return params

    @transaction.commit_on_success
    def void_statement(self,stmt_id):
        # str_id = str(stmt_id)
        # Retrieve statement, check if the verb is 'voided' - if not then set the voided flag to true else return error 
        # since you cannot unvoid a statement and should just reissue the statement under a new ID.
        try:
            stmt = models.Statement.objects.get(statement_id=stmt_id)
        except models.Statement.DoesNotExist:
            err_msg = "Statement with ID %s does not exist" % stmt_id
            raise exceptions.IDNotFoundError(err_msg)
        
        # Check if it is already voided 
        if not stmt.voided:
            stmt.voided = True
            stmt.save()
            # Create statement ref
            stmt_ref = models.StatementRef.objects.create(ref_id=stmt_id)
            return stmt_ref
        else:
            err_msg = "Statement with ID: %s is already voided, cannot unvoid. Please re-issue the statement under a new ID." % stmt_id
            raise exceptions.Forbidden(err_msg)

    @transaction.commit_on_success
    # Save sub to DB
    def save_substatement_to_db(self):
        context_activity_types = ['parent', 'grouping', 'category', 'other']
        # Pop off any result extensions
        result_exts = self.data.pop('result_extensions', {})
        # Pop off any context extensions
        context_exts = self.data.pop('context_extensions', {})
        # Pop off any context activities
        con_act_data = self.data.pop('context_contextActivities',{})

        # Try to create SubStatement            
        # Delete objectType since it is not a field in the model
        del self.data['objectType']
        sub = models.SubStatement.objects.create(**self.data)
        
        # Save any result extensions
        for k, v in result_exts.items():
            models.SubStatementResultExtensions.objects.create(key=k, value=v, substatement=sub)

        # Save any context extensions
        for k, v in context_exts.items():              
            models.SubStatementContextExtensions.objects.create(key=k, value=v, substatement=sub)

        # Save context activities
        # Can have multiple groupings
        for con_act_group in con_act_data.items():
            ca = models.SubStatementContextActivity.objects.create(key=con_act_group[0], substatement=sub)
            # Incoming contextActivities can either be a list or dict
            if isinstance(con_act_group[1], list):
                for con_act in con_act_group[1]:
                    act = ActivityManager(con_act, auth=self.auth, define=self.define).Activity
                    ca.context_activity.add(act)
            else:
                act = ActivityManager(con_act_group[1], auth=self.auth, define=self.define).Activity
                ca.context_activity.add(act)
            ca.save()

        return sub

    @transaction.commit_on_success
    # Save statement to DB
    def save_statement_to_db(self):
        context_activity_types = ['parent', 'grouping', 'category', 'other']
        # Pop off any result extensions
        result_exts = self.data.pop('result_extensions', {})
        # Pop off any context extensions
        context_exts = self.data.pop('context_extensions', {})
        # Pop off any context activities
        con_act_data = self.data.pop('context_contextActivities',{})

        self.data['user'] = get_user_from_auth(self.auth)

        # Try to create statement
        stmt = models.Statement.objects.create(**self.data)
    
        # Save any result extensions
        for k, v in result_exts.items():
            models.StatementResultExtensions.objects.create(key=k, value=v, statement=stmt)

        # Save any context extensions
        for k, v in context_exts.items():              
            models.StatementContextExtensions.objects.create(key=k, value=v, statement=stmt)

        # Save context activities
        # Can have multiple groupings
        for con_act_group in con_act_data.items():
            ca = models.StatementContextActivity.objects.create(key=con_act_group[0], statement=stmt)
            # Incoming contextActivities can either be a list or dict
            if isinstance(con_act_group[1], list):
                for con_act in con_act_group[1]:
                    act = ActivityManager(con_act, auth=self.auth, define=self.define).Activity
                    ca.context_activity.add(act)
            else:
                act = ActivityManager(con_act_group[1], auth=self.auth, define=self.define).Activity
                ca.context_activity.add(act)
            ca.save()
        
        return stmt

    def populate_result(self):
        if 'result' in self.data:
            result = self.data['result']

            for k,v in result.iteritems():
                self.data['result_' + k] = v

            if 'result_score' in self.data:
                for k,v in self.data['result_score'].iteritems():
                    self.data['result_score_' + k] = v
                del self.data['result']['score']
                del self.data['result_score']

            del self.data['result']

    def create_attachment_displays_and_descs(self, displays, descriptions, attachment):        
        for display in displays.items():
            models.StatementAttachmentDisplay.objects.create(key=display[0], value=display[1],
                attachment=attachment)
    
        if descriptions:
            for desc in descriptions.items():
                models.StatementAttachmentDesc.objects.create(key=desc[0], value=desc[1],
                    attachment=attachment)

    @transaction.commit_on_success
    def update_attachment_displays_and_descs(self, attachment, displays, descriptions):
        # Grab existing display and desc keys for the attachment
        existing_display_keys = attachment.statementattachmentdisplay_set.all().values_list('key', flat=True)
        existing_desc_keys = attachment.statementattachmentdesc_set.all().values_list('key', flat=True)                

        # Iterate through each incoming display
        for d in displays.items():
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
            #  If the new key alerady exists, update that desc with the new value
            if de[0] in existing_desc_keys:
                existing_desc = attachment.statementattachmentdesc_set.get(key=de[0])
                existing_desc.value = de[1]
                existing_desc.save()
            #  Else it doesn't exist so just create it
            else:
                models.StatementAttachmentDesc.objects.create(key=de[0], value=de[1],
                    attachment=attachment)

    def save_attachment(self, attach):
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
        return attachment, created 

    @transaction.commit_on_success
    def populate_attachments(self, attachment_data, attachment_payloads):
        if attachment_data:
            # Iterate through each attachment
            for attach in attachment_data:
                # Pop displays and descs off
                displays = attach.pop('display')
                descriptions = attach.pop('description', None)

                # Get or create based on sha2
                if 'sha2' in attach:
                    attachment, created = self.save_attachment(attach)
                # If no sha2 there must be a fileUrl which is unique
                else:
                    try:
                        attachment = models.StatementAttachment.objects.get(fileUrl=attach['fileUrl'])
                        created = False
                    except Exception, e:
                        attachment = models.StatementAttachment.objects.create(**attach)
                        created = True

                # If it was just created, create the displays and descs
                if created:
                    self.create_attachment_displays_and_descs(displays, descriptions, attachment)

                # If have define permission and attachment already has existed
                if self.define and not created:
                    self.update_attachment_displays_and_descs(attachment, displays, descriptions)

                # Add each attach to the stmt
                self.model_object.attachments.add(attachment)

                # Delete everything in cache for this statement
                if attachment_payloads:
                    att_cache.delete_many(attachment_payloads)
            self.model_object.save()

    def populate_context(self):
        if 'context' in self.data:
            context = self.data['context']

            for k,v in context.iteritems():
                self.data['context_' + k] = v

            if 'context_instructor' in self.data:
                self.data['context_instructor'] = AgentManager(params=self.data['context_instructor'],
                    create=True, define=self.define).Agent
                
            if 'context_team' in self.data:
                self.data['context_team'] = AgentManager(params=self.data['context_team'],
                    create=True, define=self.define).Agent

            if 'context_statement' in self.data:
                self.data['context_statement'] = self.data['context_statement']['id']

            del self.data['context']
    
    def save_lang_map(self, lang_map, verb):
        k = lang_map[0]
        v = lang_map[1]

        # Save lang map
        language_map = models.VerbDisplay.objects.create(key=k, value=v, verb=verb)
        return language_map
    
    @transaction.commit_on_success
    def build_verb_object(self):
        incoming_verb = self.data['verb']
        verb_id = incoming_verb['id']

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
                # If incoming key doesn't already exist in verb's lang maps - add it
                if not verb_lang_map[0] in existing_lang_map_keys: 
                    lang_map = self.save_lang_map(verb_lang_map, verb_object)    
                else:
                    existing_verb_lang_map = verb_object.verbdisplay_set.get(key=verb_lang_map[0])
                    existing_verb_lang_map.value = verb_lang_map[1]
                    existing_verb_lang_map.save()
            verb_object.save()
        self.data['verb'] = verb_object

    def build_statement_object(self):
        statement_object_data = self.data['object']

        # If not specified, the object is assumed to be an activity
        if not 'objectType' in statement_object_data:
            statement_object_data['objectType'] = 'Activity'

        valid_agent_objects = ['Agent', 'Group']
        # Check to see if voiding statement
        if self.data['verb'].verb_id == 'http://adlnet.gov/expapi/verbs/voided':
            self.data['object_statementref'] = self.void_statement(statement_object_data['id'])
        else:
            # Check objectType, get object based on type
            if statement_object_data['objectType'] == 'Activity':
                self.data['object_activity'] = ActivityManager(statement_object_data,auth=self.auth, define=self.define).Activity
            elif statement_object_data['objectType'] in valid_agent_objects:
                self.data['object_agent'] = AgentManager(params=statement_object_data, create=True, define=self.define).Agent
            elif statement_object_data['objectType'] == 'SubStatement':
                self.data['object_substatement'] = SubStatementManager(statement_object_data, self.auth).model_object
            elif statement_object_data['objectType'] == 'StatementRef':
                if not models.Statement.objects.filter(statement_id=statement_object_data['id']).exists():
                    err_msg = "No statement with ID %s was found" % statement_object_data['id']
                    raise exceptions.IDNotFoundError(err_msg)
                else:
                    self.data['object_statementref'] = models.StatementRef.objects.create(ref_id=statement_object_data['id'])
        del self.data['object']

    def build_authority_object(self):
        if 'authority' in self.data:
            auth_data = self.data['authority']
            if auth_data['objectType'] == 'Group':
                self.data['authority'] = AgentManager(params=auth_data, create=False, 
                    define=self.define).Agent
            else:
                self.data['authority'] = AgentManager(params=auth_data, create=True, 
                    define=self.define).Agent

            # If they try using a non-oauth group that already exists-throw error
            if self.data['authority'].objectType == 'Group' and not self.data['authority'].oauth_identifier:
                err_msg = "Statements cannot have a non-Oauth group as the authority"
                raise exceptions.ParamError(err_msg)
        else:
            # Look at request from auth if not supplied in stmt_data.
            if self.auth:
                auth_args = {}
                if self.auth.__class__.__name__ == 'Agent':
                    if self.auth.oauth_identifier:
                        self.data['authority'] = self.auth
                    else:
                        err_msg = "Statements cannot have a non-Oauth group as the authority"
                        raise exceptions.ParamError(err_msg)
                else:    
                    auth_args['name'] = self.auth.username
                    if self.auth.email.startswith("mailto:"):
                        auth_args['mbox'] = self.auth.email
                    else:
                        auth_args['mbox'] = "mailto:%s" % self.auth.email
                    self.data['authority'] = AgentManager(params=auth_args, create=True, define=self.define).Agent

    def check_statement_id(self):
        if 'id' in self.data:
            stmt_id = self.data['id']
            if not models.Statement.objects.filter(statement_id=stmt_id).exists():
                self.data['statement_id'] = stmt_id
                del self.data['id']
            else:
                err_msg = "The Statement ID %s already exists in the system" % stmt_id
                raise exceptions.ParamConflict(err_msg)        

    #Once JSON is verified, populate the statement object
    def populate(self):
        if self.__class__.__name__ == 'StatementManager':
            #Set voided to default false
            self.data['voided'] = False

            # If non oauth group won't be sent with the authority key, so if it's a group it's a non
            # oauth group which isn't allowed to be the authority
            self.build_authority_object()

            # Check if statement_id already exists, throw exception if it does
            # There will only be an ID when someone is performing a PUT
            self.check_statement_id()
        
        self.build_verb_object()
        self.build_statement_object()

        self.data['actor'] = AgentManager(params=self.data['actor'], create=True, define=self.define).Agent

        self.populate_context()
        self.populate_result()

        attachment_data = self.data.pop('attachments', None)
        attachment_payloads = self.data.pop('attachment_payloads', None)
        
        if self.__class__.__name__ == 'StatementManager':
            #Save statement/substatement
            self.model_object = self.save_statement_to_db()
        else:
            self.model_object = self.save_substatement_to_db()

        self.populate_attachments(attachment_data, attachment_payloads)

class SubStatementManager(StatementManager):
    def __init__(self, data, auth):        
        StatementManager.__init__(self, data, auth)