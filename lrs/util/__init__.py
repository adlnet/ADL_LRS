import ast
import json
import re
import urllib
import urlparse
from django.contrib.auth.models import User
from django.core.cache import get_cache
from django.db.models import get_models, get_app
from django.contrib import admin
from django.contrib.admin.sites import AlreadyRegistered
from dateutil import parser
from lrs.exceptions import ParamError, BadRequest
from oauth_provider.models import Consumer

agent_ifps_can_only_be_one = ['mbox', 'mbox_sha1sum', 'openID', 'account', 'openid']
def get_agent_ifp(data):
    ifp_sent = [a for a in agent_ifps_can_only_be_one if data.get(a, None) != None]    

    ifp = ifp_sent[0]
    canonical_version = data.get('canonical_version', True)
    ifp_dict = {'canonical_version': canonical_version}
    
    if not 'account' == ifp:
        ifp_dict[ifp] = data[ifp]
    else:
        if not isinstance(data['account'], dict):
            account = json.loads(data['account'])
        else:
            account = data['account']

        ifp_dict['account_homePage'] = account['homePage']
        ifp_dict['account_name'] = account['name']
    return ifp_dict

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