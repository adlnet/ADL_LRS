import re
from isodate.isodatetime import parse_datetime
from rfc3987 import parse as iriparse
from uuid import UUID

from . import convert_to_datatype
from ..exceptions import ParamError

statement_allowed_fields = ['id', 'actor', 'verb', 'object', 'result', 'stored',
                            'context', 'timestamp', 'authority', 'version', 'attachments']
statement_required_fields = ['actor', 'verb', 'object']

attachment_allowed_fields = ['usageType', 'display',
                             'description', 'contentType', 'length', 'sha2', 'fileUrl']
attachment_required_fields = ['usageType', 'display', 'contentType', 'length']

agent_ifis_can_only_be_one = ['mbox', 'mbox_sha1sum', 'openid', 'account']
agent_allowed_fields = ['objectType', 'name', 'member',
                        'mbox', 'mbox_sha1sum', 'openid', 'account']

account_fields = ['homePage', 'name']

verb_allowed_fields = ['id', 'display']

ref_fields = ['id', 'objectType']

activity_allowed_fields = ['objectType', 'id', 'definition']

act_def_allowed_fields = ['name', 'description', 'type', 'moreInfo', 'extensions',
                          'interactionType', 'correctResponsesPattern', 'choices', 'scale', 'source', 'target', 'steps']

int_act_fields = ['id', 'description']

sub_allowed_fields = ['actor', 'verb', 'object',
                      'result', 'context', 'timestamp', "objectType"]
sub_required_fields = ['actor', 'verb', 'object']

result_allowed_fields = ['score', 'success',
                         'completion', 'response', 'duration', 'extensions']

score_allowed_fields = ['scaled', 'raw', 'min', 'max']

context_allowed_fields = ['registration', 'instructor', 'team', 'contextActivities',
                          'revision', 'platform', 'language', 'statement', 'extensions']



