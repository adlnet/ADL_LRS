import json
import urllib2
from isodate.isodatetime import parse_datetime
from isodate.isoerror import ISO8601Error

from django.conf import settings
from django.db import transaction

from util import convert_to_dict, get_agent_ifp
from Authorization import auth
from StatementValidator import StatementValidator

from ..models import Statement, Agent, Activity
from ..exceptions import ParamConflict, ParamError, Forbidden, NotFound, BadRequest, IDNotFoundError

def check_for_existing_statementId(stmtID):
    return Statement.objects.filter(statement_id=stmtID).exists()

def check_for_no_other_params_supplied(query_dict):
    supplied = True
    if len(query_dict) <= 1:
        supplied = False
    return supplied

# Extra agent validation for state and profile
def validate_oauth_state_or_profile_agent(req_dict, endpoint):    
    ag = req_dict['params']['agent']
    token = req_dict['auth']['oauth_token']
    scopes = token.scope_to_list()
    if not 'all' in scopes:
        if not isinstance(ag, dict):
            ag = json.loads(ag)
        try:
            agent = Agent.objects.get(**ag)
        except Agent.DoesNotExist:
            err_msg = "Agent in %s cannot be found to match user in authorization" % endpoint
            raise NotFound(err_msg)

        if not agent in req_dict['auth']['authority'].member.all():
            err_msg = "Authorization doesn't match agent in %s" % endpoint
            raise Forbidden(err_msg)

def validate_void_statement(void_id):
    # Retrieve statement, check if the verb is 'voided' - if not then set the voided flag to true else return error 
    # since you cannot unvoid a statement and should just reissue the statement under a new ID.
    try:
        stmt = Statement.objects.get(statement_id=void_id)
    except Statement.DoesNotExist:
        err_msg = "Statement with ID %s does not exist" % void_id
        raise IDNotFoundError(err_msg)
        
    if stmt.voided:
        err_msg = "Statement with ID: %s is already voided, cannot unvoid. Please re-issue the statement under a new ID." % void_id
        raise Forbidden(err_msg)

def server_validate_statement_object(stmt_object, auth):
    if stmt_object['objectType'] == 'StatementRef' and not check_for_existing_statementId(stmt_object['id']):
            err_msg = "No statement with ID %s was found" % stmt_object['id']
            raise IDNotFoundError(err_msg)
            
def validate_stmt_authority(stmt, auth):
    # If not validated yet - validate auth first since it supercedes any auth in stmt
    if auth['authority']:
        if auth['authority'].objectType == 'Group' and not auth['authority'].oauth_identifier:
            err_msg = "Statements cannot have a non-Oauth group as the authority"
            raise ParamError(err_msg)
        elif auth['authority'].objectType == 'Group' and auth['authority'].oauth_identifier:
            if auth['authority'].member.count() != 2:
                err_msg = "OAuth authority must only contain 2 members"
                raise ParamError(err_msg)

# Retrieve JSON data from ID
def get_act_def_data(act_data):
    act_url_data = {}
    # See if id resolves
    try:
        req = urllib2.Request(act_data['id'])
        req.add_header('Accept', 'application/json, */*')
        act_resp = urllib2.urlopen(req, timeout=settings.ACTIVITY_ID_RESOLVE_TIMEOUT)
    except Exception:
        # Doesn't resolve-hopefully data is in payload
        pass
    else:
        # If it resolves then try parsing JSON from it
        try:
            act_url_data = json.loads(act_resp.read())
        except Exception:
            # Resolves but no data to retrieve - this is OK
            pass

        # If there was data from the URL
        if act_url_data:
            # If there was a defintion in received JSON already
            if 'definition' in act_data:
                act_data['definition'] = dict(act_url_data.items() + act_data['definition'].items())
            else:
                # If there was data from the URL and no definition in the JSON
                act_data['definition'] = act_url_data

            # # Have to validate new data given from URL
            # try:
            #     validator = StatementValidator()
            #     validator.validate_activity(act_data)
            # except Exception, e:
            #     raise BadRequest(e.message)
            # except ParamError, e:
            #     raise ParamError(e.message)

            # update_activity_definition(act_data)

