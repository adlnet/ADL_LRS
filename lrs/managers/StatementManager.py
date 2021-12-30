from django.core.files.base import ContentFile
import uuid

from django.core.cache import caches

from .ActivityManager import ActivityManager
from ..models import Verb, Statement, StatementAttachment, SubStatement, Agent
from ..utils import convert_to_datetime_object

att_cache = caches['attachment_cache']


class StatementManager():

    def __init__(self, stmt_data, auth_info, payload_sha2s):
        # auth_info contains define, endpoint, user, and request authority
        if self.__class__.__name__ == 'StatementManager':
            # Full statement is for a statement only, same with authority
            self.set_authority(auth_info, stmt_data)
        self.populate(auth_info, stmt_data, payload_sha2s)

    def set_authority(self, auth_info, stmt_data):
        # Could still have no authority in stmt if HTTP_AUTH and OAUTH are disabled
        # Have to set auth in kwarg dict for Agent auth object to be saved in statement
        # Also have to save auth in full_statement kwargs for when returning exact statements
        # Set object auth as well for when creating other objects in a
        # substatement
        if auth_info['agent']:
            stmt_data['authority'] = auth_info['agent']
            stmt_data['full_statement'][
                'authority'] = auth_info['agent'].to_dict()
        # If no auth in request, look in statement
        else:
            # If authority is given in statement
            if 'authority' in stmt_data:
                auth_info['agent'] = stmt_data['authority'] = Agent.objects.retrieve_or_create(
                    **stmt_data['full_statement']['authority'])[0]
            # Empty auth in request or statement
            else:
                auth_info['agent'] = None

    def build_context_activities(self, stmt, auth_info, con_act_data):
        for con_act_group in list(con_act_data.items()):
            # Incoming contextActivities can either be a list or dict
            if isinstance(con_act_group[1], list):
                for con_act in con_act_group[1]:
                    act = ActivityManager(con_act, auth=auth_info[
                                          'agent'], define=auth_info['define']).activity
                    if con_act_group[0] == 'parent':
                        stmt.context_ca_parent.add(act)
                    elif con_act_group[0] == 'grouping':
                        stmt.context_ca_grouping.add(act)
                    elif con_act_group[0] == 'category':
                        stmt.context_ca_category.add(act)
                    else:
                        stmt.context_ca_other.add(act)
            else:
                act = ActivityManager(con_act_group[1], auth=auth_info[
                                      'agent'], define=auth_info['define']).activity
                if con_act_group[0] == 'parent':
                    stmt.context_ca_parent.add(act)
                elif con_act_group[0] == 'grouping':
                    stmt.context_ca_grouping.add(act)
                elif con_act_group[0] == 'category':
                    stmt.context_ca_category.add(act)
                else:
                    stmt.context_ca_other.add(act)
        stmt.save()

    def build_substatement(self, auth_info, stmt_data):
        # Pop off any context activities
        con_act_data = stmt_data.pop('context_contextActivities', {})
        # Delete objectType since it is not a field in the model
        del stmt_data['objectType']
        sub = SubStatement.objects.create(**stmt_data)
        if con_act_data:
            self.build_context_activities(sub, auth_info, con_act_data)
        return sub

    def build_statement(self, auth_info, stmt_data):
        stmt_data['stored'] = convert_to_datetime_object(stmt_data['stored'])
        # Pop off any context activities
        con_act_data = stmt_data.pop('context_contextActivities', {})
        stmt_data['user'] = auth_info['user']
        # Name of id field in models is statement_id
        if 'id' in stmt_data:
            stmt_data['statement_id'] = stmt_data['id']
            del stmt_data['id']
        # Try to create statement
        stmt = Statement.objects.create(**stmt_data)
        if con_act_data:
            self.build_context_activities(stmt, auth_info, con_act_data)
        return stmt

    def build_result(self, stmt_data):
        if 'result' in stmt_data:
            result = stmt_data['result']
            for k, v in result.items():
                stmt_data['result_' + k] = v
            if 'result_score' in stmt_data:
                for k, v in stmt_data['result_score'].items():
                    stmt_data['result_score_' + k] = v
                del stmt_data['result']['score']
                del stmt_data['result_score']
            del stmt_data['result']

    def build_attachments(self, user_info, attachment_data, payload_sha2s):
        # Iterate through each attachment
        for attach in attachment_data:
            sha2 = attach.get('sha2', None)
            attachment = StatementAttachment.objects.create(
                canonical_data=attach)
            if sha2:
                if payload_sha2s and sha2 in payload_sha2s:
                    raw_payload = att_cache.get(sha2)
                    try:
                        payload = ContentFile(raw_payload)
                    except Exception as e:
                        raise e
                    attachment.payload.save(sha2, payload)
            attachment.statement = self.model_object
            attachment.save()

    def build_context(self, stmt_data):
        if 'context' in stmt_data:
            context = stmt_data['context']
            for k, v in context.items():
                stmt_data['context_' + k] = v
            if 'context_instructor' in stmt_data:
                stmt_data['context_instructor'] = Agent.objects.retrieve_or_create(
                    **stmt_data['context_instructor'])[0]
            if 'context_team' in stmt_data:
                stmt_data['context_team'] = Agent.objects.retrieve_or_create(
                    **stmt_data['context_team'])[0]
            if 'context_statement' in stmt_data:
                stmt_data['context_statement'] = stmt_data[
                    'context_statement']['id']
            del stmt_data['context']

    def build_verb(self, stmt_data):
        incoming_verb = stmt_data['verb']
        verb_id = incoming_verb['id']
        # Get or create the verb
        verb_object, created = Verb.objects.get_or_create(verb_id=verb_id)
        # If existing, get existing keys
        existing_lang_maps = {}
        if not created:
            if 'display' in verb_object.canonical_data:
                existing_lang_maps = verb_object.canonical_data['display']

        # Save verb displays
        if 'display' in incoming_verb:
            verb_object.canonical_data['display'] = dict(
                list(existing_lang_maps.items()) + list(incoming_verb['display'].items()))

        verb_object.canonical_data['id'] = verb_id
        verb_object.save()
        stmt_data['verb'] = verb_object

    def build_statement_object(self, auth_info, stmt_data):
        statement_object_data = stmt_data['object']
        valid_agent_objects = ['Agent', 'Group']
        # If not specified, the object is assumed to be an activity
        if 'objectType' not in statement_object_data or statement_object_data['objectType'] == 'Activity':
            statement_object_data['objectType'] = 'Activity'
            stmt_data['object_activity'] = ActivityManager(statement_object_data, auth=auth_info['agent'],
                                                           define=auth_info['define']).activity
        elif statement_object_data['objectType'] in valid_agent_objects:
            stmt_data['object_agent'] = Agent.objects.retrieve_or_create(
                **statement_object_data)[0]
        elif statement_object_data['objectType'] == 'SubStatement':
            stmt_data['object_substatement'] = SubStatementManager(
                statement_object_data, auth_info).model_object
        elif statement_object_data['objectType'] == 'StatementRef':
            stmt_data['object_statementref'] = uuid.UUID(
                statement_object_data['id'])
        del stmt_data['object']

    def populate(self, auth_info, stmt_data, payload_sha2s):
        if self.__class__.__name__ == 'StatementManager':
            stmt_data['voided'] = False

        self.build_verb(stmt_data)
        self.build_statement_object(auth_info, stmt_data)
        stmt_data['actor'] = Agent.objects.retrieve_or_create(
            **stmt_data['actor'])[0]
        self.build_context(stmt_data)
        self.build_result(stmt_data)
        # Substatement could not have timestamp
        if 'timestamp' in stmt_data:
            stmt_data['timestamp'] = convert_to_datetime_object(stmt_data[
                                                                'timestamp'])
        attachment_data = stmt_data.pop('attachments', None)

        if self.__class__.__name__ == 'StatementManager':
            # Save statement/substatement
            self.model_object = self.build_statement(auth_info, stmt_data)
        else:
            self.model_object = self.build_substatement(auth_info, stmt_data)
        if attachment_data:
            self.build_attachments(auth_info, attachment_data, payload_sha2s)


class SubStatementManager(StatementManager):

    def __init__(self, substmt_data, auth_info):
        StatementManager.__init__(self, substmt_data, auth_info, None)
