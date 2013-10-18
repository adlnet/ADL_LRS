import StringIO
import email
import json
import urllib
from collections import defaultdict
from django.http import MultiPartParser
from django.utils.translation import ugettext as _
from django.core.cache import get_cache
from lrs.util import etag, convert_to_dict, convert_post_body_to_dict
from lrs.util.jws import JWS, JWSException
from lrs.exceptions import OauthUnauthorized, ParamError, BadRequest
from oauth_provider.oauth.oauth import OAuthError
from oauth_provider.utils import send_oauth_error
from oauth_provider.decorators import CheckOAuth

att_cache = get_cache('attachment_cache')

def parse(request, more_id=None):
    r_dict = {}
    # Build headers from request in request dict
    r_dict['headers'] = get_headers(request.META)
    
    # Traditional authorization should be passed in headers
    r_dict['auth'] = {}
    if 'Authorization' in r_dict['headers']:
        # OAuth will always be dict, not http auth. Set required fields for oauth module and type for authentication
        # module
        set_authorization(r_dict, request)     
    elif 'Authorization' in request.body or 'HTTP_AUTHORIZATION' in request.body:
        # Authorization could be passed into body if cross origin request
        r_dict['auth']['type'] = 'http'
    else:
        r_dict['auth']['type'] = 'none'

    r_dict['params'] = {}
    # lookin for weird IE CORS stuff.. it'll be a post with a 'method' url param
    if request.method == 'POST' and 'method' in request.GET:
        bdy = convert_post_body_to_dict(request.body)
        # 'content' is in body for the IE cors POST
        if 'content' in bdy:
            r_dict['body'] = urllib.unquote(bdy.pop('content'))
        # headers are in the body too for IE CORS, we removes them
        r_dict['headers'].update(get_headers(bdy))
        for h in r_dict['headers']:
            bdy.pop(h, None)

        # remove extras from body
        bdy.pop('X-Experience-API-Version', None)
        bdy.pop('Content-Type', None)
        bdy.pop('If-Match', None)
        bdy.pop('If-None-Match', None)
        
        # all that should be left are params for the request, 
        # we adds them to the params object
        r_dict['params'].update(bdy)
        for k in request.GET:
            if k == 'method': # make sure the method param goes in the special method spot
                r_dict[k] = request.GET[k]
            else:
                r_dict['params'][k] = request.GET[k]
    # Just parse body for all non IE CORS stuff
    else:
        r_dict = parse_body(r_dict, request)
        # Update dict with any GET data
        r_dict['params'].update(request.GET.dict())

    # Method gets set for cors already
    if 'method' not in r_dict:
        # Differentiate GET and POST
        if request.method == "POST" and (request.path[6:] == 'statements' or request.path[6:] == 'statements/'):
            # Can have empty body for POST (acts like GET)
            if 'body' in r_dict:
                # If body is a list, it's a post
                if not isinstance(r_dict['body'], list):
                    # If actor verb and object not in body - means it's a GET or invalid POST
                    if not ('actor' in r_dict['body'] and 'verb' in r_dict['body'] and 'object' in r_dict['body']):
                        # If body keys are in get params - GET - else invalid request
                        if set(r_dict['body'].keys()).issubset(['statementId', 'voidedStatementId', 'agent', 'verb', 'activity', 'registration',
                            'related_activities', 'related_agents', 'since', 'until', 'limit', 'format', 'attachments', 'ascending']):
                            r_dict['method'] = 'GET'
                        else:
                            raise BadRequest("Statement is missing actor, verb, or object")
                    else:
                        r_dict['method'] = 'POST'
                else:
                    r_dict['method'] = 'POST'
            else:
                r_dict['method'] = 'GET'
        else:
            r_dict['method'] = request.method

    # Set if someone is hitting the statements/more endpoint
    if more_id:
        r_dict['more_id'] = more_id
    return r_dict

def set_authorization(r_dict, request):
    auth_params = r_dict['headers']['Authorization']
    if auth_params[:6] == 'OAuth ':
        # Make sure it has the required/valid oauth headers
        if CheckOAuth.is_valid_request(request):
            try:
                consumer, token, parameters = CheckOAuth.validate_token(request)
            except OAuthError, e:
                raise OauthUnauthorized(send_oauth_error(e))
            # Set consumer and token for authentication piece
            r_dict['auth']['oauth_consumer'] = consumer
            r_dict['auth']['oauth_token'] = token
            r_dict['auth']['type'] = 'oauth'
        else:
            raise OauthUnauthorized(send_oauth_error(OAuthError(_('Invalid OAuth request parameters.'))))

        # Used for OAuth scope
        endpoint = request.path[5:]
        # Since we accept with or without / on end
        if endpoint.endswith("/"):
            endpoint = endpoint[:-1]
        r_dict['auth']['endpoint'] = endpoint
    else:
        r_dict['auth']['type'] = 'http'    

