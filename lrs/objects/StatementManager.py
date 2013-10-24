import json
import re
# from datetime import datetime
from django.core.exceptions import ValidationError
from django.db import transaction
from django.core.files.base import ContentFile
from django.core.cache import get_cache
# from django.utils.timezone import utc
from functools import wraps
from isodate.isoduration import parse_duration
from isodate.isoerror import ISO8601Error
from lrs import models, exceptions
from lrs.util import get_user_from_auth, uri, convert_to_utc
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
        self.data = data
        self.populate()

    @transaction.commit_on_success
    def void_statement(self,stmt_id):
        stmt = models.Statement.objects.get(statement_id=stmt_id)
        stmt.voided = True
        stmt.save()

        # Create statement ref
        stmt_ref = models.StatementRef.objects.create(ref_id=stmt_id)
        return stmt_ref

    @transaction.commit_on_success
    # Save sub to DB
    def save_substatement_to_db(self):
        context_activity_types = ['parent', 'grouping', 'category', 'other']

        # Pop off any context activities
        con_act_data = self.data.pop('context_contextActivities',{})

        # Try to create SubStatement            
        # Delete objectType since it is not a field in the model
        del self.data['objectType']
        sub = models.SubStatement.objects.create(**self.data)
        
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

        # Pop off any context activities
        con_act_data = self.data.pop('context_contextActivities',{})

        self.data['user'] = get_user_from_auth(self.auth)
        
        # Name of id field in models is statement_id
        if 'id' in self.data:
            self.data['statement_id'] = self.data['id']
            del self.data['id']

        # Try to create statement
        stmt = models.Statement.objects.create(**self.data)
    
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

    def save_attachment(self, attach):
        sha2 = attach['sha2']
        try:
            attachment = models.StatementAttachment.objects.get(sha2=sha2)
            created = False
        except models.StatementAttachment.DoesNotExist:
            attachment = models.StatementAttachment.objects.create(**attach)                
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

                # If have define permission and attachment already has existed
                if self.define and not created:
                    if attachment.display:
                        existing_displays = attachment.display
                    else:
                        existing_displays = {}

                    if attachment.description:
                        existing_descriptions = attachment.description
                    else:
                        existing_descriptions = {}

                    # Save displays
                    if 'display' in attach:
                        attachment.display = dict(existing_displays.items() + attach['display'].items())

                    if 'description' in attach:
                        attachment.description = dict(existing_descriptions.items() + attach['description'].items())
                    attachment.save()

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
    
    @transaction.commit_on_success
    def build_verb_object(self):
        incoming_verb = self.data['verb']
        verb_id = incoming_verb['id']

        # Get or create the verb
        verb_object, created = models.Verb.objects.get_or_create(verb_id=verb_id)

        # If existing, get existing keys
        if not created:
            if verb_object.display:
                existing_lang_maps = verb_object.display    
            else:
                existing_lang_maps = {}
        else:
            existing_lang_maps = {}

        # Save verb displays
        if 'display' in incoming_verb:
            verb_object.display = dict(existing_lang_maps.items() + incoming_verb['display'].items())
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
                self.data['object_statementref'] = models.StatementRef.objects.create(ref_id=statement_object_data['id'])
        del self.data['object']

    def build_authority_object(self):
        # Could still have no authority in stmt if HTTP_AUTH and OAUTH are disabled
        if 'authority' in self.data:
            self.data['authority'] = AgentManager(params=self.data['authority'], create=True, 
                define=self.define).Agent

    #Once JSON is verified, populate the statement object
    def populate(self):
        if self.__class__.__name__ == 'StatementManager':
            # If non oauth group won't be sent with the authority key, so if it's a group it's a non
            # oauth group which isn't allowed to be the authority
            self.build_authority_object()

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