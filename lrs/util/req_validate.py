import json
from datetime import datetime
from functools import wraps
from django.utils.timezone import utc
from django.core.cache import get_cache
from lrs import models
from lrs.util import uri, StatementValidator, validate_uuid
from lrs.exceptions import ParamConflict, ParamError, Forbidden, NotFound, BadRequest, IDNotFoundError
from Authorization import auth

att_cache = get_cache('attachment_cache')

def check_for_existing_statementId(stmtID):
    return models.Statement.objects.filter(statement_id=stmtID).exists()

def check_for_no_other_params_supplied(query_dict):
    supplied = True
    if len(query_dict) <= 1:
        supplied = False
    return supplied

def check_oauth(func):
    @wraps(func)
    def inner(r_dict, *args, **kwargs):
        auth = r_dict.get('auth', None)
        auth_type = r_dict['auth'].get('type', None) if auth else None
        if auth_type and auth_type == 'oauth':
            validate_oauth_scope(r_dict)    
        return func(r_dict, *args, **kwargs)
    return inner    

def validate_oauth_scope(r_dict):
    method = r_dict['method']
    endpoint = r_dict['auth']['endpoint']
    token = r_dict['auth']['oauth_token']
    scopes = token.scope_to_list()
    err_msg = "Incorrect permissions to %s at %s" % (str(method), str(endpoint))

    validator = {'GET':{"/statements": True if 'all' in scopes or 'all/read' in scopes or 'statements/read' in scopes or 'statements/read/mine' in scopes else False,
                    "/statements/more": True if 'all' in scopes or 'all/read' in scopes or 'statements/read' in scopes or 'statements/read/mine' in scopes else False,
                    "/activities": True if 'all' in scopes or 'all/read' in scopes else False,
                    "/activities/profile": True if 'all' in scopes or 'all/read' in scopes or 'profile' in scopes else False,
                    "/activities/state": True if 'all' in scopes or 'all/read' in scopes or 'state' in scopes else False,
                    "/agents": True if 'all' in scopes or 'all/read' in scopes else False,
                    "/agents/profile": True if 'all' in scopes or 'all/read' in scopes or 'profile' in scopes else False
                },
             'HEAD':{"/statements": True if 'all' in scopes or 'all/read' in scopes or 'statements/read' in scopes or 'statements/read/mine' in scopes else False,
                    "/statements/more": True if 'all' in scopes or 'all/read' in scopes or 'statements/read' in scopes or 'statements/read/mine' in scopes else False,
                    "/activities": True if 'all' in scopes or 'all/read' in scopes else False,
                    "/activities/profile": True if 'all' in scopes or 'all/read' in scopes or 'profile' in scopes else False,
                    "/activities/state": True if 'all' in scopes or 'all/read' in scopes or 'state' in scopes else False,
                    "/agents": True if 'all' in scopes or 'all/read' in scopes else False,
                    "/agents/profile": True if 'all' in scopes or 'all/read' in scopes or 'profile' in scopes else False
                },   
             'PUT':{"/statements": True if 'all' in scopes or 'statements/write' in scopes else False,
                    "/activities": True if 'all' in scopes or 'define' in scopes else False,
                    "/activities/profile": True if 'all' in scopes or 'profile' in scopes else False,
                    "/activities/state": True if 'all' in scopes or 'state' in scopes else False,
                    "/agents": True if 'all' in scopes or 'define' in scopes else False,
                    "/agents/profile": True if 'all' in scopes or 'profile' in scopes else False
                },
             'POST':{"/statements": True if 'all' in scopes or 'statements/write' in scopes else False,
                    "/activities": True if 'all' in scopes or 'define' in scopes else False,
                    "/activities/profile": True if 'all' in scopes or 'profile' in scopes else False,
                    "/activities/state": True if 'all' in scopes or 'state' in scopes else False,
                    "/agents": True if 'all' in scopes or 'define' in scopes else False,
                    "/agents/profile": True if 'all' in scopes or 'profile' in scopes else False
                },
             'DELETE':{"/statements": True if 'all' in scopes or 'statements/write' in scopes else False,
                    "/activities": True if 'all' in scopes or 'define' in scopes else False,
                    "/activities/profile": True if 'all' in scopes or 'profile' in scopes else False,
                    "/activities/state": True if 'all' in scopes or 'state' in scopes else False,
                    "/agents": True if 'all' in scopes or 'define' in scopes else False,
                    "/agents/profile": True if 'all' in scopes or 'profile' in scopes else False
                }
             }

    # Raise forbidden if requesting wrong endpoint or with wrong method than what's in scope
    if not validator[method][endpoint]:
        raise Forbidden(err_msg)

    # Set flag to read only statements owned by user
    if 'statements/read/mine' in scopes:
        r_dict['auth']['statements_mine_only'] = True

    # Set flag for define - allowed to update global representation of activities/agents
    if 'define' in scopes or 'all' in scopes:
        r_dict['auth']['oauth_define'] = True
    else:
        r_dict['auth']['oauth_define'] = False

