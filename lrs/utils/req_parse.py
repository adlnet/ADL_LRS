import ast
import base64
import email
import hashlib
import json
from isodate.isoerror import ISO8601Error
from isodate.isodatetime import parse_datetime
from Crypto.PublicKey import RSA
from jose import jws

from django.contrib.sites.shortcuts import get_current_site
from django.core.cache import caches
from django.urls import reverse
from django.http import QueryDict

from . import convert_to_datatype, convert_post_body_to_dict
from .etag import get_etag_info
from ..exceptions import OauthUnauthorized, OauthBadRequest, ParamError, BadRequest

from oauth_provider.utils import get_oauth_request, require_params
from oauth_provider.decorators import CheckOauth
from oauth_provider.store import store

att_cache = caches['attachment_cache']


def parse(request, more_id=None):
    # Parse request into body, headers, and params
    r_dict = {}
    # Start building headers from request.META (cors headers get added later)
    r_dict['headers'] = get_headers(request.META)
    # Traditional authorization should be passed in headers
    r_dict['auth'] = {}

    body_str = request.body.decode("utf-8") if isinstance(request.body, bytes) else request.body

    if 'Authorization' in r_dict['headers']:
        # OAuth will always be dict, not http auth. Set required fields for
        # oauth module and type for authentication module
        set_normal_authorization(request, r_dict)
    elif 'Authorization' in body_str or 'HTTP_AUTHORIZATION' in body_str:
        # Authorization could be passed into body if cross origin request
        # CORS OAuth not currently supported...
        set_cors_authorization(request, r_dict)
    else:
        raise BadRequest("Request has no authorization")

    # Init query params
    r_dict['params'] = {}
    # lookin for weird IE CORS stuff.. it'll be a post with a 'method' url
    # param
    if request.method == 'POST' and 'method' in request.GET:
        parse_cors_request(request, r_dict)
    # Just parse body for all non IE CORS stuff
    else:
        parse_normal_request(request, r_dict)

    # Set if someone is hitting the statements/more endpoint
    if more_id:
        r_dict['more_id'] = more_id

    r_dict['domain'] = get_current_site(request).domain
    r_dict['scheme'] = 'https' if request.is_secure() else 'http'
    return r_dict


def set_cors_authorization(request, r_dict):
    # Not allowed to set request body so this is just a copy
    body_str = request.body.decode("utf-8") if isinstance(request.body, bytes) else request.body
    body, encoded = convert_post_body_to_dict(body_str)
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
        consumer = store.get_consumer(
            request, oauth_request, oauth_request['oauth_consumer_key'])
        token = store.get_access_token(
            request, oauth_request, consumer, oauth_request.get_parameter('oauth_token'))

        # Set consumer and token for authentication piece
        r_dict['auth']['oauth_consumer'] = consumer
        r_dict['auth']['oauth_token'] = token
        r_dict['auth']['type'] = 'oauth'
    else:
        r_dict['auth']['type'] = 'http'


def parse_post_put_body(request, r_dict):

    # If there is no body, django test client won't send a content type
    if r_dict['headers']['CONTENT_TYPE']:
        # If it is multipart/mixed we're expecting attachment data (also for
        # signed statements)
        if 'multipart/mixed' in r_dict['headers']['CONTENT_TYPE']:
            parse_attachment(request, r_dict)
        # If it's any other content-type try parsing it out
        else:
            body_str = request.body.decode("utf-8") if isinstance(request.body, bytes) else request.body
            if body_str:
                # profile/states use the raw body
                r_dict['raw_body'] = body_str
                # Only for statements since document APIs don't have to be JSON
                if r_dict['auth']['endpoint'] == reverse('lrs:statements').lower():
                    try:
                        r_dict['body'] = convert_to_datatype(body_str)
                    except Exception:
                        try:
                            r_dict['body'] = QueryDict(body_str).dict()
                        except Exception:
                            raise BadRequest("Could not parse request body")
                        else:
                            # QueryDict will create {'foo':''} key for any
                            # string - does not care if valid query string or
                            # not
                            for k, v in r_dict['body'].items():
                                if not v:
                                    raise BadRequest(
                                        "Could not parse request body, no value for: %s" % k)
                else:
                    r_dict['body'] = body_str
            else:
                raise BadRequest("No body in request")
    return r_dict


