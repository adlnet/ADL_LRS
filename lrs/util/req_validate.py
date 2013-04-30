import json
from datetime import datetime
from functools import wraps
from django.utils.decorators import decorator_from_middleware
from django.utils.timezone import utc
from lrs import models
from lrs.exceptions import ParamConflict, ParamError, Forbidden, NotFound
from Authorization import auth
import logging
import pdb
import pprint

logger = logging.getLogger('user_system_actions')

def check_for_existing_statementId(stmtID):
    exists = False
    stmt = models.statement.objects.filter(statement_id=stmtID)
    if stmt:
        exists = True
    return exists

def check_for_no_other_params_supplied(query_dict):
    supplied = True
    if len(query_dict) <= 1:
        supplied = False
    return supplied

def log_exception(log_dict, err_msg, func_name):
    log_dict['message'] = err_msg + " in %s" % func_name
    logger.exception(msg=log_dict)

def update_log_status(log_dict, status):
    parent_action = models.SystemAction.objects.get(id=log_dict['parent_id'])
    parent_action.status_code = status
    parent_action.save()

def log_parent_action(method, endpoint):
    def inner(func):
        @wraps(func)
        def wrapper(r_dict, *args, **kwargs):
            request_time = datetime.utcnow().replace(tzinfo=utc).isoformat()
            if 'auth' in r_dict and r_dict['auth']:
                user_action = models.SystemAction(level=models.SystemAction.REQUEST, timestamp=request_time,
                    message='%s /%s' % (method, endpoint), content_object=r_dict['auth'])
            else:
                user_action = models.SystemAction(level=models.SystemAction.REQUEST, timestamp=request_time,
                    message='%s /%s' % (method, endpoint))
            user_action.save()
            r_dict['initial_user_action'] = {'user': user_action.content_object, 'parent_id': user_action.id}         
            return func(r_dict, *args, **kwargs)
        return wrapper
    return inner

def check_oauth(func):
    @wraps(func)
    def inner(r_dict, *args, **kwargs):
        if r_dict['lrs_auth'] == 'oauth':
            validate_oauth_scope(r_dict)    
        return func(r_dict, *args, **kwargs)
    return inner    

def validate_oauth_scope(r_dict):
    log_dict = r_dict['initial_user_action']
    method = r_dict['method']
    endpoint = r_dict['endpoint']
    token = r_dict['oauth_token']
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
        log_exception(log_dict, err_msg, validate_oauth_scope.__name__)
        update_log_status(log_dict, 403)
        raise Forbidden(err_msg)

    # Set flag to read only statements owned by user
    if 'statements/read/mine' in scopes:
        r_dict['statements_mine_only'] = True

    # Set flag for define - allowed to update global representation of activities/agents
    if 'define' in scopes or 'all' in scopes:
        r_dict['oauth_define'] = True
    else:
        r_dict['oauth_define'] = False

# Extra agent validation for state and profile
def validate_oauth_state_or_profile_agent(r_dict, endpoint):
    log_dict = r_dict['initial_user_action']    
    ag = r_dict['agent']
    token = r_dict['oauth_token']
    scopes = token.scope_to_list()
    if not 'all' in scopes:
        if not isinstance(ag, dict):
            ag = json.loads(ag)
        try:
            agent = models.agent.objects.get(**ag)
        except models.agent.DoesNotExist:
            err_msg = "Agent in %s cannot be found to match user in authorization" % endpoint
            log_exception(log_dict, err_msg, validate_oauth_state_or_profile_agent.__name__)
            update_log_status(log_dict, 404)
            raise NotFound(err_msg)

        if not agent in r_dict['auth'].member.all():
            err_msg = "Authorization doesn't match agent in %s" % endpoint
            log_exception(log_dict, err_msg, validate_oauth_state_or_profile_agent.__name__)
            update_log_status(log_dict, 403)
            raise Forbidden(err_msg)