# Extra agent validation for state and profile
def validate_oauth_state_or_profile_agent(r_dict, endpoint):    
    ag = r_dict['params']['agent']
    token = r_dict['auth']['oauth_token']
    scopes = token.scope_to_list()
    if not 'all' in scopes:
        if not isinstance(ag, dict):
            ag = json.loads(ag)
        try:
            agent = models.Agent.objects.get(**ag)
        except models.Agent.DoesNotExist:
            err_msg = "Agent in %s cannot be found to match user in authorization" % endpoint
            raise NotFound(err_msg)

        if not agent in r_dict['auth']['id'].member.all():
            err_msg = "Authorization doesn't match agent in %s" % endpoint
            raise Forbidden(err_msg)

def validate_void_statement(void_id):
    # Retrieve statement, check if the verb is 'voided' - if not then set the voided flag to true else return error 
    # since you cannot unvoid a statement and should just reissue the statement under a new ID.
    try:
        stmt = models.Statement.objects.get(statement_id=void_id)
    except models.Statement.DoesNotExist:
        err_msg = "Statement with ID %s does not exist" % void_id
        raise IDNotFoundError(err_msg)
        
    if stmt.voided:
        err_msg = "Statement with ID: %s is already voided, cannot unvoid. Please re-issue the statement under a new ID." % void_id
        raise Forbidden(err_msg)

def server_validate_statement_object(stmt_object, auth):
    if stmt_object['objectType'] == 'StatementRef' and not check_for_existing_statementId(stmt_object['id']):
            err_msg = "No statement with ID %s was found" % stmt_object['id']
            raise IDNotFoundError(err_msg)
    elif stmt_object['objectType'] == 'Activity' or 'objectType' not in stmt_object:
        if 'definition' in stmt_object:
            try:
                activity = models.Activity.objects.get(activity_id=stmt_object['id'], global_representation=True)
            except models.Activity.DoesNotExist:
                pass
            else:
                if auth:
                    if auth['id'].__class__.__name__ == 'Agent':
                        auth_name = auth['id'].name
                    else:
                        auth_name = auth['id'].username
                else:
                    auth_name = None
                if activity.authoritative != '' and activity.authoritative != auth_name:
                    err_msg = "This ActivityID already exists, and you do not have the correct authority to create or update it."
                    raise Forbidden(err_msg)

#Make sure initial data being received is JSON
def parse(data):
    try:
        params = json.loads(data)
    except Exception, e:
        err_msg = "Error parsing the Statement object. Expecting json. Received: %s which is %s" % (data, type(data))
        raise ParamError(err_msg) 
    return params

