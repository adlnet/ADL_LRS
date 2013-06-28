import sys
import argparse
import re
from dateutil import parser as timeparser
from isodate.isoduration import parse_duration
from isodate.isoerror import ISO8601Error
import ast
from lrs.exceptions import ParamError
import pdb
SCHEME = 2
EMAIL = 5
uri_re = re.compile('^(([^:/?#]+):)?(//([^/?#]*))?([^?#]*)(\?([^#]*))?(#(.*))?')

class StatementValidator():
	def __init__(self, data):
		self.stmt = ast.literal_eval(data)
		
	def validate(self):
		# If list, validate each stmt inside
		if isinstance(self.stmt, list):
			for st in self.stmt:
				self.validate_statement(st)
			return "All Statements are valid"
		else:
			self.validate_statement(self.stmt)
			return "Statement is valid"

	def return_error(self, err_msg):
		raise ParamError(err_msg)

	def validate_email(self, email):
		res = uri_re.match(email)
		if not res.group(SCHEME) and not res.group(EMAIL):
			self.return_error("mbox value [%s] did not start with mailto:" % email)

	def validate_uri(self, uri_value, field):
		 if not uri_re.match(uri_value).group(SCHEME):
		 	self.return_error("%s with value %s was not a valid URI" % (field, uri_value))
		
	def validate_uuid(self, uuid, field):
		id_regex = re.compile("[a-fA-F0-9]{8}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{12}")
		if not id_regex.match(uuid):
			self.return_error("%s - %s is not a valid UUID" % (field, uuid))

	def check_if_dict(self, obj, field):
		if not isinstance(obj, dict):
			self.return_error("%s is not a properly formatted dictionary" % field)

	def check_if_list(self, obj, field):
		if not isinstance(obj, list):
			self.return_error("%s is not a properly formatted array" % field)

	def check_allowed_fields(self, allowed, obj, obj_name):
		# Check for fields that aren't in spec
		failed_list = [x for x in obj.keys() if not x in allowed]
		if failed_list:
			self.return_error("Invalid field(s) found in %s - %s" % (obj_name, ', '.join(failed_list)))

	def check_required_fields(self, required, obj, obj_name):
		for field in required:
			if not field in obj:
				self.return_error("%s is missing in %s" % (field, obj_name))

	def validate_statement(self, stmt):
		# Ensure dict was submitted as stmt and check allowed and required fields
		self.check_if_dict(stmt, "Statement")
		allowed_fields = ['id', 'actor', 'verb', 'object', 'result', 'context', 'timestamp', 'authority',
			'version', 'attachments']
		self.check_allowed_fields(allowed_fields, stmt, "Statement")
		required_fields = ['actor', 'verb', 'object']
		self.check_required_fields(required_fields, stmt, "Statement")

		# If version included in stmt (usually in header instead) make sure it is 1.0.0 +
		if 'version' in stmt:
			version_regex = re.compile("^1\.0(\.\d+)?$")
			if not version_regex.match(stmt['version']):
				self.return_error("%s is not a supported version" % stmt['version'])

		# If id included, make sure it is a valid UUID
		if 'id' in stmt:
			self.validate_uuid(stmt['id'], 'Statement id')

		# If timestamp included, make sure a valid date can be parsed from it
		if 'timestamp' in stmt:
			timestamp = stmt['timestamp']
			try:
				timeparser.parse(timestamp)
			except ValueError as e:
				self.return_error("Timestamp error - There was an error while parsing the date from %s -- Error: %s" % (timestamp, e.message))

		# Validate the actor and verb
		self.validate_agent(stmt['actor'], 'actor')
		self.validate_verb(stmt['verb'])

		# Validate the object
		stmt_object = stmt['object']
		self.validate_object(stmt_object)

		# If the object is validated and has no objectType, set to Activity
		if not 'objectType' in stmt_object:
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

		# If attachments is included, validate it
		if 'attachments' in stmt:
			self.validate_attachments(stmt['attachments'])

	def validate_attachments(self, attachments):
		# Ensure attachments is a list
		self.check_if_list(attachments, "Attachments")
		allowed_fields = ['usageType', 'display', 'description', 'contentType', 'length', 'sha2', 'fileUrl']
		required_fields = ['usageType', 'display', 'contentType', 'length']

		for attach in attachments:
			# For each attachment, check allowed and required fields
			self.check_allowed_fields(allowed_fields, attach, "Attachment")
			self.check_required_fields(required_fields, attach, "Attachment")

			# Validate usageType
			self.validate_uri(attach['usageType'], 'Attachments usageType')

			# If fileUrl included, validate it
			if 'fileUrl' in attach:
				self.validate_uri(attach['fileUrl'], 'Attachments fileUrl')
			else:
				# If fileUrl is not included, sha2 must be - only time sha2 is required
				if not 'sha2' in attach:
					self.return_error("Attachment sha2 is required when no fileUrl is given")

				# Ensure sha2 is submitted as string
				if not isinstance(attach['sha2'], unicode):
					self.return_error("Attachment sha2 must be a string")

			# Ensure length is an int
			if not isinstance(attach['length'], int):
				self.return_error("Attachment length must be an integer")

			# Ensure contentType is submitted as a string
			if not isinstance(attach['contentType'], unicode):
				self.return_error("Attachment contentType must be a string")

			# Ensure display is a dict (language map)
			self.check_if_dict(attach['display'], "Attachment display")
			
			# If description included, ensure it is a dict (language map)
			if 'description' in attach:
				self.check_if_dict(attach['description'], "Attachment description")

	def validate_extensions(self, extensions, field):
		# Ensure incomgin extensions is a dict
		self.check_if_dict(extensions, "%s extensions" % field)
		
		# Ensure each key in extensions is a valid URI
		for k, v in extensions.items():
			self.validate_uri(k, field)

	def validate_agent(self, agent, placement):
		# Ensure incoming agent is a dict and check allowed fields
		self.check_if_dict(agent, "Agent in %s" % placement)
		allowed_fields = ['objectType', 'name', 'member', 'mbox', 'mbox_sha1sum', 'openID', 'openid','account']
		self.check_allowed_fields(allowed_fields, agent, "Agent/Group")

		# If the agent is the object of a stmt, the objectType must be present
		if placement == 'object' and not 'objectType' in agent:
			self.return_error("objectType must be set when using an Agent as the object of a statement")
		# If the agent is not the object of a stmt and objectType is given, it must be Agent or Group
		elif placement != 'object' and 'objectType' in agent:
			if agent['objectType'] != 'Agent' and agent['objectType'] != 'Group':
				self.return_error("An agent's objectType must be either Agent or Group if given")
		# If the agent is not the object of a stmt and objectType is not given, set it to Agent 
		elif placement != 'object' and not 'objectType' in agent:
			agent['objectType'] = 'Agent'

		# Agent must have only one inverse functionlal identifier (Group may be Anonymous Group where no IFI is
		# required)
		agent_ifis_can_only_be_one = ['mbox', 'mbox_sha1sum', 'openID', 'account', 'openid']
		ifis = [a for a in agent_ifis_can_only_be_one if agent.get(a, None) != None]
		if agent['objectType'] == 'Agent' and len(ifis) != 1:
			self.return_error("One and only one of %s may be supplied with an Agent" % ", ".join(agent_ifis_can_only_be_one))

		if agent['objectType'] == 'Agent':
			# If agent, if name given, ensure name is string and validate the IFI
			if 'name' in agent and not isinstance(agent['name'], unicode):
				self.return_error("If name is given in Agent, it must be a string")
			self.validate_ifi(ifis[0], agent[ifis[0]])
		else:
			# If group, if name given, ensure name is string
			if 'name' in agent and not isinstance(agent['name'], unicode):
				self.return_error("If name is given in Group, it must be a string")

			# If no IFIs, it is an anonymous group which must contain the member property 
			if not ifis:
				if not 'member' in agent:
					self.return_error("Anonymous groups must contain member")
			else:
				# IFI given, validate it
				self.validate_ifi(ifis[0], agent[ifis[0]])

			# If member is in group (not required if have IFI)
			if 'member' in agent:
				# Ensure member list is array
				members = agent['member']
				self.check_if_list(member, "Members")
				
				# Make sure no member of group is another group
				object_types = [t['objectType'] for t in members if 'objectType' in t]
				if 'Group' in object_types:
					self.return_error('Group member value cannot be other groups')

				# Validate each member in group
				for agent in members:
					self.validate_agent(agent, 'member')

	def validate_ifi(self, ifis, ifi_value):
		# Spec not clear if openid or openID - set to openID just in case
		if ifis == 'openid':
			ifis = 'openID'
		
		# Validate each IFI accordingly
		if ifis == 'mbox':
			self.validate_email(ifi_value)
		elif ifis == 'openID':
			self.validate_uri(ifi_value, 'openID')
		elif ifis == 'account':
			self.validate_account(ifi_value)

	def validate_account(self, account):
		# Ensure incoming account is a dict and check allowed and required fields
		self.check_if_dict(account, "Account")
		allowed_fields = ['homePage', 'name']
		self.check_allowed_fields(allowed_fields, account, "Account")
		required_fields = ['homePage', 'name']
		self.check_required_fields(required_fields, account, "Account")

		# Ensure homePage is a valid URI
		self.validate_uri(account['homePage'], 'homePage')

		# Ensure name is a string
		if not isinstance(account['name'], unicode):
			self.return_error("account name must be a string")

	def validate_verb(self, verb):
		# Ensure incoming verb is a dict and check allowed fields
		self.check_if_dict(verb, "Verb")
		allowed_fields = ['id', 'display']
		self.check_allowed_fields(allowed_fields, verb, "Verb")

		# Verb must conatin id - then validate it
		if not 'id' in verb:
			self.return_error('Verb must contain an id')
		self.validate_uri(verb['id'], 'Verb id')

		# If display given, ensure it's a dict (language map)
		if 'display' in verb:
			self.check_if_dict(verb['display'], "Verb display")

	def validate_object(self, stmt_object):
		# Ensure incoming object is a dict
		self.check_if_dict(stmt_object, "Object")

		# If objectType is not given or is Activity it is an Activity
		# Validate the rest accordingly
		if not 'objectType' in stmt_object or stmt_object['objectType'] == 'Activity':
			self.validate_activity(stmt_object)
		elif stmt_object['objectType'] == 'Agent' or stmt_object['objectType'] == 'Group':
			self.validate_agent(stmt_object, 'object')
		elif stmt_object['objectType'] == 'SubStatement':
			self.validate_substatement(stmt_object)
		elif stmt_object['objectType'] == 'StatementRef':
			self.validate_statementref(stmt_object)
		else:
			self.return_error("The objectType in the statement's object is not valid - %s" % stmt_object['objectType'])

	def validate_statementref(self, ref):
		# Ensure incoming StatementRef is a dictionary an check allowed and required fields
		self.check_if_dict(ref, "StatementRef")
		allowed_fields = ['id', 'objectType']
		self.check_allowed_fields(allowed_fields, ref, "StatementRef")
		required_fields = ['id', 'objectType']
		self.check_required_fields(required_fields, ref, "StatementRef")

		# objectType must be StatementRef
		if ref['objectType'] != "StatementRef":
			self.return_error("StatementRef objectType must be set to 'StatementRef'")

		# Ensure id is a valid UUID
		self.validate_uuid(ref['id'], 'StatementRef id')

	def validate_activity(self, activity):
		# Ensure incoming activity is a dict and check allowed fields
		self.check_if_dict(activity, "Activity")
		allowed_fields = ['objectType', 'id', 'definition']
		self.check_allowed_fields(allowed_fields, activity, "Activity")

		# Id must be present
		if not 'id' in activity:
			self.return_error("Id field must be present in an Activity")

		# If definition included, validate it
		if 'definition' in activity:
			self.validate_activity_definition(activity['definition'])

	def validate_activity_definition(self, definition):
		# Ensure incoming def is a dict and check allowed fields
		self.check_if_dict(definition, "Activity definition")
		allowed_fields = ['name', 'description', 'type', 'moreInfo', 'extensions', 'interactionType',
		'correctResponsesPattern', 'choices', 'scale', 'source', 'target', 'steps']
		self.check_allowed_fields(allowed_fields, definition, "Activity definition")

		# If name or description included, ensure it is a dict (language map)
		if 'name' in definition:
			self.check_if_dict(definition['name'], "Activity definition name")
		if 'description' in definition:
			self.check_if_dict(definition['description'], "Activity definition description")

		# If type or moreInfo included, ensure it is valid URI
		if 'type' in definition:
			self.validate_uri(definition['type'], 'Activity definition type')
		if 'moreInfo' in definition:
			self.validate_uri(definition['moreInfo'], 'Activity definition moreInfo')

		# If interactionType included, ensure it is a string
		if 'interactionType' in definition:
			if not isinstance(definition['interactionType'], unicode):
				self.return_error("Activity definition interactionType must be a string")

		# If correctResponsesPatter included, ensure it is an array
		if 'correctResponsesPattern' in definition:
			self.check_if_list(definition['correctResponsesPattern'], "Activity definition correctResponsesPattern")
			for answer in definition['correctResponsesPattern']:
				# For each answer, ensure it is a string
				if not isinstance(answer, unicode):
					self.return_error("Activity definition correctResponsesPattern answer's must all be strings")

		# If choices included, ensure it is an array and validate it
		if 'choices' in definition:
			choices = definition['choices']
			self.check_if_list(choices, "Activity definition choices")
			self.validate_interaction_activities(choices, 'choices')			

		# If scale included, ensure it is an array and validate it
		if 'scale' in definition:
			scale = definition['scale']
			self.check_if_list(scale, "Activity definition scale")
			self.validate_interaction_activities(scale, 'scale')

		# If scale included, ensure it is an array and validate it
		if 'source' in definition:
			source = definition['source']
			self.check_if_list(source, "Activity definition source")
			self.validate_interaction_activities(source, 'source')

		# If target included, ensure it is an array and validate it
		if 'target' in definition:
			target = definition['target']
			self.check_if_list(target, "Activity definition target")
			self.validate_interaction_activities(target, 'target')

		# If steps included, ensure it is an array and validate it
		if 'steps' in definition:
			steps = definition['steps']
			self.check_if_list(steps, "Activity definition steps")
			self.validate_interaction_activities(steps, 'steps')

		# If extensions, validate it
		if 'extensions' in definition:
			self.validate_extensions(definition['extensions'], 'activity definition')		

	def validate_interaction_activities(self, activities, field):
		allowed_fields = ['id', 'description']
		required_fields = ['id', 'description']
		for act in activities:
			# Ensure each interaction activity is a dict and check allowed fields
			self.check_if_dict(act, "%s interaction component" % field)
			self.check_allowed_fields(allowed_fields, act, "Activity definition %s" % field)
			self.check_required_fields(required_fields, act, "Activity definition %s" % field)

			# Ensure id value is string
			if not isinstance(act['id'], unicode):
				self.return_error("Interaction activity in component %s has an id that is not a string" % field)

			# Ensure description is a dict (language map)
			self.check_if_dict(act['description'], "%s interaction component description" % field)

	def validate_substatement(self, substmt):
		# Ensure incoming substmt is a dict and check allowed and required fields
		self.check_if_dict(substmt, "SubStatement")
		allowed_fields = ['actor', 'verb', 'object', 'result', 'context', 'timestamp', "objectType"]
		self.check_allowed_fields(allowed_fields, substmt, "SubStatement")
		required_fields = ['actor', 'verb', 'object']
		self.check_required_fields(required_fields, substmt, "SubStatement")

		# If timestamp is included, ensure a valid time can be parsed
		if 'timestamp' in substmt:
			timestamp = substmt['timestamp']
			try:
				timeparser.parse(timestamp)
			except ValueError as e:
				self.return_error("Timestamp error - There was an error while parsing the date from %s -- Error: %s" % (timestamp, e.message))

		# Can't next substmts in other substmts - if not supplied it is an Activity
		if 'objectType' in substmt['object']:
			if substmt['object']['objectType'] == 'SubStatement':
				self.return_error("Cannot nest a SubStatement inside of another SubStatement")
		else:
			substmt['object']['objectType'] = 'Activity'

		# Validate agent, verb, and object
		self.validate_agent(substmt['actor'], 'actor')
		self.validate_verb(substmt['verb'])
		self.validate_object(substmt['object'])

		# If result included, validate it
		if 'result' in substmt:
			self.validate_result(substmt['result'])

		# If context included, validate it
		if 'context' in substmt:
			self.validate_context(substmt['context'], substmt['object'])

	def validate_result(self, result):
		# Ensure incoming result is dict and check allowed fields
		self.check_if_dict(result, "Result")
		allowed_fields = ['score', 'success', 'completion', 'response', 'duration', 'extensions']
		self.check_allowed_fields(allowed_fields, result, "Result")

		# If duration included, ensure valid duration can be parsed from it
		if 'duration' in result:
			try:
				parse_duration(result['duration'])
			except ISO8601Error as e:
				self.return_error("Error with result duration - %s" % e.message)

		# If success or completion included, ensure they are boolean
		if 'success' in result:
			if not isinstance(result['success'], bool):
				self.return_error("Result success must be a boolean value")
		if 'completion' in result:
			if not isinstance(result['completion'], bool):
				self.return_error("Result completion must be a boolean value")

		# If response in result, ensure it is a string
		if 'response' in result:
			if not isinstance(result['response'], unicode):
				self.return_error("Result response must be a string")

		# If extensions, validate
		if 'extensions' in result:
			self.validate_extensions(result['extensions'], 'result')

		# If score included, validate it
		if 'score' in result:
			self.validate_score(result['score'])

	def validate_score(self, score):
		# Ensure incoming score is a dict and check allowed fields
		self.check_if_dict(score, "Score")
		allowed_fields = ['scaled', 'raw', 'min', 'max']
		self.check_allowed_fields(allowed_fields, score, "Score")

		# If min and max are included, ensure min <= max
		if 'min' in score and 'max' in score:
			sc_min = score['min']
			sc_max = score['max']

			if sc_min >= sc_max:
				self.return_error("Score minimum in statement result must be less than the maximum")

			# If raw included with min and max, ensure it is between min and ax
			raw = score['raw']
			if 'raw' in score and (raw < sc_min or raw > sc_max):
				self.return_error("Score raw value in statement result must be between minimum and maximum")

		# If scale is included make sure it's between -1 and 1
		if 'scaled' in score:
			scaled = score['scaled']
			if scaled < -1 or scaled > 1:
				self.return_error("Score scaled value in statement result must be between -1 and 1")

	def validate_context(self, context, stmt_object):
		# Ensure incoming context is a dict and check allowed fields
		self.check_if_dict(context, "Context")
		allowed_fields = ['registration', 'instructor', 'team', 'contextActivities', 'revision', 'platform',
			'language', 'statement', 'extensions']
		self.check_allowed_fields(allowed_fields, context, "Context")

		# If registration included, ensure it is valid UUID
		if 'registration' in context:
			self.validate_uuid(context['registration'], 'Context registration')

		# If instructor or team included, ensure they are valid agents
		if 'instructor' in context:
			self.validate_agent(context['instructor'], 'Context instructor')
		if 'team' in context:
			self.validate_agent(context['team'], 'Context team')

		# If objectType of object in stmt is Agent/Group, context cannot have revision or platform fields
		object_type = stmt_object['objectType']
		if 'revision' in context:
			if object_type == 'Agent' or object_type == 'Group':
				self.return_error("Revision is not allowed in context if statment object is an Agent or Group")		

			# Check revision is string
			if not isinstance(context['revision'], unicode):
				self.return_error("Context revision must be a string")

		if 'platform' in context:
			if object_type == 'Agent' or object_type == 'Group':
				self.return_error("Platform is not allowed in context if statment object is an Agent or Group")		

			# Check platform is string
			if not isinstance(context['platform'], unicode):
				self.return_error("Context platform must be a string")

		# If language given, ensure it is string
		if 'language' in context:
			if not isinstance(context['language'], unicode):
				self.return_error("Context language must be a string")

		# If statement given, ensure it is a valid StatementRef
		if 'statement' in context:
			self.validate_statementref(context['statement'])

		# If contextActivities given, ensure they are valid contextActivities
		if 'contextActivities' in context:
			self.validate_context_activities(context['contextActivities'])

		# If extensions, validate
		if 'extensions' in context:
			self.validate_extensions(context['extensions'], 'context')

	def validate_context_activities(self, conacts):
		# Ensure incoming conact is dict
		self.check_if_dict(conacts, "Context activity")
		context_activity_types = ['parent', 'grouping', 'category', 'other']
		for conact in conacts.items():
			# Check if conact is a valid type
			if not conact[0] in context_activity_types:
				self.return_error("Context Activity type is not valid")
			# Ensure conact is a list or dict
			if isinstance(conact[1], list):
				for act in conact[1]:
					self.validate_activity(act)
			elif isinstance(conact[1], dict):
				self.validate_activity(conact[1])
			else:
				self.return_error("contextActivities is not formatted correctly")