@auth
@log_parent_action(method='POST', endpoint='statements')
@check_oauth
def statements_post(r_dict):
    return r_dict

@auth
@log_parent_action(method='GET', endpoint='statements/more')
@check_oauth
def statements_more_get(r_dict):
    log_dict = r_dict['initial_user_action']
    if not 'more_id' in r_dict:
        err_msg = "Missing more_id"
        log_exception(log_dict, err_msg, statements_more_get.__name__)
        update_log_status(log_dict, 400)
        raise ParamError(err_msg)
    return r_dict

@auth
@log_parent_action(method='GET', endpoint='statements')
@check_oauth
def statements_get(r_dict):
    formats = ['exact', 'canonical', 'ids']
    if 'format' in r_dict:
        if r_dict['format'] not in formats:
            raise ParamError("The format filter value (%s) was not one of the known values: %s" % (r_dict['format'], ','.join(formats)))
    else:
        r_dict['format'] = 'exact'

    # if this was the weird POST/GET then put the format in the body
    # so that retrieve_statement finds it
    if 'body' in r_dict:
        r_dict['body']['format'] = r_dict['format']        
    
    if 'statementId' in r_dict or 'voidedStatementId' in r_dict:
        if 'statementId' in r_dict and 'voidedStatementId' in r_dict:
            err_msg = "Cannot have both statementId and voidedStatementId in a GET request"
            log_exception(log_dict, err_msg, statements_put.__name__)
            update_log_status(log_dict, 400)
            raise ParamError(err_msg)
        
        not_allowed = ["agent", "verb", "activity", "registration", 
                       "related_activities", "related_agents", "since",
                       "until", "limit", "ascending"]
        bad_keys = set(not_allowed) & set(r_dict.keys())
        if bad_keys:
            err_msg = "Cannot have %s in a GET request only 'format' and/or 'attachements' are allowed with 'statementId' and 'voidedStatementId'" % ', '.join(bad_keys)
            log_exception(log_dict, err_msg, statements_put.__name__)
            update_log_status(log_dict, 400)
            raise ParamError(err_msg)
    return r_dict

@auth
@log_parent_action(method='PUT', endpoint='statements')
@check_oauth
def statements_put(r_dict):
    log_dict = r_dict['initial_user_action']
    # Must have statementId param-if not raise paramerror
    try:
        statement_id = r_dict['statementId']
    except KeyError:
        err_msg = "Error -- statements - method = %s, but statementId paramater is missing" % r_dict['method']
        log_exception(log_dict, err_msg, statements_put.__name__)
        update_log_status(log_dict, 400)
        raise ParamError(err_msg)
    
    # If statement with that ID already exists-raise conflict error
    if check_for_existing_statementId(statement_id):
        err_msg = "StatementId conflict"
        log_exception(log_dict, err_msg, statements_put.__name__)
        update_log_status(log_dict, 409)
        raise ParamConflict(err_msg)

    # If there are no other params-raise param error since nothing else is supplied
    if not check_for_no_other_params_supplied(r_dict['body']):
        err_msg = "No Content supplied"
        log_exception(log_dict, err_msg, statements_put.__name__)
        update_log_status(log_dict, 400)
        raise ParamError(err_msg)

    return r_dict