# Retrieve JSON data from ID
def get_data_from_act_id(act_id):
    resolves = True
    act_json = {}

    # See if id resolves
    try:
        req = urllib2.Request(act_id)
        req.add_header('Accept', 'application/json, */*')
        act_resp = urllib2.urlopen(req, timeout=settings.ACTIVITY_ID_RESOLVE_TIMEOUT)
    except Exception, e:
        # Doesn't resolve-hopefully data is in payload
        resolves = False
    else:
        # If it resolves then try parsing JSON from it
        try:
            act_json = json.loads(act_resp.read())
        except Exception, e:
            # Resolves but no data to retrieve - this is OK
            pass
    return act_json

def server_validation(stmt_set, auth, payload_sha2s):
    # Could be batch POST or single stmt POST
    if type(stmt_set) is list:
        auth_validated = False
        for stmt in stmt_set:
            if 'id' in stmt:
                # If statement with that ID already exists-raise conflict error
                statement_id = stmt['id']
                if check_for_existing_statementId(statement_id):
                    err_msg = "A statement with ID %s already exists" % statement_id
                    raise ParamConflict(err_msg)
            
            server_validate_statement_object(stmt['object'], auth)

            if stmt['verb']['id'] == 'http://adlnet.gov/expapi/verbs/voided':
                validate_void_statement(stmt['object']['id'])

            if not 'objectType' in stmt['object'] or stmt['object']['objectType'] == 'Activity':
                activity_data = get_data_from_act_id(stmt['object']['id'])
                activity_data['id'] = stmt['object']['id']

                try:
                    validator = StatementValidator.StatementValidator(None)
                    validator.validate_activity(activity_data)
                except Exception, e:
                    raise BadRequest(e.message)
                except ParamError, e:
                    raise ParamError(e.message)

            if 'authority' in stmt:
                # If they try using a non-oauth group that already exists-throw error
                if stmt['authority']['objectType'] == 'Group' and not 'oauth_identifier' in stmt['authority']:
                    err_msg = "Statements cannot have a non-Oauth group as the authority"
                    raise ParamError(err_msg)
            else:
                if not auth_validated:
                    if auth:
                        if auth['id'].__class__.__name__ == 'Agent' and not auth['id'].oauth_identifier:
                            err_msg = "Statements cannot have a non-Oauth group as the authority"
                            raise ParamError(err_msg)
                        auth_validated = True

            if 'attachments' in stmt:
                attachment_data = stmt['attachments']
                validate_attachments(attachment_data, payload_sha2s)
    else:
        if 'id' in stmt_set:
            statement_id = stmt_set['id']
            if check_for_existing_statementId(statement_id):
                err_msg = "A statement with ID %s already exists" % statement_id
                raise ParamConflict(err_msg)

        server_validate_statement_object(stmt_set['object'], auth)

        if stmt_set['verb']['id'] == 'http://adlnet.gov/expapi/verbs/voided':
            validate_void_statement(stmt_set['object']['id'])

        if not 'objectType' in stmt_set['object'] or stmt_set['object']['objectType'] == 'Activity':
            activity_data = get_data_from_act_id(stmt_set['object']['id'])
            activity_data['id'] = stmt_set['object']['id']

            try:
                validator = StatementValidator.StatementValidator(None)
                validator.validate_activity(activity_data)
            except Exception, e:
                raise BadRequest(e.message)
            except ParamError, e:
                raise ParamError(e.message)

        if 'authority' in stmt_set:
            # If they try using a non-oauth group that already exists-throw error
            if stmt_set['authority']['objectType'] == 'Group' and not 'oauth_identifier' in stmt_set['authority']:
                err_msg = "Statements cannot have a non-Oauth group as the authority"
                raise ParamError(err_msg)
        else:
            if auth:
                if auth['id'].__class__.__name__ == 'Agent' and not auth['id'].oauth_identifier:
                    err_msg = "Statements cannot have a non-Oauth group as the authority"
                    raise ParamError(err_msg)

        if 'attachments' in stmt_set:
            attachment_data = stmt_set['attachments']
            validate_attachments(attachment_data, payload_sha2s)

