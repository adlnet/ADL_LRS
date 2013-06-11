import json
import ast
from django.contrib.auth.models import User
from django.core.cache import get_cache
from dateutil import parser
from lrs.models import Consumer
from lrs.exceptions import ParamError, BadRequest

def convert_to_utc(timestr):
    try:
        date_object = parser.parse(timestr)
    except ValueError as e:
        raise ParamError("There was an error while parsing the date from %s -- Error: %s" % (timestr, e.message))
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
            raise BadRequest("Cannot evaluate data into dictionary to parse -- Error: %s in %s") % (e.message, incoming_data)
    return data

def get_user_from_auth(auth):
    if not auth:
        return None
    if type(auth) ==  User:
        return auth #it is a User already
    else:
        # it's a group.. gotta find out which of the 2 members is the client
        for member in auth.member.all():
            if hasattr(member, 'agentaccount'):
                key = member.agentaccount.name

        user = Consumer.objects.get(key__exact=key).user
    return user