@auth
@log_parent_action(method='POST', endpoint='activities/state')
@check_oauth
def activity_state_post(r_dict):
    log_dict = r_dict['initial_user_action']
    try:
        r_dict['activityId']
    except KeyError:
        err_msg = "Error -- activity_state - method = %s, but activityId parameter is missing.." % r_dict['method']
        log_exception(log_dict, err_msg, activity_state_post.__name__)
        update_log_status(log_dict, 400)
        raise ParamError(err_msg)
    if not 'activity_state_agent_validated' in r_dict:
        try:
            r_dict['agent']
        except KeyError:
            err_msg = "Error -- activity_state - method = %s, but agent parameter is missing.." % r_dict['method']
            log_exception(log_dict, err_msg, activity_state_post.__name__)
            update_log_status(log_dict, 400)
            raise ParamError(err_msg)
    try:
        r_dict['stateId']
    except KeyError:
        err_msg = "Error -- activity_state - method = %s, but stateId parameter is missing.." % r_dict['method']
        log_exception(log_dict, err_msg, activity_state_post.__name__)
        update_log_status(log_dict, 400)
        raise ParamError(err_msg)

    if 'CONTENT_TYPE' not in r_dict or r_dict['CONTENT_TYPE'] != "application/json":
        err_msg = "The content type for activity state POSTs must be application/json"
        log_exception(log_dict, err_msg, activity_state_post.__name__)
        update_log_status(log_dict, 400)
        raise ParamError(err_msg)
    
    # Must have body included for state
    if 'body' not in r_dict:
        err_msg = "Could not find the state"
        log_exception(log_dict, err_msg, activity_state_post.__name__)
        update_log_status(log_dict, 400)
        raise ParamError(err_msg)
    
    # Extra validation if oauth
    if r_dict['lrs_auth'] == 'oauth':
        validate_oauth_state_or_profile_agent(r_dict, "state")

    # Set state
    body_dict = r_dict.pop('raw_body', r_dict.pop('body', None))
    try:
        json.loads(body_dict)
        r_dict['state'] = body_dict
    except Exception as e:
        err_msg = "Could not parse the content into JSON"
        log_exception(log_dict, err_msg, activity_state_post.__name__)
        update_log_status(log_dict, 400)
        raise ParamError("\n".join((err_msg, e)))
    return r_dict

@auth
@log_parent_action(method='PUT', endpoint='activities/state')
@check_oauth
def activity_state_put(r_dict):
    log_dict = r_dict['initial_user_action']
    try:
        r_dict['activityId']
    except KeyError:
        err_msg = "Error -- activity_state - method = %s, but activityId parameter is missing.." % r_dict['method']
        log_exception(log_dict, err_msg, activity_state_put.__name__)
        update_log_status(log_dict, 400)
        raise ParamError(err_msg)
    if not 'activity_state_agent_validated' in r_dict:
        try:
            r_dict['agent']
        except KeyError:
            err_msg = "Error -- activity_state - method = %s, but agent parameter is missing.." % r_dict['method']
            log_exception(log_dict, err_msg, activity_state_put.__name__)
            update_log_status(log_dict, 400)
            raise ParamError(err_msg)
    try:
        r_dict['stateId']
    except KeyError:
        err_msg = "Error -- activity_state - method = %s, but stateId parameter is missing.." % r_dict['method']
        log_exception(log_dict, err_msg, activity_state_put.__name__)
        update_log_status(log_dict, 400)
        raise ParamError(err_msg)
    
    # Must have body included for state
    if 'body' not in r_dict:
        err_msg = "Could not find the profile"
        log_exception(log_dict, err_msg, activity_state_put.__name__)
        update_log_status(log_dict, 400)
        raise ParamError(err_msg)
    
    # Extra validation if oauth
    if r_dict['lrs_auth'] == 'oauth':
        validate_oauth_state_or_profile_agent(r_dict, "state")

    # Set state
    r_dict['state'] = r_dict.pop('body')
    return r_dict

@auth
@log_parent_action(method='GET', endpoint='activities/state')
@check_oauth
def activity_state_get(r_dict):
    log_dict = r_dict['initial_user_action']
    try:
        r_dict['activityId']
    except KeyError:
        err_msg = "Error -- activity_state - method = %s, but activityId parameter is missing.." % r_dict['method']
        log_exception(log_dict, err_msg, activity_state_get.__name__)
        update_log_status(log_dict, 400)
        raise ParamError(err_msg)
    if not 'activity_state_agent_validated' in r_dict:
        try:
            r_dict['agent']
        except KeyError:
            err_msg = "Error -- activity_state - method = %s, but agent parameter is missing.." % r_dict['method']
            log_exception(log_dict, err_msg, activity_state_get.__name__)
            update_log_status(log_dict, 400)
            raise ParamError(err_msg)

    # Extra validation if oauth
    if r_dict['lrs_auth'] == 'oauth':
        validate_oauth_state_or_profile_agent(r_dict, "state")    
    return r_dict