@auth
@check_oauth
def statements_post(r_dict):
    if r_dict['params'].keys():
        raise ParamError("The post statements request contained unexpected parameters: %s" % ", ".join(r_dict['params'].keys()))

    payload_sha2s = r_dict.get('payload_sha2s', None)

    if isinstance(r_dict['body'], basestring):
        from lrs.util import convert_to_dict
        r_dict['body'] = convert_to_dict(r_dict['body'])

    try:
        validator = StatementValidator.StatementValidator(r_dict['body'])
        msg = validator.validate()
    except Exception, e:
        raise BadRequest(e.message)
    except ParamError, e:
        raise ParamError(e.message)

    server_validation(r_dict['body'], r_dict.get('auth', None), r_dict.get('payload_sha2s', None))

    return r_dict

@auth
@check_oauth
def statements_more_get(r_dict):
    if not 'more_id' in r_dict:
        err_msg = "Missing more_id while trying to hit /more endpoint"
        raise ParamError(err_msg)
    return r_dict

@auth
@check_oauth
def statements_get(r_dict):
    rogueparams = set(r_dict['params']) - set(["statementId","voidedStatementId","agent", "verb", "activity", "registration", 
                       "related_activities", "related_agents", "since",
                       "until", "limit", "format", "attachments", "ascending"])
    if rogueparams:
        raise ParamError("The get statements request contained unexpected parameters: %s" % ", ".join(rogueparams))

    formats = ['exact', 'canonical', 'ids']
    if 'params' in r_dict and 'format' in r_dict['params']:
        if r_dict['params']['format'] not in formats:
            raise ParamError("The format filter value (%s) was not one of the known values: %s" % (r_dict['params']['format'], ','.join(formats)))
    else:
        r_dict['params']['format'] = 'exact'     
    
    if 'params' in r_dict and ('statementId' in r_dict['params'] or 'voidedStatementId' in r_dict['params']):
        if 'statementId' in r_dict['params'] and 'voidedStatementId' in r_dict['params']:
            err_msg = "Cannot have both statementId and voidedStatementId in a GET request"
            raise ParamError(err_msg)
        
        not_allowed = ["agent", "verb", "activity", "registration", 
                       "related_activities", "related_agents", "since",
                       "until", "limit", "ascending"]
        bad_keys = set(not_allowed) & set(r_dict['params'].keys())
        if bad_keys:
            err_msg = "Cannot have %s in a GET request only 'format' and/or 'attachments' are allowed with 'statementId' and 'voidedStatementId'" % ', '.join(bad_keys)
            raise ParamError(err_msg)

    # Django converts all query values to string - make boolean depending on if client wants attachments or not
    # Only need to do this in GET b/c GET/more will have it saved in pickle information
    if 'params' in r_dict and 'attachments' in r_dict['params']:
        if r_dict['params']['attachments'] == 'True':
            r_dict['params']['attachments'] = True
        else:
            r_dict['params']['attachments'] = False
    else:
        r_dict['params']['attachments'] = False
   
    return r_dict