def parse_cors_request(request, r_dict):
    # Query string must only have method param
    try:
        r_dict['method'] = request.GET['method'].upper()
    except Exception:
        raise BadRequest("Could not find method parameter for CORS request")
    if len(list(request.GET.keys())) > 1:
        raise BadRequest("CORS must only include method in query string parameters") 

    # Convert body to dict
    body_str = request.body.decode("utf-8") if isinstance(request.body, bytes) else request.body
    body, encoded = convert_post_body_to_dict(body_str)
    if not encoded:
        raise BadRequest("content in CORS was not URL encoded")

    # 'content' is in body for the IE cors POST
    if 'content' in body:
        # Grab what the normal body would be since it's in content
        decoded_body = body.pop('content')
        r_dict['raw_body'] = decoded_body

        # Only for statements since document API bodies don't have to be JSON (can be text)
        if r_dict['auth']['endpoint'] == reverse('lrs:statements').lower():
            try:
                # Should convert to dict if data is in JSON format
                r_dict['body'] = convert_to_datatype(decoded_body)
            except Exception:
                try:
                    # Convert to dict if data is in form format (foo=bar)
                    r_dict['body'] = QueryDict(decoded_body).dict()
                except Exception:
                    raise BadRequest(
                        "Could not parse request body in CORS request")
                else:
                    # QueryDict will create {'foo':''} key for any string -
                    # does not care if valid query string or not
                    for k, v in list(r_dict['body'].items()):
                        if not v:
                            raise BadRequest(
                                "Could not parse request body in CORS request, no value for: %s" % k)
        else:
            r_dict['body'] = decoded_body
    else:
        # If it is a CORS PUT OR POST make sure it has content
        if (r_dict['method'] == 'PUT' or r_dict['method'] == 'POST'):
            raise BadRequest("content form parameter required when sending content via CORS")

    # treat these form params as headers
    header_list = ['X-Experience-API-Version', 'Content-Type', 'If-Match', \
        'If-None-Match', 'Authorization', 'Content-Length']
    header_dict = {k:body[k] for k in body if k in header_list}
    r_dict['headers'].update(header_dict)
    if 'If-Match' in r_dict['headers']:
        r_dict['headers']['ETAG']['HTTP_IF_MATCH'] = r_dict['headers']['If-Match']
    if 'If-None-Match' in r_dict['headers']:
        r_dict['headers']['ETAG']['HTTP_IF_NONE_MATCH'] = r_dict['headers']['If-None-Match']
    # pop these headers out of body
    for h in header_list:
        body.pop(h, None)

    # all that should be left are params for the request, we add them to the
    # params object
    r_dict['params'].update(body)


def parse_normal_request(request, r_dict):
    if request.method == 'POST' or request.method == 'PUT':
        r_dict = parse_post_put_body(request, r_dict)
    elif request.method == 'DELETE':
        # Delete can have data which will be in parameter or get params
        raw = request.body
        decoded = raw if isinstance(raw, str) else raw.decode("utf-8")
        if decoded != '':
            r_dict['params'].update(ast.literal_eval(decoded))
    r_dict['params'].update(request.GET.dict())
    r_dict['method'] = request.method


def parse_attachment(request, r_dict):

    message = request.body if isinstance(request.body, str) else request.body.decode("utf-8")
    
    # Python email parse library insists on having the multipart header in the body
    # workaround to add it to the beginning since it will always be included in the header
    lines = message.splitlines()
    if not lines[0].startswith('Content-Type: multipart/mixed; boundary='):
        if 'boundary' in r_dict['headers']['CONTENT_TYPE']:
            message = "Content-Type:" + \
                r_dict['headers']['CONTENT_TYPE'] + "\r\n" + message
        else:
            raise BadRequest(
                "Could not find the boundary for the multipart content")
    
    # end workaround
    msg = email.message_from_string(message)
    if msg.is_multipart():

        # Stmt part will always be first
        stmt_part = msg.get_payload().pop(0)
        if stmt_part['Content-Type'] != "application/json":
            raise ParamError(
                "Content-Type of statement was not application/json")
        
        try:
            r_dict['body'] = json.loads(stmt_part.get_payload())
        except Exception:
            raise ParamError("Statement was not valid JSON")
        
        if isinstance(r_dict['body'], dict):
            stmt_sha2s = [a['sha2'] for a in r_dict['body']['attachments'] if 'attachments' in r_dict['body']]
        else:
            stmt_sha2s = [a['sha2'] for s in r_dict['body'] if 'attachments' in s for a in s['attachments']]
        
        # Each attachment in msg must have binary encoding and hash in header
        part_dict = {}
        
        for part in msg.get_payload():
            encoding = part.get('Content-Transfer-Encoding', None)
            
            if encoding != "binary":
                raise BadRequest(
                    "Each attachment part should have 'binary' as Content-Transfer-Encoding")
            
            if 'X-Experience-API-Hash' not in part:
                raise BadRequest(
                    "X-Experience-API-Hash header was missing from attachment")
            
            part_hash = part.get('X-Experience-API-Hash')
            validate_hash(part_hash, part)
            
            part_dict[part_hash] = part
        
        r_dict['payload_sha2s'] = [
            p['X-Experience-API-Hash'] for p in msg.get_payload()
        ]

        if not set(r_dict['payload_sha2s']).issubset(set(stmt_sha2s)):
            raise BadRequest("Not all attachments match with statement payload")
        
        parse_signature_attachments(r_dict, part_dict)
    else:
        raise ParamError(
            "This content was not multipart for the multipart request.")
    # Saves all attachments (including signatures) to memory temporarily
    # for further processing
    temp_save_attachments(msg)