@transaction.commit_on_success
def update_activity_definition(act):
    # Try to get canonical activity by id
    try:
        activity = Activity.objects.get(activity_id=act['id'], canonical_version=True)
    except Activity.DoesNotExist:
        # Could not exist yet
        pass
    # If the activity already exists in the db
    else:
        # If there is a name in the IRI act definition add it to what already exists
        if 'name'in act['definition']:
            activity.activity_definition_name = dict(activity.activity_definition_name.items() + act['definition']['name'].items())
        # If there is a description in the IRI act definition add it to what already exists
        if 'description' in act['description']:
            activity.activity_definition_description = dict(activity.activity_definition_description.items() + act['definition']['description'].items())

        activity.activity_definition_type = act['definition'].get('type', '')
        activity.activity_definition_moreInfo = act['definition'].get('moreInfo', '')
        activity.activity_definition_interactionType = act['definition'].get('interactionType', '')
        activity.activity_definition_extensions = act['definition'].get('extensions', {})
        activity.activity_definition_crpanswers = act['definition'].get('correctResponsesPattern', {})
        activity.activity_definition_choices = act['definition'].get('choices', {})
        activity.activity_definition_sources = act['definition'].get('source', {}) 
        activity.activity_definition_targets = act['definition'].get('target', {})
        activity.activity_definition_steps = act['definition'].get('steps', {})
        activity.activity_definition_scales = act['definition'].get('scale', {})
        activity.save()

def validate_body(body, auth, payload_sha2s):
        [server_validate_statement(stmt, auth, payload_sha2s) for stmt in body]
    
def server_validate_statement(stmt, auth, payload_sha2s):
    if 'id' in stmt:
        statement_id = stmt['id']
        if check_for_existing_statementId(statement_id):
            err_msg = "A statement with ID %s already exists" % statement_id
            raise ParamConflict(err_msg)

    server_validate_statement_object(stmt['object'], auth)
    if stmt['verb']['id'] == 'http://adlnet.gov/expapi/verbs/voided':
        validate_void_statement(stmt['object']['id'])

    if not 'objectType' in stmt['object'] or stmt['object']['objectType'] == 'Activity':
        # push act ID to queue here
        # pass
        get_act_def_data(stmt['object'])

        try:
            validator = StatementValidator()
            validator.validate_activity(stmt['object'])
        except Exception, e:
            raise BadRequest(e.message)
        except ParamError, e:
            raise ParamError(e.message)

    validate_stmt_authority(stmt, auth)
    if 'attachments' in stmt:
        attachment_data = stmt['attachments']
        validate_attachments(attachment_data, payload_sha2s)

@auth
def statements_post(req_dict):
    if req_dict['params'].keys():
        raise ParamError("The post statements request contained unexpected parameters: %s" % ", ".join(req_dict['params'].keys()))

    if isinstance(req_dict['body'], basestring):
        req_dict['body'] = convert_to_dict(req_dict['body'])

    try:
        validator = StatementValidator(req_dict['body'])
        validator.validate()
    except Exception, e:
        raise BadRequest(e.message)
    except ParamError, e:
        raise ParamError(e.message)

    if isinstance(req_dict['body'], dict):
        body = [req_dict['body']]
    else:
        body = req_dict['body']
    validate_body(body, req_dict['auth'], req_dict.get('payload_sha2s', None))

    return req_dict

@auth
def statements_more_get(req_dict):
    if not 'more_id' in req_dict:
        err_msg = "Missing more_id while trying to hit /more endpoint"
        raise ParamError(err_msg)
    return req_dict

def validate_statementId(req_dict):
    if 'statementId' in req_dict['params'] and 'voidedStatementId' in req_dict['params']:
        err_msg = "Cannot have both statementId and voidedStatementId in a GET request"
        raise ParamError(err_msg)
    elif 'statementId' in req_dict['params']:
        statementId = req_dict['params']['statementId']
        voided = False
    else:
        statementId = req_dict['params']['voidedStatementId']
        voided = True

    not_allowed = ["agent", "verb", "activity", "registration", 
                   "related_activities", "related_agents", "since",
                   "until", "limit", "ascending"]
    bad_keys = set(not_allowed) & set(req_dict['params'].keys())
    if bad_keys:
        err_msg = "Cannot have %s in a GET request only 'format' and/or 'attachments' are allowed with 'statementId' and 'voidedStatementId'" % ', '.join(bad_keys)
        raise ParamError(err_msg)

    # Try to retrieve stmt, if DNE then return empty else return stmt info                
    try:
        st = Statement.objects.get(statement_id=statementId)
    except Statement.DoesNotExist:
        err_msg = 'There is no statement associated with the id: %s' % statementId
        raise IDNotFoundError(err_msg)

    auth = req_dict.get('auth', None)
    mine_only = auth and 'statements_mine_only' in auth

    if auth['authority']:
        if mine_only and st.authority.id != auth['authority'].id:
            err_msg = "Incorrect permissions to view statements"
            raise Forbidden(err_msg)
    
    if st.voided != voided:
        if st.voided:
            err_msg = 'The requested statement (%s) is voided. Use the "voidedStatementId" parameter to retrieve your statement.' % statementId
        else:
            err_msg = 'The requested statement (%s) is not voided. Use the "statementId" parameter to retrieve your statement.' % statementId
        raise IDNotFoundError(err_msg)

    return statementId