@auth
@check_oauth
def statements_put(r_dict):
    # Find any unexpected parameters
    rogueparams = set(r_dict['params']) - set(["statementId"])
    if rogueparams:
        raise ParamError("The put statements request contained unexpected parameters: %s" % ", ".join(rogueparams))

    # Statement id can must be supplied in query param. If in the body too, it must be the same
    if not 'statementId' in r_dict['params']:
        err_msg = "Error -- statements - method = %s, but no statementId parameter or ID given in statement" % r_dict['method']
        raise ParamError(err_msg)
    else:
        statement_id = r_dict['params']['statementId']

    # Convert data so it can be parsed
    if isinstance(r_dict['body'], basestring):
        from lrs.util import convert_to_dict
        r_dict['body'] = convert_to_dict(r_dict['body'])

    # Try to get id if in body
    try:
        statement_body_id = r_dict['body']['id']
    except Exception, e:
        statement_body_id = None

    # If ids exist in both places, check if they are equal
    if statement_body_id and statement_id != statement_body_id:
        err_msg = "Error -- statements - method = %s, param and body ID both given, but do not match" % r_dict['method']
        raise ParamError(err_msg)

    # If statement with that ID already exists-raise conflict error
    if check_for_existing_statementId(statement_id):
        err_msg = "A statement with ID %s already exists" % statement_id
        raise ParamConflict(err_msg)
    
    # Set id inside of statement with param id
    if not statement_body_id:
        r_dict['body']['id'] = statement_id

    # If there are no other params-raise param error since nothing else is supplied
    if not check_for_no_other_params_supplied(r_dict['body']):
        err_msg = "No other params are supplied with statementId."
        raise ParamError(err_msg)

    # Validate statement in body
    try:
        validator = StatementValidator.StatementValidator(r_dict['body'])
        msg = validator.validate()
    except Exception, e:
        raise BadRequest(e.message)
    except ParamError, e:
        raise ParamError(e.message)

    server_validation(r_dict['body'], r_dict.get('auth', None), r_dict.get('payload_sha2s', None))

    return r_dict

def validate_attachments(attachment_data, payload_sha2s):
    # For each attachment that is in the actual statement
    for attachment in attachment_data:
        # If the attachment data has a sha2 field, must validate it against the payload data
        if 'sha2' in attachment:
            sha2 = attachment['sha2']
            # Check if the sha2 field is a key in the payload dict
            if not sha2 in payload_sha2s:
                err_msg = "Could not find attachment payload with sha: %s" % sha2
                raise ParamError(err_msg)

@auth
@check_oauth
def activity_state_post(r_dict):
    rogueparams = set(r_dict['params']) - set(["activityId", "agent", "stateId", "registration"])
    if rogueparams:
        raise ParamError("The post activity state request contained unexpected parameters: %s" % ", ".join(rogueparams))

    try:
        r_dict['params']['activityId']
    except KeyError:
        err_msg = "Error -- activity_state - method = %s, but activityId parameter is missing.." % r_dict['method']
        raise ParamError(err_msg)
    if not 'activity_state_agent_validated' in r_dict:
        try:
            r_dict['params']['agent']
        except KeyError:
            err_msg = "Error -- activity_state - method = %s, but agent parameter is missing.." % r_dict['method']
            raise ParamError(err_msg)
    try:
        r_dict['params']['stateId']
    except KeyError:
        err_msg = "Error -- activity_state - method = %s, but stateId parameter is missing.." % r_dict['method']
        raise ParamError(err_msg)

    if 'params' in r_dict and 'registration' in r_dict['params']:
        if not validate_uuid(r_dict['params']['registration']):
            raise ParamError("%s is not a valid uuid for the registration parameter")

    if 'headers' not in r_dict or ('CONTENT_TYPE' not in r_dict['headers'] or r_dict['headers']['CONTENT_TYPE'] != "application/json"):
        err_msg = "The content type for activity state POSTs must be application/json"
        raise ParamError(err_msg)
    
    # Must have body included for state
    if 'body' not in r_dict:
        err_msg = "Could not find the state"
        raise ParamError(err_msg)
    
    # Extra validation if oauth
    if r_dict['auth']['type'] == 'oauth':
        validate_oauth_state_or_profile_agent(r_dict, "state")

    # Set state
    r_dict['state'] = r_dict.pop('raw_body', r_dict.pop('body', None))
    return r_dict

