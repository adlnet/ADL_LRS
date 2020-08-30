import ast
import json
import urllib
import urlparse
from isodate.isodatetime import parse_datetime
from django.conf import settings

from ..exceptions import ParamError

agent_ifps_can_only_be_one = ['mbox', 'mbox_sha1sum', 'openid', 'account']


def get_agent_ifp(data):
    ifp_sent = [
        a for a in agent_ifps_can_only_be_one if data.get(a, None) is not None]

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


def convert_to_datetime_object(timestr):
    try:
        date_object = parse_datetime(timestr)
    except ValueError as e:
        raise ParamError(
            "There was an error while parsing the date from %s -- Error: %s" % (timestr, e.message))
    return date_object


def convert_to_datatype(incoming_data):
    data = {}
    # GET data will be non JSON string-have to try literal_eval
    if isinstance(incoming_data, dict) or isinstance(incoming_data, list):
        return incoming_data
    # could get weird values that json lib will parse
    # ex: '"this is not json but would not fail"'
    if incoming_data.startswith('"'):
        incoming_data = incoming_data[1:-1]
    try:
        data = json.loads(incoming_data)
    except Exception:
        try:
            data = ast.literal_eval(incoming_data)
        except Exception, e:
            raise e
    return data


def convert_post_body_to_dict(incoming_data):
    encoded = True
    pairs = [s2 for s1 in incoming_data.split('&') for s2 in s1.split(';')]
    for p in pairs:
        # this is checked for cors requests
        if p.startswith('content='):
            if p == urllib.unquote_plus(p):
                encoded = False
            break
    qs = urlparse.parse_qsl(incoming_data)
    return dict((k, v) for k, v in qs), encoded


def get_lang(langdict, lang):
    if lang:
        if 'all' in lang:
            return langdict
        else:
            for la in lang:
                if la == "anylanguage":
                    try:
                        return {settings.LANGUAGE_CODE: langdict[settings.LANGUAGE_CODE]}
                    except KeyError:
                        first = langdict.iteritems().next()
                        return {first[0]: first[1]} 
                # Return where key = lang
                try:
                    return {la: langdict[la]}
                except KeyError:
                    # if the language header does match any exactly, then if it is only a 2 character
                    # header, try matching it against the keys again ('en' would match 'en-US')
                    if not '-' in la:
                        # get all keys from langdict...get all first parts of them..if la is in it, return it
                        for k in langdict.keys():
                            if '-' in k:
                                if la == k.split('-')[0]:
                                    return {la: langdict[k]}                    
                    pass
    first = langdict.iteritems().next()
    return {first[0]: first[1]}
