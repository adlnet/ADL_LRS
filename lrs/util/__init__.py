import ast
import json
import re
import urllib
import urlparse
from django.contrib.auth.models import User
from django.db.models import get_models, get_app
from django.contrib import admin
from django.contrib.admin.sites import AlreadyRegistered
from dateutil import parser
from lrs.exceptions import ParamError
from oauth_provider.models import Consumer
from oauth2_provider.provider.oauth2.models import Client

def get_lang(d, lang):
    if isinstance(d, dict):
        try:
            # try to return the lang version from dict.. {'en-US': 'I am American'}
            return {lang: d[lang]}
        except KeyError:
            # get the first element from the dict and return it... {'fr':'Je suis American'}
            return dict([next(d.iteritems())])
    # er... if it's not a dict, just return it
    return d

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
    except Exception:
        try:
            data = ast.literal_eval(incoming_data)
        except Exception:
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
        oauth = 1
        # it's a group.. gotta find out which of the 2 members is the client
        for member in auth.member.all():
            if member.account_name: 
                key = member.account_name
                if 'oauth2' in member.account_homePage.lower():
                    oauth = 2
                break
        # get consumer/client based on oauth version
        if oauth == 1:
            user = Consumer.objects.get(key__exact=key).user
        else:
            user = Client.objects.get(client_id__exact=key).user
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