def validate_hash(part_hash, part):
    if part_hash != str(hashlib.sha256(get_part_payload(part).encode("utf-8")).hexdigest()):
        raise BadRequest(
            "Hash header %s did not match calculated hash" \
            % part_hash)

def parse_signature_attachments(r_dict, part_dict):
    # Find the signature sha2 from the list attachment values in the
    # statements (there should only be one)
    signed_stmts = []
    unsigned_stmts = []
    stmt_attachment_pairs = []
    if isinstance(r_dict['body'], list):
        for stmt in r_dict['body']:
            if 'attachments' in stmt:
                stmt_attachment_pairs.append((stmt, [a.get('sha2', None) for a in stmt['attachments']
                                if a.get('usageType', None) == "http://adlnet.gov/expapi/attachments/signature"]))
    else:        
        if 'attachments' in r_dict['body']:
            stmt_attachment_pairs = [(r_dict['body'], [a.get('sha2', None) for a in r_dict['body']['attachments']
                             if a.get('usageType', None) == "http://adlnet.gov/expapi/attachments/signature"])]
    signed_stmts = [sap for sap in stmt_attachment_pairs if sap[1]]
    unsigned_stmts = [sap for sap in stmt_attachment_pairs if not sap[1]]

    if unsigned_stmts:
        for tup in unsigned_stmts:
            validate_non_signature_attachment(unsigned_stmts, r_dict['payload_sha2s'], part_dict)

    if signed_stmts:
        handle_signatures(signed_stmts, r_dict['payload_sha2s'], part_dict)


def validate_non_signature_attachment(unsigned_stmts, sha2s, part_dict):
    for tup in unsigned_stmts:
        atts = tup[0]['attachments']
        for att in atts:
            sha2 = att.get('sha2')
            # If there isn't a fileUrl, the sha field must match
            # a received attachment payload
            if 'fileUrl' not in att:
                # Should be listed in sha2s - sha2s couldn't not match
                if sha2 not in sha2s:
                    raise BadRequest(
                        "Could not find attachment payload with sha: %s" % sha2)


def handle_signatures(stmt_tuples, sha2s, part_dict):
    for tup in stmt_tuples:
        for sha2 in tup[1]:           
            # Should be listed in sha2s - sha2s couldn't not match
            if sha2 not in sha2s:
                raise BadRequest(
                    "Could not find attachment payload with sha: %s" % sha2)                    
            part = part_dict[sha2]
            # Content type must be set to octet/stream
            if part['Content-Type'] != 'application/octet-stream':
                raise BadRequest(
                    "Signature attachment must have Content-Type of "\
                    "'application/octet-stream'")
            validate_signature(tup, part)


def validate_signature(tup, part):
    sha2_key = tup[1][0]
    signature = get_part_payload(part)
    algorithm = jws.get_unverified_headers(signature).get('alg', None)
    if not algorithm:
        raise BadRequest(
            "No signing algorithm found for JWS signature")
    if algorithm != 'RS256' and algorithm != 'RS384' and algorithm != 'RS512':
        raise BadRequest(
            "JWS signature must be calculated with SHA-256, SHA-384 or" \
            "SHA-512 algorithms")
    x5c = jws.get_unverified_headers(signature).get('x5c', None)
    jws_payload = jws.get_unverified_claims(signature)
    body_payload = tup[0]
    # If x.509 was used to sign, the public key should be in the x5c header and you need to verify it
    # If using RS256, RS384, or RS512 some JWS libs require a real private key to create JWS - xAPI spec
    # only has SHOULD - need to look into. If x.509 is necessary then
    # if no x5c header is found this should fail
    if x5c:
        verified = False
        try:
            verified = jws.verify(
                signature, cert_to_key(x5c[0]), algorithm)
        except Exception as e:
            raise BadRequest("The JWS is not valid: %s" % str(e))
        else:
            if not verified:
                raise BadRequest(
                    "The JWS is not valid - could not verify signature")
            # Compare statements
            if not compare_payloads(jws_payload, body_payload, sha2_key):
                raise BadRequest(
                    "The JWS is not valid - payload and body statements do not match")
    else:
        # Compare statements
        if not compare_payloads(jws_payload, body_payload, sha2_key):
            raise BadRequest(
                "The JWS is not valid - payload and body statements do not match")