@auth
def statements_get(req_dict):
    rogueparams = set(req_dict['params']) - set(["statementId","voidedStatementId","agent", "verb", "activity", "registration", 
                       "related_activities", "related_agents", "since",
                       "until", "limit", "format", "attachments", "ascending"])
    if rogueparams:
        raise ParamError("The get statements request contained unexpected parameters: %s" % ", ".join(rogueparams))

    formats = ['exact', 'canonical', 'ids']
    if 'params' in req_dict and 'format' in req_dict['params']:
        if req_dict['params']['format'] not in formats:
            raise ParamError("The format filter value (%s) was not one of the known values: %s" % (req_dict['params']['format'], ','.join(formats)))
    else:
        req_dict['params']['format'] = 'exact'     
    
    # StatementId could be for voided statement as well
    if 'params' in req_dict and ('statementId' in req_dict['params'] or 'voidedStatementId' in req_dict['params']):
        req_dict['statementId'] = validate_statementId(req_dict)

    if 'since' in req_dict['params']:
        try:
            parse_datetime(req_dict['params']['since'])
        except (Exception, ISO8601Error):
            raise ParamError("Since parameter was not a valid ISO8601 timestamp")

    if 'until' in req_dict['params']:
        try:
            parse_datetime(req_dict['params']['until'])
        except (Exception, ISO8601Error):
            raise ParamError("Until parameter was not a valid ISO8601 timestamp")

    # Django converts all query values to string - make boolean depending on if client wants attachments or not
    # Only need to do this in GET b/c GET/more will have it saved in pickle information
    if 'params' in req_dict and 'attachments' in req_dict['params']:
        if req_dict['params']['attachments'].lower() == 'true':
            req_dict['params']['attachments'] = True
        else:
            req_dict['params']['attachments'] = False
    else:
        req_dict['params']['attachments'] = False
    return req_dict

@auth
def statements_put(req_dict):
    # Find any unexpected parameters
    rogueparams = set(req_dict['params']) - set(["statementId"])
    if rogueparams:
        raise ParamError("The put statements request contained unexpected parameters: %s" % ", ".join(rogueparams))

    # Statement id can must be supplied in query param. If in the body too, it must be the same
    if not 'statementId' in req_dict['params']:
        raise ParamError("Error -- statements - method = %s, but no statementId parameter or ID given in statement" % req_dict['method'])
    else:
        statement_id = req_dict['params']['statementId']

    # Convert data so it can be parsed
    if isinstance(req_dict['body'], basestring):
        req_dict['body'] = convert_to_dict(req_dict['body'])

    # Try to get id if in body
    try:
        statement_body_id = req_dict['body']['id']
    except Exception, e:
        statement_body_id = None

    # If ids exist in both places, check if they are equal
    if statement_body_id and statement_id != statement_body_id:
        raise ParamError("Error -- statements - method = %s, param and body ID both given, but do not match" % req_dict['method'])

    # If statement with that ID already exists-raise conflict error
    if check_for_existing_statementId(statement_id):
        raise ParamConflict("A statement with ID %s already exists" % statement_id)
    
    # Set id inside of statement with param id
    if not statement_body_id:
        req_dict['body']['id'] = statement_id

    # If there are no other params-raise param error since nothing else is supplied
    if not check_for_no_other_params_supplied(req_dict['body']):
        raise ParamError("No other params are supplied with statementId.")

    # Validate statement in body
    try:
        validator = StatementValidator(req_dict['body'])
        validator.validate()
    except Exception, e:
        raise BadRequest(e.message)
    except ParamError, e:
        raise ParamError(e.message)
    validate_body([req_dict['body']], req_dict['auth'], req_dict.get('payload_sha2s', None))
    return req_dict

