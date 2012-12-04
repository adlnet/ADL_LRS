import json
from lrs.util import etag
from django.http import MultiPartParser
import ast
import StringIO
import pdb
import pprint

def handle_oauth_request(request, r_dict):
    r_dict = get_headers(request.META, r_dict)
    r_dict.update(request.GET.dict())
    if 'method' not in r_dict:
        r_dict['method'] = request.method
    r_dict['absolute_uri'] = request.build_absolute_uri()
    r_dict['parameters'] = request.REQUEST.items()
    r_dict['query_string'] = request.META.get('QUERY_STRING', '')
    r_dict['server_name'] = request.META.get('SERVER_NAME', '')
    r_dict['lrs_auth'] = 'oauth'
    return r_dict

def parse(request):
    r_dict = {}
    pdb.set_trace()
    # Traditional authorization should be passed in headers
    if 'Authorization' in request.META:
        if type(request.META['Authorization']) is dict:
            return handle_oauth_request(request, r_dict)
        else:
            r_dict['lrs_auth'] = 'http'
    elif 'HTTP_AUTHORIZATION' in request.META:
        if type(request.META['HTTP_AUTHORIZATION']) is dict:
            return handle_oauth_request(request, r_dict)
        else:
            r_dict['lrs_auth'] = 'http'

    # Authorization could be passed into body if cross origin request
    if 'Authorization' or 'HTTP_AUTHORIZATION' in request.body: 
        r_dict['lrs_auth'] = 'http'

    if 'lrs_auth' not in r_dict:
        r_dict['lrs_auth'] = 'none'

    r_dict['user'] = request.user

    if request.method == 'POST' and 'method' in request.GET:
        bdy = ast.literal_eval(request.body)
        r_dict.update(bdy)
        if 'content' in r_dict: # body is in 'content' for the IE cors POST
            r_dict['body'] = r_dict.pop('content')
    else:
        r_dict = parse_body(r_dict, request)

    r_dict = get_headers(request.META, r_dict)
    r_dict.update(request.GET.dict())
    if 'method' not in r_dict:
        r_dict['method'] = request.method
    return r_dict

def parse_body(r, request):
    if request.method == 'POST' or request.method == 'PUT':
        if 'multipart/form-data' in request.META['CONTENT_TYPE']:
            r.update(request.POST.dict())
            parser = MultiPartParser(request.META, StringIO.StringIO(request.raw_post_data),request.upload_handlers)
            post, files = parser.parse()
            r['files'] = files
        else:
            if request.body:
                r['body'] = request.body    

            if request.raw_post_data:
                r['raw_post_data'] = request.raw_post_data    

    return r

def get_headers(headers, r):
    # pdb.set_trace()
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