@auth
@log_parent_action(method='DELETE', endpoint='activities/state')
@check_oauth
def activity_state_delete(r_dict):
    log_dict = r_dict['initial_user_action']
    try:
        r_dict['activityId']
    except KeyError:
        err_msg = "Error -- activity_state - method = %s, but activityId parameter is missing.." % r_dict['method']
        log_exception(log_dict, err_msg, activity_state_delete.__name__)
        update_log_status(log_dict, 400)
        raise ParamError(err_msg)
    if not 'activity_state_agent_validated' in r_dict:
        try:
            r_dict['agent']
        except KeyError:
            err_msg = "Error -- activity_state - method = %s, but agent parameter is missing.." % r_dict['method']
            log_exception(log_dict, err_msg, activity_state_delete.__name__)
            update_log_status(log_dict, 400)
            raise ParamError(err_msg)
    
    # Extra validation if oauth
    if r_dict['lrs_auth'] == 'oauth':
        validate_oauth_state_or_profile_agent(r_dict, "state")
    return r_dict

@auth
@log_parent_action(method='POST', endpoint='activities/profile')
@check_oauth
def activity_profile_post(r_dict):
    log_dict = r_dict['initial_user_action']
    try:
        r_dict['activityId']
    except KeyError:
        err_msg = "Error -- activity_profile - method = %s, but activityId parameter missing.." % r_dict['method']
        log_exception(log_dict, err_msg, activity_profile_post.__name__)
        update_log_status(log_dict, 400)
        raise ParamError(err_msg)    
    try:
        r_dict['profileId']
    except KeyError:
        err_msg = "Error -- activity_profile - method = %s, but profileId parameter missing.." % r_dict['method']
        log_exception(log_dict, err_msg, activity_profile_post.__name__)
        update_log_status(log_dict, 400)
        raise ParamError(err_msg)

    if 'CONTENT_TYPE' not in r_dict or r_dict['CONTENT_TYPE'] != "application/json":
        err_msg = "The content type for activity profile POSTs must be application/json"
        log_exception(log_dict, err_msg, activity_profile_post.__name__)
        update_log_status(log_dict, 400)
        raise ParamError(err_msg)
    
    if 'body' not in r_dict:
        err_msg = "Could not find the profile document"
        log_exception(log_dict, err_msg, activity_profile_post.__name__)
        update_log_status(log_dict, 400)
        raise ParamError(err_msg)

    body_dict = r_dict.pop('raw_body', r_dict.pop('body', None))
    try:
        json.loads(body_dict)
        r_dict['profile'] = body_dict
    except Exception as e:
        err_msg = "Could not parse the content into JSON"
        log_exception(log_dict, err_msg, activity_profile_post.__name__)
        update_log_status(log_dict, 400)
        raise ParamError("\n".join((err_msg, e)))
    return r_dict

@auth
@log_parent_action(method='PUT', endpoint='activities/profile')
@check_oauth
def activity_profile_put(r_dict):
    log_dict = r_dict['initial_user_action']
    try:
        r_dict['activityId']
    except KeyError:
        err_msg = "Error -- activity_profile - method = %s, but activityId parameter missing.." % r_dict['method']
        log_exception(log_dict, err_msg, activity_profile_put.__name__)
        update_log_status(log_dict, 400)
        raise ParamError(err_msg)    
    try:
        r_dict['profileId']
    except KeyError:
        err_msg = "Error -- activity_profile - method = %s, but profileId parameter missing.." % r_dict['method']
        log_exception(log_dict, err_msg, activity_profile_put.__name__)
        update_log_status(log_dict, 400)
        raise ParamError(err_msg)
    
    if 'body' not in r_dict:
        err_msg = "Could not find the profile document"
        log_exception(log_dict, err_msg, activity_profile_put.__name__)
        update_log_status(log_dict, 400)
        raise ParamError(err_msg)

    # Set profile - req_parse converts all request bodies to dict, act profile needs it as string and need to replace single quotes with double quotes
    # b/c of quotation issue when using javascript with activity profile
    body_dict = r_dict.pop('raw_body', r_dict.pop('body', None))
    r_dict['profile'] = str(body_dict)
    return r_dict