def validate_attachments(attachment_data, payload_sha2s):
    # For each attachment that is in the actual statement
    for attachment in attachment_data:
        # If the attachment data has a sha2 field, must validate it against the payload data
        if 'sha2' in attachment:
            sha2 = attachment['sha2']
            # Check if the sha2 field is a key in the payload dict
            if payload_sha2s:
                if not sha2 in payload_sha2s:
                    err_msg = "Could not find attachment payload with sha: %s" % sha2
                    raise ParamError(err_msg)
            else:
                raise BadRequest("Missing X-Experience-API-Hash field in header")
@auth
def activity_state_post(req_dict):
    rogueparams = set(req_dict['params']) - set(["activityId", "agent", "stateId", "registration"])
    if rogueparams:
        raise ParamError("The post activity state request contained unexpected parameters: %s" % ", ".join(rogueparams))

    validator = StatementValidator()
    if 'activityId' in req_dict['params']:
        validator.validate_iri(req_dict['params']['activityId'], "activityId param for activity state")
    else:
        err_msg = "Error -- activity_state - method = %s, but activityId parameter is missing.." % req_dict['method']
        raise ParamError(err_msg)

    if not 'stateId' in req_dict['params']:
        err_msg = "Error -- activity_state - method = %s, but stateId parameter is missing.." % req_dict['method']
        raise ParamError(err_msg)    

    if 'registration' in req_dict['params']:
        validator.validate_uuid(req_dict['params']['registration'], "registration param for activity state")

    if 'agent' in req_dict['params']:
        try:
            agent = json.loads(req_dict['params']['agent'])
            req_dict['params']['agent'] = agent
        except Exception:
            raise ParamError("agent param for activity state is not valid")
        validator.validate_agent(agent, "Activity state agent param")
    else:
        err_msg = "Error -- activity_state - method = %s, but agent parameter is missing.." % req_dict['method']
        raise ParamError(err_msg)
    
    # Must have body included for state
    if 'body' not in req_dict:
        err_msg = "Could not find the state"
        raise ParamError(err_msg)
    
    # Extra validation if oauth
    if req_dict['auth']['type'] == 'oauth':
        validate_oauth_state_or_profile_agent(req_dict, "state")

    # Set state
    req_dict['state'] = req_dict.pop('raw_body', req_dict.pop('body', None))
    return req_dict

@auth
def activity_state_put(req_dict):
    rogueparams = set(req_dict['params']) - set(["activityId", "agent", "stateId", "registration"])
    if rogueparams:
        raise ParamError("The put activity state request contained unexpected parameters: %s" % ", ".join(rogueparams))

    validator = StatementValidator()
    if 'activityId' in req_dict['params']:
        validator.validate_iri(req_dict['params']['activityId'], "activityId param for activity state")
    else:
        err_msg = "Error -- activity_state - method = %s, but activityId parameter is missing.." % req_dict['method']
        raise ParamError(err_msg)

    if not 'stateId' in req_dict['params']:
        err_msg = "Error -- activity_state - method = %s, but stateId parameter is missing.." % req_dict['method']
        raise ParamError(err_msg)    

    if 'registration' in req_dict['params']:
        validator.validate_uuid(req_dict['params']['registration'], "registration param for activity state")

    if 'agent' in req_dict['params']:
        try:
            agent = json.loads(req_dict['params']['agent'])
            req_dict['params']['agent'] = agent
        except Exception:
            raise ParamError("agent param for activity state is not valid")
        validator.validate_agent(agent, "Activity state agent param")
    else:
        err_msg = "Error -- activity_state - method = %s, but agent parameter is missing.." % req_dict['method']
        raise ParamError(err_msg)
    
    # Must have body included for state
    if 'body' not in req_dict:
        err_msg = "Could not find the state"
        raise ParamError(err_msg)
    
    # Extra validation if oauth
    if req_dict['auth']['type'] == 'oauth':
        validate_oauth_state_or_profile_agent(req_dict, "state")

    # Set state
    req_dict['state'] = req_dict.pop('raw_body', req_dict.pop('body', None))
    return req_dict