@auth
@check_oauth
def activity_state_put(r_dict):
    rogueparams = set(r_dict['params']) - set(["activityId", "agent", "stateId", "registration"])
    if rogueparams:
        raise ParamError("The put activity state request contained unexpected parameters: %s" % ", ".join(rogueparams))

    try:
        r_dict['params']['activityId']
    except KeyError:
        err_msg = "Error -- activity_state - method = %s, but activityId parameter is missing.." % r_dict['method']
        raise ParamError(err_msg)
    if not 'activity_state_agent_validated' in r_dict:
        try:
            r_dict['params']['agent']
        except KeyError:
            err_msg = "Error -- activity_state - method = %s, but agent parameter is missing.." % r_dict['method']
            raise ParamError(err_msg)
    try:
        r_dict['params']['stateId']
    except KeyError:
        err_msg = "Error -- activity_state - method = %s, but stateId parameter is missing.." % r_dict['method']
        raise ParamError(err_msg)

    if 'params' in r_dict and 'registration' in r_dict['params']:
        if not validate_uuid(r_dict['params']['registration']):
            raise ParamError("%s is not a valid uuid for the registration parameter")
    
    # Must have body included for state
    if 'body' not in r_dict:
        err_msg = "Could not find the state"
        raise ParamError(err_msg)
    
    # Extra validation if oauth
    if r_dict['auth']['type'] == 'oauth':
        validate_oauth_state_or_profile_agent(r_dict, "state")

    # Set state
    r_dict['state'] = r_dict.pop('raw_body', r_dict.pop('body', None))
    return r_dict

@auth
@check_oauth
def activity_state_get(r_dict):
    rogueparams = set(r_dict['params']) - set(["activityId", "agent", "stateId", "registration", "since"])
    if rogueparams:
        raise ParamError("The get activity state request contained unexpected parameters: %s" % ", ".join(rogueparams))

    try:
        r_dict['params']['activityId']
    except KeyError:
        err_msg = "Error -- activity_state - method = %s, but activityId parameter is missing.." % r_dict['method']
        raise ParamError(err_msg)
    if not 'activity_state_agent_validated' in r_dict:
        try:
            r_dict['params']['agent']
        except KeyError:
            err_msg = "Error -- activity_state - method = %s, but agent parameter is missing.." % r_dict['method']
            raise ParamError(err_msg)

    if 'params' in r_dict and 'registration' in r_dict['params']:
        if not validate_uuid(r_dict['params']['registration']):
            raise ParamError("%s is not a valid uuid for the registration parameter")

    # Extra validation if oauth
    if r_dict['auth']['type'] == 'oauth':
        validate_oauth_state_or_profile_agent(r_dict, "state")    
    return r_dict

@auth
@check_oauth
def activity_state_delete(r_dict):
    rogueparams = set(r_dict['params']) - set(["activityId", "agent", "stateId", "registration"])
    if rogueparams:
        raise ParamError("The delete activity state request contained unexpected parameters: %s" % ", ".join(rogueparams))

    try:
        r_dict['params']['activityId']
    except KeyError:
        err_msg = "Error -- activity_state - method = %s, but activityId parameter is missing.." % r_dict['method']
        raise ParamError(err_msg)
    if not 'activity_state_agent_validated' in r_dict:
        try:
            r_dict['params']['agent']
        except KeyError:
            err_msg = "Error -- activity_state - method = %s, but agent parameter is missing.." % r_dict['method']
            raise ParamError(err_msg)

    if 'params' in r_dict and 'registration' in r_dict['params']:
        if not validate_uuid(r_dict['params']['registration']):
            raise ParamError("%s is not a valid uuid for the registration parameter")
    
    # Extra validation if oauth
    if r_dict['auth']['type'] == 'oauth':
        validate_oauth_state_or_profile_agent(r_dict, "state")
    return r_dict

@auth
@check_oauth
def activity_profile_post(r_dict):
    rogueparams = set(r_dict['params']) - set(["activityId", "profileId"])
    if rogueparams:
        raise ParamError("The post activity profile request contained unexpected parameters: %s" % ", ".join(rogueparams))

    try:
        r_dict['params']['activityId']
    except KeyError:
        err_msg = "Error -- activity_profile - method = %s, but activityId parameter missing.." % r_dict['method']
        raise ParamError(err_msg)    
    try:
        r_dict['params']['profileId']
    except KeyError:
        err_msg = "Error -- activity_profile - method = %s, but profileId parameter missing.." % r_dict['method']
        raise ParamError(err_msg)

    if 'headers' not in r_dict or ('CONTENT_TYPE' not in r_dict['headers'] or r_dict['headers']['CONTENT_TYPE'] != "application/json"):
        err_msg = "The content type for activity profile POSTs must be application/json"
        raise ParamError(err_msg)
    
    if 'body' not in r_dict:
        err_msg = "Could not find the profile document"
        raise ParamError(err_msg)

    r_dict['profile'] = r_dict.pop('raw_body', r_dict.pop('body', None))
    return r_dict