class StatementValidator():

    def __init__(self, data=None):
        # If incoming is a string, ast eval it (exception will be caught with
        # whatever is calling validator)
        if data:
            try:
                if isinstance(data, bytes):
                    try:
                        data = data.decode("utf-8")
                    except Exception:
                        self.return_error("There is an encoding problem with the statement")
                    else:
                        data = data.replace('\r', '').replace('\n', '')
                self.data = convert_to_datatype(data)
            except SyntaxError as se:
                self.return_error(str(se))
            except Exception as e:
                self.return_error(str(e))

    def validate(self):
        # If list, validate each stmt inside
        if isinstance(self.data, list):
            for st in self.data:
                self.validate_statement(st)
            return "All Statements are valid"
        elif isinstance(self.data, dict):
            self.validate_statement(self.data)
            return "Statement is valid"
        else:
            self.return_error(f"There are no statements to validate, payload: {self.data}")

    def return_error(self, err_msg):
        raise ParamError(err_msg)

    def validate_email(self, email):
        if isinstance(email, str):
            if email.startswith("mailto:"):
                email_re = re.compile("[^@]+@[^@]+\.[^@]+")
                if not email_re.match(email[7:]):
                    self.return_error(
                        "mbox value %s is not a valid email" % email)
            else:
                self.return_error(
                    "mbox value %s did not start with mailto:" % email)
        else:
            self.return_error("mbox value must be a string type")

    def validate_language(self, lang, field):
        if not isinstance(lang, str):
            self.return_error(
                "language %s is not valid in %s" % (lang, field))
        lang_parts = lang.split('-')
        for idx, part in enumerate(lang_parts):
            # If part exists and is only alpha/numeric
            if part and re.match("^[A-Za-z0-9]*$", part):
                if len(part) > 8:
                    self.return_error(
                        "language %s is not valid in %s" % (lang, field))
            else:
                self.return_error(
                    "language %s is not valid in %s" % (lang, field))        

    def validate_lang_map(self, lang_map, field):
        for lang in lang_map:
            self.validate_language(lang, field)


    def validate_dict_values(self, values, field):
        for v in values:
            if not v:
                self.return_error("%s contains a null value" % field)

    def validate_email_sha1sum(self, sha1sum):
        if isinstance(sha1sum, str):
            sha1sum_re = re.compile('([a-fA-F\d]{40}$)')
            if not sha1sum_re.match(sha1sum):
                self.return_error(
                    "mbox_sha1sum value [%s] is not a valid sha1sum" % sha1sum)
        else:
            self.return_error("mbox_sha1sum value must be a string type")

    def validate_iri(self, iri_value, field):
        if isinstance(iri_value, str):
            try:
                iriparse(iri_value, rule='IRI')
            except Exception:
                self.return_error(
                    "%s with value %s was not a valid IRI" % (field, iri_value))
        else:
            self.return_error("%s must be a string type" % field)

    def validate_uuid(self, uuid, field):
        if isinstance(uuid, str):
            try:
                val = UUID(uuid, version=4)
            except ValueError:
                self.return_error(
                    "%s - %s is not a valid UUID" % (field, uuid))
            return val.hex == uuid
        else:
            self.return_error("%s must be a string type" % field)

    def check_if_dict(self, obj, field):
        if not isinstance(obj, dict):
            self.return_error(
                "%s is not a properly formatted dictionary" % field)

    def check_if_list(self, obj, field):
        if not isinstance(obj, list):
            self.return_error("%s is not a properly formatted array" % field)

    def check_allowed_fields(self, allowed, obj, obj_name):
        # Check for fields that aren't in spec
        failed_list = [x for x in list(obj.keys()) if x not in allowed]
        if failed_list:
            self.return_error("Invalid field(s) found in %s - %s" %
                              (obj_name, ', '.join(failed_list)))

    def check_required_fields(self, required, obj, obj_name):
        for field in required:
            if field not in obj:
                self.return_error("%s is missing in %s" % (field, obj_name))

    def validate_statement(self, stmt):
        # Ensure dict was submitted as stmt and check allowed and required
        # fields
        self.check_if_dict(stmt, "Statement")
        self.check_allowed_fields(statement_allowed_fields, stmt, "Statement")
        self.check_required_fields(
            statement_required_fields, stmt, "Statement")

        # If version included in stmt (usually in header instead) make sure it
        # is 1.0.0 +
        if 'version' in stmt:
            if isinstance(stmt['version'], str):
                version_regex = re.compile("^1\.0(\.\d+)?$")
                if not version_regex.match(stmt['version']):
                    self.return_error(
                        "%s is not a supported version" % stmt['version'])
            else:
                self.return_error("Version must be a string")

        # If id included, make sure it is a valid UUID
        if 'id' in stmt:
            self.validate_uuid(stmt['id'], 'Statement id')

        # If timestamp included, make sure a valid date can be parsed from it
        if 'timestamp' in stmt:
            timestamp = stmt['timestamp']
            try:
                parse_datetime(timestamp)

                # Reject statements that don't comply with ISO 8601 offsets
                if timestamp.endswith("-00") or timestamp.endswith("-0000") or timestamp.endswith("-00:00"):
                    self.return_error(
                        "Timestamp error - Statement Timestamp Illegal offset (-00, -0000, or -00:00) %s" % timestamp)

            except Exception as e:
                self.return_error(
                    "Timestamp error - There was an error while parsing the date from %s -- Error: %s" % (timestamp, str(e)))

        # If stored included, make sure a valid date can be parsed from it
        if 'stored' in stmt:
            stored = stmt['stored']
            try:
                parse_datetime(stored)
            except Exception as e:
                self.return_error(
                    "Stored error - There was an error while parsing the date from %s -- Error: %s" % (stored, str(e)))

        # Validate the actor and verb
        self.validate_agent(stmt['actor'], 'actor')
        self.validate_verb(stmt['verb'], stmt['object'])

        # Validate the object
        stmt_object = stmt['object']
        self.validate_object(stmt_object)

        # If the object is validated and has no objectType, set to Activity
        if 'objectType' not in stmt_object:
            stmt['object']['objectType'] = 'Activity'

        # If result is included, validate it
        if 'result' in stmt:
            self.validate_result(stmt['result'])

        # If context is included, validate it
        if 'context' in stmt:
            self.validate_context(stmt['context'], stmt_object)

        # If authority is included, validate it
        if 'authority' in stmt:
            self.validate_agent(stmt['authority'], 'authority')
            if 'objectType' in stmt['authority'] and stmt['authority']['objectType'] == 'Group':
                self.validate_authority_group(stmt['authority'])

        # If attachments is included, validate it
        if 'attachments' in stmt:
            self.validate_attachments(stmt['attachments'])

    def validate_authority_group(self, authority):
        if len(authority['member']) != 2:
            self.return_error(
                "Groups representing authorities must only contain 2 members")

        if list(set(agent_ifis_can_only_be_one) & set(authority.keys())):
            self.return_error(
                "Groups representing authorities must not contain an inverse functional identifier")

    def validate_attachments(self, attachments):
        # Ensure attachments is a list
        self.check_if_list(attachments, "Attachments")

        for attach in attachments:
            # For each attachment, check allowed and required fields
            self.check_allowed_fields(
                attachment_allowed_fields, attach, "Attachment")
            self.check_required_fields(
                attachment_required_fields, attach, "Attachment")

            # Validate usageType
            self.validate_iri(attach['usageType'], 'Attachments usageType')

            # If fileUrl included, validate it
            if 'fileUrl' in attach:
                self.validate_iri(attach['fileUrl'], 'Attachments fileUrl')

            if 'sha2' not in attach:
                self.return_error(
                    "Attachment sha2 is required")
            else:
                # Ensure sha2 is submitted as string
                if not isinstance(attach['sha2'], str):
                    self.return_error("Attachment sha2 must be a string")
                sha2_re =  re.compile("^[a-f0-9]{64}$")
                if not sha2_re.match(attach['sha2']):
                    self.return_error("Not a valid sha2 inside the statement")

            # Ensure length is an int
            if not isinstance(attach['length'], int):
                self.return_error("Attachment length must be an integer")

            # Ensure contentType is submitted as a string
            if not isinstance(attach['contentType'], str):
                self.return_error("Attachment contentType must be a string")

            # Ensure display is a dict (language map)
            self.check_if_dict(attach['display'], "Attachment display")
            self.validate_lang_map(
                list(attach['display'].keys()), "attachment display")

            # If description included, ensure it is a dict (language map)
            if 'description' in attach:
                self.check_if_dict(
                    attach['description'], "Attachment description")
                self.validate_lang_map(
                    list(attach['description'].keys()), "attachment description")

    def validate_extensions(self, extensions, field):
        # Ensure incoming extensions is a dict
        self.check_if_dict(extensions, "%s extensions" % field)

        # Ensure each key in extensions is a valid IRI
        for k, v in list(extensions.items()):
            self.validate_iri(k, field)

    def validate_agent(self, agent, placement):
        # Ensure incoming agent is a dict and check allowed fields
        self.check_if_dict(agent, "Agent in %s" % placement)
        self.check_allowed_fields(agent_allowed_fields, agent, "Agent/Group")
        # If the agent is the object of a stmt, the objectType must be present
        if placement == 'object' and 'objectType' not in agent:
            self.return_error(
                "objectType must be set when using an Agent as the object of a statement")
        # If the agent is not the object of a stmt and objectType is given, it
        # must be Agent or Group
        elif placement != 'object' and 'objectType' in agent:
            if agent['objectType'] != 'Agent' and agent['objectType'] != 'Group':
                self.return_error(
                    "An agent's objectType must be either Agent or Group if given")
        # If the agent is not the object of a stmt and objectType is not given,
        # set it to Agent
        elif placement != 'object' and 'objectType' not in agent:
            agent['objectType'] = 'Agent'
        # Agent must have only one inverse functional identifier (Group may be Anonymous Group where no IFI is
        # required)
        ifis = [a for a in agent_ifis_can_only_be_one if agent.get(
            a, None) is not None]
        if agent['objectType'] == 'Agent' and len(ifis) != 1:
            self.return_error("One and only one of %s may be supplied with an Agent" % ", ".join(
                agent_ifis_can_only_be_one))
        elif agent['objectType'] == 'Group' and len(ifis) > 1:
            self.return_error("None or one and only one of %s may be supplied with a Group" % ", ".join(
                agent_ifis_can_only_be_one))

        if agent['objectType'] == 'Agent':
            # If agent, if name given, ensure name is string and validate the
            # IFI
            if 'name' in agent and not isinstance(agent['name'], str):
                self.return_error(
                    f"If name is given in Agent, it must be a string -- got {type(agent['name'])}{agent['name']}")
            self.validate_ifi(ifis[0], agent[ifis[0]])
        else:
            # If group, if name given, ensure name is string
            if 'name' in agent and not isinstance(agent['name'], str):
                self.return_error(
                    "If name is given in Group, it must be a string")

            # If no IFIs, it is an anonymous group which must contain the
            # member property
            if not ifis:
                # No ifi means anonymous group - must have member
                if 'member' not in agent:
                    self.return_error("Anonymous groups must contain member")
                else:
                    self.validate_members(agent)
            else:
                # IFI given, validate it
                self.validate_ifi(ifis[0], agent[ifis[0]])
                if 'member' in agent:
                    self.validate_members(agent)

    def validate_members(self, agent):
        # Ensure member list is array
        members = agent['member']
        self.check_if_list(members, "Members")
        if not members:
            self.return_error("Member property must contain agents")
        # Make sure no member of group is another group
        object_types = [t['objectType'] for t in members if 'objectType' in t]
        if 'Group' in object_types:
            self.return_error('Group member value cannot be other groups')

        # Validate each member in group
        for agent in members:
            self.validate_agent(agent, 'member')

    def validate_ifi(self, ifis, ifi_value):
        # Validate each IFI accordingly
        if ifis == 'mbox':
            self.validate_email(ifi_value)
        elif ifis == 'mbox_sha1sum':
            self.validate_email_sha1sum(ifi_value)
        elif ifis == 'openid':
            self.validate_iri(ifi_value, 'openid')
        elif ifis == 'account':
            self.validate_account(ifi_value)

    def validate_account(self, account):
        # Ensure incoming account is a dict and check allowed and required
        # fields
        self.check_if_dict(account, "Account")
        self.check_allowed_fields(account_fields, account, "Account")
        self.check_required_fields(account_fields, account, "Account")

        # Ensure homePage is a valid IRI
        self.validate_iri(account['homePage'], 'homePage')

        # Ensure name is a string
        if not isinstance(account['name'], str):
            self.return_error("account name must be a string")

    def validate_verb(self, verb, stmt_object=None):
        # Ensure incoming verb is a dict and check allowed fields
        self.check_if_dict(verb, "Verb")
        self.check_allowed_fields(verb_allowed_fields, verb, "Verb")

        # Verb must conatin id - then validate it
        if 'id' not in verb:
            self.return_error('Verb must contain an id')
        self.validate_iri(verb['id'], 'Verb id')

        if verb['id'] == "http://adlnet.gov/expapi/verbs/voided":
            if stmt_object['objectType']:
                if stmt_object['objectType'] != "StatementRef":
                    raise ParamError(
                        "Statement with voided verb must have StatementRef as objectType")
            else:
                raise ParamError(
                    "Statement with voided verb must have StatementRef as objectType")

        # If display given, ensure it's a dict (language map)
        if 'display' in verb:
            self.check_if_dict(verb['display'], "Verb display")
            self.validate_lang_map(list(verb['display'].keys()), "verb display")
            self.validate_dict_values(list(verb['display'].values()), "verb display")

    def validate_object(self, stmt_object):
        # Ensure incoming object is a dict
        self.check_if_dict(stmt_object, "Object")

        # If objectType is not given or is Activity it is an Activity
        # Validate the rest accordingly
        if 'objectType' not in stmt_object or stmt_object['objectType'] == 'Activity':
            self.validate_activity(stmt_object)
        elif stmt_object['objectType'] == 'Agent' or stmt_object['objectType'] == 'Group':
            self.validate_agent(stmt_object, 'object')
        elif stmt_object['objectType'] == 'SubStatement':
            self.validate_substatement(stmt_object)
        elif stmt_object['objectType'] == 'StatementRef':
            self.validate_statementref(stmt_object)
        else:
            self.return_error(
                "The objectType in the statement's object is not valid - %s" % stmt_object['objectType'])

    def validate_statementref(self, ref):
        # Ensure incoming StatementRef is a dictionary an check allowed and
        # required fields
        self.check_if_dict(ref, "StatementRef")

        # objectType must be StatementRef
        if ref['objectType'] != "StatementRef":
            self.return_error(
                "StatementRef objectType must be set to 'StatementRef'")

        self.check_allowed_fields(ref_fields, ref, "StatementRef")
        self.check_required_fields(ref_fields, ref, "StatementRef")

        # Ensure id is a valid UUID
        self.validate_uuid(ref['id'], 'StatementRef id')

    def validate_activity(self, activity):
        # Ensure incoming activity is a dict and check allowed fields
        self.check_if_dict(activity, "Activity")
        self.check_allowed_fields(
            activity_allowed_fields, activity, "Activity")

        # Id must be present
        if 'id' not in activity:
            self.return_error("Id field must be present in an Activity")

        # Id must be valid IRI
        self.validate_iri(activity['id'], "Activity id")

        # If definition included, validate it
        if 'definition' in activity:
            self.validate_activity_definition(activity['definition'])

    def validate_activity_definition(self, definition):
        # Ensure incoming def is a dict and check allowed fields
        self.check_if_dict(definition, "Activity definition")

        self.check_allowed_fields(
            act_def_allowed_fields, definition, "Activity definition")

        # If name or description included, ensure it is a dict (language map)
        if 'name' in definition:
            self.check_if_dict(definition['name'], "Activity definition name")
            self.validate_lang_map(
                list(definition['name'].keys()), "activity definition name")
        if 'description' in definition:
            self.check_if_dict(
                definition['description'], "Activity definition description")
            self.validate_lang_map(
                list(definition['description'].keys()), "activity definition description")

        # If type or moreInfo included, ensure it is valid IRI
        if 'type' in definition:
            self.validate_iri(definition['type'], 'Activity definition type')
        if 'moreInfo' in definition:
            self.validate_iri(definition['moreInfo'],
                              'Activity definition moreInfo')

        interactionType = None
        # If interactionType included, ensure it is a string
        if 'interactionType' in definition:
            if not isinstance(definition['interactionType'], str):
                self.return_error(
                    "Activity definition interactionType must be a string")

            scorm_interaction_types = ['true-false', 'choice', 'fill-in', 'long-fill-in', 'matching', 'performance',
                                       'sequencing', 'likert', 'numeric', 'other']

            # Check if valid SCORM interactionType
            if definition['interactionType'] not in scorm_interaction_types:
                self.return_error("Activity definition interactionType %s is not valid" % definition[
                                  'interactionType'])

            interactionType = definition['interactionType']
        # If crp included, ensure they are strings in a list
        if 'correctResponsesPattern' in definition:
            if not interactionType:
                self.return_error("interactionType must be given when correctResponsesPattern is used")
            self.check_if_list(definition[
                               'correctResponsesPattern'], "Activity definition correctResponsesPattern")
            for answer in definition['correctResponsesPattern']:
                # For each answer, ensure it is a string
                if not isinstance(answer, str):
                    self.return_error(
                        "Activity definition correctResponsesPattern answers must all be strings")

        if ('choices' in definition or 'scale' in definition or 'source' in definition \
            or 'target' in definition or 'steps' in definition) and not interactionType:
            self.return_error("interactionType must be given when using interaction components")

        self.validate_interaction_types(interactionType, definition)

        # If extensions, validate it
        if 'extensions' in definition:
            self.validate_extensions(
                definition['extensions'], 'activity definition extensions')

    def check_other_interaction_component_fields(self, allowed, definition):
        interaction_components = set(
            ["choices", "scale", "source", "target", "steps"])
        keys = set(definition.keys())

        both = interaction_components.intersection(keys)
        not_allowed = list(both - set(allowed))

        if not_allowed:
            self.return_error("Only interaction component field(s) allowed (%s) - not allowed: %s" %
                              (' '.join(allowed), ' '.join(not_allowed)))

        # not_allowed = any(x in keys for x in interaction_components if x not in allowed)

    def validate_interaction_types(self, interactionType, definition):
        if interactionType == "choice" or interactionType == "sequencing":
            # If choices included, ensure it is an array and validate it
            if 'choices' in definition:
                self.check_other_interaction_component_fields(
                    ['choices'], definition)
                choices = definition['choices']
                self.check_if_list(choices, "Activity definition choices")
                self.validate_interaction_activities(choices, 'choices')
        elif interactionType == "likert":
            # If scale included, ensure it is an array and validate it
            if 'scale' in definition:
                self.check_other_interaction_component_fields(
                    ['scale'], definition)
                scale = definition['scale']
                self.check_if_list(scale, "Activity definition scale")
                self.validate_interaction_activities(scale, 'scale')
        elif interactionType == "matching":
            # If scale included, ensure it is an array and validate it
            if 'source' in definition:
                self.check_other_interaction_component_fields(
                    ['target', 'source'], definition)
                source = definition['source']
                self.check_if_list(source, "Activity definition source")
                self.validate_interaction_activities(source, 'source')
            # If target included, ensure it is an array and validate it
            if 'target' in definition:
                self.check_other_interaction_component_fields(
                    ['target', 'source'], definition)
                target = definition['target']
                self.check_if_list(target, "Activity definition target")
                self.validate_interaction_activities(target, 'target')
        elif interactionType == "performance":
            # If steps included, ensure it is an array and validate it
            if 'steps' in definition:
                self.check_other_interaction_component_fields(
                    ['steps'], definition)
                steps = definition['steps']
                self.check_if_list(steps, "Activity definition steps")
                self.validate_interaction_activities(steps, 'steps')

    def validate_interaction_activities(self, activities, field):
        id_list = []
        for act in activities:
            # Ensure each interaction activity is a dict and check allowed
            # fields
            self.check_if_dict(act, "%s interaction component" % field)
            self.check_allowed_fields(
                int_act_fields, act, "Activity definition %s" % field)
            self.check_required_fields(
                int_act_fields, act, "Activity definition %s" % field)

            # Ensure id value is string
            if not isinstance(act['id'], str):
                self.return_error(
                    "Interaction activity in component %s has an id that is not a string" % field)

            id_list.append(act['id'])
            if 'description' in act:
                # Ensure description is a dict (language map)
                self.check_if_dict(
                    act['description'], "%s interaction component description" % field)
                self.validate_lang_map(list(act['description'].keys(
                )), "%s interaction component description" % field)

        # Check and make sure all ids being listed are unique
        dups = set([i for i in id_list if id_list.count(i) > 1])
        if dups:
            self.return_error(
                "Interaction activities shared the same id(s) (%s) which is not allowed" % ' '.join(dups))

    def validate_substatement(self, substmt):
        # Ensure incoming substmt is a dict and check allowed and required
        # fields
        self.check_if_dict(substmt, "SubStatement")
        self.check_allowed_fields(sub_allowed_fields, substmt, "SubStatement")
        self.check_required_fields(
            sub_required_fields, substmt, "SubStatement")

        # If timestamp is included, ensure a valid time can be parsed
        if 'timestamp' in substmt:
            timestamp = substmt['timestamp']
            try:
                parse_datetime(timestamp)

                # Reject statements that don't comply with ISO 8601 offsets
                if timestamp.endswith("-00") or timestamp.endswith("-0000") or timestamp.endswith("-00:00"):
                    self.return_error(
                        "Timestamp error - Substatement Timestamp Illegal offset (-00, -0000, or -00:00) %s" % timestamp)

            except Exception as e:
                self.return_error(
                    "Timestamp error - There was an error while parsing the date from %s -- Error: %s" % (timestamp, str(e)))

        # Can't next substmts in other substmts - if not supplied it is an
        # Activity
        if 'objectType' in substmt['object']:
            if substmt['object']['objectType'] == 'SubStatement':
                self.return_error(
                    "Cannot nest a SubStatement inside of another SubStatement")
        else:
            substmt['object']['objectType'] = 'Activity'

        # Validate agent, verb, and object
        self.validate_agent(substmt['actor'], 'actor')
        self.validate_object(substmt['object'])
        self.validate_verb(substmt['verb'])

        # If result included, validate it
        if 'result' in substmt:
            self.validate_result(substmt['result'])

        # If context included, validate it
        if 'context' in substmt:
            self.validate_context(substmt['context'], substmt['object'])

    def validate_result(self, result):
        # Ensure incoming result is dict and check allowed fields
        self.check_if_dict(result, "Result")
        self.check_allowed_fields(result_allowed_fields, result, "Result")
        duration_re = re.compile(
            '^(-?)P(?=\d|T\d)(?:(\d+)Y)?(?:(\d+)M)?(?:(\d+)([DW]))?(?:T(?:(\d+)H)?(?:(\d+)M)?(?:(\d+(?:\.\d+)?)S)?)?$')
        # If duration included, ensure valid duration can be parsed from it
        if 'duration' in result:
            if not duration_re.match(result['duration']):
                self.return_error(
                    "Error with result duration")

        # If success or completion included, ensure they are boolean
        if 'success' in result:
            if not isinstance(result['success'], bool):
                self.return_error("Result success must be a boolean value")
        if 'completion' in result:
            if not isinstance(result['completion'], bool):
                self.return_error("Result completion must be a boolean value")

        # If response in result, ensure it is a string
        if 'response' in result:
            if not isinstance(result['response'], str):
                self.return_error("Result response must be a string")

        # If extensions, validate
        if 'extensions' in result:
            self.validate_extensions(result['extensions'], 'result extensions')

        # If score included, validate it
        if 'score' in result:
            self.validate_score(result['score'])

    def validate_score(self, score):
        # Ensure incoming score is a dict and check allowed fields
        self.check_if_dict(score, "Score")
        self.check_allowed_fields(score_allowed_fields, score, "Score")

        if 'raw' in score:
            # If raw included with min and max, ensure it is between min and ax
            raw = score['raw']
            # Check raw type
            if not (isinstance(raw, float) or isinstance(raw, int)):
                self.return_error("Score raw is not a number")
        else:
            raw = None

        # If min and max are included, ensure min <= max
        if 'min' in score and 'max' in score:
            sc_min = score['min']
            sc_max = score['max']

            # Check types of min and max
            if not (isinstance(sc_min, float) or isinstance(sc_min, int)):
                self.return_error("Score minimum is not a decimal")

            if not (isinstance(sc_max, float) or isinstance(sc_max, int)):
                self.return_error("Score maximum is not a decimal")

            if sc_min >= sc_max:
                self.return_error(
                    "Score minimum in statement result must be less than the maximum")

            if raw and (raw < sc_min or raw > sc_max):
                self.return_error(
                    "Score raw value in statement result must be between minimum and maximum")

        # If scale is included make sure it's between -1 and 1
        if 'scaled' in score:
            scaled = score['scaled']

            # Check scaled type
            if not (isinstance(scaled, float) or isinstance(scaled, int)):
                self.return_error("Score scaled is not a decimal")

            if scaled < -1 or scaled > 1:
                self.return_error(
                    "Score scaled value in statement result must be between -1 and 1")

    def validate_context(self, context, stmt_object):
        # Ensure incoming context is a dict and check allowed fields
        self.check_if_dict(context, "Context")
        self.check_allowed_fields(context_allowed_fields, context, "Context")

        # If registration included, ensure it is valid UUID
        if 'registration' in context:
            self.validate_uuid(context['registration'], 'Context registration')

        # If instructor or team included, ensure they are valid agents
        if 'instructor' in context:
            self.validate_agent(context['instructor'], 'Context instructor')
        if 'team' in context:
            self.validate_agent(context['team'], 'Context team')
            if 'objectType' not in context['team'] or context['team']['objectType'] == 'Agent':
                self.return_error("Team in context must be a group")

        # If objectType of object in stmt is Agent/Group, context cannot have
        # revision or platform fields
        object_type = stmt_object['objectType']

        if 'revision' in context:
            # Check revision is string
            if not isinstance(context['revision'], str):
                self.return_error("Context revision must be a string")

            if object_type != 'Activity':
                self.return_error(
                    "Revision is not allowed in context if statement object is not an Activity")

        if 'platform' in context:
            # Check platform is string
            if not isinstance(context['platform'], str):
                self.return_error("Context platform must be a string")

            if object_type != 'Activity':
                self.return_error(
                    "Platform is not allowed in context if statement object is not an Activity")

        # If language given, ensure it is string
        if 'language' in context:
            if not isinstance(context['language'], str):
                self.return_error("Context language must be a string")
            else:
                self.validate_language(context['language'], "context language")

        # If statement given, ensure it is a valid StatementRef
        if 'statement' in context:
            self.validate_statementref(context['statement'])

        # If contextActivities given, ensure they are valid contextActivities
        if 'contextActivities' in context:
            self.validate_context_activities(context['contextActivities'])

        # If extensions, validate
        if 'extensions' in context:
            self.validate_extensions(context['extensions'], 'context extensions')

    def validate_context_activities(self, conacts):
        # Ensure incoming conact is dict
        self.check_if_dict(conacts, "Context activity")
        context_activity_types = ['parent', 'grouping', 'category', 'other']
        for conact in list(conacts.items()):
            # Check if conact is a valid type
            if not conact[0] in context_activity_types:
                self.return_error("Context activity type is not valid - %s - must be %s" %
                                  (conact[0], ', '.join(context_activity_types)))
            # Ensure conact is a list or dict
            if isinstance(conact[1], list):
                for act in conact[1]:
                    self.validate_activity(act)
            elif isinstance(conact[1], dict):
                self.validate_activity(conact[1])
            else:
                self.return_error(
                    "contextActivities is not formatted correctly")