@auth
def activity_state_get(req_dict):
    rogueparams = set(req_dict['params']) - set(["activityId", "agent", "stateId", "registration", "since"])
    if rogueparams:
        raise ParamError("The get activity state request contained unexpected parameters: %s" % ", ".join(rogueparams))

    validator = StatementValidator()
    if 'activityId' in req_dict['params']:
        validator.validate_iri(req_dict['params']['activityId'], "activityId param for activity state")
    else:
        err_msg = "Error -- activity_state - method = %s, but activityId parameter is missing.." % req_dict['method']
        raise ParamError(err_msg)

    if 'registration' in req_dict['params']:
        validator.validate_uuid(req_dict['params']['registration'], "registration param for activity state")

    if 'agent' in req_dict['params']:
        try:
            agent = json.loads(req_dict['params']['agent'])
            req_dict['params']['agent'] = agent
        except Exception:
            raise ParamError("agent param for activity state is not valid")
        validator.validate_agent(agent, "Activity state agent param")
    else:
        err_msg = "Error -- activity_state - method = %s, but agent parameter is missing.." % req_dict['method']
        raise ParamError(err_msg)

    if 'since' in req_dict['params']:
        try:
            parse_datetime(req_dict['params']['since'])
        except (Exception, ISO8601Error):
            raise ParamError("Since parameter was not a valid ISO8601 timestamp")


    # Extra validation if oauth
    if req_dict['auth']['type'] == 'oauth':
        validate_oauth_state_or_profile_agent(req_dict, "state")    
    return req_dict

@auth
def activity_state_delete(req_dict):
    rogueparams = set(req_dict['params']) - set(["activityId", "agent", "stateId", "registration"])
    if rogueparams:
        raise ParamError("The delete activity state request contained unexpected parameters: %s" % ", ".join(rogueparams))

    validator = StatementValidator()
    if 'activityId' in req_dict['params']:
        validator.validate_iri(req_dict['params']['activityId'], "activityId param for activity state")
    else:
        err_msg = "Error -- activity_state - method = %s, but activityId parameter is missing.." % req_dict['method']
        raise ParamError(err_msg)

    if 'registration' in req_dict['params']:
        validator.validate_uuid(req_dict['params']['registration'], "registration param for activity state")

    if 'agent' in req_dict['params']:
        try:
            agent = json.loads(req_dict['params']['agent'])
            req_dict['params']['agent'] = agent
        except Exception:
            raise ParamError("agent param for activity state is not valid")
        validator.validate_agent(agent, "Activity state agent param")
    else:
        err_msg = "Error -- activity_state - method = %s, but agent parameter is missing.." % req_dict['method']
        raise ParamError(err_msg)
    
    # Extra validation if oauth
    if req_dict['auth']['type'] == 'oauth':
        validate_oauth_state_or_profile_agent(req_dict, "state")
    return req_dict

@auth
def activity_profile_post(req_dict):
    rogueparams = set(req_dict['params']) - set(["activityId", "profileId"])
    if rogueparams:
        raise ParamError("The post activity profile request contained unexpected parameters: %s" % ", ".join(rogueparams))

    validator = StatementValidator()
    if 'activityId' in req_dict['params']:
        validator.validate_iri(req_dict['params']['activityId'], "activityId param for activity profile")
    else:
        err_msg = "Error -- activity_profile - method = %s, but activityId parameter missing.." % req_dict['method']
        raise ParamError(err_msg)

    if not 'profileId' in req_dict['params']:
        err_msg = "Error -- activity_profile - method = %s, but profileId parameter missing.." % req_dict['method']
        raise ParamError(err_msg)
    
    if 'body' not in req_dict:
        err_msg = "Could not find the profile document"
        raise ParamError(err_msg)

    req_dict['profile'] = req_dict.pop('raw_body', req_dict.pop('body', None))
    return req_dict

