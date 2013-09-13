import json
from datetime import datetime
from functools import wraps
from django.utils.timezone import utc
from django.core.cache import get_cache
from lrs import models
from lrs.util import uri, StatementValidator
from lrs.exceptions import ParamConflict, ParamError, Forbidden, NotFound, BadRequest
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

@auth
@check_oauth
def statements_post(r_dict):
    payload_sha2s = r_dict.get('payload_sha2s', None)

    try:
        validator = StatementValidator.StatementValidator(r_dict['body'])
        msg = validator.validate()
    except Exception, e:
        raise BadRequest(e.message)
    except ParamError, e:
        raise ParamError(e.message)

    # Could be batch POST or single stmt POST
    if type(r_dict['body']) is list:
        for stmt in r_dict['body']:
            if 'attachments' in stmt:
                attachment_data = stmt['attachments']
                validate_attachments(attachment_data, payload_sha2s)
    else:
        if 'attachments' in r_dict['body']:
            attachment_data = r_dict['body']['attachments']
            validate_attachments(attachment_data, payload_sha2s)
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
    # Statement id can must be supplied in query param. If in the body too, it must be the same
    if not 'statementId' in r_dict['params']:
        err_msg = "Error -- statements - method = %s, but no statementId parameter or ID given in statement" % r_dict['method']
        raise ParamError(err_msg)
    else:
        statement_id = r_dict['params']['statementId']

    try:
        statement_body_id = r_dict['body']['id']
    except Exception, e:
        statement_body_id = None

    if statement_body_id and statement_id != statement_body_id:
        err_msg = "Error -- statements - method = %s, param and body ID both given, but do not match" % r_dict['method']
        raise ParamError(err_msg)
    
    # If statement with that ID already exists-raise conflict error
    if check_for_existing_statementId(statement_id):
        err_msg = "A statement with ID %s already exists" % statement_id
        raise ParamConflict(err_msg)

    r_dict['statementId'] = statement_id

    # If there are no other params-raise param error since nothing else is supplied
    if not check_for_no_other_params_supplied(r_dict['body']):
        err_msg = "No other params are supplied with statementId."
        raise ParamError(err_msg)

    try:
        validator = StatementValidator.StatementValidator(r_dict['body'])
        msg = validator.validate()
    except Exception, e:
        raise BadRequest(e.message)
    except ParamError, e:
        raise ParamError(e.message)

    # Need to validate sha2 payloads if there-validator can't do that
    if 'attachments' in r_dict['body']:
        attachment_data = r_dict['body']['attachments']
        payload_sha2s = r_dict.get('payload_sha2s', None)
        validate_attachments(attachment_data, payload_sha2s)
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

    # Extra validation if oauth
    if r_dict['auth']['type'] == 'oauth':
        validate_oauth_state_or_profile_agent(r_dict, "state")    
    return r_dict

@auth
@check_oauth
def activity_state_delete(r_dict):
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
    
    # Extra validation if oauth
    if r_dict['auth']['type'] == 'oauth':
        validate_oauth_state_or_profile_agent(r_dict, "state")
    return r_dict

@auth
@check_oauth
def activity_profile_post(r_dict):
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
    try:
        r_dict['params']['activityId']
    except KeyError:
        err_msg = "Error -- activity_profile - method = %s, but no activityId parameter.. the activityId parameter is required" % r_dict['method']
        raise ParamError(err_msg)
    return r_dict

@auth
@check_oauth
def activity_profile_delete(r_dict):
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
    try:
        r_dict['params']['activityId']
    except KeyError:
        err_msg = "Error -- activities - method = %s, but activityId parameter is missing" % r_dict['method']
        raise ParamError(err_msg)
    return r_dict

@auth
@check_oauth
def agent_profile_post(r_dict):
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
    try: 
        r_dict['params']['agent']
    except KeyError:
        err_msg = "Error -- agents url, but no agent parameter.. the agent parameter is required"
        raise ParamError(err_msg)
    return r_dict
