import json
from lrs import models
from lrs.exceptions import Unauthorized, ParamConflict, ParamError, Forbidden
from Authorization import auth
from django.utils.decorators import decorator_from_middleware
import pdb
import pprint
import logging
from datetime import datetime
from django.utils.timezone import utc
from functools import wraps
import ast

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
    method = r_dict['method']
    endpoint = r_dict['endpoint']
    token = r_dict['oauth_token']
    resource = token.resource
    urls = resource.get_urls()
    scope = resource.name
    err_msg = "Incorrect permissions to %s at %s" % (str(method), str(endpoint))
    
    if scope == 'all':
        pass
    elif scope == 'all/read':
        if method != 'GET':
            raise Forbidden(err_msg)
    elif scope == 'statements/read':
        if method != 'GET':
            raise Forbidden(err_msg)
        else:
            if not endpoint in urls:
                raise Forbidden(err_msg)
    elif scope == 'statements/write':
        if method == 'GET':
            raise Forbidden(err_msg)
        else:
            if not endpoint in urls:
                raise Forbidden(err_msg)
    elif scope == 'state':
        if endpoint in urls:
            # check for actors associated
            try:
                if method == 'PUT':
                    ag = r_dict['body']['agent']
                else:
                    ag = r_dict['parameters']['agent']                    
            except KeyError:
                raise Forbidden(err_msg)
            if not isinstance(ag, dict):
                try:
                    ag = ast.literal_eval(ag)
                except:
                    ag = json.loads(ag)
            agent = models.agent.objects.gen(**ag)[0]
            if agent.name != token.user.username:
                raise Forbidden(err_msg)
        else:
            raise Forbidden(err_msg)
    elif scope == 'profile':
        if endpoint in urls:
            if 'activityId' in r_dict['parameters']:
                pass #Once activities are tied to agents, check here
            else:
                try:
                    if method == 'PUT':
                        ag = r_dict['body']['agent']
                    else:
                        ag = r_dict['parameters']['agent']                    
                except KeyError:
                    raise Forbidden(err_msg)
                if not isinstance(ag, dict):
                    try:
                        ag = ast.literal_eval(ag)
                    except:
                        ag = json.loads(ag)                
                agent = models.agent.objects.gen(**ag)[0]            
                if agent.name != token.user.username:
                    raise Forbidden(err_msg)        
        else:
            raise Forbidden(err_msg)
    elif scope == 'statements/read/mine':
        if method == 'GET':
            if endpoint in urls:
                # check for only mine
                request['mine_read_only'] = True
            else:
                raise Forbidden(err_msg)
        else:
            raise Forbidden(err_msg)
    elif scope == 'define':
        if endpoint in urls:
            # check for actors associated
            pass    
        else:
            raise Forbidden(err_msg)    

@auth
@log_parent_action(method='POST', endpoint='statements')
def statements_post(r_dict):
    return r_dict

@auth
@log_parent_action(method='GET', endpoint='statements')
def statements_get(r_dict):
    return r_dict

@auth
@log_parent_action(method='PUT', endpoint='statements')
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
@check_oauth
@log_parent_action(method='PUT', endpoint='activities/state')
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
    
    # Set state
    r_dict['state'] = r_dict.pop('body')
    return r_dict

@auth
@check_oauth
@log_parent_action(method='GET', endpoint='activities/state')
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
    return r_dict

@auth
@check_oauth
@log_parent_action(method='DELETE', endpoint='activities/state')
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
    return r_dict

@auth
@check_oauth
@log_parent_action(method='PUT', endpoint='activities/profile')
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
        err_msg = "Could not find the profile"
        log_exception(log_dict, err_msg, activity_profile_put.__name__)
        update_log_status(log_dict, 400)
        raise ParamError(err_msg)

    # Set profile - req_parse converts all request bodies to dict, act profile needs it as string and need to replace single quotes with double quotes
    # b/c of quotation issue when using javascript with activity profile
    body_dict = r_dict.pop('raw_body', r_dict.pop('body', None))
    r_dict['profile'] = str(body_dict)
    return r_dict

@auth
@check_oauth
@log_parent_action(method='GET', endpoint='activities/profile')
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
@check_oauth
@log_parent_action(method='DELETE', endpoint='activities/profile')
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

@log_parent_action(method='GET', endpoint='activities')
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
@log_parent_action(method='PUT', endpoint='agents/profile')
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
        err_msg = "Could not find the profile"
        log_exception(log_dict, err_msg, agent_profile_put.__name__)
        update_log_status(log_dict, 400)
        raise ParamError(err_msg)
    
    # Set profile
    r_dict['profile'] = r_dict.pop('body')
    return r_dict

@log_parent_action(method='GET', endpoint='agents/profile')
def agent_profile_get(r_dict):
    log_dict = r_dict['initial_user_action']
    try: 
        r_dict['agent']
    except KeyError:
        err_msg = "Error -- agent_profile - method = %s, but agent parameter missing.. the agent parameter is required" % r_dict['method']
        log_exception(log_dict, err_msg, agent_profile_get.__name__)
        update_log_status(log_dict, 400)
        raise ParamError(err_msg)
    return r_dict

@auth
@log_parent_action(method='DELETE', endpoint='agents/profile')
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
    return r_dict

@log_parent_action(method='GET', endpoint='agents')
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
