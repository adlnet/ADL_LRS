from django.db import transaction
from django.core.files.base import ContentFile
from django.core.cache import get_cache

from .ActivityManager import ActivityManager
from ..models import Verb, Statement, StatementRef, StatementAttachment, SubStatement, Agent 

att_cache = get_cache('attachment_cache')

class StatementManager():
    def __init__(self, stmt_data, auth_info):
        # auth_info contains define, endpoint, user, and request authority
        if self.__class__.__name__ == 'StatementManager':
            # Full statement is for a statement only, same with authority
            self.set_authority(auth_info, stmt_data)
        self.populate(auth_info, stmt_data)

    def set_authority(self, auth_info, stmt_data):
        # Could still have no authority in stmt if HTTP_AUTH and OAUTH are disabled
        # Have to set auth in kwarg dict for Agent auth object to be saved in statement
        # Also have to save auth in full_statement kwargs for when returning exact statements
        # Set object auth as well for when creating other objects in a substatement
        if auth_info['agent']:
            stmt_data['authority'] = auth_info['agent']
            stmt_data['full_statement']['authority'] = auth_info['agent'].to_dict()
        # If no auth in request, look in statement
        else:
            # If authority is given in statement
            if 'authority' in stmt_data:
                auth_info['agent'] = stmt_data['authority'] = Agent.objects.retrieve_or_create(**stmt_data['full_statement']['authority'])[0]
            # Empty auth in request or statement
            else:
                auth_info['agent'] = None

    @transaction.commit_on_success
    def void_statement(self, stmt_id):
        stmt = Statement.objects.get(statement_id=stmt_id)
        stmt.voided = True
        stmt.save()
        # Create statement ref
        return StatementRef.objects.create(ref_id=stmt_id)

    @transaction.commit_on_success
    # Save sub to DB
    def create_substatement(self, auth_info, stmt_data):
        # Pop off any context activities
        con_act_data = stmt_data.pop('context_contextActivities',{})
        # Delete objectType since it is not a field in the model
        del stmt_data['objectType']
        sub = SubStatement.objects.create(**stmt_data)
        
        for con_act_group in con_act_data.items():
            # Incoming contextActivities can either be a list or dict    
            if isinstance(con_act_group[1], list):
                for con_act in con_act_group[1]:
                    act = ActivityManager(con_act, auth=auth_info['agent'], define=auth_info['define']).Activity
                    if con_act_group[0] == 'parent':
                        sub.context_ca_parent.add(act)
                    elif con_act_group[0] == 'grouping':
                        sub.context_ca_grouping.add(act)
                    elif con_act_group[0] == 'category':
                        sub.context_ca_category.add(act)
                    else:
                        sub.context_ca_other.add(act)
            else:        
                act = ActivityManager(con_act_group[1], auth=auth_info['agent'], define=auth_info['define']).Activity
                if con_act_group[0] == 'parent':
                    sub.context_ca_parent.add(act)
                elif con_act_group[0] == 'grouping':
                    sub.context_ca_grouping.add(act)
                elif con_act_group[0] == 'category':
                    sub.context_ca_category.add(act)
                else:
                    sub.context_ca_other.add(act)
            sub.save()
        return sub

    @transaction.commit_on_success
    # Save statement to DB
    def create_statement(self, auth_info, stmt_data):
        # Pop off any context activities
        con_act_data = stmt_data.pop('context_contextActivities',{})
        stmt_data['user'] = auth_info['user']
        # Name of id field in models is statement_id
        if 'id' in stmt_data:
            stmt_data['statement_id'] = stmt_data['id']
            del stmt_data['id']
        # Try to create statement
        stmt = Statement.objects.create(**stmt_data)

        for con_act_group in con_act_data.items():
            # Incoming contextActivities can either be a list or dict    
            if isinstance(con_act_group[1], list):
                for con_act in con_act_group[1]:
                    act = ActivityManager(con_act, auth=auth_info['agent'], define=auth_info['define']).Activity
                    if con_act_group[0] == 'parent':
                        stmt.context_ca_parent.add(act)
                    elif con_act_group[0] == 'grouping':
                        stmt.context_ca_grouping.add(act)
                    elif con_act_group[0] == 'category':
                        stmt.context_ca_category.add(act)
                    else:
                        stmt.context_ca_other.add(act)
            else:        
                act = ActivityManager(con_act_group[1], auth=auth_info['agent'], define=auth_info['define']).Activity
                if con_act_group[0] == 'parent':
                    stmt.context_ca_parent.add(act)
                elif con_act_group[0] == 'grouping':
                    stmt.context_ca_grouping.add(act)
                elif con_act_group[0] == 'category':
                    stmt.context_ca_category.add(act)
                else:
                    stmt.context_ca_other.add(act)
            stmt.save()
        return stmt

    def build_result(self, stmt_data):
        if 'result' in stmt_data:
            result = stmt_data['result']
            for k,v in result.iteritems():
                stmt_data['result_' + k] = v
            if 'result_score' in stmt_data:
                for k,v in stmt_data['result_score'].iteritems():
                    stmt_data['result_score_' + k] = v
                del stmt_data['result']['score']
                del stmt_data['result_score']
            del stmt_data['result']

    def create_attachment(self, attach):
        sha2 = attach['sha2']
        try:
            attachment = StatementAttachment.objects.get(sha2=sha2)
            created = False
        except StatementAttachment.DoesNotExist:
            attachment = StatementAttachment.objects.create(**attach)                
            created = True
            # Since there is a sha2, there must be a payload cached
            # Decode payload from msg object saved in cache and create ContentFile from raw data
            raw_payload = att_cache.get(sha2)
            try:
                payload = ContentFile(raw_payload)
            except Exception, e:
                raise e    
            # Save ContentFile payload to attachment model object
            attachment.payload.save(sha2, payload)
        return attachment, created 

    @transaction.commit_on_success
    def create_attachments(self, user_info, attachment_data, attachment_payloads):
        if attachment_data:
            # Iterate through each attachment
            for attach in attachment_data:
                # Get or create based on sha2
                if 'sha2' in attach:
                    attachment, created = self.create_attachment(attach)
                # If no sha2 there must be a fileUrl which is unique
                else:
                    try:
                        attachment = StatementAttachment.objects.get(fileUrl=attach['fileUrl'])
                        created = False
                    except Exception:
                        attachment = StatementAttachment.objects.create(**attach)
                        created = True
                # If have define permission and attachment already has existed
                if user_info['define'] and not created:
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

    def build_context(self, stmt_data):
        if 'context' in stmt_data:
            context = stmt_data['context']
            for k,v in context.iteritems():
                stmt_data['context_' + k] = v
            if 'context_instructor' in stmt_data:
                stmt_data['context_instructor'] = Agent.objects.retrieve_or_create(**stmt_data['context_instructor'])[0]
            if 'context_team' in stmt_data:
                stmt_data['context_team'] = Agent.objects.retrieve_or_create(**stmt_data['context_team'])[0]
            if 'context_statement' in stmt_data:
                stmt_data['context_statement'] = stmt_data['context_statement']['id']
            del stmt_data['context']
    
    @transaction.commit_on_success
    def build_verb(self, stmt_data):
        incoming_verb = stmt_data['verb']
        verb_id = incoming_verb['id']
        # Get or create the verb
        verb_object, created = Verb.objects.get_or_create(verb_id=verb_id)
        # If existing, get existing keys
        existing_lang_maps = {}
        if not created and verb_object.display:
            existing_lang_maps = verb_object.display    

        # Save verb displays
        if 'display' in incoming_verb:
            verb_object.display = dict(existing_lang_maps.items() + incoming_verb['display'].items())
            verb_object.save()
        stmt_data['verb'] = verb_object

    def build_statement_object(self, auth_info, stmt_data):
        statement_object_data = stmt_data['object']
        # If not specified, the object is assumed to be an activity
        if not 'objectType' in statement_object_data:
            statement_object_data['objectType'] = 'Activity'
        valid_agent_objects = ['Agent', 'Group']
        # Check to see if voiding statement
        if stmt_data['verb'].verb_id == 'http://adlnet.gov/expapi/verbs/voided':
            stmt_data['object_statementref'] = self.void_statement(statement_object_data['id'])
        else:
            # Check objectType, get object based on type
            if statement_object_data['objectType'] == 'Activity':
                stmt_data['object_activity'] = ActivityManager(statement_object_data, auth=auth_info['agent'],
                    define=auth_info['define']).Activity
            elif statement_object_data['objectType'] in valid_agent_objects:
                stmt_data['object_agent'] = Agent.objects.retrieve_or_create(**statement_object_data)[0]
            elif statement_object_data['objectType'] == 'SubStatement':
                stmt_data['object_substatement'] = SubStatementManager(statement_object_data, auth_info).model_object
            elif statement_object_data['objectType'] == 'StatementRef':
                stmt_data['object_statementref'] = StatementRef.objects.create(ref_id=statement_object_data['id'])
        del stmt_data['object']

    # Once JSON is verified, populate the statement object
    def populate(self, auth_info, stmt_data):
        if self.__class__.__name__ == 'StatementManager':
            stmt_data['voided'] = False
        
        self.build_verb(stmt_data)
        self.build_statement_object(auth_info, stmt_data)
        stmt_data['actor'] = Agent.objects.retrieve_or_create(**stmt_data['actor'])[0]
        self.build_context(stmt_data)
        self.build_result(stmt_data)
        attachment_data = stmt_data.pop('attachments', None)
        attachment_payloads = stmt_data.pop('attachment_payloads', None)
        
        if self.__class__.__name__ == 'StatementManager':
            #Save statement/substatement
            self.model_object = self.create_statement(auth_info, stmt_data)
        else:
            self.model_object = self.create_substatement(auth_info, stmt_data)
        self.create_attachments(auth_info, attachment_data, attachment_payloads)

class SubStatementManager(StatementManager):
    def __init__(self, substmt_data, auth_info):        
        StatementManager.__init__(self, substmt_data, auth_info)