@auth
def activity_profile_put(req_dict):
    rogueparams = set(req_dict['params']) - set(["activityId", "profileId"])
    if rogueparams:
        raise ParamError("The put activity profile request contained unexpected parameters: %s" % ", ".join(rogueparams))

    validator = StatementValidator()
    if 'activityId' in req_dict['params']:
        validator.validate_iri(req_dict['params']['activityId'], "activityId param for activity profile")
    else:
        err_msg = "Error -- activity_profile - method = %s, but activityId parameter missing.." % req_dict['method']
        raise ParamError(err_msg)

    if not 'profileId' in req_dict['params']:
        err_msg = "Error -- activity_profile - method = %s, but profileId parameter missing.." % req_dict['method']
        raise ParamError(err_msg)    
    
    if 'body' not in req_dict:
        err_msg = "Could not find the profile document"
        raise ParamError(err_msg)

    # Set profile - req_parse converts all request bodies to dict, act profile needs it as string and need to replace single quotes with double quotes
    # b/c of quotation issue when using javascript with activity profile
    req_dict['profile'] = req_dict.pop('raw_body', req_dict.pop('body', None))
    return req_dict

@auth
def activity_profile_get(req_dict):
    rogueparams = set(req_dict['params']) - set(["activityId", "profileId", "since"])
    if rogueparams:
        raise ParamError("The get activity profile request contained unexpected parameters: %s" % ", ".join(rogueparams))

    validator = StatementValidator()
    if 'activityId' in req_dict['params']:
        validator.validate_iri(req_dict['params']['activityId'], "activityId param for activity profile")
    else:
        err_msg = "Error -- activity_profile - method = %s, but activityId parameter missing.." % req_dict['method']
        raise ParamError(err_msg)

    if 'since' in req_dict['params']:
        try:
            parse_datetime(req_dict['params']['since'])
        except (Exception, ISO8601Error):
            raise ParamError("Since parameter was not a valid ISO8601 timestamp")

    return req_dict

@auth
def activity_profile_delete(req_dict):
    rogueparams = set(req_dict['params']) - set(["activityId", "profileId"])
    if rogueparams:
        raise ParamError("The delete activity profile request contained unexpected parameters: %s" % ", ".join(rogueparams))

    validator = StatementValidator()
    if 'activityId' in req_dict['params']:
        validator.validate_iri(req_dict['params']['activityId'], "activityId param for activity profile")
    else:
        err_msg = "Error -- activity_profile - method = %s, but activityId parameter missing.." % req_dict['method']
        raise ParamError(err_msg)

    if not 'profileId' in req_dict['params']:
        err_msg = "Error -- activity_profile - method = %s, but profileId parameter missing.." % req_dict['method']
        raise ParamError(err_msg)    

    return req_dict

@auth
def activities_get(req_dict):
    rogueparams = set(req_dict['params']) - set(["activityId"])
    if rogueparams:
        raise ParamError("The get activities request contained unexpected parameters: %s" % ", ".join(rogueparams))

    try:
        activityId = req_dict['params']['activityId']
    except KeyError:
        err_msg = "Error -- activities - method = %s, but activityId parameter is missing" % req_dict['method']
        raise ParamError(err_msg)

    # Try to retrieve activity, if DNE then return empty else return activity info
    try:
        Activity.objects.get(activity_id=activityId, canonical_version=True)
    except Activity.DoesNotExist:    
        err_msg = "No activity found with ID %s" % activityId
        raise IDNotFoundError(err_msg)

    return req_dict

@auth
def agent_profile_post(req_dict):
    rogueparams = set(req_dict['params']) - set(["agent", "profileId"])
    if rogueparams:
        raise ParamError("The post agent profile request contained unexpected parameters: %s" % ", ".join(rogueparams))

    validator = StatementValidator()
    if 'agent' in req_dict['params']:
        try:
            agent = json.loads(req_dict['params']['agent'])
            req_dict['params']['agent'] = agent
        except Exception:
            raise ParamError("agent param for agent profile is not valid")
        validator.validate_agent(agent, "agent param for agent profile")
    else:
        err_msg = "Error -- agent_profile - method = %s, but agent parameter missing.." % req_dict['method']
        raise ParamError(err_msg)

    if not 'profileId' in req_dict['params']:
        err_msg = "Error -- agent_profile - method = %s, but profileId parameter missing.." % req_dict['method']
        raise ParamError(err_msg)
    
    if 'body' not in req_dict:
        err_msg = "Could not find the profile document"
        raise ParamError(err_msg)

    # Extra validation if oauth
    if req_dict['auth']['type'] == 'oauth':
        validate_oauth_state_or_profile_agent(req_dict, "profile")
    
    # Set profile
    req_dict['profile'] = req_dict.pop('raw_body', req_dict.pop('body', None))

    return req_dict