@auth
@log_parent_action(method='GET', endpoint='activities/profile')
@check_oauth
def activity_profile_get(r_dict):
    log_dict = r_dict['initial_user_action']
    try:
        r_dict['activityId']
    except KeyError:
        err_msg = "Error -- activity_profile - method = %s, but no activityId parameter.. the activityId parameter is required" % r_dict['method']
        log_exception(log_dict, err_msg, activity_profile_get.__name__)
        update_log_status(log_dict, 400)
        raise ParamError(err_msg)
    return r_dict

@auth
@log_parent_action(method='DELETE', endpoint='activities/profile')
@check_oauth
def activity_profile_delete(r_dict):
    log_dict = r_dict['initial_user_action']
    try:
        r_dict['activityId']
    except KeyError:
        err_msg = "Error -- activity_profile - method = %s, but no activityId parameter.. the activityId parameter is required" % r_dict['method']
        log_exception(log_dict, err_msg, activity_profile_delete.__name__)
        update_log_status(log_dict, 400)
        raise ParamError(err_msg)
    try:
        r_dict['profileId']
    except KeyError:
        err_msg = "Error -- activity_profile - method = %s, but no profileId parameter.. the profileId parameter is required" % r_dict['method']
        log_exception(log_dict, err_msg, activity_profile_delete.__name__)
        update_log_status(log_dict, 400)
        raise ParamError(err_msg)
    return r_dict

@auth
@log_parent_action(method='GET', endpoint='activities')
@check_oauth
def activities_get(r_dict):
    log_dict = r_dict['initial_user_action']
    try:
        r_dict['activityId']
    except KeyError:
        err_msg = "Error -- activities - method = %s, but activityId parameter is missing" % r_dict['method']
        log_exception(log_dict, err_msg, activities_get.__name__)
        update_log_status(log_dict, 400)
        raise ParamError(err_msg)
    return r_dict

@auth
@log_parent_action(method='POST', endpoint='agents/profile')
@check_oauth
def agent_profile_post(r_dict):
    log_dict = r_dict['initial_user_action']
    try: 
        r_dict['agent']
    except KeyError:
        err_msg = "Error -- agent_profile - method = %s, but agent parameter missing.." % r_dict['method']
        log_exception(log_dict, err_msg, agent_profile_post.__name__)
        update_log_status(log_dict, 400)
        raise ParamError(err_msg)
    try:
        r_dict['profileId']
    except KeyError:
        err_msg = "Error -- agent_profile - method = %s, but profileId parameter missing.." % r_dict['method']
        log_exception(log_dict, err_msg, agent_profile_post.__name__)
        update_log_status(log_dict, 400)
        raise ParamError(msg)

    if 'CONTENT_TYPE' not in r_dict or r_dict['CONTENT_TYPE'] != "application/json":
        err_msg = "The content type for agent profile POSTs must be application/json"
        log_exception(log_dict, err_msg, agent_profile_post.__name__)
        update_log_status(log_dict, 400)
        raise ParamError(err_msg)
    
    if 'body' not in r_dict:
        err_msg = "Could not find the profile document"
        log_exception(log_dict, err_msg, agent_profile_post.__name__)
        update_log_status(log_dict, 400)
        raise ParamError(err_msg)

    # Extra validation if oauth
    if r_dict['lrs_auth'] == 'oauth':
        validate_oauth_state_or_profile_agent(r_dict, "profile")
    
    # Set profile
    body_dict = r_dict.pop('raw_body', r_dict.pop('body', None))
    try:
        json.loads(body_dict)
        r_dict['profile'] = body_dict
    except Exception as e:
        err_msg = "Could not parse the content into JSON"
        log_exception(log_dict, err_msg, agent_profile_post.__name__)
        update_log_status(log_dict, 400)
        raise ParamError("\n".join((err_msg, e)))
    return r_dict