@auth
@check_oauth
def activity_profile_put(r_dict):
    rogueparams = set(r_dict['params']) - set(["activityId", "profileId"])
    if rogueparams:
        raise ParamError("The put activity profile request contained unexpected parameters: %s" % ", ".join(rogueparams))

    try:
        r_dict['params']['activityId']
    except KeyError:
        err_msg = "Error -- activity_profile - method = %s, but activityId parameter missing.." % r_dict['method']
        raise ParamError(err_msg)    
    try:
        r_dict['params']['profileId']
    except KeyError:
        err_msg = "Error -- activity_profile - method = %s, but profileId parameter missing.." % r_dict['method']
        raise ParamError(err_msg)
    
    if 'body' not in r_dict:
        err_msg = "Could not find the profile document"
        raise ParamError(err_msg)

    # Set profile - req_parse converts all request bodies to dict, act profile needs it as string and need to replace single quotes with double quotes
    # b/c of quotation issue when using javascript with activity profile
    r_dict['profile'] = r_dict.pop('raw_body', r_dict.pop('body', None))
    return r_dict

@auth
@check_oauth
def activity_profile_get(r_dict):
    rogueparams = set(r_dict['params']) - set(["activityId", "profileId", "since"])
    if rogueparams:
        raise ParamError("The get activity profile request contained unexpected parameters: %s" % ", ".join(rogueparams))

    try:
        r_dict['params']['activityId']
    except KeyError:
        err_msg = "Error -- activity_profile - method = %s, but no activityId parameter.. the activityId parameter is required" % r_dict['method']
        raise ParamError(err_msg)
    return r_dict

@auth
@check_oauth
def activity_profile_delete(r_dict):
    rogueparams = set(r_dict['params']) - set(["activityId", "profileId"])
    if rogueparams:
        raise ParamError("The delete activity profile request contained unexpected parameters: %s" % ", ".join(rogueparams))

    try:
        r_dict['params']['activityId']
    except KeyError:
        err_msg = "Error -- activity_profile - method = %s, but no activityId parameter.. the activityId parameter is required" % r_dict['method']
        raise ParamError(err_msg)
    try:
        r_dict['params']['profileId']
    except KeyError:
        err_msg = "Error -- activity_profile - method = %s, but no profileId parameter.. the profileId parameter is required" % r_dict['method']
        raise ParamError(err_msg)
    return r_dict

@auth
@check_oauth
def activities_get(r_dict):
    rogueparams = set(r_dict['params']) - set(["activityId"])
    if rogueparams:
        raise ParamError("The get activities request contained unexpected parameters: %s" % ", ".join(rogueparams))

    try:
        r_dict['params']['activityId']
    except KeyError:
        err_msg = "Error -- activities - method = %s, but activityId parameter is missing" % r_dict['method']
        raise ParamError(err_msg)
    return r_dict

