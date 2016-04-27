import email
import urllib
import json
import itertools
from base64 import b64decode, b64encode
from isodate.isoerror import ISO8601Error
from isodate.isodatetime import parse_datetime

from django.core.cache import get_cache
from django.http import QueryDict

from . import convert_to_datatype, convert_post_body_to_dict
from etag import get_etag_info
from jws import JWS, JWSException
from ..exceptions import OauthUnauthorized, OauthBadRequest, ParamError, BadRequest

from oauth_provider.utils import get_oauth_request, require_params
from oauth_provider.decorators import CheckOauth
from oauth_provider.store import store
from oauth2_provider.provider.oauth2.models import AccessToken

att_cache = get_cache('attachment_cache')


def parse(request, more_id=None):
    # Parse request into body, headers, and params
    r_dict = {}
    # Start building headers from request.META
    r_dict['headers'] = get_headers(request.META)
    # Traditional authorization should be passed in headers
    r_dict['auth'] = {}
    if 'Authorization' in r_dict['headers']:
        # OAuth will always be dict, not http auth. Set required fields for oauth module and type for authentication module
        set_normal_authorization(request, r_dict)
    elif 'Authorization' in request.body or 'HTTP_AUTHORIZATION' in request.body:
        # Authorization could be passed into body if cross origin request
        # CORS OAuth not currently supported...
        set_cors_authorization(request, r_dict)
    else:
        raise BadRequest("Request has no authorization")

    # Init query params
    r_dict['params'] = {}
    # lookin for weird IE CORS stuff.. it'll be a post with a 'method' url param
    if request.method == 'POST' and 'method' in request.GET:
        parse_cors_request(request, r_dict)
    # Just parse body for all non IE CORS stuff
    else:
        parse_normal_request(request, r_dict)

    # Set method if not already set
    # CORS request will already be set - don't reset
    if 'method' not in r_dict:
        r_dict['method'] = request.method
    # Differentiate GET and POST
    if r_dict['method'] == "POST" and r_dict['auth']['endpoint'] == '/statements':
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
        # CORS request will already be set - don't reset
        if 'method' not in r_dict:
            r_dict['method'] = request.method
    # Set if someone is hitting the statements/more endpoint
    if more_id:
        r_dict['more_id'] = more_id
    return r_dict


def set_cors_authorization(request, r_dict):
    # Not allowed to set request body so this is just a copy
    body = convert_post_body_to_dict(request.body)
    if 'HTTP_AUTHORIZATION' not in r_dict['headers'] and 'HTTP_AUTHORIZATION' not in r_dict['headers']:
        if 'HTTP_AUTHORIZATION' in body:
            r_dict['headers']['Authorization'] = body.pop('HTTP_AUTHORIZATION')
        elif 'Authorization' in body:
            r_dict['headers']['Authorization'] = body.pop('Authorization')
        else:
            r_dict['headers']['Authorization'] = None
    r_dict['auth']['endpoint'] = get_endpoint(request)
    r_dict['auth']['type'] = 'http'


def set_normal_authorization(request, r_dict):
    auth_params = r_dict['headers']['Authorization']
    # OAuth1 and basic http auth come in as string
    r_dict['auth']['endpoint'] = get_endpoint(request)
    if auth_params[:6] == 'OAuth ':
        oauth_request = get_oauth_request(request)
        # Returns HttpBadRequest if missing any params
        missing = require_params(oauth_request)
        if missing:
            raise missing

        check = CheckOauth()
        e_type, error = check.check_access_token(request)
        if e_type and error:
            if e_type == 'auth':
                raise OauthUnauthorized(error)
            else:
                raise OauthBadRequest(error)
        # Consumer and token should be clean by now
        consumer = store.get_consumer(request, oauth_request, oauth_request['oauth_consumer_key'])
        token = store.get_access_token(request, oauth_request, consumer, oauth_request.get_parameter('oauth_token'))

        # Set consumer and token for authentication piece
        r_dict['auth']['oauth_consumer'] = consumer
        r_dict['auth']['oauth_token'] = token
        r_dict['auth']['type'] = 'oauth'
    elif auth_params[:7] == 'Bearer ':
        try:
            access_token = AccessToken.objects.get(token=auth_params[7:])
        except AccessToken.DoesNotExist:
            raise OauthUnauthorized("Access Token does not exist")
        else:
            if access_token.get_expire_delta() <= 0:
                raise OauthUnauthorized('Access Token has expired')
            r_dict['auth']['oauth_token'] = access_token
            r_dict['auth']['type'] = 'oauth2'
    else:
        r_dict['auth']['type'] = 'http'


