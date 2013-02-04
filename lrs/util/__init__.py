from django.contrib.auth.models import User
from lrs.models import Consumer, SystemAction
import logging

logger = logging.getLogger('user_system_actions')

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