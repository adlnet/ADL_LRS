import StringIO
import email
from collections import defaultdict
from django.http import MultiPartParser
from django.utils.translation import ugettext as _
from lrs.util import etag, convert_to_dict
from lrs.exceptions import OauthUnauthorized, ParamError
from oauth_provider.oauth.oauth import OAuthError
from oauth_provider.utils import send_oauth_error
from oauth_provider.decorators import CheckOAuth
import pdb
import pprint

def parse(request, more_id=None):
    r_dict = {}
    
    # Build headers from request in request dict
    r_dict = get_headers(request.META, r_dict)
    
    # Traditional authorization should be passed in headers
    if 'Authorization' in r_dict:
        # OAuth will always be dict, not http auth. Set required fields for oauth module and lrs_auth for authentication
        # module
        auth_params = r_dict['Authorization']
        if auth_params[:6] == 'OAuth ':
            # Make sure it has the required/valid oauth headers
            if CheckOAuth.is_valid_request(request):
                try:
                    consumer, token, parameters = CheckOAuth.validate_token(request)
                except OAuthError, e:
                    raise OauthUnauthorized(send_oauth_error(e))
                # Set consumer and token for authentication piece
                r_dict['oauth_consumer'] = consumer
                r_dict['oauth_token'] = token
                r_dict['lrs_auth'] = 'oauth'
            else:
                raise OauthUnauthorized(send_oauth_error(OAuthError(_('Invalid request parameters.'))))

            # Used for OAuth scope
            endpoint = request.path[5:]
            # Since we accept with or without / on end
            if endpoint.endswith("/"):
                endpoint = endpoint[:-1]
            r_dict['endpoint'] = endpoint
        else:
            r_dict['lrs_auth'] = 'http'
    elif 'Authorization' in request.body or 'HTTP_AUTHORIZATION' in request.body:
        # Authorization could be passed into body if cross origin request
        r_dict['lrs_auth'] = 'http'
    else:
        r_dict['lrs_auth'] = 'none'

    if request.method == 'POST' and 'method' in request.GET:
        bdy = convert_to_dict(request.body)
        r_dict.update(bdy)
        if 'content' in r_dict: # body is in 'content' for the IE cors POST
            r_dict['body'] = r_dict.pop('content')
    else:
        r_dict = parse_body(r_dict, request)

    # Update dict with any GET data
    r_dict.update(request.GET.dict())

    # A 'POST' can actually be a GET
    if 'method' not in r_dict:
        if request.method == "POST" and "application/json" not in r_dict['CONTENT_TYPE'] and "multipart/mixed" not in r_dict['CONTENT_TYPE']:
            r_dict['method'] = 'GET'
        else:
            r_dict['method'] = request.method

    # Set if someone is hitting the statements/more endpoint
    if more_id:
        r_dict['more_id'] = more_id

    return r_dict

def parse_body(r, request):
    if request.method == 'POST' or request.method == 'PUT':
        # Parse out profiles/states if the POST dict is not empty
        if 'multipart/form-data' in request.META['CONTENT_TYPE']:
            if request.POST.dict().keys():
                r.update(request.POST.dict())
                parser = MultiPartParser(request.META, StringIO.StringIO(request.raw_post_data),request.upload_handlers)
                post, files = parser.parse()
                r['files'] = files
        # If it is multipart/mixed, parse out all data
        elif 'multipart/mixed' in request.META['CONTENT_TYPE']: 
            message = request.body
            # i need boundary to be in the message for email to parse it right
            if 'boundary' not in message[:message.index("--")]:
                if 'boundary' in request.META['CONTENT_TYPE']:
                    message = request.META['CONTENT_TYPE'] + message
                else:
                    raise ParamError("Could not find the boundary for this multipart content")
            msg = email.message_from_string(message)
            if msg.is_multipart():
                parts = []
                for part in msg.walk():
                    parts.append(part)
                if len(parts) < 1:
                    raise ParamError("The content didn't contain a statement")
                # ignore parts[0], it's the whole thing
                # parts[1] better be the statement
                r['body'] = convert_to_dict(parts[1].get_payload())
                if len(parts) > 2:
                    r['attachment_payloads'] = []
                    for a in parts[2:]:
                        # attachments
                        thehash = a.get("X-Experience-API-Hash")
                        if not thehash:
                            raise ParamError("X-Experience-API-Hash header was missing from attachment")
                        headers = defaultdict(str)
                        # Don't need headers right now
                        # for h,v in a.items():
                        #     headers[h] = v
                        # r['attachment_payloads'].append({thehash : {"headers":headers,"payload":a.get_payload()}})
                        # r['attachment_payloads'].append({thehash : {"payload":a.get_payload()}})
                        r['attachment_payloads'].append((thehash, a.get_payload()))

            else:
                raise ParamError("This content was not multipart.")
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

def get_headers(headers, r):
    if 'HTTP_UPDATED' in headers:
        r['updated'] = headers['HTTP_UPDATED']
    else:
        r['updated'] = headers.get('updated', None)

    r['CONTENT_TYPE'] = headers.get('CONTENT_TYPE', '')

    r['ETAG'] = etag.get_etag_info(headers, r, required=False)
    if 'HTTP_AUTHORIZATION' in headers:
        r['Authorization'] = headers['HTTP_AUTHORIZATION']
    if 'Authorization' in headers:
        r['Authorization'] = headers['Authorization']
    if 'Accept_Language' in headers:
        r['language'] = headers['Accept_Language']    
    return r