def parse_normal_body(request, r_dict):
    if request.method == 'POST' or request.method == 'PUT':
        # If it is multipart/mixed we're expecting attachment data (also for signed statements)
        if 'multipart/mixed' in r_dict['headers']['CONTENT_TYPE']:
            parse_attachment(request, r_dict)
        # If it's any other content-type try parsing it out
        else:
            if request.body:
                # profile/states use the raw body
                r_dict['raw_body'] = request.body
                # Only for statements since document APIs don't have to be JSON
                if r_dict['auth']['endpoint'] == '/statements':
                    try:
                        r_dict['body'] = convert_to_datatype(request.body)
                    except Exception:
                        try:
                            r_dict['body'] = QueryDict(request.body).dict()
                        except Exception:
                            raise BadRequest("Could not parse request body")
                        else:
                            # QueryDict will create {'foo':''} key for any string - does not care if valid query string or not
                            for k, v in r_dict['body'].items():
                                if not v:
                                    raise BadRequest("Could not parse request body, no value for: %s" % k)
                else:
                    r_dict['body'] = request.body
            else:
                raise BadRequest("No body in request")
    return r_dict


def parse_cors_request(request, r_dict):
    # Convert body to dict
    body = convert_post_body_to_dict(request.body)
    # 'content' is in body for the IE cors POST
    if 'content' in body:
        # Grab what the normal body would be since it's in content (unquote if necessary)
        str_body = urllib.unquote(body.pop('content'))
        r_dict['raw_body'] = str_body
        # Only for statements since document API bodies don't have to be JSON
        if r_dict['auth']['endpoint'] == '/statements':
            try:
                # Should convert to dict if data is in JSON format
                r_dict['body'] = convert_to_datatype(str_body)
            except Exception:
                try:
                    # Convert to dict if data is in form format (foo=bar)
                    r_dict['body'] = QueryDict(str_body).dict()
                except Exception:
                    raise BadRequest("Could not parse request body in CORS request")
                else:
                    # QueryDict will create {'foo':''} key for any string - does not care if valid query string or not
                    for k, v in r_dict['body'].items():
                        if not v:
                            raise BadRequest("Could not parse request body in CORS request, no value for: %s" % k)
        else:
            r_dict['body'] = str_body
        # Catch attachments early
        if 'attachments' in r_dict['body']:
            raise BadRequest(("Attachments are not supported in cross origin requests since they require a "
                              "multipart/mixed Content-Type"))

    # Remove extra headers from body that we already captured in get_headers
    body.pop('X-Experience-API-Version', None)
    body.pop('Content-Type', None)
    body.pop('If-Match', None)
    body.pop('If-None-Match', None)
    body.pop('HTTP_AUTHORIZATION', None)
    body.pop('Authorization', None)

    # all that should be left are params for the request, we add them to the params object
    r_dict['params'].update(body)
    # Add query string params
    for k in request.GET:
        # make sure the method param goes in the special method spot
        if k == 'method':
            r_dict[k] = request.GET[k].upper()
        else:
            r_dict['params'][k] = request.GET[k]

    # If it is a CORS PUT OR POST make sure it has content
    if (r_dict['method'] == 'PUT' or r_dict['method'] == 'POST') \
            and 'body' not in r_dict:
        raise BadRequest("CORS PUT or POST both require content parameter")
    set_agent_param(r_dict)


def parse_normal_request(request, r_dict):
    r_dict = parse_normal_body(request, r_dict)
    # Update dict with any GET data
    r_dict['params'].update(request.GET.dict())
    set_agent_param(r_dict)