def compare_payloads(jws_payload, body_payload, sha2_key):
    # Need to copy the dict so use dict()
    try:
        jws_placeholder = dict(json.loads(jws_payload))
    except Exception:
        raise BadRequest(
            f"Invalid JSON serialization of signature payload\n\nJWS: {type(jws_payload)} {jws_payload}\n\nBODY: {type(body_payload)} {body_payload}")

    jws_placeholder.pop("id", None)
    jws_placeholder.pop("authority", None)
    jws_placeholder.pop("stored", None)
    jws_placeholder.pop("timestamp", None)
    jws_placeholder.pop("version", None)
    jws_placeholder.pop("attachments", None)
    # JWT specific standard fields
    jws_placeholder.pop("iss", None)
    jws_placeholder.pop("sub", None)
    jws_placeholder.pop("aud", None)
    jws_placeholder.pop("exp", None)
    jws_placeholder.pop("nbf", None)
    jws_placeholder.pop("iat", None)
    jws_placeholder.pop("jti", None)

    body_placeholder = dict(body_payload)
    body_placeholder.pop("id", None)
    body_placeholder.pop("authority", None)
    body_placeholder.pop("stored", None)
    body_placeholder.pop("timestamp", None)
    body_placeholder.pop("version", None)
    body_placeholder.pop("attachments", None)

    return json.dumps(jws_placeholder, sort_keys=True) == json.dumps(body_placeholder, sort_keys=True)


def temp_save_attachments(msg):
    for part in msg.get_payload():
        xhash = part.get('X-Experience-API-Hash')
        att_cache.set(xhash, get_part_payload(part))


def get_part_payload(part):
    c_type = part['Content-Type']
    # Email class adds newline for text/plain
    # workaround
    if "text/plain" in c_type:
        payload = part.get_payload()
        if payload.endswith('\n'):
            payload = payload[:-1]
    else:
        payload = part.get_payload()
    return payload


def cert_to_key(cert):
    return RSA.importKey(base64.b64decode(cert))


def get_endpoint(request):
    # Used for OAuth scope
    parts = request.path.split("/")
    parts[1] = parts[1].lower()
    endpoint = "/".join(parts)
    # Since we accept with or without / on end
    if endpoint.endswith("/"):
        return endpoint[:-1]
    return endpoint


def get_headers(headers):
    header_dict = {}
    # Get updated header
    if 'HTTP_UPDATED' in headers:
        try:
            header_dict['updated'] = parse_datetime(
                headers.pop('HTTP_UPDATED'))
        except (Exception, ISO8601Error):
            raise ParamError(
                "Updated header was not a valid ISO8601 timestamp")
    elif 'updated' in headers:
        try:
            header_dict['updated'] = parse_datetime(headers.pop('updated'))
        except (Exception, ISO8601Error):
            raise ParamError(
                "Updated header was not a valid ISO8601 timestamp")

    # Get content type header
    header_dict['CONTENT_TYPE'] = headers.pop('CONTENT_TYPE', None)
    if not header_dict['CONTENT_TYPE'] and 'Content-Type' in headers:
        header_dict['CONTENT_TYPE'] = headers.pop('Content-Type')
    # Could not exist with deletes
    if header_dict['CONTENT_TYPE']:
        # FireFox automatically adds ;charset=foo to the end of headers. This
        # will strip it out
        if ';' in header_dict['CONTENT_TYPE'] and 'boundary' not in header_dict['CONTENT_TYPE']:
            header_dict['CONTENT_TYPE'] = header_dict['CONTENT_TYPE'].split(';')[
                0]

    # Get etag
    header_dict['ETAG'] = get_etag_info(headers)

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
    elif 'HTTP_ACCEPT_LANGUAGE' in headers:
        header_dict['language'] = headers.pop('HTTP_ACCEPT_LANGUAGE')

    # Get xapi version
    if 'X-Experience-API-Version' in headers:
        header_dict[
            'X-Experience-API-Version'] = headers.pop('X-Experience-API-Version')
    return header_dict