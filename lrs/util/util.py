import ast
import json
import urllib
import urlparse
from isodate.isodatetime import parse_datetime

from django.db.models import get_models, get_app
from django.contrib import admin
from django.contrib.admin.sites import AlreadyRegistered

from ..exceptions import ParamError

agent_ifps_can_only_be_one = ['mbox', 'mbox_sha1sum', 'openid', 'account']
def get_agent_ifp(data):
    ifp_sent = [a for a in agent_ifps_can_only_be_one if data.get(a, None) != None]    

    ifp = ifp_sent[0]
    ifp_dict = {}
    
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
        date_object = parse_datetime(timestr)
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

def get_lang(langdict, lang):
    if lang:
        # Return where key = lang
        try:
            return {lang:langdict[lang]}
        except KeyError:
            pass

    first = langdict.iteritems().next()      
    return {first[0]:first[1]}

def autoregister(*app_list):
    for app_name in app_list:
        app_models = get_app(app_name)
        for model in get_models(app_models):
            try:
                admin.site.register(model)
            except AlreadyRegistered:
                pass    