def parse_attachment(request, r_dict):
    # Email library insists on having the multipart header in the body - workaround
    message = request.body
    if 'boundary' not in message[:message.index("--")]:
        if 'boundary' in r_dict['headers']['CONTENT_TYPE']:
            message = "Content-Type:" + r_dict['headers']['CONTENT_TYPE'] + "\r\n" + message
        else:
            raise BadRequest("Could not find the boundary for the multipart content")

    msg = email.message_from_string(message)
    if msg.is_multipart():
        parts = msg.get_payload()
        stmt_part = parts.pop(0)
        if stmt_part['Content-Type'] != "application/json":
            raise ParamError("Content-Type of statement was not application/json")

        try:
            r_dict['body'] = json.loads(stmt_part.get_payload())
        except Exception:
            raise ParamError("Statement was not valid JSON")

        # Find the signature sha2 from the list attachment values in the statements (there should only be one)
        if isinstance(r_dict['body'], list):
            signature_att = list(itertools.chain(*[[a.get('sha2', None) for a in s['attachments'] if a.get('usageType', None) == "http://adlnet.gov/expapi/attachments/signature"] for s in r_dict['body'] if 'attachments' in s]))
        else:
            signature_att = [a.get('sha2', None) for a in r_dict['body']['attachments'] if a.get('usageType', None) == "http://adlnet.gov/expapi/attachments/signature" and 'attachments' in r_dict['body']]

        # Get all sha2s from the request
        payload_sha2s = [p.get('X-Experience-API-Hash', None) for p in msg.get_payload()]
        # Check each sha2 in payload, if even one of them is None then there is a missing hash
        for sha2 in payload_sha2s:
            if not sha2:
                raise BadRequest("X-Experience-API-Hash header was missing from attachment")

        # Check the sig sha2 in statements if it not in the payload sha2s then the sig sha2 is missing
        for sig in signature_att:
            if sig:
                if sig not in payload_sha2s:
                    raise BadRequest("Signature attachment is missing from request")
            else:
                raise BadRequest("Signature attachment is missing from request")

        # We know all sha2s are there so set it and loop through each payload
        r_dict['payload_sha2s'] = payload_sha2s
        for part in msg.get_payload():
            xhash = part.get('X-Experience-API-Hash')
            c_type = part['Content-Type']
            # Payloads are base64 encoded implictly from email lib (except for plaintext)
            if "text/plain" in c_type:
                payload = b64encode(part.get_payload())
            else:
                payload = part.get_payload()
            att_cache.set(xhash, payload)
    else:
        raise ParamError("This content was not multipart for the multipart request.")
    # See if the posted statements have attachments
    att_stmts = []
    if isinstance(r_dict['body'], list):
        for s in r_dict['body']:
            if 'attachments' in s:
                att_stmts.append(s)
    elif 'attachments' in r_dict['body']:
        att_stmts.append(r_dict['body'])
    if att_stmts:
        # find if any of those statements with attachments have a signed statement
        signed_stmts = [(s, a) for s in att_stmts for a in s.get('attachments', None) if a['usageType'] == "http://adlnet.gov/expapi/attachments/signature"]
        for ss in signed_stmts:
            attmnt = b64decode(att_cache.get(ss[1]['sha2']))
            jws = JWS(jws=attmnt)
            try:
                if not jws.verify() or not jws.validate(ss[0]):
                    raise BadRequest("The JSON Web Signature is not valid")
            except JWSException as jwsx:
                raise BadRequest(jwsx)


def get_endpoint(request):
    # Used for OAuth scope
    endpoint = request.path[5:]
    # Since we accept with or without / on end
    if endpoint.endswith("/"):
        return endpoint[:-1]
    return endpoint


def get_headers(headers):
    header_dict = {}
    # Get updated header
    if 'HTTP_UPDATED' in headers:
        try:
            header_dict['updated'] = parse_datetime(headers.pop('HTTP_UPDATED'))
        except (Exception, ISO8601Error):
            raise ParamError("Updated header was not a valid ISO8601 timestamp")
    elif 'updated' in headers:
        try:
            header_dict['updated'] = parse_datetime(headers.pop('updated'))
        except (Exception, ISO8601Error):
            raise ParamError("Updated header was not a valid ISO8601 timestamp")

    # Get content type header
    header_dict['CONTENT_TYPE'] = headers.pop('CONTENT_TYPE', None)
    if not header_dict['CONTENT_TYPE'] and 'Content-Type' in headers:
        header_dict['CONTENT_TYPE'] = headers.pop('Content-Type')
    # Could not exist with deletes
    if header_dict['CONTENT_TYPE']:
        # FireFox automatically adds ;charset=foo to the end of headers. This will strip it out
        if ';' in header_dict['CONTENT_TYPE'] and 'boundary' not in header_dict['CONTENT_TYPE']:
            header_dict['CONTENT_TYPE'] = header_dict['CONTENT_TYPE'].split(';')[0]

    # Get etag
    header_dict['ETAG'] = get_etag_info(headers, required=False)

    # Get authorization - don't pop off - needed for setting authorization
    if 'HTTP_AUTHORIZATION' in headers:
        header_dict['Authorization'] = headers.get('HTTP_AUTHORIZATION')
    elif 'Authorization' in headers:
        header_dict['Authorization'] = headers.get('Authorization')

    # Get language
    if 'Accept_Language' in headers:
        header_dict['language'] = headers.pop('Accept_Language')
    elif 'Accept-Language' in headers:
        header_dict['language'] = headers.pop('Accept-Language')

    # Get xapi version
    if 'X-Experience-API-Version' in headers:
        header_dict['X-Experience-API-Version'] = headers.pop('X-Experience-API-Version')
    return header_dict


def set_agent_param(r_dict):
    # Convert agent to dict if get param for statements
    if 'agent' in r_dict['params'] and r_dict['auth']['endpoint'] == '/statements':
        try:
            r_dict['params']['agent'] = convert_to_datatype(r_dict['params']['agent'])
        except Exception:
            raise BadRequest("Agent param was not a valid JSON structure")
