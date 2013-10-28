import json
import ast
from django.contrib.auth.models import User
from django.core.cache import get_cache
from django.db.models import get_models, get_app
from django.contrib import admin
from django.contrib.admin.sites import AlreadyRegistered
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
    if type(incoming_data) == dict:
        return incoming_data
    try:
        data = json.loads(incoming_data)
    except Exception, e:
        try:
            data = ast.literal_eval(incoming_data)
        except Exception, e:
            data = incoming_data
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
        for member in auth.member.all():
            if member.account_name: 
                key = member.account_name

        user = Consumer.objects.get(key__exact=key).user
    return user

def validate_uuid(uuid):
    import re
    id_regex = re.compile("[a-fA-F0-9]{8}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{12}")
    return id_regex.match(uuid)

def autoregister(*app_list):
    for app_name in app_list:
        app_models = get_app(app_name)
        for model in get_models(app_models):
            try:
                admin.site.register(model)
            except AlreadyRegistered:
                pass    