@auth
@log_parent_action(method='PUT', endpoint='agents/profile')
@check_oauth
def agent_profile_put(r_dict):
    log_dict = r_dict['initial_user_action']
    try: 
        r_dict['agent']
    except KeyError:
        err_msg = "Error -- agent_profile - method = %s, but agent parameter missing.." % r_dict['method']
        log_exception(log_dict, err_msg, agent_profile_put.__name__)
        update_log_status(log_dict, 400)
        raise ParamError(err_msg)
    try:
        r_dict['profileId']
    except KeyError:
        err_msg = "Error -- agent_profile - method = %s, but profileId parameter missing.." % r_dict['method']
        log_exception(log_dict, err_msg, agent_profile_put.__name__)
        update_log_status(log_dict, 400)
        raise ParamError(msg)
    
    if 'body' not in r_dict:
        err_msg = "Could not find the profile document"
        log_exception(log_dict, err_msg, agent_profile_put.__name__)
        update_log_status(log_dict, 400)
        raise ParamError(err_msg)

    # Extra validation if oauth
    if r_dict['lrs_auth'] == 'oauth':
        validate_oauth_state_or_profile_agent(r_dict, "profile")
    
    body_dict = r_dict.pop('raw_body', r_dict.pop('body', None))
    r_dict['profile'] = str(body_dict)
    return r_dict

@auth
@log_parent_action(method='GET', endpoint='agents/profile')
@check_oauth
def agent_profile_get(r_dict):
    log_dict = r_dict['initial_user_action']
    try: 
        r_dict['agent']
    except KeyError:
        err_msg = "Error -- agent_profile - method = %s, but agent parameter missing.. the agent parameter is required" % r_dict['method']
        log_exception(log_dict, err_msg, agent_profile_get.__name__)
        update_log_status(log_dict, 400)
        raise ParamError(err_msg)

    # Extra validation if oauth
    if r_dict['lrs_auth'] == 'oauth':
        validate_oauth_state_or_profile_agent(r_dict, "profile")
    return r_dict

@auth
@log_parent_action(method='DELETE', endpoint='agents/profile')
@check_oauth
def agent_profile_delete(r_dict):
    log_dict = r_dict['initial_user_action']
    try: 
        r_dict['agent']
    except KeyError:
        err_msg = "Error -- agent_profile - method = %s, but no agent parameter.. the agent parameter is required" % r_dict['method']
        log_exception(log_dict, err_msg, agent_profile_delete.__name__)
        update_log_status(log_dict, 400)
        raise ParamError(err_msg)
    try:
        r_dict['profileId']
    except KeyError:
        err_msg = "Error -- agent_profile - method = %s, but no profileId parameter.. the profileId parameter is required" % r_dict['method']
        log_exception(log_dict, err_msg, agent_profile_delete.__name__)
        update_log_status(log_dict, 400)
        raise ParamError(err_msg)
    
    # Extra validation if oauth
    if r_dict['lrs_auth'] == 'oauth':
        validate_oauth_state_or_profile_agent(r_dict, "profile")
    return r_dict

@auth
@log_parent_action(method='GET', endpoint='agents')
@check_oauth
def agents_get(r_dict):
    log_dict = r_dict['initial_user_action']
    try: 
        r_dict['agent']
    except KeyError:
        err_msg = "Error -- agents url, but no agent parameter.. the agent parameter is required"
        log_exception(log_dict, err_msg, agents_get.__name__)
        update_log_status(log_dict, 400)
        raise ParamError(err_msg)
    return r_dict