@auth
@check_oauth
def agent_profile_post(r_dict):
    rogueparams = set(r_dict['params']) - set(["agent", "profileId"])
    if rogueparams:
        raise ParamError("The post agent profile request contained unexpected parameters: %s" % ", ".join(rogueparams))

    try: 
        r_dict['params']['agent']
    except KeyError:
        err_msg = "Error -- agent_profile - method = %s, but agent parameter missing.." % r_dict['method']
        raise ParamError(err_msg)
    try:
        r_dict['params']['profileId']
    except KeyError:
        err_msg = "Error -- agent_profile - method = %s, but profileId parameter missing.." % r_dict['method']
        raise ParamError(msg)

    if 'headers' not in r_dict or ('CONTENT_TYPE' not in r_dict['headers'] or r_dict['headers']['CONTENT_TYPE'] != "application/json"):
        err_msg = "The content type for agent profile POSTs must be application/json"
        raise ParamError(err_msg)
    
    if 'body' not in r_dict:
        err_msg = "Could not find the profile document"
        raise ParamError(err_msg)

    # Extra validation if oauth
    if r_dict['auth']['type'] == 'oauth':
        validate_oauth_state_or_profile_agent(r_dict, "profile")
    
    # Set profile
    r_dict['profile'] = r_dict.pop('raw_body', r_dict.pop('body', None))

    return r_dict

@auth
@check_oauth
def agent_profile_put(r_dict):
    rogueparams = set(r_dict['params']) - set(["agent", "profileId"])
    if rogueparams:
        raise ParamError("The put agent profile request contained unexpected parameters: %s" % ", ".join(rogueparams))

    try: 
        r_dict['params']['agent']
    except KeyError:
        err_msg = "Error -- agent_profile - method = %s, but agent parameter missing.." % r_dict['method']
        raise ParamError(err_msg)
    try:
        r_dict['params']['profileId']
    except KeyError:
        err_msg = "Error -- agent_profile - method = %s, but profileId parameter missing.." % r_dict['method']
        raise ParamError(err_msg)
    
    if 'body' not in r_dict:
        err_msg = "Could not find the profile document"
        raise ParamError(err_msg)

    # Extra validation if oauth
    if r_dict['auth']['type'] == 'oauth':
        validate_oauth_state_or_profile_agent(r_dict, "profile")
    r_dict['profile'] = r_dict.pop('raw_body', r_dict.pop('body', None))
    return r_dict

@auth
@check_oauth
def agent_profile_get(r_dict):
    rogueparams = set(r_dict['params']) - set(["agent", "profileId", "since"])
    if rogueparams:
        raise ParamError("The get agent profile request contained unexpected parameters: %s" % ", ".join(rogueparams))

    try: 
        r_dict['params']['agent']
    except KeyError:
        err_msg = "Error -- agent_profile - method = %s, but agent parameter missing.. the agent parameter is required" % r_dict['method']
        raise ParamError(err_msg)

    # Extra validation if oauth
    if r_dict['auth']['type'] == 'oauth':
        validate_oauth_state_or_profile_agent(r_dict, "profile")
    return r_dict

@auth
@check_oauth
def agent_profile_delete(r_dict):
    rogueparams = set(r_dict['params']) - set(["agent", "profileId"])
    if rogueparams:
        raise ParamError("The delete agent profile request contained unexpected parameters: %s" % ", ".join(rogueparams))

    try: 
        r_dict['params']['agent']
    except KeyError:
        err_msg = "Error -- agent_profile - method = %s, but no agent parameter.. the agent parameter is required" % r_dict['method']
        raise ParamError(err_msg)
    try:
        r_dict['params']['profileId']
    except KeyError:
        err_msg = "Error -- agent_profile - method = %s, but no profileId parameter.. the profileId parameter is required" % r_dict['method']
        raise ParamError(err_msg)
    
    # Extra validation if oauth
    if r_dict['auth']['type'] == 'oauth':
        validate_oauth_state_or_profile_agent(r_dict, "profile")
    return r_dict

@auth
@check_oauth
def agents_get(r_dict):
    rogueparams = set(r_dict['params']) - set(["agent"])
    if rogueparams:
        raise ParamError("The get agent request contained unexpected parameters: %s" % ", ".join(rogueparams))

    try: 
        r_dict['params']['agent']
    except KeyError:
        err_msg = "Error -- agents url, but no agent parameter.. the agent parameter is required"
        raise ParamError(err_msg)
    return r_dict
