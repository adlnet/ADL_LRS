import json
import ast
from django.contrib.auth.models import User
from dateutil import parser
from lrs.models import Consumer, SystemAction
from lrs.exceptions import ParamError, BadRequest
import logging

logger = logging.getLogger('user_system_actions')

def convert_to_utc(timestr):
    try:
        date_object = parser.parse(timestr)
    except ValueError as e:
        raise ParamError(e)
    return date_object

def convert_to_dict(incoming_data):
    data = {}
    # GET data will be non JSON string-have to try literal_eval
    try:
        data = json.loads(incoming_data)
    except Exception, e:
        try:
            data = ast.literal_eval(incoming_data)
        except Exception, e:
            raise BadRequest("Cannot evaluate data into dictionary to parse")
    return data

def convert_post_body_to_dict(incoming_data):
    import urllib, urlparse
    qs = urlparse.parse_qsl(urllib.unquote_plus(incoming_data))
    return dict((k,v) for k, v in qs)

def get_user_from_auth(auth):
    if not auth:
        return None
    if type(auth) ==  User:
        return auth #it is a User already
    else:
        # it's a group.. gotta find out which of the 2 members is the client
        try:
            key = auth.member.all()[0].agent_account.name
        except:
            key = auth.member.all()[1].agent_account.name
        user = Consumer.objects.get(key__exact=key).user
    return user

def log_info_processing(log_dict, method, func_name):
    if log_dict:
        log_dict['message'] = 'Processing %s data in %s' % (method, func_name)
        logger.info(msg=log_dict)

def log_exception(log_dict, err_msg, func_name):
    if log_dict:
        log_dict['message'] = err_msg + " in %s" % func_name
        logger.exception(msg=log_dict)

def update_parent_log_status(log_dict, status):
    if log_dict:
        parent_action = SystemAction.objects.get(id=log_dict['parent_id'])
        parent_action.status_code = status
        parent_action.save()

def log_message(log_dict, msg, name, func_name, err=False):
    if log_dict:
        log_dict['message'] = msg + " in %s.%s" % (name, func_name)
        if err:
            logger.error(msg=log_dict)
        else:
            logger.info(msg=log_dict)