@auth
def agent_profile_put(req_dict):
    rogueparams = set(req_dict['params']) - set(["agent", "profileId"])
    if rogueparams:
        raise ParamError("The put agent profile request contained unexpected parameters: %s" % ", ".join(rogueparams))

    validator = StatementValidator()
    if 'agent' in req_dict['params']:
        try:
            agent = json.loads(req_dict['params']['agent'])
            req_dict['params']['agent'] = agent
        except Exception:
            raise ParamError("agent param for agent profile is not valid")
        validator.validate_agent(agent, "agent param for agent profile")
    else:
        err_msg = "Error -- agent_profile - method = %s, but agent parameter missing.." % req_dict['method']
        raise ParamError(err_msg)

    if not 'profileId' in req_dict['params']:
        err_msg = "Error -- agent_profile - method = %s, but profileId parameter missing.." % req_dict['method']
        raise ParamError(err_msg) 
    
    if 'body' not in req_dict:
        err_msg = "Could not find the profile document"
        raise ParamError(err_msg)

    # Extra validation if oauth
    if req_dict['auth']['type'] == 'oauth':
        validate_oauth_state_or_profile_agent(req_dict, "profile")
    req_dict['profile'] = req_dict.pop('raw_body', req_dict.pop('body', None))
    return req_dict

@auth
def agent_profile_get(req_dict):
    rogueparams = set(req_dict['params']) - set(["agent", "profileId", "since"])
    if rogueparams:
        raise ParamError("The get agent profile request contained unexpected parameters: %s" % ", ".join(rogueparams))

    validator = StatementValidator()
    if 'agent' in req_dict['params']:
        try:
            agent = json.loads(req_dict['params']['agent'])
            req_dict['params']['agent'] = agent
        except Exception:
            raise ParamError("agent param for agent profile is not valid")
        validator.validate_agent(agent, "agent param for agent profile")
    else:
        err_msg = "Error -- agent_profile - method = %s, but agent parameter missing.." % req_dict['method']
        raise ParamError(err_msg)

    if 'since' in req_dict['params']:
        try:
            parse_datetime(req_dict['params']['since'])
        except (Exception, ISO8601Error):
            raise ParamError("Since parameter was not a valid ISO8601 timestamp")

    # Extra validation if oauth
    if req_dict['auth']['type'] == 'oauth':
        validate_oauth_state_or_profile_agent(req_dict, "profile")
    return req_dict

@auth
def agent_profile_delete(req_dict):
    rogueparams = set(req_dict['params']) - set(["agent", "profileId"])
    if rogueparams:
        raise ParamError("The delete agent profile request contained unexpected parameters: %s" % ", ".join(rogueparams))

    validator = StatementValidator()
    if 'agent' in req_dict['params']:
        try:
            agent = json.loads(req_dict['params']['agent'])
            req_dict['params']['agent'] = agent
        except Exception:
            raise ParamError("agent param for agent profile is not valid")
        validator.validate_agent(agent, "agent param for agent profile")
    else:
        err_msg = "Error -- agent_profile - method = %s, but agent parameter missing.." % req_dict['method']
        raise ParamError(err_msg)

    if not 'profileId' in req_dict['params']:
        err_msg = "Error -- agent_profile - method = %s, but profileId parameter missing.." % req_dict['method']
        raise ParamError(err_msg) 
    
    # Extra validation if oauth
    if req_dict['auth']['type'] == 'oauth':
        validate_oauth_state_or_profile_agent(req_dict, "profile")
    return req_dict

@auth
def agents_get(req_dict):
    rogueparams = set(req_dict['params']) - set(["agent"])
    if rogueparams:
        raise ParamError("The get agent request contained unexpected parameters: %s" % ", ".join(rogueparams))

    try: 
        req_dict['params']['agent']
    except KeyError:
        err_msg = "Error -- agents url, but no agent parameter.. the agent parameter is required"
        raise ParamError(err_msg)

    agent = json.loads(req_dict['params']['agent'])
    params = get_agent_ifp(agent)

    if not Agent.objects.filter(**params).exists():
        raise IDNotFoundError("Error with Agent. The agent partial did not match any agents on record")

    req_dict['agent_ifp'] = params
    return req_dict