def parse_attachment(r, request):
    message = request.body
    # i need boundary to be in the message for email to parse it right
    if 'boundary' not in message[:message.index("--")]:
        if 'boundary' in request.META['CONTENT_TYPE']:
            message = request.META['CONTENT_TYPE'] + message
        else:
            raise BadRequest("Could not find the boundary for the multipart content")
    msg = email.message_from_string(message)
    if msg.is_multipart():
        parts = []
        for part in msg.walk():
            parts.append(part)
        if len(parts) < 1:
            raise ParamError("The content of the multipart request didn't contain a statement")
        # ignore parts[0], it's the whole thing
        # parts[1] better be the statement
        r['body'] = convert_to_dict(parts[1].get_payload())
        if len(parts) > 2:
            r['payload_sha2s'] = []
            for a in parts[2:]:
                # attachments
                thehash = a.get("X-Experience-API-Hash")
                if not thehash:
                    raise BadRequest("X-Experience-API-Hash header was missing from attachment")
                headers = defaultdict(str)
                r['payload_sha2s'].append(thehash)
                # Save msg object to cache
                att_cache.set(thehash, a)
    else:
        raise ParamError("This content was not multipart for the multipart request.")
    # see if the posted statements have attachments
    att_stmts = []
    if isinstance(r['body'], list):
        for s in r['body']:
            if 'attachments' in s:
                att_stmts.append(s)
    elif 'attachments' in r['body']:
        att_stmts.append(r['body'])
    if att_stmts:
        # find if any of those statements with attachments have a signed statement
        signed_stmts = [(s,a) for s in att_stmts for a in s.get('attachments', None) if a['usageType'] == "http://adlnet.gov/expapi/attachments/signature"]
        for ss in signed_stmts:
            attmnt = att_cache.get(ss[1]['sha2']).get_payload(decode=True)
            jws = JWS(jws=attmnt)
            try:
                if not jws.verify() or not jws.validate(ss[0]):
                    raise BadRequest("The JSON Web Signature is not valid")
            except JWSException as jwsx:
                raise BadRequest(jwsx)    

def parse_body(r, request):
    if request.method == 'POST' or request.method == 'PUT':
        # Parse out profiles/states if the POST dict is not empty
        if 'multipart/form-data' in request.META['CONTENT_TYPE']:
            if request.POST.dict().keys():
                r['params'].update(request.POST.dict())
                parser = MultiPartParser(request.META, StringIO.StringIO(request.raw_post_data),request.upload_handlers)
                post, files = parser.parse()
                r['files'] = files
        # If it is multipart/mixed, parse out all data
        elif 'multipart/mixed' in request.META['CONTENT_TYPE']: 
            parse_attachment(r, request)
        # Normal POST/PUT data
        else:
            if request.body:
                # profile uses the request body
                r['raw_body'] = request.body
                # Body will be some type of string, not necessarily JSON
                r['body'] = convert_to_dict(request.body)
            else:
                raise Exception("No body in request")
    return r

def get_headers(headers):
    r = {}
    if 'HTTP_UPDATED' in headers:
        r['updated'] = headers['HTTP_UPDATED']
    elif 'updated' in headers:
        r['updated'] = headers['updated']

    r['CONTENT_TYPE'] = headers.get('CONTENT_TYPE', '')
    if r['CONTENT_TYPE'] == '' and 'Content-Type' in headers:
        r['CONTENT_TYPE'] = headers['Content-Type']

    r['ETAG'] = etag.get_etag_info(headers, required=False)
    if 'HTTP_AUTHORIZATION' in headers:
        r['Authorization'] = headers.get('HTTP_AUTHORIZATION', None)
    elif 'Authorization' in headers:
        r['Authorization'] = headers.get('Authorization', None)

    if 'Accept_Language' in headers:
        r['language'] = headers.get('Accept_Language', None)
    elif 'Accept-Language' in headers:
        r['language'] = headers['Accept-Language']
    return r
